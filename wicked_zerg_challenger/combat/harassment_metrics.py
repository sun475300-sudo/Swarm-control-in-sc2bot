"""Harassment metrics + penetration verification (PLAN-NIGHTLY P1.2).

Layered on top of HarassmentExtensionMixin. Where the mixin decides *what
each unit does this tick*, this module answers three questions the mixin
cannot:

1. **Did the harass actually reach enemy main?** (penetration_success)
2. **How many enemy workers has it killed?** (workers_killed)
3. **Did the retreat succeed?** (retreat_success)

These metrics feed the paper's cross-domain contribution (Contribution 3
in PAPER_DRAFT.md) — "same compositional pattern wins in both UAV and
SC2 domains" needs numerical proof from the SC2 side.

Determinism guarantees:
    * No I/O, no time.time().
    * Pure functions where possible.
    * The stateful counter class updates only when explicit events are
      pushed through the ``on_unit_died`` / ``on_position`` methods.

Usage (integration into StrategyManager or CombatManager)::

    from wicked_zerg_challenger.combat.harassment_metrics import (
        HarassmentMetrics,
    )

    metrics = HarassmentMetrics(enemy_main_position=(80, 50), penetration_radius_m=15.0)

    # Every tick:
    for unit in harassment_units:
        metrics.on_position(unit.tag, (unit.position.x, unit.position.y))

    # On step-end death events:
    for tag, unit_type in dead_workers_this_tick:
        metrics.on_unit_died(tag, unit_type, killer_type="ZERGLING")

    # At any point:
    summary = metrics.summary()
    # -> {"workers_killed": 5, "penetration_success": True, "retreat_success": 2, ...}
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, Optional, Set, Tuple


Position2D = Tuple[float, float]

# Unit type strings we treat as "workers" — matches the SC2 UnitTypeId enum
# member names so we do not need to import the enum here.
_WORKER_TYPES: Set[str] = {"SCV", "PROBE", "DRONE", "MULE"}

# Unit type strings we accept as "harass units" for the killer credit.
_HARASS_TYPES: Set[str] = {"ZERGLING", "MUTALISK", "BANELING", "ROACH"}


def is_worker(unit_type: str) -> bool:
    """Return True if the given SC2 UnitTypeId name is a worker."""
    return unit_type.upper() in _WORKER_TYPES


def is_harass_unit(unit_type: str) -> bool:
    """Return True if the given SC2 UnitTypeId name is a harass unit."""
    return unit_type.upper() in _HARASS_TYPES


def distance2d(a: Position2D, b: Position2D) -> float:
    """Euclidean 2D distance."""
    return ((a[0] - b[0]) ** 2 + (a[1] - b[1]) ** 2) ** 0.5


@dataclass
class HarassmentEpisode:
    """One send-out cycle of the harass unit.

    An episode starts when a harass unit's position first crosses within
    ``penetration_radius`` of enemy main and ends when it either dies or
    leaves the enemy main region for the base recovery zone.
    """

    unit_tag: int
    penetrated: bool = False
    penetrated_at_position: Optional[Position2D] = None
    workers_killed: int = 0
    retreated_alive: bool = False
    died: bool = False


class HarassmentMetrics:
    """Track per-episode harassment stats deterministically.

    Args:
        enemy_main_position: (x, y) of enemy main base.
        penetration_radius_m: How close (in map tiles) a harass unit must
            get to enemy main to count as "penetrated". Default 15 tiles.
        retreat_zone_position: (x, y) of own base / rally point. Used to
            detect "successfully retreated" if unit reaches this zone alive.
        retreat_zone_radius_m: How close to retreat_zone counts as arrived.
    """

    def __init__(
        self,
        enemy_main_position: Position2D,
        penetration_radius_m: float = 15.0,
        retreat_zone_position: Optional[Position2D] = None,
        retreat_zone_radius_m: float = 10.0,
    ) -> None:
        self.enemy_main = enemy_main_position
        self.penetration_radius = float(penetration_radius_m)
        self.retreat_zone = retreat_zone_position
        self.retreat_radius = float(retreat_zone_radius_m)

        self._episodes: Dict[int, HarassmentEpisode] = {}
        self._total_workers_killed = 0
        self._total_penetrations = 0
        self._total_retreats_alive = 0
        self._total_deaths = 0

    # ------------------------------------------------------------------
    # Events
    # ------------------------------------------------------------------

    def on_position(self, unit_tag: int, position: Position2D) -> None:
        """Called every tick with the harass unit's current position.

        Creates/updates the unit's episode. First entry into the enemy
        main radius flips ``penetrated=True``. Arrival at the retreat
        zone (if defined) flips ``retreated_alive=True`` and closes the
        episode.
        """
        ep = self._episodes.get(unit_tag)
        if ep is None:
            ep = HarassmentEpisode(unit_tag=unit_tag)
            self._episodes[unit_tag] = ep

        if not ep.penetrated:
            if distance2d(position, self.enemy_main) <= self.penetration_radius:
                ep.penetrated = True
                ep.penetrated_at_position = position
                self._total_penetrations += 1

        if self.retreat_zone is not None and not ep.retreated_alive and not ep.died:
            if (
                ep.penetrated
                and distance2d(position, self.retreat_zone) <= self.retreat_radius
            ):
                ep.retreated_alive = True
                self._total_retreats_alive += 1

    def on_unit_died(
        self,
        dead_tag: int,
        dead_type: str,
        killer_type: Optional[str] = None,
        killer_tag: Optional[int] = None,
    ) -> None:
        """Called when a unit dies.

        If ``dead_type`` is a worker and ``killer_type`` is a harass
        unit, credit the killer's episode with +1 worker kill. If
        ``dead_type`` is a harass unit, close its episode with died=True.
        """
        if is_worker(dead_type) and killer_type is not None and is_harass_unit(killer_type):
            self._total_workers_killed += 1
            if killer_tag is not None:
                ep = self._episodes.get(killer_tag)
                if ep is None:
                    ep = HarassmentEpisode(unit_tag=killer_tag)
                    self._episodes[killer_tag] = ep
                ep.workers_killed += 1

        if is_harass_unit(dead_type):
            ep = self._episodes.get(dead_tag)
            if ep is None:
                ep = HarassmentEpisode(unit_tag=dead_tag)
                self._episodes[dead_tag] = ep
            ep.died = True
            self._total_deaths += 1

    # ------------------------------------------------------------------
    # Read-only accessors
    # ------------------------------------------------------------------

    def summary(self) -> Dict[str, float]:
        """Return current snapshot. Safe to call any time."""
        n_ep = len(self._episodes)
        return {
            "episodes": float(n_ep),
            "workers_killed": float(self._total_workers_killed),
            "workers_killed_per_episode": (
                self._total_workers_killed / n_ep if n_ep else 0.0
            ),
            "penetrations": float(self._total_penetrations),
            "penetration_rate": (
                self._total_penetrations / n_ep if n_ep else 0.0
            ),
            "retreats_alive": float(self._total_retreats_alive),
            "retreat_success_rate": (
                self._total_retreats_alive / self._total_penetrations
                if self._total_penetrations
                else 0.0
            ),
            "deaths": float(self._total_deaths),
            "kd_ratio": (
                self._total_workers_killed / self._total_deaths
                if self._total_deaths
                else float("inf") if self._total_workers_killed else 0.0
            ),
        }

    def episode_for(self, unit_tag: int) -> Optional[HarassmentEpisode]:
        return self._episodes.get(unit_tag)

    def reset(self) -> None:
        """Wipe state — call between games."""
        self._episodes.clear()
        self._total_workers_killed = 0
        self._total_penetrations = 0
        self._total_retreats_alive = 0
        self._total_deaths = 0


__all__ = [
    "HarassmentMetrics",
    "HarassmentEpisode",
    "is_worker",
    "is_harass_unit",
    "distance2d",
]
