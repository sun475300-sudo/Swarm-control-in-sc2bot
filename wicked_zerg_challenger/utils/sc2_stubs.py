"""Lenient stubs for python-sc2 imports.

Many bot modules use ``try: from sc2... import X / except ImportError:
class X: pass`` to stay importable in environments without python-sc2 (e.g.
CI without burnysc2, lint tooling). The naive ``class UnitTypeId: pass``
fallback breaks at module-load time as soon as a default value references
an enum member, e.g. ``def f(self, x: UnitTypeId = UnitTypeId.OVERLORD)``.

This module exposes ``get_sc2_imports()`` which returns the real
python-sc2 classes when available, and otherwise returns lenient stubs
whose attribute lookups never raise ``AttributeError`` — every access
yields a sentinel instance with a ``.name`` attribute set to the lookup
key. That's enough to keep modules importable for tests/lint while
preserving real behaviour at runtime when the library is installed.

Usage::

    from utils.sc2_stubs import get_sc2_imports

    BotAI, UnitTypeId, AbilityId, UpgradeId, Point2, Unit = get_sc2_imports()
"""

from __future__ import annotations

import logging
from typing import Tuple, Type

_logger = logging.getLogger(__name__)
_warned_once = False


class _LenientStubMeta(type):
    """Metaclass that turns any attribute lookup into a sentinel.

    The sentinel is an instance of the stub class with ``.name`` set to
    the looked-up key, mirroring the surface area of python-sc2 enums
    enough for module import to succeed.
    """

    def __getattr__(cls, name: str):  # noqa: D401 - simple proxy
        sentinel = object.__new__(cls)
        object.__setattr__(sentinel, "name", name)
        object.__setattr__(sentinel, "value", name)
        return sentinel


class _StubBotAI:
    """Placeholder for ``sc2.bot_ai.BotAI`` when python-sc2 is missing."""


class _StubPoint2:
    """Placeholder for ``sc2.position.Point2`` when python-sc2 is missing."""


class _StubUnit:
    """Placeholder for ``sc2.unit.Unit`` when python-sc2 is missing."""


class _StubUnitTypeId(metaclass=_LenientStubMeta):
    """Lenient stub for ``sc2.ids.unit_typeid.UnitTypeId``."""


class _StubAbilityId(metaclass=_LenientStubMeta):
    """Lenient stub for ``sc2.ids.ability_id.AbilityId``."""


class _StubUpgradeId(metaclass=_LenientStubMeta):
    """Lenient stub for ``sc2.ids.upgrade_id.UpgradeId``."""


def _emit_missing_warning_once() -> None:
    global _warned_once
    if _warned_once:
        return
    _warned_once = True
    _logger.warning(
        "python-sc2 not available — bot modules will use lenient stubs. "
        "Install 'burnysc2' (and 's2clientprotocol --no-deps') for full "
        "behaviour."
    )


def get_sc2_imports() -> Tuple[Type, Type, Type, Type, Type, Type]:
    """Return ``(BotAI, UnitTypeId, AbilityId, UpgradeId, Point2, Unit)``.

    Falls back to lenient stubs when python-sc2 cannot be imported.
    """
    try:
        from sc2.bot_ai import BotAI as _BotAI
        from sc2.ids.ability_id import AbilityId as _AbilityId
        from sc2.ids.unit_typeid import UnitTypeId as _UnitTypeId
        from sc2.ids.upgrade_id import UpgradeId as _UpgradeId
        from sc2.position import Point2 as _Point2
        from sc2.unit import Unit as _Unit

        return _BotAI, _UnitTypeId, _AbilityId, _UpgradeId, _Point2, _Unit
    except ImportError:
        _emit_missing_warning_once()
        return (
            _StubBotAI,
            _StubUnitTypeId,
            _StubAbilityId,
            _StubUpgradeId,
            _StubPoint2,
            _StubUnit,
        )


__all__ = ["get_sc2_imports"]
