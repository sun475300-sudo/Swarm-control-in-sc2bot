"""
Swarm Behavior Module #24 - AttritionPress.
The group's effective centroid drifts +0.2 units east each tick; units maintain
a standard circular formation around this ever-advancing virtual centroid,
applying slow but relentless pressure forward.
"""

import math
from typing import List, Tuple
from .formation_controller import FormationController, Position

_DRIFT_RATE = 0.2    # eastward centroid drift per tick
_PRESS_RADIUS = 3.0  # formation radius around the drifting centroid


class Behavior24:
    """AttritionPress: circular formation around a centroid that drifts east over time."""

    def __init__(self) -> None:
        self.controller = FormationController()
        self.name = "behavior_24"
        self._drift_x: float = 0.0   # cumulative eastward drift applied

    def tick(self, positions: List[Position]) -> List[Position]:
        """
        Compute the actual centroid, apply the accumulated eastward drift to
        produce a virtual centroid, then place units in a circular formation
        around it.  Each tick advances the drift by _DRIFT_RATE.

        Args:
            positions: Current (x, y) positions for each unit.

        Returns:
            Target positions in the pressed circular formation.
        """
        if not positions:
            return []

        n = len(positions)
        cx = sum(p[0] for p in positions) / n
        cy = sum(p[1] for p in positions) / n

        # Advance drift
        self._drift_x += _DRIFT_RATE
        vcx = cx + self._drift_x
        vcy = cy

        targets: List[Position] = []
        for i in range(n):
            angle = (2 * math.pi * i) / n
            tx = vcx + _PRESS_RADIUS * math.cos(angle)
            ty = vcy + _PRESS_RADIUS * math.sin(angle)
            targets.append((tx, ty))

        return targets

    def __repr__(self) -> str:
        return f"{self.__class__.__name__}()"
