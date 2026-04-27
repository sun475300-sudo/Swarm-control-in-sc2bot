"""
Swarm Behavior Module #27 - CohesionRally.
Aggressively pulls all units toward the group centroid with a strong weight
(3x cohesion), snapping scattered units back into a tight cluster quickly.
"""

import math
from typing import List, Tuple
from .formation_controller import FormationController, Position

_COHESION_WEIGHT = 3.0   # multiplier on pull toward centroid
_BASE_RADIUS = 1.0       # final tight cluster radius


class Behavior27:
    """CohesionRally: strong cohesion pull (weight=3.0) collapsing units to centroid."""

    def __init__(self) -> None:
        self.controller = FormationController()
        self.name = "behavior_27"

    def tick(self, positions: List[Position]) -> List[Position]:
        """
        For each unit, compute the vector from its current position toward the
        centroid and move it _COHESION_WEIGHT times that vector, then place it
        on a tiny ring around the centroid to avoid stacking.

        Args:
            positions: Current (x, y) positions for each unit.

        Returns:
            Target positions strongly pulled toward the centroid.
        """
        if not positions:
            return []

        n = len(positions)
        cx = sum(p[0] for p in positions) / n
        cy = sum(p[1] for p in positions) / n

        targets: List[Position] = []
        for i, (px, py) in enumerate(positions):
            dx = cx - px
            dy = cy - py
            dist = math.hypot(dx, dy)

            if dist < 1e-6:
                # Already at centroid: place on tight ring
                angle = (2 * math.pi * i) / n
                tx = cx + _BASE_RADIUS * math.cos(angle)
                ty = cy + _BASE_RADIUS * math.sin(angle)
            else:
                # Pull strongly toward centroid; clamp so we don't overshoot
                pull = min(dist, dist * _COHESION_WEIGHT)
                nx = dx / dist
                ny = dy / dist
                tx = px + pull * nx
                ty = py + pull * ny

            targets.append((tx, ty))

        return targets

    def __repr__(self) -> str:
        return f"{self.__class__.__name__}()"
