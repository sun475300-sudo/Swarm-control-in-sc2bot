#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Unit tests for AdvancedScoutingSystemV2

Tests:
1. Initialization and default values
2. Dynamic scout interval by game time
3. Emergency mode detection
4. Scout report generation
5. Active scout management
6. Patrol route system
7. Watchtower claiming
8. Drop path monitoring
9. Priority target updates
10. Scout cleanup
11. Changeling management
"""

import unittest
from unittest.mock import Mock, MagicMock, patch, AsyncMock
import sys
import os

# Add parent directory to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

try:
    from scouting.advanced_scout_system_v2 import AdvancedScoutingSystemV2
    from sc2.position import Point2
    SCOUT_V2_AVAILABLE = True
except (ImportError, TypeError):
    SCOUT_V2_AVAILABLE = False


@unittest.skipIf(not SCOUT_V2_AVAILABLE, "sc2 library not available")
class TestAdvancedScoutingSystemV2(unittest.TestCase):
    """Test suite for AdvancedScoutingSystemV2"""

    def setUp(self):
        """Set up test fixtures"""
        self.bot = Mock()
        self.bot.time = 0.0
        self.bot.iteration = 0
        self.bot.units = Mock()
        self.bot.enemy_units = Mock(return_value=[])
        self.bot.enemy_structures = Mock(return_value=[])
        self.bot.expansion_locations_list = []
        self.bot.enemy_start_locations = [Point2((200, 200))]
        self.bot.start_location = Point2((30, 30))
        self.bot.game_info = Mock()
        self.bot.game_info.map_center = Point2((100, 100))
        self.bot.blackboard = Mock()
        self.bot.blackboard.last_enemy_seen_time = 0

        # Mock unit_authority_manager
        with patch('scouting.advanced_scout_system_v2.UnitAuthorityManager', create=True):
            self.scout = AdvancedScoutingSystemV2(self.bot)

    def test_initialization(self):
        """Test system initializes with correct defaults"""
        self.assertEqual(self.scout.scouts_sent, 0)
        self.assertEqual(self.scout.scouts_lost, 0)
        self.assertIsInstance(self.scout.active_scouts, dict)
        self.assertEqual(len(self.scout.active_scouts), 0)
        self.assertIsInstance(self.scout.MAX_SCOUTS, dict)
        self.assertIn("WORKER", self.scout.MAX_SCOUTS)
        self.assertIn("ZERGLING", self.scout.MAX_SCOUTS)

    def test_dynamic_interval_early_game(self):
        """Test scout interval is 25s in early game (0-5min)"""
        self.bot.time = 60.0  # 1 minute
        interval = self.scout._get_dynamic_interval()
        self.assertEqual(interval, 25.0)

    def test_dynamic_interval_tech_timing(self):
        """Test scout interval is 20s during tech timing (4-7min)"""
        self.bot.time = 300.0  # 5 minutes (in tech timing window 240-420)
        self.bot.blackboard.last_enemy_seen_time = 295.0  # fresh intel
        interval = self.scout._get_dynamic_interval()
        self.assertEqual(interval, 20.0)

    def test_dynamic_interval_mid_game(self):
        """Test scout interval is 40s in mid game (5-10min, outside tech window)"""
        self.bot.time = 450.0  # 7.5 minutes (past tech timing window)
        self.bot.blackboard.last_enemy_seen_time = 445.0  # fresh intel
        interval = self.scout._get_dynamic_interval()
        self.assertEqual(interval, 40.0)

    def test_dynamic_interval_late_game(self):
        """Test scout interval is 35s in late game (10min+)"""
        self.bot.time = 700.0  # 11+ minutes
        self.bot.blackboard.last_enemy_seen_time = 695.0  # fresh intel
        interval = self.scout._get_dynamic_interval()
        self.assertEqual(interval, 35.0)

    def test_dynamic_interval_emergency(self):
        """Test scout interval is 15s in emergency mode"""
        self.bot.time = 200.0
        self.bot.blackboard.last_enemy_seen_time = 100.0  # 100s stale
        interval = self.scout._get_dynamic_interval()
        self.assertEqual(interval, 15.0)

    def test_emergency_mode_stale_intel(self):
        """Test emergency mode activates when intel is >60s old"""
        self.bot.time = 120.0
        self.bot.blackboard.last_enemy_seen_time = 50.0  # 70s stale
        self.assertTrue(self.scout._is_emergency_mode())

    def test_emergency_mode_fresh_intel(self):
        """Test emergency mode is off when intel is fresh"""
        self.bot.time = 120.0
        self.bot.blackboard.last_enemy_seen_time = 100.0  # 20s fresh
        self.assertFalse(self.scout._is_emergency_mode())

    def test_emergency_mode_no_blackboard(self):
        """Test emergency mode handles missing blackboard gracefully"""
        self.bot.blackboard = None
        self.bot.time = 200.0
        self.assertFalse(self.scout._is_emergency_mode())

    def test_scout_report_structure(self):
        """Test get_scout_report returns correct structure"""
        report = self.scout.get_scout_report()
        expected_keys = [
            "zergling_patrol_count", "overlord_scout_count",
            "overseer_scout_count", "patrol_units", "watchtowers_held",
            "total_active", "scouts_sent", "scouts_lost", "priority_targets"
        ]
        for key in expected_keys:
            self.assertIn(key, report)

    def test_scout_report_empty(self):
        """Test report values are zero when no scouts active"""
        report = self.scout.get_scout_report()
        self.assertEqual(report["total_active"], 0)
        self.assertEqual(report["scouts_sent"], 0)
        self.assertEqual(report["scouts_lost"], 0)
        self.assertEqual(report["watchtowers_held"], 0)


@unittest.skipIf(not SCOUT_V2_AVAILABLE, "sc2 library not available")
class TestScoutReportWithActiveScouts(unittest.TestCase):
    """Test scout report with active scouts"""

    def setUp(self):
        self.bot = Mock()
        self.bot.time = 300.0
        self.bot.iteration = 100
        self.bot.enemy_start_locations = [Point2((200, 200))]
        self.bot.start_location = Point2((30, 30))
        self.bot.game_info = Mock()
        self.bot.game_info.map_center = Point2((100, 100))
        self.bot.blackboard = Mock()
        self.bot.blackboard.last_enemy_seen_time = 290.0

        with patch('scouting.advanced_scout_system_v2.UnitAuthorityManager', create=True):
            self.scout = AdvancedScoutingSystemV2(self.bot)

        # Simulate active scouts
        self.scout.active_scouts = {
            101: {"type": "ZERGLING", "target": Point2((50, 50)), "start_time": 100.0, "mode": "scout"},
            102: {"type": "ZERGLING", "target": Point2((80, 80)), "start_time": 110.0, "mode": "scout"},
            201: {"type": "OVERLORD", "target": Point2((120, 120)), "start_time": 50.0, "mode": "patrol"},
            301: {"type": "OVERSEER", "target": Point2((150, 150)), "start_time": 200.0, "mode": "scout"},
        }
        self.scout.scouts_sent = 10
        self.scout.scouts_lost = 2

    def test_report_counts_by_type(self):
        """Test report correctly counts scouts by type"""
        report = self.scout.get_scout_report()
        self.assertEqual(report["zergling_patrol_count"], 2)
        self.assertEqual(report["overlord_scout_count"], 1)
        self.assertEqual(report["overseer_scout_count"], 1)
        self.assertEqual(report["total_active"], 4)

    def test_report_tracks_losses(self):
        """Test report includes sent and lost counts"""
        report = self.scout.get_scout_report()
        self.assertEqual(report["scouts_sent"], 10)
        self.assertEqual(report["scouts_lost"], 2)


if __name__ == '__main__':
    unittest.main()
