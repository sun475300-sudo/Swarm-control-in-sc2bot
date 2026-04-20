"""
Swarm Behavior Module #30 - AdaptiveBehavior.
Switches formation strategy based on the number of units present:
  - 1-3 units  : tight circle (radius=2.0) - conserve and protect
  - 4-8 units  : wedge formation (direction=0.0) - balanced attack
  - 9+ units   : wide spread (radius=12.0) - area denial and AoE avoidance
"""

import math
from typing import List, Tuple
from .formation_controller import FormationController, Position

_SMALL_RADIUS = 2.0
_LARGE_SPREAD = 12.0
_WEDGE_DIRECTION = 0.0   # east


class Behavior30:
    """AdaptiveBehavior: tight circle (<=3), wedge (4-8), or spread (>8) by unit count."""

    def __init__(self) -> None:
        self.controller = FormationController()
        self.name = "behavior_30"

    def tick(self, positions: List[Position]) -> List[Position]:
        """
        Dynamically choose the formation based on current unit count.
        Small groups cluster tightly, medium groups use a wedge, large
        groups spread wide to cover ground and avoid splash damage.

        Args:
            positions: Current (x, y) positions for each unit.

        Returns:
            Target positions for the selected adaptive formation.
        """
        if not positions:
            return []

        n = len(positions)

        if n <= 3:
            # Tight protective circle
            cx = sum(p[0] for p in positions) / n
            cy = sum(p[1] for p in positions) / n
            if n == 1:
                return [(cx, cy)]
            targets: List[Position] = []
            for i in range(n):
                angle = (2 * math.pi * i) / n
                tx = cx + _SMALL_RADIUS * math.cos(angle)
                ty = cy + _SMALL_RADIUS * math.sin(angle)
                targets.append((tx, ty))
            return targets

        elif n <= 8:
            # Wedge attack formation pointing east
            return self.controller.wedge_formation(positions, direction=_WEDGE_DIRECTION)

        else:
            # Wide spread to deny AoE and control territory
            return self.controller.spread_formation(positions, spread=_LARGE_SPREAD)

    def __repr__(self) -> str:
        return f"{self.__class__.__name__}()"
