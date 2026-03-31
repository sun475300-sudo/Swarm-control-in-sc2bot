# Phase 413: LangGraph - SC2 Stateful Decision Workflow
# LangGraph stateful graph for SC2 game decision making with checkpointing

from langgraph.graph import StateGraph, START, END
from langgraph.checkpoint.memory import MemorySaver
from langchain_anthropic import ChatAnthropic
from langchain_core.messages import HumanMessage, AIMessage, SystemMessage
from typing import TypedDict, Annotated, Optional, Literal
import operator
import json

# ============================================================
# State: SC2GameState TypedDict
# ============================================================

class SC2GameState(TypedDict):
    # Game info
    game_id:      int
    game_loop:    int
    game_phase:   Literal["early", "mid", "late"]

    # Economy
    minerals:     int
    vespene:      int
    supply_used:  int
    supply_cap:   int
    worker_count: int

    # Combat
    army_supply:       int
    enemy_race:        str
    enemy_army_supply: int
    enemy_visible:     bool

    # Observations
    observations: Annotated[list[str], operator.add]

    # Analysis
    threats:     list[str]
    strategy:    str
    action_plan: list[str]

    # Reflection
    reflection:     str
    iteration:      int
    should_attack:  bool

    # Messages
    messages: Annotated[list, operator.add]

# ============================================================
# LLM
# ============================================================

llm = ChatAnthropic(model="claude-3-haiku-20240307", temperature=0.2)

# ============================================================
# Nodes
# ============================================================

def observe(state: SC2GameState) -> SC2GameState:
    """Collect and structure observations from the game environment."""
    minute = state["game_loop"] / 22.4 / 60
    obs = []

    # Economy observations
    if state["minerals"] > 600:
        obs.append("ALERT: Mineral float - spend faster")
    if state["supply_used"] >= state["supply_cap"] - 2:
        obs.append("ALERT: Supply blocked - build overlords")
    if state["worker_count"] < 16:
        obs.append("LOW WORKERS: Prioritize drone production")

    # Combat observations
    if state["enemy_visible"]:
        obs.append(f"Enemy visible: {state['enemy_army_supply']} supply army")
    if state["army_supply"] >= 40:
        obs.append(f"Army ready: {state['army_supply']} supply - consider attacking")

    # Phase detection
    if minute < 5:
        phase = "early"
    elif minute < 12:
        phase = "mid"
    else:
        phase = "late"

    return {
        **state,
        "game_phase": phase,
        "observations": obs,
        "messages": [HumanMessage(content=f"Game state at {minute:.1f} min: {json.dumps(obs)}")]
    }

def analyze(state: SC2GameState) -> SC2GameState:
    """Analyze observations to identify threats and opportunities."""
    system = SystemMessage(content="""You are an SC2 Zerg strategist.
    Analyze the game state observations and identify:
    1. Key threats (max 3)
    2. Strategic opportunities (max 3)
    Be concise. Format: THREATS: [...] OPPORTUNITIES: [...]""")

    obs_text = "\n".join(state["observations"])
    response = llm.invoke([system, HumanMessage(content=f"Observations:\n{obs_text}")])

    threats = []
    text = response.content
    if "supply blocked" in "\n".join(state["observations"]).lower():
        threats.append("Supply block imminent")
    if state["enemy_army_supply"] > state["army_supply"] * 1.3:
        threats.append("Enemy army larger - defend")
    if state["minerals"] > 600:
        threats.append("Economy inefficiency - mineral float")

    return {
        **state,
        "threats": threats,
        "messages": [AIMessage(content=response.content)],
    }

def plan(state: SC2GameState) -> SC2GameState:
    """Create an action plan based on analysis."""
    system = SystemMessage(content=f"""You are planning SC2 Zerg strategy.
    Phase: {state['game_phase']}, vs {state['enemy_race']}.
    Army: {state['army_supply']}, Enemy army: {state['enemy_army_supply']}.
    Create a 3-5 step action plan. Be specific and actionable.""")

    context = f"""
    Threats: {state['threats']}
    Phase: {state['game_phase']}
    Economy: {state['minerals']}m / {state['vespene']}v
    Supply: {state['supply_used']}/{state['supply_cap']}
    """
    response = llm.invoke([system, HumanMessage(content=context)])

    # Parse action plan from response
    plan_steps = []
    if "supply" in response.content.lower():
        plan_steps.append("Build overlords to avoid supply block")
    if state["worker_count"] < 40 and state["game_phase"] != "late":
        plan_steps.append(f"Drone up to {40 if state['game_phase'] == 'mid' else 66} workers")
    if state["army_supply"] >= 30 and state["game_phase"] in ("mid", "late"):
        plan_steps.append("Move army to center map for control")
    if state["minerals"] > 500:
        plan_steps.append("Spend minerals: add production buildings or expand")

    strategy = {
        ("early", "Terran"):  "Eco expand, roach warren prep",
        ("mid",   "Terran"):  "Roach-Hydra timing at 9 min",
        ("late",  "Terran"):  "Brood Lord + Infestor deathball",
        ("early", "Protoss"): "3-hatch opener, roach warren",
        ("mid",   "Protoss"): "Roach-Ravager-Hydra + corruptors",
        ("late",  "Protoss"): "Ultra-BL-Infestor, deny bases",
        ("early", "Zerg"):    "Match pool timing, speedlings",
        ("mid",   "Zerg"):    "Muta race or roach-hydra",
        ("late",  "Zerg"):    "Brood Lord macro",
    }.get((state["game_phase"], state["enemy_race"]), "Standard Zerg macro")

    return {
        **state,
        "strategy": strategy,
        "action_plan": plan_steps,
        "messages": [AIMessage(content=response.content)],
    }

def execute(state: SC2GameState) -> SC2GameState:
    """Execute the highest priority action from the plan."""
    if not state["action_plan"]:
        return {**state, "messages": [AIMessage(content="No actions to execute")]}

    priority_action = state["action_plan"][0]
    remaining       = state["action_plan"][1:]

    # Simulate action effect
    should_attack = (
        state["army_supply"] >= 40
        and state["game_phase"] in ("mid", "late")
        and state["enemy_army_supply"] < state["army_supply"] * 1.2
    )

    return {
        **state,
        "action_plan":  remaining,
        "should_attack": should_attack,
        "messages": [AIMessage(content=f"Executing: {priority_action}. Attack={should_attack}")],
    }

def reflect(state: SC2GameState) -> SC2GameState:
    """Reflect on decisions and update strategy for next iteration."""
    system = SystemMessage(content="""Briefly reflect on the SC2 strategy decisions made.
    Was the strategy appropriate? What would you do differently? Max 2 sentences.""")

    context = f"Strategy: {state['strategy']}. Threats: {state['threats']}. Attack: {state['should_attack']}"
    response = llm.invoke([system, HumanMessage(content=context)])

    return {
        **state,
        "reflection": response.content,
        "iteration":  state.get("iteration", 0) + 1,
        "messages":   [AIMessage(content=f"Reflection: {response.content}")],
    }

# ============================================================
# Conditional Edges
# ============================================================

def route_by_phase(state: SC2GameState) -> Literal["plan_mid_late", "plan_early"]:
    if state["game_phase"] in ("mid", "late"):
        return "plan_mid_late"
    return "plan_early"

def should_continue(state: SC2GameState) -> Literal["execute", END]:
    if state["action_plan"] and state["iteration"] < 3:
        return "execute"
    return END

# ============================================================
# Build Graph
# ============================================================

def build_sc2_graph() -> StateGraph:
    workflow = StateGraph(SC2GameState)

    # Add nodes
    workflow.add_node("observe",  observe)
    workflow.add_node("analyze",  analyze)
    workflow.add_node("plan",     plan)
    workflow.add_node("execute",  execute)
    workflow.add_node("reflect",  reflect)

    # Edges
    workflow.add_edge(START,      "observe")
    workflow.add_edge("observe",  "analyze")
    workflow.add_edge("analyze",  "plan")
    workflow.add_edge("plan",     "execute")
    workflow.add_edge("execute",  "reflect")
    workflow.add_conditional_edges("reflect", should_continue, {"execute": "execute", END: END})

    return workflow

# ============================================================
# Main
# ============================================================

def main():
    print("[LangGraph] Building SC2 decision workflow...")

    workflow  = build_sc2_graph()
    checkpointer = MemorySaver()
    app = workflow.compile(checkpointer=checkpointer)

    initial_state: SC2GameState = {
        "game_id":          42,
        "game_loop":        4480,
        "game_phase":       "mid",
        "minerals":         420,
        "vespene":          180,
        "supply_used":      44,
        "supply_cap":       54,
        "worker_count":     30,
        "army_supply":      26,
        "enemy_race":       "Terran",
        "enemy_army_supply": 20,
        "enemy_visible":    True,
        "observations":     [],
        "threats":          [],
        "strategy":         "",
        "action_plan":      [],
        "reflection":       "",
        "iteration":        0,
        "should_attack":    False,
        "messages":         [],
    }

    config = {"configurable": {"thread_id": "game-42"}}
    result = app.invoke(initial_state, config=config)

    print(f"\n=== SC2 Decision Result ===")
    print(f"Phase:       {result['game_phase']}")
    print(f"Strategy:    {result['strategy']}")
    print(f"Attack:      {result['should_attack']}")
    print(f"Reflection:  {result['reflection']}")
    print(f"Iterations:  {result['iteration']}")
    print("\n[LangGraph] Workflow complete with checkpointing enabled")

if __name__ == "__main__":
    main()
