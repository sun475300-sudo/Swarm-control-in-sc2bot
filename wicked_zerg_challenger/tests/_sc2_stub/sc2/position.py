"""Stub Point2 / Point3."""

import math


class Point2(tuple):
    """Minimal Point2 substitute supporting basic geometry used by tests."""

    def __new__(cls, value=(0.0, 0.0)):
        try:
            x, y = value
        except (TypeError, ValueError):
            x, y = 0.0, 0.0
        return super().__new__(cls, (float(x), float(y)))

    @property
    def x(self) -> float:
        return self[0]

    @property
    def y(self) -> float:
        return self[1]

    def distance_to(self, other) -> float:
        ox = getattr(other, "x", None)
        oy = getattr(other, "y", None)
        if ox is None or oy is None:
            try:
                ox, oy = other
            except (TypeError, ValueError):
                return 0.0
        return math.hypot(self.x - ox, self.y - oy)

    def towards(self, other, distance: float) -> "Point2":
        ox = getattr(other, "x", None)
        oy = getattr(other, "y", None)
        if ox is None or oy is None:
            ox, oy = other
        dx, dy = ox - self.x, oy - self.y
        length = math.hypot(dx, dy) or 1.0
        return Point2(
            (self.x + dx / length * distance, self.y + dy / length * distance)
        )

    def offset(self, delta) -> "Point2":
        try:
            dx, dy = delta
        except (TypeError, ValueError):
            dx, dy = float(delta), float(delta)
        return Point2((self.x + dx, self.y + dy))


class Point3(Point2):
    def __new__(cls, value=(0.0, 0.0, 0.0)):
        try:
            x, y, z = value
        except (TypeError, ValueError):
            x, y, z = 0.0, 0.0, 0.0
        obj = super().__new__(cls, (float(x), float(y)))
        obj._z = float(z)
        return obj

    @property
    def z(self) -> float:
        return self._z
