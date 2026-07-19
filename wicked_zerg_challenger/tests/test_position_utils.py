# -*- coding: utf-8 -*-
import os
import sys
import unittest

os.environ["PROTOCOL_BUFFERS_PYTHON_IMPLEMENTATION"] = "python"
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from sc2.position import Point2

from utils.position_utils import (
    clamp_position,
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


class FakeUnit:
    def __init__(self, x, y, health=0, supply_cost=0):
        self.position = Point2((x, y))
        self.health = health
        self.supply_cost = supply_cost


class TestGetCenterPosition(unittest.TestCase):
    def test_empty_returns_origin(self):
        self.assertEqual(get_center_position([]), Point2((0, 0)))

    def test_single_unit_returns_its_position(self):
        u = FakeUnit(5, 7)
        self.assertEqual(get_center_position([u]), u.position)

    def test_multiple_units_averages_position(self):
        units = [FakeUnit(0, 0), FakeUnit(10, 0), FakeUnit(5, 10)]
        center = get_center_position(units)
        self.assertAlmostEqual(center.x, 5.0)
        self.assertAlmostEqual(center.y, 10.0 / 3)


class TestGetWeightedCenter(unittest.TestCase):
    def test_health_weighted_favors_high_hp_unit(self):
        units = [FakeUnit(0, 0, health=1), FakeUnit(10, 0, health=99)]
        center = get_weighted_center(units, weight_by_health=True)
        self.assertGreater(center.x, 5.0)

    def test_supply_weighted_falls_back_to_geometric_when_zero_supply(self):
        units = [FakeUnit(0, 0, supply_cost=0), FakeUnit(10, 0, supply_cost=0)]
        center = get_weighted_center(units, weight_by_supply=True)
        self.assertAlmostEqual(center.x, 5.0)

    def test_defaults_to_geometric_center(self):
        units = [FakeUnit(0, 0), FakeUnit(10, 10)]
        center = get_weighted_center(units)
        self.assertAlmostEqual(center.x, 5.0)
        self.assertAlmostEqual(center.y, 5.0)


class TestClosestFurthestUnit(unittest.TestCase):
    def test_get_closest_unit(self):
        units = [FakeUnit(0, 0), FakeUnit(10, 10), FakeUnit(1, 1)]
        closest = get_closest_unit(units, Point2((0, 0)))
        self.assertEqual(closest.position, Point2((0, 0)))

    def test_get_furthest_unit(self):
        units = [FakeUnit(0, 0), FakeUnit(10, 10), FakeUnit(1, 1)]
        furthest = get_furthest_unit(units, Point2((0, 0)))
        self.assertEqual(furthest.position, Point2((10, 10)))

    def test_empty_returns_none(self):
        self.assertIsNone(get_closest_unit([], Point2((0, 0))))
        self.assertIsNone(get_furthest_unit([], Point2((0, 0))))


class TestDistanceAndSpread(unittest.TestCase):
    def test_get_average_distance(self):
        units = [FakeUnit(0, 0), FakeUnit(10, 0)]
        avg = get_average_distance(units, Point2((0, 0)))
        self.assertAlmostEqual(avg, 5.0)

    def test_get_spread_radius(self):
        units = [FakeUnit(0, 0), FakeUnit(10, 0)]
        self.assertAlmostEqual(get_spread_radius(units), 5.0)

    def test_get_spread_radius_single_unit_is_zero(self):
        self.assertEqual(get_spread_radius([FakeUnit(0, 0)]), 0.0)


class TestIsPositionSafe(unittest.TestCase):
    def test_safe_when_no_enemies(self):
        self.assertTrue(is_position_safe(Point2((0, 0)), []))

    def test_unsafe_when_enemy_within_range(self):
        enemies = [FakeUnit(1, 0)]
        self.assertFalse(is_position_safe(Point2((0, 0)), enemies, safe_distance=10.0))

    def test_safe_when_enemy_outside_range(self):
        enemies = [FakeUnit(100, 0)]
        self.assertTrue(is_position_safe(Point2((0, 0)), enemies, safe_distance=10.0))


class TestGeometryHelpers(unittest.TestCase):
    def test_interpolate_position_midpoint(self):
        mid = interpolate_position(Point2((0, 0)), Point2((10, 10)), 0.5)
        self.assertAlmostEqual(mid.x, 5.0)
        self.assertAlmostEqual(mid.y, 5.0)

    def test_clamp_position_keeps_within_bounds(self):
        clamped = clamp_position(Point2((-5, 50)), 0, 20, 0, 20)
        self.assertEqual(clamped, Point2((0, 20)))

    def test_get_bounding_box(self):
        units = [FakeUnit(-2, 3), FakeUnit(8, -4)]
        min_corner, max_corner = get_bounding_box(units)
        self.assertEqual(min_corner, Point2((-2, -4)))
        self.assertEqual(max_corner, Point2((8, 3)))


if __name__ == "__main__":
    unittest.main()
