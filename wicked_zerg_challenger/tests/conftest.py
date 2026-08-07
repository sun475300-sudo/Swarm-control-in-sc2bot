# -*- coding: utf-8 -*-
"""Test configuration - runs before test collection.

* Forces the pure-Python protobuf implementation for compatibility with
  s2clientprotocol when sc2 is installed.
* When the optional `sc2`/`burnysc2` package is NOT installed, registers a
  minimal fake `sc2.*` module tree in `sys.modules` so that both production
  source files and the tests themselves resolve the *same* stub classes.
  Without this both sides build their own ad-hoc stubs and equality checks
  silently fail (e.g. `Difficulty.Easy` from the test never equals the
  ladder entry inside `difficulty_progression.py`).
"""

import os
import sys
import types
from enum import Enum

os.environ["PROTOCOL_BUFFERS_PYTHON_IMPLEMENTATION"] = "python"

try:  # noqa: SIM105 - we *want* the explicit branching here
    import sc2  # type: ignore  # noqa: F401
except ImportError:
    # Make the project root importable so `utils.sc2_compat` resolves
    _here = os.path.dirname(os.path.abspath(__file__))
    _project_root = os.path.abspath(os.path.join(_here, ".."))
    if _project_root not in sys.path:
        sys.path.insert(0, _project_root)

    from utils import sc2_compat as _compat  # type: ignore

    # ---- sc2.data --------------------------------------------------------
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

    sc2_pkg = types.ModuleType("sc2")
    sc2_pkg.__path__ = []  # mark as a package so submodule imports work
    sc2_data = types.ModuleType("sc2.data")
    sc2_data.Difficulty = Difficulty
    sc2_data.Race = Race
    sc2_pkg.data = sc2_data

    # ---- sc2.position ----------------------------------------------------
    sc2_position = types.ModuleType("sc2.position")
    sc2_position.Point2 = _compat.Point2
    sc2_position.Point3 = _compat.Point3
    sc2_pkg.position = sc2_position

    # ---- sc2.unit / sc2.units --------------------------------------------
    sc2_unit = types.ModuleType("sc2.unit")
    sc2_unit.Unit = _compat.Unit
    sc2_pkg.unit = sc2_unit

    sc2_units = types.ModuleType("sc2.units")

    class _UnitsList(list):
        """Minimal Units stub with the helpers tests typically need.

        The real `sc2.units.Units` constructor takes (iterable, bot_object).
        We accept the second argument and ignore it so production code that
        does `Units([], None)` works against the stub without a TypeError.
        """

        def __init__(self, iterable=(), bot=None):
            super().__init__(iterable)
            self._bot = bot

        def closer_than(self, distance, position):
            return _UnitsList(
                u for u in self if getattr(u, "position", None) is not None
            )

        def closest_to(self, position):
            return self[0] if self else None

        def furthest_to(self, position):
            return self[-1] if self else None

        def filter(self, predicate):
            return _UnitsList(u for u in self if predicate(u))

    sc2_units.Units = _UnitsList
    sc2_pkg.units = sc2_units

    # ---- sc2.bot_ai ------------------------------------------------------
    sc2_bot_ai = types.ModuleType("sc2.bot_ai")
    sc2_bot_ai.BotAI = _compat.BotAI
    sc2_pkg.bot_ai = sc2_bot_ai

    # ---- sc2.ids.* -------------------------------------------------------
    sc2_ids = types.ModuleType("sc2.ids")
    sc2_ids.__path__ = []
    sc2_pkg.ids = sc2_ids

    for _modname, _attr_name, _attr in (
        ("unit_typeid", "UnitTypeId", _compat.UnitTypeId),
        ("ability_id", "AbilityId", _compat.AbilityId),
        ("upgrade_id", "UpgradeId", _compat.UpgradeId),
        ("buff_id", "BuffId", _compat.BuffId),
        ("effect_id", "EffectId", _compat.EffectId),
    ):
        _m = types.ModuleType(f"sc2.ids.{_modname}")
        setattr(_m, _attr_name, _attr)
        setattr(sc2_ids, _modname, _m)
        sys.modules[f"sc2.ids.{_modname}"] = _m

    sys.modules["sc2"] = sc2_pkg
    sys.modules["sc2.data"] = sc2_data
    sys.modules["sc2.position"] = sc2_position
    sys.modules["sc2.unit"] = sc2_unit
    sys.modules["sc2.units"] = sc2_units
    sys.modules["sc2.bot_ai"] = sc2_bot_ai
    sys.modules["sc2.ids"] = sc2_ids
