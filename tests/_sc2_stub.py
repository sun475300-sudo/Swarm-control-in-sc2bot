"""Lightweight ``sc2`` stub for offline test environments.

The real `python-sc2` / `burnysc2` library has heavy native dependencies
(e.g. ``mpyq``) that fail to build in CI sandboxes without a C toolchain.
Most unit tests in this repo only need symbolic enum members
(``UnitTypeId.QUEEN``, ``UpgradeId.ZERGLINGMOVEMENTSPEED``) and a tiny
``Point2`` value class to import the modules under test. We register a
minimum stub in ``sys.modules`` so collection succeeds when sc2 isn't
installed.

Importing this module is idempotent and a no-op when the real ``sc2``
package is already importable.
"""

from __future__ import annotations

import sys
import types
from typing import Any


def _module(name: str) -> types.ModuleType:
    mod = types.ModuleType(name)
    sys.modules[name] = mod
    return mod


class _AutoEnum:
    """Attribute-on-access enum: every uppercase attribute is unique-by-name.

    Mimics ``enum.Enum`` access patterns just enough for tests:
        UnitTypeId.QUEEN  ==  UnitTypeId.QUEEN  (cached identity)
        UnitTypeId.QUEEN  !=  UnitTypeId.DRONE
    """

    _members: dict[str, "_AutoEnum"]

    def __init__(self, name: str) -> None:
        self.name = name
        self.value = name

    def __repr__(self) -> str:  # pragma: no cover - debug aid
        return f"<{type(self).__name__}.{self.name}>"

    def __eq__(self, other: object) -> bool:
        return isinstance(other, _AutoEnum) and other.name == self.name and type(other) is type(self)

    def __hash__(self) -> int:
        return hash((type(self).__name__, self.name))


def _make_enum_class(cls_name: str) -> type:
    cache: dict[str, Any] = {}

    class _Meta(type):
        def __getattr__(cls, item: str) -> Any:
            if item.startswith("_"):
                raise AttributeError(item)
            if item not in cache:
                cache[item] = cls(item)
            return cache[item]

        def __getitem__(cls, item: str) -> Any:
            # Mirror ``Enum[name]`` lookups used by some serialization paths.
            if not isinstance(item, str) or item.startswith("_"):
                raise KeyError(item)
            if item not in cache:
                cache[item] = cls(item)
            return cache[item]

        def __iter__(cls) -> Any:
            return iter(list(cache.values()))

    return _Meta(cls_name, (_AutoEnum,), {"_members": cache})


class Point2(tuple):
    """Minimal 2-tuple-like point used for position math in tests."""

    def __new__(cls, value: Any = (0.0, 0.0)) -> "Point2":
        if isinstance(value, (tuple, list)):
            x, y = float(value[0]), float(value[1])
        else:
            raise TypeError(f"Point2 expects iterable of len 2, got {value!r}")
        return super().__new__(cls, (x, y))

    @property
    def x(self) -> float:
        return self[0]

    @property
    def y(self) -> float:
        return self[1]

    def distance_to(self, other: Any) -> float:
        ox, oy = (other[0], other[1]) if isinstance(other, (tuple, list)) else (other.x, other.y)
        return ((self.x - ox) ** 2 + (self.y - oy) ** 2) ** 0.5


def install() -> None:
    """Register the stub in ``sys.modules`` if sc2 isn't already installed."""
    try:
        import sc2  # noqa: F401  - real package wins
        return
    except Exception:
        pass

    sc2 = _module("sc2")
    ids = _module("sc2.ids")
    unit_typeid_mod = _module("sc2.ids.unit_typeid")
    upgrade_id_mod = _module("sc2.ids.upgrade_id")
    ability_id_mod = _module("sc2.ids.ability_id")
    buff_id_mod = _module("sc2.ids.buff_id")
    position_mod = _module("sc2.position")
    data_mod = _module("sc2.data")
    bot_ai_mod = _module("sc2.bot_ai")
    unit_mod = _module("sc2.unit")
    units_mod = _module("sc2.units")
    game_info_mod = _module("sc2.game_info")
    main_mod = _module("sc2.main")
    player_mod = _module("sc2.player")
    maps_mod = _module("sc2.maps")

    sc2.ids = ids  # type: ignore[attr-defined]

    unit_typeid_mod.UnitTypeId = _make_enum_class("UnitTypeId")  # type: ignore[attr-defined]
    upgrade_id_mod.UpgradeId = _make_enum_class("UpgradeId")  # type: ignore[attr-defined]
    ability_id_mod.AbilityId = _make_enum_class("AbilityId")  # type: ignore[attr-defined]
    buff_id_mod.BuffId = _make_enum_class("BuffId")  # type: ignore[attr-defined]

    position_mod.Point2 = Point2  # type: ignore[attr-defined]
    position_mod.Point3 = Point2  # type: ignore[attr-defined]

    data_mod.Race = _make_enum_class("Race")  # type: ignore[attr-defined]
    data_mod.Difficulty = _make_enum_class("Difficulty")  # type: ignore[attr-defined]
    data_mod.Result = _make_enum_class("Result")  # type: ignore[attr-defined]
    data_mod.AIBuild = _make_enum_class("AIBuild")  # type: ignore[attr-defined]

    class _BotAI:
        def __init__(self, *a: Any, **kw: Any) -> None: ...

    bot_ai_mod.BotAI = _BotAI  # type: ignore[attr-defined]

    class _Unit:
        def __init__(self, *a: Any, **kw: Any) -> None: ...

    unit_mod.Unit = _Unit  # type: ignore[attr-defined]

    class _Units(list):  # type: ignore[type-arg]
        # The real ``sc2.units.Units`` accepts ``Units(units, bot_object=None)``;
        # the second arg is the host bot reference. The stub ignores it but
        # preserves the constructor signature so production code paths import
        # cleanly.
        def __init__(self, units: Any = (), bot_object: Any = None) -> None:
            super().__init__(units)
            self.bot_object = bot_object

    units_mod.Units = _Units  # type: ignore[attr-defined]

    class _GameInfo:
        def __init__(self, *a: Any, **kw: Any) -> None: ...

    game_info_mod.GameInfo = _GameInfo  # type: ignore[attr-defined]

    def _run_game(*a: Any, **kw: Any) -> None:
        raise RuntimeError("sc2 stub: run_game not available offline")

    main_mod.run_game = _run_game  # type: ignore[attr-defined]

    class _Bot:
        def __init__(self, *a: Any, **kw: Any) -> None: ...

    class _Computer:
        def __init__(self, *a: Any, **kw: Any) -> None: ...

    player_mod.Bot = _Bot  # type: ignore[attr-defined]
    player_mod.Computer = _Computer  # type: ignore[attr-defined]

    def _get(name: str) -> str:
        return name

    maps_mod.get = _get  # type: ignore[attr-defined]
