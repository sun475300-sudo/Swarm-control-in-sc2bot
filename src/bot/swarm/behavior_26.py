"""
Swarm Behavior Module #26 - SpreadControl.
Units spread extremely wide (spread=12.0) to maximise zone coverage and
avoid AoE damage.  Uses the formation controller's spread_formation method.
"""

import math
from typing import List, Tuple
from .formation_controller import FormationController, Position

_SPREAD_RADIUS = 12.0


class Behavior26:
    """SpreadControl: maximum spacing (spread=12.0) to deny enemy AoE effectiveness."""

    def __init__(self) -> None:
        self.controller = FormationController()
        self.name = "behavior_26"

    def tick(self, positions: List[Position]) -> List[Position]:
        """
        Push every unit as far from the centroid as possible (radius 12.0)
        to deny area-of-effect weapons and control a wide zone.

        Args:
            positions: Current (x, y) positions for each unit.

        Returns:
            Target positions on the wide spread formation circle.
        """
        return self.controller.spread_formation(positions, spread=_SPREAD_RADIUS)

    def __repr__(self) -> str:
        return f"{self.__class__.__name__}()"
