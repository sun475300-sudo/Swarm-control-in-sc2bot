"""
Swarm Behavior Module #5 - Encircle.
Distribute units evenly in a large circle around the centroid.
"""

import math
from typing import List, Tuple
from .formation_controller import FormationController, Position

_ENCIRCLE_RADIUS = 8.0


class Behavior05:
    """Encircle: distribute units evenly in a large circle (radius=8.0) around centroid."""

    def __init__(self) -> None:
        self.controller = FormationController()
        self.name = "behavior_05"

    def tick(self, positions: List[Position]) -> List[Position]:
        """
        Place each unit on a circle of radius 8.0 around the group centroid.

        Args:
            positions: Current (x, y) positions for each unit.

        Returns:
            Target positions evenly distributed on the encirclement circle.
        """
        if not positions:
            return []

        n = len(positions)
        cx = sum(p[0] for p in positions) / n
        cy = sum(p[1] for p in positions) / n

        targets: List[Position] = []
        for i in range(n):
            angle = (2 * math.pi * i) / n
            tx = cx + _ENCIRCLE_RADIUS * math.cos(angle)
            ty = cy + _ENCIRCLE_RADIUS * math.sin(angle)
            targets.append((tx, ty))

        return targets

    def __repr__(self) -> str:
        return f"{self.__class__.__name__}()"
