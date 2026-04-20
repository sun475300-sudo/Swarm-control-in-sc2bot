"""
Swarm Behavior Module #13 - FunnelFormation.
Units are sorted by their current y position and stacked into a single-file
vertical column centered on the centroid, funneling into a narrow corridor.
"""

import math
from typing import List, Tuple
from .formation_controller import FormationController, Position

_COLUMN_SPACING = 1.5   # vertical gap between stacked units


class Behavior13:
    """FunnelFormation: compress units into a single-file vertical column sorted by y."""

    def __init__(self) -> None:
        self.controller = FormationController()
        self.name = "behavior_13"

    def tick(self, positions: List[Position]) -> List[Position]:
        """
        Sort units by their y coordinate and place them in a tight vertical
        column at the centroid's x position, creating a funnelled single-file.

        Args:
            positions: Current (x, y) positions for each unit.

        Returns:
            Target positions in a single-file vertical column.
        """
        if not positions:
            return []

        n = len(positions)
        cx = sum(p[0] for p in positions) / n
        cy = sum(p[1] for p in positions) / n

        # Sort indices by current y position to preserve relative order
        sorted_indices = sorted(range(n), key=lambda i: positions[i][1])

        # Build column: each slot is _COLUMN_SPACING apart vertically, centred
        targets_by_slot: List[Position] = []
        for slot in range(n):
            ty = cy + (slot - (n - 1) / 2.0) * _COLUMN_SPACING
            targets_by_slot.append((cx, ty))

        # Map back to original unit order
        targets: List[Position] = [None] * n  # type: ignore[list-item]
        for slot, original_idx in enumerate(sorted_indices):
            targets[original_idx] = targets_by_slot[slot]

        return targets

    def __repr__(self) -> str:
        return f"{self.__class__.__name__}()"
