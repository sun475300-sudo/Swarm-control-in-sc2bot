# -*- coding: utf-8 -*-
"""
Formation Controller for Swarm Behavior Modules.

Provides geometric formation management for coordinated unit positioning.
Units are arranged in configurable formations (circular, line, or spread)
around a shared centroid calculated from their current positions.
"""

from __future__ import annotations

import math
from typing import List, Tuple, Union


# Position type: (x, y) tuple or object with x/y attributes
Position = Union[Tuple[float, float], object]


def _to_xy(pos: Position) -> Tuple[float, float]:
    """Extract (x, y) from a position tuple or object with .x/.y attributes."""
    if isinstance(pos, (tuple, list)):
        return (float(pos[0]), float(pos[1]))
    return (float(getattr(pos, "x", 0.0)), float(getattr(pos, "y", 0.0)))


class FormationController:
    """
    Controller for maintaining geometric unit formations.

    Calculates target positions for units to maintain a formation pattern
    (circular, line, or spread) centred on the group's current centroid.
    """

    def __init__(
        self,
        formation_radius: float = 3.0,
        formation_type: str = "circle",
    ) -> None:
        """
        Initialize formation controller.

        Args:
            formation_radius: Desired spacing/radius between units in the
                formation.  For circular formations this is the orbit radius;
                for line/spread formations it is the gap between adjacent slots.
            formation_type: Formation shape — ``'circle'``, ``'line'``, or
                ``'spread'``.
        """
        self.formation_radius = formation_radius
        self.formation_type = formation_type

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _centroid(positions: List[Tuple[float, float]]) -> Tuple[float, float]:
        """Return the arithmetic centroid of *positions*."""
        if not positions:
            return (0.0, 0.0)
        cx = sum(p[0] for p in positions) / len(positions)
        cy = sum(p[1] for p in positions) / len(positions)
        return (cx, cy)

    def _circular_targets(
        self,
        centroid: Tuple[float, float],
        count: int,
    ) -> List[Tuple[float, float]]:
        """Place *count* units evenly on a circle centred at *centroid*."""
        targets: List[Tuple[float, float]] = []
        for i in range(count):
            angle = 2.0 * math.pi * i / count
            x = centroid[0] + self.formation_radius * math.cos(angle)
            y = centroid[1] + self.formation_radius * math.sin(angle)
            targets.append((x, y))
        return targets

    def _line_targets(
        self,
        centroid: Tuple[float, float],
        count: int,
    ) -> List[Tuple[float, float]]:
        """Place *count* units in a horizontal line centred at *centroid*."""
        targets: List[Tuple[float, float]] = []
        total_width = (count - 1) * self.formation_radius
        start_x = centroid[0] - total_width / 2.0
        for i in range(count):
            x = start_x + i * self.formation_radius
            targets.append((x, centroid[1]))
        return targets

    def _spread_targets(
        self,
        centroid: Tuple[float, float],
        count: int,
    ) -> List[Tuple[float, float]]:
        """Place *count* units in a grid/cluster centred at *centroid*.

        The centroid of the returned target positions is guaranteed to equal
        *centroid*, even when the grid is only partially filled.
        """
        cols = max(1, math.ceil(math.sqrt(count)))
        # Generate raw slot positions (origin-relative)
        raw: List[Tuple[float, float]] = []
        for i in range(count):
            col = i % cols
            row = i // cols
            raw.append((col * self.formation_radius, row * self.formation_radius))
        # Centre the raw slots on the input centroid
        raw_cx = sum(x for x, _ in raw) / count
        raw_cy = sum(y for _, y in raw) / count
        dx = centroid[0] - raw_cx
        dy = centroid[1] - raw_cy
        return [(x + dx, y + dy) for x, y in raw]

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def maintain_formation(self, positions: List[Position]) -> List[Tuple[float, float]]:
        """
        Calculate target positions to maintain a formation.

        The formation is always centred on the centroid of the provided
        *positions*, so the group translates as a whole without drifting.

        Args:
            positions: Current unit positions — either ``(x, y)`` tuples or
                objects that expose ``.x`` and ``.y`` attributes (e.g. SC2
                ``Point2`` instances).

        Returns:
            A list of ``(x, y)`` target positions, one entry per input unit,
            ordered to match the input list.
        """
        if not positions:
            return []

        xy_positions = [_to_xy(p) for p in positions]
        centroid = self._centroid(xy_positions)
        count = len(xy_positions)

        if self.formation_type == "circle":
            targets = self._circular_targets(centroid, count)
        elif self.formation_type == "line":
            targets = self._line_targets(centroid, count)
        else:  # "spread" or any unrecognised value
            targets = self._spread_targets(centroid, count)

        return targets
