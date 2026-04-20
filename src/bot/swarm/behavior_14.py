"""
Swarm Behavior Module #14 - FlankLeft.
All units offset 90 degrees counterclockwise from the centroid, shifting
the entire formation to the left (north when facing east).
"""

import math
from typing import List, Tuple
from .formation_controller import FormationController, Position

_FLANK_DISTANCE = 4.0   # lateral offset distance


class Behavior14:
    """FlankLeft: rotate entire formation 90 degrees CCW (offset north) from centroid."""

    def __init__(self) -> None:
        self.controller = FormationController()
        self.name = "behavior_14"

    def tick(self, positions: List[Position]) -> List[Position]:
        """
        Maintain a line formation then shift the whole group northward (left flank)
        by _FLANK_DISTANCE units.

        Args:
            positions: Current (x, y) positions for each unit.

        Returns:
            Target positions of the left-flanking line.
        """
        if not positions:
            return []

        # Line formation then shift +y (north = left when facing east)
        formation = self.controller.line_formation(positions, direction=0.0)
        targets: List[Position] = [
            (tx, ty + _FLANK_DISTANCE) for tx, ty in formation
        ]
        return targets

    def __repr__(self) -> str:
        return f"{self.__class__.__name__}()"
