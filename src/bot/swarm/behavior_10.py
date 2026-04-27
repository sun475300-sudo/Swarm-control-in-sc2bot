"""
Swarm Behavior Module #10 - SurroundAndAttack.
Encirclement that tightens its radius over time, starting at 8.0 and
shrinking by 0.1 per tick down to a minimum of 2.0.
"""

import math
from typing import List, Tuple
from .formation_controller import FormationController, Position

_INITIAL_RADIUS = 8.0
_SHRINK_RATE = 0.1
_MIN_RADIUS = 2.0


class Behavior10:
    """SurroundAndAttack: encirclement with tightening radius each tick."""

    def __init__(self) -> None:
        self.controller = FormationController()
        self.name = "behavior_10"
        self._tick_count: int = 0

    def tick(self, positions: List[Position]) -> List[Position]:
        """
        Place units on a shrinking encirclement ring.  Radius starts at 8.0
        and decreases by 0.1 each tick, clamped to a minimum of 2.0.

        Args:
            positions: Current (x, y) positions for each unit.

        Returns:
            Target positions on the tightening circle.
        """
        if not positions:
            return []

        radius = max(_MIN_RADIUS, _INITIAL_RADIUS - self._tick_count * _SHRINK_RATE)
        self._tick_count += 1

        n = len(positions)
        cx = sum(p[0] for p in positions) / n
        cy = sum(p[1] for p in positions) / n

        targets: List[Position] = []
        for i in range(n):
            angle = (2 * math.pi * i) / n
            tx = cx + radius * math.cos(angle)
            ty = cy + radius * math.sin(angle)
            targets.append((tx, ty))

        return targets

    def __repr__(self) -> str:
        return f"{self.__class__.__name__}()"
