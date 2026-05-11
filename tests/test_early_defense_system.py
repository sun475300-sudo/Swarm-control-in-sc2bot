"""Regression coverage for wicked_zerg_challenger.early_defense_system helpers.

The proxy-rush response picks the closest proxy structure via
``min(targets, key=lambda s: self._distance_to_main(s))``. If ``_distance_to_main``
silently returns the 999.0 sentinel because its fallback path tries to call
``Point2.distance_to(Unit)`` (which the burnysc2 API rejects), every proxy
target ties for last place and the worker pull picks the wrong building. This
file pins the corrected behaviour with pure-Python doubles so the regression
is visible without a running SC2 client.
"""
from __future__ import annotations

import math
from types import SimpleNamespace

import pytest

from wicked_zerg_challenger.early_defense_system import EarlyDefenseSystem


class _Point:
    """Minimal Point2 stand-in: only knows distance_to(_Point)."""

    __slots__ = ("x", "y")

    def __init__(self, x: float, y: float) -> None:
        self.x, self.y = x, y

    def distance_to(self, other: "_Point") -> float:
        # Reject anything that isn't a sibling _Point — that's exactly the
        # burnysc2 Point2.distance_to() behaviour we're guarding against.
        if not isinstance(other, _Point):
            raise TypeError("Point2.distance_to expects a Point2, not a Unit")
        return math.hypot(self.x - other.x, self.y - other.y)


class _Unit:
    """Stand-in for a sc2 Unit. distance_to() accepts only sibling _Units."""

    def __init__(self, x: float, y: float, *, refuse_unit_distance: bool = False) -> None:
        self.position = _Point(x, y)
        self._refuse = refuse_unit_distance

    def distance_to(self, other) -> float:
        if self._refuse:
            raise TypeError("simulating a unit that lacks distance_to(Unit)")
        if isinstance(other, _Unit):
            return self.position.distance_to(other.position)
        raise TypeError("Unit.distance_to expects a Unit, not a Point2")


class _Workers(list):
    def __bool__(self) -> bool:
        return len(self) > 0


def _make_bot(main_pos=(50.0, 50.0)):
    main = _Unit(*main_pos)
    return SimpleNamespace(townhalls=[main], workers=_Workers(), time=60.0)


class TestDistanceToMainFallback:
    def test_happy_path_uses_distance_to(self):
        """Normal path: obj.distance_to(main_base) succeeds."""
        bot = _make_bot()
        sys_ = EarlyDefenseSystem(bot)
        proxy = _Unit(53.0, 54.0)  # 5.0 away from (50,50)
        assert sys_._distance_to_main(proxy) == pytest.approx(5.0)

    def test_fallback_compares_positions_not_unit(self):
        """If obj.distance_to(main_base) raises, fall back to position-to-position.

        The pre-fix code did ``position.distance_to(main_base)`` which would
        re-raise because main_base is a Unit, not a Point2 — and the helper
        returned 999.0 for every proxy structure, breaking ``min(...)`` tie-
        breaking. The fix uses ``main_base.position`` for the comparison.
        """
        bot = _make_bot()
        sys_ = EarlyDefenseSystem(bot)
        # Unit whose distance_to() refuses to accept the main_base Unit, forcing
        # the fallback path.
        proxy = _Unit(53.0, 54.0, refuse_unit_distance=True)
        assert sys_._distance_to_main(proxy) == pytest.approx(5.0)
        # ...and a farther proxy ranks farther.
        proxy_far = _Unit(80.0, 90.0, refuse_unit_distance=True)
        assert sys_._distance_to_main(proxy_far) > sys_._distance_to_main(proxy)

    def test_no_main_returns_sentinel(self):
        """When the bot has no townhalls, return the 999.0 sentinel cleanly."""
        bot = SimpleNamespace(townhalls=[], workers=_Workers(), time=60.0)
        sys_ = EarlyDefenseSystem(bot)
        assert sys_._distance_to_main(_Unit(0.0, 0.0)) == 999.0

    def test_proxy_target_picker_orders_correctly_under_fallback(self):
        """The original bug: ``min(targets, key=_distance_to_main)`` returned
        an arbitrary target because every distance was 999.0. After the fix,
        the closer proxy wins even on the fallback path."""
        bot = _make_bot(main_pos=(50.0, 50.0))
        sys_ = EarlyDefenseSystem(bot)
        near = _Unit(53.0, 54.0, refuse_unit_distance=True)  # ~5 away
        far = _Unit(90.0, 90.0, refuse_unit_distance=True)   # ~56 away
        chosen = min([far, near], key=lambda s: sys_._distance_to_main(s))
        assert chosen is near


class _StructureUnit(_Unit):
    """Stand-in for an enemy structure with type_id like burnysc2 exposes."""

    def __init__(self, x, y, name: str, *, refuse_unit_distance: bool = False) -> None:
        super().__init__(x, y, refuse_unit_distance=refuse_unit_distance)
        self.type_id = SimpleNamespace(name=name)
        self.tag = id(self)


class TestProxyDetectionFallback:
    """The same Point2-vs-Unit fallback bug lived in _detect_proxy_structure_rush
    at line 210: when `structure.distance_to(main_base)` raised, the fallback
    computed `position.distance_to(main_base)` which also raised, so distance
    silently became 999.0 — well outside the 40-tile proxy gate. Real proxy
    Barracks at 35 tiles away would then go undetected.
    """

    @pytest.mark.asyncio
    async def test_proxy_detected_when_unit_distance_raises(self):
        bot = _make_bot(main_pos=(50.0, 50.0))
        # A proxy Barracks 5 tiles from our main, with refuse_unit_distance=True
        # so the structure.distance_to(main_base) call raises and forces the
        # fallback branch.
        proxy = _StructureUnit(53.0, 54.0, "BARRACKS", refuse_unit_distance=True)
        bot.enemy_structures = [proxy]
        sys_ = EarlyDefenseSystem(bot)
        await sys_._detect_proxy_structure_rush()
        # Pre-fix the fallback returned 999.0 (> 40), so proxy_response_active
        # stayed False even though the structure is right next to our base.
        assert sys_.proxy_response_active is True
        assert proxy.tag in sys_.proxy_structure_tags

    @pytest.mark.asyncio
    async def test_proxy_ignored_when_far_under_fallback(self):
        """And conversely: a genuinely-far structure still doesn't trip the gate."""
        bot = _make_bot(main_pos=(50.0, 50.0))
        far_proxy = _StructureUnit(120.0, 120.0, "BARRACKS", refuse_unit_distance=True)
        bot.enemy_structures = [far_proxy]
        sys_ = EarlyDefenseSystem(bot)
        await sys_._detect_proxy_structure_rush()
        assert sys_.proxy_response_active is False
