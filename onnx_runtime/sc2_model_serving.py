# onnx_runtime/sc2_model_serving.py
# Phase 598: ONNX Runtime — Cross-platform SC2 model serving
#
# Exports PyTorch policy and value networks to ONNX format, applies graph
# optimizations and INT8 quantization, then serves inference through
# onnxruntime with CPU / CUDA / TensorRT execution providers.

from __future__ import annotations

import io
import json
import logging
import os
import statistics
import tempfile
import time
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Any, Dict, List, Optional, Sequence, Tuple, Union

import numpy as np

try:
    import torch
    import torch.nn as nn
except ImportError:
    torch = None  # type: ignore[assignment]
    nn = None  # type: ignore[assignment]

try:
    import onnx
    from onnx import TensorProto, helper, numpy_helper
except ImportError:
    onnx = None  # type: ignore[assignment]

try:
    import onnxruntime as ort
except ImportError:
    ort = None  # type: ignore[assignment]

try:
    from onnxruntime.quantization import (
        CalibrationDataReader,
        QuantFormat,
        QuantType,
        quantize_dynamic,
        quantize_static,
    )
except ImportError:
    CalibrationDataReader = None  # type: ignore[assignment,misc]

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

SC2_STATE_DIM = 267          # flattened game-state vector size
SC2_SPATIAL_H = 64           # spatial feature map height
SC2_SPATIAL_W = 64           # spatial feature map width
SC2_SPATIAL_CHANNELS = 17    # spatial feature channels
SC2_NUM_ACTIONS = 573        # total SC2 action space
DEFAULT_WARMUP_RUNS = 10
DEFAULT_BENCHMARK_RUNS = 100

# ---------------------------------------------------------------------------
# Enums & data classes
# ---------------------------------------------------------------------------

class ExecutionProviderKind(Enum):
    CPU = "CPUExecutionProvider"
    CUDA = "CUDAExecutionProvider"
    TENSORRT = "TensorrtExecutionProvider"


@dataclass
class ModelMetadata:
    name: str
    version: str
    description: str
    author: str = "SC2 Zerg Bot"
    domain: str = "sc2.ai"
    extra: Dict[str, str] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, str]:
        base = {
            "name": self.name,
            "version": self.version,
            "description": self.description,
            "author": self.author,
            "domain": self.domain,
        }
        base.update(self.extra)
        return base


@dataclass
class BenchmarkResult:
    model_name: str
    provider: str
    batch_size: int
    num_runs: int
    latency_mean_ms: float
    latency_p50_ms: float
    latency_p95_ms: float
    latency_p99_ms: float
    throughput_samples_per_sec: float
    memory_peak_mb: Optional[float] = None

    def summary(self) -> str:
        return (
            f"[{self.model_name}] provider={self.provider} bs={self.batch_size} | "
            f"mean={self.latency_mean_ms:.2f}ms  p50={self.latency_p50_ms:.2f}ms  "
            f"p95={self.latency_p95_ms:.2f}ms  p99={self.latency_p99_ms:.2f}ms | "
            f"throughput={self.throughput_samples_per_sec:.1f} samples/s"
        )


@dataclass
class ValidationResult:
    model_name: str
    max_abs_diff: float
    mean_abs_diff: float
    cosine_sim: float
    passed: bool
    tolerance: float

    def summary(self) -> str:
        status = "PASS" if self.passed else "FAIL"
        return (
            f"[{self.model_name}] {status} | max_diff={self.max_abs_diff:.6f} "
            f"mean_diff={self.mean_abs_diff:.6f} cosine={self.cosine_sim:.6f} "
            f"tol={self.tolerance}"
        )


# ---------------------------------------------------------------------------
# Sample PyTorch networks (for export demonstration)
# ---------------------------------------------------------------------------

if nn is not None:

    class SC2PolicyNet(nn.Module):
        """Lightweight policy network mapping game state to action logits."""

        def __init__(
            self,
            state_dim: int = SC2_STATE_DIM,
            hidden: int = 256,
            num_actions: int = SC2_NUM_ACTIONS,
        ):
            super().__init__()
            self.net = nn.Sequential(
                nn.Linear(state_dim, hidden),
                nn.ReLU(),
                nn.Linear(hidden, hidden),
                nn.ReLU(),
                nn.Linear(hidden, num_actions),
            )

        def forward(self, x: torch.Tensor) -> torch.Tensor:
            return self.net(x)

    class SC2ValueNet(nn.Module):
        """Value network estimating win probability from game state."""

        def __init__(self, state_dim: int = SC2_STATE_DIM, hidden: int = 256):
            super().__init__()
            self.net = nn.Sequential(
                nn.Linear(state_dim, hidden),
                nn.ReLU(),
                nn.Linear(hidden, hidden),
                nn.ReLU(),
                nn.Linear(hidden, 1),
                nn.Tanh(),
            )

        def forward(self, x: torch.Tensor) -> torch.Tensor:
            return self.net(x)

    class SC2SpatialPolicyNet(nn.Module):
        """Policy network with spatial CNN head for map-level decisions."""

        def __init__(
            self,
            spatial_channels: int = SC2_SPATIAL_CHANNELS,
            state_dim: int = SC2_STATE_DIM,
            num_actions: int = SC2_NUM_ACTIONS,
        ):
            super().__init__()
            self.spatial_encoder = nn.Sequential(
                nn.Conv2d(spatial_channels, 32, 5, padding=2),
                nn.ReLU(),
                nn.Conv2d(32, 32, 3, padding=1),
                nn.ReLU(),
                nn.AdaptiveAvgPool2d(1),
            )
            self.scalar_encoder = nn.Sequential(
                nn.Linear(state_dim, 128),
                nn.ReLU(),
            )
            self.head = nn.Sequential(
                nn.Linear(32 + 128, 256),
                nn.ReLU(),
                nn.Linear(256, num_actions),
            )

        def forward(
            self, spatial: torch.Tensor, scalar: torch.Tensor
        ) -> torch.Tensor:
            s = self.spatial_encoder(spatial).squeeze(-1).squeeze(-1)
            v = self.scalar_encoder(scalar)
            combined = torch.cat([s, v], dim=-1)
            return self.head(combined)


# ---------------------------------------------------------------------------
# Calibration data reader (for static INT8 quantization)
# ---------------------------------------------------------------------------

class SC2CalibrationReader:
    """Generates calibration data for ONNX static quantization."""

    def __init__(
        self,
        input_names: List[str],
        input_shapes: Dict[str, Tuple[int, ...]],
        num_batches: int = 50,
    ):
        self.input_names = input_names
        self.input_shapes = input_shapes
        self.num_batches = num_batches
        self._batch_idx = 0

    def get_next(self) -> Optional[Dict[str, np.ndarray]]:
        if self._batch_idx >= self.num_batches:
            return None
        self._batch_idx += 1
        return {
            name: np.random.randn(*self.input_shapes[name]).astype(np.float32)
            for name in self.input_names
        }

    def rewind(self) -> None:
        self._batch_idx = 0


# ---------------------------------------------------------------------------
# SC2ModelServer
# ---------------------------------------------------------------------------

class SC2ModelServer:
    """Cross-platform ONNX Runtime model server for SC2 inference.

    Capabilities
    -------------
    * Export PyTorch models to ONNX with dynamic batch axes.
    * Optimise ONNX graphs (constant folding, fusion, layout transforms).
    * Dynamic / static INT8 quantization for edge or tournament setups.
    * Serve inference through CPU, CUDA, or TensorRT providers.
    * Multi-model hosting (policy + value networks side-by-side).
    * Built-in benchmarking and cross-framework validation.
    """

    def __init__(self, model_dir: Union[str, Path] = "./onnx_models"):
        self.model_dir = Path(model_dir)
        self.model_dir.mkdir(parents=True, exist_ok=True)

        # name -> InferenceSession
        self._sessions: Dict[str, ort.InferenceSession] = {}  # type: ignore[name-defined]
        # name -> metadata
        self._metadata: Dict[str, ModelMetadata] = {}
        # name -> path
        self._model_paths: Dict[str, Path] = {}

        logger.info("SC2ModelServer initialised (model_dir=%s)", self.model_dir)

    # ------------------------------------------------------------------
    # PyTorch -> ONNX export
    # ------------------------------------------------------------------

    def export_pytorch(
        self,
        model: Any,
        model_name: str,
        sample_inputs: Union[Any, Tuple[Any, ...]],
        input_names: Optional[List[str]] = None,
        output_names: Optional[List[str]] = None,
        dynamic_axes: Optional[Dict[str, Dict[int, str]]] = None,
        opset_version: int = 17,
        metadata: Optional[ModelMetadata] = None,
    ) -> Path:
        """Export a PyTorch ``nn.Module`` to ONNX format.

        Parameters
        ----------
        model : nn.Module
            Trained PyTorch model.
        model_name : str
            Identifier used for file naming and session lookup.
        sample_inputs : Tensor | tuple[Tensor, ...]
            Representative inputs for tracing.
        dynamic_axes : dict, optional
            Map of tensor-name -> {axis_idx: axis_label} enabling dynamic
            shapes (typically ``{0: "batch"}``).
        opset_version : int
            ONNX opset (default 17).
        metadata : ModelMetadata, optional
            Descriptive metadata embedded into the ONNX model.

        Returns
        -------
        Path
            Location of the exported ``.onnx`` file.
        """
        if torch is None:
            raise RuntimeError("PyTorch is required for model export")

        model.eval()
        out_path = self.model_dir / f"{model_name}.onnx"

        # Determine input / output names
        if input_names is None:
            if isinstance(sample_inputs, (tuple, list)):
                input_names = [f"input_{i}" for i in range(len(sample_inputs))]
            else:
                input_names = ["input"]
        if output_names is None:
            output_names = ["output"]

        # Default dynamic axes: batch dimension on every input / output
        if dynamic_axes is None:
            dynamic_axes = {}
            for n in input_names:
                dynamic_axes[n] = {0: "batch"}
            for n in output_names:
                dynamic_axes[n] = {0: "batch"}

        logger.info("Exporting %s to ONNX (opset %d) ...", model_name, opset_version)

        with torch.no_grad():
            torch.onnx.export(
                model,
                sample_inputs if isinstance(sample_inputs, tuple) else (sample_inputs,),
                str(out_path),
                input_names=input_names,
                output_names=output_names,
                dynamic_axes=dynamic_axes,
                opset_version=opset_version,
                do_constant_folding=True,
            )

        # Embed metadata
        if metadata is None:
            metadata = ModelMetadata(
                name=model_name,
                version="1.0.0",
                description=f"SC2 {model_name} network",
            )
        self._embed_metadata(out_path, metadata)
        self._metadata[model_name] = metadata
        self._model_paths[model_name] = out_path

        size_mb = out_path.stat().st_size / (1024 * 1024)
        logger.info("Export complete: %s (%.2f MB)", out_path, size_mb)
        return out_path

    # ------------------------------------------------------------------
    # ONNX model optimisation
    # ------------------------------------------------------------------

    def optimise(
        self,
        model_name: str,
        opt_level: int = 99,
        enable_transformers_opts: bool = False,
    ) -> Path:
        """Apply ONNX Runtime graph optimisations.

        Parameters
        ----------
        model_name : str
            Previously exported model identifier.
        opt_level : int
            Optimisation level (1 = basic, 2 = extended, 99 = all).
        enable_transformers_opts : bool
            When ``True``, enable transformer-specific fusions.

        Returns
        -------
        Path
            Path to the optimised ONNX model.
        """
        src_path = self._resolve_path(model_name)
        opt_path = self.model_dir / f"{model_name}_opt.onnx"

        so = ort.SessionOptions()
        level_map = {
            0: ort.GraphOptimizationLevel.ORT_DISABLE_ALL,
            1: ort.GraphOptimizationLevel.ORT_ENABLE_BASIC,
            2: ort.GraphOptimizationLevel.ORT_ENABLE_EXTENDED,
            99: ort.GraphOptimizationLevel.ORT_ENABLE_ALL,
        }
        so.graph_optimization_level = level_map.get(
            opt_level, ort.GraphOptimizationLevel.ORT_ENABLE_ALL
        )
        so.optimized_model_filepath = str(opt_path)

        if enable_transformers_opts:
            so.add_session_config_entry(
                "session.transformers_optimization", "true"
            )

        # Creating a session with optimized_model_filepath writes the optimised
        # graph to disk then we discard this temporary session.
        _ = ort.InferenceSession(str(src_path), sess_options=so)

        self._model_paths[model_name] = opt_path
        size_mb = opt_path.stat().st_size / (1024 * 1024)
        logger.info("Optimised model saved: %s (%.2f MB)", opt_path, size_mb)
        return opt_path

    # ------------------------------------------------------------------
    # Quantization
    # ------------------------------------------------------------------

    def quantize_dynamic_int8(self, model_name: str) -> Path:
        """Apply dynamic INT8 quantization (weights only).

        Ideal for CPU-bound edge deployment where calibration data is not
        available.
        """
        src_path = self._resolve_path(model_name)
        q_path = self.model_dir / f"{model_name}_int8_dyn.onnx"

        quantize_dynamic(
            model_input=str(src_path),
            model_output=str(q_path),
            weight_type=QuantType.QInt8,
        )

        self._model_paths[f"{model_name}_int8_dyn"] = q_path
        size_mb = q_path.stat().st_size / (1024 * 1024)
        logger.info("Dynamic INT8 model: %s (%.2f MB)", q_path, size_mb)
        return q_path

    def quantize_static_int8(
        self,
        model_name: str,
        calibration_reader: Any,
        quant_format: Optional[Any] = None,
    ) -> Path:
        """Apply static INT8 quantization using calibration data.

        Parameters
        ----------
        calibration_reader : CalibrationDataReader
            Provides representative data batches for range calibration.
        quant_format : QuantFormat, optional
            ``QuantFormat.QDQ`` (default) or ``QuantFormat.QOperator``.
        """
        src_path = self._resolve_path(model_name)
        q_path = self.model_dir / f"{model_name}_int8_static.onnx"
        if quant_format is None:
            quant_format = QuantFormat.QDQ

        quantize_static(
            model_input=str(src_path),
            model_output=str(q_path),
            calibration_data_reader=calibration_reader,
            quant_format=quant_format,
            weight_type=QuantType.QInt8,
            activation_type=QuantType.QUInt8,
        )

        self._model_paths[f"{model_name}_int8_static"] = q_path
        size_mb = q_path.stat().st_size / (1024 * 1024)
        logger.info("Static INT8 model: %s (%.2f MB)", q_path, size_mb)
        return q_path

    # ------------------------------------------------------------------
    # Session management
    # ------------------------------------------------------------------

    def load_session(
        self,
        model_name: str,
        providers: Optional[List[ExecutionProviderKind]] = None,
        inter_op_threads: int = 1,
        intra_op_threads: int = 0,
        enable_mem_pattern: bool = True,
        enable_profiling: bool = False,
        warmup_runs: int = DEFAULT_WARMUP_RUNS,
    ) -> None:
        """Create an ``InferenceSession`` for the named model.

        Parameters
        ----------
        providers : list[ExecutionProviderKind], optional
            Ordered list of execution providers.  Falls back to CPU.
        inter_op_threads / intra_op_threads : int
            ORT thread-pool sizes (0 = auto-detect).
        warmup_runs : int
            Number of warm-up inference calls to stabilise JIT caches.
        """
        model_path = self._resolve_path(model_name)

        so = ort.SessionOptions()
        so.inter_op_num_threads = inter_op_threads
        so.intra_op_num_threads = intra_op_threads
        so.enable_mem_pattern = enable_mem_pattern
        so.enable_cpu_mem_arena = True
        so.execution_mode = ort.ExecutionMode.ORT_SEQUENTIAL
        if enable_profiling:
            so.enable_profiling = True

        ep_list = (
            [p.value for p in providers]
            if providers
            else [ExecutionProviderKind.CPU.value]
        )

        session = ort.InferenceSession(str(model_path), sess_options=so, providers=ep_list)
        self._sessions[model_name] = session

        active_eps = session.get_providers()
        logger.info(
            "Session loaded: %s | providers=%s", model_name, active_eps
        )

        # Warm-up
        if warmup_runs > 0:
            self._warmup(model_name, warmup_runs)

    def _warmup(self, model_name: str, runs: int) -> None:
        """Run dummy inferences to warm up the session."""
        session = self._sessions[model_name]
        dummy_inputs = self._make_dummy_inputs(session, batch_size=1)
        for _ in range(runs):
            session.run(None, dummy_inputs)
        logger.info("Warm-up complete for %s (%d runs)", model_name, runs)

    def unload_session(self, model_name: str) -> None:
        """Release an inference session and free resources."""
        session = self._sessions.pop(model_name, None)
        if session is not None:
            del session
            logger.info("Session unloaded: %s", model_name)

    # ------------------------------------------------------------------
    # Inference
    # ------------------------------------------------------------------

    def infer(
        self,
        model_name: str,
        inputs: Dict[str, np.ndarray],
        output_names: Optional[List[str]] = None,
    ) -> List[np.ndarray]:
        """Run inference on a loaded model.

        Parameters
        ----------
        model_name : str
            Session identifier.
        inputs : dict[str, ndarray]
            Named input arrays matching the ONNX graph inputs.
        output_names : list[str], optional
            Specific outputs to retrieve (``None`` = all).

        Returns
        -------
        list[ndarray]
            Model outputs in the same order as ``output_names``.
        """
        session = self._get_session(model_name)
        return session.run(output_names, inputs)

    def infer_policy(self, state: np.ndarray) -> np.ndarray:
        """Convenience: get action logits from the policy network."""
        if "policy" not in self._sessions:
            raise RuntimeError("Policy session not loaded. Call load_session('policy').")
        results = self.infer("policy", {"input": state})
        return results[0]

    def infer_value(self, state: np.ndarray) -> np.ndarray:
        """Convenience: get value estimate from the value network."""
        if "value" not in self._sessions:
            raise RuntimeError("Value session not loaded. Call load_session('value').")
        results = self.infer("value", {"input": state})
        return results[0]

    def infer_multi(
        self, state: np.ndarray
    ) -> Tuple[np.ndarray, np.ndarray]:
        """Run both policy and value inference in one call.

        Returns ``(action_logits, value_estimate)`` as a tuple.
        """
        logits = self.infer_policy(state)
        value = self.infer_value(state)
        return logits, value

    # ------------------------------------------------------------------
    # Shape inference
    # ------------------------------------------------------------------

    def get_input_info(
        self, model_name: str
    ) -> List[Dict[str, Any]]:
        """Return input names, shapes, and types for a loaded session."""
        session = self._get_session(model_name)
        info = []
        for inp in session.get_inputs():
            info.append(
                {
                    "name": inp.name,
                    "shape": inp.shape,
                    "type": inp.type,
                }
            )
        return info

    def get_output_info(
        self, model_name: str
    ) -> List[Dict[str, Any]]:
        """Return output names, shapes, and types for a loaded session."""
        session = self._get_session(model_name)
        info = []
        for out in session.get_outputs():
            info.append(
                {
                    "name": out.name,
                    "shape": out.shape,
                    "type": out.type,
                }
            )
        return info

    def infer_shapes(self, model_name: str) -> None:
        """Run ONNX shape inference and update the model file in-place."""
        if onnx is None:
            raise RuntimeError("onnx package is required for shape inference")
        model_path = self._resolve_path(model_name)
        model_proto = onnx.load(str(model_path))
        from onnx import shape_inference

        inferred = shape_inference.infer_shapes(model_proto)
        onnx.save(inferred, str(model_path))
        logger.info("Shape inference applied to %s", model_name)

    # ------------------------------------------------------------------
    # Validation (ONNX vs PyTorch)
    # ------------------------------------------------------------------

    def validate(
        self,
        model_name: str,
        pytorch_model: Any,
        num_samples: int = 20,
        tolerance: float = 1e-4,
    ) -> ValidationResult:
        """Compare ONNX outputs against PyTorch reference outputs.

        Runs *num_samples* random inputs through both backends and checks
        that the maximum absolute difference stays within *tolerance*.
        """
        if torch is None:
            raise RuntimeError("PyTorch is required for validation")

        session = self._get_session(model_name)
        inputs_meta = session.get_inputs()
        pytorch_model.eval()

        max_diffs: List[float] = []
        mean_diffs: List[float] = []
        cosines: List[float] = []

        for _ in range(num_samples):
            np_inputs = self._make_dummy_inputs(session, batch_size=1)

            # ONNX inference
            onnx_outputs = session.run(None, np_inputs)

            # PyTorch inference
            torch_inputs = tuple(
                torch.from_numpy(np_inputs[inp.name]) for inp in inputs_meta
            )
            with torch.no_grad():
                pt_out = pytorch_model(*torch_inputs)
            if isinstance(pt_out, torch.Tensor):
                pt_out = [pt_out]
            elif isinstance(pt_out, tuple):
                pt_out = list(pt_out)

            for o_arr, p_tensor in zip(onnx_outputs, pt_out):
                p_arr = p_tensor.numpy()
                diff = np.abs(o_arr - p_arr)
                max_diffs.append(float(diff.max()))
                mean_diffs.append(float(diff.mean()))
                # cosine similarity
                o_flat = o_arr.flatten()
                p_flat = p_arr.flatten()
                denom = np.linalg.norm(o_flat) * np.linalg.norm(p_flat)
                cos = float(np.dot(o_flat, p_flat) / max(denom, 1e-12))
                cosines.append(cos)

        result = ValidationResult(
            model_name=model_name,
            max_abs_diff=max(max_diffs),
            mean_abs_diff=statistics.mean(mean_diffs),
            cosine_sim=statistics.mean(cosines),
            passed=max(max_diffs) < tolerance,
            tolerance=tolerance,
        )
        logger.info("Validation: %s", result.summary())
        return result

    # ------------------------------------------------------------------
    # Benchmarking
    # ------------------------------------------------------------------

    def benchmark(
        self,
        model_name: str,
        batch_size: int = 1,
        num_runs: int = DEFAULT_BENCHMARK_RUNS,
        warmup_runs: int = DEFAULT_WARMUP_RUNS,
    ) -> BenchmarkResult:
        """Measure inference latency and throughput.

        Returns a ``BenchmarkResult`` with mean, p50, p95, p99 latency
        statistics and throughput in samples-per-second.
        """
        session = self._get_session(model_name)
        dummy = self._make_dummy_inputs(session, batch_size=batch_size)

        # Warm-up
        for _ in range(warmup_runs):
            session.run(None, dummy)

        latencies: List[float] = []
        for _ in range(num_runs):
            t0 = time.perf_counter()
            session.run(None, dummy)
            t1 = time.perf_counter()
            latencies.append((t1 - t0) * 1000.0)  # ms

        latencies.sort()

        def _percentile(data: List[float], pct: float) -> float:
            idx = int(len(data) * pct / 100.0)
            return data[min(idx, len(data) - 1)]

        mean_lat = statistics.mean(latencies)
        total_time_s = sum(latencies) / 1000.0
        throughput = (num_runs * batch_size) / total_time_s

        provider = ", ".join(session.get_providers())

        result = BenchmarkResult(
            model_name=model_name,
            provider=provider,
            batch_size=batch_size,
            num_runs=num_runs,
            latency_mean_ms=mean_lat,
            latency_p50_ms=_percentile(latencies, 50),
            latency_p95_ms=_percentile(latencies, 95),
            latency_p99_ms=_percentile(latencies, 99),
            throughput_samples_per_sec=throughput,
        )
        logger.info("Benchmark: %s", result.summary())
        return result

    def benchmark_batch_sweep(
        self,
        model_name: str,
        batch_sizes: Sequence[int] = (1, 2, 4, 8, 16, 32),
        num_runs: int = DEFAULT_BENCHMARK_RUNS,
    ) -> List[BenchmarkResult]:
        """Run benchmarks across multiple batch sizes."""
        results = []
        for bs in batch_sizes:
            try:
                r = self.benchmark(model_name, batch_size=bs, num_runs=num_runs)
                results.append(r)
            except Exception as exc:
                logger.warning("Benchmark failed for bs=%d: %s", bs, exc)
        return results

    # ------------------------------------------------------------------
    # Metadata helpers
    # ------------------------------------------------------------------

    def _embed_metadata(self, model_path: Path, meta: ModelMetadata) -> None:
        """Write metadata properties into an ONNX model file."""
        if onnx is None:
            logger.warning("onnx package not found; skipping metadata embed")
            return
        model_proto = onnx.load(str(model_path))
        for key, value in meta.to_dict().items():
            entry = model_proto.metadata_props.add()
            entry.key = key
            entry.value = value
        onnx.save(model_proto, str(model_path))

    def read_metadata(self, model_name: str) -> Dict[str, str]:
        """Read metadata from an ONNX model on disk."""
        if onnx is None:
            raise RuntimeError("onnx package is required")
        model_path = self._resolve_path(model_name)
        model_proto = onnx.load(str(model_path))
        return {p.key: p.value for p in model_proto.metadata_props}

    # ------------------------------------------------------------------
    # Multi-model serving helpers
    # ------------------------------------------------------------------

    def load_policy_and_value(
        self,
        policy_name: str = "policy",
        value_name: str = "value",
        providers: Optional[List[ExecutionProviderKind]] = None,
    ) -> None:
        """Load both policy and value sessions for dual-head inference."""
        self.load_session(policy_name, providers=providers)
        self.load_session(value_name, providers=providers)
        logger.info("Multi-model serving ready (policy + value)")

    def list_sessions(self) -> List[str]:
        """Return names of all loaded sessions."""
        return list(self._sessions.keys())

    def list_models(self) -> List[Dict[str, Any]]:
        """List all known models with path and metadata."""
        models = []
        for name, path in self._model_paths.items():
            models.append(
                {
                    "name": name,
                    "path": str(path),
                    "size_mb": round(path.stat().st_size / (1024 * 1024), 2)
                    if path.exists()
                    else None,
                    "loaded": name in self._sessions,
                    "metadata": self._metadata.get(name),
                }
            )
        return models

    # ------------------------------------------------------------------
    # Full pipeline convenience
    # ------------------------------------------------------------------

    def export_and_serve(
        self,
        pytorch_model: Any,
        model_name: str,
        sample_inputs: Any,
        providers: Optional[List[ExecutionProviderKind]] = None,
        optimise: bool = True,
        quantize: bool = False,
        validate: bool = True,
        metadata: Optional[ModelMetadata] = None,
    ) -> Dict[str, Any]:
        """End-to-end: export, optimise, optionally quantize, load, validate.

        Returns a summary dict with paths, validation results, and benchmark.
        """
        summary: Dict[str, Any] = {"model_name": model_name}

        # 1. Export
        onnx_path = self.export_pytorch(
            pytorch_model, model_name, sample_inputs, metadata=metadata
        )
        summary["export_path"] = str(onnx_path)

        # 2. Optimise
        if optimise:
            opt_path = self.optimise(model_name)
            summary["optimised_path"] = str(opt_path)

        # 3. Quantize (dynamic INT8)
        if quantize:
            q_path = self.quantize_dynamic_int8(model_name)
            summary["quantized_path"] = str(q_path)
            # Point session to quantized model
            self._model_paths[model_name] = q_path

        # 4. Load session
        self.load_session(model_name, providers=providers)
        summary["providers"] = self._sessions[model_name].get_providers()

        # 5. Validate
        if validate:
            vr = self.validate(model_name, pytorch_model)
            summary["validation"] = vr.summary()

        # 6. Quick benchmark
        br = self.benchmark(model_name, batch_size=1, num_runs=50)
        summary["benchmark"] = br.summary()

        return summary

    # ------------------------------------------------------------------
    # Internal utilities
    # ------------------------------------------------------------------

    def _resolve_path(self, model_name: str) -> Path:
        """Get the file path for a model, checking registration then disk."""
        if model_name in self._model_paths:
            return self._model_paths[model_name]
        # Try common naming conventions
        for suffix in ("", "_opt", "_int8_dyn", "_int8_static"):
            candidate = self.model_dir / f"{model_name}{suffix}.onnx"
            if candidate.exists():
                self._model_paths[model_name] = candidate
                return candidate
        raise FileNotFoundError(
            f"No ONNX model found for '{model_name}' in {self.model_dir}"
        )

    def _get_session(self, model_name: str) -> Any:
        """Retrieve a loaded session or raise."""
        session = self._sessions.get(model_name)
        if session is None:
            raise RuntimeError(
                f"Session '{model_name}' is not loaded. "
                f"Call load_session('{model_name}') first."
            )
        return session

    @staticmethod
    def _make_dummy_inputs(
        session: Any, batch_size: int = 1
    ) -> Dict[str, np.ndarray]:
        """Create random inputs matching a session's expected shapes."""
        dummy: Dict[str, np.ndarray] = {}
        for inp in session.get_inputs():
            shape = []
            for dim in inp.shape:
                if isinstance(dim, str) or dim is None:
                    shape.append(batch_size)
                else:
                    shape.append(dim)
            dtype = np.float32
            if "int" in (inp.type or "").lower():
                dtype = np.int64
            dummy[inp.name] = np.random.randn(*shape).astype(dtype)
        return dummy


# ---------------------------------------------------------------------------
# CLI entry point
# ---------------------------------------------------------------------------

def main() -> None:
    """Demonstrate full export-optimise-serve-benchmark pipeline."""
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    )

    if torch is None or ort is None:
        logger.error("PyTorch and onnxruntime are required. pip install torch onnxruntime")
        return

    server = SC2ModelServer(model_dir="./onnx_models")

    # --- Policy network ---
    policy_net = SC2PolicyNet()
    policy_sample = torch.randn(1, SC2_STATE_DIM)
    policy_meta = ModelMetadata(
        name="sc2_policy",
        version="1.0.0",
        description="Zerg policy network — maps game state to action logits",
    )

    policy_summary = server.export_and_serve(
        pytorch_model=policy_net,
        model_name="policy",
        sample_inputs=policy_sample,
        metadata=policy_meta,
    )
    print("\n=== Policy Network ===")
    for k, v in policy_summary.items():
        print(f"  {k}: {v}")

    # --- Value network ---
    value_net = SC2ValueNet()
    value_sample = torch.randn(1, SC2_STATE_DIM)
    value_meta = ModelMetadata(
        name="sc2_value",
        version="1.0.0",
        description="Zerg value network — estimates win probability",
    )

    value_summary = server.export_and_serve(
        pytorch_model=value_net,
        model_name="value",
        sample_inputs=value_sample,
        metadata=value_meta,
    )
    print("\n=== Value Network ===")
    for k, v in value_summary.items():
        print(f"  {k}: {v}")

    # --- Multi-model inference ---
    print("\n=== Multi-Model Inference ===")
    state = np.random.randn(4, SC2_STATE_DIM).astype(np.float32)
    logits, value = server.infer_multi(state)
    print(f"  Batch size: {state.shape[0]}")
    print(f"  Action logits shape: {logits.shape}")
    print(f"  Value shape: {value.shape}")

    # --- Batch sweep benchmark ---
    print("\n=== Batch Sweep Benchmark (Policy) ===")
    results = server.benchmark_batch_sweep("policy", batch_sizes=[1, 4, 16, 64])
    for r in results:
        print(f"  {r.summary()}")

    # --- Input / output info ---
    print("\n=== Model I/O Info ===")
    for name in server.list_sessions():
        print(f"  [{name}] inputs:  {server.get_input_info(name)}")
        print(f"  [{name}] outputs: {server.get_output_info(name)}")

    # --- Model registry ---
    print("\n=== Model Registry ===")
    for m in server.list_models():
        print(f"  {m['name']}: {m['path']} ({m['size_mb']} MB) loaded={m['loaded']}")


if __name__ == "__main__":
    main()
