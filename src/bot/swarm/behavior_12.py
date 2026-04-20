"""
Swarm Behavior Module #12 - DefensiveCircle.
Units form a larger defensive perimeter circle (radius=5.0) around the centroid.
"""

import math
from typing import List, Tuple
from .formation_controller import FormationController, Position

_DEFENSE_RADIUS = 5.0


class Behavior12:
    """DefensiveCircle: circular formation with a wider radius=5.0 for defense."""

    def __init__(self) -> None:
        self.controller = FormationController()
        self.name = "behavior_12"

    def tick(self, positions: List[Position]) -> List[Position]:
        """
        Arrange units in an evenly-spaced ring of radius 5.0 around the centroid.

        Args:
            positions: Current (x, y) positions for each unit.

        Returns:
            Target positions on the defensive perimeter.
        """
        if not positions:
            return []

        n = len(positions)
        cx = sum(p[0] for p in positions) / n
        cy = sum(p[1] for p in positions) / n

        targets: List[Position] = []
        for i in range(n):
            angle = (2 * math.pi * i) / n
            tx = cx + _DEFENSE_RADIUS * math.cos(angle)
            ty = cy + _DEFENSE_RADIUS * math.sin(angle)
            targets.append((tx, ty))

        return targets

    def __repr__(self) -> str:
        return f"{self.__class__.__name__}()"
