"""
Swarm Behavior Module #23 - SkirmishHitRun.
Units oscillate in a semicircular arc on the east side of the centroid using
sin/cos, simulating a hit-and-run attack: they strike (+x) then withdraw (-x)
while sweeping north/south in a crescent.
"""

import math
from typing import List, Tuple
from .formation_controller import FormationController, Position

_ARC_RADIUS = 5.0     # radius of the semicircular sweep
_OSC_STEP = 0.15      # radians per tick for oscillation
_HALF_ARC = math.pi / 2.0  # semicircle half-angle


class Behavior23:
    """SkirmishHitRun: units sweep a semicircular arc east of centroid, oscillating."""

    def __init__(self) -> None:
        self.controller = FormationController()
        self.name = "behavior_23"
        self._angle: float = 0.0   # driving oscillation angle

    def tick(self, positions: List[Position]) -> List[Position]:
        """
        Place units on a semicircular arc east of the centroid.  The arc angle
        oscillates via sin so units strike forward then withdraw, creating a
        hit-and-run sweep pattern.

        Args:
            positions: Current (x, y) positions for each unit.

        Returns:
            Target positions on the oscillating eastern semicircle.
        """
        if not positions:
            return []

        n = len(positions)
        cx = sum(p[0] for p in positions) / n
        cy = sum(p[1] for p in positions) / n

        self._angle += _OSC_STEP
        # Oscillation factor: swings between 0 and 1 using sin
        osc = (math.sin(self._angle) + 1.0) / 2.0

        targets: List[Position] = []
        for i in range(n):
            # Spread units evenly across the semicircle (-pi/2 to +pi/2, east-facing)
            spread_angle = -_HALF_ARC + (math.pi * i / max(n - 1, 1)) if n > 1 else 0.0
            # Oscillate the effective radius from 0.5*R to R
            r = _ARC_RADIUS * (0.5 + 0.5 * osc)
            tx = cx + r * math.cos(spread_angle)
            ty = cy + r * math.sin(spread_angle)
            targets.append((tx, ty))

        return targets

    def __repr__(self) -> str:
        return f"{self.__class__.__name__}()"
