"""
Swarm Behavior Module #19 - SiegeFormation.
Outer ring (ranged, radius=7.0) contains the first half of units;
inner circle (melee, radius=3.0) contains the second half.
"""

import math
from typing import List, Tuple
from .formation_controller import FormationController, Position

_OUTER_RADIUS = 7.0
_INNER_RADIUS = 3.0


class Behavior19:
    """SiegeFormation: outer ranged ring (radius=7) + inner melee ring (radius=3)."""

    def __init__(self) -> None:
        self.controller = FormationController()
        self.name = "behavior_19"

    def tick(self, positions: List[Position]) -> List[Position]:
        """
        Place the first half of units on an outer ring (radius=7.0) and the
        remaining units on an inner ring (radius=3.0) around the centroid.

        Args:
            positions: Current (x, y) positions for each unit.

        Returns:
            Target positions for the siege formation.
        """
        if not positions:
            return []

        n = len(positions)
        cx = sum(p[0] for p in positions) / n
        cy = sum(p[1] for p in positions) / n

        mid = (n + 1) // 2   # first half is ranged (outer)
        outer_count = mid
        inner_count = n - mid

        targets: List[Position] = []

        # Outer ring (first half)
        for i in range(outer_count):
            denom = max(outer_count, 1)
            angle = (2 * math.pi * i) / denom
            tx = cx + _OUTER_RADIUS * math.cos(angle)
            ty = cy + _OUTER_RADIUS * math.sin(angle)
            targets.append((tx, ty))

        # Inner ring (second half)
        for i in range(inner_count):
            denom = max(inner_count, 1)
            angle = (2 * math.pi * i) / denom
            tx = cx + _INNER_RADIUS * math.cos(angle)
            ty = cy + _INNER_RADIUS * math.sin(angle)
            targets.append((tx, ty))

        return targets

    def __repr__(self) -> str:
        return f"{self.__class__.__name__}()"
