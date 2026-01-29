# -*- coding: utf-8 -*-
"""
Unit Tests for unit_helpers.py

Tests all 11 utility functions:
- find_nearby_enemies
- get_health_ratio
- get_shield_ratio
- filter_workers_by_task
- execute_unit_action
- calculate_unit_supply
- is_unit_idle
- is_unit_attacking
- get_unit_range
- can_unit_attack
"""

import unittest
from unittest.mock import Mock, MagicMock, patch
import sys
import os

# Add parent directory to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from utils.unit_helpers import (
    find_nearby_enemies,
    get_health_ratio,
    get_shield_ratio,
    filter_workers_by_task,
    execute_unit_action,
    calculate_unit_supply,
    is_unit_idle,
    is_unit_attacking,
    get_unit_range,
    can_unit_attack
)


class MockUnit:
    """Mock unit for testing"""
    def __init__(self, tag=1, health=100, health_max=100, shield=0, shield_max=0,
                 supply_cost=2, position_x=10, position_y=10, is_idle=False,
                 is_flying=False, ground_range=5.0, air_range=0.0):
        self.tag = tag
        self.health = health
        self.health_max = health_max
        self.shield = shield
        self.shield_max = shield_max
        self.supply_cost = supply_cost
        self.position = Mock(x=position_x, y=position_y)
        self.is_idle = is_idle
        self.is_flying = is_flying
        self.ground_range = ground_range
        self.air_range = air_range
        self.is_attacking = False
        self.orders = []
        self.type_id = Mock(name="ZERGLING")

    def distance_to(self, target):
        """Calculate distance to target"""
        if hasattr(target, 'position'):
            target_pos = target.position
        else:
            target_pos = target
        dx = self.position.x - target_pos.x
        dy = self.position.y - target_pos.y
        return (dx**2 + dy**2)**0.5

    def can_attack(self, target):
        """Check if can attack target"""
        return True


class MockUnits:
    """Mock Units collection"""
    def __init__(self, units):
        self.units = units

    def __iter__(self):
        return iter(self.units)

    def __len__(self):
        return len(self.units)

    def closer_than(self, distance, unit):
        """Return units closer than distance"""
        return MockUnits([u for u in self.units if u.distance_to(unit) < distance])

    def filter(self, func):
        """Filter units by function"""
        return MockUnits([u for u in self.units if func(u)])

    def first(self):
        """Return first unit"""
        return self.units[0] if self.units else None


class TestFindNearbyEnemies(unittest.TestCase):
    """Test find_nearby_enemies function"""

    def test_find_enemies_within_range(self):
        """Test finding enemies within specified range"""
        unit = MockUnit(position_x=10, position_y=10)
        enemy1 = MockUnit(tag=2, position_x=12, position_y=10)  # Distance 2
        enemy2 = MockUnit(tag=3, position_x=20, position_y=10)  # Distance 10
        enemies = MockUnits([enemy1, enemy2])

        result = find_nearby_enemies(unit, enemies, 5.0)
        self.assertEqual(len(result.units), 1)
        self.assertEqual(result.units[0].tag, 2)

    def test_find_enemies_empty_collection(self):
        """Test with empty enemy collection"""
        unit = MockUnit()
        enemies = MockUnits([])
        result = find_nearby_enemies(unit, enemies, 5.0)
        self.assertEqual(len(result), 0)

    def test_find_enemies_none_unit(self):
        """Test with None unit"""
        enemies = MockUnits([MockUnit()])
        result = find_nearby_enemies(None, enemies, 5.0)
        self.assertEqual(len(result), 0)


class TestGetHealthRatio(unittest.TestCase):
    """Test get_health_ratio function"""

    def test_full_health(self):
        """Test unit at full health"""
        unit = MockUnit(health=100, health_max=100)
        self.assertEqual(get_health_ratio(unit), 1.0)

    def test_half_health(self):
        """Test unit at half health"""
        unit = MockUnit(health=50, health_max=100)
        self.assertEqual(get_health_ratio(unit), 0.5)

    def test_zero_health(self):
        """Test unit at zero health"""
        unit = MockUnit(health=0, health_max=100)
        self.assertEqual(get_health_ratio(unit), 0.0)

    def test_none_unit(self):
        """Test with None unit"""
        self.assertEqual(get_health_ratio(None), 0.0)

    def test_missing_attributes(self):
        """Test unit without health attributes"""
        unit = Mock(spec=[])
        self.assertEqual(get_health_ratio(unit), 0.0)


class TestGetShieldRatio(unittest.TestCase):
    """Test get_shield_ratio function"""

    def test_full_shield(self):
        """Test Protoss unit with full shield"""
        unit = MockUnit(shield=100, shield_max=100)
        self.assertEqual(get_shield_ratio(unit), 1.0)

    def test_half_shield(self):
        """Test unit with half shield"""
        unit = MockUnit(shield=50, shield_max=100)
        self.assertEqual(get_shield_ratio(unit), 0.5)

    def test_no_shield(self):
        """Test unit with no shield (Zerg/Terran)"""
        unit = MockUnit(shield=0, shield_max=0)
        self.assertEqual(get_shield_ratio(unit), 0.0)

    def test_none_unit(self):
        """Test with None unit"""
        self.assertEqual(get_shield_ratio(None), 0.0)


class TestFilterWorkersByTask(unittest.TestCase):
    """Test filter_workers_by_task function"""

    def test_filter_idle_workers(self):
        """Test filtering idle workers"""
        worker1 = MockUnit(tag=1, is_idle=True)
        worker2 = MockUnit(tag=2, is_idle=False)
        workers = MockUnits([worker1, worker2])

        result = filter_workers_by_task(workers, lambda w: w.is_idle)
        self.assertEqual(len(result.units), 1)
        self.assertTrue(result.units[0].is_idle)

    def test_filter_empty_collection(self):
        """Test filtering empty collection"""
        workers = MockUnits([])
        result = filter_workers_by_task(workers, lambda w: w.is_idle)
        self.assertEqual(len(result), 0)

    def test_filter_none_workers(self):
        """Test with None workers"""
        result = filter_workers_by_task(None, lambda w: True)
        self.assertEqual(len(result), 0)


class TestExecuteUnitAction(unittest.TestCase):
    """Test execute_unit_action function"""

    def test_successful_action(self):
        """Test successful action execution"""
        unit = MockUnit()
        action = Mock()
        result = execute_unit_action(unit, action, "arg1", kwarg1="value1")
        self.assertTrue(result)
        action.assert_called_once_with("arg1", kwarg1="value1")

    def test_failed_action_attribute_error(self):
        """Test action with AttributeError"""
        unit = MockUnit()
        action = Mock(side_effect=AttributeError("Test error"))
        result = execute_unit_action(unit, action)
        self.assertFalse(result)

    def test_failed_action_type_error(self):
        """Test action with TypeError"""
        unit = MockUnit()
        action = Mock(side_effect=TypeError("Test error"))
        result = execute_unit_action(unit, action)
        self.assertFalse(result)

    def test_none_unit(self):
        """Test with None unit"""
        action = Mock()
        result = execute_unit_action(None, action)
        self.assertFalse(result)
        action.assert_not_called()


class TestCalculateUnitSupply(unittest.TestCase):
    """Test calculate_unit_supply function"""

    def test_calculate_total_supply(self):
        """Test calculating total supply"""
        unit1 = MockUnit(supply_cost=2)
        unit2 = MockUnit(supply_cost=1)
        unit3 = MockUnit(supply_cost=3)
        units = MockUnits([unit1, unit2, unit3])

        result = calculate_unit_supply(units)
        self.assertEqual(result, 6)

    def test_empty_collection(self):
        """Test with empty collection"""
        units = MockUnits([])
        result = calculate_unit_supply(units)
        self.assertEqual(result, 0)

    def test_none_units(self):
        """Test with None units"""
        result = calculate_unit_supply(None)
        self.assertEqual(result, 0)

    def test_units_without_supply_cost(self):
        """Test units without supply_cost attribute"""
        unit = Mock(spec=[])
        units = MockUnits([unit])
        result = calculate_unit_supply(units)
        self.assertEqual(result, 1)  # Fallback to count


class TestIsUnitIdle(unittest.TestCase):
    """Test is_unit_idle function"""

    def test_idle_unit(self):
        """Test idle unit"""
        unit = MockUnit(is_idle=True)
        self.assertTrue(is_unit_idle(unit))

    def test_busy_unit(self):
        """Test busy unit"""
        unit = MockUnit(is_idle=False)
        self.assertFalse(is_unit_idle(unit))

    def test_none_unit(self):
        """Test with None unit"""
        self.assertFalse(is_unit_idle(None))

    def test_unit_without_is_idle(self):
        """Test unit without is_idle attribute"""
        unit = Mock(spec=[])
        self.assertFalse(is_unit_idle(unit))


class TestIsUnitAttacking(unittest.TestCase):
    """Test is_unit_attacking function"""

    def test_attacking_unit(self):
        """Test unit that is attacking"""
        unit = MockUnit()
        unit.is_attacking = True
        self.assertTrue(is_unit_attacking(unit))

    def test_not_attacking_unit(self):
        """Test unit that is not attacking"""
        unit = MockUnit()
        unit.is_attacking = False
        self.assertFalse(is_unit_attacking(unit))

    def test_none_unit(self):
        """Test with None unit"""
        self.assertFalse(is_unit_attacking(None))

    def test_unit_with_attack_order(self):
        """Test unit with attack order"""
        unit = MockUnit()
        delattr(unit, 'is_attacking')  # Remove is_attacking to test fallback
        order = Mock()
        order.ability = Mock()
        order.ability.button_name = "ATTACK"
        unit.orders = [order]
        self.assertTrue(is_unit_attacking(unit))


class TestGetUnitRange(unittest.TestCase):
    """Test get_unit_range function"""

    def test_ground_range(self):
        """Test getting ground attack range"""
        unit = MockUnit(ground_range=5.0, air_range=0.0)
        self.assertEqual(get_unit_range(unit), 5.0)

    def test_air_range(self):
        """Test getting air attack range"""
        unit = Mock(spec=['air_range'])
        unit.air_range = 7.0
        self.assertEqual(get_unit_range(unit), 7.0)

    def test_no_range(self):
        """Test unit with no attack range"""
        unit = Mock(spec=[])
        self.assertEqual(get_unit_range(unit), 0.0)

    def test_none_unit(self):
        """Test with None unit"""
        self.assertEqual(get_unit_range(None), 0.0)


class TestCanUnitAttack(unittest.TestCase):
    """Test can_unit_attack function"""

    def test_can_attack_in_range(self):
        """Test unit can attack target in range"""
        unit = MockUnit(position_x=10, position_y=10, ground_range=5.0)
        target = MockUnit(position_x=12, position_y=10)  # Distance 2
        self.assertTrue(can_unit_attack(unit, target))

    def test_cannot_attack_out_of_range(self):
        """Test unit cannot attack target out of range"""
        unit = MockUnit(position_x=10, position_y=10, ground_range=5.0)
        target = MockUnit(position_x=30, position_y=10)  # Distance 20
        self.assertFalse(can_unit_attack(unit, target))

    def test_cannot_attack_no_range(self):
        """Test unit with no attack range"""
        unit = MockUnit(ground_range=0.0, air_range=0.0)
        target = MockUnit()
        self.assertFalse(can_unit_attack(unit, target))

    def test_none_unit(self):
        """Test with None unit"""
        target = MockUnit()
        self.assertFalse(can_unit_attack(None, target))

    def test_none_target(self):
        """Test with None target"""
        unit = MockUnit()
        self.assertFalse(can_unit_attack(unit, None))


if __name__ == '__main__':
    # Run all tests
    unittest.main(verbosity=2)
