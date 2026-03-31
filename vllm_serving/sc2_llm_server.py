"""
Phase 433: vLLM - High-Throughput SC2 Strategy LLM Server
PagedAttention-based serving for low-latency SC2 strategy recommendations.
"""

import asyncio
from typing import AsyncGenerator, Optional
from dataclasses import dataclass, field


# ── Request/Response schemas ──────────────────────────────────────────────────

@dataclass
class GameStateQuery:
    """SC2 game state query for strategy recommendation."""
    request_id: str
    game_time: float
    race: str
    opponent_race: str
    supply_used: int
    supply_cap: int
    minerals: int
    gas: int
    army_supply: int
    prompt: str = ""

    def to_prompt(self) -> str:
        return (
            f"[SC2 Strategy Advisor]\n"
            f"Matchup: {self.race} vs {self.opponent_race}\n"
            f"Game time: {self.game_time:.0f}s | Supply: {self.supply_used}/{self.supply_cap}\n"
            f"Economy: {self.minerals} minerals, {self.gas} gas\n"
            f"Army supply: {self.army_supply}\n"
            f"Recommend the best action for the next 30 seconds:"
        )


@dataclass
class StrategyResponse:
    """LLM-generated strategy recommendation."""
    request_id: str
    text: str
    tokens_generated: int
    finish_reason: str
    latency_ms: float


# ── vLLM engine wrapper ───────────────────────────────────────────────────────

class SC2LLMEngine:
    """
    Wraps vLLM's AsyncLLMEngine for SC2 strategy inference.
    Uses PagedAttention for efficient KV-cache management.
    """

    def __init__(
        self,
        model: str = "mistralai/Mistral-7B-Instruct-v0.2",
        max_model_len: int = 4096,
        tensor_parallel_size: int = 1,
        gpu_memory_utilization: float = 0.90,
    ):
        self.model = model
        self.max_model_len = max_model_len
        self._engine = None
        print(f"[vLLM] SC2LLMEngine configured: {model}")
        print(f"  max_model_len={max_model_len}, gpu_mem={gpu_memory_utilization}")

    def _build_engine(self):
        """Lazily initialize AsyncLLMEngine with PagedAttention."""
        from vllm import AsyncLLMEngine, AsyncEngineArgs
        args = AsyncEngineArgs(
            model=self.model,
            max_model_len=self.max_model_len,
            gpu_memory_utilization=0.90,
            enforce_eager=False,      # Use CUDA graphs for speed
            trust_remote_code=True,
        )
        self._engine = AsyncLLMEngine.from_engine_args(args)
        print(f"[vLLM] AsyncLLMEngine initialized with PagedAttention.")

    async def generate_strategy(
        self,
        query: GameStateQuery,
        max_tokens: int = 256,
        temperature: float = 0.7,
    ) -> AsyncGenerator[str, None]:
        """Stream strategy recommendation tokens for a game state query."""
        from vllm import SamplingParams
        import time

        if self._engine is None:
            self._build_engine()

        sampling_params = SamplingParams(
            temperature=temperature,
            max_tokens=max_tokens,
            top_p=0.95,
            stop=["</strategy>", "\n\n\n"],
        )

        prompt = query.to_prompt()
        start = time.time()

        async for output in self._engine.generate(prompt, sampling_params, query.request_id):
            for completion in output.outputs:
                yield completion.text

    async def batch_generate(
        self,
        queries: list[GameStateQuery],
        max_tokens: int = 128,
    ) -> list[StrategyResponse]:
        """
        Continuous batching: submit all queries concurrently.
        vLLM's scheduler handles dynamic batching with PagedAttention.
        """
        import time

        async def _single(q: GameStateQuery) -> StrategyResponse:
            text_chunks = []
            start = time.time()
            async for chunk in self.generate_strategy(q, max_tokens=max_tokens):
                text_chunks.append(chunk)
            return StrategyResponse(
                request_id=q.request_id,
                text="".join(text_chunks),
                tokens_generated=len("".join(text_chunks).split()),
                finish_reason="stop",
                latency_ms=(time.time() - start) * 1000,
            )

        return await asyncio.gather(*[_single(q) for q in queries])


# ── FastAPI server (vLLM compatible) ─────────────────────────────────────────

def build_fastapi_app(engine: SC2LLMEngine):
    """Build FastAPI app exposing SC2 strategy generation endpoints."""
    from fastapi import FastAPI
    from fastapi.responses import StreamingResponse
    import json

    app = FastAPI(title="SC2 Strategy LLM Server", version="1.0.0")

    @app.post("/v1/strategy")
    async def get_strategy(query: dict):
        game_query = GameStateQuery(
            request_id=query.get("request_id", "req_001"),
            game_time=query.get("game_time", 300),
            race=query.get("race", "Zerg"),
            opponent_race=query.get("opponent_race", "Terran"),
            supply_used=query.get("supply_used", 100),
            supply_cap=query.get("supply_cap", 150),
            minerals=query.get("minerals", 400),
            gas=query.get("gas", 200),
            army_supply=query.get("army_supply", 40),
        )

        async def token_stream():
            async for token in engine.generate_strategy(game_query):
                yield json.dumps({"token": token}) + "\n"

        return StreamingResponse(token_stream(), media_type="text/event-stream")

    @app.get("/health")
    def health():
        return {"status": "ok", "engine": engine.model}

    return app


# ── Entry point ───────────────────────────────────────────────────────────────

if __name__ == "__main__":
    print("[vLLM] SC2 LLM Server configuration:")
    print("  Engine: AsyncLLMEngine with PagedAttention")
    print("  Model: mistralai/Mistral-7B-Instruct-v0.2")
    print("  Features: Continuous batching, streaming, async generation")
    print("  Endpoints: POST /v1/strategy, GET /health")
    print("\nTo run: uvicorn sc2_llm_server:app --host 0.0.0.0 --port 8080")

    engine = SC2LLMEngine()
    sample_query = GameStateQuery(
        request_id="demo_001",
        game_time=300.0,
        race="Zerg",
        opponent_race="Terran",
        supply_used=80,
        supply_cap=100,
        minerals=350,
        gas=150,
        army_supply=30,
    )
    print(f"\n[Sample prompt]\n{sample_query.to_prompt()}")

# Phase 433: vLLM registered
