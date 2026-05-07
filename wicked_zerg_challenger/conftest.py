# -*- coding: utf-8 -*-
"""Top-level conftest for the SC2 bot test suite.

The real ``sc2`` package (burnysc2) is hard to install in CI sandboxes because
its dependency ``mpyq`` requires legacy build tooling. The bot itself imports
``sc2`` at module load time, which causes ``ImportError`` during pytest's
collection phase for any test that touches manager modules.

This conftest installs a lightweight stub for the ``sc2`` namespace into
``sys.modules`` *before* any test module is imported. The stub only exposes the
symbols actually referenced by the bot/test code (``Point2``, ``Unit``,
``Units``, the *Id enums, ``Difficulty``, ``Race``, ``Result``, ``Bot``,
``Computer``, ``run_game``). When the real library is installed the stub is
not registered, so tests still exercise the real types.
"""

from __future__ import annotations

import os
import sys
import types
from enum import Enum
from importlib import util as _import_util

# Ensure protobuf uses the pure-python implementation - matches the historic
# wicked_zerg_challenger/tests/conftest.py behaviour.
os.environ.setdefault("PROTOCOL_BUFFERS_PYTHON_IMPLEMENTATION", "python")


def _install_sc2_stub() -> None:
    """Register a minimal in-memory ``sc2`` package when the real one is missing."""

    if _import_util.find_spec("sc2") is not None:
        return

    sc2 = types.ModuleType("sc2")
    sc2.__path__ = []  # mark as a package so submodule imports work

    # ── sc2.position.Point2 ────────────────────────────────────────────────
    position = types.ModuleType("sc2.position")

    class Point2(tuple):  # type: ignore[misc]
        """Minimal stand-in compatible with ``Point2((x, y))`` constructor."""

        def __new__(cls, value=(0.0, 0.0)):
            x, y = value
            obj = super().__new__(cls, (float(x), float(y)))
            return obj

        @property
        def x(self) -> float:
            return self[0]

        @property
        def y(self) -> float:
            return self[1]

        def distance_to(self, other) -> float:
            ox, oy = (other[0], other[1]) if hasattr(other, "__getitem__") else (
                other.x,
                other.y,
            )
            return ((self.x - ox) ** 2 + (self.y - oy) ** 2) ** 0.5

        def towards(self, other, distance: float = 1.0) -> "Point2":
            ox, oy = (other[0], other[1]) if hasattr(other, "__getitem__") else (
                other.x,
                other.y,
            )
            dx, dy = ox - self.x, oy - self.y
            d = (dx * dx + dy * dy) ** 0.5 or 1.0
            return Point2((self.x + dx * distance / d, self.y + dy * distance / d))

    position.Point2 = Point2

    # ── sc2.unit.Unit ──────────────────────────────────────────────────────
    unit_mod = types.ModuleType("sc2.unit")

    class Unit:  # noqa: D401 - stub
        """Placeholder for type annotations only."""

    unit_mod.Unit = Unit

    # ── sc2.units.Units ────────────────────────────────────────────────────
    units_mod = types.ModuleType("sc2.units")

    class Units(list):
        """List-compatible stand-in supporting the few helpers the bot uses."""

        def __init__(self, units=None, bot_object=None):
            super().__init__(units or [])
            self._bot_object = bot_object

        @property
        def amount(self) -> int:
            return len(self)

        @property
        def exists(self) -> bool:
            return len(self) > 0

        def closer_than(self, distance, position):
            ref = getattr(position, "position", position)
            return Units(
                [u for u in self if getattr(u, "distance_to", lambda *_: 0)(ref) < distance],
                self._bot_object,
            )

        def filter(self, func):
            return Units([u for u in self if func(u)], self._bot_object)

        def first(self):
            return self[0] if self else None

        def random(self):
            return self.first()

        def of_type(self, types_):  # pragma: no cover - rarely used in stub
            return self

    units_mod.Units = Units

    # ── sc2.ids.* ──────────────────────────────────────────────────────────
    ids_pkg = types.ModuleType("sc2.ids")
    ids_pkg.__path__ = []

    def _make_enum_module(modname: str, classname: str) -> types.ModuleType:
        m = types.ModuleType(modname)

        class _DynEnum:
            """Permissive enum: any attribute access yields a stable sentinel."""

            _members: dict = {}

            def __class_getitem__(cls, item):
                return cls._get(item)

            def __init__(self, name: str, value: int):
                self.name = name
                self.value = value

            def __repr__(self) -> str:  # pragma: no cover
                return f"<{classname}.{self.name}>"

            def __eq__(self, other) -> bool:
                return isinstance(other, _DynEnum) and self.name == other.name

            def __hash__(self) -> int:
                return hash((classname, self.name))

            @classmethod
            def _get(cls, name: str) -> "_DynEnum":
                if name not in cls._members:
                    cls._members[name] = cls(name, len(cls._members) + 1)
                return cls._members[name]

        class _Meta(type):
            def __getattr__(cls, name):  # type: ignore[override]
                return _DynEnum._get(name)

        Holder = _Meta(classname, (), {})
        setattr(m, classname, Holder)
        return m

    unit_typeid = _make_enum_module("sc2.ids.unit_typeid", "UnitTypeId")
    ability_id = _make_enum_module("sc2.ids.ability_id", "AbilityId")
    upgrade_id = _make_enum_module("sc2.ids.upgrade_id", "UpgradeId")
    buff_id = _make_enum_module("sc2.ids.buff_id", "BuffId")
    effect_id = _make_enum_module("sc2.ids.effect_id", "EffectId")

    # ── sc2.data ───────────────────────────────────────────────────────────
    data_mod = types.ModuleType("sc2.data")

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

    class Race(Enum):
        NoRace = 0
        Terran = 1
        Zerg = 2
        Protoss = 3
        Random = 4

    class Result(Enum):
        Victory = 1
        Defeat = 2
        Tie = 3
        Undecided = 4

    data_mod.Difficulty = Difficulty
    data_mod.Race = Race
    data_mod.Result = Result

    # ── sc2.player ─────────────────────────────────────────────────────────
    player_mod = types.ModuleType("sc2.player")

    class Bot:  # pragma: no cover - simple holder
        def __init__(self, race=None, ai=None, name: str = "Bot"):
            self.race = race
            self.ai = ai
            self.name = name

    class Computer:  # pragma: no cover - simple holder
        def __init__(self, race=None, difficulty=None, ai_build=None):
            self.race = race
            self.difficulty = difficulty
            self.ai_build = ai_build

    player_mod.Bot = Bot
    player_mod.Computer = Computer

    # ── sc2.main.run_game ──────────────────────────────────────────────────
    main_mod = types.ModuleType("sc2.main")

    def run_game(*args, **kwargs):  # pragma: no cover - never called in tests
        raise RuntimeError("sc2 stub: run_game is not available without the real library")

    main_mod.run_game = run_game

    # ── sc2.bot_ai ─────────────────────────────────────────────────────────
    bot_ai_mod = types.ModuleType("sc2.bot_ai")

    class BotAI:  # pragma: no cover - simple base
        pass

    bot_ai_mod.BotAI = BotAI

    # ── Register everything ────────────────────────────────────────────────
    modules = {
        "sc2": sc2,
        "sc2.position": position,
        "sc2.unit": unit_mod,
        "sc2.units": units_mod,
        "sc2.ids": ids_pkg,
        "sc2.ids.unit_typeid": unit_typeid,
        "sc2.ids.ability_id": ability_id,
        "sc2.ids.upgrade_id": upgrade_id,
        "sc2.ids.buff_id": buff_id,
        "sc2.ids.effect_id": effect_id,
        "sc2.data": data_mod,
        "sc2.player": player_mod,
        "sc2.main": main_mod,
        "sc2.bot_ai": bot_ai_mod,
    }
    for name, mod in modules.items():
        sys.modules.setdefault(name, mod)

    # Convenience attributes on the package itself.
    sc2.position = position
    sc2.unit = unit_mod
    sc2.units = units_mod
    sc2.ids = ids_pkg
    sc2.data = data_mod
    sc2.player = player_mod
    sc2.main = main_mod
    sc2.bot_ai = bot_ai_mod
    ids_pkg.unit_typeid = unit_typeid
    ids_pkg.ability_id = ability_id
    ids_pkg.upgrade_id = upgrade_id
    ids_pkg.buff_id = buff_id
    ids_pkg.effect_id = effect_id


_install_sc2_stub()
