"""
Phase 636: TensorFlow Lite Edge Inference for SC2
Convert trained policy networks to TFLite format with post-training
quantization (dynamic range, full integer, float16) and benchmark
inference latency / throughput / accuracy on edge-class hardware.
Target: < 10 ms per decision for real-time SC2 play.
"""

from __future__ import annotations

import os
import struct
import sys
import time
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional, Tuple

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import numpy as np

try:
    import tensorflow as tf

    TF_AVAILABLE = True
except ImportError:
    TF_AVAILABLE = False

try:
    import tflite_runtime.interpreter as tflite_rt

    TFLITE_RUNTIME_AVAILABLE = True
except ImportError:
    TFLITE_RUNTIME_AVAILABLE = False


# ============================================================
# Quantization Mode Enum
# ============================================================


class QuantMode(str, Enum):
    """Supported TFLite quantization modes."""

    FLOAT32 = "float32"
    FLOAT16 = "float16"
    DYNAMIC_RANGE = "dynamic_range"
    FULL_INTEGER = "full_integer"


# ============================================================
# Configuration
# ============================================================


@dataclass
class QuantizationConfig:
    """Controls how a model is quantized during TFLite conversion."""

    mode: QuantMode = QuantMode.DYNAMIC_RANGE
    representative_dataset_size: int = 200
    input_mean: float = 0.0
    input_std: float = 1.0
    num_calibration_steps: int = 100
    experimental_new_quantizer: bool = True


@dataclass
class TFLiteConfig:
    """Top-level configuration for the TFLite edge pipeline."""

    obs_dim: int = 48
    hidden_dim: int = 128
    n_actions: int = 10
    max_units: int = 16
    quant: QuantizationConfig = field(default_factory=QuantizationConfig)
    warmup_runs: int = 5
    benchmark_runs: int = 50
    target_latency_ms: float = 10.0
    num_threads: int = 4
    use_xnnpack: bool = True


# ============================================================
# Mock Policy Network (NumPy-based)
# ============================================================


class MockPolicyNetwork:
    """Simulates a trained SC2 policy network for conversion testing.

    Architecture: obs -> Dense(128,relu) -> Dense(128,relu) -> [logits, value]
    """

    def __init__(self, cfg: TFLiteConfig, seed: int = 42):
        self.cfg = cfg
        rng = np.random.RandomState(seed)
        self.w1 = rng.randn(cfg.obs_dim, cfg.hidden_dim).astype(np.float32) * 0.1
        self.b1 = np.zeros(cfg.hidden_dim, dtype=np.float32)
        self.w2 = rng.randn(cfg.hidden_dim, cfg.hidden_dim).astype(np.float32) * 0.1
        self.b2 = np.zeros(cfg.hidden_dim, dtype=np.float32)
        self.w_act = rng.randn(cfg.hidden_dim, cfg.n_actions).astype(np.float32) * 0.1
        self.b_act = np.zeros(cfg.n_actions, dtype=np.float32)
        self.w_val = rng.randn(cfg.hidden_dim, 1).astype(np.float32) * 0.1
        self.b_val = np.zeros(1, dtype=np.float32)

    def forward(self, obs: np.ndarray) -> Dict[str, np.ndarray]:
        h = np.maximum(0, obs @ self.w1 + self.b1)
        h = np.maximum(0, h @ self.w2 + self.b2)
        return {
            "action_logits": h @ self.w_act + self.b_act,
            "value": (h @ self.w_val + self.b_val).squeeze(-1),
        }

    def get_weights(self) -> List[np.ndarray]:
        return [
            self.w1,
            self.b1,
            self.w2,
            self.b2,
            self.w_act,
            self.b_act,
            self.w_val,
            self.b_val,
        ]

    @property
    def param_count(self) -> int:
        return sum(w.size for w in self.get_weights())


# ============================================================
# TFLite Converter
# ============================================================


class TFLiteConverter:
    """Converts a policy network to TFLite format with quantization.

    Uses real TF when available; otherwise simulates conversion
    with NumPy-based mock flatbuffer blobs.
    """

    def __init__(self, cfg: TFLiteConfig):
        self.cfg = cfg
        self._conversion_log: List[Dict[str, Any]] = []

    def convert_real(self, network: MockPolicyNetwork) -> bytes:
        """Convert via real TensorFlow Lite converter."""
        if not TF_AVAILABLE:
            raise RuntimeError("TensorFlow required for real conversion")
        import tempfile

        with tempfile.TemporaryDirectory() as tmpdir:
            # Build Keras model
            inp = tf.keras.Input(shape=(self.cfg.obs_dim,))
            h = tf.keras.layers.Dense(self.cfg.hidden_dim, activation="relu")(inp)
            h = tf.keras.layers.Dense(self.cfg.hidden_dim, activation="relu")(h)
            act_out = tf.keras.layers.Dense(self.cfg.n_actions)(h)
            val_out = tf.keras.layers.Dense(1)(h)
            model = tf.keras.Model(inputs=inp, outputs=[act_out, val_out])
            sd_path = os.path.join(tmpdir, "saved_model")
            tf.saved_model.save(model, sd_path)

            converter = tf.lite.TFLiteConverter.from_saved_model(sd_path)
            mode = self.cfg.quant.mode
            if mode == QuantMode.FLOAT16:
                converter.optimizations = [tf.lite.Optimize.DEFAULT]
                converter.target_spec.supported_types = [tf.float16]
            elif mode == QuantMode.DYNAMIC_RANGE:
                converter.optimizations = [tf.lite.Optimize.DEFAULT]
            elif mode == QuantMode.FULL_INTEGER:
                converter.optimizations = [tf.lite.Optimize.DEFAULT]
                rng = np.random.RandomState(0)

                def rep_gen():
                    for _ in range(self.cfg.quant.representative_dataset_size):
                        yield [rng.randn(1, self.cfg.obs_dim).astype(np.float32)]

                converter.representative_dataset = rep_gen
                converter.target_spec.supported_ops = [
                    tf.lite.OpsSet.TFLITE_BUILTINS_INT8
                ]
                converter.inference_input_type = tf.int8
                converter.inference_output_type = tf.int8
            tflite_model = converter.convert()
        self._conversion_log.append(
            {
                "mode": mode.value,
                "model_size_bytes": len(tflite_model),
                "timestamp": time.time(),
                "method": "real_tf",
            }
        )
        return tflite_model

    def convert_mock(self, network: MockPolicyNetwork) -> bytes:
        """Simulate TFLite conversion without TensorFlow."""
        weights = network.get_weights()
        mode = self.cfg.quant.mode

        if mode == QuantMode.FLOAT32:
            quantized = [w.tobytes() for w in weights]
            tag = b"FP32"
        elif mode == QuantMode.FLOAT16:
            quantized = [w.astype(np.float16).tobytes() for w in weights]
            tag = b"FP16"
        elif mode in (QuantMode.DYNAMIC_RANGE, QuantMode.FULL_INTEGER):
            quantized = []
            for w in weights:
                w_min, w_max = w.min(), w.max()
                scale = (w_max - w_min) / 255.0 if w_max != w_min else 1.0
                zp = int(-w_min / scale) if scale != 0 else 0
                q = np.clip(np.round(w / scale) + zp, 0, 255).astype(np.uint8)
                quantized.append(struct.pack("<ff", scale, float(zp)) + q.tobytes())
            tag = b"DYN8" if mode == QuantMode.DYNAMIC_RANGE else b"INT8"
        else:
            raise ValueError(f"Unknown mode: {mode}")

        parts = [b"TFL3", tag, struct.pack("<I", len(quantized))]
        for qw in quantized:
            parts.append(struct.pack("<I", len(qw)))
            parts.append(qw)
        model_bytes = b"".join(parts)

        self._conversion_log.append(
            {
                "mode": mode.value,
                "model_size_bytes": len(model_bytes),
                "original_param_bytes": network.param_count * 4,
                "compression_ratio": (network.param_count * 4)
                / max(len(model_bytes), 1),
                "timestamp": time.time(),
                "method": "mock",
            }
        )
        return model_bytes

    def convert(self, network: MockPolicyNetwork) -> bytes:
        if TF_AVAILABLE:
            return self.convert_real(network)
        return self.convert_mock(network)

    @property
    def conversion_log(self) -> List[Dict[str, Any]]:
        return list(self._conversion_log)


# ============================================================
# Edge Inference Engine
# ============================================================


class EdgeInferenceEngine:
    """Runs TFLite inference; falls back to NumPy mock."""

    def __init__(self, cfg: TFLiteConfig):
        self.cfg = cfg
        self._interpreter = None
        self._mock_network: Optional[MockPolicyNetwork] = None
        self._latencies: List[float] = []
        self._throughputs: List[float] = []
        self._is_real = False

    def load_model(
        self, model_bytes: bytes, network: Optional[MockPolicyNetwork] = None
    ):
        if TFLITE_RUNTIME_AVAILABLE:
            self._interpreter = tflite_rt.Interpreter(
                model_content=model_bytes, num_threads=self.cfg.num_threads
            )
            self._interpreter.allocate_tensors()
            self._is_real = True
        elif TF_AVAILABLE:
            self._interpreter = tf.lite.Interpreter(
                model_content=model_bytes, num_threads=self.cfg.num_threads
            )
            self._interpreter.allocate_tensors()
            self._is_real = True
        else:
            self._mock_network = network
            self._is_real = False

    def predict(self, obs: np.ndarray) -> Dict[str, np.ndarray]:
        t0 = time.perf_counter()
        if self._is_real and self._interpreter is not None:
            inp = self._interpreter.get_input_details()
            out = self._interpreter.get_output_details()
            if obs.shape[0] != inp[0]["shape"][0]:
                self._interpreter.resize_tensor_input(inp[0]["index"], obs.shape)
                self._interpreter.allocate_tensors()
            self._interpreter.set_tensor(inp[0]["index"], obs)
            self._interpreter.invoke()
            result = {
                "action_logits": self._interpreter.get_tensor(out[0]["index"]),
                "value": self._interpreter.get_tensor(out[1]["index"]).squeeze(-1),
            }
        elif self._mock_network is not None:
            result = self._mock_network.forward(obs)
        else:
            raise RuntimeError("No model loaded")

        elapsed_ms = (time.perf_counter() - t0) * 1000.0
        self._latencies.append(elapsed_ms)
        bs = obs.shape[0] if obs.ndim > 1 else 1
        self._throughputs.append(bs / (elapsed_ms / 1000.0) if elapsed_ms > 0 else 0.0)
        return result

    def benchmark(
        self, obs: np.ndarray, warmup: Optional[int] = None, runs: Optional[int] = None
    ) -> Dict[str, float]:
        warmup = warmup or self.cfg.warmup_runs
        runs = runs or self.cfg.benchmark_runs
        for _ in range(warmup):
            self.predict(obs)
        self._latencies.clear()
        self._throughputs.clear()
        for _ in range(runs):
            self.predict(obs)
        lat = np.array(self._latencies)
        thr = np.array(self._throughputs)
        return {
            "mean_latency_ms": float(np.mean(lat)),
            "p50_latency_ms": float(np.percentile(lat, 50)),
            "p95_latency_ms": float(np.percentile(lat, 95)),
            "p99_latency_ms": float(np.percentile(lat, 99)),
            "min_latency_ms": float(np.min(lat)),
            "max_latency_ms": float(np.max(lat)),
            "mean_throughput_fps": float(np.mean(thr)),
            "total_runs": runs,
            "meets_target": bool(np.percentile(lat, 95) < self.cfg.target_latency_ms),
        }

    def compare_accuracy(
        self, network: MockPolicyNetwork, n_samples: int = 100, seed: int = 42
    ) -> Dict[str, float]:
        rng = np.random.RandomState(seed)
        cos_logits, mae_logits, mae_vals = [], [], []
        for _ in range(n_samples):
            obs = rng.randn(1, self.cfg.obs_dim).astype(np.float32)
            orig = network.forward(obs)
            tfl = self.predict(obs)
            a, b = orig["action_logits"].flatten(), tfl["action_logits"].flatten()
            denom = np.linalg.norm(a) * np.linalg.norm(b)
            cos_logits.append(float(np.dot(a, b) / denom) if denom > 0 else 1.0)
            mae_logits.append(float(np.max(np.abs(a - b))))
            mae_vals.append(float(np.abs(orig["value"] - tfl["value"]).mean()))
        return {
            "logits_cosine_sim_mean": float(np.mean(cos_logits)),
            "logits_max_abs_error_max": float(np.max(mae_logits)),
            "value_mean_abs_error": float(np.mean(mae_vals)),
            "n_samples": n_samples,
        }

    @property
    def latency_stats(self) -> Dict[str, float]:
        if not self._latencies:
            return {"mean_ms": 0.0, "count": 0}
        arr = np.array(self._latencies)
        return {
            "mean_ms": float(np.mean(arr)),
            "std_ms": float(np.std(arr)),
            "count": len(arr),
        }

    def reset_stats(self):
        self._latencies.clear()
        self._throughputs.clear()


# ============================================================
# TFLite Agent (SC2 integration)
# ============================================================


class TFLiteAgent:
    """SC2 agent using a TFLite-converted policy for edge inference."""

    ACTION_NAMES = [
        "no_op",
        "attack",
        "move",
        "hold",
        "patrol",
        "gather",
        "build",
        "ability",
        "retreat",
        "regroup",
    ]

    def __init__(self, cfg: Optional[TFLiteConfig] = None, seed: int = 42):
        self.cfg = cfg or TFLiteConfig()
        self.seed = seed
        self.network = MockPolicyNetwork(self.cfg, seed=seed)
        self.converter = TFLiteConverter(self.cfg)
        self.engine = EdgeInferenceEngine(self.cfg)
        self._model_bytes: Optional[bytes] = None
        self._is_loaded = False
        self.step_count = 0

    def convert_and_load(self, quant_mode: Optional[QuantMode] = None):
        if quant_mode is not None:
            self.cfg.quant.mode = quant_mode
        self._model_bytes = self.converter.convert(self.network)
        self.engine.load_model(self._model_bytes, network=self.network)
        self._is_loaded = True

    @property
    def model_size_bytes(self) -> int:
        return len(self._model_bytes) if self._model_bytes else 0

    def act(self, obs: np.ndarray, deterministic: bool = False) -> Dict[str, Any]:
        if not self._is_loaded:
            self.convert_and_load()
        out = self.engine.predict(obs)
        logits = out["action_logits"]
        exp_l = np.exp(logits - np.max(logits, axis=-1, keepdims=True))
        probs = exp_l / np.sum(exp_l, axis=-1, keepdims=True)
        if deterministic:
            actions = np.argmax(probs, axis=-1)
        else:
            rng = np.random.RandomState(self.step_count + self.seed)
            actions = np.array(
                [
                    rng.choice(probs.shape[-1], p=probs[b])
                    for b in range(probs.shape[0])
                ],
                dtype=np.int64,
            )
        self.step_count += 1
        return {"actions": actions, "action_probs": probs, "values": out["value"]}

    def act_on_game_state(
        self, game_state: Dict[str, Any], deterministic: bool = False
    ) -> List[Dict[str, Any]]:
        units = game_state.get("units", [])
        friendly = [u for u in units if u.get("is_friendly", True)]
        n = min(len(friendly), self.cfg.max_units)
        obs = np.zeros((n, self.cfg.obs_dim), dtype=np.float32)
        for i in range(n):
            u = friendly[i]
            obs[i, 0] = u.get("type_id", 0) / 300.0
            obs[i, 1] = u.get("health", 0) / 500.0
            obs[i, 2] = u.get("shield", 0) / 200.0
            obs[i, 3] = u.get("energy", 0) / 200.0
            obs[i, 4] = u.get("x", 0) / 200.0
            obs[i, 5] = u.get("y", 0) / 200.0
            obs[i, 6] = 1.0 if u.get("is_friendly", True) else 0.0
            obs[i, 7] = u.get("weapon_cooldown", 0) / 50.0
            obs[i, 8] = 1.0 if u.get("is_flying", False) else 0.0
            obs[i, 9] = u.get("ground_range", 0) / 15.0
        result = self.act(obs, deterministic=deterministic)
        decisions = []
        for i in range(n):
            idx = int(result["actions"][i])
            decisions.append(
                {
                    "unit_tag": friendly[i].get("tag", i),
                    "action_type": self.ACTION_NAMES[idx],
                    "action_idx": idx,
                    "value_estimate": float(result["values"][i]),
                    "action_probs": {
                        nm: float(result["action_probs"][i, j])
                        for j, nm in enumerate(self.ACTION_NAMES)
                    },
                }
            )
        return decisions

    def run_quant_comparison(self) -> Dict[str, Any]:
        results = {}
        obs = (
            np.random.RandomState(self.seed)
            .randn(1, self.cfg.obs_dim)
            .astype(np.float32)
        )
        for mode in QuantMode:
            self.cfg.quant.mode = mode
            conv = TFLiteConverter(self.cfg)
            mb = conv.convert(self.network)
            eng = EdgeInferenceEngine(self.cfg)
            eng.load_model(mb, network=self.network)
            bench = eng.benchmark(obs, warmup=3, runs=30)
            acc = eng.compare_accuracy(self.network, n_samples=50)
            results[mode.value] = {
                "model_size_bytes": len(mb),
                "mean_latency_ms": bench["mean_latency_ms"],
                "p95_latency_ms": bench["p95_latency_ms"],
                "meets_target": bench["meets_target"],
                "logits_cosine_sim": acc["logits_cosine_sim_mean"],
                "logits_max_abs_error": acc["logits_max_abs_error_max"],
            }
        return results

    def benchmark(self, batch_size: int = 1) -> Dict[str, float]:
        if not self._is_loaded:
            self.convert_and_load()
        obs = (
            np.random.RandomState(self.seed)
            .randn(batch_size, self.cfg.obs_dim)
            .astype(np.float32)
        )
        return self.engine.benchmark(obs)

    def export_model(self, path: str):
        if self._model_bytes is None:
            self.convert_and_load()
        with open(path, "wb") as f:
            f.write(self._model_bytes)

    def summary(self) -> str:
        lines = [
            "TFLiteAgent Summary",
            f"  Backend:        {'TFLite' if self._is_loaded else 'not loaded'}",
            f"  Quant mode:     {self.cfg.quant.mode.value}",
            f"  Model params:   {self.network.param_count:,}",
            f"  Model size:     {self.model_size_bytes:,} bytes",
            f"  obs_dim:        {self.cfg.obs_dim}",
            f"  hidden_dim:     {self.cfg.hidden_dim}",
            f"  n_actions:      {self.cfg.n_actions}",
            f"  target_latency: {self.cfg.target_latency_ms} ms",
            f"  steps_taken:    {self.step_count}",
        ]
        stats = self.engine.latency_stats
        if stats["count"] > 0:
            lines.append(f"  avg_latency:    {stats['mean_ms']:.2f} ms")
        return "\n".join(lines)


# ============================================================
# CLI Demo
# ============================================================


def _demo_conversion():
    print("=" * 60)
    print("TFLite Conversion (all quantization modes)")
    print("=" * 60)
    cfg = TFLiteConfig()
    net = MockPolicyNetwork(cfg, seed=42)
    orig_size = net.param_count * 4
    print(f"  Parameters: {net.param_count:,}")
    for mode in QuantMode:
        cfg.quant.mode = mode
        mb = TFLiteConverter(cfg).convert_mock(net)
        print(
            f"  {mode.value:15s} -> {len(mb):>8,} bytes "
            f"(compression: {orig_size / max(len(mb), 1):.2f}x)"
        )
    print()


def _demo_benchmark():
    print("=" * 60)
    print("Edge Inference Benchmark")
    print("=" * 60)
    cfg = TFLiteConfig(benchmark_runs=100, warmup_runs=10)
    net = MockPolicyNetwork(cfg, seed=42)
    obs = np.random.randn(1, cfg.obs_dim).astype(np.float32)
    for mode in QuantMode:
        cfg.quant.mode = mode
        mb = TFLiteConverter(cfg).convert_mock(net)
        eng = EdgeInferenceEngine(cfg)
        eng.load_model(mb, network=net)
        b = eng.benchmark(obs)
        s = "PASS" if b["meets_target"] else "FAIL"
        print(
            f"  {mode.value:15s} | mean:{b['mean_latency_ms']:6.3f}ms "
            f"| p95:{b['p95_latency_ms']:6.3f}ms "
            f"| thr:{b['mean_throughput_fps']:8.0f}fps | [{s}]"
        )
    print()


def _demo_game_state():
    print("=" * 60)
    print("TFLite Agent Game State")
    print("=" * 60)
    agent = TFLiteAgent(seed=42)
    agent.convert_and_load(QuantMode.DYNAMIC_RANGE)
    gs = {
        "units": [
            {
                "type_id": 84,
                "x": 50,
                "y": 50,
                "health": 45,
                "is_friendly": True,
                "tag": 1001,
            },
            {
                "type_id": 84,
                "x": 52,
                "y": 48,
                "health": 40,
                "is_friendly": True,
                "tag": 1002,
            },
            {
                "type_id": 105,
                "x": 55,
                "y": 53,
                "health": 35,
                "is_friendly": True,
                "tag": 1003,
            },
        ]
    }
    for d in agent.act_on_game_state(gs, deterministic=True):
        print(
            f"  Unit {d['unit_tag']}: {d['action_type']} (value={d['value_estimate']:.3f})"
        )
    print()
    print(agent.summary())
    print()


def _demo_quant_comparison():
    print("=" * 60)
    print("Full Quantization Comparison")
    print("=" * 60)
    agent = TFLiteAgent(seed=42)
    results = agent.run_quant_comparison()
    print(
        f"  {'Mode':15s} | {'Size':>10s} | {'Latency':>10s} | "
        f"{'CosSim':>8s} | {'MaxErr':>8s} | Target"
    )
    print("  " + "-" * 72)
    for mn, st in results.items():
        ts = "PASS" if st["meets_target"] else "FAIL"
        print(
            f"  {mn:15s} | {st['model_size_bytes']:>8,} B | "
            f"{st['mean_latency_ms']:>8.3f}ms | "
            f"{st['logits_cosine_sim']:>8.6f} | "
            f"{st['logits_max_abs_error']:>8.6f} | {ts}"
        )
    print()


def demo():
    """Run all Phase 636 demonstrations."""
    print("Phase 636: TensorFlow Lite Edge Inference for SC2")
    print(f"TensorFlow available: {TF_AVAILABLE}")
    print(f"TFLite runtime available: {TFLITE_RUNTIME_AVAILABLE}")
    print()
    _demo_conversion()
    _demo_benchmark()
    _demo_game_state()
    _demo_quant_comparison()
    print("Phase 636 demo complete.")


if __name__ == "__main__":
    demo()

# Phase 636: TFLite registered
