# -*- coding: utf-8 -*-
"""Test configuration — runs before test collection.

Responsibilities:
1. Configure protobuf compatibility for the sc2 library (when installed).
2. Ensure the wicked_zerg_challenger package directory is on sys.path so
   each test can ``from <module> import ...`` directly.
3. When the real ``sc2`` library is not installed (CI / lint environments),
   register a permissive stub package so that source modules importing
   ``sc2.ids.unit_typeid.UnitTypeId`` etc. can still be imported. The stubs
   accept arbitrary attribute access (``UnitTypeId.OVERLORD``, etc.) which
   is sufficient for tests that mock around them.
"""

from __future__ import annotations

import os
import sys
import types
from pathlib import Path

# Fix protobuf compatibility with sc2 library (s2clientprotocol).
os.environ.setdefault("PROTOCOL_BUFFERS_PYTHON_IMPLEMENTATION", "python")

# Make the wicked_zerg_challenger package directory importable so that
# bare imports like ``from blackboard import GameStateBlackboard`` resolve.
_PKG_ROOT = Path(__file__).resolve().parent.parent
if str(_PKG_ROOT) not in sys.path:
    sys.path.insert(0, str(_PKG_ROOT))


def _install_sc2_stub() -> None:
    """Register a minimal stub for the ``sc2`` package when missing.

    The real sc2 library exposes a tree of modules (``sc2.ids.unit_typeid``,
    ``sc2.position`` …). Tests that rely on the production code paths need
    those names to import cleanly, but they don't need the real values —
    every test either mocks SC2 interactions or skips when the library is
    unavailable. The stub therefore returns a permissive sentinel for any
    attribute access.
    """

    try:
        import sc2  # noqa: F401  (real library present, nothing to do)
        return
    except Exception:
        pass

    class _StubMeta(type):
        def __getattr__(cls, name):  # type: ignore[override]
            value = type(name, (), {"name": name, "value": name, "__repr__": lambda self: name})
            setattr(cls, name, value)
            return value

    class _StubEnum(metaclass=_StubMeta):
        pass

    def _make_module(fullname: str) -> types.ModuleType:
        mod = types.ModuleType(fullname)
        sys.modules[fullname] = mod
        return mod

    sc2 = _make_module("sc2")

    # sc2.ids.* — enum-like classes
    ids_pkg = _make_module("sc2.ids")
    sc2.ids = ids_pkg  # type: ignore[attr-defined]

    for sub, attr in (
        ("unit_typeid", "UnitTypeId"),
        ("ability_id", "AbilityId"),
        ("upgrade_id", "UpgradeId"),
        ("buff_id", "BuffId"),
        ("effect_id", "EffectId"),
    ):
        m = _make_module(f"sc2.ids.{sub}")
        cls = type(attr, (_StubEnum,), {})
        setattr(m, attr, cls)
        setattr(ids_pkg, sub, m)

    # sc2.position
    pos_mod = _make_module("sc2.position")

    class Point2(tuple):  # noqa: D401  (minimal stub)
        def __new__(cls, xy=(0, 0)):
            return super().__new__(cls, xy)

        @property
        def x(self):
            return self[0] if len(self) > 0 else 0

        @property
        def y(self):
            return self[1] if len(self) > 1 else 0

        def distance_to(self, other):
            try:
                ox = other[0] if hasattr(other, "__getitem__") else getattr(other, "x", 0)
                oy = other[1] if hasattr(other, "__getitem__") else getattr(other, "y", 0)
            except Exception:
                ox, oy = 0, 0
            dx = self.x - ox
            dy = self.y - oy
            return (dx * dx + dy * dy) ** 0.5

        def distance_to_point2(self, other):
            return self.distance_to(other)

        def __sub__(self, other):
            try:
                return Point2((self.x - other[0], self.y - other[1]))
            except Exception:
                return Point2((self.x, self.y))

        def __add__(self, other):
            try:
                return Point2((self.x + other[0], self.y + other[1]))
            except Exception:
                return Point2((self.x, self.y))

    class Point3(Point2):
        pass

    pos_mod.Point2 = Point2
    pos_mod.Point3 = Point3
    sc2.position = pos_mod  # type: ignore[attr-defined]

    # Real Enums for sc2.data (so things like Race[name] and isinstance work)
    import enum

    Race = enum.Enum("Race", ["NoRace", "Terran", "Zerg", "Protoss", "Random"])
    Difficulty = enum.Enum(
        "Difficulty",
        [
            "VeryEasy", "Easy", "Medium", "MediumHard", "Hard", "Harder",
            "VeryHard", "CheatVision", "CheatMoney", "CheatInsane",
        ],
    )
    Result = enum.Enum("Result", ["Victory", "Defeat", "Tie", "Undecided"])

    # sc2.bot_ai / sc2.unit / sc2.units / sc2.data / sc2.constants / sc2.maps / sc2.main / sc2.player
    for name, attrs in (
        ("bot_ai", {"BotAI": type("BotAI", (), {})}),
        ("unit", {"Unit": type("Unit", (), {})}),
        ("units", {
            "Units": type(
                "Units",
                (list,),
                {
                    "__init__": lambda self, items=(), bot_object=None: list.__init__(
                        self, items
                    ),
                    "filter": lambda self, fn: type(self)(
                        [u for u in self if fn(u)], None
                    ),
                    "closer_than": lambda self, r, p: type(self)([], None),
                    "amount": property(lambda self: len(self)),
                },
            ),
        }),
        ("data", {
            "Race": Race,
            "Difficulty": Difficulty,
            "Result": Result,
        }),
        ("constants", {}),
        ("maps", {"get": staticmethod(lambda name: name)}),
        ("main", {"run_game": staticmethod(lambda *a, **kw: None)}),
        ("player", {
            "Bot": type("Bot", (), {}),
            "Computer": type("Computer", (), {}),
            "Human": type("Human", (), {}),
        }),
    ):
        m = _make_module(f"sc2.{name}")
        for k, v in attrs.items():
            setattr(m, k, v)
        setattr(sc2, name, m)


_install_sc2_stub()
