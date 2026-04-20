# -*- coding: utf-8 -*-
"""
FormationController for Swarm Behavior Modules.

Provides base formation maintenance used by all behavior_*.py modules.
"""

import math
from typing import List, Tuple

Position = Tuple[float, float]


class FormationController:
    """
    Lightweight formation controller for swarm behavior modules.

    Manages a group of unit positions and computes target positions
    that maintain the desired formation shape and spacing.
    """

    def __init__(self, formation_radius: float = 3.0) -> None:
        self.formation_radius = formation_radius
        self._center: Position = (0.0, 0.0)

    # ------------------------------------------------------------------
    # Core helpers
    # ------------------------------------------------------------------

    def _centroid(self, positions: List[Position]) -> Position:
        if not positions:
            return (0.0, 0.0)
        cx = sum(p[0] for p in positions) / len(positions)
        cy = sum(p[1] for p in positions) / len(positions)
        return (cx, cy)

    def _dist(self, a: Position, b: Position) -> float:
        return math.hypot(a[0] - b[0], a[1] - b[1])

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def maintain_formation(self, positions: List[Position]) -> List[Position]:
        """
        Return target positions that keep units in a circular formation
        around the current centroid.

        Args:
            positions: Current (x, y) positions for each unit.

        Returns:
            Target (x, y) positions in the same order.
        """
        if not positions:
            return []

        n = len(positions)
        self._center = self._centroid(positions)

        if n == 1:
            return list(positions)

        # Evenly-spaced ring around centroid
        targets: List[Position] = []
        for i in range(n):
            angle = (2 * math.pi * i) / n
            tx = self._center[0] + self.formation_radius * math.cos(angle)
            ty = self._center[1] + self.formation_radius * math.sin(angle)
            targets.append((tx, ty))

        return targets

    def spread_formation(self, positions: List[Position], spread: float = 6.0) -> List[Position]:
        """Push units away from centroid by `spread` units."""
        if not positions:
            return []

        n = len(positions)
        self._center = self._centroid(positions)

        targets: List[Position] = []
        for i in range(n):
            angle = (2 * math.pi * i) / n
            tx = self._center[0] + spread * math.cos(angle)
            ty = self._center[1] + spread * math.sin(angle)
            targets.append((tx, ty))

        return targets

    def wedge_formation(self, positions: List[Position], direction: float = 0.0) -> List[Position]:
        """
        Wedge (V-shape) pointing in `direction` radians.

        Args:
            positions: Current unit positions.
            direction: Heading in radians (0 = east).
        """
        if not positions:
            return []

        n = len(positions)
        self._center = self._centroid(positions)

        targets: List[Position] = []
        half_angle = math.pi / 4  # 45-degree half-spread

        for i in range(n):
            # Distribute units in a V behind the leader
            side = -1 if i % 2 == 0 else 1
            row = (i + 1) // 2
            angle = direction + math.pi + side * half_angle * (row / max(n, 1))
            dist = self.formation_radius * row
            tx = self._center[0] + dist * math.cos(angle)
            ty = self._center[1] + dist * math.sin(angle)
            targets.append((tx, ty))

        return targets

    def line_formation(self, positions: List[Position], direction: float = 0.0) -> List[Position]:
        """Units in a horizontal line perpendicular to `direction`."""
        if not positions:
            return []

        n = len(positions)
        self._center = self._centroid(positions)

        perp = direction + math.pi / 2
        targets: List[Position] = []

        for i in range(n):
            offset = (i - (n - 1) / 2.0) * self.formation_radius
            tx = self._center[0] + offset * math.cos(perp)
            ty = self._center[1] + offset * math.sin(perp)
            targets.append((tx, ty))

        return targets
