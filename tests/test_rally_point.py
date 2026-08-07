"""Tests for wicked_zerg_challenger/combat/rally_point.py.

No SC2 game instance required — uses SimpleNamespace stand-ins for bot,
townhalls, and units.
"""
from __future__ import annotations

import math
from types import SimpleNamespace

import pytest

from wicked_zerg_challenger.combat.rally_point import RallyPointManager


class P:
    __slots__ = ("x", "y")

    def __init__(self, x, y=None):
        # Accept both P(x, y) and P((x, y)) — mimics sc2.Point2 which is
        # constructed from a tuple.
        if y is None and hasattr(x, "__iter__"):
            x, y = list(x)[:2]
        self.x = float(x)
        self.y = float(y)

    def distance_to(self, other) -> float:
        ox = getattr(other, "x", None)
        oy = getattr(other, "y", None)
        if ox is None or oy is None:
            raise AttributeError("missing x/y")
        return math.hypot(self.x - ox, self.y - oy)

    def towards(self, other, distance: float) -> "P":
        d = self.distance_to(other)
        if d == 0:
            return P(self.x, self.y)
        return P(
            self.x + (other.x - self.x) * (distance / d),
            self.y + (other.y - self.y) * (distance / d),
        )


def _make_unit(pos: P, tag: int = 1, is_idle: bool = False):
    return SimpleNamespace(
        tag=tag,
        is_idle=is_idle,
        position=pos,
        distance_to=lambda other, _pos=pos: _pos.distance_to(other),
        move=lambda target: ("move", target),
    )


def _make_townhalls(positions):
    items = [SimpleNamespace(position=p) for p in positions]
    list_obj = list(items)
    list_obj_with_amount = SimpleNamespace(
        amount=len(items),
        exists=bool(items),
        first=items[0] if items else None,
        closest_to=lambda target: min(
            items, key=lambda th: th.position.distance_to(target)
        ),
    )
    # Mimic Units iteration via __bool__
    list_obj_with_amount.__bool__ = lambda self=list_obj_with_amount: bool(items)
    return list_obj_with_amount


def _make_bot(time=0.0, ths=None, map_center=P(50, 50)):
    bot = SimpleNamespace(
        time=time,
        townhalls=ths,
        game_info=SimpleNamespace(map_center=map_center) if map_center else None,
        Point2=P,
        do=lambda action: None,
        start_location=P(0, 0),
    )
    return bot


# ---------------------------------------------------------------------------
# min_army_for_attack: early-game vs late-game threshold
# ---------------------------------------------------------------------------

def test_min_army_early_game_uses_lower_threshold():
    bot = _make_bot(time=120.0)
    rpm = RallyPointManager(bot)
    assert rpm.min_army_for_attack == RallyPointManager.DEFAULT_EARLY_GAME_MIN_ATTACK


def test_min_army_late_game_uses_higher_threshold():
    bot = _make_bot(time=600.0)
    rpm = RallyPointManager(bot)
    assert rpm.min_army_for_attack == RallyPointManager.DEFAULT_MIN_ARMY_FOR_ATTACK


def test_min_army_at_cutoff_uses_late_game_value():
    """At exactly EARLY_GAME_CUTOFF_SEC seconds, switch to late game threshold."""
    bot = _make_bot(time=float(RallyPointManager.EARLY_GAME_CUTOFF_SEC))
    rpm = RallyPointManager(bot)
    assert rpm.min_army_for_attack == RallyPointManager.DEFAULT_MIN_ARMY_FOR_ATTACK


# ---------------------------------------------------------------------------
# should_update_rally_point: cache TTL
# ---------------------------------------------------------------------------

def test_should_update_when_unset():
    rpm = RallyPointManager(_make_bot())
    assert rpm.should_update_rally_point(0.0) is True


def test_should_update_respects_interval():
    rpm = RallyPointManager(_make_bot())
    rpm._rally_point = P(10, 10)
    rpm._last_rally_update = 100.0
    interval = RallyPointManager.DEFAULT_RALLY_UPDATE_INTERVAL
    # halfway through interval — no update
    assert rpm.should_update_rally_point(100.0 + interval / 2) is False
    # at/after interval — update
    assert rpm.should_update_rally_point(100.0 + interval) is True


# ---------------------------------------------------------------------------
# update_rally_point: positions itself bias_pct of the way to map center
# ---------------------------------------------------------------------------

def test_update_rally_point_biases_toward_map_center():
    bot = _make_bot(
        time=5.0, ths=_make_townhalls([P(0, 0)]), map_center=P(100, 100)
    )
    rpm = RallyPointManager(bot)
    rpm.update_rally_point()
    bias = RallyPointManager.RALLY_BIAS_FROM_BASE
    assert rpm.rally_point.x == pytest.approx(100 * bias)
    assert rpm.rally_point.y == pytest.approx(100 * bias)
    assert rpm._last_rally_update == 5.0


def test_update_rally_point_no_townhalls_does_nothing():
    bot = _make_bot(ths=_make_townhalls([]))
    rpm = RallyPointManager(bot)
    rpm.update_rally_point()
    assert rpm.rally_point is None


def test_update_rally_point_falls_back_on_error():
    """When game_info is missing AND townhalls has no .position support,
    we fall back to start_location."""
    bot = SimpleNamespace(
        townhalls=SimpleNamespace(exists=True, first=SimpleNamespace()),
        # no game_info, no Point2 — and the dummy first has no .position
        start_location=P(7, 7),
        time=0.0,
    )
    rpm = RallyPointManager(bot)
    rpm.update_rally_point()
    assert rpm.rally_point == bot.start_location


# ---------------------------------------------------------------------------
# calculate_rally_point: forward rally for 2-base+, otherwise own base
# ---------------------------------------------------------------------------

def test_calculate_rally_pushes_forward_when_multi_base():
    map_center = P(100, 100)
    bot = _make_bot(
        ths=_make_townhalls([P(0, 0), P(50, 50)]), map_center=map_center
    )
    rpm = RallyPointManager(bot)
    rally = rpm.calculate_rally_point()
    # closest-to-center base is (50, 50); push FORWARD_RALLY_PUSH_DISTANCE toward (100, 100)
    push = RallyPointManager.FORWARD_RALLY_PUSH_DISTANCE
    expected = P(50, 50).towards(map_center, push)
    assert rally.x == pytest.approx(expected.x)
    assert rally.y == pytest.approx(expected.y)


def test_calculate_rally_returns_none_when_no_townhalls():
    bot = _make_bot(ths=None)
    rpm = RallyPointManager(bot)
    assert rpm.calculate_rally_point() is None


# ---------------------------------------------------------------------------
# is_army_gathered: 70% threshold
# ---------------------------------------------------------------------------

def test_is_army_gathered_true_when_no_rally_point():
    rpm = RallyPointManager(_make_bot())
    assert rpm.is_army_gathered([_make_unit(P(0, 0))]) is True


def test_is_army_gathered_true_at_gathered_ratio_threshold():
    rpm = RallyPointManager(_make_bot())
    rpm._rally_point = P(0, 0)
    radius = RallyPointManager.GATHERED_RADIUS - 1  # safely inside
    # 7/10 inside → exactly at GATHERED_RATIO
    units = [_make_unit(P(radius, 0), tag=i) for i in range(7)] + [
        _make_unit(P(100, 100), tag=10 + i) for i in range(3)
    ]
    assert rpm.is_army_gathered(units) is True


def test_is_army_gathered_false_below_threshold():
    rpm = RallyPointManager(_make_bot())
    rpm._rally_point = P(0, 0)
    radius = RallyPointManager.GATHERED_RADIUS - 1
    # 5/10 inside → below 0.7 ratio
    units = [_make_unit(P(radius, 0), tag=i) for i in range(5)] + [
        _make_unit(P(100, 100), tag=10 + i) for i in range(5)
    ]
    assert rpm.is_army_gathered(units) is False


def test_is_army_gathered_handles_broken_unit_gracefully():
    rpm = RallyPointManager(_make_bot())
    rpm._rally_point = P(0, 0)
    radius = RallyPointManager.GATHERED_RADIUS - 1
    broken_unit = SimpleNamespace(
        tag=99, distance_to=lambda *_: (_ for _ in ()).throw(AttributeError())
    )
    units = [_make_unit(P(radius, 0), tag=i) for i in range(7)] + [broken_unit]
    # Broken unit counted in total but not as "near" → 7/8 still passes 0.7
    assert rpm.is_army_gathered(units) is True


# ---------------------------------------------------------------------------
# has_minimum_army
# ---------------------------------------------------------------------------

def test_has_minimum_army_uses_early_threshold_in_early_game():
    bot = _make_bot(time=100.0)
    rpm = RallyPointManager(bot)
    units = [_make_unit(P(0, 0), tag=i) for i in range(
        RallyPointManager.DEFAULT_EARLY_GAME_MIN_ATTACK
    )]
    assert rpm.has_minimum_army(units) is True
    assert rpm.has_minimum_army(units[:-1]) is False


def test_has_minimum_army_uses_late_threshold_in_late_game():
    bot = _make_bot(time=999.0)
    rpm = RallyPointManager(bot)
    units = [_make_unit(P(0, 0), tag=i) for i in range(
        RallyPointManager.DEFAULT_MIN_ARMY_FOR_ATTACK
    )]
    assert rpm.has_minimum_army(units) is True
    assert rpm.has_minimum_army(units[:-1]) is False
