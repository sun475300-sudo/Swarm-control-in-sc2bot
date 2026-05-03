# -*- coding: utf-8 -*-
"""
Unit tests for building_placement_helper.

Covers:
- Module-level constants (CREEP_REQUIRED, CREEP_NOT_REQUIRED partitioning)
- requires_creep / can_build_off_creep
- Module-level is_too_close_to_resources: minerals, geyser, gas building
- BuildingPlacementHelper.has_creep delegation to bot.has_creep
- BuildingPlacementHelper.is_too_close_to_resources (instance method)
- find_creep_positions: spiral search hits creep on the disk; respects
  max_candidates; returns empty when no creep at all
- get_closest_creep_position: prefers points beyond min_distance
"""

import os
import sys
import unittest
from unittest.mock import Mock

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from building_placement_helper import (
    CREEP_NOT_REQUIRED,
    CREEP_REQUIRED,
    BuildingPlacementHelper,
    can_build_off_creep,
    is_too_close_to_resources,
    requires_creep,
)
from sc2.ids.unit_typeid import UnitTypeId
from sc2.position import Point2


def _resource(position):
    r = Mock()
    r.position = position
    return r


def _bot_with_resources(
    minerals=None, geysers=None, gas_buildings=None, map_size=(200, 200)
):
    bot = Mock()
    bot.mineral_field = list(minerals or [])
    bot.vespene_geyser = list(geysers or [])
    bot.gas_buildings = list(gas_buildings or [])
    bot.game_info = Mock()
    bot.game_info.map_size = Mock()
    bot.game_info.map_size.x = map_size[0]
    bot.game_info.map_size.y = map_size[1]
    return bot


class TestModuleConstants(unittest.TestCase):
    def test_creep_required_subset(self):
        for tid in (
            UnitTypeId.SPAWNINGPOOL,
            UnitTypeId.EVOLUTIONCHAMBER,
            UnitTypeId.SPINECRAWLER,
            UnitTypeId.SPORECRAWLER,
            UnitTypeId.HYDRALISKDEN,
            UnitTypeId.SPIRE,
        ):
            self.assertIn(tid, CREEP_REQUIRED)

    def test_creep_not_required_subset(self):
        for tid in (
            UnitTypeId.HATCHERY,
            UnitTypeId.LAIR,
            UnitTypeId.HIVE,
            UnitTypeId.EXTRACTOR,
        ):
            self.assertIn(tid, CREEP_NOT_REQUIRED)

    def test_partitioning_is_disjoint(self):
        self.assertFalse(CREEP_REQUIRED & CREEP_NOT_REQUIRED)


class TestRequiresCreep(unittest.TestCase):
    def test_creep_buildings(self):
        self.assertTrue(requires_creep(UnitTypeId.SPAWNINGPOOL))
        self.assertTrue(requires_creep(UnitTypeId.SPORECRAWLER))

    def test_non_creep_buildings(self):
        self.assertFalse(requires_creep(UnitTypeId.HATCHERY))
        self.assertFalse(requires_creep(UnitTypeId.EXTRACTOR))


class TestCanBuildOffCreep(unittest.TestCase):
    def test_townhalls_and_extractor(self):
        self.assertTrue(can_build_off_creep(UnitTypeId.HATCHERY))
        self.assertTrue(can_build_off_creep(UnitTypeId.EXTRACTOR))

    def test_creep_buildings(self):
        self.assertFalse(can_build_off_creep(UnitTypeId.SPAWNINGPOOL))


class TestIsTooCloseToResources(unittest.TestCase):
    def test_no_resources_returns_false(self):
        bot = _bot_with_resources()
        self.assertFalse(is_too_close_to_resources(Point2((50, 50)), bot))

    def test_close_to_mineral_returns_true(self):
        bot = _bot_with_resources(minerals=[_resource(Point2((10, 10)))])
        self.assertTrue(
            is_too_close_to_resources(Point2((11, 11)), bot, min_distance=3.0)
        )

    def test_far_from_mineral_returns_false(self):
        bot = _bot_with_resources(minerals=[_resource(Point2((10, 10)))])
        self.assertFalse(
            is_too_close_to_resources(Point2((50, 50)), bot, min_distance=3.0)
        )

    def test_close_to_geyser_returns_true(self):
        bot = _bot_with_resources(geysers=[_resource(Point2((20, 20)))])
        self.assertTrue(
            is_too_close_to_resources(Point2((21, 20)), bot, min_distance=3.0)
        )

    def test_close_to_extractor_returns_true(self):
        bot = _bot_with_resources(gas_buildings=[_resource(Point2((30, 30)))])
        self.assertTrue(
            is_too_close_to_resources(Point2((30, 31)), bot, min_distance=3.0)
        )

    def test_swallows_exception(self):
        bad = Mock()

        # Iterating raises
        class _Iter:
            def __iter__(self):
                raise RuntimeError("boom")

        bad.mineral_field = _Iter()
        # Should be safe because of try/except
        self.assertFalse(is_too_close_to_resources(Point2((10, 10)), bad))

    def test_custom_min_distance(self):
        bot = _bot_with_resources(minerals=[_resource(Point2((10, 10)))])
        # Distance is 5 — within 6 but outside 4
        candidate = Point2((14, 13))  # ~5
        self.assertFalse(is_too_close_to_resources(candidate, bot, min_distance=4.0))
        self.assertTrue(is_too_close_to_resources(candidate, bot, min_distance=6.0))


class TestHelperHasCreep(unittest.TestCase):
    def test_delegates_to_bot_has_creep(self):
        bot = Mock()
        bot.has_creep = Mock(return_value=True)
        helper = BuildingPlacementHelper(bot)
        self.assertTrue(helper.has_creep(Point2((10, 10))))
        bot.has_creep.return_value = False
        self.assertFalse(helper.has_creep(Point2((10, 10))))

    def test_no_has_creep_returns_false(self):
        bot = Mock(spec=[])
        helper = BuildingPlacementHelper(bot)
        self.assertFalse(helper.has_creep(Point2((10, 10))))

    def test_swallows_exception(self):
        bot = Mock()
        bot.has_creep = Mock(side_effect=RuntimeError("boom"))
        helper = BuildingPlacementHelper(bot)
        self.assertFalse(helper.has_creep(Point2((10, 10))))


class TestHelperIsTooCloseToResources(unittest.TestCase):
    def test_close_to_mineral(self):
        bot = _bot_with_resources(minerals=[_resource(Point2((10, 10)))])
        helper = BuildingPlacementHelper(bot)
        self.assertTrue(helper.is_too_close_to_resources(Point2((11, 10)), 3.0))

    def test_far_from_mineral(self):
        bot = _bot_with_resources(minerals=[_resource(Point2((10, 10)))])
        helper = BuildingPlacementHelper(bot)
        self.assertFalse(helper.is_too_close_to_resources(Point2((50, 50)), 3.0))


class TestFindCreepPositions(unittest.TestCase):
    def test_no_creep_returns_empty(self):
        bot = _bot_with_resources()
        bot.has_creep = Mock(return_value=False)
        helper = BuildingPlacementHelper(bot)
        positions = helper.find_creep_positions(Point2((50, 50)), search_radius=10.0)
        self.assertEqual(positions, [])

    def test_creep_everywhere_finds_max_candidates(self):
        bot = _bot_with_resources()
        bot.has_creep = Mock(return_value=True)
        helper = BuildingPlacementHelper(bot)
        positions = helper.find_creep_positions(
            Point2((100, 100)), search_radius=10.0, max_candidates=5
        )
        self.assertEqual(len(positions), 5)

    def test_includes_center_when_on_creep(self):
        bot = _bot_with_resources()
        bot.has_creep = Mock(return_value=True)
        helper = BuildingPlacementHelper(bot)
        positions = helper.find_creep_positions(
            Point2((100, 100)), search_radius=4.0, max_candidates=20
        )
        self.assertIn(Point2((100, 100)), positions)

    def test_excludes_out_of_map(self):
        bot = _bot_with_resources(map_size=(50, 50))
        bot.has_creep = Mock(return_value=True)
        helper = BuildingPlacementHelper(bot)
        # Searching from a point near the edge — no result with x or y > 50
        positions = helper.find_creep_positions(
            Point2((48, 48)), search_radius=10.0, max_candidates=50
        )
        for p in positions:
            self.assertGreaterEqual(p.x, 0)
            self.assertLess(p.x, 50)
            self.assertGreaterEqual(p.y, 0)
            self.assertLess(p.y, 50)


class TestGetClosestCreepPosition(unittest.TestCase):
    def test_no_creep_returns_none(self):
        bot = _bot_with_resources()
        bot.has_creep = Mock(return_value=False)
        helper = BuildingPlacementHelper(bot)
        self.assertIsNone(
            helper.get_closest_creep_position(Point2((100, 100)), min_distance=5)
        )

    def test_returns_position_beyond_min_distance(self):
        bot = _bot_with_resources()
        bot.has_creep = Mock(return_value=True)
        helper = BuildingPlacementHelper(bot)
        result = helper.get_closest_creep_position(Point2((100, 100)), min_distance=4.0)
        self.assertIsNotNone(result)
        self.assertGreaterEqual(result.distance_to(Point2((100, 100))), 4.0 - 1e-6)


if __name__ == "__main__":
    unittest.main()
