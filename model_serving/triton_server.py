"""
Phase 360: Triton Inference Server
Triton Inference Server integration for serving SC2 models at scale.
Model ensemble: obs_encoder → policy_net → action_decoder as a pipeline.
Supports gRPC async inference and dynamic batching.
"""

import asyncio
import json
import numpy as np
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple, Any

try:
    import tritonclient.grpc.aio as grpcclient
    from tritonclient.utils import InferenceServerException, triton_to_np_dtype

    TRITON_AVAILABLE = True
except ImportError:
    TRITON_AVAILABLE = False
    grpcclient = None


# --- Configuration ---


@dataclass
class TritonConfig:
    url: str = "localhost:8001"  # gRPC endpoint
    model_name: str = "sc2_ensemble"
    obs_encoder_model: str = "sc2_obs_encoder"
    policy_model: str = "sc2_policy"
    action_decoder_model: str = "sc2_action_decoder"
    max_batch_size: int = 32
    timeout_ms: float = 100.0
    verbose: bool = False


@dataclass
class InferenceRequest:
    obs: np.ndarray  # (B, obs_dim) float32
    action_mask: Optional[np.ndarray] = None  # (B, action_dim) bool


@dataclass
class InferenceResponse:
    action_type: np.ndarray  # (B,) int32
    action_args: Dict[str, np.ndarray] = field(default_factory=dict)
    value: np.ndarray = field(default_factory=lambda: np.zeros(1))
    latency_ms: float = 0.0


# --- Model Repository Config Generator ---


def generate_model_config(
    model_name: str,
    input_shapes: List[Tuple],
    output_shapes: List[Tuple],
    max_batch_size: int = 32,
    backend: str = "onnxruntime",
) -> Dict:
    """Generate Triton model config dict."""
    config = {
        "name": model_name,
        "backend": backend,
        "max_batch_size": max_batch_size,
        "input": [
            {"name": f"input_{i}", "data_type": "TYPE_FP32", "dims": list(shape)}
            for i, shape in enumerate(input_shapes)
        ],
        "output": [
            {"name": f"output_{i}", "data_type": "TYPE_FP32", "dims": list(shape)}
            for i, shape in enumerate(output_shapes)
        ],
        "dynamic_batching": {
            "preferred_batch_size": [8, 16, 32],
            "max_queue_delay_microseconds": 1000,
        },
        "instance_group": [{"kind": "KIND_GPU", "count": 1}],
    }
    return config


def generate_ensemble_config(cfg: TritonConfig) -> Dict:
    """Generate ensemble model pipeline config."""
    return {
        "name": cfg.model_name,
        "platform": "ensemble",
        "max_batch_size": cfg.max_batch_size,
        "input": [{"name": "obs", "data_type": "TYPE_FP32", "dims": [-1]}],
        "output": [
            {"name": "policy_logits", "data_type": "TYPE_FP32", "dims": [-1]},
            {"name": "value", "data_type": "TYPE_FP32", "dims": [1]},
        ],
        "ensemble_scheduling": {
            "step": [
                {
                    "model_name": cfg.obs_encoder_model,
                    "model_version": 1,
                    "input_map": {"input_0": "obs"},
                    "output_map": {"output_0": "encoded_obs"},
                },
                {
                    "model_name": cfg.policy_model,
                    "model_version": 1,
                    "input_map": {"input_0": "encoded_obs"},
                    "output_map": {"output_0": "policy_logits", "output_1": "value"},
                },
            ]
        },
    }


# --- Triton SC2 Client ---


class TritonSC2Client:
    """
    Async gRPC client for SC2 model inference via Triton Inference Server.
    Supports single-step and batched async inference.
    """

    def __init__(self, cfg: TritonConfig):
        self.cfg = cfg
        self._client = None

    async def connect(self) -> None:
        if not TRITON_AVAILABLE:
            raise RuntimeError(
                "tritonclient not installed. pip install tritonclient[grpc]"
            )
        self._client = grpcclient.InferenceServerClient(
            url=self.cfg.url, verbose=self.cfg.verbose
        )
        is_live = await self._client.is_server_live()
        print(f"[Triton] Server live: {is_live} at {self.cfg.url}")

    async def is_model_ready(self, model_name: Optional[str] = None) -> bool:
        if self._client is None:
            return False
        name = model_name or self.cfg.model_name
        return await self._client.is_model_ready(name)

    async def infer(self, request: InferenceRequest) -> InferenceResponse:
        """Send async inference request and return decoded response."""
        import time

        t0 = time.perf_counter()
        if self._client is None:
            raise RuntimeError("Not connected. Call connect() first.")

        obs = request.obs.astype(np.float32)
        inputs = [grpcclient.InferInput("obs", obs.shape, "FP32")]
        inputs[0].set_data_from_numpy(obs)

        outputs = [
            grpcclient.InferRequestedOutput("policy_logits"),
            grpcclient.InferRequestedOutput("value"),
        ]
        response = await self._client.infer(
            model_name=self.cfg.model_name,
            inputs=inputs,
            outputs=outputs,
            timeout=self.cfg.timeout_ms / 1000.0,
        )
        policy_logits = response.as_numpy("policy_logits")
        value = response.as_numpy("value")
        action_type = np.argmax(policy_logits, axis=-1).astype(np.int32)
        latency_ms = (time.perf_counter() - t0) * 1000
        return InferenceResponse(
            action_type=action_type, value=value, latency_ms=round(latency_ms, 2)
        )

    async def batch_infer(
        self, requests: List[InferenceRequest]
    ) -> List[InferenceResponse]:
        """Run multiple requests concurrently."""
        tasks = [self.infer(r) for r in requests]
        return await asyncio.gather(*tasks)

    async def close(self) -> None:
        if self._client is not None:
            await self._client.close()
            self._client = None

    async def get_model_metadata(self) -> Dict:
        if self._client is None:
            return {}
        meta = await self._client.get_model_metadata(self.cfg.model_name)
        return {
            "name": meta.name,
            "versions": list(meta.versions),
            "platform": meta.platform,
        }
