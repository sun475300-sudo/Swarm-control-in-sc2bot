"""Minimal sc2 stub used when burnysc2 is not installed.

The real burnysc2 package depends on mpyq which requires a native build.
The CI runner and many dev containers cannot build mpyq, so tests must run
without the real package.

This stub provides:
- sc2.bot_ai.BotAI base class
- sc2.data.Race / Difficulty enums
- sc2.position.Point2 minimal vector
- sc2.ids.unit_typeid.UnitTypeId (auto-populated enum-like class)
- sc2.ids.upgrade_id.UpgradeId
- sc2.ids.ability_id.AbilityId
- sc2.ids.buff_id.BuffId
- sc2.ids.effect_id.EffectId

Enum-like classes intentionally use ``__getattr__`` so any new identifier
referenced by bot code resolves to a unique sentinel without needing manual
updates here.
"""

from __future__ import annotations

import sys
import types
from typing import Any


class _AutoEnumValue:
    """Sentinel object representing one enum member."""

    __slots__ = ("_cls", "_name", "value")

    def __init__(self, cls: str, name: str, value: int) -> None:
        self._cls = cls
        self._name = name
        self.value = value

    @property
    def name(self) -> str:
        return self._name

    def __repr__(self) -> str:
        return f"<{self._cls}.{self._name}: {self.value}>"

    def __str__(self) -> str:
        return f"{self._cls}.{self._name}"

    def __eq__(self, other: object) -> bool:
        if isinstance(other, _AutoEnumValue):
            return self._cls == other._cls and self._name == other._name
        return NotImplemented

    def __hash__(self) -> int:
        return hash((self._cls, self._name))

    def __int__(self) -> int:
        return self.value


class _AutoEnumMeta(type):
    """Metaclass that auto-generates :class:`_AutoEnumValue` members on access."""

    _registry: dict[str, dict[str, _AutoEnumValue]] = {}
    _counter: dict[str, int] = {}

    def __getattr__(cls, item: str) -> _AutoEnumValue:
        if item.startswith("_") or item in {"mro", "value", "name"}:
            raise AttributeError(item)
        members = _AutoEnumMeta._registry.setdefault(cls.__name__, {})
        if item not in members:
            _AutoEnumMeta._counter[cls.__name__] = (
                _AutoEnumMeta._counter.get(cls.__name__, 0) + 1
            )
            members[item] = _AutoEnumValue(
                cls.__name__, item, _AutoEnumMeta._counter[cls.__name__]
            )
        return members[item]

    def __iter__(cls):
        return iter(_AutoEnumMeta._registry.get(cls.__name__, {}).values())

    def __contains__(cls, item: Any) -> bool:
        if isinstance(item, _AutoEnumValue):
            return item._cls == cls.__name__
        return False

    def __getitem__(cls, name: str) -> _AutoEnumValue:
        """Mimic enum.Enum subscript: ``Race["Terran"]`` -> member."""
        if not isinstance(name, str):
            raise KeyError(name)
        members = _AutoEnumMeta._registry.setdefault(cls.__name__, {})
        if name not in members:
            _AutoEnumMeta._counter[cls.__name__] = (
                _AutoEnumMeta._counter.get(cls.__name__, 0) + 1
            )
            members[name] = _AutoEnumValue(
                cls.__name__, name, _AutoEnumMeta._counter[cls.__name__]
            )
        return members[name]

    def __instancecheck__(cls, instance: Any) -> bool:
        """Make ``isinstance(value, Race)`` true for any auto-enum member of that class."""
        return isinstance(instance, _AutoEnumValue) and instance._cls == cls.__name__


class UnitTypeId(metaclass=_AutoEnumMeta):
    pass


class UpgradeId(metaclass=_AutoEnumMeta):
    pass


class AbilityId(metaclass=_AutoEnumMeta):
    pass


class BuffId(metaclass=_AutoEnumMeta):
    pass


class EffectId(metaclass=_AutoEnumMeta):
    pass


class Race(metaclass=_AutoEnumMeta):
    pass


# Pre-seed the well-known race shorthands the bot expects.
Race.Zerg  # noqa: B018
Race.Terran  # noqa: B018
Race.Protoss  # noqa: B018
Race.Random  # noqa: B018


class Difficulty(metaclass=_AutoEnumMeta):
    pass


Difficulty.VeryEasy  # noqa: B018
Difficulty.Easy  # noqa: B018
Difficulty.Medium  # noqa: B018
Difficulty.MediumHard  # noqa: B018
Difficulty.Hard  # noqa: B018
Difficulty.Harder  # noqa: B018
Difficulty.VeryHard  # noqa: B018
Difficulty.CheatVision  # noqa: B018
Difficulty.CheatMoney  # noqa: B018
Difficulty.CheatInsane  # noqa: B018


class Point2(tuple):
    """Minimal 2D point compatible with burnysc2.position.Point2."""

    def __new__(cls, xy):
        if isinstance(xy, Point2):
            return xy
        x, y = xy
        return super().__new__(cls, (float(x), float(y)))

    @property
    def x(self) -> float:
        return self[0]

    @property
    def y(self) -> float:
        return self[1]

    def distance_to(self, other) -> float:
        ox, oy = other[0], other[1]
        return ((self.x - ox) ** 2 + (self.y - oy) ** 2) ** 0.5

    def distance_to_point2(self, other) -> float:
        return self.distance_to(other)

    def towards(self, other, distance: float = 1.0) -> "Point2":
        ox, oy = other[0], other[1]
        dx, dy = ox - self.x, oy - self.y
        length = (dx * dx + dy * dy) ** 0.5 or 1.0
        return Point2(
            (self.x + dx / length * distance, self.y + dy / length * distance)
        )

    def offset(self, p) -> "Point2":
        return Point2((self.x + p[0], self.y + p[1]))

    def rounded(self) -> "Point2":
        return Point2((round(self.x), round(self.y)))

    def __add__(self, other):  # type: ignore[override]
        if isinstance(other, (tuple, list, Point2)):
            return Point2((self.x + other[0], self.y + other[1]))
        return Point2((self.x + other, self.y + other))

    def __sub__(self, other):
        if isinstance(other, (tuple, list, Point2)):
            return Point2((self.x - other[0], self.y - other[1]))
        return Point2((self.x - other, self.y - other))


class Point3(Point2):
    def __new__(cls, xyz):
        x, y, z = xyz
        instance = tuple.__new__(cls, (float(x), float(y), float(z)))
        return instance

    @property
    def z(self) -> float:
        return self[2]


class BotAI:
    """Stand-in for burnysc2's BotAI base class.

    Real BotAI exposes a large surface (state, units, structures, etc.).
    Tests typically subclass it but inject their own state via mocks, so we
    only need a no-op base class.
    """

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        pass

    async def on_start(self) -> None:
        return None

    async def on_step(self, iteration: int) -> None:
        return None


class Unit:
    """Minimal Unit placeholder. Tests inject MagicMocks for real behavior."""

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        pass


class Units(list):
    """Minimal Units container — behaves like a list."""

    def __init__(self, iterable=(), bot=None) -> None:
        super().__init__(iterable)
        self.bot = bot

    def filter(self, predicate):
        return Units([u for u in self if predicate(u)], self.bot)

    @property
    def amount(self) -> int:
        return len(self)

    @property
    def empty(self) -> bool:
        return len(self) == 0

    @property
    def exists(self) -> bool:
        return len(self) > 0

    def closer_than(self, distance, position):
        px, py = position[0], position[1]
        return Units(
            [
                u
                for u in self
                if hasattr(u, "position")
                and ((u.position[0] - px) ** 2 + (u.position[1] - py) ** 2) ** 0.5
                < distance
            ],
            self.bot,
        )

    def closest_to(self, position):
        if not self:
            return None
        px, py = position[0], position[1]
        return min(
            self,
            key=lambda u: (
                ((u.position[0] - px) ** 2 + (u.position[1] - py) ** 2)
                if hasattr(u, "position")
                else float("inf")
            ),
        )


def _build_maps_module() -> types.ModuleType:
    mod = types.ModuleType("sc2.maps")

    def get(map_name: str):  # noqa: ARG001
        return map_name

    mod.get = get
    return mod


def _build_main_module() -> types.ModuleType:
    mod = types.ModuleType("sc2.main")

    def run_game(*args: Any, **kwargs: Any):  # noqa: ARG001
        return None

    def run_replay(*args: Any, **kwargs: Any):  # noqa: ARG001
        return None

    mod.run_game = run_game
    mod.run_replay = run_replay
    return mod


def _build_player_module() -> types.ModuleType:
    mod = types.ModuleType("sc2.player")

    class _Player:
        def __init__(self, race=None, difficulty=None, name: str = "Player") -> None:
            self.race = race
            self.difficulty = difficulty
            self.name = name

    class Bot(_Player):
        def __init__(self, race=None, ai=None, name: str = "Bot") -> None:
            super().__init__(race=race, name=name)
            self.ai = ai

    class Computer(_Player):
        pass

    class Human(_Player):
        pass

    mod.Bot = Bot
    mod.Computer = Computer
    mod.Human = Human
    return mod


class Result:
    Victory = "Victory"
    Defeat = "Defeat"
    Tie = "Tie"
    Undecided = "Undecided"


def _install() -> None:
    """Register stub modules in :mod:`sys.modules`."""
    pkg = types.ModuleType("sc2")
    pkg.__path__ = []  # mark as package
    sys.modules.setdefault("sc2", pkg)

    bot_ai = types.ModuleType("sc2.bot_ai")
    bot_ai.BotAI = BotAI
    sys.modules.setdefault("sc2.bot_ai", bot_ai)
    pkg.bot_ai = bot_ai

    data = types.ModuleType("sc2.data")
    data.Race = Race
    data.Difficulty = Difficulty
    data.Result = Result
    sys.modules.setdefault("sc2.data", data)
    pkg.data = data

    position = types.ModuleType("sc2.position")
    position.Point2 = Point2
    position.Point3 = Point3
    sys.modules.setdefault("sc2.position", position)
    pkg.position = position

    unit = types.ModuleType("sc2.unit")
    unit.Unit = Unit
    sys.modules.setdefault("sc2.unit", unit)
    pkg.unit = unit

    units = types.ModuleType("sc2.units")
    units.Units = Units
    sys.modules.setdefault("sc2.units", units)
    pkg.units = units

    maps_mod = _build_maps_module()
    sys.modules.setdefault("sc2.maps", maps_mod)
    pkg.maps = maps_mod

    main_mod = _build_main_module()
    sys.modules.setdefault("sc2.main", main_mod)
    pkg.main = main_mod

    player_mod = _build_player_module()
    sys.modules.setdefault("sc2.player", player_mod)
    pkg.player = player_mod

    ids = types.ModuleType("sc2.ids")
    ids.__path__ = []
    sys.modules.setdefault("sc2.ids", ids)
    pkg.ids = ids

    for sub, cls in (
        ("unit_typeid", UnitTypeId),
        ("upgrade_id", UpgradeId),
        ("ability_id", AbilityId),
        ("buff_id", BuffId),
        ("effect_id", EffectId),
    ):
        mod = types.ModuleType(f"sc2.ids.{sub}")
        attr_name = {
            "unit_typeid": "UnitTypeId",
            "upgrade_id": "UpgradeId",
            "ability_id": "AbilityId",
            "buff_id": "BuffId",
            "effect_id": "EffectId",
        }[sub]
        setattr(mod, attr_name, cls)
        sys.modules.setdefault(f"sc2.ids.{sub}", mod)
        setattr(ids, sub, mod)


_install()
