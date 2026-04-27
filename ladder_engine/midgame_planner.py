"""
Phase 362: Mid-Game Planner
Mid-game strategic planning for Zerg: timing attacks, economic transitions,
and tech switches based on current game state.
"""

from dataclasses import dataclass, field
from typing import List, Dict, Optional
from enum import Enum


class GamePhase(Enum):
    OPENING = "opening"  # < 4 min
    EARLY_MID = "early_mid"  # 4-8 min
    MID = "mid"  # 8-14 min
    LATE_MID = "late_mid"  # 14-20 min
    LATE = "late"  # > 20 min


class PlanType(Enum):
    TIMING_ATTACK = "timing_attack"
    EXPAND_THIRD = "expand_to_third"
    TECH_SWITCH = "tech_switch"
    DRONE_UP = "drone_up"
    DEFEND_AND_MACRO = "defend_and_macro"


@dataclass
class StrategicPlan:
    plan_type: PlanType
    priority: float  # 0.0 - 1.0
    trigger_supply: int
    description: str
    actions: List[str] = field(default_factory=list)
    estimated_timing: float = 0.0  # game seconds

    def add_action(self, action: str):
        self.actions.append(action)

    def __repr__(self):
        return f"Plan({self.plan_type.value}, priority={self.priority:.2f}, @{self.trigger_supply}sup)"


@dataclass
class GameState:
    """Snapshot of relevant game state for planning decisions."""

    game_time: float = 0.0
    supply_used: int = 0
    supply_cap: int = 14
    worker_count: int = 12
    army_supply: int = 0
    base_count: int = 1
    has_lair: bool = False
    has_hive: bool = False
    has_roach_warren: bool = False
    has_hydralisk_den: bool = False
    has_spire: bool = False
    minerals: int = 0
    vespene: int = 0
    income_minerals: float = 0.0
    income_vespene: float = 0.0
    opponent_race: str = "Unknown"
    opponent_army_supply: int = 0


class MidGamePlanner:
    """Generates strategic plans for Zerg mid-game based on game state analysis."""

    # Thresholds
    MIN_ARMY_FOR_TIMING = 30
    IDEAL_WORKER_THIRD = 48
    EXPAND_MINERAL_BANK = 350

    def __init__(self):
        self._plan_history: List[StrategicPlan] = []

    def analyze_phase(self, state: GameState) -> GamePhase:
        t = state.game_time
        if t < 240:
            return GamePhase.OPENING
        elif t < 480:
            return GamePhase.EARLY_MID
        elif t < 840:
            return GamePhase.MID
        elif t < 1200:
            return GamePhase.LATE_MID
        return GamePhase.LATE

    def _army_strength_ratio(self, state: GameState) -> float:
        if state.opponent_army_supply == 0:
            return 2.0
        return state.army_supply / max(state.opponent_army_supply, 1)

    # ------------------------------------------------------------------
    # Core plan generators
    # ------------------------------------------------------------------

    def timing_attack(self, state: GameState) -> Optional[StrategicPlan]:
        """Return a timing-attack plan when army is strong enough."""
        if state.army_supply < self.MIN_ARMY_FOR_TIMING:
            return None
        ratio = self._army_strength_ratio(state)
        if ratio < 0.8:
            return None

        plan = StrategicPlan(
            plan_type=PlanType.TIMING_ATTACK,
            priority=min(0.4 + ratio * 0.2, 0.95),
            trigger_supply=state.supply_used,
            description="Execute army timing attack before opponent can consolidate.",
            estimated_timing=state.game_time + 30,
        )
        plan.add_action("Move army to opponent natural ramp")
        plan.add_action("Produce reinforcement units from all hatches")
        if state.has_lair:
            plan.add_action("Spread overlords for vision coverage")
        plan.add_action("Target production buildings first")
        return plan

    def expand_to_third(self, state: GameState) -> Optional[StrategicPlan]:
        """Return expansion plan when economy supports a third base."""
        already_three = state.base_count >= 3
        if already_three:
            return None
        needs_minerals = state.minerals >= self.EXPAND_MINERAL_BANK
        needs_workers = state.worker_count >= self.IDEAL_WORKER_THIRD
        if not (needs_minerals or needs_workers):
            return None

        priority = 0.6 if needs_workers else 0.4
        plan = StrategicPlan(
            plan_type=PlanType.EXPAND_THIRD,
            priority=priority,
            trigger_supply=state.supply_used,
            description="Take third base to sustain economy for late-game.",
            estimated_timing=state.game_time + 15,
        )
        plan.add_action("Send drone to third expansion site")
        plan.add_action("Produce overlord to raise supply cap")
        plan.add_action("Transfer 4 drones to new hatchery minerals")
        return plan

    def tech_switch(self, state: GameState) -> Optional[StrategicPlan]:
        """Return tech-switch plan when current army is countered."""
        if not state.has_lair:
            return None

        plan = StrategicPlan(
            plan_type=PlanType.TECH_SWITCH,
            priority=0.55,
            trigger_supply=state.supply_used,
            description="Transition army composition to counter opponent tech.",
        )

        opp = state.opponent_race.lower()
        if opp == "terran":
            if not state.has_roach_warren:
                plan.add_action("Build Roach Warren for roach/ravager anti-bio")
            else:
                plan.add_action("Research Glial Reconstitution (roach speed)")
                plan.add_action("Add Ravager production for forcefield denial")
        elif opp == "protoss":
            if not state.has_hydralisk_den:
                plan.add_action("Build Hydralisk Den for anti-air vs skytoss")
            plan.add_action("Research Grooved Spines (hydra range)")
        elif opp == "zerg":
            if not state.has_spire:
                plan.add_action("Build Spire for mutalisk harass")
            plan.add_action("Research Zerg Flyer Attacks")
        return plan

    # ------------------------------------------------------------------
    # Master planner
    # ------------------------------------------------------------------

    def generate_plans(self, state: GameState) -> List[StrategicPlan]:
        """Generate all applicable plans sorted by priority (highest first)."""
        phase = self.analyze_phase(state)
        plans: List[StrategicPlan] = []

        if phase in (GamePhase.EARLY_MID, GamePhase.MID):
            p = self.timing_attack(state)
            if p:
                plans.append(p)

        if phase in (GamePhase.MID, GamePhase.LATE_MID):
            p = self.expand_to_third(state)
            if p:
                plans.append(p)
            p = self.tech_switch(state)
            if p:
                plans.append(p)

        if not plans:
            # Default: drone up and macro
            plans.append(
                StrategicPlan(
                    plan_type=PlanType.DRONE_UP,
                    priority=0.3,
                    trigger_supply=state.supply_used,
                    description="Macro phase: saturate workers and bank resources.",
                    actions=[
                        "Produce drones until 66% worker ratio",
                        "Inject all queens",
                    ],
                )
            )

        plans.sort(key=lambda p: p.priority, reverse=True)
        self._plan_history.extend(plans)
        return plans

    def top_plan(self, state: GameState) -> StrategicPlan:
        """Return the single highest-priority plan."""
        return self.generate_plans(state)[0]

    def get_economy_efficiency(self, state: GameState) -> Dict[str, float]:
        """Return efficiency metrics for economy management."""
        worker_ratio = state.worker_count / max(state.supply_used, 1)
        army_ratio = state.army_supply / max(state.supply_used, 1)
        bank_ratio = (state.minerals + state.vespene) / max(
            state.income_minerals + state.income_vespene, 1
        )
        return {
            "worker_ratio": round(worker_ratio, 3),
            "army_ratio": round(army_ratio, 3),
            "bank_ratio": round(bank_ratio, 3),
            "income_minerals": state.income_minerals,
            "income_vespene": state.income_vespene,
        }
