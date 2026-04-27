"""
Swarm Behavior Module #15 - FlankRight.
All units offset 90 degrees clockwise from the centroid, shifting
the entire formation to the right (south when facing east).
"""

import math
from typing import List, Tuple
from .formation_controller import FormationController, Position

_FLANK_DISTANCE = 4.0   # lateral offset distance


class Behavior15:
    """FlankRight: rotate entire formation 90 degrees CW (offset south) from centroid."""

    def __init__(self) -> None:
        self.controller = FormationController()
        self.name = "behavior_15"

    def tick(self, positions: List[Position]) -> List[Position]:
        """
        Maintain a line formation then shift the whole group southward (right flank)
        by _FLANK_DISTANCE units.

        Args:
            positions: Current (x, y) positions for each unit.

        Returns:
            Target positions of the right-flanking line.
        """
        if not positions:
            return []

        # Line formation then shift -y (south = right when facing east)
        formation = self.controller.line_formation(positions, direction=0.0)
        targets: List[Position] = [
            (tx, ty - _FLANK_DISTANCE) for tx, ty in formation
        ]
        return targets

    def __repr__(self) -> str:
        return f"{self.__class__.__name__}()"
