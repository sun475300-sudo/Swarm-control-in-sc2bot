# -*- coding: utf-8 -*-
"""Shared sc2 (burnysc2) test stub.

Installed into ``sys.modules`` by test ``conftest.py`` files so unit tests
can run without burnysc2 present. Tests that need real SC2 semantics should
guard their imports and skip themselves when the real module is unavailable.
"""
from __future__ import annotations

import sys
import types
from enum import Enum
from typing import Any


def install_sc2_stub() -> bool:
    """Install an ``sc2`` stub in ``sys.modules`` if the real package is absent.

    Returns True when a stub was installed, False if the real module was
    importable and left intact.
    """
    try:
        import sc2  # type: ignore  # noqa: F401
        return False
    except ImportError:
        pass

    class _IdMember:
        """Enum-like ID member with ``name`` / ``value`` attributes."""

        __slots__ = ("name", "value")

        def __init__(self, name: str, value: int = 0):
            self.name = name
            self.value = value

        def __repr__(self) -> str:
            return f"<{type(self).__name__}.{self.name}>"

        def __str__(self) -> str:
            return self.name

        def __eq__(self, other: Any) -> bool:
            if isinstance(other, _IdMember):
                return self.name == other.name and type(self) is type(other)
            if isinstance(other, str):
                return self.name == other
            return NotImplemented

        def __ne__(self, other: Any) -> bool:
            result = self.__eq__(other)
            if result is NotImplemented:
                return result
            return not result

        def __hash__(self) -> int:
            return hash((type(self).__name__, self.name))

    class _DynamicIdMeta(type):
        def __getattr__(cls, name: str):
            if name.startswith("_"):
                raise AttributeError(name)
            cache = cls.__dict__.get("_member_cache")
            if cache is None:
                cache = {}
                type.__setattr__(cls, "_member_cache", cache)
            if name not in cache:
                cache[name] = _IdMember(name, value=len(cache) + 1)
            return cache[name]

    class UnitTypeId(metaclass=_DynamicIdMeta):
        pass

    class AbilityId(metaclass=_DynamicIdMeta):
        pass

    class UpgradeId(metaclass=_DynamicIdMeta):
        pass

    class BuffId(metaclass=_DynamicIdMeta):
        pass

    class EffectId(metaclass=_DynamicIdMeta):
        pass

    def _distance(a, b) -> float:
        ax = a[0] if isinstance(a, (tuple, list)) else a.x
        ay = a[1] if isinstance(a, (tuple, list)) else a.y
        bx = b[0] if isinstance(b, (tuple, list)) else b.x
        by = b[1] if isinstance(b, (tuple, list)) else b.y
        return ((ax - bx) ** 2 + (ay - by) ** 2) ** 0.5

    class Point2(tuple):
        def __new__(cls, iterable=(0.0, 0.0)):
            xy = tuple(iterable)
            if len(xy) != 2:
                raise ValueError("Point2 needs exactly 2 coordinates")
            return super().__new__(cls, xy)

        @property
        def x(self):
            return self[0]

        @property
        def y(self):
            return self[1]

        def distance_to(self, other) -> float:
            return _distance(self, other)

        def distance_to_point2(self, other) -> float:
            return _distance(self, other)

        def towards(self, other, distance: float = 1.0) -> "Point2":
            ox = other[0] if isinstance(other, (tuple, list)) else other.x
            oy = other[1] if isinstance(other, (tuple, list)) else other.y
            dx = ox - self[0]
            dy = oy - self[1]
            length = (dx * dx + dy * dy) ** 0.5
            if length == 0:
                return Point2((self[0], self[1]))
            return Point2(
                (self[0] + dx / length * distance, self[1] + dy / length * distance)
            )

    class Point3(tuple):
        def __new__(cls, iterable=(0.0, 0.0, 0.0)):
            return super().__new__(cls, tuple(iterable))

    class Race(Enum):
        NoRace = 0
        Terran = 1
        Zerg = 2
        Protoss = 3
        Random = 4

    class Difficulty(Enum):
        VeryEasy = 1
        Easy = 2
        Medium = 3
        MediumHard = 4
        Hard = 5
        Harder = 6
        VeryHard = 7
        CheatVision = 8
        CheatMoney = 9
        CheatInsane = 10

    class AIBuild(Enum):
        RandomBuild = 0
        Rush = 1
        Timing = 2
        Power = 3
        Macro = 4
        Air = 5

    class Result(Enum):
        Victory = 1
        Defeat = 2
        Tie = 3

    class BotAI:
        pass

    class Unit:
        pass

    class Units(list):
        """Burnysc2-compatible ``Units`` collection stub.

        Mirrors ``Units(iterable, bot_object)`` signature and a small subset
        of the filter/predicate helpers exercised by unit tests.
        """

        def __init__(self, iterable=(), bot_object=None):
            super().__init__(iterable)
            self._bot_object = bot_object

        def filter(self, predicate):
            return Units((u for u in self if predicate(u)), self._bot_object)

        def sorted(self, key=None, reverse=False):
            return Units(sorted(self, key=key, reverse=reverse), self._bot_object)

        @property
        def exists(self) -> bool:
            return len(self) > 0

        @property
        def empty(self) -> bool:
            return len(self) == 0

        @property
        def amount(self) -> int:
            return len(self)

        def closer_than(self, distance, origin):
            op = origin.position if hasattr(origin, "position") else origin
            return self.filter(lambda u: _distance(u.position, op) < distance)

        def further_than(self, distance, origin):
            op = origin.position if hasattr(origin, "position") else origin
            return self.filter(lambda u: _distance(u.position, op) > distance)

    sc2 = types.ModuleType("sc2")
    mods = {
        "sc2": sc2,
        "sc2.ids": types.ModuleType("sc2.ids"),
        "sc2.ids.unit_typeid": types.ModuleType("sc2.ids.unit_typeid"),
        "sc2.ids.ability_id": types.ModuleType("sc2.ids.ability_id"),
        "sc2.ids.upgrade_id": types.ModuleType("sc2.ids.upgrade_id"),
        "sc2.ids.buff_id": types.ModuleType("sc2.ids.buff_id"),
        "sc2.ids.effect_id": types.ModuleType("sc2.ids.effect_id"),
        "sc2.position": types.ModuleType("sc2.position"),
        "sc2.data": types.ModuleType("sc2.data"),
        "sc2.bot_ai": types.ModuleType("sc2.bot_ai"),
        "sc2.unit": types.ModuleType("sc2.unit"),
        "sc2.units": types.ModuleType("sc2.units"),
    }

    mods["sc2.ids.unit_typeid"].UnitTypeId = UnitTypeId
    mods["sc2.ids.ability_id"].AbilityId = AbilityId
    mods["sc2.ids.upgrade_id"].UpgradeId = UpgradeId
    mods["sc2.ids.buff_id"].BuffId = BuffId
    mods["sc2.ids.effect_id"].EffectId = EffectId
    mods["sc2.position"].Point2 = Point2
    mods["sc2.position"].Point3 = Point3
    mods["sc2.data"].Race = Race
    mods["sc2.data"].Difficulty = Difficulty
    mods["sc2.data"].AIBuild = AIBuild
    mods["sc2.data"].Result = Result
    mods["sc2.bot_ai"].BotAI = BotAI
    mods["sc2.unit"].Unit = Unit
    mods["sc2.units"].Units = Units

    for name, mod in mods.items():
        sys.modules[name] = mod

    return True
