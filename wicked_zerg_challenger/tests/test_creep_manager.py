# -*- coding: utf-8 -*-
"""
Unit tests for CreepManager pure-logic surfaces.

We focus on the deterministic helpers and skip the heavy on_step /
_update_creep_coverage paths (those need a fully-mocked SC2 bot with
pathing_grid arrays).

Covered:
- Class-level constants
- __init__ defaults
- _get_direction_target: enemy_start preferred, map_center fallback
- _get_expansion_targets / _get_scout_targets: aggregation
- _get_base_perimeter_targets: 6 angular points per townhall at radius 12
- _dedupe_positions: removes near-duplicates within 2.5 tiles
- _score_target: along-direction beats perpendicular; degenerate dir
- get_creep_target: cached_targets path returns highest-scoring candidate
- get_tumor_count: counts the three tumor types
"""

import os
import sys
import unittest
from unittest.mock import Mock

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from creep_manager import CreepManager
from sc2.ids.unit_typeid import UnitTypeId
from sc2.position import Point2


def _struct(type_id, position=Point2((0, 0))):
    s = Mock()
    s.type_id = type_id
    s.position = position
    s.tag = id(s)
    return s


class TestConstants(unittest.TestCase):
    def test_constants(self):
        self.assertEqual(CreepManager.TUMOR_MIN_SPACING_DIST, 10)
        self.assertEqual(CreepManager.TUMOR_SPREAD_RANGE, 10.0)
        self.assertEqual(CreepManager.QUEEN_TUMOR_RANGE, 8.0)
        self.assertEqual(CreepManager.EXPANSION_BLOCK_DIST, 3)
        self.assertAlmostEqual(CreepManager.COVERAGE_TARGET, 0.30)
        self.assertEqual(CreepManager.COVERAGE_SAMPLE_STEP, 15)


class TestInitDefaults(unittest.TestCase):
    def test_defaults(self):
        bot = Mock()
        m = CreepManager(bot)
        self.assertEqual(m.last_update, 0)
        self.assertEqual(m.update_interval, 10)
        self.assertEqual(m.tumor_relay_interval, 6)
        self.assertEqual(m.cached_targets, [])
        self.assertEqual(m.used_tumor_tags, set())
        self.assertEqual(m.max_tumors_per_cycle, 6)
        self.assertEqual(m._creep_coverage, 0.0)


class TestDirectionTarget(unittest.TestCase):
    def test_prefers_enemy_start(self):
        bot = Mock()
        bot.enemy_start_locations = [Point2((100, 100))]
        m = CreepManager(bot)
        self.assertEqual(m._get_direction_target(), Point2((100, 100)))

    def test_falls_back_to_map_center(self):
        bot = Mock()
        bot.enemy_start_locations = []
        bot.game_info = Mock()
        bot.game_info.map_center = Point2((50, 50))
        m = CreepManager(bot)
        self.assertEqual(m._get_direction_target(), Point2((50, 50)))

    def test_no_data_returns_none(self):
        bot = Mock(spec=[])
        m = CreepManager(bot)
        self.assertIsNone(m._get_direction_target())


class TestExpansionTargets(unittest.TestCase):
    def test_returns_list_copy(self):
        bot = Mock()
        bot.expansion_locations_list = [Point2((1, 1)), Point2((2, 2))]
        m = CreepManager(bot)
        result = m._get_expansion_targets()
        self.assertEqual(len(result), 2)
        # Should be a list, not the underlying object
        self.assertIsInstance(result, list)

    def test_empty_when_no_data(self):
        bot = Mock(spec=[])
        m = CreepManager(bot)
        self.assertEqual(m._get_expansion_targets(), [])


class TestScoutTargets(unittest.TestCase):
    def test_aggregates_cached_and_overlord_assignments(self):
        bot = Mock()
        scout = Mock()
        scout.cached_positions = [Point2((10, 10))]
        scout.overlord_assignments = {1: Point2((20, 20)), 2: Point2((30, 30))}
        bot.scout = scout
        m = CreepManager(bot)
        targets = m._get_scout_targets()
        self.assertEqual(len(targets), 3)

    def test_no_scout_returns_empty(self):
        bot = Mock(spec=[])
        m = CreepManager(bot)
        self.assertEqual(m._get_scout_targets(), [])


class TestBasePerimeterTargets(unittest.TestCase):
    def test_six_angular_points_per_townhall(self):
        bot = Mock()
        th1 = _struct(UnitTypeId.HATCHERY, Point2((50, 50)))
        bot.townhalls = [th1]
        m = CreepManager(bot)
        targets = m._get_base_perimeter_targets()
        # 360 / 60 = 6 angular positions
        self.assertEqual(len(targets), 6)
        # Each should be ~12 tiles from base center
        for p in targets:
            d = ((p.x - 50) ** 2 + (p.y - 50) ** 2) ** 0.5
            self.assertAlmostEqual(d, 12.0, delta=0.01)

    def test_no_townhalls_returns_empty(self):
        bot = Mock()
        bot.townhalls = []
        m = CreepManager(bot)
        self.assertEqual(m._get_base_perimeter_targets(), [])


class TestDedupePositions(unittest.TestCase):
    # Note: Point2((0, 0)) is falsy because it inherits tuple.__bool__,
    # so the dedupe drops it. Tests use non-origin coordinates.

    def test_keeps_distinct(self):
        positions = [Point2((5, 5)), Point2((10, 10)), Point2((20, 20))]
        result = CreepManager._dedupe_positions(positions)
        self.assertEqual(len(result), 3)

    def test_drops_near_duplicates(self):
        positions = [Point2((5, 5)), Point2((6, 6)), Point2((20, 20))]
        result = CreepManager._dedupe_positions(positions)
        self.assertEqual(len(result), 2)

    def test_filters_none(self):
        positions = [Point2((5, 5)), None, Point2((20, 20))]
        result = CreepManager._dedupe_positions(positions)
        self.assertEqual(len(result), 2)

    def test_filters_origin_as_falsy(self):
        # Documents the current behavior: Point2((0,0)) is falsy and dropped.
        positions = [Point2((0, 0)), Point2((10, 10))]
        result = CreepManager._dedupe_positions(positions)
        self.assertEqual(result, [Point2((10, 10))])


class TestScoreTarget(unittest.TestCase):
    def test_zero_direction_returns_distance(self):
        origin = Point2((0, 0))
        candidate = Point2((3, 4))
        self.assertEqual(CreepManager._score_target(origin, candidate, origin), 5.0)

    def test_along_direction_higher_than_perpendicular(self):
        origin = Point2((0, 0))
        direction = Point2((10, 0))
        aligned = Point2((5, 0))
        perp = Point2((0, 5))
        self.assertGreater(
            CreepManager._score_target(origin, aligned, direction),
            CreepManager._score_target(origin, perp, direction),
        )


class TestGetCreepTarget(unittest.TestCase):
    def test_falsy_origin_returns_none(self):
        # Point2((0,0)) is falsy, so an origin at the origin makes
        # get_creep_target short-circuit. Documents that fact.
        bot = Mock()
        bot.enemy_start_locations = [Point2((100, 0))]
        m = CreepManager(bot)
        m.cached_targets = [Point2((10, 10))]
        u = Mock()
        u.position = Point2((0, 0))
        self.assertIsNone(m.get_creep_target(u))

    def test_returns_best_scored_candidate(self):
        bot = Mock()
        bot.enemy_start_locations = [Point2((100, 50))]
        m = CreepManager(bot)
        m.cached_targets = [Point2((50, 50)), Point2((10, 90))]  # along vs perp
        u = Mock()
        u.position = Point2((10, 50))
        result = m.get_creep_target(u)
        # The (50, 50) candidate is along enemy direction, should win
        self.assertEqual(result, Point2((50, 50)))

    def test_no_cached_targets_offsets_toward_direction(self):
        bot = Mock()
        bot.enemy_start_locations = [Point2((100, 50))]
        bot.scout = None
        bot.expansion_locations_list = None
        bot.townhalls = []
        bot.creep_highway_astar = None
        m = CreepManager(bot)
        u = Mock()
        u.position = Point2((10, 50))  # non-origin, truthy
        result = m.get_creep_target(u)
        self.assertIsNotNone(result)


class TestGetTumorCount(unittest.TestCase):
    def test_no_structures_returns_zero(self):
        bot = Mock(spec=[])
        m = CreepManager(bot)
        self.assertEqual(m.get_tumor_count(), 0)

    def test_counts_only_tumor_types(self):
        bot = Mock()
        bot.structures = [
            _struct(UnitTypeId.CREEPTUMOR),
            _struct(UnitTypeId.CREEPTUMORBURROWED),
            _struct(UnitTypeId.CREEPTUMORQUEEN),
            _struct(UnitTypeId.HATCHERY),
        ]
        m = CreepManager(bot)
        self.assertEqual(m.get_tumor_count(), 3)


if __name__ == "__main__":
    unittest.main()
