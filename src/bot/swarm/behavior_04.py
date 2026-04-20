"""
Swarm Behavior Module #4 - LineAdvance.
Horizontal line formation perpendicular to the east direction.
"""

import math
from typing import List, Tuple
from .formation_controller import FormationController, Position


class Behavior04:
    """LineAdvance: horizontal line formation perpendicular to east direction."""

    def __init__(self) -> None:
        self.controller = FormationController()
        self.name = "behavior_04"

    def tick(self, positions: List[Position]) -> List[Position]:
        """
        Arrange units in a horizontal line perpendicular to east (direction=0.0).

        Args:
            positions: Current (x, y) positions for each unit.

        Returns:
            Target positions in a horizontal line.
        """
        return self.controller.line_formation(positions, direction=0.0)

    def __repr__(self) -> str:
        return f"{self.__class__.__name__}()"
