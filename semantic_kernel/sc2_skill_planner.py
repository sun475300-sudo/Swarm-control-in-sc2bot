"""
Phase 628: Semantic Kernel Skill Planner for SC2
=================================================
Semantic Kernel-style skill orchestration for StarCraft II strategy planning.

Implements a skill-based architecture where discrete SC2 capabilities (analyze
matchup, suggest build order, evaluate army, plan attack) are composed into
complex multi-step strategies via a sequential planner. A persistent memory
layer stores and recalls past game outcomes to inform future decisions.

Key components:
    - SKill / SKFunction: atomic skill units with typed parameters
    - SKPlanner: sequential chaining of skills into strategy pipelines
    - SKMemory: episodic memory for game outcomes and lessons learned
    - SC2SkillPlanner: top-level facade tying everything together
"""

from __future__ import annotations

import hashlib
import json
import logging
import math
import random
import time
from collections import defaultdict
from dataclasses import dataclass, field
from enum import Enum, auto
from typing import Any, Callable, Dict, List, Optional, Sequence, Tuple

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

SC2_RACES = ("Zerg", "Terran", "Protoss")

MATCHUP_LABELS = [
    "ZvZ", "ZvT", "ZvP",
    "TvZ", "TvT", "TvP",
    "PvZ", "PvT", "PvP",
]

GAME_PHASES = ("early", "mid", "late")

# Canonical action categories that skills can map to
ACTION_BUILD = "build"
ACTION_ATTACK = "attack"
ACTION_DEFEND = "defend"
ACTION_EXPAND = "expand"
ACTION_SCOUT = "scout"
ACTION_TECH = "tech"
ACTION_HARASS = "harass"

ALL_ACTIONS = (
    ACTION_BUILD, ACTION_ATTACK, ACTION_DEFEND,
    ACTION_EXPAND, ACTION_SCOUT, ACTION_TECH, ACTION_HARASS,
)


# ---------------------------------------------------------------------------
# Enums
# ---------------------------------------------------------------------------

class SkillCategory(Enum):
    """Broad categories for SC2 skills."""
    ANALYSIS = auto()
    STRATEGY = auto()
    TACTICS = auto()
    ECONOMY = auto()
    INTELLIGENCE = auto()


class PlanStatus(Enum):
    """Execution status of a plan."""
    PENDING = auto()
    RUNNING = auto()
    SUCCESS = auto()
    FAILED = auto()
    CANCELLED = auto()


# ---------------------------------------------------------------------------
# Data classes
# ---------------------------------------------------------------------------

@dataclass
class SkillParameter:
    """Typed parameter declaration for a skill function."""
    name: str
    description: str
    param_type: str = "str"  # str, int, float, bool, list, dict
    required: bool = True
    default: Any = None

    def validate(self, value: Any) -> bool:
        """Check whether *value* is compatible with declared type."""
        type_map = {
            "str": str, "int": int, "float": (int, float),
            "bool": bool, "list": (list, tuple), "dict": dict,
        }
        expected = type_map.get(self.param_type, object)
        return isinstance(value, expected)


@dataclass
class SkillResult:
    """Result returned by a single skill invocation."""
    skill_name: str
    success: bool
    data: Dict[str, Any] = field(default_factory=dict)
    error: Optional[str] = None
    elapsed_ms: float = 0.0
    actions: List[str] = field(default_factory=list)

    def summary(self) -> str:
        status = "OK" if self.success else f"FAIL({self.error})"
        return f"[{self.skill_name}] {status} ({self.elapsed_ms:.1f}ms)"


@dataclass
class PlanStep:
    """One step inside a sequential plan."""
    index: int
    skill_name: str
    parameters: Dict[str, Any] = field(default_factory=dict)
    result: Optional[SkillResult] = None
    depends_on: List[int] = field(default_factory=list)

    @property
    def completed(self) -> bool:
        return self.result is not None


@dataclass
class Plan:
    """A sequential plan consisting of ordered steps."""
    plan_id: str
    name: str
    steps: List[PlanStep] = field(default_factory=list)
    status: PlanStatus = PlanStatus.PENDING
    created_at: float = field(default_factory=time.time)
    context: Dict[str, Any] = field(default_factory=dict)

    @property
    def completed_steps(self) -> int:
        return sum(1 for s in self.steps if s.completed)

    @property
    def progress(self) -> float:
        if not self.steps:
            return 0.0
        return self.completed_steps / len(self.steps)

    def results_summary(self) -> List[str]:
        return [s.result.summary() for s in self.steps if s.result]


@dataclass
class MemoryEntry:
    """Single memory record (an episode or fact)."""
    key: str
    content: Dict[str, Any]
    tags: List[str] = field(default_factory=list)
    relevance: float = 1.0
    timestamp: float = field(default_factory=time.time)
    access_count: int = 0


# ---------------------------------------------------------------------------
# SKFunction
# ---------------------------------------------------------------------------

class SKFunction:
    """
    A callable skill function with declared parameters and metadata.

    Each SKFunction wraps a Python callable and enriches it with parameter
    declarations, descriptions, and the set of SC2 game actions it can
    produce.
    """

    def __init__(
        self,
        name: str,
        func: Callable[..., SkillResult],
        description: str = "",
        parameters: Optional[List[SkillParameter]] = None,
        game_actions: Optional[List[str]] = None,
    ) -> None:
        self.name = name
        self.func = func
        self.description = description
        self.parameters: List[SkillParameter] = parameters or []
        self.game_actions: List[str] = game_actions or []
        self._call_count: int = 0
        self._total_ms: float = 0.0

    # ------------------------------------------------------------------
    def invoke(self, context: Dict[str, Any]) -> SkillResult:
        """Execute the function, measuring elapsed time."""
        self._call_count += 1
        t0 = time.perf_counter()
        try:
            result = self.func(context)
            result.elapsed_ms = (time.perf_counter() - t0) * 1000
            result.actions = list(self.game_actions)
            self._total_ms += result.elapsed_ms
            return result
        except Exception as exc:
            elapsed = (time.perf_counter() - t0) * 1000
            self._total_ms += elapsed
            return SkillResult(
                skill_name=self.name,
                success=False,
                error=str(exc),
                elapsed_ms=elapsed,
            )

    # ------------------------------------------------------------------
    def validate_params(self, context: Dict[str, Any]) -> List[str]:
        """Return list of validation errors (empty == OK)."""
        errors: List[str] = []
        for p in self.parameters:
            if p.required and p.name not in context:
                errors.append(f"Missing required parameter: {p.name}")
            elif p.name in context and not p.validate(context[p.name]):
                errors.append(
                    f"Parameter '{p.name}' expected {p.param_type}, "
                    f"got {type(context[p.name]).__name__}"
                )
        return errors

    @property
    def avg_ms(self) -> float:
        if self._call_count == 0:
            return 0.0
        return self._total_ms / self._call_count

    def __repr__(self) -> str:
        return f"SKFunction({self.name!r}, calls={self._call_count})"


# ---------------------------------------------------------------------------
# SKill
# ---------------------------------------------------------------------------

class SKill:
    """
    A named collection of related SKFunctions (a *skill*).

    Skills group functions that share a common domain, e.g. the
    "MatchupAnalysis" skill contains functions for race identification,
    composition evaluation, and counter-strategy lookup.
    """

    def __init__(
        self,
        name: str,
        category: SkillCategory = SkillCategory.ANALYSIS,
        description: str = "",
    ) -> None:
        self.name = name
        self.category = category
        self.description = description
        self.functions: Dict[str, SKFunction] = {}
        self.enabled: bool = True

    # ------------------------------------------------------------------
    def add_function(self, func: SKFunction) -> None:
        self.functions[func.name] = func

    def get_function(self, name: str) -> Optional[SKFunction]:
        return self.functions.get(name)

    def list_functions(self) -> List[str]:
        return list(self.functions.keys())

    def invoke(self, func_name: str, context: Dict[str, Any]) -> SkillResult:
        fn = self.functions.get(func_name)
        if fn is None:
            return SkillResult(
                skill_name=f"{self.name}.{func_name}",
                success=False,
                error=f"Function '{func_name}' not found in skill '{self.name}'",
            )
        if not self.enabled:
            return SkillResult(
                skill_name=f"{self.name}.{func_name}",
                success=False,
                error=f"Skill '{self.name}' is disabled",
            )
        return fn.invoke(context)

    def __repr__(self) -> str:
        return f"SKill({self.name!r}, funcs={len(self.functions)})"


# ---------------------------------------------------------------------------
# SKMemory
# ---------------------------------------------------------------------------

class SKMemory:
    """
    Episodic + semantic memory store for the planner.

    Stores past game outcomes, learned heuristics, and contextual facts
    so that the planner can recall them when composing strategies.
    """

    def __init__(self, capacity: int = 5000) -> None:
        self.capacity = capacity
        self._store: Dict[str, MemoryEntry] = {}
        self._tag_index: Dict[str, List[str]] = defaultdict(list)

    # ------------------------------------------------------------------
    def save(
        self,
        key: str,
        content: Dict[str, Any],
        tags: Optional[List[str]] = None,
        relevance: float = 1.0,
    ) -> None:
        """Store or overwrite a memory entry."""
        if len(self._store) >= self.capacity and key not in self._store:
            self._evict_least_relevant()
        entry = MemoryEntry(
            key=key, content=content,
            tags=tags or [], relevance=relevance,
        )
        self._store[key] = entry
        for tag in entry.tags:
            if key not in self._tag_index[tag]:
                self._tag_index[tag].append(key)

    def recall(self, key: str) -> Optional[Dict[str, Any]]:
        """Retrieve a memory entry by key."""
        entry = self._store.get(key)
        if entry is None:
            return None
        entry.access_count += 1
        return entry.content

    def search_by_tag(self, tag: str, limit: int = 10) -> List[MemoryEntry]:
        """Find entries matching a tag, sorted by relevance."""
        keys = self._tag_index.get(tag, [])
        entries = [self._store[k] for k in keys if k in self._store]
        entries.sort(key=lambda e: e.relevance, reverse=True)
        return entries[:limit]

    def search_by_prefix(self, prefix: str, limit: int = 10) -> List[MemoryEntry]:
        """Find entries whose key starts with *prefix*."""
        matches = [e for k, e in self._store.items() if k.startswith(prefix)]
        matches.sort(key=lambda e: e.timestamp, reverse=True)
        return matches[:limit]

    def forget(self, key: str) -> bool:
        entry = self._store.pop(key, None)
        if entry is None:
            return False
        for tag in entry.tags:
            if key in self._tag_index[tag]:
                self._tag_index[tag].remove(key)
        return True

    def size(self) -> int:
        return len(self._store)

    def _evict_least_relevant(self) -> None:
        if not self._store:
            return
        worst_key = min(self._store, key=lambda k: self._store[k].relevance)
        self.forget(worst_key)

    def summarize(self) -> Dict[str, Any]:
        tag_counts = {t: len(keys) for t, keys in self._tag_index.items()}
        return {
            "total_entries": self.size(),
            "capacity": self.capacity,
            "tag_counts": tag_counts,
        }


# ---------------------------------------------------------------------------
# Built-in SC2 Skill Functions
# ---------------------------------------------------------------------------

def _analyze_matchup(ctx: Dict[str, Any]) -> SkillResult:
    """Analyze the current matchup and determine strategic considerations."""
    our_race = ctx.get("our_race", "Zerg")
    enemy_race = ctx.get("enemy_race", "Terran")
    game_time = ctx.get("game_time", 0.0)

    matchup = f"{our_race[0]}v{enemy_race[0]}"

    # Phase detection
    if game_time < 180:
        phase = "early"
    elif game_time < 480:
        phase = "mid"
    else:
        phase = "late"

    # Heuristic threat profiles per matchup
    threat_profiles: Dict[str, Dict[str, Any]] = {
        "ZvT": {
            "early": {"threats": ["hellion_rush", "reaper_harass"], "priority": "defense"},
            "mid": {"threats": ["bio_push", "mine_drop"], "priority": "tech"},
            "late": {"threats": ["liberator_siege", "ghost_snipe"], "priority": "flank"},
        },
        "ZvP": {
            "early": {"threats": ["cannon_rush", "adept_harass"], "priority": "scout"},
            "mid": {"threats": ["immortal_push", "oracle_harass"], "priority": "roach_hydra"},
            "late": {"threats": ["carrier_deathball", "storm"], "priority": "corruptor_viper"},
        },
        "ZvZ": {
            "early": {"threats": ["ling_flood", "bane_bust"], "priority": "ling_bane"},
            "mid": {"threats": ["roach_all_in", "muta_harass"], "priority": "roach"},
            "late": {"threats": ["brood_lord", "ultra_ling"], "priority": "late_comp"},
        },
    }

    profile = threat_profiles.get(matchup, {}).get(phase, {
        "threats": ["unknown"], "priority": "adaptive",
    })

    return SkillResult(
        skill_name="AnalyzeMatchup",
        success=True,
        data={
            "matchup": matchup,
            "phase": phase,
            "threats": profile.get("threats", []),
            "priority": profile.get("priority", "adaptive"),
            "our_race": our_race,
            "enemy_race": enemy_race,
            "game_time": game_time,
        },
    )


def _suggest_build_order(ctx: Dict[str, Any]) -> SkillResult:
    """Suggest a build order based on matchup analysis."""
    matchup = ctx.get("matchup", "ZvT")
    phase = ctx.get("phase", "early")
    priority = ctx.get("priority", "macro")

    build_db: Dict[str, Dict[str, List[str]]] = {
        "ZvT": {
            "early": [
                "16 hatch", "18 gas", "17 pool",
                "20 ling speed", "30 queen x2", "36 third hatch",
            ],
            "mid": [
                "lair", "evo chamber x2", "+1/+1",
                "bane nest", "roach warren (optional)",
                "66 supply: 4th base",
            ],
            "late": [
                "hive", "adrenal glands", "ultra cavern",
                "greater spire (alt)", "infestation pit",
            ],
        },
        "ZvP": {
            "early": [
                "16 hatch", "18 gas", "17 pool",
                "19 overlord", "queen x2", "ling speed",
            ],
            "mid": [
                "roach warren", "lair", "hydra den",
                "+1 ranged", "3rd base saturate",
            ],
            "late": [
                "hive", "viper", "lurker den",
                "+3/+3", "brood lords",
            ],
        },
        "ZvZ": {
            "early": [
                "14 pool", "16 hatch", "15 gas",
                "ling speed", "bane nest", "queen x2",
            ],
            "mid": [
                "roach warren", "lair", "evo chamber",
                "+1 missile", "overseer",
            ],
            "late": [
                "hive", "ultra cavern", "greater spire",
                "infestor", "brood lords",
            ],
        },
    }

    steps = build_db.get(matchup, {}).get(phase, ["adaptive macro expansion"])

    confidence = 0.85 if matchup in build_db else 0.5

    return SkillResult(
        skill_name="SuggestBuildOrder",
        success=True,
        data={
            "matchup": matchup,
            "phase": phase,
            "build_steps": steps,
            "confidence": confidence,
            "priority": priority,
        },
    )


def _evaluate_army(ctx: Dict[str, Any]) -> SkillResult:
    """Evaluate current army composition strength and weaknesses."""
    our_army: Dict[str, int] = ctx.get("our_army", {})
    enemy_army: Dict[str, int] = ctx.get("enemy_army", {})

    # Unit strength table (simplified)
    unit_power: Dict[str, float] = {
        "zergling": 0.5, "baneling": 1.2, "roach": 2.0,
        "hydralisk": 3.0, "mutalisk": 3.5, "ultralisk": 8.0,
        "brood_lord": 6.0, "corruptor": 4.0, "infestor": 3.0,
        "lurker": 4.5, "viper": 3.5, "ravager": 3.0,
        "queen": 2.5, "overlord": 0.1, "overseer": 0.5,
        "marine": 1.0, "marauder": 2.0, "medivac": 2.0,
        "siege_tank": 4.0, "thor": 6.0, "viking": 3.0,
        "liberator": 4.0, "ghost": 4.5, "hellion": 1.5,
        "banshee": 3.5, "battlecruiser": 8.0,
        "zealot": 1.5, "stalker": 2.5, "sentry": 1.5,
        "adept": 2.0, "immortal": 4.5, "colossus": 6.0,
        "disruptor": 5.0, "archon": 4.0, "high_templar": 3.5,
        "carrier": 8.0, "void_ray": 3.5, "phoenix": 2.5,
        "oracle": 3.0, "tempest": 5.0, "mothership": 10.0,
    }

    our_power = sum(
        unit_power.get(unit, 1.0) * count
        for unit, count in our_army.items()
    )
    enemy_power = sum(
        unit_power.get(unit, 1.0) * count
        for unit, count in enemy_army.items()
    )

    if enemy_power == 0:
        ratio = 999.0
    else:
        ratio = our_power / enemy_power

    if ratio > 1.5:
        assessment = "dominant"
        recommendation = "attack"
    elif ratio > 1.1:
        assessment = "slight_advantage"
        recommendation = "pressure"
    elif ratio > 0.9:
        assessment = "even"
        recommendation = "defensive_macro"
    elif ratio > 0.6:
        assessment = "disadvantage"
        recommendation = "turtle_and_tech"
    else:
        assessment = "critical"
        recommendation = "emergency_defense"

    return SkillResult(
        skill_name="EvaluateArmy",
        success=True,
        data={
            "our_power": round(our_power, 1),
            "enemy_power": round(enemy_power, 1),
            "power_ratio": round(ratio, 2),
            "assessment": assessment,
            "recommendation": recommendation,
            "our_unit_count": sum(our_army.values()),
            "enemy_unit_count": sum(enemy_army.values()),
        },
    )


def _plan_attack(ctx: Dict[str, Any]) -> SkillResult:
    """Generate an attack plan based on army evaluation and map info."""
    assessment = ctx.get("assessment", "even")
    recommendation = ctx.get("recommendation", "pressure")
    our_army = ctx.get("our_army", {})
    enemy_position = ctx.get("enemy_position", (50.0, 50.0))
    our_position = ctx.get("our_position", (25.0, 25.0))

    # Distance heuristic
    dx = enemy_position[0] - our_position[0]
    dy = enemy_position[1] - our_position[1]
    distance = math.sqrt(dx * dx + dy * dy)

    # Choose attack style
    has_air = any(
        u in our_army
        for u in ("mutalisk", "corruptor", "brood_lord", "viper", "overseer")
    )
    has_siege = any(
        u in our_army
        for u in ("lurker", "brood_lord", "ravager", "infestor")
    )

    if assessment == "dominant":
        style = "all_in_push"
        phases = ["rally_all", "a_move_main", "cleanup"]
    elif assessment == "slight_advantage" and has_air:
        style = "multi_prong"
        phases = ["air_harass_mineral_line", "ground_push_natural", "reinforce"]
    elif has_siege:
        style = "siege_advance"
        phases = ["setup_siege_position", "creep_forward", "engage_at_range"]
    else:
        style = "poke_and_retreat"
        phases = ["move_to_vision", "poke_frontline", "retreat_if_losing"]

    waypoints = []
    steps_count = 3
    for i in range(1, steps_count + 1):
        frac = i / steps_count
        wx = our_position[0] + dx * frac
        wy = our_position[1] + dy * frac
        waypoints.append((round(wx, 1), round(wy, 1)))

    return SkillResult(
        skill_name="PlanAttack",
        success=True,
        data={
            "style": style,
            "phases": phases,
            "waypoints": waypoints,
            "distance": round(distance, 1),
            "has_air": has_air,
            "has_siege": has_siege,
            "assessment": assessment,
        },
    )


# ---------------------------------------------------------------------------
# SKPlanner
# ---------------------------------------------------------------------------

class SKPlanner:
    """
    Sequential planner that chains skills into multi-step strategies.

    The planner builds a :class:`Plan` from a goal description and a set
    of registered skills.  During execution it feeds each step's output
    into the next step's context, enabling data to flow through the chain.
    """

    def __init__(self) -> None:
        self.skills: Dict[str, SKill] = {}
        self._plans: Dict[str, Plan] = {}
        self._plan_counter: int = 0

    # ------------------------------------------------------------------
    # Skill registration
    # ------------------------------------------------------------------

    def register_skill(self, skill: SKill) -> None:
        self.skills[skill.name] = skill
        logger.info("Registered skill: %s (%d functions)",
                     skill.name, len(skill.functions))

    def unregister_skill(self, name: str) -> bool:
        return self.skills.pop(name, None) is not None

    def list_skills(self) -> List[str]:
        return list(self.skills.keys())

    def find_function(self, func_name: str) -> Optional[Tuple[SKill, SKFunction]]:
        """Locate a function across all skills."""
        for skill in self.skills.values():
            fn = skill.get_function(func_name)
            if fn is not None:
                return skill, fn
        return None

    # ------------------------------------------------------------------
    # Plan creation
    # ------------------------------------------------------------------

    def create_plan(
        self,
        name: str,
        steps: List[Tuple[str, Dict[str, Any]]],
        context: Optional[Dict[str, Any]] = None,
    ) -> Plan:
        """
        Build a plan from a list of (function_name, params) tuples.

        Parameters
        ----------
        name : str
            Human-readable plan name.
        steps : list of (func_name, params)
            Ordered skill function invocations.
        context : dict, optional
            Initial shared context.
        """
        self._plan_counter += 1
        plan_id = f"plan-{self._plan_counter:04d}"
        plan_steps: List[PlanStep] = []
        for i, (func_name, params) in enumerate(steps):
            plan_steps.append(PlanStep(index=i, skill_name=func_name, parameters=params))

        plan = Plan(
            plan_id=plan_id,
            name=name,
            steps=plan_steps,
            context=context or {},
        )
        self._plans[plan_id] = plan
        return plan

    def create_strategy_plan(
        self,
        our_race: str,
        enemy_race: str,
        game_time: float,
        our_army: Dict[str, int],
        enemy_army: Dict[str, int],
        our_position: Tuple[float, float] = (25.0, 25.0),
        enemy_position: Tuple[float, float] = (50.0, 50.0),
    ) -> Plan:
        """
        Build the standard 4-step SC2 strategy pipeline.

        1. AnalyzeMatchup -> 2. SuggestBuildOrder ->
        3. EvaluateArmy   -> 4. PlanAttack
        """
        steps: List[Tuple[str, Dict[str, Any]]] = [
            ("AnalyzeMatchup", {
                "our_race": our_race,
                "enemy_race": enemy_race,
                "game_time": game_time,
            }),
            ("SuggestBuildOrder", {}),   # filled from step 1
            ("EvaluateArmy", {
                "our_army": our_army,
                "enemy_army": enemy_army,
            }),
            ("PlanAttack", {
                "our_position": our_position,
                "enemy_position": enemy_position,
            }),
        ]
        return self.create_plan(
            name=f"Strategy_{our_race}v{enemy_race}_{int(game_time)}s",
            steps=steps,
            context={
                "our_race": our_race,
                "enemy_race": enemy_race,
                "game_time": game_time,
            },
        )

    # ------------------------------------------------------------------
    # Plan execution
    # ------------------------------------------------------------------

    def execute_plan(self, plan: Plan) -> Plan:
        """
        Run every step sequentially, passing accumulated context forward.
        """
        plan.status = PlanStatus.RUNNING
        accumulated: Dict[str, Any] = dict(plan.context)

        for step in plan.steps:
            # Merge step-local parameters into accumulated context
            step_ctx = {**accumulated, **step.parameters}

            pair = self.find_function(step.skill_name)
            if pair is None:
                step.result = SkillResult(
                    skill_name=step.skill_name,
                    success=False,
                    error=f"Skill function '{step.skill_name}' not found",
                )
                plan.status = PlanStatus.FAILED
                return plan

            skill, fn = pair
            result = fn.invoke(step_ctx)
            step.result = result

            if not result.success:
                plan.status = PlanStatus.FAILED
                return plan

            # Feed result data into accumulated context for next steps
            accumulated.update(result.data)

        plan.status = PlanStatus.SUCCESS
        return plan

    def get_plan(self, plan_id: str) -> Optional[Plan]:
        return self._plans.get(plan_id)

    def list_plans(self) -> List[str]:
        return list(self._plans.keys())


# ---------------------------------------------------------------------------
# SC2SkillPlanner  (top-level facade)
# ---------------------------------------------------------------------------

class SC2SkillPlanner:
    """
    High-level facade integrating the planner, built-in skills, and memory.

    Usage::

        planner = SC2SkillPlanner()
        result = planner.strategize(
            our_race="Zerg", enemy_race="Terran",
            game_time=300.0,
            our_army={"zergling": 40, "baneling": 12, "queen": 4},
            enemy_army={"marine": 30, "medivac": 4, "siege_tank": 6},
        )
    """

    def __init__(self, memory_capacity: int = 5000) -> None:
        self.planner = SKPlanner()
        self.memory = SKMemory(capacity=memory_capacity)
        self._register_builtin_skills()
        self._game_counter: int = 0

    # ------------------------------------------------------------------
    def _register_builtin_skills(self) -> None:
        # --- AnalyzeMatchup skill ---
        analyze_skill = SKill(
            "MatchupAnalysis", SkillCategory.ANALYSIS,
            "Analyze SC2 matchup and identify threats",
        )
        analyze_skill.add_function(SKFunction(
            name="AnalyzeMatchup",
            func=_analyze_matchup,
            description="Determine matchup characteristics and threat profile",
            parameters=[
                SkillParameter("our_race", "Our race", "str"),
                SkillParameter("enemy_race", "Enemy race", "str"),
                SkillParameter("game_time", "Seconds elapsed", "float", required=False, default=0.0),
            ],
            game_actions=[ACTION_SCOUT],
        ))
        self.planner.register_skill(analyze_skill)

        # --- SuggestBuildOrder skill ---
        build_skill = SKill(
            "BuildOrderSuggestion", SkillCategory.STRATEGY,
            "Suggest build orders for current game state",
        )
        build_skill.add_function(SKFunction(
            name="SuggestBuildOrder",
            func=_suggest_build_order,
            description="Generate build order steps",
            parameters=[
                SkillParameter("matchup", "Matchup label", "str"),
                SkillParameter("phase", "Game phase", "str"),
            ],
            game_actions=[ACTION_BUILD, ACTION_TECH, ACTION_EXPAND],
        ))
        self.planner.register_skill(build_skill)

        # --- EvaluateArmy skill ---
        army_skill = SKill(
            "ArmyEvaluation", SkillCategory.TACTICS,
            "Evaluate army strength and give recommendation",
        )
        army_skill.add_function(SKFunction(
            name="EvaluateArmy",
            func=_evaluate_army,
            description="Compare army power levels",
            parameters=[
                SkillParameter("our_army", "Our units {name: count}", "dict"),
                SkillParameter("enemy_army", "Enemy units {name: count}", "dict"),
            ],
            game_actions=[ACTION_DEFEND, ACTION_ATTACK],
        ))
        self.planner.register_skill(army_skill)

        # --- PlanAttack skill ---
        attack_skill = SKill(
            "AttackPlanning", SkillCategory.TACTICS,
            "Generate attack plans with waypoints",
        )
        attack_skill.add_function(SKFunction(
            name="PlanAttack",
            func=_plan_attack,
            description="Create phased attack plan",
            parameters=[
                SkillParameter("assessment", "Army assessment", "str"),
                SkillParameter("our_position", "Our army position", "list", required=False),
                SkillParameter("enemy_position", "Enemy position", "list", required=False),
            ],
            game_actions=[ACTION_ATTACK, ACTION_HARASS],
        ))
        self.planner.register_skill(attack_skill)

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def strategize(
        self,
        our_race: str = "Zerg",
        enemy_race: str = "Terran",
        game_time: float = 300.0,
        our_army: Optional[Dict[str, int]] = None,
        enemy_army: Optional[Dict[str, int]] = None,
        our_position: Tuple[float, float] = (25.0, 25.0),
        enemy_position: Tuple[float, float] = (50.0, 50.0),
    ) -> Dict[str, Any]:
        """Run full strategy pipeline and return consolidated result."""
        if our_army is None:
            our_army = {"zergling": 20, "queen": 3}
        if enemy_army is None:
            enemy_army = {"marine": 15}

        plan = self.planner.create_strategy_plan(
            our_race=our_race,
            enemy_race=enemy_race,
            game_time=game_time,
            our_army=our_army,
            enemy_army=enemy_army,
            our_position=our_position,
            enemy_position=enemy_position,
        )

        executed = self.planner.execute_plan(plan)

        # Persist to memory
        self._game_counter += 1
        mem_key = f"strategy_{self._game_counter:05d}"
        strategy_data = {
            "plan_id": executed.plan_id,
            "status": executed.status.name,
            "steps": executed.results_summary(),
        }
        matchup_tag = f"{our_race[0]}v{enemy_race[0]}"
        self.memory.save(
            key=mem_key,
            content=strategy_data,
            tags=[matchup_tag, executed.status.name],
            relevance=1.0 if executed.status == PlanStatus.SUCCESS else 0.3,
        )

        return {
            "plan_id": executed.plan_id,
            "name": executed.name,
            "status": executed.status.name,
            "progress": executed.progress,
            "results": executed.results_summary(),
            "step_data": [
                s.result.data if s.result else {} for s in executed.steps
            ],
            "memory_key": mem_key,
        }

    def recall_past_strategies(
        self,
        matchup: Optional[str] = None,
        limit: int = 5,
    ) -> List[Dict[str, Any]]:
        """Retrieve past strategies from memory."""
        if matchup:
            entries = self.memory.search_by_tag(matchup, limit=limit)
        else:
            entries = self.memory.search_by_prefix("strategy_", limit=limit)
        return [e.content for e in entries]

    def get_memory_stats(self) -> Dict[str, Any]:
        return self.memory.summarize()


# ---------------------------------------------------------------------------
# Demo
# ---------------------------------------------------------------------------

def demo() -> None:
    """Demonstrate Phase 628 Semantic Kernel Skill Planner."""
    print("=" * 70)
    print("Phase 628: Semantic Kernel Skill Planner for SC2  -  Demo")
    print("=" * 70)

    planner = SC2SkillPlanner()

    # --- Registered skills ---
    print("\n[1] Registered skills:")
    for s_name in planner.planner.list_skills():
        skill = planner.planner.skills[s_name]
        funcs = ", ".join(skill.list_functions())
        print(f"    {s_name} ({skill.category.name}): {funcs}")

    # --- Run strategy pipeline: ZvT ---
    print("\n[2] Strategy pipeline: Zerg vs Terran @ 300s")
    result_zvt = planner.strategize(
        our_race="Zerg",
        enemy_race="Terran",
        game_time=300.0,
        our_army={"zergling": 40, "baneling": 12, "queen": 4, "roach": 8},
        enemy_army={"marine": 30, "medivac": 4, "siege_tank": 6},
    )
    print(f"    Plan: {result_zvt['name']}")
    print(f"    Status: {result_zvt['status']}")
    for line in result_zvt["results"]:
        print(f"      {line}")

    for i, data in enumerate(result_zvt["step_data"]):
        print(f"    Step {i} data keys: {list(data.keys())}")

    # --- Run strategy pipeline: ZvP ---
    print("\n[3] Strategy pipeline: Zerg vs Protoss @ 600s (late)")
    result_zvp = planner.strategize(
        our_race="Zerg",
        enemy_race="Protoss",
        game_time=600.0,
        our_army={"hydralisk": 20, "corruptor": 8, "viper": 3, "queen": 5},
        enemy_army={"carrier": 6, "void_ray": 4, "high_templar": 3},
    )
    print(f"    Plan: {result_zvp['name']}")
    print(f"    Status: {result_zvp['status']}")
    for line in result_zvp["results"]:
        print(f"      {line}")

    # --- Memory recall ---
    print("\n[4] Memory recall:")
    zvt_history = planner.recall_past_strategies(matchup="ZvT", limit=3)
    print(f"    ZvT memories: {len(zvt_history)}")
    for mem in zvt_history:
        print(f"      {mem.get('plan_id', '?')}: {mem.get('status', '?')}")

    stats = planner.get_memory_stats()
    print(f"    Memory stats: {stats}")

    # --- Individual skill invocation ---
    print("\n[5] Direct skill invocation: AnalyzeMatchup")
    pair = planner.planner.find_function("AnalyzeMatchup")
    if pair:
        _, fn = pair
        direct_result = fn.invoke({
            "our_race": "Zerg",
            "enemy_race": "Zerg",
            "game_time": 120.0,
        })
        print(f"    {direct_result.summary()}")
        print(f"    Threats: {direct_result.data.get('threats')}")

    # --- Custom plan ---
    print("\n[6] Custom 2-step plan (Analyze + Build Order):")
    custom = planner.planner.create_plan(
        name="EconFocus",
        steps=[
            ("AnalyzeMatchup", {"our_race": "Zerg", "enemy_race": "Protoss", "game_time": 60.0}),
            ("SuggestBuildOrder", {}),
        ],
    )
    planner.planner.execute_plan(custom)
    for s in custom.steps:
        if s.result:
            print(f"    {s.result.summary()}")
            if "build_steps" in s.result.data:
                for bs in s.result.data["build_steps"]:
                    print(f"        -> {bs}")

    print("\n" + "=" * 70)
    print("Phase 628 demo complete.")
    print("=" * 70)


if __name__ == "__main__":
    demo()

# Phase 628: Semantic Kernel registered
