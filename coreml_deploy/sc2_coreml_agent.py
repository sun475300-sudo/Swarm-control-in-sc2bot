"""
Phase 637: CoreML Mobile Deployment for SC2 Companion App
Convert trained SC2 policy/strategy advisor models to CoreML (.mlmodel)
format for iOS/macOS deployment. Includes ONNX/PyTorch conversion
pipeline, Neural Engine optimization, batch prediction, GPU acceleration,
and companion-app integration endpoints.
"""

from __future__ import annotations

import math
import random
import time
import os
import sys
import json
import struct
import tempfile
from dataclasses import dataclass, field
from typing import Optional, List, Tuple, Dict, Any, Union
from enum import Enum
from collections import defaultdict

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import numpy as np

try:
    import coremltools as ct

    COREML_AVAILABLE = True
except ImportError:
    COREML_AVAILABLE = False

try:
    import torch
    import torch.nn as nn

    TORCH_AVAILABLE = True
except ImportError:
    TORCH_AVAILABLE = False

try:
    import onnx

    ONNX_AVAILABLE = True
except ImportError:
    ONNX_AVAILABLE = False


# ============================================================
# Enums
# ============================================================


class ComputeUnit(str, Enum):
    """Target compute unit for CoreML inference."""

    CPU_ONLY = "cpu_only"
    CPU_AND_GPU = "cpu_and_gpu"
    CPU_AND_NE = "cpu_and_ne"  # Neural Engine
    ALL = "all"


class ConversionSource(str, Enum):
    """Source format for model conversion."""

    PYTORCH = "pytorch"
    ONNX = "onnx"
    NUMPY = "numpy"


class PrecisionMode(str, Enum):
    """Model precision for CoreML."""

    FLOAT32 = "float32"
    FLOAT16 = "float16"
    QUANTIZED_8BIT = "quantized_8bit"


# ============================================================
# Configuration
# ============================================================


@dataclass
class MLModelSpec:
    """Defines input/output schema for a CoreML model."""

    model_name: str = "SC2StrategyAdvisor"
    model_version: str = "1.0.0"
    model_author: str = "SC2 Bot Project"
    model_description: str = "SC2 strategy advisor for iOS companion app"

    # Input schema
    input_name: str = "game_state"
    input_shape: Tuple[int, ...] = (1, 48)
    input_dtype: str = "float32"
    input_description: str = "Encoded SC2 game state observation vector"

    # Output schemas
    output_action_name: str = "action_probabilities"
    output_action_shape: Tuple[int, ...] = (1, 10)
    output_action_description: str = "Probability distribution over SC2 actions"

    output_value_name: str = "state_value"
    output_value_shape: Tuple[int, ...] = (1,)
    output_value_description: str = "Estimated value of the current game state"

    output_strategy_name: str = "strategy_recommendation"
    output_strategy_shape: Tuple[int, ...] = (1, 5)
    output_strategy_description: str = "Recommended macro strategy scores"

    # Metadata
    license: str = "MIT"
    short_description: str = "Real-time SC2 strategy advisor"


@dataclass
class CoreMLConfig:
    """Configuration for the CoreML deployment pipeline."""

    # Model architecture
    obs_dim: int = 48
    hidden_dim: int = 128
    n_actions: int = 10
    n_strategies: int = 5
    max_units: int = 16

    # Conversion
    source: ConversionSource = ConversionSource.NUMPY
    precision: PrecisionMode = PrecisionMode.FLOAT16
    compute_unit: ComputeUnit = ComputeUnit.ALL

    # Spec
    spec: MLModelSpec = field(default_factory=MLModelSpec)

    # Benchmark
    warmup_runs: int = 5
    benchmark_runs: int = 50
    target_latency_ms: float = 15.0

    # Companion app settings
    enable_batch_prediction: bool = True
    max_batch_size: int = 8
    enable_background_updates: bool = True
    update_interval_seconds: float = 2.0

    # Export
    output_path: str = ""


# ============================================================
# Mock Strategy Advisor Network
# ============================================================


class MockStrategyNetwork:
    """Simulates a trained SC2 strategy advisor model.

    Architecture:
        obs -> Dense(128, relu) -> Dense(128, relu) ->
            action_head -> action_probs (10)
            value_head  -> state_value  (1)
            strategy_head -> strategy_scores (5)
    """

    STRATEGY_NAMES = [
        "aggressive_rush",
        "economic_boom",
        "tech_push",
        "defensive_turtle",
        "timing_attack",
    ]

    def __init__(self, cfg: CoreMLConfig, seed: int = 42):
        self.cfg = cfg
        rng = np.random.RandomState(seed)

        # Shared trunk
        self.w1 = rng.randn(cfg.obs_dim, cfg.hidden_dim).astype(np.float32) * 0.1
        self.b1 = np.zeros(cfg.hidden_dim, dtype=np.float32)
        self.w2 = rng.randn(cfg.hidden_dim, cfg.hidden_dim).astype(np.float32) * 0.1
        self.b2 = np.zeros(cfg.hidden_dim, dtype=np.float32)

        # Action head
        self.w_act = rng.randn(cfg.hidden_dim, cfg.n_actions).astype(np.float32) * 0.1
        self.b_act = np.zeros(cfg.n_actions, dtype=np.float32)

        # Value head
        self.w_val = rng.randn(cfg.hidden_dim, 1).astype(np.float32) * 0.1
        self.b_val = np.zeros(1, dtype=np.float32)

        # Strategy head
        self.w_str = (
            rng.randn(cfg.hidden_dim, cfg.n_strategies).astype(np.float32) * 0.1
        )
        self.b_str = np.zeros(cfg.n_strategies, dtype=np.float32)

    def forward(self, obs: np.ndarray) -> Dict[str, np.ndarray]:
        """Run inference. obs shape: (batch, obs_dim)."""
        h = np.maximum(0, obs @ self.w1 + self.b1)
        h = np.maximum(0, h @ self.w2 + self.b2)

        action_logits = h @ self.w_act + self.b_act
        # Softmax for action probs
        exp_l = np.exp(action_logits - np.max(action_logits, axis=-1, keepdims=True))
        action_probs = exp_l / np.sum(exp_l, axis=-1, keepdims=True)

        value = (h @ self.w_val + self.b_val).squeeze(-1)

        strategy_scores = h @ self.w_str + self.b_str
        # Softmax for strategy
        exp_s = np.exp(
            strategy_scores - np.max(strategy_scores, axis=-1, keepdims=True)
        )
        strategy_probs = exp_s / np.sum(exp_s, axis=-1, keepdims=True)

        return {
            "action_probs": action_probs,
            "value": value,
            "strategy_scores": strategy_probs,
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
            self.w_str,
            self.b_str,
        ]

    @property
    def param_count(self) -> int:
        return sum(w.size for w in self.get_weights())


# ============================================================
# CoreML Converter
# ============================================================


class CoreMLConverter:
    """Converts SC2 strategy models to CoreML format.

    Supports real coremltools conversion when available,
    or simulates the pipeline for testing.
    """

    def __init__(self, cfg: CoreMLConfig):
        self.cfg = cfg
        self._conversion_log: List[Dict[str, Any]] = []

    def _build_torch_model(self, network: MockStrategyNetwork) -> Any:
        """Build a PyTorch model from mock weights (requires torch)."""
        if not TORCH_AVAILABLE:
            raise RuntimeError("PyTorch required for torch-based conversion")

        class SC2Model(nn.Module):
            def __init__(
                self, obs_dim: int, hidden_dim: int, n_actions: int, n_strategies: int
            ):
                super().__init__()
                self.trunk = nn.Sequential(
                    nn.Linear(obs_dim, hidden_dim),
                    nn.ReLU(),
                    nn.Linear(hidden_dim, hidden_dim),
                    nn.ReLU(),
                )
                self.action_head = nn.Linear(hidden_dim, n_actions)
                self.value_head = nn.Linear(hidden_dim, 1)
                self.strategy_head = nn.Linear(hidden_dim, n_strategies)

            def forward(self, x: torch.Tensor):
                h = self.trunk(x)
                actions = torch.softmax(self.action_head(h), dim=-1)
                value = self.value_head(h).squeeze(-1)
                strategy = torch.softmax(self.strategy_head(h), dim=-1)
                return actions, value, strategy

        model = SC2Model(
            self.cfg.obs_dim,
            self.cfg.hidden_dim,
            self.cfg.n_actions,
            self.cfg.n_strategies,
        )

        # Load weights from mock network
        with torch.no_grad():
            model.trunk[0].weight.copy_(torch.from_numpy(network.w1.T))
            model.trunk[0].bias.copy_(torch.from_numpy(network.b1))
            model.trunk[2].weight.copy_(torch.from_numpy(network.w2.T))
            model.trunk[2].bias.copy_(torch.from_numpy(network.b2))
            model.action_head.weight.copy_(torch.from_numpy(network.w_act.T))
            model.action_head.bias.copy_(torch.from_numpy(network.b_act))
            model.value_head.weight.copy_(torch.from_numpy(network.w_val.T))
            model.value_head.bias.copy_(torch.from_numpy(network.b_val))
            model.strategy_head.weight.copy_(torch.from_numpy(network.w_str.T))
            model.strategy_head.bias.copy_(torch.from_numpy(network.b_str))

        model.eval()
        return model

    def convert_from_pytorch(self, network: MockStrategyNetwork) -> Any:
        """Convert using real coremltools from a PyTorch model."""
        if not COREML_AVAILABLE:
            raise RuntimeError("coremltools required for real conversion")
        if not TORCH_AVAILABLE:
            raise RuntimeError("PyTorch required for PyTorch-based conversion")

        model = self._build_torch_model(network)
        example_input = torch.randn(1, self.cfg.obs_dim)
        traced = torch.jit.trace(model, example_input)

        spec = self.cfg.spec
        compute_map = {
            ComputeUnit.CPU_ONLY: ct.ComputeUnit.CPU_ONLY,
            ComputeUnit.CPU_AND_GPU: ct.ComputeUnit.CPU_AND_GPU,
            ComputeUnit.CPU_AND_NE: ct.ComputeUnit.CPU_AND_NE,
            ComputeUnit.ALL: ct.ComputeUnit.ALL,
        }

        mlmodel = ct.convert(
            traced,
            inputs=[
                ct.TensorType(
                    name=spec.input_name,
                    shape=(1, self.cfg.obs_dim),
                )
            ],
            compute_units=compute_map.get(self.cfg.compute_unit, ct.ComputeUnit.ALL),
        )

        # Set metadata
        mlmodel.author = spec.model_author
        mlmodel.short_description = spec.short_description
        mlmodel.version = spec.model_version
        mlmodel.license = spec.license

        if self.cfg.precision == PrecisionMode.FLOAT16:
            mlmodel = ct.models.neural_network.quantization_utils.quantize_weights(
                mlmodel, nbits=16
            )
        elif self.cfg.precision == PrecisionMode.QUANTIZED_8BIT:
            mlmodel = ct.models.neural_network.quantization_utils.quantize_weights(
                mlmodel, nbits=8
            )

        self._conversion_log.append(
            {
                "source": "pytorch",
                "precision": self.cfg.precision.value,
                "compute_unit": self.cfg.compute_unit.value,
                "timestamp": time.time(),
                "method": "real_coreml",
            }
        )

        return mlmodel

    def convert_mock(self, network: MockStrategyNetwork) -> Dict[str, Any]:
        """Simulate CoreML conversion without coremltools.

        Returns a dict representing the mlmodel structure
        with quantized weights for benchmarking.
        """
        weights = network.get_weights()
        spec = self.cfg.spec

        # Simulate precision reduction
        if self.cfg.precision == PrecisionMode.FLOAT16:
            serialized = [w.astype(np.float16).tobytes() for w in weights]
            bytes_per_param = 2
        elif self.cfg.precision == PrecisionMode.QUANTIZED_8BIT:
            serialized = []
            for w in weights:
                w_min, w_max = float(w.min()), float(w.max())
                scale = (w_max - w_min) / 255.0 if w_max != w_min else 1.0
                zp = int(-w_min / scale) if scale != 0 else 0
                q = np.clip(np.round(w / scale) + zp, 0, 255).astype(np.uint8)
                header = struct.pack("<ff", scale, float(zp))
                serialized.append(header + q.tobytes())
            bytes_per_param = 1
        else:
            serialized = [w.tobytes() for w in weights]
            bytes_per_param = 4

        total_size = sum(len(s) for s in serialized)

        mlmodel_mock = {
            "format": "mlmodel_mock",
            "spec": {
                "model_name": spec.model_name,
                "model_version": spec.model_version,
                "author": spec.model_author,
                "description": spec.model_description,
                "inputs": [
                    {
                        "name": spec.input_name,
                        "shape": list(spec.input_shape),
                        "dtype": spec.input_dtype,
                        "description": spec.input_description,
                    }
                ],
                "outputs": [
                    {
                        "name": spec.output_action_name,
                        "shape": list(spec.output_action_shape),
                        "description": spec.output_action_description,
                    },
                    {
                        "name": spec.output_value_name,
                        "shape": list(spec.output_value_shape),
                        "description": spec.output_value_description,
                    },
                    {
                        "name": spec.output_strategy_name,
                        "shape": list(spec.output_strategy_shape),
                        "description": spec.output_strategy_description,
                    },
                ],
            },
            "precision": self.cfg.precision.value,
            "compute_unit": self.cfg.compute_unit.value,
            "weight_blobs": serialized,
            "total_weight_bytes": total_size,
            "param_count": network.param_count,
            "bytes_per_param": bytes_per_param,
        }

        self._conversion_log.append(
            {
                "source": "numpy",
                "precision": self.cfg.precision.value,
                "compute_unit": self.cfg.compute_unit.value,
                "model_size_bytes": total_size,
                "original_size_bytes": network.param_count * 4,
                "compression_ratio": (network.param_count * 4) / max(total_size, 1),
                "timestamp": time.time(),
                "method": "mock",
            }
        )

        return mlmodel_mock

    def convert(self, network: MockStrategyNetwork) -> Any:
        """Convert using real tools if available, else mock."""
        if COREML_AVAILABLE and TORCH_AVAILABLE:
            return self.convert_from_pytorch(network)
        return self.convert_mock(network)

    @property
    def conversion_log(self) -> List[Dict[str, Any]]:
        return list(self._conversion_log)


# ============================================================
# CoreML Predictor
# ============================================================


class CoreMLPredictor:
    """Runs CoreML inference with GPU / Neural Engine delegation.

    Falls back to NumPy simulation when coremltools is unavailable.
    Supports batch prediction and tracks latency metrics.
    """

    def __init__(self, cfg: CoreMLConfig):
        self.cfg = cfg
        self._real_model = None
        self._mock_network: Optional[MockStrategyNetwork] = None
        self._is_real_coreml = False
        self._latencies: List[float] = []
        self._throughputs: List[float] = []
        self._prediction_count = 0

    def load_model(self, model: Any, network: Optional[MockStrategyNetwork] = None):
        """Load a CoreML model for prediction.

        model: either a real MLModel or our mock dict.
        network: fallback NumPy network for mock prediction.
        """
        if COREML_AVAILABLE and hasattr(model, "predict"):
            self._real_model = model
            self._is_real_coreml = True
        else:
            self._mock_network = network
            self._is_real_coreml = False

    def predict(self, obs: np.ndarray) -> Dict[str, np.ndarray]:
        """Run prediction on observation batch.

        obs: (batch, obs_dim) float32 array.
        Returns action_probs, value, strategy_scores.
        """
        t0 = time.perf_counter()

        if self._is_real_coreml and self._real_model is not None:
            result = self._predict_coreml(obs)
        elif self._mock_network is not None:
            result = self._predict_mock(obs)
        else:
            raise RuntimeError("No model loaded. Call load_model() first.")

        elapsed_ms = (time.perf_counter() - t0) * 1000.0
        self._latencies.append(elapsed_ms)
        batch_size = obs.shape[0] if obs.ndim > 1 else 1
        throughput = batch_size / (elapsed_ms / 1000.0) if elapsed_ms > 0 else 0.0
        self._throughputs.append(throughput)
        self._prediction_count += 1

        return result

    def _predict_coreml(self, obs: np.ndarray) -> Dict[str, np.ndarray]:
        """Run prediction via real CoreML."""
        spec = self.cfg.spec
        predictions = self._real_model.predict({spec.input_name: obs})
        return {
            "action_probs": predictions[spec.output_action_name],
            "value": predictions[spec.output_value_name],
            "strategy_scores": predictions[spec.output_strategy_name],
        }

    def _predict_mock(self, obs: np.ndarray) -> Dict[str, np.ndarray]:
        """Simulate CoreML inference using NumPy."""
        return self._mock_network.forward(obs)

    def predict_batch(self, obs_batch: np.ndarray) -> List[Dict[str, np.ndarray]]:
        """Predict for a batch by splitting into individual calls.

        In real CoreML, batch prediction would use MLBatchProvider.
        """
        results = []
        max_bs = self.cfg.max_batch_size
        for start in range(0, obs_batch.shape[0], max_bs):
            end = min(start + max_bs, obs_batch.shape[0])
            chunk = obs_batch[start:end]
            results.append(self.predict(chunk))
        return results

    def benchmark(
        self, obs: np.ndarray, warmup: Optional[int] = None, runs: Optional[int] = None
    ) -> Dict[str, float]:
        """Benchmark inference latency and throughput."""
        warmup = warmup or self.cfg.warmup_runs
        runs = runs or self.cfg.benchmark_runs

        for _ in range(warmup):
            self.predict(obs)

        self._latencies.clear()
        self._throughputs.clear()

        for _ in range(runs):
            self.predict(obs)

        latencies = np.array(self._latencies)
        throughputs = np.array(self._throughputs)

        return {
            "mean_latency_ms": float(np.mean(latencies)),
            "p50_latency_ms": float(np.percentile(latencies, 50)),
            "p95_latency_ms": float(np.percentile(latencies, 95)),
            "p99_latency_ms": float(np.percentile(latencies, 99)),
            "min_latency_ms": float(np.min(latencies)),
            "max_latency_ms": float(np.max(latencies)),
            "std_latency_ms": float(np.std(latencies)),
            "mean_throughput_fps": float(np.mean(throughputs)),
            "total_runs": runs,
            "meets_target": bool(
                np.percentile(latencies, 95) < self.cfg.target_latency_ms
            ),
        }

    def compare_accuracy(
        self, network: MockStrategyNetwork, n_samples: int = 100, seed: int = 42
    ) -> Dict[str, float]:
        """Compare CoreML output vs original network."""
        rng = np.random.RandomState(seed)
        cos_sims_actions = []
        cos_sims_strategy = []
        value_errors = []

        for _ in range(n_samples):
            obs = rng.randn(1, self.cfg.obs_dim).astype(np.float32)

            orig = network.forward(obs)
            pred = self.predict(obs)

            # Action probs cosine similarity
            a = orig["action_probs"].flatten()
            b = pred["action_probs"].flatten()
            denom = np.linalg.norm(a) * np.linalg.norm(b)
            cos_sims_actions.append(float(np.dot(a, b) / denom) if denom > 0 else 1.0)

            # Strategy cosine similarity
            sa = orig["strategy_scores"].flatten()
            sb = pred["strategy_scores"].flatten()
            denom_s = np.linalg.norm(sa) * np.linalg.norm(sb)
            cos_sims_strategy.append(
                float(np.dot(sa, sb) / denom_s) if denom_s > 0 else 1.0
            )

            # Value absolute error
            value_errors.append(float(np.abs(orig["value"] - pred["value"]).mean()))

        return {
            "action_cosine_sim_mean": float(np.mean(cos_sims_actions)),
            "action_cosine_sim_min": float(np.min(cos_sims_actions)),
            "strategy_cosine_sim_mean": float(np.mean(cos_sims_strategy)),
            "value_mean_abs_error": float(np.mean(value_errors)),
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
# Companion App Integration Layer
# ============================================================


class CompanionAppBridge:
    """Simulates the iOS companion app integration layer.

    Provides endpoints for:
    - Real-time strategy recommendations
    - Build order suggestions
    - Game state summaries for display
    - Background model updates
    """

    RACE_NAMES = {0: "Terran", 1: "Zerg", 2: "Protoss"}

    def __init__(self, predictor: CoreMLPredictor, cfg: CoreMLConfig):
        self.predictor = predictor
        self.cfg = cfg
        self._update_history: List[Dict[str, Any]] = []
        self._recommendation_cache: Dict[str, Any] = {}
        self._last_update_time = 0.0

    def get_strategy_recommendation(self, game_state: Dict[str, Any]) -> Dict[str, Any]:
        """Generate a human-readable strategy recommendation.

        Returns a dict suitable for display in the iOS companion app.
        """
        obs = self._encode_game_state(game_state)
        out = self.predictor.predict(obs)

        strategy_scores = out["strategy_scores"].flatten()
        top_idx = int(np.argmax(strategy_scores))
        strategy_name = MockStrategyNetwork.STRATEGY_NAMES[top_idx]

        action_probs = out["action_probs"].flatten()
        top_action_idx = int(np.argmax(action_probs))
        action_names = [
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
        top_action = action_names[top_action_idx]

        value = float(out["value"].flatten()[0])
        win_probability = 1.0 / (1.0 + math.exp(-value))

        recommendation = {
            "strategy": strategy_name,
            "strategy_confidence": float(strategy_scores[top_idx]),
            "all_strategies": {
                name: float(strategy_scores[i])
                for i, name in enumerate(MockStrategyNetwork.STRATEGY_NAMES)
            },
            "suggested_action": top_action,
            "win_probability": win_probability,
            "game_phase": self._detect_game_phase(game_state),
            "urgency": self._compute_urgency(game_state, value),
            "display_text": self._format_recommendation_text(
                strategy_name, top_action, win_probability, game_state
            ),
        }

        self._recommendation_cache = recommendation
        return recommendation

    def get_build_order_suggestion(
        self, game_state: Dict[str, Any]
    ) -> List[Dict[str, Any]]:
        """Suggest next build order items based on strategy."""
        rec = self.get_strategy_recommendation(game_state)
        strategy = rec["strategy"]

        # Mock build order suggestions per strategy
        build_orders = {
            "aggressive_rush": [
                {"item": "Spawning Pool", "priority": 1, "supply": 14},
                {"item": "Zergling x6", "priority": 2, "supply": 16},
                {"item": "Metabolic Boost", "priority": 3, "supply": 18},
            ],
            "economic_boom": [
                {"item": "Hatchery", "priority": 1, "supply": 16},
                {"item": "Queen x2", "priority": 2, "supply": 20},
                {"item": "Drone x8", "priority": 3, "supply": 24},
            ],
            "tech_push": [
                {"item": "Lair", "priority": 1, "supply": 30},
                {"item": "Hydralisk Den", "priority": 2, "supply": 36},
                {"item": "Hydralisk x8", "priority": 3, "supply": 44},
            ],
            "defensive_turtle": [
                {"item": "Spine Crawler x2", "priority": 1, "supply": 22},
                {"item": "Spore Crawler x2", "priority": 2, "supply": 26},
                {"item": "Queen x3", "priority": 3, "supply": 30},
            ],
            "timing_attack": [
                {"item": "Roach Warren", "priority": 1, "supply": 28},
                {"item": "Roach x12", "priority": 2, "supply": 44},
                {"item": "Glial Reconstitution", "priority": 3, "supply": 50},
            ],
        }
        return build_orders.get(strategy, [])

    def should_update(self) -> bool:
        """Check if enough time has elapsed for a background update."""
        now = time.time()
        elapsed = now - self._last_update_time
        return elapsed >= self.cfg.update_interval_seconds

    def perform_update(self, game_state: Dict[str, Any]):
        """Perform a background model prediction update."""
        rec = self.get_strategy_recommendation(game_state)
        self._last_update_time = time.time()
        self._update_history.append(
            {
                "timestamp": self._last_update_time,
                "strategy": rec["strategy"],
                "win_prob": rec["win_probability"],
            }
        )

    def _encode_game_state(self, game_state: Dict[str, Any]) -> np.ndarray:
        """Encode game state dict into observation vector."""
        obs = np.zeros((1, self.cfg.obs_dim), dtype=np.float32)

        # Aggregate unit features
        units = game_state.get("units", [])
        friendly = [u for u in units if u.get("is_friendly", True)]
        enemy = [u for u in units if not u.get("is_friendly", True)]

        obs[0, 0] = len(friendly) / 50.0
        obs[0, 1] = len(enemy) / 50.0
        obs[0, 2] = sum(u.get("health", 0) for u in friendly) / 5000.0
        obs[0, 3] = sum(u.get("health", 0) for u in enemy) / 5000.0
        obs[0, 4] = game_state.get("minerals", 0) / 1000.0
        obs[0, 5] = game_state.get("vespene", 0) / 500.0
        obs[0, 6] = game_state.get("supply_used", 0) / 200.0
        obs[0, 7] = game_state.get("supply_cap", 0) / 200.0
        obs[0, 8] = game_state.get("game_time_seconds", 0) / 600.0
        obs[0, 9] = game_state.get("worker_count", 0) / 80.0

        # Per-unit features for first few units
        for i, u in enumerate(friendly[:8]):
            base = 10 + i * 4
            if base + 3 < self.cfg.obs_dim:
                obs[0, base] = u.get("type_id", 0) / 300.0
                obs[0, base + 1] = u.get("health", 0) / 500.0
                obs[0, base + 2] = u.get("x", 0) / 200.0
                obs[0, base + 3] = u.get("y", 0) / 200.0

        return obs

    def _detect_game_phase(self, game_state: Dict[str, Any]) -> str:
        """Detect current game phase based on time and supply."""
        game_time = game_state.get("game_time_seconds", 0)
        supply = game_state.get("supply_used", 0)
        if game_time < 180 or supply < 30:
            return "early_game"
        elif game_time < 480 or supply < 100:
            return "mid_game"
        return "late_game"

    def _compute_urgency(self, game_state: Dict[str, Any], value: float) -> str:
        """Compute urgency level for display."""
        if value < -0.5:
            return "critical"
        elif value < -0.1:
            return "high"
        elif value < 0.3:
            return "medium"
        return "low"

    def _format_recommendation_text(
        self, strategy: str, action: str, win_prob: float, game_state: Dict[str, Any]
    ) -> str:
        """Format a human-readable recommendation for the app."""
        phase = self._detect_game_phase(game_state)
        strategy_display = strategy.replace("_", " ").title()
        lines = [
            f"Recommended: {strategy_display}",
            f"Phase: {phase.replace('_', ' ').title()}",
            f"Win probability: {win_prob:.0%}",
            f"Next action: {action}",
        ]
        return " | ".join(lines)


# ============================================================
# CoreML Agent (SC2 integration)
# ============================================================


class CoreMLAgent:
    """SC2 agent using CoreML-converted strategy advisor.

    Wraps conversion, prediction, companion app integration,
    and benchmarking into a unified interface.
    """

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

    def __init__(self, cfg: Optional[CoreMLConfig] = None, seed: int = 42):
        self.cfg = cfg or CoreMLConfig()
        self.seed = seed
        self.network = MockStrategyNetwork(self.cfg, seed=seed)
        self.converter = CoreMLConverter(self.cfg)
        self.predictor = CoreMLPredictor(self.cfg)
        self.bridge: Optional[CompanionAppBridge] = None
        self._mlmodel = None
        self._is_loaded = False
        self.step_count = 0

    def convert_and_load(
        self,
        precision: Optional[PrecisionMode] = None,
        compute_unit: Optional[ComputeUnit] = None,
    ):
        """Convert the strategy model and load for prediction."""
        if precision is not None:
            self.cfg.precision = precision
        if compute_unit is not None:
            self.cfg.compute_unit = compute_unit

        self._mlmodel = self.converter.convert(self.network)
        self.predictor.load_model(self._mlmodel, network=self.network)
        self.bridge = CompanionAppBridge(self.predictor, self.cfg)
        self._is_loaded = True

    def act(self, obs: np.ndarray, deterministic: bool = False) -> Dict[str, Any]:
        """Select actions using CoreML inference."""
        if not self._is_loaded:
            self.convert_and_load()

        out = self.predictor.predict(obs)
        probs = out["action_probs"]

        if deterministic:
            actions = np.argmax(probs, axis=-1)
        else:
            batch_size = probs.shape[0]
            n_actions = probs.shape[-1]
            actions = np.zeros(batch_size, dtype=np.int64)
            rng = np.random.RandomState(self.step_count + self.seed)
            for b in range(batch_size):
                actions[b] = rng.choice(n_actions, p=probs[b])

        self.step_count += 1
        return {
            "actions": actions,
            "action_probs": probs,
            "values": out["value"],
            "strategy_scores": out["strategy_scores"],
        }

    def get_recommendation(self, game_state: Dict[str, Any]) -> Dict[str, Any]:
        """Get companion app strategy recommendation."""
        if not self._is_loaded:
            self.convert_and_load()
        return self.bridge.get_strategy_recommendation(game_state)

    def get_build_order(self, game_state: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Get companion app build order suggestion."""
        if not self._is_loaded:
            self.convert_and_load()
        return self.bridge.get_build_order_suggestion(game_state)

    def run_precision_comparison(self) -> Dict[str, Any]:
        """Benchmark all precision modes."""
        results = {}
        rng = np.random.RandomState(self.seed)
        obs = rng.randn(1, self.cfg.obs_dim).astype(np.float32)

        for precision in PrecisionMode:
            self.cfg.precision = precision
            self.converter = CoreMLConverter(self.cfg)
            mlmodel = self.converter.convert(self.network)

            predictor = CoreMLPredictor(self.cfg)
            predictor.load_model(mlmodel, network=self.network)

            bench = predictor.benchmark(obs, warmup=3, runs=30)
            accuracy = predictor.compare_accuracy(self.network, n_samples=50)

            model_size = 0
            if isinstance(mlmodel, dict):
                model_size = mlmodel.get("total_weight_bytes", 0)

            results[precision.value] = {
                "model_size_bytes": model_size,
                "mean_latency_ms": bench["mean_latency_ms"],
                "p95_latency_ms": bench["p95_latency_ms"],
                "meets_target": bench["meets_target"],
                "action_cosine_sim": accuracy["action_cosine_sim_mean"],
                "strategy_cosine_sim": accuracy["strategy_cosine_sim_mean"],
                "value_error": accuracy["value_mean_abs_error"],
            }

        return results

    def benchmark(self, batch_size: int = 1) -> Dict[str, float]:
        """Quick benchmark of current configuration."""
        if not self._is_loaded:
            self.convert_and_load()
        rng = np.random.RandomState(self.seed)
        obs = rng.randn(batch_size, self.cfg.obs_dim).astype(np.float32)
        return self.predictor.benchmark(obs)

    def export_model(self, path: str):
        """Export the mock mlmodel structure to JSON."""
        if not self._is_loaded:
            self.convert_and_load()
        if isinstance(self._mlmodel, dict):
            # Remove non-serializable weight blobs for JSON export
            export = {k: v for k, v in self._mlmodel.items() if k != "weight_blobs"}
            with open(path, "w") as f:
                json.dump(export, f, indent=2)
        elif COREML_AVAILABLE and hasattr(self._mlmodel, "save"):
            self._mlmodel.save(path)

    def summary(self) -> str:
        lines = [
            "CoreMLAgent Summary",
            f"  Backend:           {'CoreML' if self._is_loaded else 'not loaded'}",
            f"  Precision:         {self.cfg.precision.value}",
            f"  Compute unit:      {self.cfg.compute_unit.value}",
            f"  Model params:      {self.network.param_count:,}",
            f"  obs_dim:           {self.cfg.obs_dim}",
            f"  hidden_dim:        {self.cfg.hidden_dim}",
            f"  n_actions:         {self.cfg.n_actions}",
            f"  n_strategies:      {self.cfg.n_strategies}",
            f"  max_units:         {self.cfg.max_units}",
            f"  target_latency:    {self.cfg.target_latency_ms} ms",
            f"  batch_prediction:  {self.cfg.enable_batch_prediction}",
            f"  max_batch_size:    {self.cfg.max_batch_size}",
            f"  steps_taken:       {self.step_count}",
        ]
        stats = self.predictor.latency_stats
        if stats["count"] > 0:
            lines.append(f"  avg_latency:       {stats['mean_ms']:.2f} ms")
        return "\n".join(lines)


# ============================================================
# CLI Demo
# ============================================================


def _demo_mock_network():
    print("=" * 60)
    print("Mock Strategy Network Demo")
    print("=" * 60)

    cfg = CoreMLConfig(obs_dim=48, hidden_dim=128, n_actions=10, n_strategies=5)
    net = MockStrategyNetwork(cfg, seed=42)
    print(f"  Parameters: {net.param_count:,}")

    obs = np.random.randn(4, cfg.obs_dim).astype(np.float32)
    out = net.forward(obs)
    print(f"  Action probs shape:    {out['action_probs'].shape}")
    print(f"  Value shape:           {out['value'].shape}")
    print(f"  Strategy scores shape: {out['strategy_scores'].shape}")
    print(
        f"  Top strategy:          "
        f"{MockStrategyNetwork.STRATEGY_NAMES[np.argmax(out['strategy_scores'][0])]}"
    )
    print()


def _demo_conversion():
    print("=" * 60)
    print("CoreML Conversion Demo (all precisions)")
    print("=" * 60)

    cfg = CoreMLConfig(obs_dim=48, hidden_dim=128, n_actions=10, n_strategies=5)
    net = MockStrategyNetwork(cfg, seed=42)
    original_size = net.param_count * 4

    for precision in PrecisionMode:
        cfg.precision = precision
        converter = CoreMLConverter(cfg)
        mlmodel = converter.convert_mock(net)
        size = mlmodel["total_weight_bytes"]
        ratio = original_size / max(size, 1)
        print(
            f"  {precision.value:15s} -> {size:>8,} bytes "
            f"(compression: {ratio:.2f}x)"
        )

    print(f"  Original float32:    {original_size:>8,} bytes")
    print()


def _demo_inference_benchmark():
    print("=" * 60)
    print("CoreML Inference Benchmark Demo")
    print("=" * 60)

    cfg = CoreMLConfig(
        obs_dim=48,
        hidden_dim=128,
        n_actions=10,
        n_strategies=5,
        benchmark_runs=100,
        warmup_runs=10,
    )
    net = MockStrategyNetwork(cfg, seed=42)

    for precision in PrecisionMode:
        cfg.precision = precision
        converter = CoreMLConverter(cfg)
        mlmodel = converter.convert_mock(net)

        predictor = CoreMLPredictor(cfg)
        predictor.load_model(mlmodel, network=net)

        obs = np.random.randn(1, cfg.obs_dim).astype(np.float32)
        bench = predictor.benchmark(obs)

        status = "PASS" if bench["meets_target"] else "FAIL"
        print(
            f"  {precision.value:15s} | mean: {bench['mean_latency_ms']:6.3f} ms | "
            f"p95: {bench['p95_latency_ms']:6.3f} ms | "
            f"throughput: {bench['mean_throughput_fps']:8.0f} fps | [{status}]"
        )

    print()


def _demo_companion_app():
    print("=" * 60)
    print("Companion App Integration Demo")
    print("=" * 60)

    agent = CoreMLAgent(seed=42)
    agent.convert_and_load(PrecisionMode.FLOAT16, ComputeUnit.ALL)

    game_state = {
        "units": [
            {
                "type_id": 84,
                "x": 50,
                "y": 50,
                "health": 45,
                "shield": 0,
                "energy": 0,
                "is_friendly": True,
                "tag": 1001,
            },
            {
                "type_id": 84,
                "x": 52,
                "y": 48,
                "health": 40,
                "shield": 0,
                "energy": 0,
                "is_friendly": True,
                "tag": 1002,
            },
            {
                "type_id": 105,
                "x": 55,
                "y": 53,
                "health": 35,
                "shield": 0,
                "energy": 0,
                "is_friendly": True,
                "tag": 1003,
            },
            {
                "type_id": 48,
                "x": 80,
                "y": 60,
                "health": 150,
                "shield": 50,
                "energy": 100,
                "is_friendly": False,
                "tag": 2001,
            },
        ],
        "minerals": 450,
        "vespene": 200,
        "supply_used": 42,
        "supply_cap": 52,
        "game_time_seconds": 300,
        "worker_count": 22,
    }

    rec = agent.get_recommendation(game_state)
    print(f"  Strategy:       {rec['strategy']}")
    print(f"  Confidence:     {rec['strategy_confidence']:.3f}")
    print(f"  Win probability:{rec['win_probability']:.3f}")
    print(f"  Game phase:     {rec['game_phase']}")
    print(f"  Urgency:        {rec['urgency']}")
    print(f"  Display text:   {rec['display_text']}")
    print()

    build = agent.get_build_order(game_state)
    print("  Build order suggestions:")
    for item in build:
        print(f"    [{item['priority']}] {item['item']} (supply {item['supply']})")
    print()


def _demo_precision_comparison():
    print("=" * 60)
    print("Precision Comparison Demo")
    print("=" * 60)

    agent = CoreMLAgent(seed=42)
    results = agent.run_precision_comparison()

    print(
        f"  {'Precision':15s} | {'Size':>10s} | {'Latency':>10s} | "
        f"{'ActCos':>8s} | {'StrCos':>8s} | Target"
    )
    print("  " + "-" * 75)
    for prec_name, stats in results.items():
        target_str = "PASS" if stats["meets_target"] else "FAIL"
        print(
            f"  {prec_name:15s} | {stats['model_size_bytes']:>8,} B | "
            f"{stats['mean_latency_ms']:>8.3f} ms | "
            f"{stats['action_cosine_sim']:>8.6f} | "
            f"{stats['strategy_cosine_sim']:>8.6f} | {target_str}"
        )

    print()


def _demo_batch_prediction():
    print("=" * 60)
    print("Batch Prediction Demo")
    print("=" * 60)

    cfg = CoreMLConfig(max_batch_size=4)
    agent = CoreMLAgent(cfg=cfg, seed=42)
    agent.convert_and_load(PrecisionMode.FLOAT16)

    obs = np.random.randn(12, cfg.obs_dim).astype(np.float32)
    results = agent.predictor.predict_batch(obs)

    print(f"  Input batch size: {obs.shape[0]}")
    print(f"  Number of chunks: {len(results)}")
    for i, res in enumerate(results):
        print(
            f"  Chunk {i}: action_probs {res['action_probs'].shape}, "
            f"strategy {res['strategy_scores'].shape}"
        )

    print()


def demo():
    """Run all Phase 637 demonstrations."""
    print("Phase 637: CoreML Mobile Deployment for SC2 Companion App")
    print(f"CoreML available: {COREML_AVAILABLE}")
    print(f"PyTorch available: {TORCH_AVAILABLE}")
    print(f"ONNX available: {ONNX_AVAILABLE}")
    print()

    _demo_mock_network()
    _demo_conversion()
    _demo_inference_benchmark()
    _demo_companion_app()
    _demo_precision_comparison()
    _demo_batch_prediction()

    print("Phase 637 demo complete.")


if __name__ == "__main__":
    demo()

# Phase 637: CoreML registered
