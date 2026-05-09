#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Tests for STRATEGY_PLAN Phase 3 ZvZ implementation."""

import os
import sys
import unittest
from types import SimpleNamespace

os.environ["PROTOCOL_BUFFERS_PYTHON_IMPLEMENTATION"] = "python"
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from build_order_system import BuildOrderSystem, BuildOrderType, ZVZ_BUILDS
from combat.micro_combat import ZvZMicroAdjustments
from scouting_system import ZVZ_SCOUT_PRIORITIES, ZvZScoutingSystem
from strategy_manager import (
    EnemyRace,
    GamePhase,
    StrategyManager,
    ZVZ_COMPOSITION_TIMELINE,
)


class Blackboard:
    def __init__(self, values=None):
        self.values = dict(values or {})

    def get(self, key, default=None):
        return self.values.get(key, default)

    def set(self, key, value):
        self.values[key] = value


class Point:
    def __init__(self, x, y):
        self.x = float(x)
        self.y = float(y)

    def distance_to(self, other):
        pos = getattr(other, "position", other)
        return ((self.x - pos.x) ** 2 + (self.y - pos.y) ** 2) ** 0.5

    def towards(self, other, distance):
        pos = getattr(other, "position", other)
        total = self.distance_to(pos) or 1.0
        return Point(
            self.x + (pos.x - self.x) / total * distance,
            self.y + (pos.y - self.y) / total * distance,
        )


class FakeUnit:
    def __init__(self, tag, name, position, health=100, health_max=100):
        self.tag = tag
        self.type_id = SimpleNamespace(name=name)
        self.position = position
        self.health = health
        self.health_max = health_max
        self.health_percentage = health / health_max if health_max else 1.0

    def distance_to(self, other):
        return self.position.distance_to(other)

    def attack(self, target):
        return ("attack", self.tag, target)

    def move(self, target):
        return ("move", self.tag, target)

    def __call__(self, ability, target=None):
        return ("ability", self.tag, ability, target)


class FakeStructure:
    def __init__(self, name, position):
        self.type_id = SimpleNamespace(name=name)
        self.position = position


class FakeBot:
    def __init__(self, blackboard=None):
        self.time = 120.0
        self.iteration = 22
        self.enemy_race = "Race.Zerg"
        self.enemy_units = []
        self.enemy_structures = []
        self.blackboard = blackboard or Blackboard()
        self.start_location = Point(10, 10)
        self.enemy_start_locations = [Point(100, 100)]
        self.expansion_locations_list = [
            Point(100, 100),
            Point(88, 88),
            Point(75, 75),
        ]
        self.game_info = SimpleNamespace(map_center=Point(50, 50))
        self.actions = []
        self.units = []
        self.townhalls = []
        self.state = SimpleNamespace(upgrades=set())

    def do(self, action):
        self.actions.append(action)

    def already_pending_upgrade(self, _upgrade):
        return False


class BuildBot(FakeBot):
    def __init__(self, blackboard=None):
        super().__init__(blackboard)
        self.supply_used = 12
        self.supply_cap = 14
        self.minerals = 50
        self.vespene = 0


class TestZvZBuildOrders(unittest.TestCase):
    def test_zvz_default_build_is_safe_14pool(self):
        system = BuildOrderSystem(BuildBot())

        self.assertEqual(system.current_build_order, BuildOrderType.SAFE_14POOL)
        self.assertEqual(system.current_matchup_build_key, "safe_14pool")
        self.assertEqual(system.current_build_transition, "ling_bane_control")

    def test_ling_flood_selects_roach_warren_macro(self):
        system = BuildOrderSystem(
            BuildBot(Blackboard({"enemy_ling_flood_detected": True}))
        )

        self.assertEqual(system._select_zvz_build(), "roach_warren_macro")
        self.assertEqual(system.current_matchup_build_key, "roach_warren_macro")

    def test_aggressive_opening_selects_12pool(self):
        system = BuildOrderSystem(BuildBot(Blackboard({"aggressive_opening": True})))

        self.assertEqual(system._select_zvz_build(), "12pool_rush")
        self.assertEqual(system.current_matchup_build_key, "12pool_rush")

    def test_zvz_build_catalog_has_three_builds(self):
        self.assertEqual(
            set(ZVZ_BUILDS), {"safe_14pool", "12pool_rush", "roach_warren_macro"}
        )


class TestZvZCompositionTimeline(unittest.TestCase):
    def test_midgame_muta_sets_hydra_spore_response(self):
        bot = FakeBot()
        bot.time = 360.0
        manager = StrategyManager(bot, bot.blackboard)
        manager.detected_enemy_race = EnemyRace.ZERG
        manager.game_phase = GamePhase.MID
        manager._cached_enemy_composition = {"MUTALISK": 3}

        manager._apply_zvz_composition_timeline()

        ratios = manager.get_unit_ratios()
        self.assertEqual(bot.blackboard.get("zvz_enemy_composition"), "vs_muta")
        self.assertAlmostEqual(ratios["hydralisk"], 0.50)
        self.assertTrue(bot.blackboard.get("urgent_spore_all_bases"))

    def test_timeline_ratios_normalize_lurkermp_key(self):
        bot = FakeBot()
        bot.time = 700.0
        manager = StrategyManager(bot, bot.blackboard)
        manager.detected_enemy_race = EnemyRace.ZERG
        manager.game_phase = GamePhase.LATE
        manager._cached_enemy_composition = {}

        manager._apply_zvz_composition_timeline()

        ratios = manager.get_unit_ratios()
        self.assertIn("lurkermp", ratios)
        self.assertNotIn("LURKERMP", ratios)

    def test_zvz_timeline_contains_required_phases(self):
        self.assertIn("early", ZVZ_COMPOSITION_TIMELINE)
        self.assertIn("mid", ZVZ_COMPOSITION_TIMELINE)
        self.assertIn("late", ZVZ_COMPOSITION_TIMELINE)


class TestZvZMicroAdjustments(unittest.TestCase):
    def test_lings_flee_close_enemy_baneling(self):
        bot = FakeBot()
        ling = FakeUnit(1, "ZERGLING", Point(10, 10))
        enemy_bane = FakeUnit(20, "BANELING", Point(12, 10))

        handled = ZvZMicroAdjustments(bot).apply([ling], [enemy_bane])

        self.assertIn(1, handled)
        self.assertTrue(any(action[0] == "move" for action in bot.actions))

    def test_baneling_attacks_densest_ling_pack(self):
        bot = FakeBot()
        bane = FakeUnit(2, "BANELING", Point(8, 8))
        enemy_lings = [
            FakeUnit(30 + index, "ZERGLING", Point(10 + index * 0.2, 10))
            for index in range(4)
        ]

        handled = ZvZMicroAdjustments(bot).apply([bane], enemy_lings)

        self.assertIn(2, handled)
        self.assertTrue(any(action[0] == "attack" for action in bot.actions))

    def test_low_health_roach_retreats_in_mirror(self):
        bot = FakeBot()
        roach = FakeUnit(3, "ROACH", Point(30, 30), health=25, health_max=100)
        enemy_roach = FakeUnit(40, "ROACH", Point(35, 30))

        handled = ZvZMicroAdjustments(bot).apply([roach], [enemy_roach])

        self.assertIn(3, handled)
        self.assertTrue(any(action[0] == "move" for action in bot.actions))


class TestZvZScoutingSystem(unittest.TestCase):
    def test_priorities_follow_phase_windows(self):
        scout = ZvZScoutingSystem(FakeBot())

        self.assertEqual(scout.get_priorities(100), ZVZ_SCOUT_PRIORITIES["early"])
        self.assertEqual(scout.get_priorities(240), ZVZ_SCOUT_PRIORITIES["mid"])
        self.assertEqual(scout.get_priorities(500), ZVZ_SCOUT_PRIORITIES["late"])

    def test_early_pool_and_spire_update_blackboard(self):
        bot = FakeBot()
        bot.time = 80.0
        scout = ZvZScoutingSystem(bot)

        scout.record_scouted_structure(FakeStructure("SPAWNINGPOOL", Point(100, 100)))
        scout.record_scouted_structure(FakeStructure("SPIRE", Point(100, 100)))

        self.assertTrue(bot.blackboard.get("enemy_12pool_detected"))
        self.assertTrue(bot.blackboard.get("spire_existence"))
        self.assertTrue(bot.blackboard.get("AIR_THREAT_INCOMING"))

    def test_ling_flood_updates_blackboard_from_units(self):
        bot = FakeBot()
        bot.enemy_units = [
            FakeUnit(index, "ZERGLING", Point(100, 100)) for index in range(10)
        ]
        scout = ZvZScoutingSystem(bot)

        scout.update_blackboard_from_visible_structures()

        self.assertTrue(bot.blackboard.get("enemy_ling_flood_detected"))


if __name__ == "__main__":
    unittest.main()
