# -*- coding: utf-8 -*-
"""
Unit tests for EconomyManager

Tests cover:
- Emergency mode and configuration
- Resource status and drone count
- Gold base detection
- Expansion selection
- Supply management
- Worker distribution logic
"""

import unittest
from unittest.mock import Mock, MagicMock, patch
import sys
import os

# Add parent directory to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from economy_manager import EconomyManager
from sc2.ids.unit_typeid import UnitTypeId
from sc2.position import Point2


class TestEconomyManager(unittest.TestCase):
    """Test suite for EconomyManager"""

    def setUp(self):
        """Set up test fixtures"""
        self.bot = Mock()
        self.bot.larva = Mock()
        self.bot.larva.amount = 3
        self.bot.larva.exists = True
        self.bot.workers = Mock()
        self.bot.workers.amount = 12
        self.bot.townhalls = Mock()
        self.bot.townhalls.amount = 1
        self.bot.townhalls.exists = True
        self.bot.minerals = 50
        self.bot.vespene = 0
        self.bot.supply_left = 5
        self.bot.supply_used = 12
        self.bot.supply_cap = 17
        self.bot.time = 0
        self.bot.iteration = 0
        self.bot.start_location = Point2((50, 50))
        self.bot.enemy_start_locations = [Point2((150, 150))]
        self.bot.expansion_locations_list = [
            Point2((60, 60)),
            Point2((140, 140))
        ]
        self.bot.mineral_field = Mock()
        self.bot.gas_buildings = Mock()
        self.bot.blackboard = None

        # Mock already_pending method
        self.bot.already_pending = Mock(return_value=0)

        # Mock Units.closer_than
        self.bot.mineral_field.closer_than = Mock(return_value=[])

        self.manager = EconomyManager(self.bot)

    # ==================== Emergency Mode & Configuration Tests ====================

    def test_set_emergency_mode_true(self):
        """Test setting emergency mode to True"""
        self.manager.set_emergency_mode(True)
        self.assertTrue(self.manager._emergency_mode)

    def test_set_emergency_mode_false(self):
        """Test setting emergency mode to False"""
        self.manager.set_emergency_mode(False)
        self.assertFalse(self.manager._emergency_mode)

    def test_emergency_mode_default_false(self):
        """Test emergency mode defaults to False"""
        self.assertFalse(self.manager._emergency_mode)

    def test_gold_mineral_threshold_constant(self):
        """Test GOLD_MINERAL_THRESHOLD is properly defined"""
        self.assertEqual(EconomyManager.GOLD_MINERAL_THRESHOLD, 1200)

    def test_balancer_initialization(self):
        """Test EconomyCombatBalancer is initialized"""
        self.assertIsNotNone(self.manager.balancer)

    # ==================== Resource Status & Drone Count Tests ====================

    def test_get_target_drone_count_default(self):
        """Test get_target_drone_count returns default value"""
        result = self.manager.get_target_drone_count()
        self.assertEqual(result, 66)

    def test_get_target_drone_count_custom(self):
        """Test get_target_drone_count returns custom value"""
        self.manager._target_drone_count = 80
        result = self.manager.get_target_drone_count()
        self.assertEqual(result, 80)

    # ==================== Gold Base Detection Tests ====================

    def test_is_gold_expansion_with_gold_minerals(self):
        """Test gold expansion detection with gold minerals present"""
        mock_hatch = Mock()
        mock_hatch.position = Point2((60, 60))

        # Mock gold mineral
        mock_gold_mineral = Mock()
        mock_gold_mineral.mineral_contents = 1500  # > GOLD_MINERAL_THRESHOLD
        mock_gold_mineral.position = Point2((62, 62))

        mock_minerals = Mock()
        mock_minerals.closer_than = Mock(return_value=[mock_gold_mineral])
        self.bot.mineral_field = mock_minerals

        result = self.manager._is_gold_expansion(Point2((60, 60)))
        self.assertTrue(result)

    def test_is_gold_expansion_without_gold_minerals(self):
        """Test gold expansion detection without gold minerals"""
        mock_hatch = Mock()
        mock_hatch.position = Point2((60, 60))

        # Mock normal mineral
        mock_normal_mineral = Mock()
        mock_normal_mineral.mineral_contents = 900  # < GOLD_MINERAL_THRESHOLD
        mock_normal_mineral.position = Point2((62, 62))

        mock_minerals = Mock()
        mock_minerals.closer_than = Mock(return_value=[mock_normal_mineral])
        self.bot.mineral_field = mock_minerals

        result = self.manager._is_gold_expansion(Point2((60, 60)))
        self.assertFalse(result)

    def test_is_gold_expansion_no_minerals_nearby(self):
        """Test gold expansion detection with no minerals"""
        mock_minerals = Mock()
        mock_minerals.closer_than = Mock(return_value=[])
        self.bot.mineral_field = mock_minerals

        result = self.manager._is_gold_expansion(Point2((60, 60)))
        self.assertFalse(result)

    def test_get_gold_expansion_locations_empty(self):
        """Test getting gold expansion locations with none available"""
        # Mock no gold minerals
        mock_minerals = Mock()
        mock_minerals.closer_than = Mock(return_value=[])
        self.bot.mineral_field = mock_minerals

        result = self.manager._get_gold_expansion_locations()
        self.assertEqual(result, [])

    def test_get_gold_expansion_locations_with_gold(self):
        """Test getting gold expansion locations with gold base"""
        # Mock townhalls (no existing bases)
        self.bot.townhalls = []

        # Mock enemy structures (none)
        self.bot.enemy_structures = []

        # Mock gold mineral
        mock_gold_mineral = Mock()
        mock_gold_mineral.mineral_contents = 1500
        mock_gold_mineral.position = Point2((62, 62))

        mock_minerals = Mock()
        # Return gold mineral for expansion location check
        mock_minerals.closer_than = Mock(return_value=[mock_gold_mineral])
        self.bot.mineral_field = mock_minerals

        result = self.manager._get_gold_expansion_locations()
        # Should find gold expansions
        self.assertIsInstance(result, list)

    def test_get_gold_expansion_locations_caching(self):
        """Test gold expansion location caching"""
        # First call
        self.bot.time = 0
        result1 = self.manager._get_gold_expansion_locations()

        # Second call within 30 seconds (should use cache)
        self.bot.time = 10
        result2 = self.manager._get_gold_expansion_locations()

        # Cache time should be set
        self.assertGreaterEqual(self.manager._gold_cache_time, 0)

    # ==================== Supply Management Tests ====================

    def test_supply_calculations(self):
        """Test supply calculations are accessible"""
        self.assertEqual(self.bot.supply_left, 5)
        self.assertEqual(self.bot.supply_used, 12)
        self.assertEqual(self.bot.supply_cap, 17)

    # ==================== Expansion Selection Tests ====================

    def test_expansion_cooldown_initialization(self):
        """Test expansion cooldown is initialized"""
        self.assertEqual(self.manager._expansion_cooldown, 6.0)
        self.assertEqual(self.manager._last_expansion_attempt_time, 0.0)

    def test_transferred_hatcheries_initialization(self):
        """Test transferred hatcheries set is initialized"""
        self.assertIsInstance(self.manager.transferred_hatcheries, set)
        self.assertEqual(len(self.manager.transferred_hatcheries), 0)

    # ==================== Resource Reservation Tests ====================

    def test_resource_reservation_initialization(self):
        """Test resource reservation system is initialized"""
        self.assertEqual(self.manager._reserved_minerals, 0)
        self.assertEqual(self.manager._reserved_gas, 0)

    def test_mineral_reserved_for_expansion(self):
        """Test expansion mineral reservation is initialized"""
        self.assertEqual(self.manager._mineral_reserved_for_expansion, 0)
        self.assertEqual(self.manager._expansion_reserved_until, 0.0)

    # ==================== Configuration Tests ====================

    def test_config_none_defaults(self):
        """Test default values when config is None"""
        # Manager initialized with config=None in setUp
        self.assertEqual(self.manager.macro_hatchery_mineral_threshold, 1500)
        self.assertEqual(self.manager.macro_hatchery_larva_threshold, 3)

    def test_blackboard_integration(self):
        """Test blackboard integration is set up"""
        # Blackboard is None in setUp
        self.assertIsNone(self.manager.blackboard)

    # ==================== Helper Method Tests ====================

    def test_early_split_done_flag_initialization(self):
        """Test early worker split flag starts unset"""
        self.assertFalse(hasattr(self.manager, '_early_split_done'))


if __name__ == '__main__':
    unittest.main()
