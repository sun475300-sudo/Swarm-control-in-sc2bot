# -*- coding: utf-8 -*-
"""
SC2 import-compat shim.

When the optional `sc2`/`burnysc2` package is not installed (CI lint, doc
generation, unit tests that don't need a live game), the bot still has to
*import* cleanly. Many modules historically declared their own minimal stub:

    try:
        from sc2.ids.unit_typeid import UnitTypeId
    except ImportError:
        class UnitTypeId:
            pass

That works for `isinstance`-style guards but breaks the moment a default
parameter or class-body constant references `UnitTypeId.OVERLORD` — the stub
class doesn't have that attribute, so import fails with an `AttributeError`.

This module provides:

* `_AnyAttr`  - a metaclass that returns a sentinel string for any
                undefined attribute. Both *class*-level access
                (`UnitTypeId.OVERLORD`) and *instance*-level access work.
* `UnitTypeId`, `AbilityId`, `UpgradeId`, `BuffId`, `EffectId` - empty
                classes built on `_AnyAttr` so any attribute lookup succeeds.
* `BotAI`, `Unit`, `Point2`, `Point3`, `Race` - minimal dataclasses with
                permissive attribute access for downstream type hints.

Modules should import these as a group:

    try:
        from sc2.ids.unit_typeid import UnitTypeId
        from sc2.ids.ability_id import AbilityId
    except ImportError:
        from utils.sc2_compat import UnitTypeId, AbilityId
"""

from __future__ import annotations


class _AnyAttr(type):
    """Metaclass that returns a sentinel for any unknown class attribute.

    Also supports subscript access (`Race["Zerg"]`) by routing it through
    the same sentinel lookup. This is critical for code paths like
    `Race[serialized_str]` that survive when sc2 is unavailable.
    """

    def __getattr__(cls, name: str):
        cache = cls.__dict__.get("_sentinel_cache_per_class")
        if cache is None:
            cache = {}
            type.__setattr__(cls, "_sentinel_cache_per_class", cache)
        if name not in cache:
            cache[name] = f"<{cls.__name__}.{name}>"
        return cache[name]

    def __getitem__(cls, key):
        # Route Race["Zerg"] / Difficulty["Easy"] through attribute lookup
        return cls.__getattr__(str(key))


class _StubBase(metaclass=_AnyAttr):
    def __getattr__(self, name: str):  # instance-level fallback
        return f"<{type(self).__name__}.{name}>"

    def __eq__(self, other):
        return isinstance(other, type(self)) and repr(self) == repr(other)

    def __hash__(self):
        return hash(repr(self))


class UnitTypeId(_StubBase):
    """Stub for sc2.ids.unit_typeid.UnitTypeId."""


class AbilityId(_StubBase):
    """Stub for sc2.ids.ability_id.AbilityId."""


class UpgradeId(_StubBase):
    """Stub for sc2.ids.upgrade_id.UpgradeId."""


class BuffId(_StubBase):
    """Stub for sc2.ids.buff_id.BuffId."""


class EffectId(_StubBase):
    """Stub for sc2.ids.effect_id.EffectId."""


class Race(_StubBase):
    """Stub for sc2.data.Race."""


class Point2:
    """Minimal Point2 stub supporting basic arithmetic and distance."""

    __slots__ = ("x", "y")

    def __init__(self, xy=(0.0, 0.0)):
        try:
            self.x, self.y = float(xy[0]), float(xy[1])
        except (TypeError, IndexError):
            self.x = self.y = 0.0

    def distance_to(self, other) -> float:
        try:
            return ((self.x - other.x) ** 2 + (self.y - other.y) ** 2) ** 0.5
        except AttributeError:
            return 0.0

    def __iter__(self):
        yield self.x
        yield self.y

    def __repr__(self):
        return f"Point2(({self.x}, {self.y}))"


class Point3(Point2):
    __slots__ = ("z",)

    def __init__(self, xyz=(0.0, 0.0, 0.0)):
        super().__init__((xyz[0], xyz[1]))
        try:
            self.z = float(xyz[2])
        except (TypeError, IndexError):
            self.z = 0.0


class _UnitStub:
    """Permissive Unit stub - any attribute access returns None."""

    def __getattr__(self, name: str):
        return None


class Unit(_UnitStub):
    pass


class BotAI:
    """Minimal BotAI stub used purely for typing fallback."""

    pass


__all__ = [
    "AbilityId",
    "BotAI",
    "BuffId",
    "EffectId",
    "Point2",
    "Point3",
    "Race",
    "Unit",
    "UnitTypeId",
    "UpgradeId",
]
