"""Math helpers used by formation, pathing, and analytics code."""

from __future__ import annotations

import math
from typing import Iterable, Sequence, Tuple

Point = Tuple[float, float]


def clamp(value: float, low: float, high: float) -> float:
    """Return ``value`` constrained to ``[low, high]``."""
    if low > high:
        raise ValueError("low must not exceed high")
    if value < low:
        return low
    if value > high:
        return high
    return value


def lerp(a: float, b: float, t: float) -> float:
    """Linear interpolate from ``a`` to ``b`` by parameter ``t``."""
    return a + (b - a) * t


def distance(p: Point, q: Point) -> float:
    """Euclidean distance between two 2D points."""
    return math.hypot(q[0] - p[0], q[1] - p[1])


def manhattan(p: Point, q: Point) -> float:
    """Manhattan (L1) distance between two 2D points."""
    return abs(q[0] - p[0]) + abs(q[1] - p[1])


def normalize(vec: Point) -> Point:
    """Return the unit vector of ``vec``; ``(0, 0)`` for the zero vector."""
    length = math.hypot(*vec)
    if length == 0.0:
        return (0.0, 0.0)
    return (vec[0] / length, vec[1] / length)


def angle_between(p: Point, q: Point) -> float:
    """Angle (radians) of the vector from ``p`` to ``q``, in ``[-pi, pi]``."""
    return math.atan2(q[1] - p[1], q[0] - p[0])


def sign(value: float) -> int:
    """Return -1, 0, or 1 matching the sign of ``value``."""
    if value > 0:
        return 1
    if value < 0:
        return -1
    return 0


def mean(values: Iterable[float]) -> float:
    """Arithmetic mean of ``values`` (raises on an empty iterable)."""
    items = list(values)
    if not items:
        raise ValueError("cannot take mean of empty sequence")
    return sum(items) / len(items)


def variance(values: Sequence[float]) -> float:
    """Population variance of ``values`` (returns 0.0 for length <= 1)."""
    if len(values) <= 1:
        return 0.0
    avg = sum(values) / len(values)
    return sum((v - avg) ** 2 for v in values) / len(values)


def stddev(values: Sequence[float]) -> float:
    """Population standard deviation of ``values``."""
    return math.sqrt(variance(values))
