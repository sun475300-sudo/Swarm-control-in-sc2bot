# -*- coding: utf-8 -*-
"""Test configuration - runs before test collection.

When the upstream ``sc2`` (a.k.a. burnysc2) package isn't installed we
synthesise a minimal stub tree so the test modules that ``import`` from
it can still be collected. The stubs come from ``utils.sc2_compat`` so
they behave consistently with the production fallbacks.
"""

import os
import sys
import types

# Fix protobuf compatibility with sc2 library (s2clientprotocol)
os.environ["PROTOCOL_BUFFERS_PYTHON_IMPLEMENTATION"] = "python"

# Ensure the wicked_zerg_challenger package is importable
_here = os.path.dirname(os.path.abspath(__file__))
_parent = os.path.dirname(_here)
if _parent not in sys.path:
    sys.path.insert(0, _parent)


def _inject_sc2_stubs() -> None:
    """Register a fake ``sc2`` module tree built on the local compat shim."""
    try:
        import sc2  # noqa: F401

        return  # real package available; nothing to do
    except ImportError:
        pass

    try:
        from utils.sc2_compat import (
            AbilityId,
            BotAI,
            BuffId,
            Point2,
            Unit,
            Units,
            UnitTypeId,
            UpgradeId,
        )
    except ImportError:
        return  # nothing we can do

    sc2_pkg = types.ModuleType("sc2")
    sc2_pkg.__path__ = []  # mark as package so submodule imports work
    sys.modules["sc2"] = sc2_pkg

    ids_pkg = types.ModuleType("sc2.ids")
    ids_pkg.__path__ = []
    sys.modules["sc2.ids"] = ids_pkg
    sc2_pkg.ids = ids_pkg

    def _register(name, **attrs):
        mod = types.ModuleType(name)
        for key, value in attrs.items():
            setattr(mod, key, value)
        sys.modules[name] = mod
        return mod

    class _EnumMeta(type):
        """Lookup-friendly metaclass: ``Race.Zerg`` and ``Race['Zerg']`` work."""

        def __getattr__(cls, name):
            if name.startswith("_"):
                raise AttributeError(name)
            token = cls._new_token(name)
            setattr(cls, name, token)
            return token

        def __getitem__(cls, name):
            return getattr(cls, name)

        def __iter__(cls):
            return iter([])

    class _EnumBase(metaclass=_EnumMeta):
        @classmethod
        def _new_token(cls, name):
            token = cls.__new__(cls)
            token._name = name
            return token

        def __init__(self, *args, **kwargs):
            pass

        @property
        def name(self):
            return self._name

        @property
        def value(self):
            return self._name

        def __repr__(self):
            return f"{type(self).__name__}.{self._name}"

        def __eq__(self, other):
            return (
                isinstance(other, _EnumBase)
                and type(self) is type(other)
                and self._name == other._name
            )

        def __hash__(self):
            return hash((type(self).__name__, self._name))

    class Race(_EnumBase):
        pass

    class Difficulty(_EnumBase):
        pass

    class Result(_EnumBase):
        pass

    _register("sc2.bot_ai", BotAI=BotAI)
    _register("sc2.ids.unit_typeid", UnitTypeId=UnitTypeId)
    _register("sc2.ids.ability_id", AbilityId=AbilityId)
    _register("sc2.ids.upgrade_id", UpgradeId=UpgradeId)
    _register("sc2.ids.buff_id", BuffId=BuffId)
    _register("sc2.position", Point2=Point2, Point3=Point2)
    _register("sc2.unit", Unit=Unit)
    _register("sc2.units", Units=Units)
    _register("sc2.data", Race=Race, Difficulty=Difficulty, Result=Result)

    def _get_map(name):  # pragma: no cover - test-only shim
        return types.SimpleNamespace(name=name)

    maps_mod = _register("sc2.maps", get=_get_map)
    sc2_pkg.maps = maps_mod

    async def _run_game(*args, **kwargs):  # pragma: no cover - test-only shim
        return None

    _register("sc2.main", run_game=_run_game)
    _register(
        "sc2.player",
        Bot=type("Bot", (), {"__init__": lambda self, *a, **k: None}),
        Computer=type("Computer", (), {"__init__": lambda self, *a, **k: None}),
        Human=type("Human", (), {"__init__": lambda self, *a, **k: None}),
    )


_inject_sc2_stubs()
