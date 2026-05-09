# -*- coding: utf-8 -*-
"""Test configuration - runs before test collection.

Installs a lightweight ``sc2`` stub package when the real ``python-sc2`` is
not available, so unit tests that import ``sc2.*`` symbols can still be
collected and run their non-game-dependent assertions. Tests that exercise
real game state should still skip themselves explicitly.
"""

import os
import sys
import types

# Fix protobuf compatibility with sc2 library (s2clientprotocol)
os.environ["PROTOCOL_BUFFERS_PYTHON_IMPLEMENTATION"] = "python"


def _install_sc2_stub() -> None:
    """Install a permissive ``sc2`` stub if the real package is missing.

    The stub uses ``__getattr__`` so any attribute access (e.g.
    ``UnitTypeId.OVERLORD``, ``UnitTypeId.SOMETHING_NEW``) returns a string
    placeholder, which is enough for tests that only need stable, hashable
    identifiers.
    """
    try:
        import sc2  # noqa: F401

        return
    except ImportError:
        pass

    class _IdMember:
        """A stand-in for an sc2 enum member with a stable name and value."""

        __slots__ = ("_name", "_cls_name")

        def __init__(self, cls_name, name):
            self._cls_name = cls_name
            self._name = name

        @property
        def name(self):
            return self._name

        @property
        def value(self):
            return self._name

        def __repr__(self):
            return f"{self._cls_name}.{self._name}"

        def __str__(self):
            return self._name

        def __eq__(self, other):
            if isinstance(other, _IdMember):
                return self._cls_name == other._cls_name and self._name == other._name
            if isinstance(other, str):
                return self._name == other
            return NotImplemented

        def __hash__(self):
            return hash((self._cls_name, self._name))

    class _AnyIdMeta(type):
        """Metaclass that lazily returns an _IdMember for any attribute access."""

        def __getattr__(cls, name):  # type: ignore[override]
            if name.startswith("_"):
                raise AttributeError(name)
            member = _IdMember(cls.__name__, name)
            setattr(cls, name, member)
            return member

        def __getitem__(cls, name):  # type: ignore[override]
            return getattr(cls, name)

        def __iter__(cls):  # type: ignore[override]
            return iter(())

    def _make_id_class(name):
        return _AnyIdMeta(name, (), {})

    UnitTypeId = _make_id_class("UnitTypeId")
    AbilityId = _make_id_class("AbilityId")
    UpgradeId = _make_id_class("UpgradeId")
    EffectId = _make_id_class("EffectId")
    BuffId = _make_id_class("BuffId")

    class Point2(tuple):
        def __new__(cls, *args):
            if len(args) == 1:
                return super().__new__(cls, tuple(args[0]))
            return super().__new__(cls, args)

        @property
        def x(self):
            return self[0]

        @property
        def y(self):
            return self[1]

        def distance_to(self, other):
            ox, oy = (other[0], other[1]) if not hasattr(other, "x") else (other.x, other.y)
            return ((self[0] - ox) ** 2 + (self[1] - oy) ** 2) ** 0.5

    class Point3(tuple):
        def __new__(cls, *args):
            if len(args) == 1:
                return super().__new__(cls, tuple(args[0]))
            return super().__new__(cls, args)

    class _EnumLikeMeta(type):
        """Class[member] subscript access returns a member with a .name attribute."""

        def __getitem__(cls, name):  # type: ignore[override]
            return cls._member_for(name)

    class _EnumLikeBase(metaclass=_EnumLikeMeta):
        _members = ()  # type: ignore[var-annotated]

        @classmethod
        def _member_for(cls, name):
            inst = cls.__new__(cls)
            inst._name = name
            return inst

        def __init__(self, name=""):
            self._name = name

        @property
        def name(self):
            return self._name

        @property
        def value(self):
            return self._name

        def __repr__(self):
            return f"{type(self).__name__}.{self._name}"

        def __str__(self):
            return self._name

        def __eq__(self, other):
            if isinstance(other, _EnumLikeBase):
                return type(self) is type(other) and self._name == other._name
            if isinstance(other, str):
                return self._name == other
            return NotImplemented

        def __hash__(self):
            return hash((type(self).__name__, self._name))

    def _make_enum_like(name, members):
        cls = _EnumLikeMeta(name, (_EnumLikeBase,), {"_members": tuple(members)})
        for member in members:
            setattr(cls, member, cls._member_for(member))
        return cls

    Race = _make_enum_like("Race", ["Zerg", "Protoss", "Terran", "Random", "NoRace"])
    Difficulty = _make_enum_like(
        "Difficulty",
        [
            "VeryEasy",
            "Easy",
            "Medium",
            "MediumHard",
            "Hard",
            "Harder",
            "VeryHard",
            "CheatVision",
            "CheatMoney",
            "CheatInsane",
        ],
    )
    Result = _make_enum_like("Result", ["Victory", "Defeat", "Tie", "Undecided"])

    class BotAI:
        pass

    class Bot:
        def __init__(self, race=None, ai=None, name=None):
            self.race = race
            self.ai = ai
            self.name = name

    class Computer:
        def __init__(self, race=None, difficulty=None, ai_build=None):
            self.race = race
            self.difficulty = difficulty
            self.ai_build = ai_build

    class Unit:
        pass

    class Units(list):
        def __init__(self, units=(), bot_object=None):
            super().__init__(units)
            self._bot = bot_object

        def filter(self, predicate):
            return Units([u for u in self if predicate(u)], self._bot)

        def closer_than(self, distance, position):
            ref = position
            ref_xy = (ref.x, ref.y) if hasattr(ref, "x") else (ref[0], ref[1])

            def _close(u):
                if hasattr(u, "distance_to"):
                    try:
                        return u.distance_to(position) < distance
                    except Exception:
                        return False
                if hasattr(u, "position"):
                    px, py = u.position
                    return ((px - ref_xy[0]) ** 2 + (py - ref_xy[1]) ** 2) ** 0.5 < distance
                return False

            return Units([u for u in self if _close(u)], self._bot)

    def run_game(*args, **kwargs):
        raise RuntimeError("sc2 stub: run_game is not available in test environment")

    def run_ladder_game(*args, **kwargs):
        raise RuntimeError("sc2 stub: run_ladder_game is not available in test environment")

    sc2 = types.ModuleType("sc2")
    sc2.BotAI = BotAI
    sc2.Race = Race
    sc2.Difficulty = Difficulty
    sc2.Result = Result
    sc2.run_game = run_game

    bot_ai_mod = types.ModuleType("sc2.bot_ai")
    bot_ai_mod.BotAI = BotAI

    data_mod = types.ModuleType("sc2.data")
    data_mod.Race = Race
    data_mod.Difficulty = Difficulty
    data_mod.Result = Result

    main_mod = types.ModuleType("sc2.main")
    main_mod.run_game = run_game
    main_mod.run_ladder_game = run_ladder_game

    player_mod = types.ModuleType("sc2.player")
    player_mod.Bot = Bot
    player_mod.Computer = Computer

    position_mod = types.ModuleType("sc2.position")
    position_mod.Point2 = Point2
    position_mod.Point3 = Point3

    unit_mod = types.ModuleType("sc2.unit")
    unit_mod.Unit = Unit

    units_mod = types.ModuleType("sc2.units")
    units_mod.Units = Units

    ids_mod = types.ModuleType("sc2.ids")
    unit_typeid_mod = types.ModuleType("sc2.ids.unit_typeid")
    unit_typeid_mod.UnitTypeId = UnitTypeId
    ability_id_mod = types.ModuleType("sc2.ids.ability_id")
    ability_id_mod.AbilityId = AbilityId
    upgrade_id_mod = types.ModuleType("sc2.ids.upgrade_id")
    upgrade_id_mod.UpgradeId = UpgradeId
    effect_id_mod = types.ModuleType("sc2.ids.effect_id")
    effect_id_mod.EffectId = EffectId
    buff_id_mod = types.ModuleType("sc2.ids.buff_id")
    buff_id_mod.BuffId = BuffId

    maps_mod = types.ModuleType("sc2.maps")

    sys.modules.setdefault("sc2", sc2)
    sys.modules.setdefault("sc2.bot_ai", bot_ai_mod)
    sys.modules.setdefault("sc2.data", data_mod)
    sys.modules.setdefault("sc2.main", main_mod)
    sys.modules.setdefault("sc2.player", player_mod)
    sys.modules.setdefault("sc2.position", position_mod)
    sys.modules.setdefault("sc2.unit", unit_mod)
    sys.modules.setdefault("sc2.units", units_mod)
    sys.modules.setdefault("sc2.ids", ids_mod)
    sys.modules.setdefault("sc2.ids.unit_typeid", unit_typeid_mod)
    sys.modules.setdefault("sc2.ids.ability_id", ability_id_mod)
    sys.modules.setdefault("sc2.ids.upgrade_id", upgrade_id_mod)
    sys.modules.setdefault("sc2.ids.effect_id", effect_id_mod)
    sys.modules.setdefault("sc2.ids.buff_id", buff_id_mod)
    sys.modules.setdefault("sc2.maps", maps_mod)


_install_sc2_stub()
