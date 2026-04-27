# Phase 411: AutoGen - SC2 Multi-Agent Strategy Framework
# Microsoft AutoGen multi-agent collaboration for SC2 decision making

import json
from typing import Annotated, Optional

import autogen
from autogen import (
    AssistantAgent,
    GroupChat,
    GroupChatManager,
    UserProxyAgent,
    config_list_from_json,
)

# ============================================================
# LLM Configuration
# ============================================================

config_list = [
    {
        "model": "claude-3-haiku-20240307",
        "api_key": "YOUR_ANTHROPIC_KEY",
        "api_type": "anthropic",
    }
]

llm_config = {
    "config_list": config_list,
    "temperature": 0.3,
    "timeout": 120,
}

# ============================================================
# Tool Functions
# ============================================================


def analyze_game_state(
    minerals: Annotated[int, "Current mineral count"],
    vespene: Annotated[int, "Current vespene count"],
    supply_used: Annotated[int, "Supply used"],
    supply_cap: Annotated[int, "Supply cap"],
    game_loop: Annotated[int, "Current game loop"],
    enemy_race: Annotated[str, "Enemy race"],
) -> str:
    """Analyze the current SC2 game state and return a structured assessment."""
    minute = game_loop / 22.4 / 60
    economy_score = min(1.0, (minerals + vespene * 1.5) / 1000)
    supply_pct = supply_used / max(supply_cap, 1)

    return json.dumps(
        {
            "game_minute": round(minute, 1),
            "economy_score": round(economy_score, 2),
            "supply_pressure": supply_pct > 0.9,
            "phase": "early" if minute < 5 else "mid" if minute < 12 else "late",
            "enemy_race": enemy_race,
            "minerals": minerals,
            "vespene": vespene,
        }
    )


def recommend_action(
    phase: Annotated[str, "Game phase: early/mid/late"],
    enemy_race: Annotated[str, "Enemy race"],
    supply_used: Annotated[int, "Current supply"],
    economy_score: Annotated[float, "Economy score 0-1"],
) -> str:
    """Recommend the next strategic action for the SC2 bot."""
    recommendations = {
        (
            "early",
            "Terran",
        ): "Scout with overlord, build spine crawler at natural, prepare zergling speed",
        (
            "early",
            "Protoss",
        ): "Scout for 4-gate or stargate, build roach warren defensively",
        (
            "early",
            "Zerg",
        ): "Check for pool timing, match unit production, prepare speedlings",
        (
            "mid",
            "Terran",
        ): "Go roach-hydra with +1/+1 attack, deny third base, attack at 9 min",
        (
            "mid",
            "Protoss",
        ): "Roach-ravager-hydra with corruptors for colossus, fungal forcefield",
        (
            "mid",
            "Zerg",
        ): "Muta-ling play or roach-hydra, control map with overlord vision",
        (
            "late",
            "Terran",
        ): "Brood lord + infestor + corruptor vs mech, ultra-ling vs bio",
        ("late", "Protoss"): "Zerg deathball: ultra + BL + infestor, deny third/fourth",
        ("late", "Zerg"): "Hive tech: ultra or BL depending on enemy composition",
    }
    key = (phase, enemy_race)
    action = recommendations.get(key, "Expand and macro up, drone to 70+ workers")
    return json.dumps({"recommended_action": action, "phase": phase, "vs": enemy_race})


def build_order_advisor(
    enemy_race: Annotated[str, "Enemy race: Zerg/Terran/Protoss"],
    style: Annotated[str, "Play style: aggressive/defensive/economic"],
) -> str:
    """Provide a complete build order for the given matchup and style."""
    build_orders = {
        ("Terran", "aggressive"): [
            "12 Pool",
            "14 Hatchery",
            "16 Gas",
            "18 Zergling speed",
            "20 Hatchery",
            "4:00 Roach Warren",
            "6:00 attack with 12 roaches+lings",
        ],
        ("Terran", "economic"): [
            "17 Hatchery",
            "17 Gas",
            "16 Pool",
            "21 Hatchery",
            "Queen x3",
            "Roach Warren at 5:00",
            "Macro up to 70 drones",
        ],
        ("Protoss", "defensive"): [
            "17 Hatchery",
            "16 Pool",
            "17 Gas x2",
            "Roach Warren at 4:30",
            "Lair at 5:30",
            "Hydra Den at 6:30",
            "Ravager research",
        ],
    }
    key = (enemy_race, style)
    steps = build_orders.get(key, ["17 Hatch", "16 Pool", "Standard macro opener"])
    return json.dumps(
        {"build_order": steps, "matchup": f"Zv{enemy_race[0]}", "style": style}
    )


# ============================================================
# Agents
# ============================================================


def create_strategist_agent() -> AssistantAgent:
    return AssistantAgent(
        name="StrategistAgent",
        llm_config=llm_config,
        system_message="""You are the head SC2 strategist for a Zerg bot.
        Your role: analyze the overall game situation, set high-level strategy,
        and coordinate other agents. Call analyze_game_state and recommend_action tools.
        Be concise. Always end with STRATEGY_DECIDED: <decision>.""",
    )


def create_economy_agent() -> AssistantAgent:
    return AssistantAgent(
        name="EconomyAgent",
        llm_config=llm_config,
        system_message="""You are the SC2 economy specialist.
        Monitor minerals, vespene, and worker saturation.
        Advise on when to take new bases, how many drones to make, gas timing.
        Output: ECONOMY_STATUS: <status> and WORKER_TARGET: <number>.""",
    )


def create_scout_agent() -> AssistantAgent:
    return AssistantAgent(
        name="ScoutAgent",
        llm_config=llm_config,
        system_message="""You are the SC2 scouting coordinator.
        Analyze enemy unit counts, tech paths, and threat levels.
        Advise on when the enemy will attack and what composition they are building.
        Output: THREAT_LEVEL: <low/medium/high> and ENEMY_COMPOSITION: <units>.""",
    )


def create_combat_agent() -> AssistantAgent:
    return AssistantAgent(
        name="CombatAgent",
        llm_config=llm_config,
        system_message="""You are the SC2 combat director.
        Decide unit composition, attack timing, and micro strategies.
        Use build_order_advisor to recommend optimal army composition.
        Output: ATTACK_TIMING: <game_minute> and ARMY_COMPOSITION: <units>.""",
    )


# ============================================================
# Group Chat
# ============================================================


def create_sc2_group_chat(game_state: dict) -> str:
    """Run a multi-agent group chat to decide SC2 strategy."""

    strategist = create_strategist_agent()
    economy = create_economy_agent()
    scout = create_scout_agent()
    combat = create_combat_agent()

    # User proxy to trigger conversation
    user_proxy = UserProxyAgent(
        name="SC2BotProxy",
        human_input_mode="NEVER",
        max_consecutive_auto_reply=3,
        code_execution_config=False,
    )

    # Register tools
    for agent in [strategist, economy, scout, combat]:
        autogen.register_function(
            analyze_game_state,
            caller=agent,
            executor=user_proxy,
            description="Analyze current game state",
        )
        autogen.register_function(
            recommend_action,
            caller=agent,
            executor=user_proxy,
            description="Get recommended strategic action",
        )
        autogen.register_function(
            build_order_advisor,
            caller=agent,
            executor=user_proxy,
            description="Get build order recommendation",
        )

    group_chat = GroupChat(
        agents=[user_proxy, strategist, economy, scout, combat],
        messages=[],
        max_round=8,
        speaker_selection_method="round_robin",
    )

    manager = GroupChatManager(groupchat=group_chat, llm_config=llm_config)

    message = f"""
    Current SC2 game state:
    - Minerals: {game_state['minerals']}, Vespene: {game_state['vespene']}
    - Supply: {game_state['supply_used']}/{game_state['supply_cap']}
    - Game loop: {game_state['game_loop']} ({game_state['game_loop']/22.4/60:.1f} min)
    - Enemy race: {game_state['enemy_race']}
    - Workers: {game_state['workers']}

    Analyze this situation and provide coordinated strategy recommendations.
    """

    user_proxy.initiate_chat(manager, message=message)
    return "Group chat complete"


# ============================================================
# Main
# ============================================================


def main():
    print("[AutoGen] SC2 multi-agent strategy framework initializing...")

    game_state = {
        "minerals": 450,
        "vespene": 200,
        "supply_used": 48,
        "supply_cap": 54,
        "game_loop": 4032,
        "enemy_race": "Terran",
        "workers": 36,
    }

    result = create_sc2_group_chat(game_state)
    print(f"\n[AutoGen] {result}")


if __name__ == "__main__":
    main()
