# -*- coding: utf-8 -*-
"""
utils/position_utils.py 위치 유틸리티 함수 단위 테스트.
"""

import os
import sys
import unittest
from dataclasses import dataclass
from unittest.mock import MagicMock

os.environ.setdefault("PROTOCOL_BUFFERS_PYTHON_IMPLEMENTATION", "python")
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from sc2.position import Point2

from utils.position_utils import (
    get_average_distance,
    get_center_position,
    get_closest_unit,
    get_furthest_unit,
    get_spread_radius,
    get_weighted_center,
    is_position_safe,
)


def _unit(x, y, health=100, supply=1):
    """Create a mock unit with position, health, supply_cost."""
    u = MagicMock()
    u.position = Point2((float(x), float(y)))
    u.health = health
    u.supply_cost = supply
    return u


class TestGetCenterPosition(unittest.TestCase):
    def test_empty_returns_origin(self):
        result = get_center_position([])
        self.assertEqual(result, Point2((0, 0)))

    def test_single_returns_own_position(self):
        u = _unit(5, 7)
        self.assertEqual(get_center_position([u]), Point2((5, 7)))

    def test_two_units_midpoint(self):
        units = [_unit(0, 0), _unit(10, 10)]
        result = get_center_position(units)
        self.assertAlmostEqual(result.x, 5.0)
        self.assertAlmostEqual(result.y, 5.0)

    def test_three_units_average(self):
        units = [_unit(0, 0), _unit(3, 0), _unit(0, 6)]
        result = get_center_position(units)
        self.assertAlmostEqual(result.x, 1.0)
        self.assertAlmostEqual(result.y, 2.0)


class TestGetWeightedCenter(unittest.TestCase):
    def test_empty_returns_origin(self):
        self.assertEqual(get_weighted_center([]), Point2((0, 0)))

    def test_health_weight_pulls_toward_high_hp(self):
        # 첫 유닛 hp 90, 두 번째 hp 10 → 무게중심은 첫 유닛 쪽으로 치우침
        units = [_unit(0, 0, health=90), _unit(10, 0, health=10)]
        result = get_weighted_center(units, weight_by_health=True)
        # (0*90 + 10*10) / 100 = 1.0
        self.assertAlmostEqual(result.x, 1.0)

    def test_health_zero_falls_back_to_geometric(self):
        units = [_unit(0, 0, health=0), _unit(10, 0, health=0)]
        result = get_weighted_center(units, weight_by_health=True)
        self.assertAlmostEqual(result.x, 5.0)

    def test_supply_weight(self):
        units = [_unit(0, 0, supply=2), _unit(10, 0, supply=8)]
        result = get_weighted_center(units, weight_by_supply=True)
        # (0*2 + 10*8) / 10 = 8.0
        self.assertAlmostEqual(result.x, 8.0)

    def test_no_weighting_falls_back_to_geometric(self):
        units = [_unit(0, 0), _unit(10, 0)]
        result = get_weighted_center(units)
        self.assertAlmostEqual(result.x, 5.0)


class TestGetClosestUnit(unittest.TestCase):
    def test_empty_returns_none(self):
        self.assertIsNone(get_closest_unit([], Point2((0, 0))))

    def test_returns_closest(self):
        units = [_unit(0, 0), _unit(10, 0), _unit(5, 0)]
        result = get_closest_unit(units, Point2((6, 0)))
        self.assertEqual(result.position, Point2((5, 0)))


class TestGetFurthestUnit(unittest.TestCase):
    def test_empty_returns_none(self):
        self.assertIsNone(get_furthest_unit([], Point2((0, 0))))

    def test_returns_furthest(self):
        units = [_unit(0, 0), _unit(20, 0), _unit(5, 0)]
        result = get_furthest_unit(units, Point2((0, 0)))
        self.assertEqual(result.position, Point2((20, 0)))


class TestGetAverageDistance(unittest.TestCase):
    def test_empty_returns_zero(self):
        self.assertEqual(get_average_distance([], Point2((0, 0))), 0.0)

    def test_average(self):
        units = [_unit(0, 0), _unit(4, 0), _unit(8, 0)]
        # distances: 0, 4, 8 → avg = 4.0
        self.assertAlmostEqual(get_average_distance(units, Point2((0, 0))), 4.0)


class TestGetSpreadRadius(unittest.TestCase):
    def test_empty_returns_zero(self):
        self.assertEqual(get_spread_radius([]), 0.0)

    def test_single_unit_returns_zero(self):
        self.assertEqual(get_spread_radius([_unit(5, 5)]), 0.0)

    def test_spread(self):
        units = [_unit(0, 0), _unit(10, 0)]
        # center = (5,0), max distance = 5
        self.assertAlmostEqual(get_spread_radius(units), 5.0)


class TestIsPositionSafe(unittest.TestCase):
    def test_no_enemies_is_safe(self):
        self.assertTrue(is_position_safe(Point2((0, 0)), []))

    def test_distant_enemies_safe(self):
        enemies = [_unit(100, 100)]
        self.assertTrue(is_position_safe(Point2((0, 0)), enemies, safe_distance=10.0))

    def test_close_enemies_unsafe(self):
        enemies = [_unit(2, 0)]
        self.assertFalse(is_position_safe(Point2((0, 0)), enemies, safe_distance=10.0))


if __name__ == "__main__":
    unittest.main()
