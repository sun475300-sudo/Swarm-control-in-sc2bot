"""Swarm Behavior #02 - Boids Flocking (Separation + Cohesion)."""

import math
from typing import List
from .formation_controller import FormationController, Position


class Behavior02:
    """
    Boids-inspired flocking: units naturally flock together
    while maintaining personal space.
    """

    SEPARATION_RADIUS = 2.5
    SEPARATION_WEIGHT = 1.5
    COHESION_WEIGHT = 0.8

    def __init__(self) -> None:
        self.controller = FormationController(formation_radius=2.5)
        self.name = "boids_flocking"

    def tick(self, positions: List[Position]) -> List[Position]:
        if not positions:
            return []
        if len(positions) == 1:
            return list(positions)

        cx = sum(p[0] for p in positions) / len(positions)
        cy = sum(p[1] for p in positions) / len(positions)

        targets: List[Position] = []
        for pos in positions:
            dx_coh = (cx - pos[0]) * self.COHESION_WEIGHT
            dy_coh = (cy - pos[1]) * self.COHESION_WEIGHT

            dx_sep = dy_sep = 0.0
            for other in positions:
                if other is pos:
                    continue
                dist = math.hypot(pos[0] - other[0], pos[1] - other[1])
                if 0 < dist < self.SEPARATION_RADIUS:
                    strength = (self.SEPARATION_RADIUS - dist) / self.SEPARATION_RADIUS
                    dx_sep += (pos[0] - other[0]) / dist * strength * self.SEPARATION_WEIGHT
                    dy_sep += (pos[1] - other[1]) / dist * strength * self.SEPARATION_WEIGHT

            targets.append((pos[0] + dx_coh + dx_sep, pos[1] + dy_coh + dy_sep))

        return targets

    def __repr__(self) -> str:
        return f"{self.__class__.__name__}()"
