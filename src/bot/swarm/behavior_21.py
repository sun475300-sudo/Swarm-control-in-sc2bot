"""
Swarm Behavior Module #21 - GroundScreen.
Front row (first half of units) forms a line formation ahead of the centroid,
rear row (second half) forms a second line behind - creating a screening layer.
"""

import math
from typing import List, Tuple
from .formation_controller import FormationController, Position

_ROW_OFFSET = 3.0    # distance between front and rear rows
_LINE_SPACING = 2.0  # spacing between units within each row


class Behavior21:
    """GroundScreen: front half in a forward line, rear half in a rearward line."""

    def __init__(self) -> None:
        self.controller = FormationController()
        self.name = "behavior_21"

    def tick(self, positions: List[Position]) -> List[Position]:
        """
        Split units into two horizontal lines: the first half forms the front
        screen ahead of the centroid (+x), the second half forms the rear
        support line behind the centroid (-x).

        Args:
            positions: Current (x, y) positions for each unit.

        Returns:
            Target positions for the two-row ground screen.
        """
        if not positions:
            return []

        n = len(positions)
        cx = sum(p[0] for p in positions) / n
        cy = sum(p[1] for p in positions) / n

        mid = (n + 1) // 2
        front_count = mid
        rear_count = n - mid

        targets: List[Position] = []

        # Front row: first half, line ahead (+x offset from centroid)
        for i in range(front_count):
            slot = i - (front_count - 1) / 2.0
            tx = cx + _ROW_OFFSET
            ty = cy + slot * _LINE_SPACING
            targets.append((tx, ty))

        # Rear row: second half, line behind (-x offset from centroid)
        for i in range(rear_count):
            slot = i - (rear_count - 1) / 2.0
            tx = cx - _ROW_OFFSET
            ty = cy + slot * _LINE_SPACING
            targets.append((tx, ty))

        return targets

    def __repr__(self) -> str:
        return f"{self.__class__.__name__}()"
