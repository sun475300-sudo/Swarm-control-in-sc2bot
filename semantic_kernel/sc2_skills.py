# Phase 414: Semantic Kernel - SC2 AI Planning
# Microsoft Semantic Kernel for goal-directed SC2 strategy execution

import asyncio
import json
from typing import Annotated

import semantic_kernel as sk
from semantic_kernel.connectors.ai.anthropic import AnthropicChatCompletion
from semantic_kernel.contents import ChatHistory
from semantic_kernel.core_plugins import (
    MathPlugin,
    TextPlugin,
)
from semantic_kernel.functions import kernel_function
from semantic_kernel.planners.function_calling_stepwise_planner import (
    FunctionCallingStepwisePlanner,
    FunctionCallingStepwisePlannerOptions,
)

# ============================================================
# Plugins (Native Functions)
# ============================================================


class StrategyPlugin:
    """SC2 strategy analysis and recommendation plugin."""

    @kernel_function(
        name="analyze_matchup", description="Analyze a SC2 matchup and return strategy"
    )
    def analyze_matchup(
        self,
        player_race: Annotated[str, "Player race: Zerg/Terran/Protoss"],
        enemy_race: Annotated[str, "Enemy race: Zerg/Terran/Protoss"],
        game_phase: Annotated[str, "Game phase: early/mid/late"],
    ) -> str:
        strategies = {
            ("Zerg", "Terran", "mid"): "Roach-Hydra +1/+1 timing push at 9 min",
            (
                "Zerg",
                "Protoss",
                "mid",
            ): "Roach-Ravager-Hydra with Corruptors for Colossus",
            ("Zerg", "Zerg", "mid"): "Mutalisk race to control map, deny third",
            ("Zerg", "Terran", "late"): "Brood Lord + Infestor + Corruptor deathball",
            ("Zerg", "Protoss", "late"): "Ultra + BL + Infestor, deny fourth base",
            ("Zerg", "Zerg", "late"): "Brood Lord macro, secure fourth and fifth base",
        }
        key = (player_race, enemy_race, game_phase)
        return strategies.get(key, f"Standard {player_race} macro vs {enemy_race}")

    @kernel_function(
        name="get_counter_unit",
        description="Get the counter unit for an enemy composition",
    )
    def get_counter_unit(
        self,
        enemy_units: Annotated[str, "Comma-separated enemy unit types"],
    ) -> str:
        counters = {
            "Marine": "Baneling (splash damage one-shots marines)",
            "Tank": "Brood Lord (out-ranges tank, attacks from distance)",
            "Colossus": "Corruptor (air unit, dedicated colossus counter)",
            "Immortal": "Zergling + Surround (overwhelm with numbers)",
            "Stalker": "Roach (tanky, efficient vs gateway units)",
            "Carrier": "Corruptor + Hydralisk (anti-air focus fire)",
        }
        units = [u.strip() for u in enemy_units.split(",")]
        results = {u: counters.get(u, "Roach-Hydra general composition") for u in units}
        return json.dumps(results)


class EconomyPlugin:
    """SC2 economy optimization plugin."""

    @kernel_function(
        name="calculate_drone_target", description="Calculate optimal drone count"
    )
    def calculate_drone_target(
        self,
        bases: Annotated[int, "Number of active bases"],
        game_phase: Annotated[str, "Game phase: early/mid/late"],
    ) -> str:
        targets = {"early": 20, "mid": 40, "late": 66}
        base_target = bases * 16 + (bases * 3 if bases >= 2 else 0)
        phase_target = targets.get(game_phase, 40)
        optimal = min(base_target, phase_target)
        return json.dumps(
            {
                "optimal_workers": optimal,
                "bases": bases,
                "phase": game_phase,
                "gas_workers": bases * 3 if game_phase != "early" else 0,
            }
        )

    @kernel_function(
        name="check_supply_block", description="Check if supply is blocked"
    )
    def check_supply_block(
        self,
        supply_used: Annotated[int, "Supply currently used"],
        supply_cap: Annotated[int, "Supply cap"],
    ) -> str:
        is_blocked = supply_used >= supply_cap - 2
        pct = supply_used / max(supply_cap, 1) * 100
        return json.dumps(
            {
                "supply_blocked": is_blocked,
                "supply_pct": round(pct, 1),
                "overlords_needed": (
                    max(0, (supply_used - supply_cap + 10) // 8 + 1)
                    if is_blocked
                    else 0
                ),
            }
        )


class CombatPlugin:
    """SC2 combat management plugin."""

    @kernel_function(
        name="evaluate_attack_timing", description="Evaluate whether to attack now"
    )
    def evaluate_attack_timing(
        self,
        army_supply: Annotated[int, "Player army supply"],
        enemy_army_supply: Annotated[int, "Estimated enemy army supply"],
        game_minute: Annotated[float, "Current game minute"],
    ) -> str:
        supply_advantage = army_supply / max(enemy_army_supply, 1)
        timing_windows = [
            (6.0, 8.0, 30, "6-minute timing push"),
            (9.0, 11.0, 40, "9-minute roach-hydra push"),
            (14.0, 17.0, 60, "14-minute hive timing"),
        ]

        for start, end, min_supply, label in timing_windows:
            if start <= game_minute <= end and army_supply >= min_supply:
                should_attack = supply_advantage >= 1.0
                return json.dumps(
                    {
                        "should_attack": should_attack,
                        "window": label,
                        "reason": (
                            "Timing window + supply advantage"
                            if should_attack
                            else "Timing window but supply deficit"
                        ),
                    }
                )

        return json.dumps(
            {
                "should_attack": supply_advantage >= 1.5,
                "window": "standard",
                "reason": "Attack when supply advantage >= 1.5x",
            }
        )

    @kernel_function(
        name="get_army_composition", description="Get recommended army composition"
    )
    def get_army_composition(
        self,
        matchup: Annotated[str, "Matchup: ZvT/ZvP/ZvZ"],
        game_phase: Annotated[str, "Game phase: early/mid/late"],
    ) -> str:
        compositions = {
            ("ZvT", "mid"): {"Roach": 12, "Hydralisk": 8, "Queen": 2},
            ("ZvT", "late"): {"BroodLord": 6, "Infestor": 4, "Corruptor": 8},
            ("ZvP", "mid"): {"Roach": 10, "Ravager": 4, "Hydralisk": 8, "Corruptor": 4},
            ("ZvP", "late"): {"Ultralisk": 4, "BroodLord": 4, "Infestor": 4},
            ("ZvZ", "mid"): {"Mutalisk": 14, "Zergling": 20},
            ("ZvZ", "late"): {"BroodLord": 8, "Infestor": 4, "Corruptor": 6},
        }
        key = (matchup, game_phase)
        comp = compositions.get(key, {"Roach": 10, "Hydralisk": 8})
        return json.dumps(comp)


# ============================================================
# Semantic Functions (Prompt Templates)
# ============================================================

STRATEGY_SUMMARY_PROMPT = """
You are an SC2 Zerg strategist. Given this game situation, write a 2-sentence strategy summary.

Game Phase: {{$game_phase}}
Matchup: {{$matchup}}
Economy: {{$minerals}}m / {{$vespene}}v
Army: {{$army_supply}} supply vs enemy {{$enemy_supply}} supply

Strategy summary:
"""

# ============================================================
# Kernel Setup
# ============================================================


def create_kernel() -> sk.Kernel:
    kernel = sk.Kernel()

    # Add Anthropic chat service
    kernel.add_service(
        AnthropicChatCompletion(
            ai_model_id="claude-3-haiku-20240307",
            api_key="YOUR_ANTHROPIC_KEY",
            service_id="anthropic-claude",
        )
    )

    # Register plugins
    kernel.add_plugin(StrategyPlugin(), plugin_name="Strategy")
    kernel.add_plugin(EconomyPlugin(), plugin_name="Economy")
    kernel.add_plugin(CombatPlugin(), plugin_name="Combat")

    return kernel


# ============================================================
# Planner: Goal-directed execution
# ============================================================


async def run_strategic_planner(kernel: sk.Kernel, goal: str) -> str:
    options = FunctionCallingStepwisePlannerOptions(
        max_iterations=5,
        max_tokens=2048,
    )
    planner = FunctionCallingStepwisePlanner(
        service_id="anthropic-claude", options=options
    )
    result = await planner.invoke(kernel, goal)
    return result.final_answer


# ============================================================
# Main
# ============================================================


async def main():
    print("[Semantic Kernel] SC2 AI planning system starting...")
    kernel = create_kernel()

    # Direct plugin calls
    strategy_plugin = kernel.plugins["Strategy"]
    matchup_result = await kernel.invoke(
        strategy_plugin["analyze_matchup"],
        player_race="Zerg",
        enemy_race="Terran",
        game_phase="mid",
    )
    print(f"[SK] Matchup analysis: {matchup_result}")

    economy_plugin = kernel.plugins["Economy"]
    drone_result = await kernel.invoke(
        economy_plugin["calculate_drone_target"], bases=3, game_phase="mid"
    )
    print(f"[SK] Drone target: {drone_result}")

    combat_plugin = kernel.plugins["Combat"]
    attack_result = await kernel.invoke(
        combat_plugin["evaluate_attack_timing"],
        army_supply=42,
        enemy_army_supply=30,
        game_minute=9.5,
    )
    print(f"[SK] Attack eval: {attack_result}")

    # Goal-directed planner
    goal = """
    Game state: Zerg vs Terran, 9 minutes in, 44 supply army, enemy has ~30 supply army.
    Minerals: 380, Vespene: 160. 3 bases.
    Goal: Determine if I should attack now and what composition to use.
    """
    print(f"\n[SK] Running planner for goal...")
    # answer = await run_strategic_planner(kernel, goal)
    # print(f"[SK] Planner answer: {answer}")
    print("[SK] Planner configured and ready (requires valid API key to execute)")


if __name__ == "__main__":
    asyncio.run(main())
