# -*- coding: utf-8 -*-
"""Test configuration - runs before test collection.

Provides a lightweight stub for the ``sc2`` (burnysc2) package when the
real library is not installed. The stub satisfies module-level imports
that production code and tests perform during collection, so the suite
can be collected and run in CI/dev environments without the C-extension
dependency (``mpyq`` wheels often fail on stripped-down images).

When the real ``sc2`` library *is* installed, it wins by being imported
first; the stub installer is a no-op in that case.
"""

import os
import sys
from types import ModuleType

# Fix protobuf compatibility with sc2 library (s2clientprotocol).
os.environ["PROTOCOL_BUFFERS_PYTHON_IMPLEMENTATION"] = "python"


def _install_sc2_stub() -> None:
    try:
        import sc2  # noqa: F401
        return
    except ImportError:
        pass

    class _AutoModule(ModuleType):
        """Module that fabricates attributes on demand as nested stubs."""

        def __getattr__(self, name):
            if name.startswith("__"):
                raise AttributeError(name)
            value = _AutoModule(f"{self.__name__}.{name}")
            sys.modules[value.__name__] = value
            setattr(self, name, value)
            return value

    class _IdMeta(type):
        """Metaclass that fabricates ID members on demand (e.g. ``UnitTypeId.DRONE``).

        Supports both attribute access (``UnitTypeId.DRONE``) and subscript
        access (``Race["Zerg"]``) so production code that uses either style
        keeps working against the stub.
        """

        _cache: dict = {}

        def __getattr__(cls, name):
            if name.startswith("__"):
                raise AttributeError(name)
            key = (cls.__name__, name)
            if key not in _IdMeta._cache:
                _IdMeta._cache[key] = cls(name)
            return _IdMeta._cache[key]

        def __getitem__(cls, name):
            return cls.__getattr__(name)

    class _IdBase(metaclass=_IdMeta):
        def __init__(self, name: str):
            self.name = name
            self.value = name

        def __repr__(self) -> str:
            return f"<{type(self).__name__}.{self.name}>"

        def __eq__(self, other) -> bool:
            return isinstance(other, type(self)) and self.name == other.name

        def __hash__(self) -> int:
            return hash((type(self).__name__, self.name))

    class UnitTypeId(_IdBase):
        pass

    class UpgradeId(_IdBase):
        pass

    class AbilityId(_IdBase):
        pass

    class BuffId(_IdBase):
        pass

    class EffectId(_IdBase):
        pass

    class Point2:
        def __init__(self, *args):
            if len(args) == 1 and hasattr(args[0], "__iter__"):
                args = tuple(args[0])
            self.x, self.y = (args + (0.0, 0.0))[:2]

        def __iter__(self):
            yield self.x
            yield self.y

        def __len__(self) -> int:
            return 2

        def __getitem__(self, idx):
            return (self.x, self.y)[idx]

        def __repr__(self) -> str:
            return f"Point2({self.x}, {self.y})"

        def __eq__(self, other) -> bool:
            if isinstance(other, Point2):
                return self.x == other.x and self.y == other.y
            if hasattr(other, "x") and hasattr(other, "y"):
                return self.x == other.x and self.y == other.y
            try:
                ox, oy = other
                return self.x == ox and self.y == oy
            except (TypeError, ValueError):
                return NotImplemented

        def __hash__(self) -> int:
            return hash((round(self.x, 6), round(self.y, 6)))

        def distance_to(self, other) -> float:
            ox, oy = (other.x, other.y) if hasattr(other, "x") else other
            return ((self.x - ox) ** 2 + (self.y - oy) ** 2) ** 0.5

    class Point3(Point2):
        def __init__(self, *args):
            super().__init__(*args)
            self.z = args[2] if len(args) >= 3 else 0.0

    class Race(_IdBase):
        pass

    class Difficulty(_IdBase):
        pass

    class Result(_IdBase):
        pass

    class Unit:
        pass

    class Units(list):
        # burnysc2 signature is ``Units(units, bot_object)``; accept and
        # ignore extra positional/keyword args so test code can construct
        # them without knowing about the bot.
        def __init__(self, units=(), *args, **kwargs):
            super().__init__(units)

        @property
        def amount(self):
            return len(self)

        @property
        def ready(self):
            return self

        @property
        def exists(self):
            return len(self) > 0

    class BotAI:
        pass

    sc2 = _AutoModule("sc2")
    sys.modules["sc2"] = sc2

    ids = _AutoModule("sc2.ids")
    sys.modules["sc2.ids"] = ids

    for name, cls in {
        "unit_typeid": UnitTypeId,
        "upgrade_id": UpgradeId,
        "ability_id": AbilityId,
        "buff_id": BuffId,
        "effect_id": EffectId,
    }.items():
        mod = ModuleType(f"sc2.ids.{name}")
        attr = "".join(part.capitalize() for part in name.split("_"))
        # Special-case the canonical class names that match the imports.
        canonical = {
            "unit_typeid": "UnitTypeId",
            "upgrade_id": "UpgradeId",
            "ability_id": "AbilityId",
            "buff_id": "BuffId",
            "effect_id": "EffectId",
        }[name]
        setattr(mod, canonical, cls)
        sys.modules[mod.__name__] = mod
        setattr(ids, name, mod)

    position = ModuleType("sc2.position")
    position.Point2 = Point2
    position.Point3 = Point3
    sys.modules["sc2.position"] = position

    unit = ModuleType("sc2.unit")
    unit.Unit = Unit
    sys.modules["sc2.unit"] = unit

    units = ModuleType("sc2.units")
    units.Units = Units
    sys.modules["sc2.units"] = units

    bot_ai = ModuleType("sc2.bot_ai")
    bot_ai.BotAI = BotAI
    sys.modules["sc2.bot_ai"] = bot_ai

    data = ModuleType("sc2.data")
    data.Race = Race
    data.Difficulty = Difficulty
    data.Result = Result
    sys.modules["sc2.data"] = data

    main = ModuleType("sc2.main")
    main.run_game = lambda *a, **k: None
    sys.modules["sc2.main"] = main

    player = ModuleType("sc2.player")
    player.Bot = type("Bot", (), {})
    player.Computer = type("Computer", (), {})
    sys.modules["sc2.player"] = player

    maps = ModuleType("sc2.maps")
    maps.get = lambda name: name
    sys.modules["sc2.maps"] = maps


_install_sc2_stub()
