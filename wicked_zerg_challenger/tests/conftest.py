# -*- coding: utf-8 -*-
"""Test configuration - runs before test collection.

Provides lightweight sc2 stubs when the real `sc2`/`burnysc2` package is not
installed, so unit tests that only depend on `Point2`, `UnitTypeId`,
`Difficulty`, `Race`, `Unit`, and `Units` for type/value checks can still be
collected and executed in offline environments such as CI.

When the real sc2 package is available, imports resolve to it and these stubs
are not registered.
"""

import os
import sys
import types

# Fix protobuf compatibility with sc2 library (s2clientprotocol)
os.environ["PROTOCOL_BUFFERS_PYTHON_IMPLEMENTATION"] = "python"


def _install_sc2_stubs():
    """Register minimal sc2.* shim modules for offline test collection."""
    try:
        import sc2  # noqa: F401

        return  # Real sc2 installed; nothing to do.
    except ImportError:
        pass

    sc2_pkg = types.ModuleType("sc2")
    sc2_pkg.__path__ = []  # mark as package

    # sc2.position
    position_mod = types.ModuleType("sc2.position")

    class Point2(tuple):
        def __new__(cls, coords=(0, 0)):
            if isinstance(coords, Point2):
                return coords
            return super().__new__(cls, (float(coords[0]), float(coords[1])))

        @property
        def x(self):
            return self[0]

        @property
        def y(self):
            return self[1]

        def distance_to(self, other):
            ox, oy = (other[0], other[1]) if not hasattr(other, "x") else (other.x, other.y)
            return ((self[0] - ox) ** 2 + (self[1] - oy) ** 2) ** 0.5

        def towards(self, other, distance):
            return Point2(self)

    class Point3(Point2):
        pass

    position_mod.Point2 = Point2
    position_mod.Point3 = Point3

    # sc2.unit
    unit_mod = types.ModuleType("sc2.unit")

    class Unit:  # minimal stand-in
        pass

    unit_mod.Unit = Unit

    # sc2.units
    units_mod = types.ModuleType("sc2.units")

    class Units(list):
        def __init__(self, items=None, bot_object=None):
            super().__init__(list(items or []))
            self._bot = bot_object

        def filter(self, predicate):
            return Units([u for u in self if predicate(u)], self._bot)

        def closer_than(self, distance, target):
            tx, ty = (target.position.x, target.position.y) if hasattr(target, "position") else (target[0], target[1])
            return Units(
                [
                    u
                    for u in self
                    if hasattr(u, "position")
                    and ((u.position.x - tx) ** 2 + (u.position.y - ty) ** 2) ** 0.5 < distance
                ],
                self._bot,
            )

    units_mod.Units = Units

    # sc2.data
    data_mod = types.ModuleType("sc2.data")

    class _Enum:
        def __init__(self, owner_name, member_name, value=None):
            self._owner = owner_name
            self.name = member_name
            self.value = value if value is not None else member_name

        def __repr__(self):
            return f"{self._owner}.{self.name}"

        def __str__(self):
            return self.__repr__()

        def __eq__(self, other):
            return (
                isinstance(other, _Enum)
                and self._owner == other._owner
                and self.name == other.name
            )

        def __hash__(self):
            return hash((self._owner, self.name))

    class _EnumMeta(type):
        def __getattr__(cls, name):
            if name.startswith("_") or name in ("name", "value"):
                raise AttributeError(name)
            inst = _Enum(cls.__name__, name)
            setattr(cls, name, inst)
            return inst

        def __getitem__(cls, name):
            return getattr(cls, name)

        def __call__(cls, value):
            for attr in dir(cls):
                if attr.startswith("_"):
                    continue
                obj = getattr(cls, attr, None)
                if isinstance(obj, _Enum) and (obj.value == value or obj.name == value):
                    return obj
            inst = _Enum(cls.__name__, str(value), value)
            return inst

        def __instancecheck__(cls, instance):
            return isinstance(instance, _Enum) and instance._owner == cls.__name__

    class Difficulty(metaclass=_EnumMeta):
        pass

    class Race(metaclass=_EnumMeta):
        pass

    class Result(metaclass=_EnumMeta):
        pass

    data_mod.Difficulty = Difficulty
    data_mod.Race = Race
    data_mod.Result = Result

    # sc2.ids package + unit_typeid
    ids_pkg = types.ModuleType("sc2.ids")
    ids_pkg.__path__ = []
    unit_typeid_mod = types.ModuleType("sc2.ids.unit_typeid")
    ability_id_mod = types.ModuleType("sc2.ids.ability_id")
    upgrade_id_mod = types.ModuleType("sc2.ids.upgrade_id")
    buff_id_mod = types.ModuleType("sc2.ids.buff_id")

    class UnitTypeId(metaclass=_EnumMeta):
        pass

    class AbilityId(metaclass=_EnumMeta):
        pass

    class UpgradeId(metaclass=_EnumMeta):
        pass

    class BuffId(metaclass=_EnumMeta):
        pass

    unit_typeid_mod.UnitTypeId = UnitTypeId
    ability_id_mod.AbilityId = AbilityId
    upgrade_id_mod.UpgradeId = UpgradeId
    buff_id_mod.BuffId = BuffId

    # sc2.bot_ai
    bot_ai_mod = types.ModuleType("sc2.bot_ai")

    class BotAI:
        pass

    bot_ai_mod.BotAI = BotAI

    # Register all shims
    modules = {
        "sc2": sc2_pkg,
        "sc2.position": position_mod,
        "sc2.unit": unit_mod,
        "sc2.units": units_mod,
        "sc2.data": data_mod,
        "sc2.ids": ids_pkg,
        "sc2.ids.unit_typeid": unit_typeid_mod,
        "sc2.ids.ability_id": ability_id_mod,
        "sc2.ids.upgrade_id": upgrade_id_mod,
        "sc2.ids.buff_id": buff_id_mod,
        "sc2.bot_ai": bot_ai_mod,
    }
    for name, mod in modules.items():
        sys.modules.setdefault(name, mod)


_install_sc2_stubs()
