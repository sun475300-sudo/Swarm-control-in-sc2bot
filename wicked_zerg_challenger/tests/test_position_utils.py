# -*- coding: utf-8 -*-
import os
import sys
import unittest

os.environ["PROTOCOL_BUFFERS_PYTHON_IMPLEMENTATION"] = "python"
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

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


class FakePosition:
    def __init__(self, x, y):
        self.x = x
        self.y = y

    def distance_to(self, other):
        return ((self.x - other.x) ** 2 + (self.y - other.y) ** 2) ** 0.5


class FakeUnit:
    def __init__(self, x, y, health=100, supply_cost=1):
        self.position = FakePosition(x, y)
        self.health = health
        self.supply_cost = supply_cost


class TestPositionUtils(unittest.TestCase):
    def test_get_center_position_empty(self):
        center = get_center_position([])
        self.assertEqual((center.x, center.y), (0, 0))

    def test_get_center_position_single_unit_returns_its_position(self):
        u = FakeUnit(5, 5)
        center = get_center_position([u])
        self.assertIs(center, u.position)

    def test_get_center_position_multiple_units(self):
        units = [FakeUnit(0, 0), FakeUnit(10, 0), FakeUnit(5, 10)]
        center = get_center_position(units)
        self.assertAlmostEqual(center.x, 5.0)
        self.assertAlmostEqual(center.y, 10 / 3)

    def test_get_weighted_center_by_health(self):
        # Heavy unit at (0,0), light unit at (10,0) -> center pulled toward heavy unit
        units = [FakeUnit(0, 0, health=300), FakeUnit(10, 0, health=100)]
        center = get_weighted_center(units, weight_by_health=True)
        self.assertAlmostEqual(center.x, 2.5)

    def test_get_weighted_center_zero_health_falls_back_to_geometric(self):
        units = [FakeUnit(0, 0, health=0), FakeUnit(10, 0, health=0)]
        center = get_weighted_center(units, weight_by_health=True)
        self.assertAlmostEqual(center.x, 5.0)

    def test_get_weighted_center_by_supply(self):
        units = [FakeUnit(0, 0, supply_cost=6), FakeUnit(10, 0, supply_cost=2)]
        center = get_weighted_center(units, weight_by_supply=True)
        self.assertAlmostEqual(center.x, 2.5)

    def test_get_closest_and_furthest_unit(self):
        units = [FakeUnit(0, 0), FakeUnit(10, 0), FakeUnit(20, 0)]
        target = FakePosition(1, 0)
        self.assertIs(get_closest_unit(units, target), units[0])
        self.assertIs(get_furthest_unit(units, target), units[2])

    def test_get_closest_unit_empty_returns_none(self):
        self.assertIsNone(get_closest_unit([], FakePosition(0, 0)))

    def test_get_average_distance(self):
        units = [FakeUnit(0, 0), FakeUnit(4, 0)]
        avg = get_average_distance(units, FakePosition(0, 0))
        self.assertAlmostEqual(avg, 2.0)

    def test_get_average_distance_empty(self):
        self.assertEqual(get_average_distance([], FakePosition(0, 0)), 0.0)

    def test_get_spread_radius(self):
        units = [FakeUnit(0, 0), FakeUnit(10, 0)]
        self.assertAlmostEqual(get_spread_radius(units), 5.0)

    def test_get_spread_radius_single_unit(self):
        self.assertEqual(get_spread_radius([FakeUnit(0, 0)]), 0.0)

    def test_is_position_safe(self):
        enemies = [FakeUnit(0, 0)]
        self.assertFalse(is_position_safe(FakePosition(1, 0), enemies, safe_distance=5))
        self.assertTrue(is_position_safe(FakePosition(100, 0), enemies, safe_distance=5))

    def test_is_position_safe_no_enemies(self):
        self.assertTrue(is_position_safe(FakePosition(0, 0), []))

    def test_get_perimeter_positions_count_and_radius(self):
        center = FakePosition(0, 0)
        points = get_perimeter_positions(center, radius=10, count=4)
        self.assertEqual(len(points), 4)
        for p in points:
            dist = (p.x**2 + p.y**2) ** 0.5
            self.assertAlmostEqual(dist, 10.0, places=5)

    def test_interpolate_position(self):
        start = FakePosition(0, 0)
        end = FakePosition(10, 10)
        mid = interpolate_position(start, end, 0.5)
        self.assertAlmostEqual(mid.x, 5.0)
        self.assertAlmostEqual(mid.y, 5.0)

    def test_clamp_position(self):
        pos = FakePosition(-5, 50)
        clamped = clamp_position(pos, 0, 20, 0, 20)
        self.assertEqual((clamped.x, clamped.y), (0, 20))

    def test_get_bounding_box(self):
        units = [FakeUnit(-1, 2), FakeUnit(5, -3), FakeUnit(2, 8)]
        min_corner, max_corner = get_bounding_box(units)
        self.assertEqual((min_corner.x, min_corner.y), (-1, -3))
        self.assertEqual((max_corner.x, max_corner.y), (5, 8))

    def test_get_bounding_box_empty(self):
        min_corner, max_corner = get_bounding_box([])
        self.assertEqual((min_corner.x, min_corner.y), (0, 0))
        self.assertEqual((max_corner.x, max_corner.y), (0, 0))


if __name__ == "__main__":
    unittest.main()
