"""Stub for sc2.units.Units."""
from __future__ import annotations


class Units(list):
    """List-like container matching the surface used in tests."""

    def __init__(self, iterable=(), *args, **kwargs):
        super().__init__(iterable)

    @property
    def amount(self) -> int:
        return len(self)

    @property
    def exists(self) -> bool:
        return bool(self)

    @property
    def ready(self) -> "Units":
        return Units(u for u in self if getattr(u, "is_ready", True))

    @property
    def not_ready(self) -> "Units":
        return Units(u for u in self if not getattr(u, "is_ready", True))

    @property
    def idle(self) -> "Units":
        return Units(u for u in self if getattr(u, "is_idle", False))

    def of_type(self, type_id):
        types = type_id if isinstance(type_id, (set, list, tuple)) else {type_id}
        return Units(u for u in self if getattr(u, "type_id", None) in types)

    def filter(self, predicate):
        return Units(u for u in self if predicate(u))

    def closer_than(self, distance, target):
        return Units(u for u in self if _dist(u, target) < distance)

    def farther_than(self, distance, target):
        return Units(u for u in self if _dist(u, target) > distance)

    def closest_to(self, target):
        if not self:
            return None
        return min(self, key=lambda u: _dist(u, target))


def _dist(unit, target) -> float:
    pos_a = getattr(unit, "position", unit)
    pos_b = getattr(target, "position", target)
    ax, ay = pos_a[0], pos_a[1]
    bx, by = pos_b[0], pos_b[1]
    return ((ax - bx) ** 2 + (ay - by) ** 2) ** 0.5
