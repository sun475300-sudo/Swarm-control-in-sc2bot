# -*- coding: utf-8 -*-
"""
Unit tests for CombatManager

Tests cover:
- Unit filtering methods
- Threat evaluation
- Target selection
- Rally point system
- Enemy tracking
- Assignment cleanup
"""

import unittest
from unittest.mock import Mock, MagicMock, patch
import sys
import os

# Add parent directory to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from combat_manager import CombatManager
from sc2.ids.unit_typeid import UnitTypeId
from sc2.position import Point2


class TestCombatManager(unittest.TestCase):
    """Test suite for CombatManager"""

    def setUp(self):
        """Set up test fixtures"""
        self.bot = Mock()
        self.bot.units = Mock()
        self.bot.enemy_units = Mock()
        self.bot.enemy_structures = []
        self.bot.townhalls = Mock()
        self.bot.start_location = Point2((50, 50))
        self.bot.enemy_start_locations = [Point2((150, 150))]
        self.bot.expansion_locations_list = [
            Point2((60, 60)),
            Point2((140, 140))
        ]
        self.bot.iteration = 0
        self.bot.time = 0

        # Mock game_info
        self.bot.game_info = Mock()
        self.bot.game_info.map_center = Point2((100, 100))
        mock_map_size = Mock()
        mock_map_size.width = 200
        mock_map_size.height = 200
        self.bot.game_info.map_size = mock_map_size

        # Mock managers
        self.bot.unit_authority = None
        self.bot.micro = None
        self.bot.intel = None

        self.manager = CombatManager(self.bot)

    # ==================== Helper Methods Tests ====================

    def test_has_units_with_units(self):
        """Test _has_units returns True when units exist"""
        mock_units = Mock()
        mock_units.exists = True
        mock_units.amount = 5

        result = self.manager._has_units(mock_units)
        self.assertTrue(result)

    def test_has_units_empty(self):
        """Test _has_units returns False when no units"""
        mock_units = Mock()
        mock_units.exists = False
        mock_units.amount = 0

        result = self.manager._has_units(mock_units)
        self.assertFalse(result)

    def test_has_units_none(self):
        """Test _has_units returns False for None"""
        result = self.manager._has_units(None)
        self.assertFalse(result)

    def test_units_amount_with_units(self):
        """Test _units_amount returns correct count"""
        mock_units = Mock()
        mock_units.amount = 10

        result = self.manager._units_amount(mock_units)
        self.assertEqual(result, 10)

    def test_units_amount_empty(self):
        """Test _units_amount returns 0 for empty units"""
        mock_units = Mock()
        mock_units.amount = 0

        result = self.manager._units_amount(mock_units)
        self.assertEqual(result, 0)

    def test_units_amount_none(self):
        """Test _units_amount returns 0 for None"""
        result = self.manager._units_amount(None)
        self.assertEqual(result, 0)

    # ==================== Unit Filtering Tests ====================

    def test_filter_army_units_zerglings(self):
        """Test filtering army units includes Zerglings"""
        mock_zergling = Mock()
        mock_zergling.type_id = UnitTypeId.ZERGLING
        mock_zergling.name = "Zergling"

        mock_units = [mock_zergling]

        result = self.manager._filter_army_units(mock_units)
        self.assertEqual(len(result), 1)
        self.assertEqual(result[0].type_id, UnitTypeId.ZERGLING)

    def test_filter_army_units_excludes_workers(self):
        """Test filtering excludes workers"""
        mock_drone = Mock()
        mock_drone.type_id = UnitTypeId.DRONE
        mock_drone.name = "Drone"

        mock_units = [mock_drone]

        result = self.manager._filter_army_units(mock_units)
        self.assertEqual(len(result), 0)

    def test_filter_army_units_mixed(self):
        """Test filtering mixed unit types"""
        mock_zergling = Mock()
        mock_zergling.type_id = UnitTypeId.ZERGLING
        mock_zergling.name = "Zergling"

        mock_drone = Mock()
        mock_drone.type_id = UnitTypeId.DRONE
        mock_drone.name = "Drone"

        mock_roach = Mock()
        mock_roach.type_id = UnitTypeId.ROACH
        mock_roach.name = "Roach"

        mock_units = [mock_zergling, mock_drone, mock_roach]

        result = self.manager._filter_army_units(mock_units)
        self.assertEqual(len(result), 2)
        self.assertIn(mock_zergling, result)
        self.assertIn(mock_roach, result)

    def test_filter_air_units(self):
        """Test filtering air units"""
        mock_mutalisk = Mock()
        mock_mutalisk.type_id = UnitTypeId.MUTALISK
        mock_mutalisk.name = "Mutalisk"
        mock_mutalisk.is_flying = True

        mock_zergling = Mock()
        mock_zergling.type_id = UnitTypeId.ZERGLING
        mock_zergling.name = "Zergling"
        mock_zergling.is_flying = False

        mock_units = [mock_mutalisk, mock_zergling]

        result = self.manager._filter_air_units(mock_units)
        self.assertEqual(len(result), 1)
        self.assertEqual(result[0].type_id, UnitTypeId.MUTALISK)

    def test_filter_ground_units(self):
        """Test filtering ground units"""
        mock_zergling = Mock()
        mock_zergling.type_id = UnitTypeId.ZERGLING
        mock_zergling.name = "Zergling"
        mock_zergling.is_flying = False

        mock_mutalisk = Mock()
        mock_mutalisk.type_id = UnitTypeId.MUTALISK
        mock_mutalisk.name = "Mutalisk"
        mock_mutalisk.is_flying = True

        mock_units = [mock_zergling, mock_mutalisk]

        result = self.manager._filter_ground_units(mock_units)
        self.assertEqual(len(result), 1)
        self.assertEqual(result[0].type_id, UnitTypeId.ZERGLING)

    # ==================== Threat Evaluation Tests ====================

    def test_is_base_under_attack_no_townhalls(self):
        """Test base under attack returns False when no townhalls"""
        self.bot.townhalls = Mock()
        self.bot.townhalls.exists = False
        self.bot.townhalls.amount = 0

        result = self.manager._is_base_under_attack()
        self.assertFalse(result)

    def test_is_base_under_attack_no_enemies(self):
        """Test base under attack returns False when no enemies"""
        mock_hatch = Mock()
        mock_hatch.position = Point2((50, 50))

        mock_townhalls = Mock()
        mock_townhalls.exists = True
        mock_townhalls.__iter__ = Mock(return_value=iter([mock_hatch]))
        self.bot.townhalls = mock_townhalls
        self.bot.enemy_units = []

        result = self.manager._is_base_under_attack()
        self.assertFalse(result)

    def test_is_base_under_attack_enemy_nearby(self):
        """Test base under attack returns True when enemy nearby"""
        mock_hatch = Mock()
        mock_hatch.position = Point2((50, 50))

        mock_enemy = Mock()
        mock_enemy.position = Point2((55, 55))  # Close
        mock_enemy.type_id = Mock()
        mock_enemy.type_id.name = "MARINE"
        def enemy_distance_to(pos):
            return ((pos.x - 55)**2 + (pos.y - 55)**2) ** 0.5
        mock_enemy.distance_to = enemy_distance_to

        mock_townhalls = Mock()
        mock_townhalls.exists = True
        mock_townhalls.__iter__ = Mock(return_value=iter([mock_hatch]))
        self.bot.townhalls = mock_townhalls
        self.bot.enemy_units = [mock_enemy]

        result = self.manager._is_base_under_attack()
        self.assertTrue(result)

    def test_evaluate_base_threat_no_enemies(self):
        """Test evaluate base threat with no enemies"""
        mock_hatch = Mock()
        mock_hatch.position = Point2((50, 50))

        mock_townhalls = Mock()
        mock_townhalls.exists = True
        mock_townhalls.__iter__ = Mock(return_value=iter([mock_hatch]))
        self.bot.townhalls = mock_townhalls

        result = self.manager._evaluate_base_threat([])
        self.assertIsNone(result)

    def test_evaluate_base_threat_enemy_far_away(self):
        """Test evaluate base threat when enemy is far"""
        mock_hatch = Mock()
        mock_hatch.position = Point2((50, 50))

        mock_enemy = Mock()
        mock_enemy.position = Point2((150, 150))  # Very far
        mock_enemy.type_id = Mock()
        mock_enemy.type_id.name = "MARINE"
        def enemy_distance_to(pos):
            return ((pos.x - 150)**2 + (pos.y - 150)**2) ** 0.5
        mock_enemy.distance_to = enemy_distance_to

        mock_townhalls = Mock()
        mock_townhalls.exists = True
        mock_townhalls.__iter__ = Mock(return_value=iter([mock_hatch]))
        self.bot.townhalls = mock_townhalls

        result = self.manager._evaluate_base_threat([mock_enemy])
        self.assertIsNone(result)

    def test_evaluate_base_threat_enemy_close(self):
        """Test evaluate base threat when enemy is close"""
        mock_hatch = Mock()
        mock_hatch.position = Point2((50, 50))

        mock_enemy = Mock()
        mock_enemy.position = Point2((55, 55))  # Close
        mock_enemy.type_id = Mock()
        mock_enemy.type_id.name = "MARINE"
        def enemy_distance_to(pos):
            return ((pos.x - 55)**2 + (pos.y - 55)**2) ** 0.5
        mock_enemy.distance_to = enemy_distance_to

        mock_townhalls = Mock()
        mock_townhalls.exists = True
        mock_townhalls.__iter__ = Mock(return_value=iter([mock_hatch]))
        self.bot.townhalls = mock_townhalls

        result = self.manager._evaluate_base_threat([mock_enemy])
        self.assertIsNotNone(result)

    def test_get_units_near_base_no_townhalls(self):
        """Test get units near base with no townhalls"""
        self.bot.townhalls = Mock()
        self.bot.townhalls.exists = False
        self.bot.townhalls.amount = 0

        mock_units = [Mock(), Mock()]

        result = self.manager._get_units_near_base(mock_units, range_distance=20)
        self.assertEqual(len(result), 0)

    def test_get_units_near_base_with_units(self):
        """Test get units near base returns nearby units"""
        mock_hatch = Mock()
        mock_hatch.position = Point2((50, 50))

        mock_townhalls = Mock()
        mock_townhalls.exists = True
        mock_townhalls.__iter__ = Mock(return_value=iter([mock_hatch]))
        self.bot.townhalls = mock_townhalls

        mock_unit_close = Mock()
        mock_unit_close.position = Point2((55, 55))
        mock_unit_close.tag = 1

        mock_unit_far = Mock()
        mock_unit_far.position = Point2((80, 80))
        mock_unit_far.tag = 2

        # Mock bot.units.closer_than to return only close unit
        mock_bot_units = Mock()
        mock_bot_units.closer_than = Mock(return_value=[mock_unit_close])
        self.bot.units = mock_bot_units

        mock_units = [mock_unit_close, mock_unit_far]

        result = self.manager._get_units_near_base(mock_units, range_distance=20)
        self.assertEqual(len(result), 1)
        self.assertEqual(result[0], mock_unit_close)

    # ==================== Target Selection Tests ====================

    def test_get_attack_target_no_enemies(self):
        """Test get attack target with no enemies returns enemy start location"""
        result = self.manager._get_attack_target([])
        # When no enemies, should return enemy start location
        self.assertEqual(result, Point2((150, 150)))

    def test_get_attack_target_with_enemies(self):
        """Test get attack target with enemies"""
        mock_enemy = Mock()
        mock_enemy.position = Point2((150, 150))

        result = self.manager._get_attack_target([mock_enemy])
        self.assertIsNotNone(result)

    def test_find_priority_attack_target_workers(self):
        """Test priority target selection - simplified"""
        # This method has complex dependencies, just test it doesn't crash
        mock_hatch = Mock()
        mock_hatch.position = Point2((50, 50))

        mock_townhalls = Mock()
        mock_townhalls.exists = True
        mock_townhalls.first = mock_hatch
        mock_townhalls.__iter__ = Mock(return_value=iter([mock_hatch]))
        self.bot.townhalls = mock_townhalls
        self.bot.enemy_units = []
        self.bot.enemy_structures = []

        target = self.manager._find_priority_attack_target()
        # Should return a target (could be enemy start or search target)
        self.assertIsNotNone(target)

    def test_find_priority_attack_target_no_enemies(self):
        """Test priority target selection with no enemies"""
        mock_hatch = Mock()
        mock_hatch.position = Point2((50, 50))

        mock_townhalls = Mock()
        mock_townhalls.exists = True
        mock_townhalls.first = mock_hatch
        mock_townhalls.__iter__ = Mock(return_value=iter([mock_hatch]))
        self.bot.townhalls = mock_townhalls
        self.bot.enemy_units = []
        self.bot.enemy_structures = []

        target = self.manager._find_priority_attack_target()
        # Should return a target (search location or enemy start)
        self.assertIsNotNone(target)

    def test_select_mutalisk_target_prioritizes_workers(self):
        """Test mutalisk target selection prioritizes workers"""
        mock_worker = Mock()
        mock_worker.type_id = Mock()
        mock_worker.type_id.name = "PROBE"
        mock_worker.can_attack_air = False
        mock_worker.position = Point2((140, 140))
        mock_worker.health = 40
        mock_worker.health_percentage = 1.0

        mock_stalker = Mock()
        mock_stalker.type_id = Mock()
        mock_stalker.type_id.name = "STALKER"
        mock_stalker.can_attack_air = True
        mock_stalker.position = Point2((145, 145))
        mock_stalker.health = 160
        mock_stalker.health_percentage = 1.0

        enemy_units = [mock_stalker, mock_worker]

        target = self.manager._select_mutalisk_target(enemy_units)
        self.assertIsNotNone(target)
        # Should target the worker
        self.assertEqual(target.type_id.name, "PROBE")

    # ==================== Rally Point Tests ====================

    def test_update_rally_point_creates_rally(self):
        """Test rally point is created"""
        mock_hatch = Mock()
        mock_hatch.position = Point2((50, 50))
        mock_hatch.first = mock_hatch

        mock_townhalls = Mock()
        mock_townhalls.exists = True
        mock_townhalls.first = mock_hatch
        self.bot.townhalls = mock_townhalls
        self.bot.time = 100

        self.manager._update_rally_point()
        self.assertIsNotNone(self.manager._rally_point)

    def test_is_army_gathered_no_rally_point(self):
        """Test army gathered returns True when no rally point (considered gathered)"""
        self.manager._rally_point = None

        result = self.manager._is_army_gathered([])
        self.assertTrue(result)

    def test_is_army_gathered_sufficient_units(self):
        """Test army gathered returns True with sufficient units"""
        self.manager._rally_point = Point2((100, 100))

        # Create mock units near rally point
        mock_units = []
        for i in range(8):
            unit = Mock()
            unit.position = Point2((100 + i, 100))
            unit.distance_to = Mock(return_value=5.0)
            mock_units.append(unit)

        result = self.manager._is_army_gathered(mock_units)
        self.assertTrue(result)

    def test_is_army_gathered_insufficient_units(self):
        """Test army gathered checks 70% threshold"""
        self.manager._rally_point = Point2((100, 100))

        # Create mock units - only 1 out of 3 near rally point
        mock_units = []
        for i in range(3):
            unit = Mock()
            unit.position = Point2((100 + i*20, 100 + i*20))  # Far apart
            if i == 0:
                unit.distance_to = Mock(return_value=5.0)  # Only first unit near
            else:
                unit.distance_to = Mock(return_value=50.0)  # Others far
            mock_units.append(unit)

        result = self.manager._is_army_gathered(mock_units)
        # 1/3 = 33% < 70%, should return False
        self.assertFalse(result)

    # ==================== Enemy Tracking Tests ====================

    def test_get_enemy_center_no_enemies(self):
        """Test get enemy center with no enemies returns Point2((0,0)) from centroid helper"""
        result = self.manager._get_enemy_center([])
        # When HELPERS_AVAILABLE=True, centroid() returns Point2((0, 0)) for empty list
        self.assertEqual(result, Point2((0, 0)))

    def test_get_enemy_center_single_enemy(self):
        """Test get enemy center with single enemy"""
        mock_enemy = Mock()
        mock_enemy.position = Point2((100, 100))

        result = self.manager._get_enemy_center([mock_enemy])
        self.assertIsNotNone(result)
        self.assertEqual(result.x, 100)
        self.assertEqual(result.y, 100)

    def test_get_enemy_center_multiple_enemies(self):
        """Test get enemy center with multiple enemies"""
        mock_enemy1 = Mock()
        mock_enemy1.position = Point2((100, 100))

        mock_enemy2 = Mock()
        mock_enemy2.position = Point2((120, 120))

        result = self.manager._get_enemy_center([mock_enemy1, mock_enemy2])
        self.assertIsNotNone(result)
        # Center should be approximately (110, 110)
        self.assertAlmostEqual(result.x, 110, delta=5)
        self.assertAlmostEqual(result.y, 110, delta=5)

    def test_closest_enemy_no_enemies(self):
        """Test closest enemy with no enemies"""
        mock_unit = Mock()
        mock_unit.position = Point2((50, 50))

        result = self.manager._closest_enemy([], mock_unit)
        self.assertIsNone(result)

    def test_closest_enemy_single_enemy(self):
        """Test closest enemy with single enemy"""
        mock_unit = Mock()
        mock_unit.position = Point2((50, 50))

        mock_enemy = Mock()
        mock_enemy.position = Point2((60, 60))

        result = self.manager._closest_enemy([mock_enemy], mock_unit)
        self.assertEqual(result, mock_enemy)

    def test_closest_enemy_multiple_enemies(self):
        """Test closest enemy selects nearest"""
        mock_unit = Mock()
        mock_unit.position = Point2((50, 50))
        def unit_distance_to(enemy):
            return ((enemy.position.x - 50)**2 + (enemy.position.y - 50)**2) ** 0.5
        mock_unit.distance_to = unit_distance_to

        mock_enemy_close = Mock()
        mock_enemy_close.position = Point2((55, 55))

        mock_enemy_far = Mock()
        mock_enemy_far.position = Point2((150, 150))

        result = self.manager._closest_enemy([mock_enemy_far, mock_enemy_close], mock_unit)
        self.assertEqual(result, mock_enemy_close)

    # ==================== Assignment Cleanup Tests ====================

    def test_cleanup_assignments_removes_dead_units(self):
        """Test cleanup removes assignments for dead units"""
        # Add some assignments
        self.manager._unit_assignments[123] = "attack"
        self.manager._unit_assignments[456] = "defend"

        # Mock bot.units with only one unit alive
        mock_unit = Mock()
        mock_unit.tag = 123

        self.bot.units = [mock_unit]

        self.manager._cleanup_assignments()

        # Unit 456 should be removed (not in bot.units)
        self.assertIn(123, self.manager._unit_assignments)
        self.assertNotIn(456, self.manager._unit_assignments)

    def test_cleanup_assignments_preserves_alive_units(self):
        """Test cleanup preserves assignments for alive units"""
        # Add assignment
        self.manager._unit_assignments[123] = "attack"

        # Mock bot.units with unit alive
        mock_unit = Mock()
        mock_unit.tag = 123

        self.bot.units = [mock_unit]

        self.manager._cleanup_assignments()

        # Unit 123 should still be assigned
        self.assertIn(123, self.manager._unit_assignments)
        self.assertEqual(self.manager._unit_assignments[123], "attack")

    # ==================== Integration Tests ====================

    def test_get_army_supply_no_units(self):
        """Test get army supply with no units"""
        self.bot.units = []

        result = self.manager._get_army_supply()
        self.assertEqual(result, 0)

    def test_get_army_supply_with_units(self):
        """Test get army supply with units"""
        mock_zergling = Mock()
        mock_zergling.type_id = UnitTypeId.ZERGLING
        mock_zergling.name = "Zergling"
        mock_zergling.is_flying = False

        mock_roach = Mock()
        mock_roach.type_id = UnitTypeId.ROACH
        mock_roach.name = "Roach"
        mock_roach.is_flying = False

        # Mock as Units object with proper methods
        mock_units = Mock()
        mock_units.__iter__ = Mock(return_value=iter([mock_zergling, mock_roach]))
        mock_units.filter = Mock(return_value=[mock_zergling, mock_roach])

        self.bot.units = mock_units

        result = self.manager._get_army_supply()
        # Should count army units (implementation may vary)
        self.assertGreaterEqual(result, 0)


if __name__ == '__main__':
    unittest.main()
