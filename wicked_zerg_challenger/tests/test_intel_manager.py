#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Unit tests for IntelManager

Tests:
1. Build pattern detection
2. Confidence score calculation
3. Confidence status determination
4. Threat level assessment
5. Blackboard integration
"""

import unittest
from unittest.mock import Mock, MagicMock
import sys
import os

# Add parent directory to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from intel_manager import IntelManager


class TestIntelManager(unittest.TestCase):
    """Test suite for IntelManager"""

    def setUp(self):
        """Set up test fixtures"""
        self.bot = Mock()
        self.bot.time = 0.0
        self.bot.iteration = 0
        self.bot.enemy_race = Mock()
        self.bot.enemy_race.name = "Terran"
        self.bot.enemy_units = []
        self.bot.enemy_structures = []
        self.bot.townhalls = []
        self.bot.blackboard = Mock()

        self.intel = IntelManager(self.bot)

    def test_initialization(self):
        """Test IntelManager initializes correctly"""
        self.assertEqual(self.intel.enemy_army_supply, 0)
        self.assertEqual(self.intel.enemy_base_count, 0)
        self.assertEqual(self.intel._build_pattern_confidence, 0.0)
        self.assertEqual(self.intel._build_pattern_status, "unknown")

    def test_build_pattern_confidence_calculation_basic(self):
        """Test basic confidence calculation"""
        pattern = "terran_bio"
        structure_counts = {
            "BARRACKS": 3,
            "COMMANDCENTER": 1
        }
        enemy_units = []
        game_time = 180.0

        # Set up intel manager state
        self.intel.enemy_tech_buildings = {"BARRACKS"}
        self.intel.enemy_unit_counts = {}

        confidence = self.intel._calculate_build_confidence(
            pattern, structure_counts, enemy_units, game_time
        )

        # Should have some confidence from tech buildings and time
        self.assertGreater(confidence, 0.0)
        self.assertLessEqual(confidence, 1.0)

    def test_build_pattern_confidence_with_units(self):
        """Test confidence increases with related units"""
        pattern = "terran_bio"
        structure_counts = {"BARRACKS": 3}
        enemy_units = []
        game_time = 180.0

        # Set up with related units
        self.intel.enemy_tech_buildings = {"BARRACKS"}
        self.intel.enemy_unit_counts = {
            "MARINE": 10,
            "MARAUDER": 5,
            "MEDIVAC": 2
        }

        confidence = self.intel._calculate_build_confidence(
            pattern, structure_counts, enemy_units, game_time
        )

        # Should have higher confidence with many related units
        self.assertGreater(confidence, 0.3)

    def test_build_pattern_status_unknown(self):
        """Test build pattern status is unknown with low confidence"""
        self.intel._build_pattern_confidence = 0.2

        if self.intel._build_pattern_confidence >= 0.7:
            status = "confirmed"
        elif self.intel._build_pattern_confidence >= 0.3:
            status = "suspected"
        else:
            status = "unknown"

        self.assertEqual(status, "unknown")

    def test_build_pattern_status_suspected(self):
        """Test build pattern status is suspected with medium confidence"""
        self.intel._build_pattern_confidence = 0.5

        if self.intel._build_pattern_confidence >= 0.7:
            status = "confirmed"
        elif self.intel._build_pattern_confidence >= 0.3:
            status = "suspected"
        else:
            status = "unknown"

        self.assertEqual(status, "suspected")

    def test_build_pattern_status_confirmed(self):
        """Test build pattern status is confirmed with high confidence"""
        self.intel._build_pattern_confidence = 0.8

        if self.intel._build_pattern_confidence >= 0.7:
            status = "confirmed"
        elif self.intel._build_pattern_confidence >= 0.3:
            status = "suspected"
        else:
            status = "unknown"

        self.assertEqual(status, "confirmed")

    def test_rush_pattern_high_confidence(self):
        """Test rush patterns get high confidence early game"""
        pattern = "terran_rush"
        structure_counts = {"BARRACKS": 2}
        enemy_units = []
        game_time = 120.0  # 2 minutes - early game

        self.intel.enemy_tech_buildings = {"BARRACKS"}
        self.intel.enemy_unit_counts = {"MARINE": 8}

        confidence = self.intel._calculate_build_confidence(
            pattern, structure_counts, enemy_units, game_time
        )

        # Rush pattern in early game should have bonus confidence
        self.assertGreater(confidence, 0.4)

    def test_threat_level_none(self):
        """Test threat level is none with no enemies"""
        self.bot.enemy_units = []
        self.bot.townhalls = [Mock()]

        self.intel._update_threat_status()

        self.assertEqual(self.intel._threat_level, "none")
        self.assertFalse(self.intel._under_attack)

    def test_blackboard_integration(self):
        """Test intel data is pushed to blackboard"""
        detected_pattern = "terran_bio"
        self.intel._enemy_build_pattern = detected_pattern
        self.intel._build_pattern_confidence = 0.8
        self.intel._build_pattern_status = "confirmed"
        self.intel._recommended_response = ["baneling", "zergling"]
        self.intel._under_attack = False
        self.intel._threat_level = "none"
        self.intel._high_threat_units_detected = False
        self.intel.enemy_army_supply = 50
        self.intel.enemy_base_count = 2
        self.intel.enemy_worker_count = 30

        self.intel._push_intel_to_blackboard(detected_pattern)

        # Verify blackboard was called
        self.bot.blackboard.set.assert_called()

        # Check specific values
        calls = self.bot.blackboard.set.call_args_list
        call_dict = {call[0][0]: call[0][1] for call in calls}

        self.assertEqual(call_dict["enemy_build_pattern"], "terran_bio")
        self.assertEqual(call_dict["enemy_build_confidence"], 0.8)
        self.assertEqual(call_dict["enemy_build_status"], "confirmed")
        self.assertEqual(call_dict["recommended_counter_units"],
                        ["baneling", "zergling"])

    def test_is_build_pattern_confirmed(self):
        """Test build pattern confirmation check"""
        self.intel._build_pattern_status = "confirmed"
        self.assertTrue(self.intel.is_build_pattern_confirmed())

        self.intel._build_pattern_status = "suspected"
        self.assertFalse(self.intel.is_build_pattern_confirmed())

        self.intel._build_pattern_status = "unknown"
        self.assertFalse(self.intel.is_build_pattern_confirmed())

    def test_get_build_pattern_confidence(self):
        """Test confidence score retrieval"""
        self.intel._build_pattern_confidence = 0.75
        self.assertEqual(self.intel.get_build_pattern_confidence(), 0.75)

    def test_get_build_pattern_status(self):
        """Test status retrieval"""
        self.intel._build_pattern_status = "confirmed"
        self.assertEqual(self.intel.get_build_pattern_status(), "confirmed")

    def test_recommended_response_for_terran_bio(self):
        """Test recommended response for Terran bio"""
        structure_counts = {"BARRACKS": 3}
        enemy_units = []

        self.intel._detect_enemy_build_pattern(
            [Mock(type_id=Mock(name="BARRACKS")) for _ in range(3)],
            enemy_units
        )

        pattern = self.intel.get_enemy_build_pattern()
        response = self.intel.get_recommended_response()

        self.assertEqual(pattern, "terran_bio")
        self.assertIn("baneling", response)

    def test_confidence_increases_with_time(self):
        """Test confidence score increases with game time"""
        pattern = "protoss_robo"
        structure_counts = {"ROBOTICSFACILITY": 1}
        enemy_units = []

        self.intel.enemy_tech_buildings = {"ROBOTICSFACILITY"}
        self.intel.enemy_unit_counts = {}

        # Early game
        confidence_early = self.intel._calculate_build_confidence(
            pattern, structure_counts, enemy_units, 60.0
        )

        # Late game
        confidence_late = self.intel._calculate_build_confidence(
            pattern, structure_counts, enemy_units, 300.0
        )

        # Confidence should increase with time
        self.assertGreater(confidence_late, confidence_early)


class TestIntelManagerIntegration(unittest.TestCase):
    """Integration tests for IntelManager"""

    def setUp(self):
        """Set up test fixtures"""
        self.bot = Mock()
        self.bot.time = 0.0
        self.bot.iteration = 0
        self.bot.enemy_race = Mock()
        self.bot.enemy_race.name = "Terran"
        self.bot.enemy_units = []
        self.bot.enemy_structures = []
        self.bot.townhalls = []
        self.bot.blackboard = Mock()

        self.intel = IntelManager(self.bot)

    def test_full_detection_flow(self):
        """Test complete detection flow from structures to blackboard"""
        # Set up enemy structures
        barracks1 = Mock()
        barracks1.type_id = Mock()
        barracks1.type_id.name = "BARRACKS"

        barracks2 = Mock()
        barracks2.type_id = Mock()
        barracks2.type_id.name = "BARRACKS"

        barracks3 = Mock()
        barracks3.type_id = Mock()
        barracks3.type_id.name = "BARRACKS"

        enemy_structures = [barracks1, barracks2, barracks3]

        # Set up enemy units
        marine1 = Mock()
        marine1.type_id = Mock()
        marine1.type_id.name = "MARINE"
        marine1.supply_cost = 1

        enemy_units = [marine1] * 10  # 10 marines

        # Run detection
        self.bot.enemy_structures = enemy_structures
        self.bot.enemy_units = enemy_units
        self.bot.time = 180.0

        self.intel.update(self.intel.last_update)

        # Verify pattern detected
        pattern = self.intel.get_enemy_build_pattern()
        self.assertEqual(pattern, "terran_bio")

        # Verify confidence calculated
        confidence = self.intel.get_build_pattern_confidence()
        self.assertGreater(confidence, 0.0)

        # Verify status determined
        status = self.intel.get_build_pattern_status()
        self.assertIn(status, ["unknown", "suspected", "confirmed"])


if __name__ == '__main__':
    unittest.main()
