"""
Swarm Behavior Module #6 - Scatter.
Units flee away from the centroid along their individual outward direction.
"""

import math
from typing import List, Tuple
from .formation_controller import FormationController, Position

_SCATTER_DISTANCE = 6.0


class Behavior06:
    """Scatter: units move away from centroid in their individual direction (anti-cohesion)."""

    def __init__(self) -> None:
        self.controller = FormationController()
        self.name = "behavior_06"

    def tick(self, positions: List[Position]) -> List[Position]:
        """
        Push each unit directly away from the group centroid by a fixed distance.

        Units that are already at the centroid are assigned evenly-spaced angles
        so they still scatter rather than stacking.

        Args:
            positions: Current (x, y) positions for each unit.

        Returns:
            Target positions displaced away from the centroid.
        """
        if not positions:
            return []

        n = len(positions)
        cx = sum(p[0] for p in positions) / n
        cy = sum(p[1] for p in positions) / n

        targets: List[Position] = []
        for i, (px, py) in enumerate(positions):
            dx = px - cx
            dy = py - cy
            dist = math.hypot(dx, dy)
            if dist < 1e-6:
                # Unit is at centroid; assign a default evenly-spaced outward angle
                angle = (2 * math.pi * i) / n
                dx = math.cos(angle)
                dy = math.sin(angle)
            else:
                dx /= dist
                dy /= dist
            targets.append((px + _SCATTER_DISTANCE * dx, py + _SCATTER_DISTANCE * dy))

        return targets

    def __repr__(self) -> str:
        return f"{self.__class__.__name__}()"
