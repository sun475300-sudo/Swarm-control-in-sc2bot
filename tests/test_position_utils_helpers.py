"""Tests for utils/position_utils — helpers + 2026-05-06 additions."""

from __future__ import annotations

import math

import pytest
from wicked_zerg_challenger.utils.position_utils import (
    angle_to_target,
    dispersion_score,
    get_bounding_box,
    get_center_position,
    get_perimeter_positions,
    get_spread_radius,
    get_weighted_center,
    interpolate_position,
)


class _FakePoint2:
    __slots__ = ("x", "y")

    def __init__(self, x: float, y: float):
        self.x = float(x)
        self.y = float(y)

    def distance_to(self, other) -> float:
        return math.hypot(self.x - other.x, self.y - other.y)


class _FakeUnit:
    def __init__(self, x: float, y: float, *, health: float = 100.0, supply: float = 1):
        self.position = _FakePoint2(x, y)
        self.health = health
        self.supply_cost = supply


def test_get_center_position_simple():
    units = [_FakeUnit(0, 0), _FakeUnit(10, 0), _FakeUnit(0, 10), _FakeUnit(10, 10)]
    c = get_center_position(units)
    assert c.x == pytest.approx(5.0)
    assert c.y == pytest.approx(5.0)


def test_get_center_position_empty_returns_origin():
    c = get_center_position([])
    assert c.x == 0.0 and c.y == 0.0


def test_weighted_center_health_skews_toward_high_hp():
    # Two units, one full hp at (0,0), one tiny hp at (10,10)
    units = [_FakeUnit(0, 0, health=100), _FakeUnit(10, 10, health=10)]
    c = get_weighted_center(units, weight_by_health=True)
    # Should sit closer to (0,0) than geometric center (5,5)
    assert c.x < 5.0
    assert c.y < 5.0


def test_weighted_center_supply_skews_toward_high_supply():
    units = [_FakeUnit(0, 0, supply=8), _FakeUnit(10, 10, supply=1)]
    c = get_weighted_center(units, weight_by_supply=True)
    assert c.x < 5.0
    assert c.y < 5.0


def test_perimeter_positions_count_and_radius():
    center = _FakePoint2(50, 50)
    pts = get_perimeter_positions(center, radius=10, count=8)
    assert len(pts) == 8
    for p in pts:
        d = math.hypot(p.x - 50, p.y - 50)
        assert d == pytest.approx(10.0, rel=1e-6)


def test_interpolate_position_midpoint():
    p = interpolate_position(_FakePoint2(0, 0), _FakePoint2(10, 20), 0.5)
    assert p.x == pytest.approx(5.0)
    assert p.y == pytest.approx(10.0)


def test_bounding_box():
    units = [_FakeUnit(1, 2), _FakeUnit(3, -4), _FakeUnit(-5, 7)]
    lo, hi = get_bounding_box(units)
    assert (lo.x, lo.y) == (-5, -4)
    assert (hi.x, hi.y) == (3, 7)


def test_spread_radius_zero_for_singleton():
    assert get_spread_radius([_FakeUnit(0, 0)]) == 0.0
    assert get_spread_radius([]) == 0.0


def test_spread_radius_max_distance_from_center():
    units = [_FakeUnit(0, 0), _FakeUnit(10, 0)]
    # center = (5, 0); each unit is 5 away
    assert get_spread_radius(units) == pytest.approx(5.0)


# ============================================================================
# 2026-05-06 추가 헬퍼: angle_to_target, dispersion_score
# ============================================================================


class TestAngleToTarget:
    def test_east_is_zero(self):
        a = angle_to_target(_FakePoint2(0, 0), _FakePoint2(5, 0))
        assert a == pytest.approx(0.0, abs=1e-6)

    def test_north_is_half_pi(self):
        a = angle_to_target(_FakePoint2(0, 0), _FakePoint2(0, 5))
        assert a == pytest.approx(math.pi / 2, abs=1e-6)

    def test_south_is_negative_half_pi(self):
        a = angle_to_target(_FakePoint2(0, 0), _FakePoint2(0, -5))
        assert a == pytest.approx(-math.pi / 2, abs=1e-6)

    def test_west_is_pi(self):
        a = angle_to_target(_FakePoint2(0, 0), _FakePoint2(-5, 0))
        assert abs(abs(a) - math.pi) < 1e-6  # ±π


class TestDispersionScore:
    def test_empty_zero(self):
        assert dispersion_score([]) == 0.0

    def test_singleton_zero(self):
        assert dispersion_score([_FakeUnit(0, 0)]) == 0.0

    def test_two_units_half_distance(self):
        # centroid is midpoint, each unit is 5 from center → avg = 5
        score = dispersion_score([_FakeUnit(0, 0), _FakeUnit(10, 0)])
        assert score == pytest.approx(5.0)

    def test_tight_formation_low_score(self):
        units = [_FakeUnit(50 + 0.5 * i, 50) for i in range(8)]
        assert dispersion_score(units) < 3.0

    def test_dispersed_formation_high_score(self):
        units = [
            _FakeUnit(0, 0),
            _FakeUnit(100, 0),
            _FakeUnit(0, 100),
            _FakeUnit(100, 100),
        ]
        # centroid = (50, 50); each is sqrt(50^2 + 50^2) ≈ 70.7 away
        assert dispersion_score(units) > 50.0
