#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Unit tests for BuildOrderSystem.

Tests:
- Build order selection by enemy race (ZvZ, ZvP, ZvT)
- Build step parsing from commander_knowledge.json
- Knowledge JSON integrity (all builds, unit ratios)
"""

import json
import os
import sys
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import AsyncMock, Mock

# Add bot directory to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from build_order_system import BuildOrderSystem, BuildOrderType, UnitTypeId
from sc2.position import Point2


class MockBot:
    """Mock SC2 bot for build order testing."""

    def __init__(self, race_str=None):
        self.time = 0.0
        self.supply_used = 12
        self.supply_cap = 14
        self.minerals = 50
        self.vespene = 0
        self.workers = Mock(amount=12)
        self.structures = Mock(side_effect=lambda *a: Mock(amount=0, exists=False))
        self.townhalls = Mock(amount=1, exists=True, first=Mock(position=Mock()))
        self.game_info = Mock()
        self.iteration = 0

        if race_str:
            self.enemy_race = Mock()
            self.enemy_race.__str__ = lambda self_inner: race_str
        else:
            self.enemy_race = None

    def can_afford(self, unit_type):
        return True

    def already_pending(self, unit_type):
        return 0


class TestBuildOrderRaceSelection(unittest.TestCase):
    """Test build order selection by enemy race."""

    def test_zvz_selects_safe_14pool(self):
        bot = MockBot("Race.Zerg")
        system = BuildOrderSystem(bot)
        self.assertEqual(system.current_build_order, BuildOrderType.SAFE_14POOL)

    def test_zvp_selects_roach_rush(self):
        bot = MockBot("Race.Protoss")
        system = BuildOrderSystem(bot)
        self.assertEqual(system.current_build_order, BuildOrderType.ROACH_RUSH)

    def test_zvt_selects_hatch_first(self):
        bot = MockBot("Race.Terran")
        system = BuildOrderSystem(bot)
        self.assertEqual(system.current_build_order, BuildOrderType.HATCH_FIRST_16)

    def test_unknown_race_fallback(self):
        bot = MockBot()  # No enemy_race
        system = BuildOrderSystem(bot)
        self.assertEqual(system.current_build_order, BuildOrderType.ROACH_RUSH)


class TestBuildOrderStepParsing(unittest.TestCase):
    """Test build steps are correctly parsed from JSON."""

    def test_standard_12pool_has_steps(self):
        bot = MockBot("Race.Terran")
        system = BuildOrderSystem(bot)
        self.assertGreater(
            len(system.build_steps), 0, "STANDARD_12POOL should have build steps"
        )

    def test_safe_14pool_has_steps(self):
        bot = MockBot("Race.Zerg")
        system = BuildOrderSystem(bot)
        self.assertGreater(
            len(system.build_steps), 0, "SAFE_14POOL should have build steps"
        )

    def test_build_steps_have_supply(self):
        bot = MockBot("Race.Terran")
        system = BuildOrderSystem(bot)
        for step in system.build_steps:
            self.assertIsInstance(step.supply, int)
            self.assertGreater(step.supply, 0)

    def test_build_steps_have_action(self):
        bot = MockBot("Race.Terran")
        system = BuildOrderSystem(bot)
        valid_actions = {"build", "train", "expand", "morph", "upgrade"}
        for step in system.build_steps:
            self.assertIn(
                step.action,
                valid_actions,
                f"Step action '{step.action}' not in valid actions",
            )


class TestKnowledgeJsonIntegrity(unittest.TestCase):
    """Test commander_knowledge.json has all required data."""

    def setUp(self):
        json_path = Path(__file__).parent.parent / "commander_knowledge.json"
        self.assertTrue(
            json_path.exists(), f"commander_knowledge.json not found at {json_path}"
        )
        with open(json_path, "r", encoding="utf-8") as f:
            self.knowledge = json.load(f)

    def test_build_orders_section_exists(self):
        self.assertIn("build_orders", self.knowledge)

    def test_standard_12pool_exists(self):
        self.assertIn("STANDARD_12POOL", self.knowledge["build_orders"])

    def test_safe_14pool_exists(self):
        self.assertIn("SAFE_14POOL", self.knowledge["build_orders"])

    def test_roach_rush_exists(self):
        self.assertIn("ROACH_RUSH", self.knowledge["build_orders"])

    def test_all_builds_have_steps(self):
        for name, build in self.knowledge["build_orders"].items():
            self.assertIn("steps", build, f"{name} missing 'steps'")
            self.assertGreater(len(build["steps"]), 0, f"{name} has empty steps")

    def test_all_builds_have_name(self):
        for key, build in self.knowledge["build_orders"].items():
            self.assertIn("name", build, f"{key} missing 'name'")

    def test_unit_ratios_section_exists(self):
        self.assertIn("unit_ratios", self.knowledge)

    def test_unit_ratios_all_races(self):
        ratios = self.knowledge["unit_ratios"]
        for race in ["Terran", "Protoss", "Zerg"]:
            self.assertIn(race, ratios, f"Missing unit ratios for {race}")
            for phase in ["early", "mid", "late"]:
                self.assertIn(phase, ratios[race], f"Missing {phase} phase for {race}")

    def test_unit_ratios_sum_to_one(self):
        """Each phase's ratios should approximately sum to 1.0."""
        ratios = self.knowledge["unit_ratios"]
        for race, phases in ratios.items():
            for phase, units in phases.items():
                total = sum(units.values())
                self.assertAlmostEqual(
                    total, 1.0, places=1, msg=f"{race}/{phase} ratios sum to {total}"
                )

    def test_counter_rules_exist(self):
        self.assertIn("counter_rules", self.knowledge)
        self.assertGreater(len(self.knowledge["counter_rules"]), 0)


class TestBuildOrderStats(unittest.TestCase):
    """Test build order statistics tracking."""

    def test_stats_initialized_for_all_types(self):
        bot = MockBot("Race.Terran")
        system = BuildOrderSystem(bot)
        for build_type in BuildOrderType:
            self.assertIn(build_type, system.build_order_stats)

    def test_stats_have_required_fields(self):
        bot = MockBot("Race.Terran")
        system = BuildOrderSystem(bot)
        for build_type, stats in system.build_order_stats.items():
            self.assertIn("games", stats)
            self.assertIn("wins", stats)


class TestOpeningExpansionPriority(unittest.TestCase):
    """Test first natural expansion cannot be skipped by short retry windows."""

    def test_opening_hatchery_step_is_held_before_ninety_seconds(self):
        bot = MockBot("Race.Terran")
        bot.time = 65.0
        bot.supply_used = 16
        bot.minerals = 250
        bot.can_afford = Mock(return_value=False)

        system = BuildOrderSystem(bot)
        system.current_step_index = 1
        step = system.build_steps[system.current_step_index]

        self.assertEqual(step.action, "expand")
        self.assertEqual(step.unit_type, UnitTypeId.HATCHERY)

        import asyncio

        for iteration in range(system._max_retries_before_skip + 5):
            bot.iteration = iteration
            asyncio.run(system.execute(iteration))

        self.assertEqual(system.current_step_index, 1)
        self.assertEqual(system._skipped_steps, [])

    def test_first_expansion_prefers_closest_untaken_natural(self):
        bot = MockBot("Race.Terran")
        main = SimpleNamespace(position=Point2((50, 50)))
        natural = Point2((60, 60))
        distant = Point2((140, 140))
        bot.time = 55.0
        bot.minerals = 300
        bot.start_location = Point2((50, 50))
        bot.expansion_locations_list = [distant, natural, Point2((50, 50))]
        bot.townhalls = Mock(amount=1, exists=True, first=main)
        bot.townhalls.__iter__ = Mock(return_value=iter([main]))
        bot.can_place = AsyncMock(return_value=True)
        bot.get_next_expansion = AsyncMock(return_value=distant)
        worker = Mock()
        worker.build = Mock(return_value=("build", UnitTypeId.HATCHERY, natural))
        bot.workers.exists = True
        bot.workers.closest_to = Mock(return_value=worker)
        bot.do = Mock()

        class FakeTechCoordinator:
            def __init__(self):
                self.requests = []

            def is_planned(self, structure_type):
                return False

            def request_structure(self, structure_type, location, priority, requester):
                self.requests.append((structure_type, location, priority, requester))
                return True

        bot.tech_coordinator = FakeTechCoordinator()
        system = BuildOrderSystem(bot)

        import asyncio

        result = asyncio.run(system._expand(UnitTypeId.HATCHERY))

        self.assertTrue(result)
        self.assertEqual(bot.tech_coordinator.requests, [])
        worker.build.assert_called_once_with(UnitTypeId.HATCHERY, natural)
        bot.do.assert_called_once_with(("build", UnitTypeId.HATCHERY, natural))
        bot.get_next_expansion.assert_not_awaited()

    def test_extractor_waits_until_first_hatchery_started(self):
        bot = MockBot("Race.Terran")
        bot.time = 70.0
        bot.townhalls.amount = 1
        bot.already_pending = Mock(return_value=0)
        bot.tech_coordinator = Mock()

        system = BuildOrderSystem(bot)

        import asyncio

        result = asyncio.run(system._build_structure(UnitTypeId.EXTRACTOR))

        self.assertFalse(result)
        bot.tech_coordinator.request_structure.assert_not_called()

    def test_second_extractor_waits_until_third_base(self):
        bot = MockBot("Race.Terran")
        bot.time = 150.0
        bot.townhalls.amount = 2
        bot.already_pending = Mock(return_value=0)
        bot.structures = Mock(
            side_effect=lambda unit_type: Mock(
                amount=1 if unit_type == UnitTypeId.EXTRACTOR else 0,
                exists=unit_type == UnitTypeId.EXTRACTOR,
            )
        )
        bot.tech_coordinator = Mock()

        system = BuildOrderSystem(bot)

        import asyncio

        result = asyncio.run(system._build_structure(UnitTypeId.EXTRACTOR))

        self.assertFalse(result)
        bot.tech_coordinator.request_structure.assert_not_called()

    def test_roach_warren_waits_for_third_hatchery_reserve(self):
        bot = MockBot("Race.Terran")
        bot.time = 190.0
        bot.minerals = 250
        bot.townhalls.amount = 2
        bot.townhalls.ready = Mock(amount=2)
        bot.already_pending = Mock(return_value=0)
        bot.structures = Mock(
            side_effect=lambda unit_type: Mock(amount=0, exists=False)
        )
        bot.can_afford = Mock(return_value=True)
        bot.tech_coordinator = Mock()

        system = BuildOrderSystem(bot)

        import asyncio

        result = asyncio.run(system._build_structure(UnitTypeId.ROACHWARREN))

        self.assertFalse(result)
        bot.can_afford.assert_not_called()
        bot.tech_coordinator.request_structure.assert_not_called()

    def test_queen_training_waits_for_third_hatchery_reserve(self):
        bot = MockBot("Race.Terran")
        bot.time = 190.0
        bot.minerals = 250
        bot.townhalls.amount = 2
        bot.townhalls.ready = Mock(amount=2)
        bot.already_pending = Mock(return_value=0)
        bot.can_afford = Mock(return_value=True)
        bot.do = Mock()

        system = BuildOrderSystem(bot)

        import asyncio

        result = asyncio.run(system._train_unit(UnitTypeId.QUEEN))

        self.assertFalse(result)
        bot.can_afford.assert_not_called()
        bot.do.assert_not_called()

    def test_pending_third_hatchery_releases_mineral_reserve(self):
        bot = MockBot("Race.Terran")
        bot.time = 190.0
        bot.townhalls.amount = 2
        bot.townhalls.ready = Mock(amount=2)
        bot.already_pending = Mock(
            side_effect=lambda unit_type: 1
            if unit_type == UnitTypeId.HATCHERY
            else 0
        )

        system = BuildOrderSystem(bot)

        self.assertFalse(system._should_reserve_third_base_minerals())

    def test_fourth_hatchery_reserve_active_on_three_bases(self):
        bot = MockBot("Race.Terran")
        bot.time = 370.0
        bot.townhalls.amount = 3
        bot.townhalls.ready = Mock(amount=3)
        bot.already_pending = Mock(return_value=0)

        system = BuildOrderSystem(bot)

        self.assertTrue(system._should_reserve_third_base_minerals())

    def test_pending_fourth_hatchery_releases_mineral_reserve(self):
        bot = MockBot("Race.Terran")
        bot.time = 370.0
        bot.townhalls.amount = 3
        bot.townhalls.ready = Mock(amount=3)
        bot.already_pending = Mock(
            side_effect=lambda unit_type: 1
            if unit_type == UnitTypeId.HATCHERY
            else 0
        )

        system = BuildOrderSystem(bot)

        self.assertFalse(system._should_reserve_third_base_minerals())

    def test_pending_natural_keeps_third_hatchery_reserve(self):
        bot = MockBot("Race.Terran")
        bot.time = 150.0
        bot.townhalls.amount = 1
        bot.townhalls.ready = Mock(amount=1)
        bot.already_pending = Mock(
            side_effect=lambda unit_type: 1
            if unit_type == UnitTypeId.HATCHERY
            else 0
        )

        system = BuildOrderSystem(bot)

        self.assertTrue(system._should_reserve_third_base_minerals())

    def test_pending_natural_in_townhall_amount_keeps_third_hatchery_reserve(self):
        bot = MockBot("Race.Terran")
        bot.time = 150.0
        bot.townhalls.amount = 2
        bot.townhalls.ready = Mock(amount=1)
        bot.already_pending = Mock(
            side_effect=lambda unit_type: 1
            if unit_type == UnitTypeId.HATCHERY
            else 0
        )

        system = BuildOrderSystem(bot)

        self.assertTrue(system._should_reserve_third_base_minerals())


if __name__ == "__main__":
    unittest.main()
