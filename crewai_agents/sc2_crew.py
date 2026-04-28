# Phase 412: CrewAI - SC2 Agent Crew
# CrewAI agent crew for collaborative SC2 bot strategy management

import json
from typing import Optional

from crewai import Agent, Crew, Process, Task
from crewai.tools import tool
from langchain_anthropic import ChatAnthropic

# ============================================================
# LLM
# ============================================================

claude_llm = ChatAnthropic(
    model="claude-3-haiku-20240307",
    anthropic_api_key="YOUR_ANTHROPIC_KEY",
    temperature=0.3,
)

# ============================================================
# Tools (crewai @tool decorator)
# ============================================================


@tool("analyze_game_state")
def analyze_game_state_tool(game_state_json: str) -> str:
    """Analyze the current SC2 game state from JSON input.
    Input: JSON with minerals, vespene, supply_used, supply_cap, game_loop, enemy_race.
    Returns: structured analysis of economy, threats, and phase."""
    state = json.loads(game_state_json)
    minute = state.get("game_loop", 0) / 22.4 / 60
    phase = "early" if minute < 5 else "mid" if minute < 12 else "late"

    mineral_sat = "sufficient" if state.get("minerals", 0) > 300 else "low"
    supply_pct = state.get("supply_used", 0) / max(state.get("supply_cap", 1), 1)

    return json.dumps(
        {
            "phase": phase,
            "game_minute": round(minute, 1),
            "economy_status": mineral_sat,
            "supply_blocked": supply_pct > 0.92,
            "supply_pct": round(supply_pct * 100, 1),
            "recommended_workers": (
                66 if phase == "late" else 44 if phase == "mid" else 20
            ),
        }
    )


@tool("suggest_strategy")
def suggest_strategy_tool(matchup: str, phase: str, army_supply: int) -> str:
    """Suggest the optimal strategy for the given SC2 matchup and game phase.
    Input: matchup (ZvT/ZvP/ZvZ), phase (early/mid/late), army_supply.
    Returns: strategy recommendation with unit composition."""
    strategies = {
        "ZvT_early": "Speedling expand, deny scouting, prepare roach warren",
        "ZvT_mid": "Roach-Hydra with +1/+1, attack at 9 min with 12R+8H",
        "ZvT_late": "Brood Lord + Infestor + Corruptor vs mech, Ultra+ling vs bio",
        "ZvP_early": "Safe 3-hatch opener, roach warren for defense",
        "ZvP_mid": "Roach-Ravager-Hydra, deny forcefield, corruptors for colossus",
        "ZvP_late": "Zerg deathball: Ultra+BL+Infestor, deny 4th base",
        "ZvZ_early": "Pool-first or standard 3-hatch, match zergling production",
        "ZvZ_mid": "Mutalisk race - get 12+ mutas before engaging",
        "ZvZ_late": "Brood Lord control, deny bases with spine crawlers",
    }
    key = f"{matchup}_{phase}"
    return json.dumps(
        {
            "strategy": strategies.get(key, "Macro up and scout more"),
            "army_priority": "attack" if army_supply >= 40 else "build_up",
            "attack_threshold_supply": 40,
        }
    )


@tool("optimize_build_order")
def optimize_build_order_tool(enemy_race: str, opener: str) -> str:
    """Generate an optimized build order for the given enemy race and opener style.
    Input: enemy_race (Zerg/Terran/Protoss), opener (fast_expand/pool_first/hatch_first).
    Returns: step-by-step build order."""
    builds = {
        ("Terran", "hatch_first"): [
            "17 Hatch",
            "17 Gas",
            "16 Pool",
            "21 Hatch",
            "Speedling",
            "Roach Warren 4:30",
        ],
        ("Protoss", "pool_first"): [
            "16 Pool",
            "18 Hatch",
            "18 Gas x2",
            "Roach Warren 4:00",
            "Lair 5:00",
        ],
        ("Zerg", "hatch_first"): [
            "17 Hatch",
            "17 Gas",
            "16 Pool",
            "Zergling speed",
            "3rd hatch 5:00",
        ],
    }
    key = (enemy_race, opener)
    steps = builds.get(key, ["17 Hatch", "17 Gas", "16 Pool", "Standard macro"])
    return json.dumps({"build_order": steps, "vs": enemy_race, "opener": opener})


@tool("coordinate_attack")
def coordinate_attack_tool(
    army_supply: int, game_minute: float, enemy_base_x: float, enemy_base_y: float
) -> str:
    """Coordinate an army attack with timing and positioning.
    Input: army_supply, game_minute, enemy base coordinates.
    Returns: attack order with rally point and timing."""
    if army_supply < 30:
        return json.dumps(
            {"action": "wait", "reason": "Army too small", "min_supply": 30}
        )

    attack_type = (
        "timing_push"
        if game_minute < 10
        else "all_in" if game_minute < 15 else "deathball"
    )
    return json.dumps(
        {
            "action": "attack",
            "type": attack_type,
            "target": {"x": enemy_base_x, "y": enemy_base_y},
            "army_supply": army_supply,
            "timing": f"{game_minute:.1f} min",
            "formation": "surround" if attack_type == "deathball" else "frontal",
        }
    )


# ============================================================
# Agents
# ============================================================

senior_strategist = Agent(
    role="Senior SC2 Strategist",
    goal="Analyze the overall game state and determine the winning macro strategy for the Zerg bot",
    backstory="""You are a Grandmaster-level SC2 strategist specializing in Zerg.
    You have deep knowledge of all three matchups (ZvT, ZvP, ZvZ) and can identify
    the best strategic approach based on the current game state, enemy composition,
    and tech progression. You coordinate the entire crew.""",
    verbose=True,
    allow_delegation=True,
    tools=[analyze_game_state_tool, suggest_strategy_tool],
    llm=claude_llm,
)

economy_analyst = Agent(
    role="Economy Analyst",
    goal="Maximize resource efficiency and worker saturation for the SC2 bot",
    backstory="""You are a specialist in SC2 Zerg macro economics.
    You ensure optimal drone production, base timing, and resource management.
    You know exactly how many workers to build at each phase and when to cut drones.""",
    verbose=True,
    allow_delegation=False,
    tools=[analyze_game_state_tool, optimize_build_order_tool],
    llm=claude_llm,
)

scout_coordinator = Agent(
    role="Scout Coordinator",
    goal="Track enemy movements, tech paths, and attack timings",
    backstory="""You are responsible for Zerg intelligence gathering.
    Using overlords, overseers, and zerglings you maintain map vision.
    You identify enemy army composition, tech buildings, and predict attacks.""",
    verbose=True,
    allow_delegation=False,
    tools=[analyze_game_state_tool],
    llm=claude_llm,
)

combat_director = Agent(
    role="Combat Director",
    goal="Execute optimal army compositions and attack timings for the Zerg bot",
    backstory="""You are the SC2 combat specialist who decides when to attack,
    what units to build, and how to micro the army. You know all the key timing
    windows and army compositions for each matchup.""",
    verbose=True,
    allow_delegation=False,
    tools=[suggest_strategy_tool, coordinate_attack_tool],
    llm=claude_llm,
)

# ============================================================
# Tasks
# ============================================================


def create_tasks(game_state_json: str) -> list:
    analyze_game = Task(
        description=f"""Analyze the current SC2 game state: {game_state_json}
        Use the analyze_game_state tool to evaluate economy, supply, and phase.
        Identify the game phase and primary threats.""",
        agent=senior_strategist,
        expected_output="Structured game analysis with phase, threats, and economy status",
    )

    suggest_strategy = Task(
        description="""Based on the game analysis, suggest the optimal Zerg strategy.
        Use the suggest_strategy tool with the matchup and phase from the analysis.
        Provide clear strategic direction for the entire crew.""",
        agent=senior_strategist,
        expected_output="Clear strategy recommendation with unit composition and attack timing",
        context=[analyze_game],
    )

    optimize_build = Task(
        description="""Create an optimized build order for the current game situation.
        Use the optimize_build_order tool to generate specific build steps.
        Ensure the build order aligns with the suggested strategy.""",
        agent=economy_analyst,
        expected_output="Step-by-step build order with supply counts and timing",
        context=[suggest_strategy],
    )

    coordinate_attack = Task(
        description="""Determine the optimal attack timing and coordinates.
        Use the coordinate_attack tool based on current army supply and game minute.
        Specify rally points and formation type.""",
        agent=combat_director,
        expected_output="Attack order with timing, coordinates, and formation",
        context=[suggest_strategy],
    )

    return [analyze_game, suggest_strategy, optimize_build, coordinate_attack]


# ============================================================
# Crew
# ============================================================


def run_sc2_crew(game_state: dict) -> str:
    game_state_json = json.dumps(game_state)
    tasks = create_tasks(game_state_json)

    crew = Crew(
        agents=[senior_strategist, economy_analyst, scout_coordinator, combat_director],
        tasks=tasks,
        process=Process.sequential,
        verbose=True,
    )

    result = crew.kickoff()
    return result


# ============================================================
# Main
# ============================================================


def main():
    print("[CrewAI] SC2 strategy crew initializing...")

    game_state = {
        "minerals": 380,
        "vespene": 175,
        "supply_used": 44,
        "supply_cap": 54,
        "game_loop": 5376,
        "enemy_race": "Terran",
        "workers": 32,
        "army_supply": 24,
    }

    result = run_sc2_crew(game_state)
    print(f"\n[CrewAI] Final crew decision:\n{result}")


if __name__ == "__main__":
    main()
