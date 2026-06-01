"""Stub for sc2.position.Point2 — minimal 2D-point implementation."""
from __future__ import annotations

import math
from typing import Tuple, Union


class Point2(tuple):
    """Lightweight stand-in for sc2.position.Point2."""

    __slots__ = ()

    def __new__(cls, *args) -> "Point2":
        if len(args) == 1:
            xy = args[0]
            x, y = xy[0], xy[1]
        elif len(args) == 2:
            x, y = args
        else:
            raise TypeError("Point2 expects (x, y) or (xy,)")
        return tuple.__new__(cls, (float(x), float(y)))

    @property
    def x(self) -> float:
        return self[0]

    @property
    def y(self) -> float:
        return self[1]

    @property
    def position(self) -> "Point2":
        return self

    def distance_to(self, other: Union["Point2", Tuple[float, float], object]) -> float:
        ox, oy = _xy(other)
        return math.hypot(self[0] - ox, self[1] - oy)

    def distance_to_point2(self, other) -> float:
        return self.distance_to(other)

    def towards(
        self,
        other: Union["Point2", Tuple[float, float], object],
        distance: float,
    ) -> "Point2":
        ox, oy = _xy(other)
        dx, dy = ox - self[0], oy - self[1]
        d = math.hypot(dx, dy)
        if d == 0:
            return Point2(self[0], self[1])
        return Point2(self[0] + dx / d * distance, self[1] + dy / d * distance)

    def __add__(self, other):
        ox, oy = _xy(other)
        return Point2(self[0] + ox, self[1] + oy)

    def __sub__(self, other):
        ox, oy = _xy(other)
        return Point2(self[0] - ox, self[1] - oy)

    def __mul__(self, scalar):
        return Point2(self[0] * scalar, self[1] * scalar)

    def __repr__(self) -> str:
        return f"Point2({self[0]}, {self[1]})"


def _xy(other) -> Tuple[float, float]:
    if isinstance(other, Point2):
        return other[0], other[1]
    pos = getattr(other, "position", None)
    if pos is not None and pos is not other:
        return _xy(pos)
    if isinstance(other, tuple) and len(other) >= 2:
        return float(other[0]), float(other[1])
    return float(other.x), float(other.y)
