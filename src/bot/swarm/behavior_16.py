"""
Swarm Behavior Module #16 - PincerMovement.
First half of units flank north (left), second half flank south (right),
creating a classic pincer squeeze around the enemy.
"""

import math
from typing import List, Tuple
from .formation_controller import FormationController, Position

_PINCER_OFFSET = 4.0   # lateral offset from centroid for each arm


class Behavior16:
    """PincerMovement: first half of units flank left, second half flank right."""

    def __init__(self) -> None:
        self.controller = FormationController()
        self.name = "behavior_16"

    def tick(self, positions: List[Position]) -> List[Position]:
        """
        Split the group at the midpoint: lower-indexed units move to the north
        flank, higher-indexed units to the south flank.

        Args:
            positions: Current (x, y) positions for each unit.

        Returns:
            Target positions forming the two-arm pincer.
        """
        if not positions:
            return []

        n = len(positions)
        cx = sum(p[0] for p in positions) / n
        cy = sum(p[1] for p in positions) / n

        mid = n // 2
        targets: List[Position] = []

        for i in range(n):
            if i < mid:
                # Left (north) arm: offset +y
                slot = i - (mid - 1) / 2.0
                tx = cx + slot * 2.0
                ty = cy + _PINCER_OFFSET
            else:
                # Right (south) arm: offset -y
                slot = (i - mid) - (n - mid - 1) / 2.0
                tx = cx + slot * 2.0
                ty = cy - _PINCER_OFFSET
            targets.append((tx, ty))

        return targets

    def __repr__(self) -> str:
        return f"{self.__class__.__name__}()"
