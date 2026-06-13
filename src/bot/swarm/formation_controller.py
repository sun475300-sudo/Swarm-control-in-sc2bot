"""
Formation controller for swarm behaviors.

Provides a deterministic 2D formation maintenance algorithm: given a list of
current unit positions, computes target positions that pull each unit towards
the swarm centroid while preserving relative spacing. Used as the default
controller behind every ``Behavior`` module in this package.
"""

from __future__ import annotations

import math
from typing import Iterable, List, Sequence, Tuple

Point = Tuple[float, float]


def _as_point(value) -> Point:
    """Coerce any 2-element iterable into a ``(float, float)`` tuple."""
    x, y = value
    return float(x), float(y)


class FormationController:
    """Maintain a 2D formation by pulling units toward the swarm centroid.

    The controller does not own any state about specific units; it operates on
    the position list it is handed each tick. ``cohesion`` is the fraction of
    the centroid offset to apply per tick (0.0 keeps units in place, 1.0
    collapses them to the centroid in a single step).
    """

    def __init__(self, cohesion: float = 0.25, min_spacing: float = 0.5) -> None:
        if not 0.0 <= cohesion <= 1.0:
            raise ValueError("cohesion must be in [0, 1]")
        if min_spacing < 0.0:
            raise ValueError("min_spacing must be >= 0")
        self.cohesion = float(cohesion)
        self.min_spacing = float(min_spacing)

    @staticmethod
    def centroid(positions: Sequence[Point]) -> Point:
        """Return the arithmetic mean of ``positions`` (or origin if empty)."""
        if not positions:
            return (0.0, 0.0)
        sx = sum(p[0] for p in positions)
        sy = sum(p[1] for p in positions)
        n = len(positions)
        return (sx / n, sy / n)

    def maintain_formation(self, positions: Iterable) -> List[Point]:
        """Return target positions one cohesion-step closer to the centroid.

        Units closer than ``min_spacing`` to a neighbour are nudged outward
        first to avoid stacking on top of each other.
        """
        pts: List[Point] = [_as_point(p) for p in positions]
        if not pts:
            return []

        cx, cy = self.centroid(pts)
        targets: List[Point] = []
        for x, y in pts:
            tx = x + (cx - x) * self.cohesion
            ty = y + (cy - y) * self.cohesion
            targets.append((tx, ty))

        if self.min_spacing > 0.0:
            targets = self._enforce_spacing(targets)
        return targets

    def _enforce_spacing(self, points: List[Point]) -> List[Point]:
        """Nudge points apart so no pair sits closer than ``min_spacing``."""
        adjusted = list(points)
        for i in range(len(adjusted)):
            for j in range(i + 1, len(adjusted)):
                ax, ay = adjusted[i]
                bx, by = adjusted[j]
                dx, dy = bx - ax, by - ay
                dist = math.hypot(dx, dy)
                if dist == 0.0:
                    # Degenerate: split along x by half-spacing.
                    half = self.min_spacing / 2.0
                    adjusted[i] = (ax - half, ay)
                    adjusted[j] = (bx + half, by)
                    continue
                if dist < self.min_spacing:
                    push = (self.min_spacing - dist) / 2.0
                    ux, uy = dx / dist, dy / dist
                    adjusted[i] = (ax - ux * push, ay - uy * push)
                    adjusted[j] = (bx + ux * push, by + uy * push)
        return adjusted

    def __repr__(self) -> str:
        return (
            f"FormationController(cohesion={self.cohesion}, "
            f"min_spacing={self.min_spacing})"
        )
