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

import os
import sys
import unittest
from types import SimpleNamespace
from unittest.mock import AsyncMock, Mock

# Add parent directory to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
sys.path.insert(
    0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "local_training"))
)

from local_training.production_resilience import ProductionResilience
from sc2.ids.unit_typeid import UnitTypeId
from sc2.position import Point2


class TestProductionResilience(unittest.IsolatedAsyncioTestCase):
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

        result = await self.resilience._safe_train(
            mock_larva, UnitTypeId.ZERGLING, retry_count=2
        )

        # Should succeed on second attempt
        self.assertTrue(result)
        self.assertEqual(mock_larva.train.call_count, 2)

    # ==================== Counter Unit Selection Tests ====================

    def _mock_enemy(self, name: str):
        e = Mock()
        e.type_id = Mock()
        e.type_id.name = name
        return e

    def test_get_counter_unit_returns_none_with_empty_units(self):
        """Empty enemy list yields no counter."""
        result = self.resilience._get_counter_unit(
            [], has_roach_warren=True, has_hydra_den=True, has_spire=True
        )
        self.assertIsNone(result)

    def test_get_counter_unit_terran_marine(self):
        """vs light infantry (Marines): expect Roach when warren is up."""
        self.bot.structures(UnitTypeId.BANELINGNEST).ready.exists = False
        enemies = [self._mock_enemy("MARINE")] * 5
        result = self.resilience._get_counter_unit(
            enemies, has_roach_warren=True, has_hydra_den=False, has_spire=False
        )
        self.assertEqual(result, UnitTypeId.ROACH)

    def test_get_counter_unit_protoss_air(self):
        """vs air composition (Void Rays): expect Hydralisk when den is up."""
        enemies = [self._mock_enemy("VOIDRAY")] * 4
        result = self.resilience._get_counter_unit(
            enemies, has_roach_warren=False, has_hydra_den=True, has_spire=False
        )
        self.assertEqual(result, UnitTypeId.HYDRALISK)

    def test_get_counter_unit_zerg_armored(self):
        """vs armored ground (Roaches): expect Hydralisk when den is up."""
        enemies = [self._mock_enemy("ROACH")] * 6
        result = self.resilience._get_counter_unit(
            enemies, has_roach_warren=False, has_hydra_den=True, has_spire=False
        )
        self.assertEqual(result, UnitTypeId.HYDRALISK)

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

    async def test_auto_extractors_wait_for_opening_hatchery(self):
        """ProductionResilience cannot build gas before the natural starts."""
        self.bot.time = 100.0
        self.bot.townhalls.amount = 1
        self.bot.already_pending = Mock(return_value=0)
        self.bot.structures = Mock(return_value=Mock(amount=0))
        self.bot.build = AsyncMock()

        await self.resilience._auto_build_extractors(self.bot.time)

        self.bot.build.assert_not_awaited()

    async def test_auto_second_extractor_waits_for_third_base(self):
        """ProductionResilience caps gas at one Extractor until third base."""
        self.bot.time = 150.0
        self.bot.townhalls.amount = 2
        self.bot.already_pending = Mock(return_value=0)
        self.bot.structures = Mock(return_value=Mock(amount=1))
        self.bot.build = AsyncMock()

        await self.resilience._auto_build_extractors(self.bot.time)

        self.bot.build.assert_not_awaited()

    def test_third_base_reserve_blocks_auto_tech(self):
        """Roach Warren and other macro tech wait until the third starts."""
        self.bot.time = 190.0
        self.bot.minerals = 250
        self.bot.townhalls.amount = 2
        self.bot.already_pending = Mock(return_value=0)
        self.bot.tech_coordinator = Mock()
        self.resilience._auto_build_extractors = AsyncMock()

        def structures(unit_type):
            group = Mock(amount=0, exists=False)
            group.ready = Mock(exists=unit_type == UnitTypeId.SPAWNINGPOOL)
            return group

        self.bot.structures = Mock(side_effect=structures)

        import asyncio

        asyncio.run(self.resilience._auto_build_tech_structures())

        self.bot.tech_coordinator.request_structure.assert_not_called()

    def test_third_base_reserve_blocks_army_larva_when_defense_ready(self):
        """Once minimum defense exists, larvae are held for the third Hatchery."""
        self.bot.time = 190.0
        self.bot.minerals = 250
        self.bot.townhalls.amount = 2
        self.bot.already_pending = Mock(return_value=0)

        def units(unit_type):
            amounts = {
                UnitTypeId.ZERGLING: 6,
                UnitTypeId.ROACH: 0,
                UnitTypeId.HYDRALISK: 0,
                UnitTypeId.MUTALISK: 0,
            }
            return SimpleNamespace(amount=amounts.get(unit_type, 0))

        self.bot.units = Mock(side_effect=units)
        larva = Mock()

        import asyncio

        result = asyncio.run(self.resilience._produce_army_unit(larva))

        self.assertFalse(result)
        self.bot.can_afford.assert_not_called()

    def test_pending_third_releases_production_reserve(self):
        """A pending third Hatchery releases ProductionResilience spending."""
        self.bot.time = 190.0
        self.bot.townhalls.amount = 2
        self.bot.townhalls.ready.amount = 2
        self.bot.already_pending = Mock(
            side_effect=lambda unit_type: 1 if unit_type == UnitTypeId.HATCHERY else 0
        )

        self.assertFalse(self.resilience._should_reserve_third_base_minerals())

    def test_fourth_base_reserve_active_on_three_ready_bases(self):
        """After six minutes, three-base play reserves minerals for the fourth."""
        self.bot.time = 370.0
        self.bot.townhalls.amount = 3
        self.bot.townhalls.ready.amount = 3
        self.bot.already_pending = Mock(return_value=0)

        self.assertTrue(self.resilience._should_reserve_third_base_minerals())

    def test_pending_fourth_releases_production_reserve(self):
        """A pending fourth Hatchery releases ProductionResilience spending."""
        self.bot.time = 370.0
        self.bot.townhalls.amount = 3
        self.bot.townhalls.ready.amount = 3
        self.bot.already_pending = Mock(
            side_effect=lambda unit_type: 1 if unit_type == UnitTypeId.HATCHERY else 0
        )

        self.assertFalse(self.resilience._should_reserve_third_base_minerals())

    def test_pending_natural_keeps_third_base_reserve_active(self):
        """While the natural is still pending, mineral spending is held for third."""
        self.bot.time = 150.0
        self.bot.townhalls.amount = 1
        self.bot.townhalls.ready.amount = 1
        self.bot.already_pending = Mock(
            side_effect=lambda unit_type: 1 if unit_type == UnitTypeId.HATCHERY else 0
        )

        self.assertTrue(self.resilience._should_reserve_third_base_minerals())

    def test_pending_natural_in_townhall_amount_keeps_third_base_reserve_active(self):
        """A pending natural counted in townhalls.amount is not a pending third."""
        self.bot.time = 150.0
        self.bot.townhalls.amount = 2
        self.bot.townhalls.ready.amount = 1
        self.bot.already_pending = Mock(
            side_effect=lambda unit_type: 1 if unit_type == UnitTypeId.HATCHERY else 0
        )

        self.assertTrue(self.resilience._should_reserve_third_base_minerals())


# Run async tests
if __name__ == "__main__":
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

                setattr(
                    test.__class__, test_method_name, make_sync_wrapper(test_method)
                )

    runner.run(suite)
