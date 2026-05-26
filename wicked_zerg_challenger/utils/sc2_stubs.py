"""Stub classes used when the optional ``sc2`` package isn't installed.

These classes auto-create attributes on access, so production code that
references enum values like ``UnitTypeId.SPINECRAWLER`` can still be imported
and unit-tested without a live SC2 install. The returned values are plain
strings so equality/hashing/printing still work.
"""

from __future__ import annotations


class _StubEnumValue:
    """A non-string, name-only enum value used by the auto-enum stubs.

    Implements equality/hashing/repr based on (class, name) so values from
    different stub enums (UnitTypeId.X vs AbilityId.X) don't collide and so
    ``isinstance(value, str)`` returns ``False`` — important for code that
    branches between enum and string inputs (e.g. ``"UPGRADE_NAME"``).
    """

    __slots__ = ("_cls_name", "name")

    def __init__(self, cls_name: str, name: str) -> None:
        self._cls_name = cls_name
        self.name = name

    def __eq__(self, other):  # noqa: D401
        if isinstance(other, _StubEnumValue):
            return self._cls_name == other._cls_name and self.name == other.name
        return False

    def __hash__(self) -> int:
        return hash((self._cls_name, self.name))

    def __repr__(self) -> str:
        return f"{self._cls_name}.{self.name}"

    def __str__(self) -> str:
        return self.name


class _AutoEnumMeta(type):
    """Metaclass that creates ``_StubEnumValue`` members on attribute access."""

    def __getattr__(cls, name):  # noqa: D401 - dunder-style override
        if name.startswith("_"):
            raise AttributeError(name)
        value = _StubEnumValue(cls.__name__, name)
        setattr(cls, name, value)
        return value


class UnitTypeId(metaclass=_AutoEnumMeta):
    """Stand-in for ``sc2.ids.unit_typeid.UnitTypeId``."""


class AbilityId(metaclass=_AutoEnumMeta):
    """Stand-in for ``sc2.ids.ability_id.AbilityId``."""


class UpgradeId(metaclass=_AutoEnumMeta):
    """Stand-in for ``sc2.ids.upgrade_id.UpgradeId``."""


class BuffId(metaclass=_AutoEnumMeta):
    """Stand-in for ``sc2.ids.buff_id.BuffId``."""


class EffectId(metaclass=_AutoEnumMeta):
    """Stand-in for ``sc2.ids.effect_id.EffectId``."""


class BotAI:
    """Minimal stand-in for ``sc2.bot_ai.BotAI`` allowing subclassing in tests."""


class Point2:
    """Lightweight stand-in for ``sc2.position.Point2``.

    Accepts either ``Point2(x, y)`` or ``Point2((x, y))`` and exposes ``.x`` /
    ``.y`` plus a ``distance_to`` method, which is enough for most non-game
    code paths that just need to compute or compare positions.
    """

    __slots__ = ("x", "y")

    def __init__(self, *args):
        if len(args) == 1:
            try:
                x, y = args[0]
            except (TypeError, ValueError):
                x, y = 0.0, 0.0
        elif len(args) == 2:
            x, y = args
        else:
            x, y = 0.0, 0.0
        self.x = float(x)
        self.y = float(y)

    def distance_to(self, other):
        pos = getattr(other, "position", other)
        ox = getattr(pos, "x", 0.0)
        oy = getattr(pos, "y", 0.0)
        return ((self.x - ox) ** 2 + (self.y - oy) ** 2) ** 0.5

    def __iter__(self):
        return iter((self.x, self.y))

    def __repr__(self) -> str:
        return f"Point2({self.x}, {self.y})"


__all__ = [
    "UnitTypeId",
    "AbilityId",
    "UpgradeId",
    "BuffId",
    "EffectId",
    "BotAI",
    "Point2",
]
