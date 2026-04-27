"""
Phase 623: AutoGPT Strategic Planner for SC2
Autonomous GPT-based strategic planning agent for SC2.
Implements a Thought-Action-Observation loop with self-prompting,
sub-goal generation, long-term memory, and mid-game adaptation.
"""

from __future__ import annotations

import json
import time
import uuid
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Callable, Dict, List, Optional, Tuple


# ── Enums & Constants ────────────────────────────────────────────────────────


class ThoughtType(Enum):
    STRATEGIC = "strategic"
    TACTICAL = "tactical"
    ECONOMIC = "economic"
    SCOUTING = "scouting"
    DEFENSIVE = "defensive"
    REFLECTIVE = "reflective"


class ActionType(Enum):
    BUILD_ORDER = "build_order"
    ARMY_MOVE = "army_move"
    TECH_SWITCH = "tech_switch"
    EXPAND = "expand"
    SCOUT = "scout"
    DEFEND = "defend"
    ALL_IN = "all_in"
    RETREAT = "retreat"
    UPGRADE = "upgrade"


class PlanStatus(Enum):
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


# ── Core Data Classes ────────────────────────────────────────────────────────


@dataclass
class Thought:
    """A reasoning step in the agent's thought process."""

    thought_id: str = field(default_factory=lambda: uuid.uuid4().hex[:12])
    thought_type: ThoughtType = ThoughtType.STRATEGIC
    content: str = ""
    reasoning: str = ""
    confidence: float = 0.5
    timestamp: float = field(default_factory=time.time)
    sub_goals: List[str] = field(default_factory=list)
    parent_thought_id: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.thought_id,
            "type": self.thought_type.value,
            "content": self.content,
            "reasoning": self.reasoning,
            "confidence": self.confidence,
            "sub_goals": self.sub_goals,
        }


@dataclass
class Action:
    """An action decided upon by the planner."""

    action_id: str = field(default_factory=lambda: uuid.uuid4().hex[:12])
    action_type: ActionType = ActionType.BUILD_ORDER
    description: str = ""
    parameters: Dict[str, Any] = field(default_factory=dict)
    priority: int = 5  # 1 = highest, 10 = lowest
    thought_id: str = ""  # Link back to the originating thought
    status: PlanStatus = PlanStatus.PENDING
    timestamp: float = field(default_factory=time.time)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.action_id,
            "type": self.action_type.value,
            "description": self.description,
            "parameters": self.parameters,
            "priority": self.priority,
            "status": self.status.value,
        }


@dataclass
class Observation:
    """An observation resulting from executing an action or from game state."""

    observation_id: str = field(default_factory=lambda: uuid.uuid4().hex[:12])
    action_id: Optional[str] = None
    success: bool = True
    details: str = ""
    game_state_snapshot: Dict[str, Any] = field(default_factory=dict)
    lessons_learned: List[str] = field(default_factory=list)
    timestamp: float = field(default_factory=time.time)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.observation_id,
            "action_id": self.action_id,
            "success": self.success,
            "details": self.details,
            "lessons": self.lessons_learned,
        }


# ── Long-Term Memory ────────────────────────────────────────────────────────


class LongTermMemory:
    """Persists strategic learnings across games."""

    def __init__(self) -> None:
        self._learnings: List[Dict[str, Any]] = []
        self._matchup_strategies: Dict[str, List[str]] = {}
        self._failed_strategies: List[str] = []
        self._successful_patterns: List[Dict[str, Any]] = []

    def store_learning(
        self,
        matchup: str,
        learning: str,
        outcome: str,
        game_time: float,
    ) -> None:
        """Store a strategic learning from a game."""
        entry = {
            "matchup": matchup,
            "learning": learning,
            "outcome": outcome,
            "game_time": game_time,
            "timestamp": time.time(),
        }
        self._learnings.append(entry)

        if outcome == "win":
            self._successful_patterns.append(entry)
            self._matchup_strategies.setdefault(matchup, []).append(learning)
        elif outcome == "loss":
            self._failed_strategies.append(learning)

    def recall_strategies(self, matchup: str, limit: int = 5) -> List[str]:
        """Recall successful strategies for a given matchup."""
        strategies = self._matchup_strategies.get(matchup, [])
        return strategies[-limit:]

    def recall_failures(self, limit: int = 5) -> List[str]:
        """Recall failed strategies to avoid repeating them."""
        return self._failed_strategies[-limit:]

    def get_all_learnings(self) -> List[Dict[str, Any]]:
        return list(self._learnings)

    @property
    def total_learnings(self) -> int:
        return len(self._learnings)

    def to_context_string(self, matchup: str) -> str:
        """Build a context string for the planner from memory."""
        parts: List[str] = []
        successes = self.recall_strategies(matchup)
        if successes:
            parts.append(f"Winning strategies for {matchup}: " + "; ".join(successes))
        failures = self.recall_failures()
        if failures:
            parts.append("Avoid: " + "; ".join(failures))
        return " | ".join(parts) if parts else "No prior memory for this matchup."


# ── Game State Representation ────────────────────────────────────────────────


@dataclass
class SC2GameState:
    """Snapshot of the current SC2 game state for planning."""

    game_time: float = 0.0
    minerals: int = 0
    vespene: int = 0
    supply_used: int = 0
    supply_cap: int = 0
    worker_count: int = 0
    army_supply: int = 0
    base_count: int = 1
    player_race: str = "Zerg"
    opponent_race: str = "Terran"
    army_composition: Dict[str, int] = field(default_factory=dict)
    enemy_army_estimate: Dict[str, int] = field(default_factory=dict)
    tech_buildings: List[str] = field(default_factory=list)
    upgrades: List[str] = field(default_factory=list)
    threat_level: float = 0.0  # 0.0 - 1.0

    @property
    def matchup(self) -> str:
        r1 = self.player_race[0]
        r2 = self.opponent_race[0]
        return f"{r1}v{r2}"

    @property
    def game_phase(self) -> str:
        if self.game_time < 300:
            return "early"
        elif self.game_time < 720:
            return "mid"
        return "late"

    @property
    def economy_score(self) -> float:
        return min(1.0, (self.minerals + self.vespene * 1.5) / 2000)

    def to_prompt(self) -> str:
        """Convert game state to a text prompt for reasoning."""
        return (
            f"Race: {self.player_race} vs {self.opponent_race} | "
            f"Phase: {self.game_phase} ({self.game_time:.0f}s) | "
            f"Supply: {self.supply_used}/{self.supply_cap} | "
            f"Workers: {self.worker_count} | Bases: {self.base_count} | "
            f"Army: {json.dumps(self.army_composition)} | "
            f"Enemy estimate: {json.dumps(self.enemy_army_estimate)} | "
            f"Resources: {self.minerals}m {self.vespene}g | "
            f"Threat: {self.threat_level:.1f} | "
            f"Tech: {', '.join(self.tech_buildings) or 'none'}"
        )


# ── Strategy Templates (rule-based reasoning engine) ────────────────────────

_STRATEGY_RULES: Dict[str, Callable[[SC2GameState], Optional[Thought]]] = {}


def _register_rule(name: str) -> Callable:
    def decorator(fn: Callable[[SC2GameState], Optional[Thought]]) -> Callable:
        _STRATEGY_RULES[name] = fn
        return fn

    return decorator


@_register_rule("expand_check")
def _rule_expand(state: SC2GameState) -> Optional[Thought]:
    """Check if expansion is needed."""
    if state.minerals > 500 and state.base_count < 4 and state.threat_level < 0.5:
        return Thought(
            thought_type=ThoughtType.ECONOMIC,
            content="High minerals with low threat. Should expand.",
            reasoning=f"Minerals={state.minerals}, bases={state.base_count}, "
            f"threat={state.threat_level:.1f}",
            confidence=0.8,
            sub_goals=["Take next expansion", "Add workers to saturate"],
        )
    return None


@_register_rule("army_production")
def _rule_army(state: SC2GameState) -> Optional[Thought]:
    """Check if army needs reinforcement."""
    if state.supply_cap > 0:
        army_ratio = state.army_supply / state.supply_cap
    else:
        army_ratio = 0.0
    if army_ratio < 0.4 and state.game_time > 300:
        return Thought(
            thought_type=ThoughtType.TACTICAL,
            content="Army supply is low for this stage. Need more units.",
            reasoning=f"Army ratio={army_ratio:.2f}, game_time={state.game_time:.0f}s",
            confidence=0.75,
            sub_goals=["Produce army units", "Check production capacity"],
        )
    return None


@_register_rule("scout_needed")
def _rule_scout(state: SC2GameState) -> Optional[Thought]:
    """Check if scouting is needed."""
    if not state.enemy_army_estimate and state.game_time > 120:
        return Thought(
            thought_type=ThoughtType.SCOUTING,
            content="No enemy intel. Scouting is critical.",
            reasoning="Enemy army estimate is empty after 2 minutes.",
            confidence=0.9,
            sub_goals=["Send overlord/zergling to scout", "Check enemy base count"],
        )
    return None


@_register_rule("threat_response")
def _rule_threat(state: SC2GameState) -> Optional[Thought]:
    """Respond to high threat level."""
    if state.threat_level > 0.7:
        return Thought(
            thought_type=ThoughtType.DEFENSIVE,
            content="High threat detected. Prepare defenses.",
            reasoning=f"Threat level {state.threat_level:.1f} exceeds 0.7 threshold.",
            confidence=0.85,
            sub_goals=[
                "Position army at choke",
                "Build static defense",
                "Pull workers if needed",
            ],
        )
    return None


@_register_rule("tech_progression")
def _rule_tech(state: SC2GameState) -> Optional[Thought]:
    """Check tech progression."""
    if state.game_time > 420 and len(state.tech_buildings) < 2:
        return Thought(
            thought_type=ThoughtType.STRATEGIC,
            content="Tech is behind schedule. Need to add tech structures.",
            reasoning=f"Only {len(state.tech_buildings)} tech buildings at "
            f"{state.game_time:.0f}s.",
            confidence=0.7,
            sub_goals=["Build next tech structure", "Start key upgrades"],
        )
    return None


# ── AutoGPT Planner ─────────────────────────────────────────────────────────


class AutoGPTPlanner:
    """
    Autonomous strategic planner using a Thought-Action-Observation loop.
    Self-prompts to generate sub-goals, executes, evaluates, and iterates.
    """

    def __init__(
        self,
        memory: Optional[LongTermMemory] = None,
        max_iterations: int = 10,
    ) -> None:
        self.memory = memory or LongTermMemory()
        self.max_iterations = max_iterations
        self._thought_history: List[Thought] = []
        self._action_queue: List[Action] = []
        self._observation_log: List[Observation] = []
        self._current_goals: List[str] = []
        self._iteration_count: int = 0

    def think(self, state: SC2GameState) -> Thought:
        """Generate a thought based on the current game state and memory."""
        # Consult long-term memory
        memory_context = self.memory.to_context_string(state.matchup)

        # Apply rule-based reasoning
        thoughts: List[Thought] = []
        for name, rule_fn in _STRATEGY_RULES.items():
            thought = rule_fn(state)
            if thought is not None:
                thoughts.append(thought)

        if not thoughts:
            thoughts.append(
                Thought(
                    thought_type=ThoughtType.STRATEGIC,
                    content="Stable situation. Continue current plan.",
                    reasoning="No urgent issues detected by rule engine.",
                    confidence=0.5,
                )
            )

        # Pick highest confidence thought
        best = max(thoughts, key=lambda t: t.confidence)

        # Enhance with memory context
        if memory_context and "No prior memory" not in memory_context:
            best.reasoning += f" | Memory: {memory_context}"

        self._thought_history.append(best)
        return best

    def decide_action(self, thought: Thought) -> Action:
        """Convert a thought into a concrete action."""
        action_map: Dict[ThoughtType, ActionType] = {
            ThoughtType.STRATEGIC: ActionType.BUILD_ORDER,
            ThoughtType.TACTICAL: ActionType.ARMY_MOVE,
            ThoughtType.ECONOMIC: ActionType.EXPAND,
            ThoughtType.SCOUTING: ActionType.SCOUT,
            ThoughtType.DEFENSIVE: ActionType.DEFEND,
            ThoughtType.REFLECTIVE: ActionType.UPGRADE,
        }
        action_type = action_map.get(thought.thought_type, ActionType.BUILD_ORDER)

        action = Action(
            action_type=action_type,
            description=thought.content,
            parameters={"sub_goals": thought.sub_goals},
            priority=max(1, int(10 - thought.confidence * 10)),
            thought_id=thought.thought_id,
        )
        self._action_queue.append(action)
        return action

    def observe(self, action: Action, success: bool, details: str) -> Observation:
        """Record the result of an action execution."""
        observation = Observation(
            action_id=action.action_id,
            success=success,
            details=details,
            lessons_learned=(
                [f"Action '{action.description}' succeeded. Reinforce this pattern."]
                if success
                else [
                    f"Action '{action.description}' failed. Avoid or adapt next time."
                ]
            ),
        )

        action.status = PlanStatus.COMPLETED if success else PlanStatus.FAILED
        self._observation_log.append(observation)
        return observation

    def run_tao_loop(
        self,
        state: SC2GameState,
        execute_fn: Optional[Callable[[Action], Tuple[bool, str]]] = None,
    ) -> List[Dict[str, Any]]:
        """
        Run the full Thought-Action-Observation loop.
        execute_fn: callback that takes an Action and returns (success, details).
        """
        if execute_fn is None:
            execute_fn = self._default_execute

        loop_log: List[Dict[str, Any]] = []

        for i in range(self.max_iterations):
            self._iteration_count = i + 1

            # THINK
            thought = self.think(state)

            # ACT
            action = self.decide_action(thought)
            success, details = execute_fn(action)

            # OBSERVE
            observation = self.observe(action, success, details)

            step = {
                "iteration": i + 1,
                "thought": thought.to_dict(),
                "action": action.to_dict(),
                "observation": observation.to_dict(),
            }
            loop_log.append(step)

            # Check if we should stop iterating
            if thought.confidence > 0.85 and success:
                break  # High confidence action succeeded; stable state

        return loop_log

    def reflect(self, game_result: str, state: SC2GameState) -> Dict[str, Any]:
        """Post-game reflection: store learnings in long-term memory."""
        total_actions = len(self._action_queue)
        successful = sum(
            1 for a in self._action_queue if a.status == PlanStatus.COMPLETED
        )
        failed = sum(1 for a in self._action_queue if a.status == PlanStatus.FAILED)

        # Extract key learnings
        learnings: List[str] = []
        for obs in self._observation_log:
            learnings.extend(obs.lessons_learned)

        # Store in long-term memory
        summary = (
            f"Game {state.matchup}: {game_result}. "
            f"{successful}/{total_actions} actions succeeded."
        )
        self.memory.store_learning(
            matchup=state.matchup,
            learning=summary,
            outcome=game_result,
            game_time=state.game_time,
        )

        reflection = {
            "game_result": game_result,
            "matchup": state.matchup,
            "total_actions": total_actions,
            "successful_actions": successful,
            "failed_actions": failed,
            "success_rate": round(successful / max(total_actions, 1), 2),
            "iterations": self._iteration_count,
            "key_learnings": learnings[:10],
            "memory_total": self.memory.total_learnings,
        }
        return reflection

    @staticmethod
    def _default_execute(action: Action) -> Tuple[bool, str]:
        """Default simulated execution for demo purposes."""
        # Simulate action success based on priority
        success = action.priority <= 7
        details = (
            f"Simulated execution of '{action.action_type.value}' "
            f"(priority {action.priority}): "
            f"{'success' if success else 'failed - priority too low'}"
        )
        return success, details

    def get_status(self) -> Dict[str, Any]:
        """Return planner status summary."""
        return {
            "thoughts": len(self._thought_history),
            "actions_queued": len(self._action_queue),
            "observations": len(self._observation_log),
            "current_goals": self._current_goals,
            "iterations": self._iteration_count,
            "memory_entries": self.memory.total_learnings,
        }


# ── PlanExecutor ─────────────────────────────────────────────────────────────


class PlanExecutor:
    """
    Executes a strategic plan by coordinating between the AutoGPT planner
    and the SC2 game interface. Manages plan lifecycle and adaptation.
    """

    def __init__(self, planner: AutoGPTPlanner) -> None:
        self.planner = planner
        self._execution_log: List[Dict[str, Any]] = []
        self._plan_history: List[Dict[str, Any]] = []

    def execute_plan(
        self,
        initial_state: SC2GameState,
        state_updates: Optional[List[SC2GameState]] = None,
    ) -> Dict[str, Any]:
        """Execute a full game plan with optional state updates for adaptation."""
        states = [initial_state] + (state_updates or [])
        all_logs: List[Dict[str, Any]] = []

        for idx, state in enumerate(states):
            phase_label = f"phase_{idx}"
            loop_log = self.planner.run_tao_loop(state, max_iterations=3)
            all_logs.append(
                {
                    "phase": phase_label,
                    "game_time": state.game_time,
                    "game_phase": state.game_phase,
                    "tao_steps": loop_log,
                }
            )

        plan_result = {
            "total_phases": len(states),
            "execution_log": all_logs,
            "planner_status": self.planner.get_status(),
        }
        self._plan_history.append(plan_result)
        return plan_result

    def adapt_mid_game(
        self, current_state: SC2GameState, unexpected_event: str
    ) -> Dict[str, Any]:
        """React to an unexpected mid-game event and re-plan."""
        # Generate a reactive thought
        reactive_thought = Thought(
            thought_type=ThoughtType.TACTICAL,
            content=f"Unexpected: {unexpected_event}. Re-evaluating plan.",
            reasoning=f"Event detected at {current_state.game_time:.0f}s. "
            f"Current threat: {current_state.threat_level:.1f}",
            confidence=0.6,
            sub_goals=["Assess damage", "Adjust strategy", "Stabilize economy"],
        )

        action = self.planner.decide_action(reactive_thought)
        success, details = self.planner._default_execute(action)
        observation = self.planner.observe(action, success, details)

        return {
            "event": unexpected_event,
            "reactive_thought": reactive_thought.to_dict(),
            "action_taken": action.to_dict(),
            "observation": observation.to_dict(),
        }

    def post_game_review(
        self, final_state: SC2GameState, result: str
    ) -> Dict[str, Any]:
        """Run post-game reflection and memory consolidation."""
        reflection = self.planner.reflect(result, final_state)
        return {
            "reflection": reflection,
            "plan_count": len(self._plan_history),
            "memory_summary": self.planner.memory.to_context_string(
                final_state.matchup
            ),
        }


# ── Demo ─────────────────────────────────────────────────────────────────────


def demo() -> None:
    """Demonstrate the AutoGPT Strategic Planner for SC2."""
    print("=" * 70)
    print("Phase 623: AutoGPT Strategic Planner for SC2")
    print("=" * 70)

    # 1. Initialize planner with long-term memory
    memory = LongTermMemory()
    memory.store_learning(
        "ZvT", "Roach-ravager timing at 7min wins vs greedy Terran", "win", 420
    )
    memory.store_learning(
        "ZvT", "Ling-bane all-in failed vs 2-base tank push", "loss", 360
    )

    planner = AutoGPTPlanner(memory=memory, max_iterations=5)
    executor = PlanExecutor(planner)

    print(f"\n[Memory] Pre-loaded {memory.total_learnings} strategic learnings.")

    # 2. Early game state
    early_state = SC2GameState(
        game_time=180,
        minerals=350,
        vespene=100,
        supply_used=28,
        supply_cap=36,
        worker_count=22,
        army_supply=4,
        base_count=2,
        player_race="Zerg",
        opponent_race="Terran",
        army_composition={"Zergling": 4},
        enemy_army_estimate={},
        tech_buildings=["SpawningPool"],
        threat_level=0.2,
    )
    print(f"\n[Game State] {early_state.to_prompt()}")

    # 3. Run TAO loop
    print("\n--- Thought-Action-Observation Loop ---")
    tao_log = planner.run_tao_loop(early_state)
    for step in tao_log:
        print(f"\n  Iteration {step['iteration']}:")
        print(f"    Thought: [{step['thought']['type']}] {step['thought']['content']}")
        print(
            f"    Action:  [{step['action']['type']}] {step['action']['description']}"
        )
        print(
            f"    Result:  {'OK' if step['observation']['success'] else 'FAIL'} - "
            f"{step['observation']['details'][:80]}"
        )

    # 4. Mid-game adaptation
    print("\n--- Mid-Game Adaptation ---")
    mid_state = SC2GameState(
        game_time=480,
        minerals=200,
        vespene=150,
        supply_used=88,
        supply_cap=100,
        worker_count=44,
        army_supply=40,
        base_count=3,
        player_race="Zerg",
        opponent_race="Terran",
        army_composition={"Roach": 8, "Ravager": 4, "Zergling": 12},
        enemy_army_estimate={"Marine": 20, "SiegeTank": 4},
        tech_buildings=["SpawningPool", "RoachWarren", "Lair"],
        threat_level=0.65,
    )
    adaptation = executor.adapt_mid_game(mid_state, "Enemy drop detected in main base")
    print(f"  Event: {adaptation['event']}")
    print(f"  Reaction: {adaptation['reactive_thought']['content']}")
    print(f"  Action: {adaptation['action_taken']['description']}")

    # 5. Post-game reflection
    print("\n--- Post-Game Reflection ---")
    final_state = SC2GameState(
        game_time=900,
        minerals=1500,
        vespene=800,
        supply_used=190,
        supply_cap=200,
        worker_count=66,
        army_supply=120,
        base_count=4,
        player_race="Zerg",
        opponent_race="Terran",
        army_composition={"Roach": 12, "Ravager": 6, "Hydralisk": 10, "Lurker": 4},
        enemy_army_estimate={"Marine": 30, "SiegeTank": 8, "Medivac": 4},
        tech_buildings=[
            "SpawningPool",
            "RoachWarren",
            "Lair",
            "HydraliskDen",
            "LurkerDen",
        ],
        threat_level=0.4,
    )
    review = executor.post_game_review(final_state, "win")
    reflection = review["reflection"]
    print(f"  Result: {reflection['game_result']}")
    print(
        f"  Success rate: {reflection['success_rate']:.0%} "
        f"({reflection['successful_actions']}/{reflection['total_actions']} actions)"
    )
    print(f"  Iterations: {reflection['iterations']}")
    print(f"  Key learnings:")
    for lesson in reflection["key_learnings"][:5]:
        print(f"    - {lesson}")
    print(f"  Memory entries: {reflection['memory_total']}")
    print(f"  Memory context: {review['memory_summary'][:120]}")

    # 6. Planner status
    print("\n--- Planner Status ---")
    status = planner.get_status()
    for key, value in status.items():
        print(f"  {key}: {value}")

    print("\n" + "=" * 70)
    print("Phase 623: AutoGPT strategic planner demo complete.")
    print("=" * 70)


if __name__ == "__main__":
    demo()

# Phase 623: AutoGPT registered
