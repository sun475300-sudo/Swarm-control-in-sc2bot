"""
Phase 435: LiteLLM - Unified LLM Gateway for SC2 AI
Single interface for OpenAI, Anthropic, Gemini with fallback and cost tracking.
"""

import asyncio
import json
import time
from dataclasses import dataclass, field

import litellm
from litellm import Router, acompletion, completion
from litellm.utils import ModelResponse

# ── LiteLLM configuration ─────────────────────────────────────────────────────

litellm.set_verbose = False
litellm.drop_params = True  # Ignore unsupported params per model

# Cost-per-million-token tracking (USD approximate)
MODEL_COSTS = {
    "claude-3-5-sonnet-20241022": {"input": 3.0, "output": 15.0},
    "gpt-4o": {"input": 2.5, "output": 10.0},
    "gemini/gemini-1.5-pro": {"input": 1.25, "output": 5.0},
    "gpt-4o-mini": {"input": 0.15, "output": 0.60},
}


# ── Fallback router configuration ─────────────────────────────────────────────


def build_sc2_router() -> Router:
    """Build LiteLLM router with fallback chain for SC2 strategy queries."""
    model_list = [
        {
            "model_name": "primary",
            "litellm_params": {
                "model": "claude-3-5-sonnet-20241022",
                "max_tokens": 512,
                "temperature": 0.7,
            },
        },
        {
            "model_name": "fallback-1",
            "litellm_params": {
                "model": "gpt-4o",
                "max_tokens": 512,
                "temperature": 0.7,
            },
        },
        {
            "model_name": "fallback-2",
            "litellm_params": {
                "model": "gemini/gemini-1.5-pro",
                "max_tokens": 512,
                "temperature": 0.7,
            },
        },
        {
            "model_name": "economy",
            "litellm_params": {
                "model": "gpt-4o-mini",
                "max_tokens": 256,
                "temperature": 0.5,
            },
        },
    ]

    return Router(
        model_list=model_list,
        fallbacks=[{"primary": ["fallback-1", "fallback-2", "economy"]}],
        retry_after=2,
        num_retries=3,
    )


# ── Cost tracker ──────────────────────────────────────────────────────────────


@dataclass
class CostTracker:
    total_cost_usd: float = 0.0
    calls_by_model: dict = field(default_factory=dict)
    tokens_by_model: dict = field(default_factory=dict)

    def record(self, model: str, input_tokens: int, output_tokens: int) -> float:
        costs = MODEL_COSTS.get(model, {"input": 1.0, "output": 4.0})
        cost = (
            input_tokens * costs["input"] + output_tokens * costs["output"]
        ) / 1_000_000
        self.total_cost_usd += cost
        self.calls_by_model[model] = self.calls_by_model.get(model, 0) + 1
        self.tokens_by_model[model] = (
            self.tokens_by_model.get(model, 0) + input_tokens + output_tokens
        )
        return cost

    def summary(self) -> dict:
        return {
            "total_cost_usd": round(self.total_cost_usd, 6),
            "calls_by_model": self.calls_by_model,
            "tokens_by_model": self.tokens_by_model,
        }


# ── SC2 Gateway ───────────────────────────────────────────────────────────────


class SC2LLMGateway:
    """Unified LLM gateway for SC2 strategy queries."""

    SYSTEM_PROMPT = (
        "You are an elite StarCraft 2 strategy advisor. "
        "Provide concise, actionable tactical advice based on the game state. "
        "Focus on the next 30-60 seconds of optimal play."
    )

    def __init__(self):
        self.router = build_sc2_router()
        self.tracker = CostTracker()

    async def get_strategy(
        self,
        game_state: dict,
        model: str = "primary",
        use_fallback: bool = True,
    ) -> str:
        """Get SC2 strategy advice using the router with fallback."""
        prompt = (
            f"Game state: Race={game_state.get('race')} vs {game_state.get('opponent_race')}, "
            f"Time={game_state.get('game_time', 0):.0f}s, "
            f"Supply={game_state.get('supply_used')}/{game_state.get('supply_cap')}, "
            f"Minerals={game_state.get('minerals')}, Gas={game_state.get('gas')}. "
            f"Recommend best action:"
        )

        response: ModelResponse = await self.router.acompletion(
            model=model,
            messages=[
                {"role": "system", "content": self.SYSTEM_PROMPT},
                {"role": "user", "content": prompt},
            ],
        )

        actual_model = response.model
        usage = response.usage
        self.tracker.record(actual_model, usage.prompt_tokens, usage.completion_tokens)

        return response.choices[0].message.content

    async def batch_analyze_games(
        self,
        game_states: list[dict],
        model: str = "economy",
    ) -> list[str]:
        """Analyze multiple game states concurrently via async batch."""
        tasks = [self.get_strategy(gs, model=model) for gs in game_states]
        return await asyncio.gather(*tasks, return_exceptions=True)

    def get_cost_report(self) -> dict:
        return self.tracker.summary()


# ── Demo ──────────────────────────────────────────────────────────────────────

SAMPLE_GAME_STATES = [
    {
        "race": "Zerg",
        "opponent_race": "Terran",
        "game_time": 180,
        "supply_used": 30,
        "supply_cap": 36,
        "minerals": 400,
        "gas": 0,
    },
    {
        "race": "Zerg",
        "opponent_race": "Protoss",
        "game_time": 360,
        "supply_used": 70,
        "supply_cap": 84,
        "minerals": 200,
        "gas": 150,
    },
    {
        "race": "Zerg",
        "opponent_race": "Zerg",
        "game_time": 600,
        "supply_used": 120,
        "supply_cap": 150,
        "minerals": 600,
        "gas": 350,
    },
]

if __name__ == "__main__":
    print("[LiteLLM] SC2 LLM Gateway initialized.")
    print(
        f"  Fallback chain: claude-3-5-sonnet → gpt-4o → gemini-1.5-pro → gpt-4o-mini"
    )
    print(f"  Features: Cost tracking, async batch, automatic retry")
    print(f"\n[Sample batch: {len(SAMPLE_GAME_STATES)} game states]")
    for gs in SAMPLE_GAME_STATES:
        print(f"  {gs['race']} vs {gs['opponent_race']} @ {gs['game_time']}s")

# Phase 435: LiteLLM registered
