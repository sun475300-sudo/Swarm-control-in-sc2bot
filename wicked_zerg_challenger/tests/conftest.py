# -*- coding: utf-8 -*-
"""Test configuration - runs before test collection.

Installs a permissive sc2 stub so tests that import `from sc2.*` can collect
in environments where the real `sc2` library is not installed (CI, sandboxes).
Tests that need actual SC2 behavior should still skip themselves with a
`pytest.importorskip("sc2")` or explicit guard — this stub only unblocks
module-level imports.
"""

from __future__ import annotations

import importlib
import os
import sys
import types

# Fix protobuf compatibility with sc2 library (s2clientprotocol)
os.environ.setdefault("PROTOCOL_BUFFERS_PYTHON_IMPLEMENTATION", "python")


def _install_sc2_stub() -> None:
    """Register a minimal `sc2` namespace if the real package is missing."""
    try:
        importlib.import_module("sc2")
        return  # real sc2 available — do nothing
    except ImportError:
        pass

    class _StubId:
        """Hashable sentinel that mimics an enum member (UnitTypeId.X etc)."""

        __slots__ = ("name", "value")

        def __init__(self, name: str):
            self.name = name
            self.value = name

        def __repr__(self):
            return f"_StubId({self.name!r})"

        def __hash__(self):
            return hash(("_StubId", self.name))

        def __eq__(self, other):
            return isinstance(other, _StubId) and self.name == other.name

    class _Permissive:
        """Attribute & item access returns a hashable sentinel (unique per name)."""

        _cache: dict = {}

        def __getattr__(self, name):  # type: ignore[override]
            obj = self._cache.get(name)
            if obj is None:
                obj = _StubId(name)
                self._cache[name] = obj
            return obj

        def __getitem__(self, key):
            return self.__getattr__(str(key))

        def __call__(self, *a, **kw):
            return self

    def _make_module(fullname: str) -> types.ModuleType:
        mod = types.ModuleType(fullname)
        mod.__path__ = []  # mark as package so submodules can attach
        return mod

    sc2 = _make_module("sc2")
    sc2_ids = _make_module("sc2.ids")
    sc2_data = _make_module("sc2.data")
    sc2_position = _make_module("sc2.position")
    sc2_bot_ai = _make_module("sc2.bot_ai")
    sc2_unit = _make_module("sc2.unit")
    sc2_units = _make_module("sc2.units")
    sc2_maps = _make_module("sc2.maps")
    sc2_main = _make_module("sc2.main")
    sc2_player = _make_module("sc2.player")
    sc2_ids_unit = _make_module("sc2.ids.unit_typeid")
    sc2_ids_upgrade = _make_module("sc2.ids.upgrade_id")
    sc2_ids_ability = _make_module("sc2.ids.ability_id")
    sc2_ids_buff = _make_module("sc2.ids.buff_id")
    sc2_ids_effect = _make_module("sc2.ids.effect_id")

    # IDs use permissive attribute lookup so UnitTypeId.OVERLORD etc work.
    sc2_ids_unit.UnitTypeId = _Permissive()
    sc2_ids_upgrade.UpgradeId = _Permissive()
    sc2_ids_ability.AbilityId = _Permissive()
    sc2_ids_buff.BuffId = _Permissive()
    sc2_ids_effect.EffectId = _Permissive()

    # Data: Difficulty / Race
    sc2_data.Difficulty = _Permissive()
    sc2_data.Race = _Permissive()
    sc2_data.AIBuild = _Permissive()
    sc2_data.Result = _Permissive()

    class _Point2:
        def __init__(self, *a, **kw):
            # Accept Point2(x, y), Point2((x, y)), Point2([x, y]), Point2(other_point)
            if not a:
                self.x = 0.0
                self.y = 0.0
            elif len(a) >= 2:
                self.x = float(a[0])
                self.y = float(a[1])
            else:
                arg = a[0]
                if hasattr(arg, "x") and hasattr(arg, "y"):
                    self.x = float(arg.x)
                    self.y = float(arg.y)
                else:
                    try:
                        seq = list(arg)
                        self.x = float(seq[0]) if len(seq) > 0 else 0.0
                        self.y = float(seq[1]) if len(seq) > 1 else 0.0
                    except (TypeError, ValueError):
                        self.x = 0.0
                        self.y = 0.0

        def distance_to(self, other):
            ox = getattr(other, "x", 0.0)
            oy = getattr(other, "y", 0.0)
            return ((self.x - ox) ** 2 + (self.y - oy) ** 2) ** 0.5

        def towards(self, other, distance=1.0):
            return self

        def __iter__(self):
            yield self.x
            yield self.y

        def __getitem__(self, idx):
            return (self.x, self.y)[idx]

        def __eq__(self, other):
            return (
                getattr(other, "x", None) == self.x
                and getattr(other, "y", None) == self.y
            )

        def __hash__(self):
            return hash((self.x, self.y))

    class _Point3(_Point2):
        def __init__(self, *a, **kw):
            super().__init__(*a, **kw)
            self.z = float(a[2]) if len(a) > 2 else 0.0

    sc2_position.Point2 = _Point2
    sc2_position.Point3 = _Point3

    class _BotAI:
        def __init__(self, *a, **kw):
            pass

    sc2_bot_ai.BotAI = _BotAI

    class _Unit:
        def __init__(self, *a, **kw):
            pass

    sc2_unit.Unit = _Unit

    class _Units(list):
        def __init__(self, *a, **kw):
            super().__init__()

    sc2_units.Units = _Units

    # sc2.maps.get(map_name) is sometimes called at import time
    sc2_maps.get = lambda name: name

    # sc2.player / sc2.main minimal stubs
    class _Computer:
        def __init__(self, *a, **kw):
            pass

    class _Bot:
        def __init__(self, *a, **kw):
            pass

    sc2_player.Computer = _Computer
    sc2_player.Bot = _Bot
    sc2_main.run_game = lambda *a, **kw: None

    # Wire up the package tree
    sc2.ids = sc2_ids
    sc2.data = sc2_data
    sc2.position = sc2_position
    sc2.bot_ai = sc2_bot_ai
    sc2.unit = sc2_unit
    sc2.units = sc2_units
    sc2.maps = sc2_maps
    sc2.main = sc2_main
    sc2.player = sc2_player
    sc2_ids.unit_typeid = sc2_ids_unit
    sc2_ids.upgrade_id = sc2_ids_upgrade
    sc2_ids.ability_id = sc2_ids_ability
    sc2_ids.buff_id = sc2_ids_buff
    sc2_ids.effect_id = sc2_ids_effect

    for mod in (
        sc2,
        sc2_ids,
        sc2_data,
        sc2_position,
        sc2_bot_ai,
        sc2_unit,
        sc2_units,
        sc2_maps,
        sc2_main,
        sc2_player,
        sc2_ids_unit,
        sc2_ids_upgrade,
        sc2_ids_ability,
        sc2_ids_buff,
        sc2_ids_effect,
    ):
        sys.modules[mod.__name__] = mod


_install_sc2_stub()
