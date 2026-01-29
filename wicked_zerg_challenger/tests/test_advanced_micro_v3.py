# -*- coding: utf-8 -*-
"""
Unit tests for Advanced Micro Controller V3

Tests cover:
- RavagerMicro - Corrosive Bile targeting
- LurkerMicro - Burrow positioning
- QueenMicro - Transfuse targeting
- ViperMicro - Abduct targeting
- CorruptorMicro - Caustic Spray targeting
- FocusFireCoordinator - Target selection
"""

import unittest
from unittest.mock import Mock, MagicMock
import sys
import os

# Add parent directory to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from advanced_micro_controller_v3 import (
    RavagerMicro, LurkerMicro, QueenMicro, ViperMicro,
    CorruptorMicro, FocusFireCoordinator
)
from sc2.position import Point2


class TestRavagerMicro(unittest.TestCase):
    """Test suite for RavagerMicro"""

    def setUp(self):
        """Set up test fixtures"""
        self.ravager_micro = RavagerMicro()

    def test_initialization(self):
        """Test RavagerMicro initialization"""
        self.assertEqual(self.ravager_micro.prediction_time, 1.8)
        self.assertEqual(self.ravager_micro.min_targets_for_shot, 2)
        self.assertEqual(len(self.ravager_micro.last_shot_time), 0)

    def test_cooldown_tracking(self):
        """Test cooldown tracking"""
        mock_ravager = Mock()
        mock_ravager.tag = 12345

        # No cooldown initially
        self.assertFalse(self.ravager_micro.is_on_cooldown(mock_ravager, 100.0))

        # Set cooldown
        self.ravager_micro.last_shot_time[12345] = 100.0

        # Should be on cooldown
        self.assertTrue(self.ravager_micro.is_on_cooldown(mock_ravager, 102.0))

        # Should be off cooldown after 7 seconds
        self.assertFalse(self.ravager_micro.is_on_cooldown(mock_ravager, 108.0))

    def test_predict_enemy_position(self):
        """Test enemy position prediction"""
        mock_enemy = Mock()
        mock_enemy.position = Point2((50, 50))

        predicted = self.ravager_micro.predict_enemy_position(mock_enemy, 1.8)

        self.assertIsNotNone(predicted)
        self.assertIsInstance(predicted, Point2)

    def test_find_best_bile_target_no_enemies(self):
        """Test bile target selection with no enemies"""
        mock_ravager = Mock()
        mock_ravager.tag = 12345
        mock_ravager.position = Point2((50, 50))

        target = self.ravager_micro.find_best_bile_target(mock_ravager, [], 100.0)
        self.assertIsNone(target)

    def test_find_best_bile_target_on_cooldown(self):
        """Test bile target selection when on cooldown"""
        mock_ravager = Mock()
        mock_ravager.tag = 12345
        mock_ravager.position = Point2((50, 50))
        self.ravager_micro.last_shot_time[12345] = 100.0

        mock_enemies = [Mock() for _ in range(3)]
        for i, e in enumerate(mock_enemies):
            e.position = Point2((52 + i, 52))

        target = self.ravager_micro.find_best_bile_target(mock_ravager, mock_enemies, 102.0)
        self.assertIsNone(target)


class TestLurkerMicro(unittest.TestCase):
    """Test suite for LurkerMicro"""

    def setUp(self):
        """Set up test fixtures"""
        self.lurker_micro = LurkerMicro()

    def test_initialization(self):
        """Test LurkerMicro initialization"""
        self.assertEqual(self.lurker_micro.optimal_range, 9.0)
        self.assertEqual(self.lurker_micro.burrow_threshold, 1)
        self.assertEqual(len(self.lurker_micro.burrowed_lurkers), 0)

    def test_should_burrow_with_enemies(self):
        """Test burrow decision with enemies in range"""
        mock_lurker = Mock()
        mock_lurker.is_burrowed = False
        mock_lurker.position = Point2((50, 50))

        mock_enemy = Mock()
        mock_enemy.position = Point2((55, 50))

        result = self.lurker_micro.should_burrow(mock_lurker, [mock_enemy])
        self.assertTrue(result)

    def test_should_not_burrow_already_burrowed(self):
        """Test burrow decision when already burrowed"""
        mock_lurker = Mock()
        mock_lurker.is_burrowed = True
        mock_lurker.position = Point2((50, 50))

        mock_enemy = Mock()
        mock_enemy.position = Point2((55, 50))

        result = self.lurker_micro.should_burrow(mock_lurker, [mock_enemy])
        self.assertFalse(result)

    def test_should_unburrow_no_enemies(self):
        """Test unburrow decision with no enemies"""
        mock_lurker = Mock()
        mock_lurker.is_burrowed = True
        mock_lurker.position = Point2((50, 50))

        result = self.lurker_micro.should_unburrow(mock_lurker, [])
        self.assertTrue(result)

    def test_find_optimal_position(self):
        """Test optimal position calculation"""
        mock_lurker = Mock()
        mock_lurker.position = Point2((50, 50))

        mock_bot = Mock()

        mock_enemies = [Mock() for _ in range(3)]
        for i, e in enumerate(mock_enemies):
            e.position = Point2((60 + i, 60))

        position = self.lurker_micro.find_optimal_position(
            mock_lurker,
            mock_enemies,
            mock_bot
        )

        self.assertIsNotNone(position)
        self.assertIsInstance(position, Point2)


class TestQueenMicro(unittest.TestCase):
    """Test suite for QueenMicro"""

    def setUp(self):
        """Set up test fixtures"""
        self.queen_micro = QueenMicro()

    def test_initialization(self):
        """Test QueenMicro initialization"""
        self.assertEqual(self.queen_micro.transfuse_threshold, 0.4)
        self.assertEqual(self.queen_micro.transfuse_energy_cost, 50)
        self.assertEqual(self.queen_micro.transfuse_range, 7.0)

    def test_find_transfuse_target_no_injured(self):
        """Test transfuse target when no injured units"""
        mock_queen = Mock()
        mock_queen.tag = 12345
        mock_queen.position = Point2((50, 50))

        # Healthy unit
        mock_unit = Mock()
        mock_unit.tag = 54321
        mock_unit.health = 100
        mock_unit.health_max = 100
        mock_unit.position = Point2((52, 52))
        mock_unit.type_id = Mock()

        target = self.queen_micro.find_transfuse_target(mock_queen, [mock_unit])
        self.assertIsNone(target)

    def test_find_transfuse_target_injured_unit(self):
        """Test transfuse target with injured unit"""
        mock_queen = Mock()
        mock_queen.tag = 12345
        mock_queen.position = Point2((50, 50))

        # Injured unit
        mock_unit = Mock()
        mock_unit.tag = 54321
        mock_unit.health = 30
        mock_unit.health_max = 100
        mock_unit.position = Point2((52, 52))
        mock_unit.type_id = Mock()

        target = self.queen_micro.find_transfuse_target(mock_queen, [mock_unit])
        self.assertIsNotNone(target)
        self.assertEqual(target.tag, 54321)

    def test_find_transfuse_target_out_of_range(self):
        """Test transfuse target when injured unit is out of range"""
        mock_queen = Mock()
        mock_queen.tag = 12345
        mock_queen.position = Point2((50, 50))

        # Injured but far away
        mock_unit = Mock()
        mock_unit.tag = 54321
        mock_unit.health = 30
        mock_unit.health_max = 100
        mock_unit.position = Point2((70, 70))  # > 7 range
        mock_unit.type_id = Mock()

        target = self.queen_micro.find_transfuse_target(mock_queen, [mock_unit])
        self.assertIsNone(target)


class TestViperMicro(unittest.TestCase):
    """Test suite for ViperMicro"""

    def setUp(self):
        """Set up test fixtures"""
        self.viper_micro = ViperMicro()

    def test_initialization(self):
        """Test ViperMicro initialization"""
        self.assertEqual(self.viper_micro.abduct_energy_cost, 75)
        self.assertEqual(self.viper_micro.abduct_range, 9.0)

    def test_find_abduct_target_no_enemies(self):
        """Test abduct target with no enemies"""
        mock_viper = Mock()
        mock_viper.position = Point2((50, 50))

        target = self.viper_micro.find_abduct_target(mock_viper, [])
        self.assertIsNone(target)

    def test_find_abduct_target_no_priority(self):
        """Test abduct target with no priority targets"""
        mock_viper = Mock()
        mock_viper.position = Point2((50, 50))

        # Non-priority enemy
        mock_enemy = Mock()
        mock_enemy.type_id = Mock()  # Not in priority set
        mock_enemy.position = Point2((55, 50))

        target = self.viper_micro.find_abduct_target(mock_viper, [mock_enemy])
        self.assertIsNone(target)


class TestCorruptorMicro(unittest.TestCase):
    """Test suite for CorruptorMicro"""

    def setUp(self):
        """Set up test fixtures"""
        self.corruptor_micro = CorruptorMicro()

    def test_initialization(self):
        """Test CorruptorMicro initialization"""
        self.assertEqual(self.corruptor_micro.caustic_spray_energy_cost, 75)
        self.assertEqual(self.corruptor_micro.caustic_spray_range, 6.0)
        self.assertEqual(len(self.corruptor_micro.last_spray_time), 0)

    def test_cooldown_tracking(self):
        """Test Caustic Spray cooldown tracking"""
        mock_corruptor = Mock()
        mock_corruptor.tag = 12345

        # No cooldown initially
        self.assertFalse(self.corruptor_micro.is_on_cooldown(mock_corruptor, 100.0))

        # Set cooldown
        self.corruptor_micro.last_spray_time[12345] = 100.0

        # Should be on cooldown
        self.assertTrue(self.corruptor_micro.is_on_cooldown(mock_corruptor, 102.0))

        # Should be off cooldown after 10 seconds
        self.assertFalse(self.corruptor_micro.is_on_cooldown(mock_corruptor, 111.0))

    def test_find_spray_target_on_cooldown(self):
        """Test spray target when on cooldown"""
        mock_corruptor = Mock()
        mock_corruptor.tag = 12345
        mock_corruptor.position = Point2((50, 50))
        self.corruptor_micro.last_spray_time[12345] = 100.0

        mock_enemies = [Mock()]
        target = self.corruptor_micro.find_spray_target(mock_corruptor, mock_enemies, 102.0)
        self.assertIsNone(target)


class TestFocusFireCoordinator(unittest.TestCase):
    """Test suite for FocusFireCoordinator"""

    def setUp(self):
        """Set up test fixtures"""
        self.focus_fire = FocusFireCoordinator()

    def test_initialization(self):
        """Test FocusFireCoordinator initialization"""
        self.assertEqual(len(self.focus_fire.target_assignments), 0)
        self.assertEqual(len(self.focus_fire.target_damage_count), 0)

    def test_assign_target(self):
        """Test target assignment"""
        self.focus_fire.assign_target(12345, 54321)

        self.assertEqual(self.focus_fire.target_assignments[12345], 54321)
        self.assertEqual(self.focus_fire.target_damage_count[54321], 1)

    def test_reassign_target(self):
        """Test reassigning to new target"""
        # Initial assignment
        self.focus_fire.assign_target(12345, 54321)
        self.assertEqual(self.focus_fire.target_damage_count[54321], 1)

        # Reassign to different target
        self.focus_fire.assign_target(12345, 99999)
        self.assertEqual(self.focus_fire.target_damage_count[54321], 0)
        self.assertEqual(self.focus_fire.target_damage_count[99999], 1)

    def test_clear_dead_assignments(self):
        """Test clearing assignments for dead units"""
        # Assign some targets
        self.focus_fire.assign_target(111, 999)
        self.focus_fire.assign_target(222, 888)
        self.focus_fire.assign_target(333, 999)  # Same target as 111

        # Clear with only unit 111 alive, target 999 alive
        alive_units = {111}
        alive_enemies = {999}

        self.focus_fire.clear_dead_assignments(alive_units, alive_enemies)

        # Only unit 111's assignment should remain
        self.assertEqual(len(self.focus_fire.target_assignments), 1)
        self.assertIn(111, self.focus_fire.target_assignments)
        self.assertNotIn(222, self.focus_fire.target_assignments)
        self.assertNotIn(333, self.focus_fire.target_assignments)

        # Target 999 should have count 1 (only 111 remains)
        self.assertEqual(self.focus_fire.target_damage_count[999], 1)
        self.assertNotIn(888, self.focus_fire.target_damage_count)

    def test_select_focus_target_no_enemies(self):
        """Test focus target selection with no enemies"""
        mock_unit = Mock()
        mock_unit.position = Point2((50, 50))
        mock_unit.ground_range = 5
        mock_unit.is_flying = False

        target = self.focus_fire.select_focus_target(mock_unit, [])
        self.assertIsNone(target)

    def test_select_focus_target_prevent_overkill(self):
        """Test focus target selection prevents overkill"""
        mock_unit = Mock()
        mock_unit.position = Point2((50, 50))
        mock_unit.ground_range = 10
        mock_unit.is_flying = False

        # Create two enemies
        enemy1 = Mock()
        enemy1.tag = 111
        enemy1.position = Point2((55, 50))
        enemy1.health = 100
        enemy1.type_id = Mock()

        enemy2 = Mock()
        enemy2.tag = 222
        enemy2.position = Point2((56, 50))
        enemy2.health = 100
        enemy2.type_id = Mock()

        # Assign 2 units to enemy1
        self.focus_fire.target_damage_count[111] = 2
        self.focus_fire.target_damage_count[222] = 0

        # Should select enemy2 (less damage assigned)
        target = self.focus_fire.select_focus_target(mock_unit, [enemy1, enemy2])
        self.assertIsNotNone(target)
        self.assertEqual(target.tag, 222)


# Run tests
if __name__ == '__main__':
    unittest.main(verbosity=2)
