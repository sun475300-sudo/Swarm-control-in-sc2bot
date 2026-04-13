"""
Phase 437: Pydantic AI - SC2 Strategy Agent
Type-safe AI agent with tools and structured output for SC2 decision making.
"""

from pydantic import BaseModel, Field
from pydantic_ai import Agent, RunContext
from pydantic_ai.models.openai import OpenAIModel
from dataclasses import dataclass
from typing import Optional
import asyncio


# ── Dependency injection models ───────────────────────────────────────────────

@dataclass
class SC2GameDeps:
    """Injected game state dependencies for the SC2 agent."""
    game_time: float
    race: str
    opponent_race: str
    supply_used: int
    supply_cap: int
    minerals: int
    gas: int
    army_supply: int
    worker_count: int
    expansion_count: int
    map_name: str = "Unknown"
    player_mmr: int = 3000


# ── Structured output model ───────────────────────────────────────────────────

class ActionRecommendation(BaseModel):
    """Structured action recommendation from the SC2 agent."""
    primary_action: str = Field(..., description="The single most important action right now")
    action_category: str = Field(..., pattern="^(economy|military|tech|scouting|macro)$")
    urgency: str = Field(..., pattern="^(low|medium|high|critical)$")
    units_to_build: list[str] = Field(default_factory=list, description="Units to prioritize")
    buildings_to_construct: list[str] = Field(default_factory=list)
    confidence: float = Field(..., ge=0.0, le=1.0)
    explanation: str = Field(..., max_length=300)
    estimated_impact: str = Field(..., description="Expected outcome if action is followed")


# ── Agent definition ──────────────────────────────────────────────────────────

sc2_agent = Agent(
    model=OpenAIModel("gpt-4o-mini"),
    result_type=ActionRecommendation,
    system_prompt=(
        "You are an elite StarCraft 2 strategy coach. "
        "Analyze the provided game state and recommend the single most impactful action. "
        "Be specific and tactical. Consider the current supply, economy, and army size. "
        "Provide structured recommendations that a bot can execute."
    ),
    deps_type=SC2GameDeps,
)


# ── Agent tools ───────────────────────────────────────────────────────────────

@sc2_agent.tool
async def analyze_game_state(ctx: RunContext[SC2GameDeps]) -> str:
    """Summarize the current SC2 game state for strategic analysis."""
    deps = ctx.deps
    supply_pct = deps.supply_used / max(deps.supply_cap, 1) * 100
    eco_score = (deps.minerals + deps.gas * 1.5) / 1000
    return (
        f"Game state summary:\n"
        f"- Matchup: {deps.race} vs {deps.opponent_race} on {deps.map_name}\n"
        f"- Time: {deps.game_time:.0f}s | Supply: {deps.supply_used}/{deps.supply_cap} ({supply_pct:.0f}%)\n"
        f"- Economy: {deps.minerals}m / {deps.gas}g | Eco score: {eco_score:.1f}\n"
        f"- Workers: {deps.worker_count} | Expansions: {deps.expansion_count}\n"
        f"- Army supply: {deps.army_supply} | Player MMR: {deps.player_mmr}"
    )


@sc2_agent.tool
async def get_unit_stats(ctx: RunContext[SC2GameDeps], unit_name: str) -> str:
    """Get stats for a specific SC2 unit."""
    UNIT_DB = {
        "Zergling": {"cost": "25m", "supply": 0.5, "role": "harassment/swarm", "counter": "Banelings vs bio"},
        "Roach": {"cost": "75m/25g", "supply": 2, "role": "ground assault", "counter": "Immortals, Marauders"},
        "Hydralisk": {"cost": "100m/50g", "supply": 2, "role": "anti-air/ground", "counter": "Banelings, Storms"},
        "Marine": {"cost": "50m", "supply": 1, "role": "general purpose", "counter": "Banelings, Zealots"},
        "Stalker": {"cost": "125m/50g", "supply": 2, "role": "ranged/anti-air", "counter": "Immortals"},
    }
    stats = UNIT_DB.get(unit_name, {"note": "Unit not in local database."})
    return f"{unit_name}: {stats}"


@sc2_agent.tool
async def recommend_action(
    ctx: RunContext[SC2GameDeps],
    focus: str = "balanced",
) -> str:
    """Generate a raw action recommendation based on current game phase."""
    deps = ctx.deps
    game_phase = "early" if deps.game_time < 300 else "mid" if deps.game_time < 600 else "late"
    supply_blocked = deps.supply_used >= deps.supply_cap

    if supply_blocked:
        return f"CRITICAL: Supply blocked at {deps.supply_used}/{deps.supply_cap}! Build Overlords immediately."

    workers_needed = max(0, 22 * deps.expansion_count - deps.worker_count)
    if workers_needed:
        return f"Economy: Build {workers_needed} more workers (have {deps.worker_count}, target {22 * deps.expansion_count})"

    if game_phase == "early" and deps.minerals > 400:
        return "Macro: Expand to new base - floating too many minerals in early game."

    return f"Continue {focus} play in {game_phase} game. Army supply: {deps.army_supply}."


# ── Runner ────────────────────────────────────────────────────────────────────

async def run_sc2_agent(game_state: SC2GameDeps) -> ActionRecommendation:
    """Run the SC2 agent with a game state and return structured recommendation."""
    result = await sc2_agent.run(
        user_prompt=(
            f"Analyze my {game_state.race} vs {game_state.opponent_race} game "
            f"at {game_state.game_time:.0f} seconds and give me the best action."
        ),
        deps=game_state,
    )
    return result.data


async def demo():
    """Demo the SC2 Pydantic AI agent."""
    game = SC2GameDeps(
        game_time=240.0,
        race="Zerg",
        opponent_race="Terran",
        supply_used=34,
        supply_cap=36,
        minerals=600,
        gas=0,
        army_supply=8,
        worker_count=20,
        expansion_count=2,
        map_name="Berlingrad",
        player_mmr=4200,
    )
    print("[Pydantic AI] Running SC2 agent...")
    print(f"  Deps: {game.race} vs {game.opponent_race} @ {game.game_time}s")
    try:
        rec = await run_sc2_agent(game)
        print(f"\n[ActionRecommendation]")
        print(f"  Primary: {rec.primary_action}")
        print(f"  Category: {rec.action_category} | Urgency: {rec.urgency}")
        print(f"  Confidence: {rec.confidence:.0%}")
        print(f"  Explanation: {rec.explanation}")
    except Exception as e:
        print(f"  (API call skipped in demo: {e})")


if __name__ == "__main__":
    asyncio.run(demo())

# Phase 437: Pydantic AI registered
