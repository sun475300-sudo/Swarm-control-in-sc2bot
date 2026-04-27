"""
Swarm Behavior Module #28 - ZoneControl.
Units occupy a 6x6 grid of cells starting from the centroid, spreading out
to hold and dominate a rectangular territory.
"""

import math
from typing import List, Tuple
from .formation_controller import FormationController, Position

_GRID_CELL_SIZE = 2.0   # spacing between grid positions
_GRID_COLS = 6          # number of columns in the grid
_GRID_ROWS = 6          # number of rows in the grid


class Behavior28:
    """ZoneControl: units fill a 6x6 grid area starting from the centroid."""

    def __init__(self) -> None:
        self.controller = FormationController()
        self.name = "behavior_28"

    def tick(self, positions: List[Position]) -> List[Position]:
        """
        Assign each unit a unique cell in a 6x6 grid centred on the group
        centroid.  Units beyond the 36-cell grid wrap around to the start.

        Args:
            positions: Current (x, y) positions for each unit.

        Returns:
            Target positions on the zone-control grid.
        """
        if not positions:
            return []

        n = len(positions)
        cx = sum(p[0] for p in positions) / n
        cy = sum(p[1] for p in positions) / n

        total_cells = _GRID_COLS * _GRID_ROWS
        # Grid origin: top-left corner offset so the grid is centred on centroid
        origin_x = cx - (_GRID_COLS - 1) / 2.0 * _GRID_CELL_SIZE
        origin_y = cy - (_GRID_ROWS - 1) / 2.0 * _GRID_CELL_SIZE

        targets: List[Position] = []
        for i in range(n):
            cell = i % total_cells
            col = cell % _GRID_COLS
            row = cell // _GRID_COLS
            tx = origin_x + col * _GRID_CELL_SIZE
            ty = origin_y + row * _GRID_CELL_SIZE
            targets.append((tx, ty))

        return targets

    def __repr__(self) -> str:
        return f"{self.__class__.__name__}()"
