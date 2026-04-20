"""
Swarm Behavior Module #29 - HarassmentSwarm.
Even-indexed units advance northeast (+x, +y); odd-indexed units advance
southeast (+x, -y), creating a split harassment that threatens two angles.
"""

import math
from typing import List, Tuple
from .formation_controller import FormationController, Position

_HARASS_OFFSET = 4.0   # distance each group advances from centroid


class Behavior29:
    """HarassmentSwarm: even units go NE, odd units go SE from centroid."""

    def __init__(self) -> None:
        self.controller = FormationController()
        self.name = "behavior_29"

    def tick(self, positions: List[Position]) -> List[Position]:
        """
        Split units by index parity: even-indexed units target a northeast
        position (centroid + offset in +x, +y), odd-indexed units target a
        southeast position (centroid + offset in +x, -y).

        Args:
            positions: Current (x, y) positions for each unit.

        Returns:
            Target positions for the split northeast/southeast harassment.
        """
        if not positions:
            return []

        n = len(positions)
        cx = sum(p[0] for p in positions) / n
        cy = sum(p[1] for p in positions) / n

        # Diagonal unit vector at 45 degrees (NE) and -45 degrees (SE)
        diagonal = _HARASS_OFFSET / math.sqrt(2.0)

        # Count even/odd for sub-group slot spacing
        even_count = sum(1 for i in range(n) if i % 2 == 0)
        odd_count = n - even_count

        even_slot = 0
        odd_slot = 0

        targets: List[Position] = []
        for i in range(n):
            if i % 2 == 0:
                # NE group: spread slightly in y around northeast position
                slot_offset = (even_slot - (even_count - 1) / 2.0) * 1.5
                tx = cx + diagonal
                ty = cy + diagonal + slot_offset
                even_slot += 1
            else:
                # SE group: spread slightly in y around southeast position
                slot_offset = (odd_slot - (odd_count - 1) / 2.0) * 1.5
                tx = cx + diagonal
                ty = cy - diagonal + slot_offset
                odd_slot += 1
            targets.append((tx, ty))

        return targets

    def __repr__(self) -> str:
        return f"{self.__class__.__name__}()"
