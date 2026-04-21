# -*- coding: utf-8 -*-
"""Test configuration - runs before test collection.

Provides fallback stubs for the ``sc2`` (burnysc2) package so unit tests
can run in environments where burnysc2 is not installed. Tests that want
real SC2 behaviour should skip themselves when the real module is missing.
"""
import os
import sys
import types
from enum import Enum

# Fix protobuf compatibility with sc2 library (s2clientprotocol)
os.environ["PROTOCOL_BUFFERS_PYTHON_IMPLEMENTATION"] = "python"


def _ensure_sc2_stub() -> None:
    """Install a lightweight ``sc2`` stub into ``sys.modules`` if absent.

    This mirrors the minimal surface area the test modules reach for: unit /
    ability / upgrade / buff IDs accessed as attributes, ``Point2`` geometry,
    ``Race``/``Difficulty`` enums, and a ``BotAI`` placeholder. Attribute
    access on the ID classes is dynamic so any identifier name resolves to a
    stable string token, which is sufficient for comparisons in tests.
    """
    try:
        import sc2  # type: ignore  # noqa: F401
        return
    except ImportError:
        pass

    class _IdMember:
        """Enum-like member with ``name`` / ``value`` attributes.

        Instances compare and hash by name so they behave like the real
        ``sc2.ids.*`` enum members that code under test expects.
        """

        __slots__ = ("name", "value")

        def __init__(self, name: str, value: int = 0):
            self.name = name
            self.value = value

        def __repr__(self) -> str:  # pragma: no cover - debug aid
            return f"<{type(self).__name__}.{self.name}>"

        def __str__(self) -> str:
            return self.name

        def __eq__(self, other) -> bool:
            if isinstance(other, _IdMember):
                return self.name == other.name and type(self) is type(other)
            if isinstance(other, str):
                return self.name == other
            return NotImplemented

        def __ne__(self, other) -> bool:
            result = self.__eq__(other)
            if result is NotImplemented:
                return result
            return not result

        def __hash__(self) -> int:
            return hash((type(self).__name__, self.name))

    class _DynamicIdMeta(type):
        def __getattr__(cls, name: str):  # type: ignore[override]
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
            ox, oy = other[0], other[1]
            return ((self[0] - ox) ** 2 + (self[1] - oy) ** 2) ** 0.5

        def distance_to_point2(self, other) -> float:
            return self.distance_to(other)

        def towards(self, other, distance: float = 1.0) -> "Point2":
            dx = other[0] - self[0]
            dy = other[1] - self[1]
            length = (dx * dx + dy * dy) ** 0.5
            if length == 0:
                return Point2((self[0], self[1]))
            return Point2((self[0] + dx / length * distance, self[1] + dy / length * distance))

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
        """Lightweight Units collection stub.

        Real burnysc2 ``Units`` accepts ``(iterable, bot_object)``; the bot
        reference is kept so filter methods can return new ``Units``
        instances bound to the same bot.
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
    sc2_ids = types.ModuleType("sc2.ids")
    sc2_unit_typeid = types.ModuleType("sc2.ids.unit_typeid")
    sc2_ability_id = types.ModuleType("sc2.ids.ability_id")
    sc2_upgrade_id = types.ModuleType("sc2.ids.upgrade_id")
    sc2_buff_id = types.ModuleType("sc2.ids.buff_id")
    sc2_effect_id = types.ModuleType("sc2.ids.effect_id")
    sc2_position = types.ModuleType("sc2.position")
    sc2_data = types.ModuleType("sc2.data")
    sc2_bot_ai = types.ModuleType("sc2.bot_ai")
    sc2_unit = types.ModuleType("sc2.unit")
    sc2_units = types.ModuleType("sc2.units")

    sc2_unit_typeid.UnitTypeId = UnitTypeId
    sc2_ability_id.AbilityId = AbilityId
    sc2_upgrade_id.UpgradeId = UpgradeId
    sc2_buff_id.BuffId = BuffId
    sc2_effect_id.EffectId = EffectId
    sc2_position.Point2 = Point2
    sc2_position.Point3 = Point3
    sc2_data.Race = Race
    sc2_data.Difficulty = Difficulty
    sc2_data.AIBuild = AIBuild
    sc2_data.Result = Result
    sc2_bot_ai.BotAI = BotAI
    sc2_unit.Unit = Unit
    sc2_units.Units = Units

    sys.modules["sc2"] = sc2
    sys.modules["sc2.ids"] = sc2_ids
    sys.modules["sc2.ids.unit_typeid"] = sc2_unit_typeid
    sys.modules["sc2.ids.ability_id"] = sc2_ability_id
    sys.modules["sc2.ids.upgrade_id"] = sc2_upgrade_id
    sys.modules["sc2.ids.buff_id"] = sc2_buff_id
    sys.modules["sc2.ids.effect_id"] = sc2_effect_id
    sys.modules["sc2.position"] = sc2_position
    sys.modules["sc2.data"] = sc2_data
    sys.modules["sc2.bot_ai"] = sc2_bot_ai
    sys.modules["sc2.unit"] = sc2_unit
    sys.modules["sc2.units"] = sc2_units


_ensure_sc2_stub()
