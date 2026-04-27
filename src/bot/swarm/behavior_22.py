"""
Swarm Behavior Module #22 - BaitAndRetreat.
Units cycle through a 6-phase attack/retreat pattern:
  phases 0-2: advance eastward by 2 units each tick
  phases 3-5: retreat westward by 6 units total over 3 ticks
Repeats indefinitely.
"""

import math
from typing import List, Tuple
from .formation_controller import FormationController, Position

_ADVANCE_STEP = 2.0   # units east per advance tick
_RETREAT_STEP = 2.0   # units west per retreat tick (3 ticks = 6 units total)


class Behavior22:
    """BaitAndRetreat: 3 ticks forward then 3 ticks backward cycle."""

    def __init__(self) -> None:
        self.controller = FormationController()
        self.name = "behavior_22"
        self._phase: int = 0   # 0..5, phases 0-2 = advance, 3-5 = retreat

    def tick(self, positions: List[Position]) -> List[Position]:
        """
        Advance the whole formation east for phases 0-2, then retreat west
        for phases 3-5.  The phase counter increments each tick and wraps.

        Args:
            positions: Current (x, y) positions for each unit.

        Returns:
            Target positions shifted according to the current phase.
        """
        if not positions:
            return []

        if self._phase < 3:
            offset_x = _ADVANCE_STEP
        else:
            offset_x = -_RETREAT_STEP

        self._phase = (self._phase + 1) % 6

        targets: List[Position] = [
            (px + offset_x, py) for px, py in positions
        ]
        return targets

    def __repr__(self) -> str:
        return f"{self.__class__.__name__}()"
