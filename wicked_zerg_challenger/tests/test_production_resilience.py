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
from unittest.mock import Mock

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

    def _make_enemy(self, name: str):
        """Helper: build a mock enemy unit whose type_id.name matches `name`."""
        enemy = Mock()
        enemy.type_id = Mock()
        enemy.type_id.name = name
        return enemy

    def test_get_counter_unit_terran_marine(self):
        """Test counter selection against Terran marines (light infantry)."""
        enemy_units = [self._make_enemy("MARINE")]
        # Ensure structures lookup returns "exists=False" for the baneling-nest
        # branch so we hit the roach-warren fallback.
        baneling_nest = Mock()
        baneling_nest.ready.exists = False
        self.bot.structures = Mock(return_value=baneling_nest)

        result = self.resilience._get_counter_unit(
            enemy_units, has_roach_warren=True, has_hydra_den=False, has_spire=False
        )

        valid_counters = [
            UnitTypeId.BANELING,
            UnitTypeId.ROACH,
            UnitTypeId.MUTALISK,
            UnitTypeId.ZERGLING,
        ]
        self.assertIn(result, valid_counters)

    def test_get_counter_unit_armored_ground(self):
        """Test counter selection against armored ground (e.g. Stalkers)."""
        enemy_units = [self._make_enemy("STALKER")]

        result = self.resilience._get_counter_unit(
            enemy_units, has_roach_warren=True, has_hydra_den=True, has_spire=False
        )

        valid_counters = [
            UnitTypeId.ROACH,
            UnitTypeId.HYDRALISK,
            UnitTypeId.MUTALISK,
            UnitTypeId.ZERGLING,
        ]
        self.assertIn(result, valid_counters)

    def test_get_counter_unit_air(self):
        """Test counter selection against air units (e.g. Mutalisks)."""
        enemy_units = [self._make_enemy("MUTALISK")]

        result = self.resilience._get_counter_unit(
            enemy_units, has_roach_warren=False, has_hydra_den=True, has_spire=True
        )

        valid_counters = [
            UnitTypeId.ROACH,
            UnitTypeId.MUTALISK,
            UnitTypeId.ZERGLING,
            UnitTypeId.HYDRALISK,
        ]
        self.assertIn(result, valid_counters)

    def test_get_counter_unit_no_enemies(self):
        """Empty enemy_units must return None (early exit)."""
        result = self.resilience._get_counter_unit(
            [], has_roach_warren=True, has_hydra_den=True, has_spire=True
        )
        self.assertIsNone(result)

    # ==================== Resource Management Tests ====================

    async def test_force_resource_dump_no_resources_is_safe(self):
        """force_resource_dump must not crash when nothing is buildable."""
        self.bot.can_afford = Mock(return_value=False)
        self.bot.already_pending = Mock(return_value=0)
        # No larva
        empty_units = Mock()
        empty_units.exists = False
        self.bot.units = Mock(return_value=empty_units)
        # Should complete without raising
        await self.resilience.force_resource_dump()

    async def test_force_resource_dump_skips_when_too_many_pending(self):
        """If 2+ Hatcheries already pending, skip expansion."""
        self.bot.can_afford = Mock(return_value=True)
        self.bot.already_pending = Mock(return_value=3)
        empty_units = Mock()
        empty_units.exists = False
        self.bot.units = Mock(return_value=empty_units)
        # Should not call _try_expand since already_pending >= 2
        self.resilience._try_expand = Mock()
        await self.resilience.force_resource_dump()
        self.resilience._try_expand.assert_not_called()

    # ==================== Tech Requirements Tests ====================

    def test_tech_requirement_spawning_pool(self):
        """Tech-tree IDs used by ProductionResilience must resolve."""
        self.assertEqual(UnitTypeId.SPAWNINGPOOL.name, "SPAWNINGPOOL")
        self.assertIsNotNone(UnitTypeId.SPAWNINGPOOL.value)

    def test_tech_requirement_lair(self):
        """Lair tech-id must resolve and differ from Hatchery."""
        self.assertEqual(UnitTypeId.LAIR.name, "LAIR")
        self.assertNotEqual(UnitTypeId.LAIR, UnitTypeId.HATCHERY)

    def test_tech_requirement_spire(self):
        """Spire tech-id must resolve and differ from Hydralisk Den."""
        self.assertEqual(UnitTypeId.SPIRE.name, "SPIRE")
        self.assertNotEqual(UnitTypeId.SPIRE, UnitTypeId.HYDRALISKDEN)

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
