# -*- coding: utf-8 -*-
"""
Unit tests for wicked_zerg_challenger/utils/position_utils.py.

This module had zero test coverage despite being a shared utility used
to eliminate position-calculation duplication across managers.
"""

import os
import sys

import pytest

sys.path.insert(
    0, os.path.join(os.path.dirname(__file__), "..", "wicked_zerg_challenger")
)

try:
    from sc2.position import Point2

    from utils.position_utils import (
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
except ImportError:
    pytest.skip("position_utils not importable (SC2 env required)", allow_module_level=True)


class FakeUnit:
    def __init__(self, x, y, health=100.0, health_max=100.0, supply_cost=1.0):
        self.position = Point2((x, y))
        self.health = health
        self.health_max = health_max
        self.supply_cost = supply_cost

    def distance_to(self, other):
        pos = other.position if hasattr(other, "position") else other
        return self.position.distance_to(pos)


class TestGetCenterPosition:
    def test_empty_returns_origin(self):
        assert get_center_position([]) == Point2((0, 0))

    def test_single_unit_returns_its_position(self):
        u = FakeUnit(5, 7)
        assert get_center_position([u]) == u.position

    def test_two_units_returns_midpoint(self):
        units = [FakeUnit(0, 0), FakeUnit(10, 0)]
        center = get_center_position(units)
        assert center.x == pytest.approx(5.0)
        assert center.y == pytest.approx(0.0)

    def test_square_returns_centroid(self):
        units = [FakeUnit(0, 0), FakeUnit(0, 10), FakeUnit(10, 0), FakeUnit(10, 10)]
        center = get_center_position(units)
        assert center.x == pytest.approx(5.0)
        assert center.y == pytest.approx(5.0)


class TestGetWeightedCenter:
    def test_no_weighting_matches_geometric_center(self):
        units = [FakeUnit(0, 0), FakeUnit(10, 0)]
        assert get_weighted_center(units) == get_center_position(units)

    def test_health_weighting_biases_toward_higher_health(self):
        low = FakeUnit(0, 0, health=1.0)
        high = FakeUnit(10, 0, health=99.0)
        center = get_weighted_center([low, high], weight_by_health=True)
        assert center.x > 5.0  # pulled toward the high-health unit

    def test_health_weighting_falls_back_when_total_health_zero(self):
        units = [FakeUnit(0, 0, health=0.0), FakeUnit(10, 0, health=0.0)]
        center = get_weighted_center(units, weight_by_health=True)
        assert center == get_center_position(units)

    def test_supply_weighting_biases_toward_higher_supply(self):
        cheap = FakeUnit(0, 0, supply_cost=1.0)
        expensive = FakeUnit(10, 0, supply_cost=9.0)
        center = get_weighted_center([cheap, expensive], weight_by_supply=True)
        assert center.x > 5.0  # pulled toward the high-supply unit


class TestGetClosestFurthestUnit:
    def test_empty_returns_none(self):
        assert get_closest_unit([], Point2((0, 0))) is None
        assert get_furthest_unit([], Point2((0, 0))) is None

    def test_closest_unit(self):
        units = [FakeUnit(0, 0), FakeUnit(5, 0), FakeUnit(20, 0)]
        closest = get_closest_unit(units, Point2((4, 0)))
        assert closest.position == Point2((5, 0))

    def test_furthest_unit(self):
        units = [FakeUnit(0, 0), FakeUnit(5, 0), FakeUnit(20, 0)]
        furthest = get_furthest_unit(units, Point2((0, 0)))
        assert furthest.position == Point2((20, 0))


class TestGetAverageDistance:
    def test_empty_returns_zero(self):
        assert get_average_distance([], Point2((0, 0))) == 0.0

    def test_average_of_two(self):
        units = [FakeUnit(0, 0), FakeUnit(10, 0)]
        avg = get_average_distance(units, Point2((5, 0)))
        assert avg == pytest.approx(5.0)


class TestGetSpreadRadius:
    def test_empty_or_single_returns_zero(self):
        assert get_spread_radius([]) == 0.0
        assert get_spread_radius([FakeUnit(0, 0)]) == 0.0

    def test_spread_matches_max_distance_from_center(self):
        units = [FakeUnit(-5, 0), FakeUnit(5, 0)]
        assert get_spread_radius(units) == pytest.approx(5.0)


class TestIsPositionSafe:
    def test_no_enemies_is_safe(self):
        assert is_position_safe(Point2((0, 0)), []) is True

    def test_enemy_within_safe_distance_is_unsafe(self):
        enemies = [FakeUnit(3, 0)]
        assert is_position_safe(Point2((0, 0)), enemies, safe_distance=10.0) is False

    def test_enemy_beyond_safe_distance_is_safe(self):
        enemies = [FakeUnit(20, 0)]
        assert is_position_safe(Point2((0, 0)), enemies, safe_distance=10.0) is True


class TestGeometryHelpers:
    def test_get_perimeter_positions_count_and_radius(self):
        positions = get_perimeter_positions(Point2((0, 0)), radius=10, count=4)
        assert len(positions) == 4
        for p in positions:
            assert p.distance_to(Point2((0, 0))) == pytest.approx(10.0, abs=1e-6)

    def test_interpolate_position_midpoint(self):
        mid = interpolate_position(Point2((0, 0)), Point2((10, 10)), 0.5)
        assert mid.x == pytest.approx(5.0)
        assert mid.y == pytest.approx(5.0)

    def test_interpolate_position_at_start_and_end(self):
        start, end = Point2((0, 0)), Point2((10, 10))
        assert interpolate_position(start, end, 0.0) == start
        assert interpolate_position(start, end, 1.0) == end

    def test_clamp_position_within_bounds_unchanged(self):
        p = clamp_position(Point2((5, 5)), 0, 10, 0, 10)
        assert p == Point2((5, 5))

    def test_clamp_position_outside_bounds_is_clamped(self):
        p = clamp_position(Point2((-5, 15)), 0, 10, 0, 10)
        assert p.x == 0
        assert p.y == 10

    def test_get_bounding_box_empty(self):
        min_c, max_c = get_bounding_box([])
        assert min_c == Point2((0, 0))
        assert max_c == Point2((0, 0))

    def test_get_bounding_box(self):
        units = [FakeUnit(-5, 2), FakeUnit(8, -3), FakeUnit(0, 10)]
        min_c, max_c = get_bounding_box(units)
        assert min_c == Point2((-5, -3))
        assert max_c == Point2((8, 10))
