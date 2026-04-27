"""
Swarm Behavior Module #18 - SwarmRush.
Units pack into a very tight cluster (radius=1.0) and rush forward (+x),
overwhelming the enemy through concentrated charge.
"""

import math
from typing import List, Tuple
from .formation_controller import FormationController, Position

_RUSH_RADIUS = 1.0
_RUSH_ADVANCE = 3.0   # eastward shift per tick


class Behavior18:
    """SwarmRush: tightly-packed cluster (radius=1.0) advancing east each tick."""

    def __init__(self) -> None:
        self.controller = FormationController()
        self.name = "behavior_18"

    def tick(self, positions: List[Position]) -> List[Position]:
        """
        Cluster all units tightly around the centroid then shift the cluster
        eastward by _RUSH_ADVANCE units.

        Args:
            positions: Current (x, y) positions for each unit.

        Returns:
            Target positions of the rushing cluster.
        """
        if not positions:
            return []

        n = len(positions)
        cx = sum(p[0] for p in positions) / n
        cy = sum(p[1] for p in positions) / n

        if n == 1:
            return [(cx + _RUSH_ADVANCE, cy)]

        targets: List[Position] = []
        for i in range(n):
            angle = (2 * math.pi * i) / n
            tx = cx + _RUSH_RADIUS * math.cos(angle) + _RUSH_ADVANCE
            ty = cy + _RUSH_RADIUS * math.sin(angle)
            targets.append((tx, ty))

        return targets

    def __repr__(self) -> str:
        return f"{self.__class__.__name__}()"
