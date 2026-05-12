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

import pytest

try:
    from sc2.ids.unit_typeid import UnitTypeId
    from sc2.position import Point2
except ImportError:  # pragma: no cover
    pytest.skip("sc2 library not available", allow_module_level=True)


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

    def test_force_expansion_uses_smart_expansion_not_expand_now(self):
        """Force expansion avoids ambiguous expand_now success reporting."""
        self.bot.time = 80
        self.bot.minerals = 300
        self.bot.townhalls.amount = 1
        self.bot.already_pending = Mock(return_value=0)
        self.bot.expand_now = AsyncMock(return_value=True)
        self.manager._perform_smart_expansion = AsyncMock(return_value=True)

        import asyncio

        asyncio.run(self.manager._force_expansion_if_stuck())

        self.manager._perform_smart_expansion.assert_awaited_once()
        self.bot.expand_now.assert_not_awaited()

    def test_proactive_expansion_uses_smart_expansion_not_expand_now(self):
        """Proactive expansion uses the verified worker-build path."""
        self.bot.time = 150
        self.bot.minerals = 300
        self.bot.townhalls.amount = 2
        self.bot.strategy_manager = None
        self.bot.already_pending = Mock(return_value=0)
        self.bot.can_afford = Mock(return_value=True)
        self.bot.expand_now = AsyncMock(return_value=True)
        self.manager._perform_smart_expansion = AsyncMock(return_value=True)

        import asyncio

        asyncio.run(self.manager._check_proactive_expansion())

        self.manager._perform_smart_expansion.assert_awaited_once()
        self.bot.expand_now.assert_not_awaited()

    def test_smart_expansion_direct_builds_even_with_tech_coordinator(self):
        """Smart expansion immediately issues Hatchery build to reserve minerals."""
        actions = []
        townhall = Mock()
        townhall.position = Point2((50, 50))
        townhalls = Mock()
        townhalls.amount = 1
        townhalls.__iter__ = Mock(return_value=iter([townhall]))

        worker = Mock()
        worker.build = Mock(
            return_value=("build", UnitTypeId.HATCHERY, Point2((60, 60)))
        )
        workers = Mock()
        workers.closest_to = Mock(return_value=worker)

        self.bot.time = 60
        self.bot.townhalls = townhalls
        self.bot.workers = workers
        self.bot.expansion_locations_list = [Point2((50, 50)), Point2((60, 60))]
        self.bot.can_place = AsyncMock(return_value=True)
        self.bot.resource_manager = None
        self.bot.tech_coordinator = Mock()
        self.bot.do = lambda action: actions.append(action)

        import asyncio

        result = asyncio.run(self.manager._perform_smart_expansion("test expansion"))

        self.assertTrue(result)
        self.bot.tech_coordinator.request_structure.assert_not_called()
        self.assertEqual(actions, [("build", UnitTypeId.HATCHERY, Point2((60, 60)))])

    def test_smart_expansion_uses_bot_build_when_available(self):
        """Runtime expansion uses BotAI.build so Hatchery cost is reserved."""
        townhall = Mock()
        townhall.position = Point2((50, 50))
        townhalls = Mock()
        townhalls.amount = 1
        townhalls.__iter__ = Mock(return_value=iter([townhall]))

        worker = Mock()
        worker.build = Mock()
        workers = Mock()
        workers.closest_to = Mock(return_value=worker)

        self.bot.time = 60
        self.bot.townhalls = townhalls
        self.bot.workers = workers
        self.bot.expansion_locations_list = [Point2((50, 50)), Point2((60, 60))]
        self.bot.can_place = AsyncMock(return_value=True)
        self.bot.resource_manager = None
        self.bot.build = AsyncMock(return_value=True)
        self.bot.do = Mock()

        import asyncio

        result = asyncio.run(self.manager._perform_smart_expansion("test expansion"))

        self.assertTrue(result)
        self.bot.build.assert_awaited_once_with(
            UnitTypeId.HATCHERY,
            near=Point2((60, 60)),
            max_distance=8,
            build_worker=worker,
            random_alternative=False,
        )
        worker.build.assert_not_called()
        self.bot.do.assert_not_called()

    def test_smart_expansion_skips_taken_natural_for_third(self):
        """Third base expansion must not reuse the existing natural location."""
        actions = []
        main = Mock()
        main.position = Point2((50, 50))
        natural = Mock()
        natural.position = Point2((60, 60))
        townhalls = Mock()
        townhalls.amount = 2
        townhalls.__iter__ = Mock(side_effect=lambda: iter([main, natural]))

        worker = Mock()

        def build(unit_type, position):
            return ("build", unit_type, position)

        worker.build = build
        workers = Mock()
        workers.closest_to = Mock(return_value=worker)

        self.bot.time = 176
        self.bot.townhalls = townhalls
        self.bot.workers = workers
        self.bot.expansion_locations_list = [
            Point2((50, 50)),
            Point2((60, 60)),
            Point2((75, 75)),
            Point2((120, 120)),
        ]
        self.bot.can_place = AsyncMock(return_value=True)
        self.bot.get_next_expansion = AsyncMock(return_value=Point2((60, 60)))
        self.bot.resource_manager = None
        self.bot.mineral_field.closer_than = Mock(return_value=[])
        self.bot.do = lambda action: actions.append(action)

        import asyncio

        result = asyncio.run(self.manager._perform_smart_expansion("third base"))

        self.assertTrue(result)
        self.assertEqual(actions, [("build", UnitTypeId.HATCHERY, Point2((75, 75)))])

    def test_third_base_skips_natural_when_hatchery_position_is_offset(self):
        """Expansion-site center and Hatchery position can differ by several tiles."""
        actions = []
        main = Mock()
        main.position = Point2((50, 50))
        natural = Mock()
        natural.position = Point2((60, 60))
        townhalls = Mock()
        townhalls.amount = 2
        townhalls.__iter__ = Mock(side_effect=lambda: iter([main, natural]))

        worker = Mock()
        worker.build = lambda unit_type, position: ("build", unit_type, position)
        workers = Mock()
        workers.closest_to = Mock(return_value=worker)

        self.bot.time = 176
        self.bot.townhalls = townhalls
        self.bot.workers = workers
        self.bot.expansion_locations_list = [
            Point2((50, 50)),
            Point2((70, 60)),
            Point2((85, 80)),
        ]
        self.bot.can_place = AsyncMock(return_value=True)
        self.bot.resource_manager = None
        self.bot.mineral_field.closer_than = Mock(return_value=[])
        self.bot.do = lambda action: actions.append(action)

        import asyncio

        result = asyncio.run(self.manager._perform_smart_expansion("third base"))

        self.assertTrue(result)
        self.assertEqual(actions, [("build", UnitTypeId.HATCHERY, Point2((85, 80)))])

    def test_third_base_prefers_standard_expansion_before_gold(self):
        """Before three ready bases, expansion should not choose exposed gold bases."""
        actions = []
        main = Mock()
        main.position = Point2((50, 50))
        natural = Mock()
        natural.position = Point2((60, 60))
        townhalls = Mock()
        townhalls.amount = 2
        townhalls.ready = [main, natural]
        townhalls.__iter__ = Mock(side_effect=lambda: iter([main, natural]))

        worker = Mock()

        def build(unit_type, position):
            return ("build", unit_type, position)

        worker.build = build
        workers = Mock()
        workers.closest_to = Mock(return_value=worker)

        gold_position = Point2((70, 70))
        standard_position = Point2((80, 80))
        gold_mineral = Mock()
        gold_mineral.mineral_contents = 1500
        standard_mineral = Mock()
        standard_mineral.mineral_contents = 900

        def minerals_near(_radius, position):
            if position.distance_to(gold_position) < 1:
                return [gold_mineral]
            return [standard_mineral]

        self.bot.time = 176
        self.bot.townhalls = townhalls
        self.bot.workers = workers
        self.bot.enemy_structures = []
        self.bot.expansion_locations_list = [
            Point2((50, 50)),
            Point2((60, 60)),
            gold_position,
            standard_position,
        ]
        self.bot.mineral_field.closer_than = Mock(side_effect=minerals_near)
        self.bot.can_place = AsyncMock(return_value=True)
        self.bot.resource_manager = None
        self.bot.do = lambda action: actions.append(action)

        import asyncio

        result = asyncio.run(self.manager._perform_smart_expansion("third base"))

        self.assertTrue(result)
        self.assertEqual(actions, [("build", UnitTypeId.HATCHERY, standard_position)])

    def test_gold_expansion_allowed_after_three_ready_bases(self):
        """Gold expansion priority resumes after a standard third is secured."""
        actions = []
        main = Mock()
        main.position = Point2((50, 50))
        natural = Mock()
        natural.position = Point2((60, 60))
        third = Mock()
        third.position = Point2((80, 80))
        townhalls = Mock()
        townhalls.amount = 3
        townhalls.ready = [main, natural, third]
        townhalls.__iter__ = Mock(side_effect=lambda: iter([main, natural, third]))

        worker = Mock()

        def build(unit_type, position):
            return ("build", unit_type, position)

        worker.build = build
        workers = Mock()
        workers.closest_to = Mock(return_value=worker)

        gold_position = Point2((70, 70))
        standard_position = Point2((90, 90))
        gold_mineral = Mock()
        gold_mineral.mineral_contents = 1500
        standard_mineral = Mock()
        standard_mineral.mineral_contents = 900

        def minerals_near(_radius, position):
            if position.distance_to(gold_position) < 1:
                return [gold_mineral]
            return [standard_mineral]

        self.bot.time = 260
        self.bot.townhalls = townhalls
        self.bot.workers = workers
        self.bot.enemy_structures = []
        self.bot.expansion_locations_list = [
            Point2((50, 50)),
            Point2((60, 60)),
            Point2((80, 80)),
            gold_position,
            standard_position,
        ]
        self.bot.mineral_field.closer_than = Mock(side_effect=minerals_near)
        self.bot.can_place = AsyncMock(return_value=True)
        self.bot.resource_manager = None
        self.bot.do = lambda action: actions.append(action)

        import asyncio

        result = asyncio.run(self.manager._perform_smart_expansion("fourth base"))

        self.assertTrue(result)
        self.assertEqual(actions, [("build", UnitTypeId.HATCHERY, gold_position)])

    def test_recent_opening_expansion_request_blocks_duplicate_command(self):
        """Opening natural command is not repeated before the game reports pending."""
        actions = []
        main = Mock()
        main.position = Point2((50, 50))
        townhalls = Mock()
        townhalls.amount = 1
        townhalls.__iter__ = Mock(side_effect=lambda: iter([main]))

        worker = Mock()
        worker.build = Mock(
            side_effect=lambda unit_type, position: ("build", unit_type, position)
        )
        workers = Mock()
        workers.closest_to = Mock(return_value=worker)

        self.bot.time = 100
        self.bot.townhalls = townhalls
        self.bot.workers = workers
        self.bot.expansion_locations_list = [Point2((50, 50)), Point2((60, 60))]
        self.bot.can_place = AsyncMock(return_value=True)
        self.bot.resource_manager = None
        self.bot.do = lambda action: actions.append(action)

        import asyncio

        first = asyncio.run(self.manager._perform_smart_expansion("natural"))
        self.bot.time = 104
        second = asyncio.run(self.manager._perform_smart_expansion("duplicate"))

        self.assertTrue(first)
        self.assertFalse(second)
        self.assertEqual(actions, [("build", UnitTypeId.HATCHERY, Point2((60, 60)))])

    def test_recent_third_expansion_request_blocks_duplicate_command(self):
        """A third-base worker in transit prevents another third Hatchery order."""
        actions = []
        main = Mock()
        main.position = Point2((50, 50))
        natural = Mock()
        natural.position = Point2((60, 60))
        townhalls = Mock()
        townhalls.amount = 2
        townhalls.__iter__ = Mock(side_effect=lambda: iter([main, natural]))

        worker = Mock()
        worker.build = Mock(
            side_effect=lambda unit_type, position: ("build", unit_type, position)
        )
        workers = Mock()
        workers.closest_to = Mock(return_value=worker)

        self.bot.time = 220
        self.bot.townhalls = townhalls
        self.bot.workers = workers
        self.bot.enemy_structures = []
        self.bot.enemy_units = []
        self.bot.expansion_locations_list = [
            Point2((50, 50)),
            Point2((60, 60)),
            Point2((80, 80)),
        ]
        self.bot.can_place = AsyncMock(return_value=True)
        self.bot.resource_manager = None
        self.bot.do = lambda action: actions.append(action)

        import asyncio

        first = asyncio.run(self.manager._perform_smart_expansion("third"))
        self.bot.time = 240
        second = asyncio.run(self.manager._perform_smart_expansion("duplicate third"))

        self.assertTrue(first)
        self.assertFalse(second)
        self.assertEqual(actions, [("build", UnitTypeId.HATCHERY, Point2((80, 80)))])

    def test_pending_third_blocks_duplicate_when_townhalls_count_includes_pending(self):
        """Some game states include an unfinished Hatchery in townhalls.amount."""
        main = Mock()
        main.position = Point2((50, 50))
        natural = Mock()
        natural.position = Point2((60, 60))
        townhalls = Mock()
        townhalls.amount = 3
        townhalls.ready = [main, natural]
        townhalls.__iter__ = Mock(side_effect=lambda: iter([main, natural]))

        self.bot.time = 353
        self.bot.townhalls = townhalls
        self.bot.already_pending = Mock(
            side_effect=lambda unit_type: 1 if unit_type == UnitTypeId.HATCHERY else 0
        )
        self.bot.enemy_structures = []
        self.bot.enemy_units = []
        self.bot.expansion_locations_list = [
            Point2((50, 50)),
            Point2((60, 60)),
            Point2((80, 80)),
        ]
        self.bot.can_place = AsyncMock(return_value=True)

        import asyncio

        result = asyncio.run(self.manager._perform_smart_expansion("duplicate third"))

        self.assertFalse(result)
        self.bot.can_place.assert_not_awaited()

    def test_expansion_candidate_skips_enemy_units_near_location(self):
        """Expansion selection avoids candidates covered by visible enemy units."""
        actions = []
        main = Mock()
        main.position = Point2((50, 50))
        natural = Mock()
        natural.position = Point2((60, 60))
        townhalls = Mock()
        townhalls.amount = 2
        townhalls.__iter__ = Mock(side_effect=lambda: iter([main, natural]))

        worker = Mock()
        worker.build = Mock(
            side_effect=lambda unit_type, position: ("build", unit_type, position)
        )
        workers = Mock()
        workers.closest_to = Mock(return_value=worker)
        enemy = Mock()
        enemy.position = Point2((80, 80))

        self.bot.time = 220
        self.bot.townhalls = townhalls
        self.bot.workers = workers
        self.bot.enemy_structures = []
        self.bot.enemy_units = [enemy]
        self.bot.expansion_locations_list = [
            Point2((50, 50)),
            Point2((60, 60)),
            Point2((80, 80)),
            Point2((95, 95)),
        ]
        self.bot.can_place = AsyncMock(return_value=True)
        self.bot.resource_manager = None
        self.bot.do = lambda action: actions.append(action)

        import asyncio

        result = asyncio.run(self.manager._perform_smart_expansion("safe third"))

        self.assertTrue(result)
        self.assertEqual(actions, [("build", UnitTypeId.HATCHERY, Point2((95, 95)))])

    def test_resolve_expansion_target_replaces_taken_default_location(self):
        """Fallback get_next_expansion result is replaced if that base is occupied."""
        main = Mock()
        main.position = Point2((50, 50))
        natural = Mock()
        natural.position = Point2((60, 60))
        townhalls = Mock()
        townhalls.amount = 2
        townhalls.__iter__ = Mock(side_effect=lambda: iter([main, natural]))

        self.bot.townhalls = townhalls
        self.bot.expansion_locations_list = [
            Point2((50, 50)),
            Point2((60, 60)),
            Point2((75, 75)),
        ]
        self.bot.can_place = AsyncMock(return_value=True)

        import asyncio

        target = asyncio.run(self.manager._resolve_expansion_target(Point2((60, 60))))

        self.assertEqual(target, Point2((75, 75)))

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

    def test_third_base_reservation_pauses_drone_training(self):
        """On two bases, drone recovery does not spend minerals reserved for third."""
        self.bot.time = 190
        self.bot.minerals = 150
        self.bot.workers.amount = 20
        self.bot.townhalls.amount = 2
        self.bot.supply_left = 8
        self.bot.can_afford = Mock(return_value=True)
        self.bot.do = Mock()

        import asyncio

        asyncio.run(self.manager._train_drone_if_needed())

        self.bot.do.assert_not_called()

    def test_pending_natural_starts_followup_expansion_reserve(self):
        """A pending natural near completion also starts saving for the third."""
        self.bot.time = 150
        self.bot.minerals = 150
        self.bot.workers.amount = 18
        self.bot.townhalls.amount = 1
        self.bot.supply_left = 8
        self.bot.already_pending = Mock(
            side_effect=lambda unit_type: 1 if unit_type == UnitTypeId.HATCHERY else 0
        )

        self.assertTrue(self.manager._should_reserve_followup_expansion())

    def test_pending_natural_counted_in_townhalls_still_reserves_followup(self):
        """Ready base count is used so a pending natural does not look like two bases."""
        self.bot.time = 150
        self.bot.minerals = 150
        self.bot.workers.amount = 18
        self.bot.townhalls.amount = 2
        self.bot.townhalls.ready.amount = 1
        self.bot.supply_left = 8
        self.bot.already_pending = Mock(
            side_effect=lambda unit_type: 1 if unit_type == UnitTypeId.HATCHERY else 0
        )

        self.assertTrue(self.manager._should_reserve_followup_expansion())

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

    def test_followup_expansion_reservation_pauses_spend_larva_drone(self):
        """Generic larva spending does not make drones while saving for third."""
        larva_unit = Mock()
        larva_unit.train = Mock(return_value=("train", UnitTypeId.DRONE))
        self.bot.larva.first = larva_unit
        self.bot.time = 190
        self.bot.minerals = 150
        self.bot.workers.amount = 20
        self.bot.townhalls.amount = 2
        self.bot.townhalls.ready.amount = 2
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

    def test_opening_hatchery_reservation_blocks_low_mineral_extractor_build(self):
        """Gas also waits when pool spending has dropped minerals below reserve floor."""
        self.bot.time = 76
        self.bot.minerals = 40
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

    def test_opening_hatchery_reservation_blocks_low_mineral_gas_timing(self):
        """Matchup gas timing cannot consume minerals before the natural starts."""
        self.bot.time = 76
        self.bot.minerals = 40
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

    def test_followup_expansion_reservation_blocks_force_army_when_under_droned(self):
        """Force-army larva spending still preserves minerals for the third base."""
        larva_unit = Mock()
        larva_unit.train = Mock(return_value=("train", UnitTypeId.ZERGLING))
        self.bot.larva.first = larva_unit
        self.bot.time = 170
        self.bot.minerals = 120
        self.bot.workers.amount = 18
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
