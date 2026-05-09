"""Per-phase scout-type cadence (PLAN-NIGHTLY P1.1 / TODO.md priority #1).

Layered on top of AdvancedScoutingSystemV2: where the V2 system decides
*how often* to send a scout, this module decides *which scout type* should
go and *what target* given the game phase.

Phases (game time, not iteration count):

| Phase | Window           | Scout type                  | Cadence  | Targets                          |
|-------|------------------|-----------------------------|----------|----------------------------------|
| 1     | 0:00 -> 3:00      | Overlord (already in air)   | 30 s     | enemy main entrance + ramp top   |
| 2     | 3:00 -> 8:00      | Zergling (cheap, fast)      | 60 s     | map sweep loop (4 quadrants)     |
| 3     | 8:00 +           | Overseer (cloak detection)  | 90 s     | enemy expansion + tech buildings |

Why per-phase:
  * Overlords carry no risk (uncatchable by basic units), free intel early.
  * Zerglings are throwaway by mid game and can sweep multiple quadrants.
  * Overseers expose stalker DT / lurker / banshee - the threats that win
    games when missed.

The cadence numbers are independent of the V2 system's emergency-mode
shortening; that still triggers when intel goes > 60 s stale.

Usage::

    from wicked_zerg_challenger.scouting.phase_scout_cadence import (
        PhaseScoutCadence,
    )
    cadence = PhaseScoutCadence(self.bot)
    plan = cadence.next_dispatch(game_time_s=180.0)
    if plan is not None:
        # plan.unit_type, plan.target, plan.deadline_s
        ...

Determinism:
  * No I/O, no time.time() - all decisions are pure functions of
    (game_time_s, last_dispatch_time_s, enemy_main_position).
  * Replay-based regression: at fixed (seed, map), next_dispatch() at
    t=120, 240, 480 returns the SAME plan structure.
"""
from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import List, Optional, Tuple

try:
    from sc2.bot_ai import BotAI  # type: ignore
    from sc2.ids.unit_typeid import UnitTypeId  # type: ignore
    from sc2.position import Point2  # type: ignore
except ImportError:
    # Allow running this module on systems without the SC2 bindings.
    BotAI = object  # type: ignore
    Point2 = tuple  # type: ignore

    class UnitTypeId:  # type: ignore
        OVERLORD = "OVERLORD"
        ZERGLING = "ZERGLING"
        OVERSEER = "OVERSEER"


# --- Phase-cadence parameters (single source of truth) ---

PHASE_1_END_S = 180.0          # 3:00 - overlord-only window
PHASE_2_END_S = 480.0          # 8:00 - zergling sweep window
PHASE_1_CADENCE_S = 30.0
PHASE_2_CADENCE_S = 60.0
PHASE_3_CADENCE_S = 90.0


class ScoutPhase(Enum):
    """Game-time phase enum used by PhaseScoutCadence."""

    OVERLORD_EARLY = 1     # 0 - 3 min
    ZERGLING_SWEEP = 2     # 3 - 8 min
    OVERSEER_DETECT = 3    # 8 min +


@dataclass(frozen=True)
class DispatchPlan:
    """The decision PhaseScoutCadence emits."""

    phase: ScoutPhase
    unit_type: object              # UnitTypeId.* - string fallback if SC2 unavailable
    target: Point2                 # where to send it
    deadline_s: float              # by when the unit should arrive
    quadrant_index: int = 0        # 0-3 for zergling sweep; 0 for others


def phase_for_time(game_time_s: float) -> ScoutPhase:
    """Map raw game time to the dispatch phase. Pure function."""
    if game_time_s < PHASE_1_END_S:
        return ScoutPhase.OVERLORD_EARLY
    if game_time_s < PHASE_2_END_S:
        return ScoutPhase.ZERGLING_SWEEP
    return ScoutPhase.OVERSEER_DETECT


def cadence_for_phase(phase: ScoutPhase) -> float:
    return {
        ScoutPhase.OVERLORD_EARLY: PHASE_1_CADENCE_S,
        ScoutPhase.ZERGLING_SWEEP: PHASE_2_CADENCE_S,
        ScoutPhase.OVERSEER_DETECT: PHASE_3_CADENCE_S,
    }[phase]


def _quadrant_targets(enemy_main: Point2, map_extent: float) -> List[Point2]:
    """4 sweep targets for zergling phase: NE / SE / SW / NW relative to
    midpoint between own and enemy main."""
    cx, cy = enemy_main[0], enemy_main[1]
    d = map_extent * 0.20
    return [
        Point2((cx + d, cy + d)),
        Point2((cx + d, cy - d)),
        Point2((cx - d, cy - d)),
        Point2((cx - d, cy + d)),
    ]


class PhaseScoutCadence:
    """Stateful wrapper around the pure functions above.

    Tracks the last dispatch time per phase so callers can ask
    ``next_dispatch(game_time_s)`` and get either a DispatchPlan or None
    (if it's not time yet).
    """

    def __init__(self, bot: BotAI) -> None:
        self.bot = bot
        # Last dispatch wall time per phase, indexed by phase enum.
        self._last_dispatch_s: dict = {p: -10**6 for p in ScoutPhase}
        # Round-robin quadrant index for zergling sweep
        self._zergling_quadrant = 0

    # --- Public API -----------------------------------------------------

    def next_dispatch(
        self,
        game_time_s: float,
        enemy_main: Optional[Point2] = None,
    ) -> Optional[DispatchPlan]:
        """Return a DispatchPlan if it's time to send a scout, else None."""
        phase = phase_for_time(game_time_s)
        cadence = cadence_for_phase(phase)
        elapsed_since_last = game_time_s - self._last_dispatch_s[phase]
        if elapsed_since_last < cadence:
            return None

        if enemy_main is None:
            # Best-effort fallback: try to read from the bot if available.
            enemy_main = self._infer_enemy_main()
            if enemy_main is None:
                return None

        plan = self._plan_for(phase, game_time_s, enemy_main)
        self._last_dispatch_s[phase] = game_time_s
        return plan

    # --- Internal -------------------------------------------------------

    def _infer_enemy_main(self) -> Optional[Point2]:
        """Try a few attribute names that AdvancedScoutingSystemV2 exposes."""
        for attr in ("enemy_start_locations", "enemy_main", "enemy_main_position"):
            v = getattr(self.bot, attr, None)
            if v is None:
                continue
            if isinstance(v, (list, tuple)) and len(v) > 0:
                return v[0]
            return v
        return None

    def _plan_for(
        self,
        phase: ScoutPhase,
        game_time_s: float,
        enemy_main: Point2,
    ) -> DispatchPlan:
        if phase is ScoutPhase.OVERLORD_EARLY:
            target = enemy_main
            return DispatchPlan(
                phase=phase,
                unit_type=getattr(UnitTypeId, "OVERLORD", "OVERLORD"),
                target=target,
                deadline_s=game_time_s + 60.0,
            )
        if phase is ScoutPhase.ZERGLING_SWEEP:
            map_extent = self._estimate_map_extent()
            quads = _quadrant_targets(enemy_main, map_extent)
            qi = self._zergling_quadrant % 4
            self._zergling_quadrant = (self._zergling_quadrant + 1) % 4
            return DispatchPlan(
                phase=phase,
                unit_type=getattr(UnitTypeId, "ZERGLING", "ZERGLING"),
                target=quads[qi],
                deadline_s=game_time_s + 120.0,
                quadrant_index=qi,
            )
        # Phase 3 - Overseer detect
        return DispatchPlan(
            phase=phase,
            unit_type=getattr(UnitTypeId, "OVERSEER", "OVERSEER"),
            target=enemy_main,
            deadline_s=game_time_s + 90.0,
        )

    def _estimate_map_extent(self) -> float:
        """Rough map extent in tiles. Returns 100.0 if bot info unavailable."""
        gi = getattr(self.bot, "game_info", None)
        if gi is not None:
            playable = getattr(gi, "playable_area", None)
            if playable is not None:
                w = getattr(playable, "width", None)
                h = getattr(playable, "height", None)
                if w is not None and h is not None:
                    return float(max(w, h))
        return 100.0


__all__ = [
    "PhaseScoutCadence",
    "ScoutPhase",
    "DispatchPlan",
    "phase_for_time",
    "cadence_for_phase",
    "PHASE_1_END_S",
    "PHASE_2_END_S",
    "PHASE_1_CADENCE_S",
    "PHASE_2_CADENCE_S",
    "PHASE_3_CADENCE_S",
]
