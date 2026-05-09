# -*- coding: utf-8 -*-
"""Lightweight stand-in for the burnysc2 package.

The real ``sc2`` package depends on a full StarCraft II installation. For unit
tests we just need import-resolvable stand-ins that mimic the public surface
the bot touches: ``UnitTypeId``/``AbilityId``/``UpgradeId`` enum-style classes,
``Point2``/``Point3``, ``Race``/``Difficulty``/``Result`` data, and skeleton
``BotAI``/``Unit``/``Units`` classes.

We register all submodules directly into ``sys.modules`` so subsequent
``from sc2.xxx import yyy`` statements resolve without touching disk.
"""

from __future__ import annotations

import sys
import types


class _IdMember(int):
    """Enum-style value carrying ``name`` and ``value`` attributes.

    Production code routinely calls ``unit.type_id.name`` or compares a
    ``UnitTypeId`` against another via ``==``. By subclassing ``int`` we keep
    set/dict membership cheap and stable while still exposing ``.name``.
    """

    _next_value = 1
    _name: str = ""

    def __new__(cls, name, value=None):
        if value is None:
            value = cls._next_value
            cls._next_value += 1
        obj = int.__new__(cls, int(value))
        obj._name = name
        return obj

    @property
    def name(self):
        return self._name

    @property
    def value(self):
        return int(self)

    def __repr__(self):
        return f"<{type(self).__name__}.{self._name}>"

    def __str__(self):
        return self._name

    def __eq__(self, other):
        if isinstance(other, _IdMember):
            return type(self) is type(other) and self._name == other._name
        if isinstance(other, str):
            return self._name == other
        if isinstance(other, int):
            return int(self) == int(other)
        return NotImplemented

    def __ne__(self, other):
        eq = self.__eq__(other)
        return eq if eq is NotImplemented else not eq

    def __hash__(self):
        return hash((type(self).__name__, self._name))


class _AttrAuto(type):
    """Metaclass that lazily mints ``_IdMember`` instances on attribute access."""

    def __getattr__(cls, name):  # type: ignore[override]
        if name.startswith("__"):
            raise AttributeError(name)
        cache = cls.__dict__.get("_cache")
        if cache is None:
            cache = {}
            type.__setattr__(cls, "_cache", cache)
        if name not in cache:
            cache[name] = cls(name)
        return cache[name]

    def __iter__(cls):
        return iter(cls.__dict__.get("_cache", {}).values())

    def __contains__(cls, item):
        cache = cls.__dict__.get("_cache") or {}
        if isinstance(item, _IdMember):
            return item._name in cache
        if isinstance(item, str):
            return item in cache
        return False


class UnitTypeId(_IdMember, metaclass=_AttrAuto):
    """Stub – ``UnitTypeId.MUTALISK`` returns an enum-like int with ``.name``."""


class AbilityId(_IdMember, metaclass=_AttrAuto):
    pass


class UpgradeId(_IdMember, metaclass=_AttrAuto):
    pass


class BuffId(_IdMember, metaclass=_AttrAuto):
    pass


class EffectId(_IdMember, metaclass=_AttrAuto):
    pass


class _EnumMeta(type):
    """Metaclass that allows enum-style ``Cls[name]`` and iteration."""

    def __getitem__(cls, name):
        members = cls.__dict__.get("_members") or {}
        try:
            return members[name]
        except KeyError as exc:
            raise KeyError(name) from exc

    def __iter__(cls):
        return iter((cls.__dict__.get("_members") or {}).values())

    def __contains__(cls, item):
        members = cls.__dict__.get("_members") or {}
        if isinstance(item, str):
            return item in members
        return item in members.values()


class _EnumLikeBase(metaclass=_EnumMeta):
    _members: dict = {}

    def __init__(self, name, value=None):
        self.name = name
        self.value = name if value is None else value

    def __repr__(self):
        return f"<{type(self).__name__}.{self.name}>"

    def __eq__(self, other):
        if isinstance(other, _EnumLikeBase):
            return type(self) is type(other) and self.name == other.name
        return self.name == other or self.value == other

    def __hash__(self):
        return hash((type(self).__name__, self.name))

    @classmethod
    def _register(cls, name, value=None):
        member = cls(name, value)
        # Each subclass owns its own ``_members`` mapping so siblings don't
        # collide (Race vs Difficulty vs Result).
        if "_members" not in cls.__dict__:
            cls._members = {}
        cls._members[name] = member
        setattr(cls, name, member)
        return member


class Race(_EnumLikeBase):
    _members: dict = {}


Race._register("Zerg", 1)
Race._register("Protoss", 2)
Race._register("Terran", 3)
Race._register("Random", 4)
Race._register("NoRace", 0)


class Difficulty(_EnumLikeBase):
    _members: dict = {}


for _idx, _name in enumerate(
    (
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
    ),
    start=1,
):
    Difficulty._register(_name, _idx)


class Result(_EnumLikeBase):
    _members: dict = {}


Result._register("Victory", 1)
Result._register("Defeat", 2)
Result._register("Tie", 3)
Result._register("Undecided", 4)


class Point2(tuple):
    def __new__(cls, *args):
        if len(args) == 1:
            x, y = args[0]
        elif len(args) == 2:
            x, y = args
        else:
            x, y = 0.0, 0.0
        obj = super().__new__(cls, (float(x), float(y)))
        return obj

    @property
    def x(self):
        return self[0]

    @property
    def y(self):
        return self[1]

    def distance_to(self, other):
        dx = self[0] - other[0]
        dy = self[1] - other[1]
        return (dx * dx + dy * dy) ** 0.5

    def towards(self, other, distance=1.0):
        dx = other[0] - self[0]
        dy = other[1] - self[1]
        length = (dx * dx + dy * dy) ** 0.5 or 1.0
        return Point2(
            self[0] + dx / length * distance, self[1] + dy / length * distance
        )

    def __add__(self, other):
        return Point2(self[0] + other[0], self[1] + other[1])

    def __sub__(self, other):
        return Point2(self[0] - other[0], self[1] - other[1])


class Point3(tuple):
    def __new__(cls, *args):
        if len(args) == 1:
            x, y, z = args[0]
        elif len(args) == 3:
            x, y, z = args
        else:
            x, y, z = 0.0, 0.0, 0.0
        return super().__new__(cls, (float(x), float(y), float(z)))

    @property
    def x(self):
        return self[0]

    @property
    def y(self):
        return self[1]

    @property
    def z(self):
        return self[2]


class BotAI:
    """Minimal BotAI stand-in. Override attributes/methods in tests as needed."""

    def __init__(self, *args, **kwargs):
        self.minerals = 0
        self.vespene = 0
        self.supply_used = 0
        self.supply_cap = 0
        self.supply_left = 0
        self.time = 0.0
        self.iteration = 0
        self.race = Race.Zerg
        self.enemy_race = Race.Random


class Unit:
    def __init__(self, *args, **kwargs):
        self.tag = kwargs.get("tag", 0)
        self.position = Point2(0, 0)
        self.health = 100
        self.health_max = 100
        self.shield = 0
        self.shield_max = 0
        self.energy = 0
        self.is_burrowed = False

    def distance_to(self, other):
        return self.position.distance_to(getattr(other, "position", other))


class Units(list):
    """List-like collection mirroring burnysc2's Units helper."""

    def __init__(self, units=None, bot_object=None):
        super().__init__(units or [])
        self.bot_object = bot_object

    def filter(self, pred):
        return Units([u for u in self if pred(u)], self.bot_object)

    def closer_than(self, distance, position):
        pos = getattr(position, "position", position)
        return self.filter(lambda u: u.position.distance_to(pos) < distance)

    def further_than(self, distance, position):
        pos = getattr(position, "position", position)
        return self.filter(lambda u: u.position.distance_to(pos) >= distance)

    def of_type(self, type_id):
        ids = type_id if isinstance(type_id, (set, list, tuple)) else {type_id}
        return self.filter(lambda u: getattr(u, "type_id", None) in ids)

    @property
    def amount(self):
        return len(self)

    @property
    def exists(self):
        return len(self) > 0

    def closest_to(self, position):
        if not self:
            return None
        pos = getattr(position, "position", position)
        return min(self, key=lambda u: u.position.distance_to(pos))

    def first(self):
        return self[0] if self else None

    def __or__(self, other):
        return Units(list(self) + list(other), self.bot_object)


class GameInfo:
    def __init__(self, *args, **kwargs):
        self.map_size = Point2(176, 176)
        self.player_start_location = Point2(0, 0)
        self.map_center = Point2(88, 88)


class Bot:
    def __init__(self, race, ai, name=None):
        self.race = race
        self.ai = ai
        self.name = name


class Computer:
    def __init__(self, race, difficulty, build=None):
        self.race = race
        self.difficulty = difficulty
        self.build = build


def run_game(*args, **kwargs):  # pragma: no cover - tests should not invoke
    raise RuntimeError("run_game stub – install burnysc2 to run real games")


def run_ladder_game(*args, **kwargs):  # pragma: no cover
    raise RuntimeError("run_ladder_game stub – install burnysc2 to run real games")


def get_map(map_name):  # used by `from sc2 import maps; maps.get(...)`
    return map_name


def install_into_sys_modules():
    """Insert the stub package into ``sys.modules`` (idempotent)."""

    def _module(name):
        mod = types.ModuleType(name)
        sys.modules[name] = mod
        return mod

    if "sc2" in sys.modules:
        return

    sc2 = _module("sc2")
    sc2.maps = _module("sc2.maps")
    sc2.maps.get = get_map

    data = _module("sc2.data")
    data.Race = Race
    data.Difficulty = Difficulty
    data.Result = Result
    sc2.data = data

    difficulty_mod = _module("sc2.difficulty")
    difficulty_mod.Difficulty = Difficulty

    race_mod = _module("sc2.race")
    race_mod.Race = Race

    ids = _module("sc2.ids")
    sc2.ids = ids

    unit_typeid = _module("sc2.ids.unit_typeid")
    unit_typeid.UnitTypeId = UnitTypeId
    ids.unit_typeid = unit_typeid

    ability_id = _module("sc2.ids.ability_id")
    ability_id.AbilityId = AbilityId
    ids.ability_id = ability_id

    upgrade_id = _module("sc2.ids.upgrade_id")
    upgrade_id.UpgradeId = UpgradeId
    ids.upgrade_id = upgrade_id

    buff_id = _module("sc2.ids.buff_id")
    buff_id.BuffId = BuffId
    ids.buff_id = buff_id

    effect_id = _module("sc2.ids.effect_id")
    effect_id.EffectId = EffectId
    ids.effect_id = effect_id

    bot_ai = _module("sc2.bot_ai")
    bot_ai.BotAI = BotAI
    sc2.bot_ai = bot_ai

    position = _module("sc2.position")
    position.Point2 = Point2
    position.Point3 = Point3
    sc2.position = position

    unit = _module("sc2.unit")
    unit.Unit = Unit
    sc2.unit = unit

    units = _module("sc2.units")
    units.Units = Units
    sc2.units = units

    game_info = _module("sc2.game_info")
    game_info.GameInfo = GameInfo
    sc2.game_info = game_info

    player = _module("sc2.player")
    player.Bot = Bot
    player.Computer = Computer
    sc2.player = player

    main = _module("sc2.main")
    main.run_game = run_game
    main.run_ladder_game = run_ladder_game
    sc2.main = main
