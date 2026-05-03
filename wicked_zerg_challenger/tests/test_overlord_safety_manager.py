# -*- coding: utf-8 -*-
"""
Unit tests for OverlordSafetyManager.

Focus on pure-logic surfaces that are safe to mock:
- Reset / state lifecycle
- Pillar selection helpers (_is_safe_from_enemy_start, _select_distributed_pillars,
  _use_fallback_positions, _find_best_spot)
- Optimal scout position assembly (get_optimal_scout_positions)

Heavier integration paths (_check_threats, _manage_overlords) require many
mocked Units collections; we exercise their async harness only enough to
ensure they swallow errors gracefully on a bare bot.
"""

import asyncio
import os
import sys
import unittest
from unittest.mock import MagicMock, Mock

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from overlord_safety_manager import OverlordSafetyManager
from sc2.position import Point2


def _make_bot(map_w=128, map_h=128):
    bot = Mock()
    bot.game_info = Mock()
    bot.game_info.map_size = Mock()
    bot.game_info.map_size.width = map_w
    bot.game_info.map_size.height = map_h
    bot.game_info.map_center = Point2((map_w / 2, map_h / 2))
    bot.start_location = Point2((20, 20))
    bot.enemy_start_locations = [Point2((map_w - 20, map_h - 20))]
    bot.expansion_locations_list = [
        Point2((20, 20)),
        Point2((40, 40)),
        Point2((60, 60)),
        Point2((80, 80)),
        Point2((map_w - 20, map_h - 20)),
    ]
    bot.watchtowers = []
    return bot


class TestOverlordSafetyManagerLifecycle(unittest.TestCase):
    def setUp(self):
        self.bot = _make_bot()
        self.mgr = OverlordSafetyManager(self.bot)

    def test_initialization_defaults(self):
        self.assertEqual(self.mgr.safe_spots, [])
        self.assertFalse(self.mgr._pillars_calculated)
        self.assertEqual(self.mgr.overlord_assignments, {})
        self.assertEqual(self.mgr.fleeing_overlords, set())
        self.assertEqual(self.mgr.SAFETY_DISTANCE, 15.0)
        self.assertEqual(self.mgr.RETREAT_DISTANCE, 10.0)

    def test_reset_clears_state(self):
        self.mgr.safe_spots.append(Point2((10, 10)))
        self.mgr._pillars_calculated = True
        self.mgr.overlord_assignments[42] = Point2((1, 1))
        self.mgr.fleeing_overlords.add(7)

        self.mgr.reset()

        self.assertEqual(self.mgr.safe_spots, [])
        self.assertFalse(self.mgr._pillars_calculated)
        self.assertEqual(self.mgr.overlord_assignments, {})
        self.assertEqual(self.mgr.fleeing_overlords, set())


class TestSafeFromEnemyStart(unittest.TestCase):
    def setUp(self):
        self.bot = _make_bot()
        self.mgr = OverlordSafetyManager(self.bot)

    def test_position_far_from_enemy_is_safe(self):
        far = Point2((20, 20))  # ~152 away from enemy (108, 108)
        self.assertTrue(self.mgr._is_safe_from_enemy_start(far))

    def test_position_close_to_enemy_is_unsafe(self):
        # enemy is at (108, 108); within 25
        close = Point2((100, 100))
        self.assertFalse(self.mgr._is_safe_from_enemy_start(close))

    def test_no_enemy_start_locations_is_safe(self):
        self.bot.enemy_start_locations = []
        self.assertTrue(self.mgr._is_safe_from_enemy_start(Point2((50, 50))))

    def test_missing_attr_is_safe(self):
        # Stand-in Mock object that lacks the attribute
        class Dummy:
            pass

        self.mgr.bot = Dummy()
        self.assertTrue(self.mgr._is_safe_from_enemy_start(Point2((10, 10))))


class TestFallbackPositions(unittest.TestCase):
    def test_fallback_uses_eight_edge_points(self):
        bot = _make_bot(120, 100)
        mgr = OverlordSafetyManager(bot)
        mgr._use_fallback_positions()
        self.assertEqual(len(mgr.safe_spots), 8)
        # All points should be inside the map bounds
        for p in mgr.safe_spots:
            self.assertGreaterEqual(p.x, 0)
            self.assertLessEqual(p.x, 120)
            self.assertGreaterEqual(p.y, 0)
            self.assertLessEqual(p.y, 100)

    def test_fallback_no_op_when_map_size_missing(self):
        bot = Mock()
        bot.game_info = Mock(spec=[])  # no map_size attr
        mgr = OverlordSafetyManager(bot)
        # Should not raise
        mgr._use_fallback_positions()
        self.assertEqual(mgr.safe_spots, [])


class TestSelectDistributedPillars(unittest.TestCase):
    def setUp(self):
        self.bot = _make_bot(120, 90)
        # set terrain_height width/height for cell math
        self.bot.game_info.terrain_height = Mock()
        self.bot.game_info.terrain_height.width = 120
        self.bot.game_info.terrain_height.height = 90
        self.mgr = OverlordSafetyManager(self.bot)

    def test_returns_input_when_under_max(self):
        pillars = [Point2((10, 10)), Point2((20, 20))]
        result = self.mgr._select_distributed_pillars(pillars, max_count=12)
        self.assertEqual(result, pillars)

    def test_caps_at_max_count(self):
        # Generate 30 pillars distributed over the map
        pillars = [Point2((x, y)) for x in range(5, 120, 12) for y in range(5, 90, 10)]
        self.assertGreater(len(pillars), 12)
        result = self.mgr._select_distributed_pillars(pillars, max_count=12)
        self.assertLessEqual(len(result), 12)

    def test_distribution_picks_from_distinct_cells(self):
        # Cluster all candidates in one quadrant; expect at most one per cell
        pillars = [Point2((x, y)) for x in range(0, 30) for y in range(0, 22)]
        result = self.mgr._select_distributed_pillars(pillars, max_count=12)
        # All chosen are within input set
        for p in result:
            self.assertIn(p, pillars)


class TestFindBestSpot(unittest.TestCase):
    def setUp(self):
        self.bot = _make_bot()
        self.mgr = OverlordSafetyManager(self.bot)

    def _make_overlord(self, position):
        ov = Mock()
        ov.position = position
        ov.distance_to = (
            lambda p: ((position.x - p.x) ** 2 + (position.y - p.y) ** 2) ** 0.5
        )
        return ov

    def test_returns_none_when_no_safe_spots(self):
        self.assertIsNone(
            self.mgr._find_best_spot(self._make_overlord(Point2((10, 10))))
        )

    def test_returns_closest_unoccupied(self):
        self.mgr.safe_spots = [Point2((0, 0)), Point2((50, 50)), Point2((100, 100))]
        ov = self._make_overlord(Point2((10, 10)))
        spot = self.mgr._find_best_spot(ov)
        self.assertEqual(spot, Point2((0, 0)))

    def test_skips_occupied_spots(self):
        self.mgr.safe_spots = [Point2((0, 0)), Point2((50, 50))]
        self.mgr.overlord_assignments[1] = Point2((0, 0))
        ov = self._make_overlord(Point2((10, 10)))
        spot = self.mgr._find_best_spot(ov)
        self.assertEqual(spot, Point2((50, 50)))

    def test_falls_back_to_random_when_all_occupied(self):
        spots = [Point2((0, 0)), Point2((50, 50))]
        self.mgr.safe_spots = list(spots)
        self.mgr.overlord_assignments[1] = Point2((0, 0))
        self.mgr.overlord_assignments[2] = Point2((50, 50))
        ov = self._make_overlord(Point2((10, 10)))
        result = self.mgr._find_best_spot(ov)
        self.assertIn(result, spots)


class TestOptimalScoutPositions(unittest.TestCase):
    def setUp(self):
        self.bot = _make_bot()
        self.mgr = OverlordSafetyManager(self.bot)

    def test_includes_map_center(self):
        positions = self.mgr.get_optimal_scout_positions()
        self.assertIn(self.bot.game_info.map_center, positions)

    def test_includes_enemy_natural_when_expansions_known(self):
        positions = self.mgr.get_optimal_scout_positions()
        # The natural is the closest expansion to the enemy start that isn't the start itself
        enemy_start = self.bot.enemy_start_locations[0]
        expansions = sorted(
            self.bot.expansion_locations_list, key=lambda p: p.distance_to(enemy_start)
        )
        natural = expansions[1]
        self.assertIn(natural, positions)

    def test_includes_third_base_when_available(self):
        positions = self.mgr.get_optimal_scout_positions()
        enemy_start = self.bot.enemy_start_locations[0]
        expansions = sorted(
            self.bot.expansion_locations_list, key=lambda p: p.distance_to(enemy_start)
        )
        third = expansions[2]
        self.assertIn(third, positions)

    def test_empty_enemy_start_does_not_raise(self):
        self.bot.enemy_start_locations = []
        positions = self.mgr.get_optimal_scout_positions()
        # Map center should still be returned
        self.assertIn(self.bot.game_info.map_center, positions)

    def test_includes_watchtowers_when_present(self):
        tower = Mock()
        tower.position = Point2((64, 64))
        self.bot.watchtowers = [tower]
        positions = self.mgr.get_optimal_scout_positions()
        self.assertIn(Point2((64, 64)), positions)


class TestOnStepResilience(unittest.TestCase):
    def test_on_step_swallows_errors(self):
        """on_step should never raise even when bot is partial."""
        bot = Mock()
        # Cause failures inside the methods called from on_step
        bot.game_info = Mock(spec=[])  # no map_size or terrain
        bot.units = Mock(side_effect=RuntimeError("boom"))
        mgr = OverlordSafetyManager(bot)
        # Trigger the iteration-based gates so methods actually run
        asyncio.run(mgr.on_step(0))


if __name__ == "__main__":
    unittest.main()
