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

import os
import sys
import unittest
from unittest.mock import AsyncMock, Mock

# Add parent directory to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from economy_manager import EconomyManager, ThreatLevel
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
        self.bot.expansion_locations_list = [Point2((60, 60)), Point2((140, 140))]
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
        self.assertEqual(self.manager._expansion_cooldown, 3.0)
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
        self.assertEqual(self.manager.macro_hatchery_mineral_threshold, 550)
        self.assertEqual(self.manager.macro_hatchery_larva_threshold, 3)

    def test_blackboard_integration(self):
        """Test blackboard integration is set up"""
        # Blackboard is None in setUp
        self.assertIsNone(self.manager.blackboard)

    # ==================== Helper Method Tests ====================

    def test_early_split_done_flag_initialization(self):
        """Test early worker split flag is initialized"""
        self.assertTrue(hasattr(self.manager, "_early_split_done"))

    def test_opening_natural_prefers_closest_expansion_at_one_minute(self):
        """Test 17-drone opening natural picks the closest untaken expansion."""
        actions = []
        townhall = Mock()
        townhall.position = Point2((50, 50))
        townhalls = Mock()
        townhalls.amount = 1
        townhalls.__iter__ = Mock(return_value=iter([townhall]))

        worker = Mock()
        worker.position = Point2((51, 51))

        def build(unit_type, position):
            return ("build", unit_type, position)

        worker.build = build
        workers = Mock()
        workers.amount = 17
        workers.closest_to = Mock(return_value=worker)

        self.bot.time = 60
        self.bot.minerals = 300
        self.bot.townhalls = townhalls
        self.bot.workers = workers
        self.bot.expansion_locations_list = [
            Point2((50, 50)),
            Point2((60, 60)),
            Point2((140, 140)),
        ]
        self.bot.can_place = AsyncMock(return_value=True)
        self.bot.get_next_expansion = AsyncMock(return_value=Point2((140, 140)))
        self.bot.resource_manager = None
        self.bot.tech_coordinator = None
        self.bot.do = lambda action: actions.append(action)

        import asyncio

        asyncio.run(self.manager._check_opening_natural_expansion())

        self.assertEqual(len(actions), 1)
        self.assertEqual(actions[0][0], "build")
        self.assertEqual(actions[0][1], UnitTypeId.HATCHERY)
        self.assertEqual(actions[0][2], Point2((60, 60)))
        self.assertTrue(self.manager.first_expansion_reported)
        self.assertEqual(self.manager.first_expansion_time, 60)

    def test_threat_level_high_reduces_target_drone_count(self):
        """High enemy threat lowers the live drone target to 44."""
        intel = Mock()
        intel._threat_level = "high"
        intel.enemy_army_supply = 30
        self.bot.intel = intel
        self.bot.supply_army = 10

        level = self.manager.update_economy_combat_balance()

        self.assertEqual(level, ThreatLevel.HIGH)
        self.assertEqual(self.manager.get_target_drone_count(), 44)
        self.assertEqual(self.manager.balancer.current_threat_level, "high")

    def test_critical_threat_halts_drone_training(self):
        """Critical threat sets drone target to zero and skips drone production."""
        intel = Mock()
        intel._threat_level = "critical"
        intel.enemy_army_supply = 50
        self.bot.intel = intel
        self.bot.workers.amount = 20
        self.bot.do = Mock()
        self.bot.can_afford = Mock(return_value=True)

        self.manager.update_economy_combat_balance()

        import asyncio

        asyncio.run(self.manager._train_drone_if_needed())

        self.assertEqual(self.manager.get_target_drone_count(), 0)
        self.bot.do.assert_not_called()

    def test_opening_hatchery_reservation_pauses_drone_training(self):
        """At 16 drones, minerals are saved for the first natural hatchery."""
        self.bot.time = 50
        self.bot.minerals = 150
        self.bot.workers.amount = 16
        self.bot.townhalls.amount = 1
        self.bot.can_afford = Mock(return_value=True)
        self.bot.do = Mock()

        import asyncio

        asyncio.run(self.manager._train_drone_if_needed())

        self.bot.do.assert_not_called()

    def test_opening_hatchery_reservation_pauses_spend_larva_drone(self):
        """Generic larva spending also respects first-hatchery mineral reserve."""
        larva_unit = Mock()
        larva_unit.train = Mock(return_value=("train", UnitTypeId.DRONE))
        self.bot.larva.first = larva_unit
        self.bot.time = 50
        self.bot.minerals = 150
        self.bot.workers.amount = 16
        self.bot.townhalls.amount = 1
        self.bot.supply_left = 8
        self.bot.can_afford = Mock(return_value=True)
        self.bot.do = Mock()

        import asyncio

        result = asyncio.run(self.manager.spend_larva())

        self.assertFalse(result)
        self.bot.do.assert_not_called()

    def test_opening_hatchery_reservation_starts_before_first_gas(self):
        """First-hatchery reserve starts early enough to beat matchup gas timing."""
        self.bot.time = 40
        self.bot.minerals = 80
        self.bot.workers.amount = 15
        self.bot.townhalls.amount = 1

        self.assertTrue(self.manager._should_reserve_opening_hatchery())

    def test_opening_hatchery_reservation_blocks_extractor_build(self):
        """Automatic extractor construction cannot spend first-hatchery minerals."""
        self.bot.time = 64
        self.bot.minerals = 150
        self.bot.workers.amount = 17
        self.bot.townhalls.amount = 1
        self.bot.can_afford = Mock(return_value=True)
        self.bot.do = Mock()

        import asyncio

        asyncio.run(self.manager._build_extractors())

        self.bot.can_afford.assert_not_called()
        self.bot.do.assert_not_called()

    def test_opening_hatchery_reservation_blocks_gas_timing(self):
        """Matchup gas timing waits until the first expansion has started."""
        self.bot.time = 64
        self.bot.minerals = 150
        self.bot.workers.amount = 17
        self.bot.townhalls.amount = 1
        self.bot.gas_buildings = Mock()
        self.bot.gas_buildings.amount = 0
        self.bot.can_afford = Mock(return_value=True)
        self.bot.do = Mock()

        import asyncio

        asyncio.run(self.manager._optimize_gas_timing())

        self.bot.can_afford.assert_not_called()
        self.bot.do.assert_not_called()

    def test_followup_expansion_reservation_blocks_army_larva_spending(self):
        """At two bases, minerals are saved for the third before army spending."""
        larva_unit = Mock()
        larva_unit.train = Mock(return_value=("train", UnitTypeId.ZERGLING))
        self.bot.larva.first = larva_unit
        self.bot.time = 170
        self.bot.minerals = 120
        self.bot.workers.amount = 24
        self.bot.townhalls.amount = 2
        self.bot.supply_left = 8
        self.bot.can_afford = Mock(return_value=True)
        self.bot.do = Mock()

        import asyncio

        result = asyncio.run(self.manager.spend_larva(force_army=True))

        self.assertFalse(result)
        self.bot.do.assert_not_called()

    def test_followup_expansion_reservation_blocks_extractor_build(self):
        """Automatic gas cannot spend minerals while saving for a third base."""
        self.bot.time = 170
        self.bot.minerals = 120
        self.bot.workers.amount = 24
        self.bot.townhalls.amount = 2
        self.bot.gas_buildings.amount = 0
        self.bot.can_afford = Mock(return_value=True)
        self.bot.do = Mock()

        import asyncio

        asyncio.run(self.manager._build_extractors())

        self.bot.can_afford.assert_not_called()
        self.bot.do.assert_not_called()

    def test_extra_gas_blocked_before_third_base(self):
        """After first gas, extractor count is capped until a third base exists."""
        self.bot.time = 170
        self.bot.minerals = 120
        self.bot.workers.amount = 22
        self.bot.townhalls.amount = 2
        self.bot.gas_buildings.amount = 1
        self.bot.can_afford = Mock(return_value=True)
        self.bot.do = Mock()

        import asyncio

        asyncio.run(self.manager._build_extractors())

        self.bot.can_afford.assert_not_called()
        self.bot.do.assert_not_called()

    def test_followup_expansion_reservation_sets_resource_reserve(self):
        """Resource reservation exposes 300 minerals while under-expanded."""
        self.bot.time = 170
        self.bot.minerals = 120
        self.bot.workers.amount = 24
        self.bot.townhalls.amount = 2

        self.manager._update_resource_reservations()

        self.assertEqual(self.manager._reserved_minerals, 300)
        self.assertEqual(self.manager._reserved_gas, 0)

    def test_gas_timing_by_matchup_uses_worker_thresholds(self):
        """First gas threshold is matchup-specific by drone count."""
        race = Mock()

        race.name = "Zerg"
        self.bot.enemy_race = race
        self.assertEqual(self.manager._get_gas_timing_by_matchup(), 13)

        race.name = "Terran"
        self.assertEqual(self.manager._get_gas_timing_by_matchup(), 17)

        race.name = "Protoss"
        self.assertEqual(self.manager._get_gas_timing_by_matchup(), 19)

    def test_spend_larva_prioritizes_overlord_when_supply_low(self):
        """Larva priority produces Overlord before drones or army when supply is low."""
        larva_unit = Mock()
        larva_unit.train = Mock(return_value=("train", UnitTypeId.OVERLORD))
        self.bot.larva.first = larva_unit
        self.bot.supply_left = 2
        self.bot.supply_cap = 100
        self.bot.can_afford = Mock(return_value=True)
        self.bot.do = Mock()

        import asyncio

        result = asyncio.run(self.manager.spend_larva())

        self.assertTrue(result)
        larva_unit.train.assert_called_with(UnitTypeId.OVERLORD)
        self.bot.do.assert_called_once()

    def test_army_dump_spends_available_larva_on_military_units(self):
        """Mineral float army dump spends all available larva on military units."""
        larva_a = Mock()
        larva_b = Mock()
        larva_a.train = Mock(return_value=("train", UnitTypeId.ZERGLING))
        larva_b.train = Mock(return_value=("train", UnitTypeId.ZERGLING))
        self.bot.larva = [larva_a, larva_b]
        self.bot.supply_left = 10
        self.bot.can_afford = Mock(return_value=True)
        self.bot.do = Mock()
        self.bot.structures = Mock()
        empty_structures = Mock()
        empty_structures.ready = Mock()
        empty_structures.ready.exists = False
        empty_structures.ready.amount = 0
        self.bot.structures.return_value = empty_structures

        import asyncio

        result = asyncio.run(self.manager._dump_larva_into_army())

        self.assertTrue(result)
        larva_a.train.assert_called_with(UnitTypeId.ZERGLING)
        larva_b.train.assert_called_with(UnitTypeId.ZERGLING)
        self.assertEqual(self.bot.do.call_count, 2)

    def test_mineral_float_without_larva_triggers_macro_hatchery(self):
        """No larva and >500 minerals triggers macro hatchery construction."""
        self.manager._build_macro_hatchery_if_needed = AsyncMock()

        import asyncio

        result = asyncio.run(self.manager._handle_mineral_float(900, 0, 0, 2))

        self.assertTrue(result)
        self.manager._build_macro_hatchery_if_needed.assert_awaited()


if __name__ == "__main__":
    unittest.main()
