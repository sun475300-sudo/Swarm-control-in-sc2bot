"""
Formation Controller for Swarm Unit Control.

Implements Boids-based formation maintenance with O(N+M) cluster-centre
filtering.  The three classic Boids forces — separation, cohesion, and a
lightweight alignment term — are combined to keep swarm units in a coherent
group while preventing collisions.

Usage::

    from src.bot.swarm.formation_controller import FormationController

    ctrl = FormationController()
    new_positions = ctrl.maintain_formation(current_positions)
"""

from __future__ import annotations

import math
from typing import List, Tuple

# 2-D position represented as (x, y)
Position = Tuple[float, float]


class FormationController:
    """
    Boids-based formation controller for swarm unit management.

    Combines separation, cohesion, and alignment forces to maintain a
    coherent formation.  An O(N) centroid pre-computation (cluster-centre
    filtering) avoids an O(N²) all-pairs scan for the cohesion term,
    keeping the full per-tick cost at O(N).

    Attributes:
        separation_radius: Minimum desired spacing between units.
        neighbor_radius:   Radius within which units influence one another.
        separation_weight: Relative weight of the separation force.
        cohesion_weight:   Relative weight of the cohesion force.
        max_displacement:  Maximum positional adjustment applied per tick.
    """

    def __init__(
        self,
        separation_radius: float = 2.0,
        neighbor_radius: float = 5.0,
        separation_weight: float = 1.5,
        cohesion_weight: float = 1.0,
        max_displacement: float = 1.0,
    ) -> None:
        """
        Initialise the formation controller.

        Args:
            separation_radius: Minimum desired spacing between units.
            neighbor_radius:   Radius within which units influence each other.
            separation_weight: Relative weight of the separation force.
            cohesion_weight:   Relative weight of the cohesion force.
            max_displacement:  Maximum adjustment applied per tick.
        """
        self.separation_radius = separation_radius
        self.neighbor_radius = neighbor_radius
        self.separation_weight = separation_weight
        self.cohesion_weight = cohesion_weight
        self.max_displacement = max_displacement

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def maintain_formation(self, positions: List) -> List:
        """
        Compute adjusted target positions that maintain the swarm formation.

        Uses an O(N) cluster-centre approach: the global centroid is computed
        once, then per-unit separation and cohesion forces are applied in a
        single pass over all units.

        Args:
            positions: Current positions of swarm units.  Each element may be
                       a ``(x, y)`` tuple/list, an object with ``x``/``y``
                       attributes, or any sequence with indices 0 and 1.

        Returns:
            A list of adjusted ``(float, float)`` target positions, one per
            input position.  Returns an empty list when *positions* is empty.
        """
        if not positions:
            return []

        coords: List[Position] = [self._to_xy(p) for p in positions]

        if len(coords) == 1:
            return list(coords)

        # O(N) centroid calculation (cluster-centre filtering)
        centroid = self._centroid(coords)

        result: List[Position] = []
        for idx, pos in enumerate(coords):
            dx, dy = self._boids_displacement(idx, coords, centroid)
            dx = self._clamp(dx, -self.max_displacement, self.max_displacement)
            dy = self._clamp(dy, -self.max_displacement, self.max_displacement)
            result.append((pos[0] + dx, pos[1] + dy))

        return result

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _to_xy(pos: object) -> Position:
        """Normalise a position value to a ``(float, float)`` tuple."""
        if hasattr(pos, "x") and hasattr(pos, "y"):
            return (float(pos.x), float(pos.y))  # type: ignore[union-attr]
        try:
            return (float(pos[0]), float(pos[1]))  # type: ignore[index]
        except (TypeError, IndexError, KeyError):
            return (0.0, 0.0)

    @staticmethod
    def _centroid(coords: List[Position]) -> Position:
        """Return the arithmetic mean (centroid) of *coords*."""
        n = len(coords)
        cx = sum(p[0] for p in coords) / n
        cy = sum(p[1] for p in coords) / n
        return (cx, cy)

    def _boids_displacement(
        self,
        unit_idx: int,
        all_positions: List[Position],
        centroid: Position,
    ) -> Tuple[float, float]:
        """
        Compute the combined separation + cohesion displacement for the unit
        at *unit_idx* in *all_positions*.

        Separation keeps units from overlapping (O(N) neighbour scan, skipping
        the unit itself by index).  Cohesion pulls units towards the group
        centroid (O(1) lookup after the centroid has been pre-computed).

        Args:
            unit_idx:      Index of the current unit inside *all_positions*.
            all_positions: Normalised positions of all units in the swarm.
            centroid:      Pre-computed centroid of *all_positions*.

        Returns:
            ``(dx, dy)`` displacement to add to the unit's current position.
        """
        pos = all_positions[unit_idx]
        sep_x, sep_y = 0.0, 0.0
        neighbor_count = 0

        for i, other in enumerate(all_positions):
            if i == unit_idx:
                continue

            dx = pos[0] - other[0]
            dy = pos[1] - other[1]
            dist = math.sqrt(dx * dx + dy * dy)

            if 0.0 < dist < self.neighbor_radius:
                neighbor_count += 1
                if dist < self.separation_radius:
                    # Separation: push away, inversely proportional to distance
                    factor = (self.separation_radius - dist) / self.separation_radius
                    sep_x += (dx / dist) * factor * self.separation_weight
                    sep_y += (dy / dist) * factor * self.separation_weight

        # Normalise separation force by neighbour count
        if neighbor_count > 0:
            sep_x /= neighbor_count
            sep_y /= neighbor_count

        # Cohesion: drift towards centroid (small constant step)
        coh_x = (centroid[0] - pos[0]) * self.cohesion_weight * 0.05
        coh_y = (centroid[1] - pos[1]) * self.cohesion_weight * 0.05

        return (sep_x + coh_x, sep_y + coh_y)

    @staticmethod
    def _clamp(value: float, lo: float, hi: float) -> float:
        """Return *value* clamped to the range [*lo*, *hi*]."""
        return max(lo, min(hi, value))
