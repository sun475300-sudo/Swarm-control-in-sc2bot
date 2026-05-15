"""Minimal Point2/Point3 stubs for sc2-free testing."""

import math


class Point2(tuple):
    """Point2 stub that behaves like a 2-tuple with sc2-like API."""

    def __new__(cls, coords):
        try:
            x, y = coords
        except (TypeError, ValueError):
            x = y = float(coords)
        return tuple.__new__(cls, (float(x), float(y)))

    @property
    def x(self):
        return self[0]

    @property
    def y(self):
        return self[1]

    def distance_to(self, other):
        ox = getattr(other, "x", None)
        oy = getattr(other, "y", None)
        if ox is None or oy is None:
            try:
                ox, oy = other[0], other[1]
            except Exception:
                return 0.0
        return math.hypot(self.x - ox, self.y - oy)

    distance_to_point2 = distance_to

    def towards(self, other, distance):
        ox = getattr(other, "x", None)
        oy = getattr(other, "y", None)
        if ox is None or oy is None:
            ox, oy = other[0], other[1]
        dx = ox - self.x
        dy = oy - self.y
        length = math.hypot(dx, dy) or 1.0
        return Point2(
            (self.x + dx / length * distance, self.y + dy / length * distance)
        )

    def offset(self, delta):
        try:
            dx, dy = delta
        except Exception:
            dx = dy = float(delta)
        return Point2((self.x + dx, self.y + dy))

    def __add__(self, other):
        ox = getattr(other, "x", None)
        oy = getattr(other, "y", None)
        if ox is None or oy is None:
            ox, oy = other[0], other[1]
        return Point2((self.x + ox, self.y + oy))

    def __sub__(self, other):
        ox = getattr(other, "x", None)
        oy = getattr(other, "y", None)
        if ox is None or oy is None:
            ox, oy = other[0], other[1]
        return Point2((self.x - ox, self.y - oy))


class Point3(tuple):
    """Point3 stub."""

    def __new__(cls, coords):
        x, y, z = coords
        return tuple.__new__(cls, (float(x), float(y), float(z)))

    @property
    def x(self):
        return self[0]

    @property
    def y(self):
        return self[1]

    @property
    def z(self):
        return self[2]

    def distance_to(self, other):
        ox = getattr(other, "x", 0.0)
        oy = getattr(other, "y", 0.0)
        oz = getattr(other, "z", 0.0)
        return math.sqrt((self.x - ox) ** 2 + (self.y - oy) ** 2 + (self.z - oz) ** 2)
