# -*- coding: utf-8 -*-
"""Shared minimal `sc2` stub for offline test runs.

`python-sc2` cannot be installed on the standard CI runner (mpyq fails to
build), but most of the bot's unit tests only touch the enum constants and
geometry helpers. This module installs a minimal stand-in into
`sys.modules` so that `from sc2.ids.unit_typeid import UnitTypeId` (and
similar) succeed during collection.

The stub is imported and applied by both `tests/conftest.py` and
`wicked_zerg_challenger/tests/conftest.py` to keep behaviour identical
across the two test trees.
"""

from __future__ import annotations

import os
import sys
import types

# Fix protobuf compatibility with sc2 library (s2clientprotocol)
os.environ.setdefault("PROTOCOL_BUFFERS_PYTHON_IMPLEMENTATION", "python")


class _IdToken:
    """Stub stand-in for an sc2 enum member.

    Mirrors the parts of an IntEnum that bot code touches: `.name`,
    `.value`, equality, hashability, and string formatting. Crucially not
    a `str` subclass, so `isinstance(token, str)` is False — real sc2
    IDs are IntEnum members, and bot code distinguishes string upgrade
    names from enum unit ids using exactly that check.
    """

    __slots__ = ("_id_qualified", "_id_name")

    def __init__(self, qualified: str, short: str) -> None:
        self._id_qualified = qualified
        self._id_name = short

    @property
    def name(self) -> str:
        return self._id_name

    @property
    def value(self) -> str:
        return self._id_name

    def __repr__(self) -> str:
        return self._id_qualified

    def __str__(self) -> str:
        return self._id_qualified

    def __eq__(self, other):
        if isinstance(other, _IdToken):
            return self._id_qualified == other._id_qualified
        if isinstance(other, str):
            return self._id_qualified == other or self._id_name == other
        return NotImplemented

    def __ne__(self, other):
        result = self.__eq__(other)
        if result is NotImplemented:
            return result
        return not result

    def __hash__(self) -> int:
        return hash(self._id_qualified)


class _IdMeta(type):
    _cache: dict = {}

    def __getattr__(cls, name):
        if name.startswith("_"):
            raise AttributeError(name)
        key = (cls.__name__, name)
        token = _IdMeta._cache.get(key)
        if token is None:
            token = _IdToken(f"{cls.__name__}.{name}", name)
            _IdMeta._cache[key] = token
        return token

    def __getitem__(cls, name):
        return cls.__getattr__(name)


class UnitTypeId(metaclass=_IdMeta):
    pass


class UpgradeId(metaclass=_IdMeta):
    pass


class AbilityId(metaclass=_IdMeta):
    pass


class BuffId(metaclass=_IdMeta):
    pass


class EffectId(metaclass=_IdMeta):
    pass


class _NamedToken(str):
    __slots__ = ("_token_name",)

    def __new__(cls, name: str):
        obj = str.__new__(cls, name)
        obj._token_name = name
        return obj

    @property
    def name(self) -> str:
        return self._token_name

    @property
    def value(self) -> str:
        return self._token_name


class Race:
    Zerg = _NamedToken("Zerg")
    Terran = _NamedToken("Terran")
    Protoss = _NamedToken("Protoss")
    Random = _NamedToken("Random")
    NoRace = _NamedToken("NoRace")
    _ALL = {
        "Zerg": Zerg,
        "Terran": Terran,
        "Protoss": Protoss,
        "Random": Random,
        "NoRace": NoRace,
    }

    def __class_getitem__(cls, key):
        return cls._ALL.get(key, _NamedToken(str(key)))


class Result:
    Victory = "Victory"
    Defeat = "Defeat"
    Tie = "Tie"
    Undecided = "Undecided"


class Difficulty:
    VeryEasy = _NamedToken("VeryEasy")
    Easy = _NamedToken("Easy")
    Medium = _NamedToken("Medium")
    MediumHard = _NamedToken("MediumHard")
    Hard = _NamedToken("Hard")
    Harder = _NamedToken("Harder")
    VeryHard = _NamedToken("VeryHard")
    CheatVision = _NamedToken("CheatVision")
    CheatMoney = _NamedToken("CheatMoney")
    CheatInsane = _NamedToken("CheatInsane")
    _ALL = {
        "VeryEasy": VeryEasy,
        "Easy": Easy,
        "Medium": Medium,
        "MediumHard": MediumHard,
        "Hard": Hard,
        "Harder": Harder,
        "VeryHard": VeryHard,
        "CheatVision": CheatVision,
        "CheatMoney": CheatMoney,
        "CheatInsane": CheatInsane,
    }

    def __class_getitem__(cls, key):
        return cls._ALL.get(key, _NamedToken(str(key)))


class Point2(tuple):
    def __new__(cls, value=(0.0, 0.0)):
        return tuple.__new__(cls, (float(value[0]), float(value[1])))

    @property
    def x(self):
        return self[0]

    @property
    def y(self):
        return self[1]

    def distance_to(self, other):
        ox = getattr(other, "x", other[0])
        oy = getattr(other, "y", other[1])
        return ((self.x - ox) ** 2 + (self.y - oy) ** 2) ** 0.5

    def towards(self, other, distance, limit=False):
        ox = getattr(other, "x", other[0])
        oy = getattr(other, "y", other[1])
        dx, dy = ox - self.x, oy - self.y
        length = (dx * dx + dy * dy) ** 0.5 or 1.0
        return Point2(
            (self.x + dx / length * distance, self.y + dy / length * distance)
        )

    def __add__(self, other):
        return Point2((self.x + other[0], self.y + other[1]))

    def __sub__(self, other):
        return Point2((self.x - other[0], self.y - other[1]))


class Point3(Point2):
    def __new__(cls, value=(0.0, 0.0, 0.0)):
        return tuple.__new__(cls, tuple(float(v) for v in value))

    @property
    def z(self):
        return self[2]


class Units(list):
    def __init__(self, iterable=(), bot_object=None):
        super().__init__(iterable)
        self._bot_object = bot_object

    def filter(self, pred):
        return Units([u for u in self if pred(u)], self._bot_object)

    def closer_than(self, distance, target):
        return Units(
            [
                u
                for u in self
                if hasattr(u, "distance_to") and u.distance_to(target) < distance
            ],
            self._bot_object,
        )

    def further_than(self, distance, target):
        return Units(
            [
                u
                for u in self
                if hasattr(u, "distance_to") and u.distance_to(target) >= distance
            ],
            self._bot_object,
        )

    def closest_to(self, target):
        if not self:
            return None
        return min(self, key=lambda u: u.distance_to(target))

    def of_type(self, type_id):
        try:
            iter(type_id)
            wanted = set(type_id)
        except TypeError:
            wanted = {type_id}
        return Units([u for u in self if u.type_id in wanted], self._bot_object)

    @property
    def amount(self):
        return len(self)

    @property
    def exists(self):
        return bool(self)

    @property
    def empty(self):
        return not self

    @property
    def first(self):
        return self[0]

    @property
    def ready(self):
        return Units(
            [u for u in self if getattr(u, "is_ready", True)],
            self._bot_object,
        )

    @property
    def not_ready(self):
        return Units(
            [u for u in self if not getattr(u, "is_ready", True)],
            self._bot_object,
        )


class _Stub:
    pass


def install() -> bool:
    """Install the stub into `sys.modules`. Returns True if installed.

    Returns False (and leaves the existing import alone) when the real
    `python-sc2` package is importable.
    """
    try:
        import sc2  # noqa: F401

        return False
    except ImportError:
        pass

    sc2_pkg = types.ModuleType("sc2")
    sc2_pkg.__path__ = []  # mark as package

    ids_pkg = types.ModuleType("sc2.ids")
    ids_pkg.__path__ = []

    def _mod(name, **attrs):
        m = types.ModuleType(name)
        for k, v in attrs.items():
            setattr(m, k, v)
        return m

    sys.modules["sc2"] = sc2_pkg
    sys.modules["sc2.ids"] = ids_pkg
    sys.modules["sc2.ids.unit_typeid"] = _mod(
        "sc2.ids.unit_typeid", UnitTypeId=UnitTypeId
    )
    sys.modules["sc2.ids.upgrade_id"] = _mod("sc2.ids.upgrade_id", UpgradeId=UpgradeId)
    sys.modules["sc2.ids.ability_id"] = _mod("sc2.ids.ability_id", AbilityId=AbilityId)
    sys.modules["sc2.ids.buff_id"] = _mod("sc2.ids.buff_id", BuffId=BuffId)
    sys.modules["sc2.ids.effect_id"] = _mod("sc2.ids.effect_id", EffectId=EffectId)
    sys.modules["sc2.position"] = _mod("sc2.position", Point2=Point2, Point3=Point3)
    sys.modules["sc2.data"] = _mod(
        "sc2.data", Race=Race, Result=Result, Difficulty=Difficulty
    )
    sys.modules["sc2.maps"] = _mod(
        "sc2.maps", get=lambda name: types.SimpleNamespace(name=name)
    )
    sys.modules["sc2.bot_ai"] = _mod("sc2.bot_ai", BotAI=_Stub)
    sys.modules["sc2.unit"] = _mod("sc2.unit", Unit=_Stub)
    sys.modules["sc2.units"] = _mod("sc2.units", Units=Units)
    sys.modules["sc2.constants"] = _mod("sc2.constants")
    sys.modules["sc2.game_info"] = _mod("sc2.game_info", GameInfo=_Stub)
    sys.modules["sc2.game_state"] = _mod("sc2.game_state", GameState=_Stub)
    sys.modules["sc2.main"] = _mod("sc2.main", run_game=lambda *a, **kw: None)
    sys.modules["sc2.player"] = _mod(
        "sc2.player", Bot=_Stub, Computer=_Stub, Human=_Stub
    )

    sc2_pkg.ids = ids_pkg
    sc2_pkg.position = sys.modules["sc2.position"]
    sc2_pkg.data = sys.modules["sc2.data"]
    sc2_pkg.maps = sys.modules["sc2.maps"]
    return True
