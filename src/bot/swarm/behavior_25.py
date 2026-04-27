"""
Swarm Behavior Module #25 - Breakthrough.
All units concentrate into a narrow 2-wide column with tight spacing (1.5 units),
punching through enemy lines in a compressed spearhead.
"""

import math
from typing import List, Tuple
from .formation_controller import FormationController, Position

_COLUMN_SPACING = 1.5   # tight spacing between units in the column
_COLUMN_WIDTH = 2       # number of units side-by-side per row


class Behavior25:
    """Breakthrough: tight 2-wide column with spacing=1.5 for penetration."""

    def __init__(self) -> None:
        self.controller = FormationController()
        self.name = "behavior_25"

    def tick(self, positions: List[Position]) -> List[Position]:
        """
        Arrange units into a compressed 2-column formation pointing east.
        Units are laid out in rows of 2 (left/right of the x-axis) with
        tight 1.5-unit spacing, centred on the group centroid.

        Args:
            positions: Current (x, y) positions for each unit.

        Returns:
            Target positions in the breakthrough column.
        """
        if not positions:
            return []

        n = len(positions)
        cx = sum(p[0] for p in positions) / n
        cy = sum(p[1] for p in positions) / n

        rows = math.ceil(n / _COLUMN_WIDTH)
        targets: List[Position] = []

        for i in range(n):
            row = i // _COLUMN_WIDTH
            col = i % _COLUMN_WIDTH
            # Centre rows around centroid along x (leading east)
            tx = cx + (row - (rows - 1) / 2.0) * _COLUMN_SPACING
            # Two columns: col 0 -> slightly north, col 1 -> slightly south
            ty = cy + (col - (_COLUMN_WIDTH - 1) / 2.0) * _COLUMN_SPACING
            targets.append((tx, ty))

        return targets

    def __repr__(self) -> str:
        return f"{self.__class__.__name__}()"
