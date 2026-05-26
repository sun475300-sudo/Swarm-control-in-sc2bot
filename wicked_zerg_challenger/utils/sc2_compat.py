# -*- coding: utf-8 -*-
"""Compatibility shims for tooling environments without ``sc2`` installed.

The Wicked Zerg modules each declare local stub classes for ``UnitTypeId``,
``AbilityId`` and ``UpgradeId`` so unit tests can run on machines that don't
have the burnysc2 library available. Those stubs drifted over time - some are
empty, some are missing recent identifiers, leading to false-negative test
failures (``AttributeError: type object 'UnitTypeId' has no attribute 'MARINE'``).

This module centralises a "best effort" stub that supports any attribute
access, returning a stable string token so equality comparisons keep
working. Modules can opt in with::

    try:
        from sc2.ids.unit_typeid import UnitTypeId
    except ImportError:
        from utils.sc2_compat import UnitTypeId
"""

from __future__ import annotations


class _IdToken(str):
    """String-backed enum stand-in.

    Behaves like a string for legacy code paths that compare to bare names,
    but also exposes an enum-style ``.name`` and ``.value`` so callers that
    used the real burnysc2 enums keep working.
    """

    __slots__ = ()

    @property
    def name(self):  # type: ignore[override]
        return str.__str__(self).rsplit(".", 1)[-1]

    @property
    def value(self):
        return self.name

    def __repr__(self):
        return str.__str__(self)


class _IdMeta(type):
    """Metaclass that turns any attribute access into a stable ``_IdToken``.

    The returned value is cached on the class so identity holds across
    repeated lookups (``UnitTypeId.MARINE is UnitTypeId.MARINE``).
    """

    def __getattr__(cls, name):  # noqa: D401 - dunder doc not required
        if name.startswith("_"):
            raise AttributeError(name)
        token = _IdToken(f"{cls.__name__}.{name}")
        setattr(cls, name, token)
        return token


class UnitTypeId(metaclass=_IdMeta):
    """Stub UnitTypeId. Attribute access returns an ``_IdToken``."""


class AbilityId(metaclass=_IdMeta):
    """Stub AbilityId."""


class UpgradeId(metaclass=_IdMeta):
    """Stub UpgradeId."""


class BuffId(metaclass=_IdMeta):
    """Stub BuffId."""


class Point2:
    """Minimal Point2 stand-in with the geometry helpers we rely on."""

    __slots__ = ("x", "y")

    def __init__(self, position=(0.0, 0.0)):
        if isinstance(position, Point2):
            self.x, self.y = position.x, position.y
        else:
            x, y = position
            self.x = float(x)
            self.y = float(y)

    def __iter__(self):
        yield self.x
        yield self.y

    def __getitem__(self, idx):
        return (self.x, self.y)[idx]

    def __eq__(self, other):
        try:
            return abs(self.x - other.x) < 1e-9 and abs(self.y - other.y) < 1e-9
        except AttributeError:
            return False

    def __hash__(self):
        return hash((round(self.x, 6), round(self.y, 6)))

    def __repr__(self):
        return f"Point2(({self.x}, {self.y}))"

    def distance_to(self, other) -> float:
        ox = getattr(other, "x", None)
        oy = getattr(other, "y", None)
        if ox is None or oy is None:
            ox, oy = other[0], other[1]
        return ((self.x - ox) ** 2 + (self.y - oy) ** 2) ** 0.5

    def towards(self, other, distance: float) -> "Point2":
        ox = getattr(other, "x", None)
        oy = getattr(other, "y", None)
        if ox is None or oy is None:
            ox, oy = other[0], other[1]
        total = ((ox - self.x) ** 2 + (oy - self.y) ** 2) ** 0.5 or 1.0
        return Point2(
            (
                self.x + (ox - self.x) / total * distance,
                self.y + (oy - self.y) / total * distance,
            )
        )

    def offset(self, delta) -> "Point2":
        return Point2((self.x + delta[0], self.y + delta[1]))


class BotAI:
    """Minimal BotAI base used when ``sc2`` is unavailable."""


class Unit:  # pragma: no cover - structural shim
    pass


class Units(list):
    """Best-effort ``Units`` shim that keeps the chainable API alive."""

    def __init__(self, items=None, _bot=None):
        super().__init__(items or [])

    def closer_than(self, distance, target):
        result = []
        for item in self:
            try:
                if item.distance_to(target) < distance:
                    result.append(item)
            except Exception:
                continue
        return Units(result)

    def filter(self, predicate):
        return Units([item for item in self if predicate(item)])

    @property
    def exists(self) -> bool:
        return bool(self)

    @property
    def amount(self) -> int:
        return len(self)


__all__ = [
    "AbilityId",
    "BotAI",
    "BuffId",
    "Point2",
    "Unit",
    "Units",
    "UnitTypeId",
    "UpgradeId",
]
