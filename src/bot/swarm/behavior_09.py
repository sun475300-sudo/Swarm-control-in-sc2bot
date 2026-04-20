"""
Swarm Behavior Module #9 - PatrolCircle.
Units maintain a circular ring around the centroid but rotate their angular
offset by a fixed step each tick, producing a spinning patrol pattern.
"""

import math
from typing import List, Tuple
from .formation_controller import FormationController, Position

_ROTATION_STEP = 0.05   # radians per tick
_PATROL_RADIUS = 3.0


class Behavior09:
    """PatrolCircle: circular ring formation that rotates by 0.05 rad per tick."""

    def __init__(self) -> None:
        self.controller = FormationController()
        self.name = "behavior_09"
        self._angle: float = 0.0

    def tick(self, positions: List[Position]) -> List[Position]:
        """
        Place units on a rotating ring around the centroid.  The ring's phase
        angle increments by _ROTATION_STEP each call, making the formation spin.

        Args:
            positions: Current (x, y) positions for each unit.

        Returns:
            Target positions on the rotated ring.
        """
        if not positions:
            return []

        n = len(positions)
        cx = sum(p[0] for p in positions) / n
        cy = sum(p[1] for p in positions) / n

        # Advance patrol angle
        self._angle += _ROTATION_STEP

        targets: List[Position] = []
        for i in range(n):
            angle = self._angle + (2 * math.pi * i) / n
            tx = cx + _PATROL_RADIUS * math.cos(angle)
            ty = cy + _PATROL_RADIUS * math.sin(angle)
            targets.append((tx, ty))

        return targets

    def __repr__(self) -> str:
        return f"{self.__class__.__name__}()"
