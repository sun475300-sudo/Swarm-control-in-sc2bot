"""
Swarm Behavior Module #17 - AmbushHold.
Units cluster tightly around the centroid (radius=1.5) and hold position,
ready to burst out on command.
"""

import math
from typing import List, Tuple
from .formation_controller import FormationController, Position

_AMBUSH_RADIUS = 1.5


class Behavior17:
    """AmbushHold: tight cluster (radius=1.5) around centroid for concealed hold."""

    def __init__(self) -> None:
        self.controller = FormationController()
        self.name = "behavior_17"

    def tick(self, positions: List[Position]) -> List[Position]:
        """
        Pack all units into a very tight ring of radius 1.5 around the centroid.

        Args:
            positions: Current (x, y) positions for each unit.

        Returns:
            Target positions in the tight ambush cluster.
        """
        if not positions:
            return []

        n = len(positions)
        cx = sum(p[0] for p in positions) / n
        cy = sum(p[1] for p in positions) / n

        if n == 1:
            return [(cx, cy)]

        targets: List[Position] = []
        for i in range(n):
            angle = (2 * math.pi * i) / n
            tx = cx + _AMBUSH_RADIUS * math.cos(angle)
            ty = cy + _AMBUSH_RADIUS * math.sin(angle)
            targets.append((tx, ty))

        return targets

    def __repr__(self) -> str:
        return f"{self.__class__.__name__}()"
