"""
Phase 639: Jetson Nano Edge Deployment for Real-Time SC2 Inference
===================================================================

NVIDIA Jetson Nano deployment pipeline for real-time StarCraft II policy
inference at the edge. Integrates TensorRT optimization (FP16/INT8),
CUDA stream management for asynchronous inference, and power mode
profiling to achieve < 10ms inference latency on constrained hardware.

Key features:
  - TensorRT engine building with FP16/INT8 calibration
  - CUDA stream management for async inference pipelines
  - Power mode profiles: 5W, 10W, MAXN for Jetson Nano
  - Dynamic batch scheduling based on thermal/power state
  - SC2-specific real-time policy execution on edge hardware
  - Mock hardware layer for development without physical Jetson
  - Thermal throttling detection and adaptive inference
  - Multi-model pipeline: observation encoder + policy head
"""

from __future__ import annotations

import copy
import json
import logging
import math
import os
import random
import struct
import threading
import time
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Sequence, Tuple, Union

import numpy as np

# ---------------------------------------------------------------------------
# Optional imports with fallback
# ---------------------------------------------------------------------------
try:
    import tensorrt as trt

    HAS_TRT = True
except ImportError:
    HAS_TRT = False

try:
    import pycuda.driver as cuda
    import pycuda.autoinit

    HAS_CUDA = True
except ImportError:
    HAS_CUDA = False

logger = logging.getLogger(__name__)


# ===================================================================
# Enums and constants
# ===================================================================


class PowerMode(Enum):
    """Jetson Nano power modes."""

    MODE_5W = "5W"  # 2-core ARM @ 918 MHz, GPU @ 640 MHz
    MODE_10W = "10W"  # 4-core ARM @ 1.43 GHz, GPU @ 921 MHz
    MAXN = "MAXN"  # No power limit, max clocks


class PrecisionMode(Enum):
    """TensorRT precision modes."""

    FP32 = "fp32"
    FP16 = "fp16"
    INT8 = "int8"
    MIXED = "mixed"  # FP16 backbone + INT8 policy head


class ThermalState(Enum):
    """Jetson thermal throttling states."""

    COOL = "cool"  # < 50C
    WARM = "warm"  # 50-70C
    HOT = "hot"  # 70-85C
    THROTTLING = "throttling"  # > 85C, clock reduction active


class InferenceMode(Enum):
    """Inference execution modes."""

    SYNC = "synchronous"
    ASYNC = "asynchronous"
    PIPELINED = "pipelined"


# Jetson Nano hardware specifications
JETSON_NANO_SPECS: Dict[str, Any] = {
    "gpu": "Maxwell 128-core",
    "cpu": "Quad-core ARM Cortex-A57 @ 1.43 GHz",
    "memory_gb": 4,
    "gpu_memory_shared": True,
    "max_power_w": 10,
    "cuda_cores": 128,
    "tensor_cores": 0,
    "compute_capability": "5.3",
}

# Power mode configurations
POWER_PROFILES: Dict[PowerMode, Dict[str, Any]] = {
    PowerMode.MODE_5W: {
        "cpu_cores": 2,
        "cpu_freq_mhz": 918,
        "gpu_freq_mhz": 640,
        "power_budget_w": 5.0,
        "memory_bw_gbps": 12.8,
        "inference_multiplier": 1.6,  # slower than MAXN
    },
    PowerMode.MODE_10W: {
        "cpu_cores": 4,
        "cpu_freq_mhz": 1430,
        "gpu_freq_mhz": 921,
        "power_budget_w": 10.0,
        "memory_bw_gbps": 25.6,
        "inference_multiplier": 1.0,
    },
    PowerMode.MAXN: {
        "cpu_cores": 4,
        "cpu_freq_mhz": 1430,
        "gpu_freq_mhz": 921,
        "power_budget_w": 15.0,
        "memory_bw_gbps": 25.6,
        "inference_multiplier": 0.85,
    },
}

# SC2 model configurations for Jetson deployment
SC2_JETSON_MODELS: Dict[str, Dict[str, Any]] = {
    "observation_encoder": {
        "input_dim": 256,
        "hidden_dim": 128,
        "output_dim": 64,
        "target_latency_ms": 3.0,
        "description": "Encodes raw SC2 observation into compact state vector",
    },
    "policy_head": {
        "input_dim": 64,
        "hidden_dim": 32,
        "output_dim": 16,
        "target_latency_ms": 2.0,
        "description": "Maps encoded state to action probabilities",
    },
    "value_head": {
        "input_dim": 64,
        "hidden_dim": 32,
        "output_dim": 1,
        "target_latency_ms": 1.5,
        "description": "Estimates state value for advantage computation",
    },
    "battle_predictor": {
        "input_dim": 96,
        "hidden_dim": 48,
        "output_dim": 2,
        "target_latency_ms": 2.0,
        "description": "Predicts battle outcome for engagement decisions",
    },
}


# ===================================================================
# Data classes
# ===================================================================


@dataclass
class JetsonConfig:
    """Configuration for Jetson Nano deployment.

    Encapsulates all deployment parameters including power mode,
    precision, thermal limits, and inference targets.
    """

    power_mode: PowerMode = PowerMode.MODE_10W
    precision: PrecisionMode = PrecisionMode.FP16
    max_batch_size: int = 1
    workspace_size_mb: int = 256
    inference_mode: InferenceMode = InferenceMode.ASYNC
    target_latency_ms: float = 10.0
    thermal_limit_c: float = 80.0
    enable_dla: bool = False  # Deep Learning Accelerator (Xavier only)
    num_cuda_streams: int = 2
    calibration_batches: int = 100
    enable_profiling: bool = False

    def get_power_profile(self) -> Dict[str, Any]:
        """Return the hardware profile for the current power mode."""
        return POWER_PROFILES[self.power_mode]

    def validate(self) -> List[str]:
        """Validate configuration and return list of warnings."""
        warnings: List[str] = []
        if self.precision == PrecisionMode.INT8 and self.calibration_batches < 50:
            warnings.append("INT8 calibration with < 50 batches may reduce accuracy")
        if self.max_batch_size > 4:
            warnings.append("Batch size > 4 may exceed Jetson Nano memory")
        if self.workspace_size_mb > 512:
            warnings.append("Workspace > 512MB may cause OOM on 4GB Jetson")
        if self.enable_dla:
            warnings.append("DLA is not available on Jetson Nano (Xavier/Orin only)")
        if self.target_latency_ms < 5.0 and self.power_mode == PowerMode.MODE_5W:
            warnings.append("< 5ms latency target may be unreachable in 5W mode")
        return warnings


@dataclass
class TRTEngineInfo:
    """Metadata about a built TensorRT engine."""

    name: str
    precision: str
    input_shape: Tuple[int, ...]
    output_shape: Tuple[int, ...]
    engine_size_bytes: int
    build_time_s: float
    max_batch_size: int
    num_layers: int
    estimated_latency_ms: float


@dataclass
class CUDAStreamContext:
    """Represents a CUDA stream for async inference."""

    stream_id: int
    is_busy: bool = False
    queued_requests: int = 0
    total_processed: int = 0
    total_latency_ms: float = 0.0

    @property
    def avg_latency_ms(self) -> float:
        if self.total_processed == 0:
            return 0.0
        return self.total_latency_ms / self.total_processed


@dataclass
class ThermalSnapshot:
    """Snapshot of Jetson thermal state."""

    cpu_temp_c: float
    gpu_temp_c: float
    board_temp_c: float
    thermal_state: ThermalState
    fan_speed_pct: float
    timestamp: float = 0.0


@dataclass
class InferenceResult:
    """Result from a single inference execution."""

    output: np.ndarray
    latency_ms: float
    stream_id: int
    batch_size: int
    precision: str
    thermal_state: ThermalState = ThermalState.COOL


# ===================================================================
# TensorRTOptimizer
# ===================================================================


class TensorRTOptimizer:
    """Builds and optimizes TensorRT engines for Jetson Nano deployment.

    Handles ONNX-to-TensorRT conversion, precision calibration (FP16/INT8),
    layer fusion, and engine serialization for SC2 model inference.
    """

    def __init__(self, config: JetsonConfig) -> None:
        self.config = config
        self._engines: Dict[str, TRTEngineInfo] = {}
        self._calibration_cache: Dict[str, np.ndarray] = {}
        logger.info(
            "TensorRTOptimizer initialized (precision=%s, workspace=%dMB)",
            config.precision.value,
            config.workspace_size_mb,
        )

    def _estimate_engine_size(
        self, input_dim: int, hidden_dim: int, output_dim: int
    ) -> int:
        """Estimate serialized TensorRT engine size in bytes."""
        param_count = (
            input_dim * hidden_dim + hidden_dim + hidden_dim * output_dim + output_dim
        )
        bytes_per_param = {
            PrecisionMode.FP32: 4,
            PrecisionMode.FP16: 2,
            PrecisionMode.INT8: 1,
            PrecisionMode.MIXED: 2,
        }
        bpp = bytes_per_param.get(self.config.precision, 4)
        # TensorRT adds ~2x overhead for engine metadata and execution context
        return int(param_count * bpp * 2.0 + 4096)

    def _estimate_latency(
        self, input_dim: int, hidden_dim: int, output_dim: int
    ) -> float:
        """Estimate inference latency in milliseconds for Jetson Nano."""
        flops = 2 * (input_dim * hidden_dim + hidden_dim * output_dim)
        # Jetson Nano Maxwell: ~472 GFLOPS FP16
        gflops_available = {
            PrecisionMode.FP32: 236.0,
            PrecisionMode.FP16: 472.0,
            PrecisionMode.INT8: 472.0,
            PrecisionMode.MIXED: 450.0,
        }
        gf = gflops_available.get(self.config.precision, 236.0)
        # Account for memory bandwidth bottleneck and overhead
        compute_ms = (flops / (gf * 1e6)) * 1000.0
        overhead_ms = 0.5  # kernel launch + memory transfer overhead
        power_mult = self.config.get_power_profile()["inference_multiplier"]
        return (compute_ms + overhead_ms) * power_mult

    def _generate_calibration_data(
        self, model_name: str, input_dim: int, num_batches: int
    ) -> List[np.ndarray]:
        """Generate synthetic calibration data for INT8 quantization."""
        logger.info(
            "Generating %d calibration batches for '%s'",
            num_batches,
            model_name,
        )
        batches = []
        for _ in range(num_batches):
            batch = np.random.randn(self.config.max_batch_size, input_dim).astype(
                np.float32
            )
            batches.append(batch)
        return batches

    def build_engine(
        self,
        model_name: str,
        input_dim: int,
        hidden_dim: int,
        output_dim: int,
    ) -> TRTEngineInfo:
        """Build a TensorRT engine from model specification.

        Simulates the TensorRT engine building process including layer
        fusion, precision calibration, and workspace allocation.

        Args:
            model_name: Unique name for the engine.
            input_dim: Input tensor dimension.
            hidden_dim: Hidden layer dimension.
            output_dim: Output tensor dimension.

        Returns:
            TRTEngineInfo with engine metadata.
        """
        start_time = time.time()
        logger.info(
            "Building TensorRT engine '%s' (precision=%s, batch=%d)",
            model_name,
            self.config.precision.value,
            self.config.max_batch_size,
        )

        # INT8 calibration pass
        if self.config.precision in (PrecisionMode.INT8, PrecisionMode.MIXED):
            cal_data = self._generate_calibration_data(
                model_name, input_dim, self.config.calibration_batches
            )
            # Compute per-layer activation ranges for calibration
            activation_ranges = []
            for batch in cal_data[:10]:
                hidden = batch @ (
                    np.random.randn(input_dim, hidden_dim).astype(np.float32) * 0.01
                )
                activation_ranges.append((hidden.min(), hidden.max()))
            self._calibration_cache[model_name] = np.array(activation_ranges)
            logger.info("INT8 calibration complete for '%s'", model_name)

        engine_size = self._estimate_engine_size(input_dim, hidden_dim, output_dim)
        latency = self._estimate_latency(input_dim, hidden_dim, output_dim)
        build_time = time.time() - start_time

        # Simulate layer count after fusion
        base_layers = 6  # matmul + bias + relu per FC layer (x2)
        fused_layers = max(3, base_layers - 2)  # fusion reduces layer count

        info = TRTEngineInfo(
            name=model_name,
            precision=self.config.precision.value,
            input_shape=(self.config.max_batch_size, input_dim),
            output_shape=(self.config.max_batch_size, output_dim),
            engine_size_bytes=engine_size,
            build_time_s=round(build_time, 3),
            max_batch_size=self.config.max_batch_size,
            num_layers=fused_layers,
            estimated_latency_ms=round(latency, 3),
        )

        self._engines[model_name] = info
        logger.info(
            "Engine '%s' built: %d bytes, ~%.2fms latency, %d layers",
            model_name,
            engine_size,
            latency,
            fused_layers,
        )
        return info

    def build_sc2_pipeline(self) -> Dict[str, TRTEngineInfo]:
        """Build TensorRT engines for all SC2 pipeline models.

        Returns:
            Dictionary mapping model name to engine info.
        """
        results = {}
        for name, spec in SC2_JETSON_MODELS.items():
            info = self.build_engine(
                model_name=name,
                input_dim=spec["input_dim"],
                hidden_dim=spec["hidden_dim"],
                output_dim=spec["output_dim"],
            )
            results[name] = info
        return results

    def get_engine(self, name: str) -> Optional[TRTEngineInfo]:
        """Retrieve a built engine by name."""
        return self._engines.get(name)

    def get_total_memory_mb(self) -> float:
        """Compute total GPU memory required for all engines."""
        total_bytes = sum(e.engine_size_bytes for e in self._engines.values())
        return total_bytes / (1024 * 1024)

    def summary(self) -> Dict[str, Any]:
        """Return summary of all built engines."""
        return {
            "num_engines": len(self._engines),
            "total_memory_mb": round(self.get_total_memory_mb(), 2),
            "precision": self.config.precision.value,
            "engines": {
                name: {
                    "latency_ms": info.estimated_latency_ms,
                    "size_bytes": info.engine_size_bytes,
                    "layers": info.num_layers,
                }
                for name, info in self._engines.items()
            },
        }


# ===================================================================
# JetsonInferenceEngine
# ===================================================================


class JetsonInferenceEngine:
    """Manages CUDA-accelerated inference on Jetson Nano.

    Handles CUDA stream lifecycle, async inference scheduling,
    thermal monitoring, and adaptive batch management.
    """

    def __init__(self, config: JetsonConfig) -> None:
        self.config = config
        self._streams: List[CUDAStreamContext] = []
        self._model_weights: Dict[str, Dict[str, np.ndarray]] = {}
        self._thermal_history: List[ThermalSnapshot] = []
        self._current_thermal = ThermalState.COOL
        self._inference_log: List[InferenceResult] = []
        self._lock = threading.Lock()

        # Initialize CUDA streams
        for i in range(config.num_cuda_streams):
            self._streams.append(CUDAStreamContext(stream_id=i))

        logger.info(
            "JetsonInferenceEngine initialized (%d streams, mode=%s)",
            config.num_cuda_streams,
            config.inference_mode.value,
        )

    def _get_available_stream(self) -> CUDAStreamContext:
        """Find the least loaded CUDA stream."""
        available = [s for s in self._streams if not s.is_busy]
        if available:
            return min(available, key=lambda s: s.queued_requests)
        # All busy, return one with fewest queued
        return min(self._streams, key=lambda s: s.queued_requests)

    def _simulate_thermal(self) -> ThermalSnapshot:
        """Simulate Jetson thermal sensor readings."""
        base_temp = 45.0
        load_factor = sum(s.total_processed for s in self._streams) * 0.002
        noise = random.gauss(0, 2.0)
        gpu_temp = min(95.0, base_temp + load_factor + noise)
        cpu_temp = gpu_temp - random.uniform(2, 8)
        board_temp = gpu_temp - random.uniform(5, 15)

        if gpu_temp < 50:
            state = ThermalState.COOL
        elif gpu_temp < 70:
            state = ThermalState.WARM
        elif gpu_temp < 85:
            state = ThermalState.HOT
        else:
            state = ThermalState.THROTTLING

        fan_speed = max(0.0, min(100.0, (gpu_temp - 40) * 2.0))

        snapshot = ThermalSnapshot(
            cpu_temp_c=round(cpu_temp, 1),
            gpu_temp_c=round(gpu_temp, 1),
            board_temp_c=round(board_temp, 1),
            thermal_state=state,
            fan_speed_pct=round(fan_speed, 1),
            timestamp=time.time(),
        )

        self._thermal_history.append(snapshot)
        self._current_thermal = state
        return snapshot

    def load_model(
        self, name: str, input_dim: int, hidden_dim: int, output_dim: int
    ) -> None:
        """Load model weights into GPU memory (simulated).

        Args:
            name: Model identifier.
            input_dim: Input feature dimension.
            hidden_dim: Hidden layer dimension.
            output_dim: Output dimension.
        """
        logger.info("Loading model '%s' to Jetson GPU memory", name)

        # Create mock weights matching the precision mode
        dtype = np.float32
        if self.config.precision == PrecisionMode.FP16:
            dtype = np.float16

        weights = {
            "w1": np.random.randn(input_dim, hidden_dim).astype(dtype) * 0.02,
            "b1": np.zeros(hidden_dim, dtype=dtype),
            "w2": np.random.randn(hidden_dim, hidden_dim).astype(dtype) * 0.02,
            "b2": np.zeros(hidden_dim, dtype=dtype),
            "w3": np.random.randn(hidden_dim, output_dim).astype(dtype) * 0.02,
            "b3": np.zeros(output_dim, dtype=dtype),
        }

        self._model_weights[name] = weights
        mem_bytes = sum(w.nbytes for w in weights.values())
        logger.info("Model '%s' loaded: %.2f KB GPU memory", name, mem_bytes / 1024)

    def _forward_pass(self, name: str, input_data: np.ndarray) -> np.ndarray:
        """Execute forward pass through model weights."""
        w = self._model_weights[name]
        # Ensure float32 for computation
        x = input_data.astype(np.float32)

        # Layer 1
        h = x @ w["w1"].astype(np.float32) + w["b1"].astype(np.float32)
        h = np.maximum(h, 0)  # ReLU

        # Layer 2
        h = h @ w["w2"].astype(np.float32) + w["b2"].astype(np.float32)
        h = np.maximum(h, 0)  # ReLU

        # Layer 3 (output)
        out = h @ w["w3"].astype(np.float32) + w["b3"].astype(np.float32)
        return out

    def infer_sync(self, name: str, input_data: np.ndarray) -> InferenceResult:
        """Run synchronous inference on a loaded model.

        Args:
            name: Model name.
            input_data: Input numpy array of shape (batch, input_dim).

        Returns:
            InferenceResult with output and timing info.

        Raises:
            KeyError: If model is not loaded.
        """
        if name not in self._model_weights:
            raise KeyError(f"Model '{name}' not loaded on Jetson")

        stream = self._get_available_stream()
        stream.is_busy = True
        thermal = self._simulate_thermal()

        # Apply thermal throttling penalty
        throttle_mult = 1.0
        if thermal.thermal_state == ThermalState.HOT:
            throttle_mult = 1.3
        elif thermal.thermal_state == ThermalState.THROTTLING:
            throttle_mult = 2.0

        start = time.perf_counter()
        output = self._forward_pass(name, input_data)
        base_latency = (time.perf_counter() - start) * 1000.0

        # Simulate GPU compute overhead
        power_mult = self.config.get_power_profile()["inference_multiplier"]
        latency_ms = base_latency * power_mult * throttle_mult + random.gauss(0.1, 0.05)
        latency_ms = max(0.01, latency_ms)

        stream.is_busy = False
        stream.total_processed += 1
        stream.total_latency_ms += latency_ms

        result = InferenceResult(
            output=output,
            latency_ms=round(latency_ms, 3),
            stream_id=stream.stream_id,
            batch_size=input_data.shape[0],
            precision=self.config.precision.value,
            thermal_state=thermal.thermal_state,
        )

        with self._lock:
            self._inference_log.append(result)

        return result

    def infer_async(
        self,
        name: str,
        input_data: np.ndarray,
        callback: Optional[Callable[[InferenceResult], None]] = None,
    ) -> InferenceResult:
        """Run asynchronous inference (simulated with mock CUDA streams).

        In production, this would enqueue work on a CUDA stream and
        return immediately. Here we simulate the async behavior.

        Args:
            name: Model name.
            input_data: Input array.
            callback: Optional callback invoked with result.

        Returns:
            InferenceResult.
        """
        stream = self._get_available_stream()
        stream.queued_requests += 1

        result = self.infer_sync(name, input_data)

        stream.queued_requests -= 1

        if callback is not None:
            callback(result)

        return result

    def infer_pipeline(
        self,
        observation: np.ndarray,
    ) -> Dict[str, InferenceResult]:
        """Run the full SC2 inference pipeline: encode -> policy + value.

        Chains observation_encoder output into policy_head and value_head,
        simulating a real-time SC2 decision pipeline.

        Args:
            observation: Raw game observation array.

        Returns:
            Dictionary with results from each pipeline stage.
        """
        results: Dict[str, InferenceResult] = {}

        # Stage 1: Observation encoding
        if "observation_encoder" in self._model_weights:
            enc_result = self.infer_sync("observation_encoder", observation)
            results["observation_encoder"] = enc_result
            encoded = enc_result.output
        else:
            # Fallback: use observation directly (truncated/padded)
            encoded = (
                observation[:, :64]
                if observation.shape[1] >= 64
                else np.pad(observation, ((0, 0), (0, 64 - observation.shape[1])))
            )
            results["observation_encoder"] = InferenceResult(
                output=encoded,
                latency_ms=0.0,
                stream_id=0,
                batch_size=observation.shape[0],
                precision="skip",
            )

        # Stage 2: Policy head
        if "policy_head" in self._model_weights:
            policy_result = self.infer_sync("policy_head", encoded)
            results["policy_head"] = policy_result

        # Stage 3: Value head
        if "value_head" in self._model_weights:
            value_result = self.infer_sync("value_head", encoded)
            results["value_head"] = value_result

        return results

    def get_stream_stats(self) -> List[Dict[str, Any]]:
        """Return statistics for each CUDA stream."""
        return [
            {
                "stream_id": s.stream_id,
                "total_processed": s.total_processed,
                "avg_latency_ms": round(s.avg_latency_ms, 3),
                "queued": s.queued_requests,
            }
            for s in self._streams
        ]

    def get_thermal_summary(self) -> Dict[str, Any]:
        """Return thermal monitoring summary."""
        if not self._thermal_history:
            return {"samples": 0}

        gpu_temps = [t.gpu_temp_c for t in self._thermal_history]
        return {
            "samples": len(self._thermal_history),
            "gpu_temp_avg_c": round(sum(gpu_temps) / len(gpu_temps), 1),
            "gpu_temp_max_c": round(max(gpu_temps), 1),
            "gpu_temp_min_c": round(min(gpu_temps), 1),
            "current_state": self._current_thermal.value,
            "throttle_events": sum(
                1
                for t in self._thermal_history
                if t.thermal_state == ThermalState.THROTTLING
            ),
        }

    def get_inference_stats(self) -> Dict[str, Any]:
        """Return overall inference statistics."""
        if not self._inference_log:
            return {"total_inferences": 0}

        latencies = [r.latency_ms for r in self._inference_log]
        sorted_lat = sorted(latencies)
        n = len(sorted_lat)

        return {
            "total_inferences": n,
            "avg_latency_ms": round(sum(latencies) / n, 3),
            "p50_latency_ms": round(sorted_lat[n // 2], 3),
            "p95_latency_ms": (
                round(sorted_lat[int(n * 0.95)], 3)
                if n >= 20
                else round(sorted_lat[-1], 3)
            ),
            "p99_latency_ms": (
                round(sorted_lat[int(n * 0.99)], 3)
                if n >= 100
                else round(sorted_lat[-1], 3)
            ),
            "min_latency_ms": round(sorted_lat[0], 3),
            "max_latency_ms": round(sorted_lat[-1], 3),
            "under_target": sum(
                1 for l in latencies if l < self.config.target_latency_ms
            ),
            "target_ms": self.config.target_latency_ms,
        }

    def unload_model(self, name: str) -> None:
        """Unload model from GPU memory."""
        if name in self._model_weights:
            del self._model_weights[name]
            logger.info("Model '%s' unloaded from GPU", name)

    def unload_all(self) -> None:
        """Unload all models."""
        self._model_weights.clear()
        logger.info("All models unloaded from Jetson GPU")


# ===================================================================
# JetsonAgent
# ===================================================================


class JetsonAgent:
    """High-level SC2 agent running on Jetson Nano edge hardware.

    Combines TensorRT optimization, CUDA inference, and real-time
    policy execution for StarCraft II decision making at the edge.
    """

    def __init__(self, config: Optional[JetsonConfig] = None) -> None:
        self.config = config or JetsonConfig()
        self.optimizer = TensorRTOptimizer(self.config)
        self.engine = JetsonInferenceEngine(self.config)
        self._step_count = 0
        self._total_decision_time_ms = 0.0
        self._action_history: List[Dict[str, Any]] = []

        # Validate config
        warnings = self.config.validate()
        for w in warnings:
            logger.warning("Config warning: %s", w)

        logger.info(
            "JetsonAgent initialized (power=%s, precision=%s, target=%.1fms)",
            self.config.power_mode.value,
            self.config.precision.value,
            self.config.target_latency_ms,
        )

    def setup(self) -> Dict[str, Any]:
        """Build TensorRT engines and load models onto Jetson GPU.

        Returns:
            Setup summary with engine info and memory usage.
        """
        logger.info("Setting up JetsonAgent pipeline...")

        # Build TensorRT engines
        engine_infos = self.optimizer.build_sc2_pipeline()

        # Load models into inference engine
        for name, spec in SC2_JETSON_MODELS.items():
            self.engine.load_model(
                name=name,
                input_dim=spec["input_dim"],
                hidden_dim=spec["hidden_dim"],
                output_dim=spec["output_dim"],
            )

        total_latency = sum(e.estimated_latency_ms for e in engine_infos.values())
        memory_mb = self.optimizer.get_total_memory_mb()

        summary = {
            "engines_built": len(engine_infos),
            "total_estimated_latency_ms": round(total_latency, 2),
            "total_memory_mb": round(memory_mb, 2),
            "power_mode": self.config.power_mode.value,
            "precision": self.config.precision.value,
            "models": list(engine_infos.keys()),
        }

        logger.info(
            "Setup complete: %d engines, ~%.2fms total latency, %.2fMB memory",
            len(engine_infos),
            total_latency,
            memory_mb,
        )
        return summary

    def decide(self, observation: np.ndarray) -> Dict[str, Any]:
        """Make a real-time SC2 decision from observation.

        Runs the full inference pipeline and selects the best action
        based on policy head output.

        Args:
            observation: Game observation array of shape (1, 256).

        Returns:
            Decision dictionary with action, confidence, and timing.
        """
        start = time.perf_counter()

        pipeline_results = self.engine.infer_pipeline(observation)

        # Extract policy output
        if "policy_head" in pipeline_results:
            logits = pipeline_results["policy_head"].output
        else:
            logits = np.random.randn(1, 16).astype(np.float32)

        # Softmax for action probabilities
        shifted = logits - np.max(logits, axis=-1, keepdims=True)
        exp_logits = np.exp(shifted)
        probs = exp_logits / np.sum(exp_logits, axis=-1, keepdims=True)

        action_idx = int(np.argmax(probs, axis=-1)[0])
        confidence = float(probs[0, action_idx])

        # Extract value estimate
        value = 0.0
        if "value_head" in pipeline_results:
            value = float(pipeline_results["value_head"].output[0, 0])

        total_ms = (time.perf_counter() - start) * 1000.0
        self._step_count += 1
        self._total_decision_time_ms += total_ms

        # Determine SC2 action label
        action_labels = [
            "attack",
            "defend",
            "expand",
            "scout",
            "build_army",
            "tech_up",
            "harass",
            "retreat",
            "flank",
            "siege",
            "air_switch",
            "all_in",
            "contain",
            "drop",
            "split",
            "regroup",
        ]
        action_label = action_labels[action_idx % len(action_labels)]

        decision = {
            "step": self._step_count,
            "action_idx": action_idx,
            "action": action_label,
            "confidence": round(confidence, 4),
            "value_estimate": round(value, 4),
            "total_latency_ms": round(total_ms, 3),
            "meets_target": total_ms < self.config.target_latency_ms,
            "thermal_state": self.engine._current_thermal.value,
        }

        self._action_history.append(decision)
        return decision

    def run_episode(
        self,
        num_steps: int = 100,
        observation_dim: int = 256,
    ) -> Dict[str, Any]:
        """Simulate a full SC2 game episode on Jetson.

        Args:
            num_steps: Number of game steps to simulate.
            observation_dim: Observation vector size.

        Returns:
            Episode summary with performance metrics.
        """
        logger.info(
            "Running %d-step episode on Jetson (%s mode)",
            num_steps,
            self.config.power_mode.value,
        )

        decisions = []
        for step in range(num_steps):
            obs = np.random.randn(1, observation_dim).astype(np.float32)
            decision = self.decide(obs)
            decisions.append(decision)

        latencies = [d["total_latency_ms"] for d in decisions]
        met_target = sum(1 for d in decisions if d["meets_target"])

        return {
            "num_steps": num_steps,
            "avg_latency_ms": round(sum(latencies) / len(latencies), 3),
            "max_latency_ms": round(max(latencies), 3),
            "min_latency_ms": round(min(latencies), 3),
            "target_met_pct": round(100.0 * met_target / num_steps, 1),
            "target_latency_ms": self.config.target_latency_ms,
            "power_mode": self.config.power_mode.value,
            "thermal": self.engine.get_thermal_summary(),
            "streams": self.engine.get_stream_stats(),
        }

    def compare_power_modes(self, num_steps: int = 50) -> Dict[str, Dict[str, Any]]:
        """Compare inference performance across power modes.

        Runs a short episode on each power mode to compare latency
        and throughput characteristics.

        Returns:
            Dictionary mapping power mode name to performance summary.
        """
        results = {}
        original_mode = self.config.power_mode

        for mode in PowerMode:
            self.config.power_mode = mode
            # Rebuild engine for new power profile
            self.engine = JetsonInferenceEngine(self.config)
            for name, spec in SC2_JETSON_MODELS.items():
                self.engine.load_model(
                    name=name,
                    input_dim=spec["input_dim"],
                    hidden_dim=spec["hidden_dim"],
                    output_dim=spec["output_dim"],
                )

            episode_result = self.run_episode(num_steps=num_steps)
            results[mode.value] = episode_result

        # Restore original mode
        self.config.power_mode = original_mode
        return results

    def get_agent_stats(self) -> Dict[str, Any]:
        """Return comprehensive agent statistics."""
        avg_decision = (
            self._total_decision_time_ms / self._step_count
            if self._step_count > 0
            else 0.0
        )
        return {
            "total_steps": self._step_count,
            "avg_decision_ms": round(avg_decision, 3),
            "power_mode": self.config.power_mode.value,
            "precision": self.config.precision.value,
            "target_latency_ms": self.config.target_latency_ms,
            "inference_stats": self.engine.get_inference_stats(),
            "thermal_summary": self.engine.get_thermal_summary(),
            "stream_stats": self.engine.get_stream_stats(),
            "optimizer_summary": self.optimizer.summary(),
        }

    def shutdown(self) -> None:
        """Clean shutdown of Jetson agent."""
        logger.info("Shutting down JetsonAgent...")
        self.engine.unload_all()
        logger.info("JetsonAgent shutdown complete")


# ===================================================================
# Demo
# ===================================================================


def demo() -> None:
    """Demonstrate Jetson Nano edge deployment for SC2 inference.

    Walks through TensorRT engine building, CUDA inference, power mode
    comparison, and real-time policy execution with mock hardware.
    """
    print("=" * 72)
    print("Phase 639: Jetson Nano Edge Deployment for Real-Time SC2 Inference")
    print("=" * 72)
    print()

    # --- Step 1: Configure Jetson ---
    print("[1/5] Configuring Jetson Nano...")
    config = JetsonConfig(
        power_mode=PowerMode.MODE_10W,
        precision=PrecisionMode.FP16,
        max_batch_size=1,
        workspace_size_mb=256,
        inference_mode=InferenceMode.ASYNC,
        target_latency_ms=10.0,
        num_cuda_streams=2,
    )
    warnings = config.validate()
    profile = config.get_power_profile()
    print(f"  Power mode: {config.power_mode.value}")
    print(f"  CPU: {profile['cpu_cores']} cores @ {profile['cpu_freq_mhz']} MHz")
    print(f"  GPU: {JETSON_NANO_SPECS['gpu']} @ {profile['gpu_freq_mhz']} MHz")
    print(f"  Precision: {config.precision.value}")
    print(f"  Target latency: {config.target_latency_ms}ms")
    if warnings:
        for w in warnings:
            print(f"  WARNING: {w}")
    print()

    # --- Step 2: Build TensorRT engines ---
    print("[2/5] Building TensorRT engines...")
    agent = JetsonAgent(config)
    setup_info = agent.setup()
    print(f"  Engines built: {setup_info['engines_built']}")
    print(f"  Estimated pipeline latency: {setup_info['total_estimated_latency_ms']}ms")
    print(f"  Total GPU memory: {setup_info['total_memory_mb']} MB")

    engine_summary = agent.optimizer.summary()
    for name, info in engine_summary["engines"].items():
        print(
            f"    {name}: ~{info['latency_ms']}ms, {info['size_bytes']} bytes, {info['layers']} layers"
        )
    print()

    # --- Step 3: Run inference ---
    print("[3/5] Running real-time inference...")
    for i in range(5):
        obs = np.random.randn(1, 256).astype(np.float32)
        decision = agent.decide(obs)
        target_mark = "OK" if decision["meets_target"] else "SLOW"
        print(
            f"  Step {decision['step']}: action={decision['action']:<12s} "
            f"conf={decision['confidence']:.3f} val={decision['value_estimate']:.3f} "
            f"latency={decision['total_latency_ms']:.2f}ms [{target_mark}]"
        )
    print()

    # --- Step 4: Run episode ---
    print("[4/5] Running 50-step episode...")
    episode = agent.run_episode(num_steps=50)
    print(f"  Avg latency: {episode['avg_latency_ms']}ms")
    print(f"  Max latency: {episode['max_latency_ms']}ms")
    print(f"  Target met: {episode['target_met_pct']}%")
    print(
        f"  Thermal: avg GPU {episode['thermal']['gpu_temp_avg_c']}C, "
        f"max {episode['thermal']['gpu_temp_max_c']}C"
    )
    print()

    # --- Step 5: Power mode comparison ---
    print("[5/5] Comparing power modes...")
    power_results = agent.compare_power_modes(num_steps=30)
    for mode_name, result in power_results.items():
        print(
            f"  {mode_name:<6s}: avg={result['avg_latency_ms']:.2f}ms, "
            f"target_met={result['target_met_pct']}%"
        )
    print()

    # Final stats
    stats = agent.get_agent_stats()
    print("Agent summary:")
    print(f"  Total steps: {stats['total_steps']}")
    print(f"  Avg decision time: {stats['avg_decision_ms']}ms")
    print()

    agent.shutdown()
    print("Phase 639 demo complete.")
    print()


if __name__ == "__main__":
    logging.basicConfig(
        level=logging.INFO, format="%(levelname)s | %(name)s | %(message)s"
    )
    demo()

# Phase 639: Jetson registered
