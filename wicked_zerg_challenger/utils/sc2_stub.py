"""Shared sc2-library stubs for environments where the sc2 package is absent.

Several modules need to keep importing and exposing sensible fallbacks for
``UnitTypeId``, ``AbilityId``, ``UpgradeId``, and ``Point2`` when running
tests or developer tooling without the sc2 package installed. Centralising
the stub here removes the previous per-module duplication and the
inconsistencies that came with it (some stubs had hand-listed members and
were missing common ones like ``MARINE``/``SPINECRAWLER``; some returned
plain ``str`` sentinels that collided with type checks).

Usage::

    try:
        from sc2.ids.unit_typeid import UnitTypeId
        from sc2.ids.ability_id import AbilityId
        from sc2.position import Point2
    except ImportError:
        from utils.sc2_stub import UnitTypeId, AbilityId, Point2
"""

from __future__ import annotations

from typing import Dict


class IdSentinel:
    """Hashable, equality-by-name stand-in for an sc2 enum member.

    Distinct from ``str`` so callers that do ``isinstance(value, str)`` to
    distinguish enum-typed unit IDs from raw upgrade-name strings (see
    ``build_order_system._infer_zvt_action``) still work correctly under
    stub mode.
    """

    __slots__ = ("_name",)

    def __init__(self, name: str):
        self._name = name

    def __repr__(self) -> str:  # pragma: no cover - debug aid
        return f"<IdStub:{self._name}>"

    def __eq__(self, other) -> bool:
        return isinstance(other, IdSentinel) and self._name == other._name

    def __hash__(self) -> int:
        return hash(("IdSentinel", self._name))

    @property
    def name(self) -> str:
        return self._name


class IdStub:
    """sc2 enum stand-in that yields a cached ``IdSentinel`` for any attribute.

    ``__bool__`` returns ``True`` so guards like ``if UnitTypeId:`` proceed
    in stub mode (a few modules use this gate to short-circuit when the
    real sc2 package isn't available — under the stub we want the rest of
    the function to run normally).
    """

    def __init__(self) -> None:
        self._cache: Dict[str, IdSentinel] = {}

    def __getattr__(self, name: str) -> IdSentinel:  # pragma: no cover - test/dev only
        if name.startswith("_"):
            raise AttributeError(name)
        sentinel = self._cache.get(name)
        if sentinel is None:
            sentinel = IdSentinel(name)
            self._cache[name] = sentinel
        return sentinel

    def __bool__(self) -> bool:
        return True


class _Point2(tuple):
    """Tuple-backed ``Point2`` stub with ``.x`` / ``.y`` accessors."""

    def __new__(cls, xy):
        return super().__new__(cls, xy)

    @property
    def x(self):
        return self[0]

    @property
    def y(self):
        return self[1]


UnitTypeId = IdStub()
AbilityId = IdStub()
UpgradeId = IdStub()
Point2 = _Point2
