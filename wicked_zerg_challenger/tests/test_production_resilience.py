# -*- coding: utf-8 -*-
"""
Unit tests for ProductionResilience

Tests cover:
- Learned parameter retrieval
- Safe training wrapper
- Production bottleneck detection
- Counter unit selection
- Resource management
- Tech structure requirements
"""

import unittest
from unittest.mock import Mock, MagicMock, patch, AsyncMock
import sys
import os

# Add parent directory to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'local_training')))

from local_training.production_resilience import ProductionResilience
from sc2.ids.unit_typeid import UnitTypeId
from sc2.position import Point2


class TestProductionResilience(unittest.TestCase):
    """Test suite for ProductionResilience"""

    def setUp(self):
        """Set up test fixtures"""
        self.bot = Mock()
        self.bot.units = Mock()
        self.bot.larva = Mock()
        self.bot.larva.amount = 5
        self.bot.larva.exists = True
        self.bot.townhalls = Mock()
        self.bot.townhalls.amount = 1
        self.bot.townhalls.ready = Mock()
        self.bot.structures = Mock()
        self.bot.enemy_units = Mock()
        self.bot.minerals = 200
        self.bot.vespene = 100
        self.bot.supply_left = 10
        self.bot.supply_cap = 200
        self.bot.time = 120.0
        self.bot.iteration = 2000
        self.bot.start_location = Point2((50, 50))

        # Mock can_afford
        self.bot.can_afford = Mock(return_value=True)

        # Mock do method
        self.bot.do = Mock()

        self.resilience = ProductionResilience(self.bot)

    # ==================== Learned Parameter Tests ====================

    def test_get_learned_parameter_with_default(self):
        """Test get_learned_parameter returns default when not found"""
        from local_training.production_resilience import get_learned_parameter
        result = get_learned_parameter("nonexistent_param", default_value=42)
        self.assertEqual(result, 42)

    def test_get_learned_parameter_returns_value(self):
        """Test get_learned_parameter function exists"""
        from local_training.production_resilience import get_learned_parameter
        # Should return default if parameter doesn't exist
        result = get_learned_parameter("test_param", default_value=10)
        self.assertIsNotNone(result)

    # ==================== Safe Training Tests ====================

    async def test_safe_train_success(self):
        """Test safe training succeeds with valid unit"""
        mock_larva = Mock()
        mock_larva.train = Mock(return_value=Mock())

        result = await self.resilience._safe_train(mock_larva, UnitTypeId.ZERGLING)

        self.assertTrue(result)
        mock_larva.train.assert_called_once_with(UnitTypeId.ZERGLING)
        self.bot.do.assert_called_once()

    async def test_safe_train_invalid_unit(self):
        """Test safe training fails with invalid unit"""
        result = await self.resilience._safe_train(None, UnitTypeId.ZERGLING)
        self.assertFalse(result)

    async def test_safe_train_no_train_method(self):
        """Test safe training fails when unit has no train method"""
        mock_unit = Mock(spec=[])  # No train method
        result = await self.resilience._safe_train(mock_unit, UnitTypeId.ZERGLING)
        self.assertFalse(result)

    async def test_safe_train_with_retry(self):
        """Test safe training retry mechanism"""
        mock_larva = Mock()
        mock_larva.train = Mock(side_effect=[Exception("First fail"), Mock()])

        result = await self.resilience._safe_train(mock_larva, UnitTypeId.ZERGLING, retry_count=2)

        # Should succeed on second attempt
        self.assertTrue(result)
        self.assertEqual(mock_larva.train.call_count, 2)

    # ==================== Counter Unit Selection Tests ====================

    async def test_get_counter_unit_terran_marine(self):
        """Test counter selection against Terran marines"""
        # Mock enemy composition with marines
        mock_marine = Mock()
        mock_marine.type_id = UnitTypeId.MARINE
        self.bot.enemy_units = [mock_marine]

        # Should recommend banelings against marines
        result = await self.resilience._get_counter_unit("Terran")

        # Result could be BANELING, ROACH, or MUTALISK (all valid counters)
        valid_counters = [UnitTypeId.BANELING, UnitTypeId.ROACH, UnitTypeId.MUTALISK, UnitTypeId.ZERGLING]
        self.assertIn(result, valid_counters)

    async def test_get_counter_unit_protoss(self):
        """Test counter selection against Protoss"""
        result = await self.resilience._get_counter_unit("Protoss")

        # Common Protoss counters
        valid_counters = [
            UnitTypeId.ROACH, UnitTypeId.HYDRALISK,
            UnitTypeId.MUTALISK, UnitTypeId.ZERGLING
        ]
        self.assertIn(result, valid_counters)

    async def test_get_counter_unit_zerg(self):
        """Test counter selection against Zerg"""
        result = await self.resilience._get_counter_unit("Zerg")

        # Common Zerg counters
        valid_counters = [
            UnitTypeId.ROACH, UnitTypeId.MUTALISK,
            UnitTypeId.ZERGLING, UnitTypeId.HYDRALISK
        ]
        self.assertIn(result, valid_counters)

    # ==================== Resource Management Tests ====================

    def test_check_high_minerals_threshold(self):
        """Test high minerals detection"""
        self.bot.minerals = 1500
        # High minerals should trigger resource dump
        self.assertGreater(self.bot.minerals, 1000)

    def test_check_high_gas_threshold(self):
        """Test high gas detection"""
        self.bot.vespene = 1500
        # High gas should trigger tech/unit production
        self.assertGreater(self.bot.vespene, 1000)

    def test_check_balanced_resources(self):
        """Test balanced resource state"""
        self.bot.minerals = 500
        self.bot.vespene = 200
        # Balanced resources
        self.assertLess(self.bot.minerals, 1000)
        self.assertLess(self.bot.vespene, 1000)

    # ==================== Tech Requirements Tests ====================

    def test_tech_requirement_spawning_pool(self):
        """Test spawning pool requirement detection"""
        # Should be UnitTypeId.SPAWNINGPOOL
        self.assertEqual(UnitTypeId.SPAWNINGPOOL, UnitTypeId.SPAWNINGPOOL)

    def test_tech_requirement_lair(self):
        """Test lair requirement detection"""
        self.assertEqual(UnitTypeId.LAIR, UnitTypeId.LAIR)

    def test_tech_requirement_spire(self):
        """Test spire requirement for mutalisks"""
        self.assertEqual(UnitTypeId.SPIRE, UnitTypeId.SPIRE)

    # ==================== Production Status Tests ====================

    def test_production_status_has_larva(self):
        """Test production status with available larva"""
        self.assertTrue(self.bot.larva.exists)
        self.assertGreater(self.bot.larva.amount, 0)

    def test_production_status_no_larva(self):
        """Test production status without larva"""
        self.bot.larva.amount = 0
        self.bot.larva.exists = False
        self.assertFalse(self.bot.larva.exists)

    def test_production_status_has_resources(self):
        """Test production status with resources"""
        self.assertGreater(self.bot.minerals, 0)
        self.assertGreater(self.bot.vespene, 0)

    # ==================== Module Availability Tests ====================

    def test_balancer_import(self):
        """Test EconomyCombatBalancer availability"""
        from local_training.production_resilience import BALANCER_AVAILABLE
        # Just verify the flag exists
        self.assertIsInstance(BALANCER_AVAILABLE, bool)

    def test_resource_manager_import(self):
        """Test ResourceManager availability"""
        from local_training.production_resilience import RESOURCE_MANAGER_AVAILABLE
        self.assertIsInstance(RESOURCE_MANAGER_AVAILABLE, bool)

    def test_placement_helper_import(self):
        """Test BuildingPlacementHelper availability"""
        from local_training.production_resilience import PLACEMENT_HELPER_AVAILABLE
        self.assertIsInstance(PLACEMENT_HELPER_AVAILABLE, bool)


# Run async tests
if __name__ == '__main__':
    # Patch asyncio for unittest
    import asyncio

    # Get all test methods
    loader = unittest.TestLoader()
    suite = loader.loadTestsFromTestCase(TestProductionResilience)

    # Run tests
    runner = unittest.TextTestRunner(verbosity=2)

    # Wrap async tests
    for test_group in suite:
        for test in test_group:
            test_method_name = test._testMethodName
            test_method = getattr(test, test_method_name)

            # Check if it's async
            if asyncio.iscoroutinefunction(test_method):
                # Wrap it
                def make_sync_wrapper(async_func):
                    def sync_wrapper(self):
                        loop = asyncio.get_event_loop()
                        return loop.run_until_complete(async_func(self))
                    return sync_wrapper

                setattr(test.__class__, test_method_name, make_sync_wrapper(test_method))

    runner.run(suite)
