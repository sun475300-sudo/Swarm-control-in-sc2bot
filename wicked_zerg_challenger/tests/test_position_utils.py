# -*- coding: utf-8 -*-
"""Unit tests for utils.position_utils.

Locks in the contract that the centralized helpers must satisfy now that
multiple combat / micro modules delegate to them.
"""

import os
import sys
import unittest
from unittest.mock import Mock

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from sc2.position import Point2

from utils.position_utils import (
    get_average_distance,
    get_bounding_box,
    get_center_position,
    get_closest_unit,
    get_furthest_unit,
    get_spread_radius,
    get_weighted_center,
    interpolate_position,
    is_position_safe,
)


def _unit(x, y, hp=100, supply=2):
    u = Mock()
    u.position = Point2((x, y))
    u.health = hp
    u.supply_cost = supply
    return u


class TestPositionUtils(unittest.TestCase):
    def test_get_center_position_empty(self):
        self.assertEqual(get_center_position([]), Point2((0, 0)))

    def test_get_center_position_single(self):
        u = _unit(5, 7)
        self.assertEqual(get_center_position([u]), Point2((5, 7)))

    def test_get_center_position_multiple(self):
        units = [_unit(0, 0), _unit(10, 0), _unit(0, 10), _unit(10, 10)]
        center = get_center_position(units)
        self.assertEqual(center, Point2((5, 5)))

    def test_get_weighted_center_health(self):
        # All on x-axis; HP-heavy unit pulls center toward itself.
        units = [_unit(0, 0, hp=10), _unit(10, 0, hp=90)]
        center = get_weighted_center(units, weight_by_health=True)
        self.assertAlmostEqual(center.x, 9.0)
        self.assertAlmostEqual(center.y, 0.0)

    def test_get_weighted_center_supply_zero_falls_back(self):
        units = [_unit(0, 0, supply=0), _unit(10, 0, supply=0)]
        center = get_weighted_center(units, weight_by_supply=True)
        self.assertEqual(center, Point2((5, 0)))

    def test_get_closest_and_furthest_unit_list(self):
        units = [_unit(0, 0), _unit(10, 0), _unit(20, 0)]
        target = Point2((9, 0))
        self.assertIs(get_closest_unit(units, target), units[1])
        self.assertIs(get_furthest_unit(units, target), units[2])

    def test_get_average_distance(self):
        units = [_unit(0, 0), _unit(10, 0)]
        self.assertEqual(get_average_distance(units, Point2((0, 0))), 5.0)

    def test_get_spread_radius_singleton_zero(self):
        self.assertEqual(get_spread_radius([_unit(1, 1)]), 0.0)

    def test_is_position_safe(self):
        enemy = _unit(0, 0)
        self.assertFalse(is_position_safe(Point2((5, 0)), [enemy], safe_distance=10))
        self.assertTrue(is_position_safe(Point2((50, 0)), [enemy], safe_distance=10))
        self.assertTrue(is_position_safe(Point2((0, 0)), [], safe_distance=10))

    def test_interpolate_position_endpoints(self):
        a, b = Point2((0, 0)), Point2((10, 20))
        self.assertEqual(interpolate_position(a, b, 0.0), a)
        self.assertEqual(interpolate_position(a, b, 1.0), b)
        self.assertEqual(interpolate_position(a, b, 0.5), Point2((5, 10)))

    def test_get_bounding_box(self):
        units = [_unit(0, 5), _unit(10, -3), _unit(2, 2)]
        lo, hi = get_bounding_box(units)
        self.assertEqual(lo, Point2((0, -3)))
        self.assertEqual(hi, Point2((10, 5)))


if __name__ == "__main__":
    unittest.main()
