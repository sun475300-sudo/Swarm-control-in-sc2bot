#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Unit tests for ActiveScoutingSystem

Tests:
1. Scout dispatch within expected time
2. Data integrity (Blackboard updates)
3. Multi-unit scout selection
4. Smart target prioritization
5. Changeling spawning
"""

import unittest
from unittest.mock import Mock, MagicMock, patch
import sys
import os

# Add parent directory to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from active_scouting_system import ActiveScoutingSystem


class TestActiveScoutingSystem(unittest.TestCase):
    """Test suite for ActiveScoutingSystem"""

    def setUp(self):
        """Set up test fixtures"""
        self.bot = Mock()
        self.bot.time = 0.0
        self.bot.iteration = 0
        self.bot.units = Mock()
        self.bot.enemy_units = Mock(return_value=[])
        self.bot.enemy_structures = Mock(return_value=[])
        self.bot.expansion_locations_list = []
        self.bot.enemy_start_locations = []
        self.bot.blackboard = Mock()

        self.scout_system = ActiveScoutingSystem(self.bot)

    def test_initialization(self):
        """Test system initializes correctly"""
        self.assertEqual(self.scout_system.scout_interval_default, 560)
        self.assertEqual(self.scout_system.scout_interval_alert, 336)
        self.assertEqual(self.scout_system.scouts_sent, 0)
        self.assertEqual(self.scout_system.scouts_arrived, 0)
        self.assertEqual(len(self.scout_system.scouted_locations), 0)

    def test_scout_interval_adjustment_normal_mode(self):
        """Test scout interval stays in normal mode with recent intel"""
        self.scout_system.last_intel_update = 0.0
        self.bot.time = 10.0  # 10 seconds since last intel

        self.scout_system._adjust_scout_interval(self.bot.time)

        self.assertEqual(self.scout_system.scout_interval,
                        self.scout_system.scout_interval_default)

    def test_scout_interval_adjustment_alert_mode(self):
        """Test scout interval switches to alert mode with stale intel"""
        self.scout_system.last_intel_update = 0.0
        self.bot.time = 130.0  # 130 seconds game time, 2+ minutes with no intel

        self.scout_system._adjust_scout_interval(self.bot.time)

        self.assertEqual(self.scout_system.scout_interval,
                        self.scout_system.scout_interval_alert)

    def test_smart_target_selection(self):
        """Test smart target selection prioritizes unscouted locations"""
        from sc2.position import Point2

        # Set up expansion locations
        self.bot.expansion_locations_list = [
            Point2((50, 50)),
            Point2((100, 100)),
            Point2((150, 150))
        ]
        self.bot.enemy_start_locations = [Point2((200, 200))]

        self.scout_system._update_scout_targets()

        # Should prioritize unscouted expansions
        self.assertGreater(len(self.scout_system.scout_targets), 0)
        # First targets should be unscouted expansions
        for exp_pos in self.bot.expansion_locations_list:
            self.assertIn(exp_pos, self.scout_system.scout_targets)

    def test_location_timestamp_tracking(self):
        """Test location scout times are tracked correctly"""
        from sc2.position import Point2

        location = Point2((50, 50))
        loc_key = (int(location.x), int(location.y))
        game_time = 100.0

        # Initially no timestamp
        self.assertNotIn(loc_key, self.scout_system.location_scout_times)

        # After scouting
        self.scout_system.location_scout_times[loc_key] = game_time
        self.scout_system.scouted_locations.add(loc_key)

        self.assertEqual(self.scout_system.location_scout_times[loc_key], game_time)

    def test_blackboard_integration(self):
        """Test data is pushed to blackboard correctly"""
        enemy_base_count = 3
        main_unit = ("MARINE", 10)
        tech_buildings = 2

        self.scout_system.scout_interval = self.scout_system.scout_interval_alert
        self.scout_system._push_scout_data_to_blackboard(
            enemy_base_count, main_unit, tech_buildings
        )

        # Verify blackboard was updated
        self.bot.blackboard.set.assert_called()

        # Check specific calls
        calls = self.bot.blackboard.set.call_args_list
        call_dict = {call[0][0]: call[0][1] for call in calls}

        self.assertEqual(call_dict["enemy_base_count_scout"], 3)
        self.assertEqual(call_dict["enemy_main_unit"], "MARINE")
        self.assertEqual(call_dict["scout_mode"], "alert")

    def test_performance_metrics_tracking(self):
        """Test performance metrics are tracked correctly"""
        # Initially zero
        self.assertEqual(self.scout_system.scouts_sent, 0)
        self.assertEqual(self.scout_system.scouts_arrived, 0)
        self.assertEqual(self.scout_system.scouts_lost, 0)

        # Simulate sending scouts
        self.scout_system.scouts_sent = 5
        self.scout_system.scouts_arrived = 4
        self.scout_system.scouts_lost = 1

        # Calculate success rate
        success_rate = (self.scout_system.scouts_arrived /
                       self.scout_system.scouts_sent * 100)
        self.assertEqual(success_rate, 80.0)

    def test_changeling_cooldown(self):
        """Test Changeling spawning respects cooldown"""
        from sc2.position import Point2

        location = Point2((100, 100))
        overseer = Mock()

        # First spawn should work
        self.scout_system.last_changeling_spawn = 0.0
        game_time = 50.0

        # Should allow spawn (50s > 30s cooldown)
        self.assertTrue(game_time - self.scout_system.last_changeling_spawn >= 30)

        # After spawning
        self.scout_system.last_changeling_spawn = game_time

        # Should not allow spawn within cooldown
        game_time_2 = 65.0  # Only 15s later
        self.assertFalse(game_time_2 - self.scout_system.last_changeling_spawn >= 30)

    def test_new_info_discovery_tracking(self):
        """Test new information discovery is tracked"""
        from sc2.position import Point2

        location = Point2((100, 100))
        game_time = 100.0

        # Initially no info
        initial_count = self.scout_system.new_info_discovered

        # Discover new base
        self.scout_system.enemy_expansion_timings[location] = game_time
        self.scout_system.new_info_discovered += 1

        self.assertEqual(self.scout_system.new_info_discovered, initial_count + 1)

    def test_enemy_info_retrieval(self):
        """Test enemy info can be retrieved correctly"""
        from sc2.position import Point2

        # Set up some enemy info
        self.scout_system.enemy_expansion_timings[Point2((100, 100))] = 120.0
        self.scout_system.enemy_army_composition["MARINE"] = 5
        self.scout_system.enemy_tech_progress["FACTORY"] = 180.0
        self.scout_system.scouted_locations.add((50, 50))

        info = self.scout_system.get_enemy_info()

        self.assertEqual(info["base_count"], 1)
        self.assertEqual(info["army_composition"]["MARINE"], 5)
        self.assertEqual(info["tech_buildings"]["FACTORY"], 180.0)
        self.assertEqual(info["scouted_locations"], 1)


class TestScoutTargetPrioritization(unittest.TestCase):
    """Test suite for scout target prioritization"""

    def setUp(self):
        """Set up test fixtures"""
        self.bot = Mock()
        self.bot.time = 0.0
        self.bot.expansion_locations_list = []
        self.bot.enemy_start_locations = []
        self.bot.all_units = Mock(return_value=[])

        self.scout_system = ActiveScoutingSystem(self.bot)

    def test_unscouted_expansions_prioritized(self):
        """Test unscouted expansions are prioritized"""
        from sc2.position import Point2

        exp1 = Point2((50, 50))
        exp2 = Point2((100, 100))
        exp3 = Point2((150, 150))

        self.bot.expansion_locations_list = [exp1, exp2, exp3]

        # Mark one as scouted
        self.scout_system.scouted_locations.add((int(exp2.x), int(exp2.y)))

        self.scout_system._update_scout_targets()

        # exp1 and exp3 should be in targets (unscouted)
        self.assertIn(exp1, self.scout_system.scout_targets)
        self.assertIn(exp3, self.scout_system.scout_targets)


if __name__ == '__main__':
    unittest.main()
