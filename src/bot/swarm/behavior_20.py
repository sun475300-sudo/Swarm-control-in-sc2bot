"""
Swarm Behavior Module #20 - AntiAirSpread.
Units spread wide (radius=10.0) to minimize AoE splash damage from air attacks.
"""

import math
from typing import List, Tuple
from .formation_controller import FormationController, Position

_AA_SPREAD = 10.0


class Behavior20:
    """AntiAirSpread: maximize spacing with large circular spread (radius=10.0)."""

    def __init__(self) -> None:
        self.controller = FormationController()
        self.name = "behavior_20"

    def tick(self, positions: List[Position]) -> List[Position]:
        """
        Distribute units on a large circle of radius 10.0 around the centroid
        to minimise splash-damage overlap from area attacks.

        Args:
            positions: Current (x, y) positions for each unit.

        Returns:
            Target positions on the wide anti-air spread circle.
        """
        return self.controller.spread_formation(positions, spread=_AA_SPREAD)

    def __repr__(self) -> str:
        return f"{self.__class__.__name__}()"
