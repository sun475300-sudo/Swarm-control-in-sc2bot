# -*- coding: utf-8 -*-
"""
Regression tests for utils.position_utils

These tests work without the sc2 package installed, thanks to the lightweight
Point2 fallback inside position_utils.
"""

import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

import math

import pytest
from utils.position_utils import (
    Point2,
    clamp_position,
    get_average_distance,
    get_bounding_box,
    get_center_position,
    get_closest_unit,
    get_furthest_unit,
    get_perimeter_positions,
    get_spread_radius,
    get_weighted_center,
    interpolate_position,
    is_position_safe,
)


class _FakeUnit:
    """Minimal stand-in for sc2.unit.Unit."""

    def __init__(
        self, x: float, y: float, health: float = 100.0, supply_cost: float = 2.0
    ):
        self.position = Point2((x, y))
        self.health = health
        self.supply_cost = supply_cost


def _approx(point, expected_x, expected_y):
    assert point.x == pytest.approx(expected_x)
    assert point.y == pytest.approx(expected_y)


class TestGetCenterPosition:
    def test_empty_returns_origin(self):
        result = get_center_position([])
        _approx(result, 0.0, 0.0)

    def test_single_unit_returns_that_position(self):
        u = _FakeUnit(7, 9)
        result = get_center_position([u])
        _approx(result, 7, 9)

    def test_geometric_center_of_three(self):
        units = [_FakeUnit(0, 0), _FakeUnit(6, 0), _FakeUnit(0, 6)]
        result = get_center_position(units)
        _approx(result, 2, 2)


class TestGetWeightedCenter:
    def test_health_weighted_pulls_toward_high_hp(self):
        light = _FakeUnit(0, 0, health=10)
        heavy = _FakeUnit(10, 0, health=1000)
        result = get_weighted_center([light, heavy], weight_by_health=True)
        # Should be much closer to the heavy unit at x=10 than midpoint x=5.
        assert result.x > 9.0

    def test_zero_total_health_falls_back_to_geometric(self):
        a = _FakeUnit(0, 0, health=0)
        b = _FakeUnit(10, 0, health=0)
        result = get_weighted_center([a, b], weight_by_health=True)
        _approx(result, 5, 0)

    def test_supply_weighted_balances_lings_vs_ultras(self):
        ling = _FakeUnit(0, 0, supply_cost=0.5)
        ultra = _FakeUnit(10, 0, supply_cost=6)
        result = get_weighted_center([ling, ultra], weight_by_supply=True)
        # Ultra weight 6 vs ling 0.5: center ~ (10*6 + 0*0.5)/6.5 ≈ 9.23
        assert result.x == pytest.approx(60 / 6.5)

    def test_default_returns_geometric_center(self):
        a, b = _FakeUnit(0, 0), _FakeUnit(4, 4)
        result = get_weighted_center([a, b])
        _approx(result, 2, 2)

    def test_empty_returns_origin(self):
        _approx(get_weighted_center([]), 0, 0)


class TestClosestFurthest:
    def test_get_closest_unit(self):
        units = [_FakeUnit(0, 0), _FakeUnit(5, 0), _FakeUnit(20, 0)]
        result = get_closest_unit(units, Point2((6, 0)))
        assert result.position.x == 5

    def test_get_furthest_unit(self):
        units = [_FakeUnit(0, 0), _FakeUnit(5, 0), _FakeUnit(20, 0)]
        result = get_furthest_unit(units, Point2((0, 0)))
        assert result.position.x == 20

    def test_empty_inputs_return_none(self):
        assert get_closest_unit([], Point2((0, 0))) is None
        assert get_furthest_unit([], Point2((0, 0))) is None


class TestDistanceMetrics:
    def test_get_average_distance(self):
        units = [_FakeUnit(0, 0), _FakeUnit(10, 0)]
        avg = get_average_distance(units, Point2((0, 0)))
        assert avg == pytest.approx(5.0)

    def test_average_distance_empty_is_zero(self):
        assert get_average_distance([], Point2((0, 0))) == 0.0

    def test_spread_radius_zero_for_singletons(self):
        assert get_spread_radius([]) == 0.0
        assert get_spread_radius([_FakeUnit(5, 5)]) == 0.0

    def test_spread_radius_nonzero(self):
        units = [_FakeUnit(0, 0), _FakeUnit(6, 0), _FakeUnit(0, 6)]
        spread = get_spread_radius(units)
        # Center is (2, 2); furthest unit is sqrt(20)
        assert spread == pytest.approx(math.sqrt(20))


class TestPositionSafety:
    def test_safe_with_no_enemies(self):
        assert is_position_safe(Point2((0, 0)), []) is True

    def test_safe_when_enemies_far_enough(self):
        enemies = [_FakeUnit(50, 50)]
        assert is_position_safe(Point2((0, 0)), enemies, safe_distance=10) is True

    def test_unsafe_when_enemy_close(self):
        enemies = [_FakeUnit(2, 2)]
        assert is_position_safe(Point2((0, 0)), enemies, safe_distance=10) is False


class TestPerimeterAndInterpolate:
    def test_perimeter_count(self):
        positions = get_perimeter_positions(Point2((0, 0)), 5, count=8)
        assert len(positions) == 8

    def test_perimeter_radius(self):
        center = Point2((0, 0))
        positions = get_perimeter_positions(center, 5, count=12)
        for p in positions:
            assert p.distance_to(center) == pytest.approx(5.0)

    def test_interpolate_endpoints(self):
        a = Point2((0, 0))
        b = Point2((10, 10))
        _approx(interpolate_position(a, b, 0), 0, 0)
        _approx(interpolate_position(a, b, 1), 10, 10)
        _approx(interpolate_position(a, b, 0.5), 5, 5)


class TestClampPosition:
    def test_inside_bounds_unchanged(self):
        p = clamp_position(Point2((5, 5)), 0, 10, 0, 10)
        _approx(p, 5, 5)

    def test_above_max_clamped(self):
        p = clamp_position(Point2((20, 20)), 0, 10, 0, 10)
        _approx(p, 10, 10)

    def test_below_min_clamped(self):
        p = clamp_position(Point2((-3, -7)), 0, 10, 0, 10)
        _approx(p, 0, 0)


class TestBoundingBox:
    def test_empty_returns_origin_pair(self):
        a, b = get_bounding_box([])
        _approx(a, 0, 0)
        _approx(b, 0, 0)

    def test_basic_bounding_box(self):
        units = [_FakeUnit(-3, 1), _FakeUnit(4, -2), _FakeUnit(0, 5)]
        lo, hi = get_bounding_box(units)
        _approx(lo, -3, -2)
        _approx(hi, 4, 5)
