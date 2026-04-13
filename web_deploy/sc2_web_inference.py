# Phase 641: Web Browser Inference (ONNX.js/WASM) for SC2
# Browser-based strategy inference using ONNX runtime, WebAssembly compilation,
# WebWorker offloading, and a REST API server for SC2 dashboard deployment.

from __future__ import annotations

import io
import json
import math
import time
import struct
import hashlib
import logging
import threading
from enum import Enum, auto
from pathlib import Path
from dataclasses import dataclass, field, asdict
from typing import Optional, Any, Union
from http.server import HTTPServer, BaseHTTPRequestHandler

logger = logging.getLogger(__name__)

# ============================================================
# Constants
# ============================================================

WASM_MAGIC = b"\x00asm"
WASM_VERSION = 1
ONNX_OPSET_VERSION = 17

DEFAULT_MODEL_NAME = "sc2_strategy_predictor"
DEFAULT_HOST = "0.0.0.0"
DEFAULT_PORT = 8641

STRATEGY_LABELS = [
    "rush", "timing_attack", "macro", "cheese",
    "all_in", "turtle", "harass", "drop",
    "air_switch", "counter_push",
]

RACE_ENCODING = {"terran": 0, "zerg": 1, "protoss": 2, "random": 3}

FEATURE_NAMES = [
    "minerals", "vespene", "supply_used", "supply_cap",
    "army_count", "worker_count", "base_count", "tech_level",
    "game_loop", "enemy_race", "enemy_army_estimate",
    "enemy_base_count", "apm", "upgrades_count",
    "production_facilities", "expansion_timing",
]


# ============================================================
# Enums
# ============================================================

class ModelFormat(Enum):
    ONNX = "onnx"
    WASM = "wasm"
    JSON_WEIGHTS = "json"


class CompilationTarget(Enum):
    WASM_SIMD = "wasm-simd"
    WASM_BASIC = "wasm-basic"
    WASM_THREADS = "wasm-threads"


class InferenceBackend(Enum):
    ONNXJS = auto()
    WASM_NATIVE = auto()
    CPU_FALLBACK = auto()


# ============================================================
# Data Classes
# ============================================================

@dataclass
class ModelMetadata:
    """Metadata describing an ONNX model for browser deployment."""
    name: str = DEFAULT_MODEL_NAME
    version: str = "1.0.0"
    opset_version: int = ONNX_OPSET_VERSION
    input_shape: list[int] = field(default_factory=lambda: [1, len(FEATURE_NAMES)])
    output_shape: list[int] = field(default_factory=lambda: [1, len(STRATEGY_LABELS)])
    input_names: list[str] = field(default_factory=lambda: ["game_features"])
    output_names: list[str] = field(default_factory=lambda: ["strategy_probs"])
    labels: list[str] = field(default_factory=lambda: list(STRATEGY_LABELS))
    file_size_bytes: int = 0
    checksum: str = ""
    quantized: bool = False
    compile_target: str = CompilationTarget.WASM_BASIC.value

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    def to_json(self) -> str:
        return json.dumps(self.to_dict(), indent=2)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> ModelMetadata:
        valid = {f.name for f in cls.__dataclass_fields__.values()}
        return cls(**{k: v for k, v in data.items() if k in valid})


@dataclass
class InferenceRequest:
    """A single inference request from the browser client."""
    request_id: str = ""
    features: list[float] = field(default_factory=list)
    race: str = "zerg"
    game_loop: int = 0
    timestamp: float = 0.0

    def validate(self) -> bool:
        return len(self.features) == len(FEATURE_NAMES)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class InferenceResult:
    """Prediction result returned to the browser."""
    request_id: str = ""
    strategy: str = ""
    confidence: float = 0.0
    all_probabilities: dict[str, float] = field(default_factory=dict)
    latency_ms: float = 0.0
    backend: str = ""
    timestamp: float = 0.0

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    def to_json(self) -> str:
        return json.dumps(self.to_dict(), indent=2)


# ============================================================
# WASM Compiler (Mock)
# ============================================================

class WASMCompiler:
    """Compiles ONNX model graphs to WebAssembly modules for browser execution."""

    def __init__(self, target: CompilationTarget = CompilationTarget.WASM_BASIC) -> None:
        self.target = target
        self._compilation_log: list[dict[str, Any]] = []
        self._compiled_modules: dict[str, bytes] = {}

    def compile_model(
        self,
        model_name: str,
        input_dim: int = len(FEATURE_NAMES),
        output_dim: int = len(STRATEGY_LABELS),
        hidden_dims: Optional[list[int]] = None,
    ) -> bytes:
        """Compile a neural network graph to WASM bytecode (mock)."""
        if hidden_dims is None:
            hidden_dims = [64, 32]

        start = time.time()
        layers_desc = [input_dim] + hidden_dims + [output_dim]

        # Build mock WASM module
        sections: list[bytes] = []

        # Type section: function signatures
        type_section = self._build_type_section(layers_desc)
        sections.append(type_section)

        # Function section
        func_section = self._build_function_section(len(layers_desc) - 1)
        sections.append(func_section)

        # Memory section
        mem_section = self._build_memory_section(layers_desc)
        sections.append(mem_section)

        # Code section (mock weights as bytecode)
        code_section = self._build_code_section(layers_desc)
        sections.append(code_section)

        # Assemble WASM binary
        body = b"".join(sections)
        wasm_binary = WASM_MAGIC + struct.pack("<I", WASM_VERSION) + body

        elapsed = time.time() - start
        checksum = hashlib.sha256(wasm_binary).hexdigest()[:16]

        self._compiled_modules[model_name] = wasm_binary
        self._compilation_log.append({
            "model": model_name,
            "target": self.target.value,
            "layers": layers_desc,
            "size_bytes": len(wasm_binary),
            "checksum": checksum,
            "compile_time_ms": elapsed * 1000,
            "timestamp": time.time(),
        })

        logger.info(
            "Compiled %s to WASM (%s): %d bytes, layers=%s",
            model_name, self.target.value, len(wasm_binary), layers_desc,
        )
        return wasm_binary

    def _build_type_section(self, layers: list[int]) -> bytes:
        """Mock type section encoding function signatures."""
        sig_count = len(layers) - 1
        data = struct.pack("<BH", 0x01, sig_count)
        for i in range(sig_count):
            data += struct.pack("<HH", layers[i], layers[i + 1])
        return data

    def _build_function_section(self, func_count: int) -> bytes:
        data = struct.pack("<BH", 0x03, func_count)
        for i in range(func_count):
            data += struct.pack("<H", i)
        return data

    def _build_memory_section(self, layers: list[int]) -> bytes:
        total_params = sum(
            layers[i] * layers[i + 1] + layers[i + 1]
            for i in range(len(layers) - 1)
        )
        pages = max(1, (total_params * 4) // 65536 + 1)
        return struct.pack("<BHH", 0x05, pages, pages * 2)

    def _build_code_section(self, layers: list[int]) -> bytes:
        """Generate mock code bytes representing layer computations."""
        code = b""
        for i in range(len(layers) - 1):
            n_weights = layers[i] * layers[i + 1]
            n_biases = layers[i + 1]
            # Mock: encode weight/bias counts as markers
            code += struct.pack("<II", n_weights, n_biases)
            # Simulated instruction bytes
            code += bytes([0x20, 0x00, 0x41, i & 0xFF]) * min(n_weights, 16)
        return struct.pack("<BI", 0x0A, len(code)) + code

    def get_module(self, model_name: str) -> Optional[bytes]:
        return self._compiled_modules.get(model_name)

    def get_compilation_log(self) -> list[dict[str, Any]]:
        return list(self._compilation_log)

    def get_model_info(self, model_name: str) -> Optional[dict[str, Any]]:
        for entry in reversed(self._compilation_log):
            if entry["model"] == model_name:
                return entry
        return None


# ============================================================
# ONNX.js Runner (Mock)
# ============================================================

class ONNXJSRunner:
    """Simulates ONNX.js inference as it would run in a browser environment."""

    def __init__(self, backend: InferenceBackend = InferenceBackend.ONNXJS) -> None:
        self.backend = backend
        self._model_loaded = False
        self._model_name = ""
        self._weights: dict[str, list[list[float]]] = {}
        self._biases: dict[str, list[float]] = {}
        self._inference_count = 0
        self._total_latency_ms = 0.0

    def load_model(self, metadata: ModelMetadata) -> bool:
        """Load model weights (mock: generates random-like deterministic weights)."""
        self._model_name = metadata.name
        input_dim = metadata.input_shape[-1]
        output_dim = metadata.output_shape[-1]
        hidden_dims = [64, 32]
        dims = [input_dim] + hidden_dims + [output_dim]

        for i in range(len(dims) - 1):
            layer_key = f"layer_{i}"
            rows = dims[i]
            cols = dims[i + 1]
            # Deterministic pseudo-weights using simple hash-based init
            scale = 1.0 / math.sqrt(rows)
            self._weights[layer_key] = [
                [
                    scale * math.sin((r * cols + c) * 0.1)
                    for c in range(cols)
                ]
                for r in range(rows)
            ]
            self._biases[layer_key] = [
                0.01 * math.cos(c * 0.3) for c in range(cols)
            ]

        self._model_loaded = True
        logger.info("ONNXJSRunner loaded model: %s (backend=%s)", metadata.name, self.backend.name)
        return True

    def infer(self, request: InferenceRequest) -> InferenceResult:
        """Run inference on input features."""
        start = time.time()
        if not self._model_loaded:
            return InferenceResult(
                request_id=request.request_id,
                strategy="unknown",
                confidence=0.0,
                backend=self.backend.name,
            )

        # Forward pass through layers
        activations = list(request.features)
        if len(activations) < len(FEATURE_NAMES):
            activations.extend([0.0] * (len(FEATURE_NAMES) - len(activations)))
        activations = activations[:len(FEATURE_NAMES)]

        layer_keys = sorted(self._weights.keys())
        for idx, layer_key in enumerate(layer_keys):
            w = self._weights[layer_key]
            b = self._biases[layer_key]
            out_dim = len(b)
            new_activations = []
            for j in range(out_dim):
                val = b[j]
                for i_idx, a in enumerate(activations):
                    if i_idx < len(w):
                        val += a * w[i_idx][j]
                # ReLU for hidden layers, keep raw for output
                if idx < len(layer_keys) - 1:
                    val = max(0.0, val)
                new_activations.append(val)
            activations = new_activations

        # Softmax on output
        probabilities = self._softmax(activations)

        # Map to strategy labels
        prob_dict: dict[str, float] = {}
        for i, label in enumerate(STRATEGY_LABELS):
            if i < len(probabilities):
                prob_dict[label] = round(probabilities[i], 6)
            else:
                prob_dict[label] = 0.0

        best_idx = max(range(len(probabilities)), key=lambda x: probabilities[x])
        best_strategy = STRATEGY_LABELS[best_idx] if best_idx < len(STRATEGY_LABELS) else "unknown"
        best_confidence = probabilities[best_idx]

        elapsed_ms = (time.time() - start) * 1000
        self._inference_count += 1
        self._total_latency_ms += elapsed_ms

        return InferenceResult(
            request_id=request.request_id,
            strategy=best_strategy,
            confidence=round(best_confidence, 6),
            all_probabilities=prob_dict,
            latency_ms=round(elapsed_ms, 3),
            backend=self.backend.name,
            timestamp=time.time(),
        )

    @staticmethod
    def _softmax(values: list[float]) -> list[float]:
        max_val = max(values) if values else 0.0
        exps = [math.exp(v - max_val) for v in values]
        total = sum(exps)
        if total == 0:
            return [1.0 / len(values)] * len(values)
        return [e / total for e in exps]

    def get_stats(self) -> dict[str, Any]:
        avg_latency = (
            self._total_latency_ms / self._inference_count
            if self._inference_count > 0 else 0.0
        )
        return {
            "model": self._model_name,
            "backend": self.backend.name,
            "loaded": self._model_loaded,
            "inference_count": self._inference_count,
            "avg_latency_ms": round(avg_latency, 3),
        }


# ============================================================
# WebWorker Simulator
# ============================================================

class WebWorkerPool:
    """Simulates browser WebWorker threads for offloading inference."""

    def __init__(self, num_workers: int = 2) -> None:
        self.num_workers = num_workers
        self._workers: list[dict[str, Any]] = []
        self._task_queue: list[dict[str, Any]] = []
        self._results: dict[str, InferenceResult] = {}
        self._lock = threading.Lock()
        self._next_worker = 0

        for i in range(num_workers):
            self._workers.append({
                "id": i,
                "busy": False,
                "tasks_completed": 0,
            })

    def submit_task(
        self, request: InferenceRequest, runner: ONNXJSRunner,
    ) -> InferenceResult:
        """Submit inference task to the next available worker."""
        worker = self._get_next_worker()
        with self._lock:
            worker["busy"] = True

        result = runner.infer(request)

        with self._lock:
            worker["busy"] = False
            worker["tasks_completed"] += 1
            self._results[request.request_id] = result

        return result

    def _get_next_worker(self) -> dict[str, Any]:
        worker = self._workers[self._next_worker % self.num_workers]
        self._next_worker += 1
        return worker

    def get_worker_stats(self) -> list[dict[str, Any]]:
        with self._lock:
            return [dict(w) for w in self._workers]

    def get_result(self, request_id: str) -> Optional[InferenceResult]:
        with self._lock:
            return self._results.get(request_id)


# ============================================================
# Web Model Server (REST API)
# ============================================================

class WebModelServer:
    """HTTP server that serves model metadata, health checks, and fallback inference."""

    def __init__(
        self,
        metadata: ModelMetadata,
        runner: ONNXJSRunner,
        host: str = DEFAULT_HOST,
        port: int = DEFAULT_PORT,
    ) -> None:
        self.metadata = metadata
        self.runner = runner
        self.host = host
        self.port = port
        self._server: Optional[HTTPServer] = None
        self._thread: Optional[threading.Thread] = None
        self._request_log: list[dict[str, Any]] = []
        self._running = False

    def _create_handler(self) -> type:
        server_ref = self

        class SC2Handler(BaseHTTPRequestHandler):
            def do_GET(self) -> None:
                if self.path == "/health":
                    self._respond_json({"status": "ok", "model": server_ref.metadata.name})
                elif self.path == "/metadata":
                    self._respond_json(server_ref.metadata.to_dict())
                elif self.path == "/stats":
                    self._respond_json(server_ref.runner.get_stats())
                elif self.path == "/labels":
                    self._respond_json({"labels": STRATEGY_LABELS})
                elif self.path == "/dashboard":
                    self._respond_html(server_ref._generate_dashboard_html())
                else:
                    self.send_error(404, "Not Found")

                server_ref._request_log.append({
                    "method": "GET", "path": self.path, "timestamp": time.time(),
                })

            def do_POST(self) -> None:
                if self.path == "/predict":
                    content_length = int(self.headers.get("Content-Length", 0))
                    body = self.rfile.read(content_length).decode("utf-8")
                    try:
                        data = json.loads(body)
                        req = InferenceRequest(
                            request_id=data.get("request_id", f"req_{time.time():.0f}"),
                            features=data.get("features", []),
                            race=data.get("race", "zerg"),
                            game_loop=data.get("game_loop", 0),
                            timestamp=time.time(),
                        )
                        if not req.validate():
                            self._respond_json(
                                {"error": f"Expected {len(FEATURE_NAMES)} features"}, 400,
                            )
                            return
                        result = server_ref.runner.infer(req)
                        self._respond_json(result.to_dict())
                    except json.JSONDecodeError:
                        self._respond_json({"error": "Invalid JSON"}, 400)
                else:
                    self.send_error(404, "Not Found")

                server_ref._request_log.append({
                    "method": "POST", "path": self.path, "timestamp": time.time(),
                })

            def _respond_json(self, data: Any, status: int = 200) -> None:
                body = json.dumps(data, indent=2).encode("utf-8")
                self.send_response(status)
                self.send_header("Content-Type", "application/json")
                self.send_header("Content-Length", str(len(body)))
                self.send_header("Access-Control-Allow-Origin", "*")
                self.end_headers()
                self.wfile.write(body)

            def _respond_html(self, html: str) -> None:
                body = html.encode("utf-8")
                self.send_response(200)
                self.send_header("Content-Type", "text/html; charset=utf-8")
                self.send_header("Content-Length", str(len(body)))
                self.end_headers()
                self.wfile.write(body)

            def log_message(self, fmt: str, *args: Any) -> None:
                logger.debug("HTTP: %s", fmt % args)

        return SC2Handler

    def _generate_dashboard_html(self) -> str:
        """Generate a simple SC2 strategy dashboard HTML page."""
        labels_js = json.dumps(STRATEGY_LABELS)
        features_js = json.dumps(FEATURE_NAMES)
        return f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <title>SC2 Strategy Predictor - Browser Inference</title>
    <style>
        body {{ font-family: monospace; background: #1a1a2e; color: #e0e0e0; padding: 20px; }}
        h1 {{ color: #00d4ff; }}
        .panel {{ background: #16213e; padding: 16px; margin: 10px 0; border-radius: 8px; }}
        .bar {{ height: 20px; background: #0f3460; margin: 4px 0; border-radius: 4px; }}
        .bar-fill {{ height: 100%; background: #00d4ff; border-radius: 4px; transition: width 0.3s; }}
        button {{ background: #533483; color: white; border: none; padding: 10px 20px;
                 cursor: pointer; border-radius: 4px; margin: 4px; }}
        button:hover {{ background: #e94560; }}
        #result {{ font-size: 1.2em; color: #00ff88; }}
    </style>
</head>
<body>
    <h1>SC2 Strategy Predictor</h1>
    <div class="panel">
        <h3>Model: {self.metadata.name} v{self.metadata.version}</h3>
        <p>Backend: ONNX.js/WASM | Labels: {len(STRATEGY_LABELS)}</p>
    </div>
    <div class="panel">
        <h3>Quick Predict</h3>
        <button onclick="predictRush()">Early Rush</button>
        <button onclick="predictMacro()">Macro Game</button>
        <button onclick="predictLate()">Late Game</button>
        <div id="result"></div>
    </div>
    <div class="panel" id="bars"></div>
    <script>
    const LABELS = {labels_js};
    const FEATURES = {features_js};
    async function predict(features) {{
        const resp = await fetch('/predict', {{
            method: 'POST',
            headers: {{'Content-Type': 'application/json'}},
            body: JSON.stringify({{features: features, race: 'zerg', game_loop: 3000}})
        }});
        const data = await resp.json();
        document.getElementById('result').textContent =
            'Strategy: ' + data.strategy + ' (' + (data.confidence * 100).toFixed(1) + '%)';
        renderBars(data.all_probabilities || {{}});
    }}
    function renderBars(probs) {{
        let html = '<h3>Probabilities</h3>';
        for (const label of LABELS) {{
            const pct = ((probs[label] || 0) * 100).toFixed(1);
            html += '<div>' + label + ': ' + pct + '%</div>';
            html += '<div class="bar"><div class="bar-fill" style="width:' + pct + '%"></div></div>';
        }}
        document.getElementById('bars').innerHTML = html;
    }}
    function predictRush() {{ predict([200,50,30,46,8,16,1,1,1500,1,5,1,150,0,2,90]); }}
    function predictMacro() {{ predict([1000,500,120,150,40,55,3,2,8000,1,30,2,180,4,6,200]); }}
    function predictLate() {{ predict([2000,1500,190,200,80,66,4,3,15000,1,70,3,200,8,10,300]); }}
    </script>
</body>
</html>"""

    def start(self) -> bool:
        """Start the HTTP server in a background thread."""
        try:
            handler_cls = self._create_handler()
            self._server = HTTPServer((self.host, self.port), handler_cls)
            self._running = True
            self._thread = threading.Thread(target=self._server.serve_forever, daemon=True)
            self._thread.start()
            logger.info("WebModelServer started on http://%s:%d", self.host, self.port)
            return True
        except Exception as exc:
            logger.error("Failed to start server: %s", exc)
            return False

    def stop(self) -> None:
        if self._server:
            self._server.shutdown()
            self._running = False
            logger.info("WebModelServer stopped")

    def get_request_log(self) -> list[dict[str, Any]]:
        return list(self._request_log)

    def is_running(self) -> bool:
        return self._running


# ============================================================
# Browser Inference Client
# ============================================================

class BrowserInferenceClient:
    """Client that simulates browser-side inference with WASM/ONNX.js fallback."""

    def __init__(self, server_url: str = f"http://localhost:{DEFAULT_PORT}") -> None:
        self.server_url = server_url
        self._runner: Optional[ONNXJSRunner] = None
        self._worker_pool: Optional[WebWorkerPool] = None
        self._wasm_module: Optional[bytes] = None
        self._metadata: Optional[ModelMetadata] = None
        self._history: list[InferenceResult] = []

    def initialize(
        self,
        metadata: ModelMetadata,
        wasm_module: Optional[bytes] = None,
        num_workers: int = 2,
        backend: InferenceBackend = InferenceBackend.ONNXJS,
    ) -> bool:
        """Initialize client-side inference engine."""
        self._metadata = metadata
        self._wasm_module = wasm_module
        self._runner = ONNXJSRunner(backend=backend)
        self._runner.load_model(metadata)
        self._worker_pool = WebWorkerPool(num_workers=num_workers)
        logger.info(
            "BrowserInferenceClient initialized: model=%s backend=%s workers=%d",
            metadata.name, backend.name, num_workers,
        )
        return True

    def predict(self, features: list[float], race: str = "zerg", game_loop: int = 0) -> InferenceResult:
        """Run client-side prediction using WebWorker pool."""
        if self._runner is None or self._worker_pool is None:
            return InferenceResult(strategy="uninitialized", confidence=0.0)

        request = InferenceRequest(
            request_id=f"browser_{len(self._history)}",
            features=features,
            race=race,
            game_loop=game_loop,
            timestamp=time.time(),
        )
        result = self._worker_pool.submit_task(request, self._runner)
        self._history.append(result)
        return result

    def predict_from_game_state(
        self,
        minerals: int, vespene: int,
        supply_used: int, supply_cap: int,
        army_count: int, worker_count: int,
        base_count: int = 1, tech_level: int = 1,
        game_loop: int = 0, enemy_race: str = "zerg",
        enemy_army_estimate: int = 0, enemy_base_count: int = 1,
        apm: float = 150.0, upgrades_count: int = 0,
        production_facilities: int = 3, expansion_timing: float = 150.0,
    ) -> InferenceResult:
        """Convenience method: build feature vector from game state values."""
        features = [
            float(minerals), float(vespene),
            float(supply_used), float(supply_cap),
            float(army_count), float(worker_count),
            float(base_count), float(tech_level),
            float(game_loop), float(RACE_ENCODING.get(enemy_race.lower(), 3)),
            float(enemy_army_estimate), float(enemy_base_count),
            float(apm), float(upgrades_count),
            float(production_facilities), float(expansion_timing),
        ]
        return self.predict(features, race=enemy_race, game_loop=game_loop)

    def get_history(self) -> list[dict[str, Any]]:
        return [r.to_dict() for r in self._history]

    def get_worker_stats(self) -> list[dict[str, Any]]:
        if self._worker_pool is None:
            return []
        return self._worker_pool.get_worker_stats()

    def get_runner_stats(self) -> dict[str, Any]:
        if self._runner is None:
            return {}
        return self._runner.get_stats()


# ============================================================
# Demo
# ============================================================

def demo() -> None:
    """Demonstrate web browser inference pipeline for SC2 strategy prediction."""
    logging.basicConfig(level=logging.INFO, format="%(levelname)s | %(message)s")
    print("=" * 60)
    print(" Phase 641: Web Browser Inference (ONNX.js/WASM) - Demo")
    print("=" * 60)

    # --- Model metadata ---
    metadata = ModelMetadata(
        name="sc2_strategy_v2",
        version="2.1.0",
        quantized=False,
    )
    print(f"\n[1] Model: {metadata.name} v{metadata.version}")
    print(f"  Input:  {metadata.input_shape}  ({len(FEATURE_NAMES)} features)")
    print(f"  Output: {metadata.output_shape}  ({len(STRATEGY_LABELS)} strategies)")

    # --- WASM compilation ---
    print("\n[2] WASM Compilation")
    compiler = WASMCompiler(target=CompilationTarget.WASM_SIMD)
    wasm_binary = compiler.compile_model(metadata.name, hidden_dims=[64, 32])
    info = compiler.get_model_info(metadata.name)
    print(f"  Target: {compiler.target.value}")
    print(f"  Binary size: {len(wasm_binary)} bytes")
    if info:
        print(f"  Compile time: {info['compile_time_ms']:.2f} ms")
        print(f"  Checksum: {info['checksum']}")

    # --- ONNX.js runner ---
    print("\n[3] ONNX.js Runner")
    runner = ONNXJSRunner(backend=InferenceBackend.ONNXJS)
    runner.load_model(metadata)

    test_features = [400.0, 200.0, 60.0, 86.0, 20.0, 30.0, 2.0, 1.0,
                     4000.0, 1.0, 15.0, 1.0, 160.0, 2.0, 4.0, 150.0]
    req = InferenceRequest(request_id="test_001", features=test_features, race="zerg", game_loop=4000)
    result = runner.infer(req)
    print(f"  Strategy: {result.strategy} (confidence: {result.confidence:.4f})")
    print(f"  Latency: {result.latency_ms:.3f} ms")
    print(f"  Top predictions:")
    sorted_probs = sorted(result.all_probabilities.items(), key=lambda x: -x[1])
    for label, prob in sorted_probs[:5]:
        bar = "#" * int(prob * 40)
        print(f"    {label:<16} {prob:.4f} {bar}")

    # --- WebWorker pool ---
    print("\n[4] WebWorker Pool")
    pool = WebWorkerPool(num_workers=3)
    scenarios = [
        ("early_rush", [200, 50, 30, 46, 8, 16, 1, 1, 1500, 1, 5, 1, 150, 0, 2, 90]),
        ("mid_macro",  [800, 400, 100, 130, 35, 50, 2, 2, 7000, 1, 25, 2, 175, 3, 5, 180]),
        ("late_army",  [1500, 1200, 185, 200, 75, 60, 4, 3, 14000, 1, 60, 3, 195, 7, 9, 280]),
    ]
    for name, feats in scenarios:
        r = InferenceRequest(
            request_id=name, features=[float(f) for f in feats], race="zerg",
        )
        res = pool.submit_task(r, runner)
        print(f"  {name:<12} -> {res.strategy:<16} ({res.confidence:.4f})")

    worker_stats = pool.get_worker_stats()
    for ws in worker_stats:
        print(f"  Worker {ws['id']}: {ws['tasks_completed']} tasks completed")

    # --- Browser client ---
    print("\n[5] BrowserInferenceClient")
    client = BrowserInferenceClient()
    client.initialize(metadata, wasm_module=wasm_binary, num_workers=2)

    game_states = [
        {"minerals": 300, "vespene": 100, "supply_used": 40, "supply_cap": 60,
         "army_count": 12, "worker_count": 22, "game_loop": 2500, "enemy_race": "terran"},
        {"minerals": 1200, "vespene": 800, "supply_used": 150, "supply_cap": 180,
         "army_count": 55, "worker_count": 55, "game_loop": 10000, "enemy_race": "protoss"},
        {"minerals": 2500, "vespene": 2000, "supply_used": 195, "supply_cap": 200,
         "army_count": 90, "worker_count": 66, "game_loop": 18000, "enemy_race": "zerg"},
    ]
    for gs in game_states:
        res = client.predict_from_game_state(**gs)
        print(f"  Loop {gs['game_loop']:>6} vs {gs['enemy_race']:<8} -> "
              f"{res.strategy:<16} ({res.confidence:.4f})")

    # --- Runner stats ---
    print("\n[6] Runner Stats")
    stats = runner.get_stats()
    for k, v in stats.items():
        print(f"  {k}: {v}")

    # --- Client history ---
    print(f"\n[7] Client inference history: {len(client.get_history())} entries")
    client_workers = client.get_worker_stats()
    for ws in client_workers:
        print(f"  Worker {ws['id']}: {ws['tasks_completed']} tasks")

    print(f"\n[8] Dashboard available at: http://localhost:{DEFAULT_PORT}/dashboard")
    print("  (Server not started in demo mode to avoid port binding)")

    print("\n[OK] Demo complete.")


if __name__ == "__main__":
    demo()

# Phase 641: Web Deploy registered
