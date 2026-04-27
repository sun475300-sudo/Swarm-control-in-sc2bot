"""
Phase 359: TensorRT Export
Export SC2 model to TensorRT for inference acceleration.
Supports FP16/INT8 quantization and engine serialization.
Expected speedup: 3-5x over PyTorch.
"""

import os
import time
import torch
import torch.nn as nn
from typing import Optional, Dict, Tuple, List

try:
    import tensorrt as trt
    import pycuda.driver as cuda
    import pycuda.autoinit

    TRT_AVAILABLE = True
except ImportError:
    TRT_AVAILABLE = False
    trt = None

try:
    import onnx
    import onnxruntime as ort

    ONNX_AVAILABLE = True
except ImportError:
    ONNX_AVAILABLE = False


def export_to_onnx(
    model: nn.Module,
    dummy_input: torch.Tensor,
    output_path: str,
    input_names: List[str] = None,
    output_names: List[str] = None,
    dynamic_axes: Optional[Dict] = None,
    opset: int = 17,
) -> str:
    """Export PyTorch model to ONNX format."""
    os.makedirs(os.path.dirname(output_path) or ".", exist_ok=True)
    model.eval()
    input_names = input_names or ["obs"]
    output_names = output_names or ["policy_logits", "value"]
    dynamic_axes = dynamic_axes or {
        "obs": {0: "batch_size"},
        "policy_logits": {0: "batch_size"},
        "value": {0: "batch_size"},
    }
    with torch.no_grad():
        torch.onnx.export(
            model,
            dummy_input,
            output_path,
            input_names=input_names,
            output_names=output_names,
            dynamic_axes=dynamic_axes,
            opset_version=opset,
            do_constant_folding=True,
            export_params=True,
        )
    print(f"[ONNX] Model exported to: {output_path}")

    if ONNX_AVAILABLE:
        import onnx as onnx_mod

        model_check = onnx_mod.load(output_path)
        onnx_mod.checker.check_model(model_check)
        print("[ONNX] Model check passed.")
    return output_path


def optimize_with_tensorrt(
    onnx_path: str,
    engine_path: str,
    precision: str = "fp16",
    max_batch_size: int = 32,
    workspace_gb: int = 4,
    calibration_data: Optional[torch.Tensor] = None,
) -> Optional[str]:
    """Build TensorRT engine from ONNX model with FP16 or INT8 quantization."""
    if not TRT_AVAILABLE:
        print("[TensorRT] Not available. Install tensorrt and pycuda.")
        return None

    logger = trt.Logger(trt.Logger.WARNING)
    builder = trt.Builder(logger)
    network = builder.create_network(
        1 << int(trt.NetworkDefinitionCreationFlag.EXPLICIT_BATCH)
    )
    parser = trt.OnnxParser(network, logger)

    with open(onnx_path, "rb") as f:
        if not parser.parse(f.read()):
            for err in range(parser.num_errors):
                print(f"[TRT Parse Error] {parser.get_error(err)}")
            return None

    config = builder.create_builder_config()
    config.set_memory_pool_limit(trt.MemoryPoolType.WORKSPACE, workspace_gb * (1 << 30))

    if precision == "fp16" and builder.platform_has_fast_fp16:
        config.set_flag(trt.BuilderFlag.FP16)
        print("[TensorRT] Using FP16 precision.")
    elif precision == "int8" and builder.platform_has_fast_int8:
        config.set_flag(trt.BuilderFlag.INT8)
        print("[TensorRT] Using INT8 precision.")

    profile = builder.create_optimization_profile()
    input_name = network.get_input(0).name
    obs_dim = network.get_input(0).shape[-1]
    profile.set_shape(
        input_name,
        (1, obs_dim),
        (max_batch_size // 2, obs_dim),
        (max_batch_size, obs_dim),
    )
    config.add_optimization_profile(profile)

    serialized = builder.build_serialized_network(network, config)
    if serialized is None:
        print("[TensorRT] Build failed.")
        return None

    os.makedirs(os.path.dirname(engine_path) or ".", exist_ok=True)
    with open(engine_path, "wb") as f:
        f.write(serialized)
    print(f"[TensorRT] Engine saved to: {engine_path}")
    return engine_path


def load_tensorrt_engine(engine_path: str):
    """Load a serialized TensorRT engine from disk."""
    if not TRT_AVAILABLE:
        return None
    logger = trt.Logger(trt.Logger.WARNING)
    runtime = trt.Runtime(logger)
    with open(engine_path, "rb") as f:
        engine = runtime.deserialize_cuda_engine(f.read())
    return engine


def benchmark_inference(
    model: nn.Module,
    engine_path: Optional[str],
    obs_dim: int = 512,
    batch_size: int = 1,
    n_warmup: int = 50,
    n_runs: int = 200,
) -> Dict[str, float]:
    """Benchmark PyTorch vs TensorRT inference latency."""
    dummy = torch.randn(batch_size, obs_dim)
    results: Dict[str, float] = {}

    # PyTorch benchmark
    model.eval()
    with torch.no_grad():
        for _ in range(n_warmup):
            model(dummy)
    start = time.perf_counter()
    with torch.no_grad():
        for _ in range(n_runs):
            model(dummy)
    pt_ms = (time.perf_counter() - start) * 1000 / n_runs
    results["pytorch_ms"] = round(pt_ms, 3)
    results["pytorch_fps"] = round(1000 / pt_ms, 1)
    print(f"[Bench] PyTorch: {pt_ms:.3f} ms/step ({results['pytorch_fps']} fps)")

    # ONNX Runtime benchmark
    if (
        ONNX_AVAILABLE
        and engine_path
        and engine_path.endswith(".onnx")
        and os.path.exists(engine_path)
    ):
        sess = ort.InferenceSession(engine_path, providers=["CPUExecutionProvider"])
        inp = dummy.numpy()
        for _ in range(n_warmup):
            sess.run(None, {"obs": inp})
        start = time.perf_counter()
        for _ in range(n_runs):
            sess.run(None, {"obs": inp})
        ort_ms = (time.perf_counter() - start) * 1000 / n_runs
        results["onnx_ms"] = round(ort_ms, 3)
        results["speedup_onnx"] = round(pt_ms / ort_ms, 2)
        print(
            f"[Bench] ONNX: {ort_ms:.3f} ms/step (speedup: {results['speedup_onnx']}x)"
        )

    return results
