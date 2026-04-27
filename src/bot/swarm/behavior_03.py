"""
Swarm Behavior Module #3 - WedgeAttack.
V-shape wedge formation pointing east for coordinated attack.
"""

import math
from typing import List, Tuple
from .formation_controller import FormationController, Position


class Behavior03:
    """WedgeAttack: V-shape wedge pointing east (direction=0.0)."""

    def __init__(self) -> None:
        self.controller = FormationController()
        self.name = "behavior_03"

    def tick(self, positions: List[Position]) -> List[Position]:
        """
        Arrange units in a V-shape wedge pointing east.

        Args:
            positions: Current (x, y) positions for each unit.

        Returns:
            Target positions forming a wedge pointing east.
        """
        return self.controller.wedge_formation(positions, direction=0.0)

    def __repr__(self) -> str:
        return f"{self.__class__.__name__}()"
