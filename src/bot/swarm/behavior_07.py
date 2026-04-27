"""
Swarm Behavior Module #7 - Retreat.
All units converge on the centroid then shift west together.
"""

import math
from typing import List, Tuple
from .formation_controller import FormationController, Position

_RETREAT_OFFSET = 5.0   # units west of the centroid


class Behavior07:
    """Retreat: pull all units toward centroid then offset the whole group west."""

    def __init__(self) -> None:
        self.controller = FormationController()
        self.name = "behavior_07"

    def tick(self, positions: List[Position]) -> List[Position]:
        """
        Move units into a tight circular formation, then shift the entire
        formation westward (negative x direction) by a fixed offset.

        Args:
            positions: Current (x, y) positions for each unit.

        Returns:
            Target positions for the retreating formation.
        """
        if not positions:
            return []

        # First form a tight ring around centroid
        formation = self.controller.maintain_formation(positions)

        # Shift entire formation west
        targets: List[Position] = [
            (tx - _RETREAT_OFFSET, ty) for tx, ty in formation
        ]
        return targets

    def __repr__(self) -> str:
        return f"{self.__class__.__name__}()"
