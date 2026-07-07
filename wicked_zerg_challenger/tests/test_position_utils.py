# -*- coding: utf-8 -*-
"""
Unit tests for utils/position_utils.py and the related
utils/common_helpers.py wrappers (centroid, closest_enemy, filter_by_type,
units_amount) that combat_manager.py relies on via HELPERS_AVAILABLE.
"""

import os
import sys
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
    is_position_safe,
)


def make_unit(x, y, health=100, supply_cost=2):
    unit = Mock()
    unit.position = Point2((x, y))
    unit.health = health
    unit.supply_cost = supply_cost
    return unit


class TestGetCenterPosition:
    def test_empty_returns_origin(self):
        assert get_center_position([]) == Point2((0, 0))

    def test_single_unit_returns_its_position(self):
        unit = make_unit(5, 7)
        assert get_center_position([unit]) == Point2((5, 7))

    def test_multiple_units_average(self):
        units = [make_unit(0, 0), make_unit(10, 0), make_unit(5, 10)]
        center = get_center_position(units)
        assert center.x == 5
        assert abs(center.y - 10 / 3) < 1e-9


class TestGetWeightedCenter:
    def test_health_weighted_pulls_toward_high_health_unit(self):
        units = [make_unit(0, 0, health=1), make_unit(10, 0, health=99)]
        center = get_weighted_center(units, weight_by_health=True)
        assert center.x > 5

    def test_supply_weighted_pulls_toward_high_supply_unit(self):
        units = [make_unit(0, 0, supply_cost=1), make_unit(10, 0, supply_cost=9)]
        center = get_weighted_center(units, weight_by_supply=True)
        assert center.x > 5

    def test_falls_back_to_geometric_center_when_no_weighting(self):
        units = [make_unit(0, 0), make_unit(10, 0)]
        assert get_weighted_center(units) == get_center_position(units)

    def test_zero_total_health_falls_back(self):
        units = [make_unit(0, 0, health=0), make_unit(10, 0, health=0)]
        center = get_weighted_center(units, weight_by_health=True)
        assert center == get_center_position(units)


class TestGetClosestFurthestUnit:
    def test_closest_unit_from_list(self):
        units = [make_unit(0, 0), make_unit(100, 0)]
        closest = get_closest_unit(units, Point2((1, 0)))
        assert closest is units[0]

    def test_furthest_unit_from_list(self):
        units = [make_unit(0, 0), make_unit(100, 0)]
        furthest = get_furthest_unit(units, Point2((1, 0)))
        assert furthest is units[1]

    def test_empty_returns_none(self):
        assert get_closest_unit([], Point2((0, 0))) is None
        assert get_furthest_unit([], Point2((0, 0))) is None


class TestDistanceAndSpread:
    def test_average_distance(self):
        units = [make_unit(0, 0), make_unit(10, 0)]
        assert get_average_distance(units, Point2((0, 0))) == 5.0

    def test_spread_radius_single_unit_is_zero(self):
        assert get_spread_radius([make_unit(0, 0)]) == 0.0

    def test_spread_radius_multiple_units(self):
        units = [make_unit(-5, 0), make_unit(5, 0)]
        assert get_spread_radius(units) == 5.0


class TestIsPositionSafe:
    def test_safe_when_no_enemies(self):
        assert is_position_safe(Point2((0, 0)), []) is True

    def test_unsafe_when_enemy_within_range(self):
        enemies = [make_unit(5, 0)]
        assert is_position_safe(Point2((0, 0)), enemies, safe_distance=10.0) is False

    def test_safe_when_enemy_outside_range(self):
        enemies = [make_unit(50, 0)]
        assert is_position_safe(Point2((0, 0)), enemies, safe_distance=10.0) is True


class TestGetBoundingBox:
    def test_bounding_box_of_units(self):
        units = [make_unit(-3, 2), make_unit(4, -1)]
        min_corner, max_corner = get_bounding_box(units)
        assert min_corner == Point2((-3, -1))
        assert max_corner == Point2((4, 2))

    def test_bounding_box_empty(self):
        min_corner, max_corner = get_bounding_box([])
        assert min_corner == Point2((0, 0))
        assert max_corner == Point2((0, 0))


class TestCommonHelpersWrappers:
    """
    combat_manager.py imports centroid/closest_enemy/filter_by_type/units_amount
    from utils.common_helpers and gates their use behind HELPERS_AVAILABLE. These
    names did not exist previously, so the import silently raised ImportError and
    HELPERS_AVAILABLE was always False -- this test locks in that the import now
    succeeds and each function matches the behavior of the previous fallback code.
    """

    def test_import_succeeds(self):
        from utils.common_helpers import (
            centroid,
            closest_enemy,
            filter_by_type,
            units_amount,
        )

        assert callable(centroid)
        assert callable(closest_enemy)
        assert callable(filter_by_type)
        assert callable(units_amount)

    def test_centroid_matches_get_center_position(self):
        from utils.common_helpers import centroid

        units = [make_unit(0, 0), make_unit(10, 0), make_unit(5, 10)]
        assert centroid(units) == get_center_position(units)

    def test_centroid_empty_returns_none(self):
        from utils.common_helpers import centroid

        assert centroid([]) is None

    def test_closest_enemy_returns_nearest(self):
        from utils.common_helpers import closest_enemy

        unit = make_unit(0, 0)
        enemies = [make_unit(100, 0), make_unit(1, 0)]
        assert closest_enemy(unit, enemies) is enemies[1]

    def test_closest_enemy_empty_returns_none(self):
        from utils.common_helpers import closest_enemy

        assert closest_enemy(make_unit(0, 0), []) is None

    def test_filter_by_type_list_fallback(self):
        from utils.common_helpers import filter_by_type

        zergling = make_unit(0, 0)
        zergling.type_id = Mock()
        zergling.type_id.name = "ZERGLING"
        roach = make_unit(1, 1)
        roach.type_id = Mock()
        roach.type_id.name = "ROACH"

        result = filter_by_type([zergling, roach], {"ZERGLING"})
        assert result == [zergling]

    def test_units_amount(self):
        from utils.common_helpers import units_amount

        assert units_amount([make_unit(0, 0), make_unit(1, 1)]) == 2
        assert units_amount([]) == 0
