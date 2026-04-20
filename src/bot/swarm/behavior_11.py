"""
Swarm Behavior Module #11 - StutterStep.
Units alternate between stepping forward (+x) and stepping back (-x)
each tick, creating a pulsing advance-and-retreat micro pattern.
"""

import math
from typing import List, Tuple
from .formation_controller import FormationController, Position

_STEP_DISTANCE = 1.0


class Behavior11:
    """StutterStep: units move forward 1 unit then back 1 unit alternately each tick."""

    def __init__(self) -> None:
        self.controller = FormationController()
        self.name = "behavior_11"
        self._forward: bool = True

    def tick(self, positions: List[Position]) -> List[Position]:
        """
        On forward ticks shift units east by _STEP_DISTANCE; on backward ticks
        shift them west by the same amount.  Toggles each call.

        Args:
            positions: Current (x, y) positions for each unit.

        Returns:
            Target positions stepped forward or backward.
        """
        if not positions:
            return []

        offset_x = _STEP_DISTANCE if self._forward else -_STEP_DISTANCE
        self._forward = not self._forward

        targets: List[Position] = [
            (px + offset_x, py) for px, py in positions
        ]
        return targets

    def __repr__(self) -> str:
        return f"{self.__class__.__name__}()"
