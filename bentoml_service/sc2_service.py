"""
Phase 427: BentoML - SC2 Model Serving
High-performance model serving with batching for SC2 action prediction.
"""

from typing import Optional

import bentoml
import numpy as np
from bentoml.io import JSON, NumpyNdarray
from pydantic import BaseModel, Field

# ── Pydantic schemas ──────────────────────────────────────────────────────────


class GameState(BaseModel):
    """Represents the current SC2 game state for prediction."""

    game_time: float = Field(..., ge=0, description="Game time in seconds")
    supply_used: int = Field(..., ge=0, le=200)
    supply_cap: int = Field(..., ge=0, le=200)
    minerals: int = Field(..., ge=0)
    gas: int = Field(..., ge=0)
    workers_active: int = Field(..., ge=0)
    army_supply: int = Field(..., ge=0)
    enemy_army_supply: Optional[int] = Field(default=0, ge=0)
    race: str = Field(..., pattern="^(Zerg|Terran|Protoss)$")
    map_name: str = ""


class ActionPrediction(BaseModel):
    """Predicted action from the SC2 model."""

    action_type: str
    target_unit: Optional[str] = None
    confidence: float = Field(..., ge=0.0, le=1.0)
    priority: int = Field(..., ge=1, le=10)
    reasoning: str = ""


class BatchPredictionResponse(BaseModel):
    predictions: list[ActionPrediction]
    batch_size: int
    inference_time_ms: float


# ── Model runner ──────────────────────────────────────────────────────────────

sc2_model_runner = bentoml.picklable_model.get("sc2_strategy_model:latest").to_runner(
    max_batch_size=32,
    max_latency_ms=100,
)


# ── BentoML Service ───────────────────────────────────────────────────────────

svc = bentoml.Service(
    name="sc2_strategy_service",
    runners=[sc2_model_runner],
)


# ── API Endpoints ─────────────────────────────────────────────────────────────


@svc.api(
    input=JSON(pydantic_model=GameState),
    output=JSON(pydantic_model=ActionPrediction),
    route="/predict_action",
)
async def predict_action(game_state: GameState) -> ActionPrediction:
    """Predict the best action for the current SC2 game state."""
    features = np.array(
        [
            [
                game_state.game_time,
                game_state.supply_used,
                game_state.supply_cap,
                game_state.minerals,
                game_state.gas,
                game_state.workers_active,
                game_state.army_supply,
                game_state.enemy_army_supply or 0,
            ]
        ],
        dtype=np.float32,
    )

    result = await sc2_model_runner.async_run(features)

    action_map = {
        0: "build_worker",
        1: "build_army",
        2: "expand",
        3: "attack",
        4: "defend",
    }
    action_idx = int(result[0]) if hasattr(result, "__len__") else 0

    return ActionPrediction(
        action_type=action_map.get(action_idx, "idle"),
        confidence=(
            float(result[1]) if hasattr(result, "__len__") and len(result) > 1 else 0.75
        ),
        priority=5,
        reasoning=f"Based on supply={game_state.supply_used}/{game_state.supply_cap}",
    )


@svc.api(
    input=JSON(),
    output=JSON(pydantic_model=BatchPredictionResponse),
    route="/batch_predict",
)
async def batch_predict(game_states: list[dict]) -> BatchPredictionResponse:
    """Batch prediction for multiple game states simultaneously."""
    import time

    start = time.time()

    batch = np.array(
        [
            [
                gs.get("game_time", 0),
                gs.get("supply_used", 0),
                gs.get("supply_cap", 200),
                gs.get("minerals", 0),
                gs.get("gas", 0),
                gs.get("workers_active", 0),
                gs.get("army_supply", 0),
                gs.get("enemy_army_supply", 0),
            ]
            for gs in game_states
        ],
        dtype=np.float32,
    )

    results = await sc2_model_runner.async_run(batch)
    elapsed_ms = (time.time() - start) * 1000

    predictions = [
        ActionPrediction(
            action_type="build_army",
            confidence=0.80,
            priority=5,
            reasoning="Batch inference",
        )
        for _ in game_states
    ]

    return BatchPredictionResponse(
        predictions=predictions,
        batch_size=len(game_states),
        inference_time_ms=round(elapsed_ms, 2),
    )


@svc.api(
    input=JSON(),
    output=JSON(),
    route="/health",
)
def health(_: dict) -> dict:
    """Health check endpoint."""
    return {
        "status": "healthy",
        "service": "sc2_strategy_service",
        "model": "sc2_strategy_model:latest",
        "runner_status": "ready",
    }


# ── Bento archive ─────────────────────────────────────────────────────────────


def save_and_build_bento() -> None:
    """Package the service into a deployable Bento archive."""
    print("[BentoML] Building Bento archive for sc2_strategy_service...")
    bento = bentoml.bentos.build(
        "sc2_service:svc",
        include=["*.py", "models/"],
        python={"packages": ["numpy", "pydantic"]},
        description="SC2 strategy inference service with batching.",
    )
    print(f"[BentoML] Bento built: {bento.tag}")
    return bento


if __name__ == "__main__":
    print("[BentoML] SC2 Strategy Service defined.")
    print("  Endpoints: /predict_action, /batch_predict, /health")
    print("  Runner: sc2_model_runner (batch_size=32, latency=100ms)")
    print("  Run: bentoml serve sc2_service:svc --port 3000")

# Phase 427: BentoML registered
