# -*- coding: utf-8 -*-
"""Tests for STRATEGY_PLAN Phase 1 ZvT implementation."""

import os
import sys
import unittest
from types import SimpleNamespace

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from build_order_system import ZVT_BUILDS, BuildOrderSystem, BuildOrderType, UnitTypeId
from combat.micro_combat import ZvTMicroAdjustments
from scouting_system import ZVT_SCOUT_PRIORITIES, ZvTScoutingSystem
from strategy_manager import (
    ZVT_COMPOSITION_TIMELINE,
    EnemyRace,
    GamePhase,
    StrategyManager,
)


class Blackboard:
    def __init__(self, values=None):
        self.values = dict(values or {})

    def get(self, key, default=None):
        return self.values.get(key, default)

    def set(self, key, value):
        self.values[key] = value


class FakeBot:
    def __init__(self, blackboard=None):
        self.time = 0.0
        self.enemy_race = "Race.Terran"
        self.enemy_units = []
        self.enemy_structures = []
        self.blackboard = blackboard or Blackboard()


class BuildBot(FakeBot):
    def __init__(self, blackboard=None):
        super().__init__(blackboard)
        self.supply_used = 12
        self.supply_cap = 14
        self.minerals = 50
        self.vespene = 0


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

    def offset(self, delta):
        return Point(self.x + delta[0], self.y + delta[1])


class FakeUnit:
    def __init__(self, tag, unit_type, position):
        self.tag = tag
        self.type_id = unit_type
        self.position = position
        self.health_percentage = 1.0
        self.weapon_cooldown = 0
        self.ground_range = 1
        self.is_biological = True
        self.health = 100

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


class TestZvTBuildOrders(unittest.TestCase):
    def test_zvt_default_build_is_hatch_first(self):
        system = BuildOrderSystem(BuildBot())

        self.assertEqual(system.current_build_order, BuildOrderType.HATCH_FIRST_16)
        self.assertEqual(system.current_matchup_build_key, "hatch_first_16")
        self.assertEqual(system.current_build_transition, "roach_hydra_mid")
        self.assertGreater(len(system.build_steps), 0)

    def test_zvt_proxy_selects_aggressive_pool_first(self):
        bot = BuildBot(Blackboard({"enemy_proxy_detected": True}))
        system = BuildOrderSystem(bot)

        self.assertEqual(system._select_zvt_build(), "aggressive_pool_first")
        self.assertEqual(system.current_matchup_build_key, "aggressive_pool_first")

    def test_zvt_safe_expand_selects_fast_lair_macro(self):
        bot = BuildBot(
            Blackboard({"enemy_expand_confirmed": True, "enemy_aggression": False})
        )
        system = BuildOrderSystem(bot)

        self.assertEqual(system._select_zvt_build(), "fast_lair_macro")
        self.assertEqual(system.current_matchup_build_key, "fast_lair_macro")
        self.assertIn("upgrade", {step.action for step in system.build_steps})
        self.assertIn("morph", {step.action for step in system.build_steps})

    def test_zvt_build_catalog_has_three_builds(self):
        self.assertEqual(
            set(ZVT_BUILDS),
            {"hatch_first_16", "aggressive_pool_first", "fast_lair_macro"},
        )


class TestZvTCompositionTimeline(unittest.TestCase):
    def test_terran_bio_sets_midgame_baneling_ratio(self):
        bot = FakeBot()
        bot.time = 360.0
        manager = StrategyManager(bot, bot.blackboard)
        manager.detected_enemy_race = EnemyRace.TERRAN
        manager.game_phase = GamePhase.MID
        manager._cached_enemy_composition = {"MARINE": 8, "MARAUDER": 2}

        manager._apply_zvt_composition_timeline()

        ratios = manager.get_unit_ratios()
        self.assertEqual(bot.blackboard.get("zvt_enemy_composition"), "vs_bio")
        self.assertAlmostEqual(ratios["baneling"], 0.25)
        self.assertIn("hydralisk", ratios)

    def test_terran_fusion_core_sets_late_bc_ratio(self):
        bot = FakeBot()
        bot.time = 700.0
        bot.enemy_structures = [FakeStructure("FUSIONCORE", Point(50, 50))]
        manager = StrategyManager(bot, bot.blackboard)
        manager.detected_enemy_race = EnemyRace.TERRAN
        manager.game_phase = GamePhase.LATE
        manager._cached_enemy_composition = {}

        manager._apply_zvt_composition_timeline()

        ratios = manager.get_unit_ratios()
        self.assertEqual(bot.blackboard.get("zvt_enemy_composition"), "vs_bc")
        self.assertAlmostEqual(ratios["corruptor"], 0.40)

    def test_timeline_constant_contains_required_phases(self):
        self.assertIn("early", ZVT_COMPOSITION_TIMELINE)
        self.assertIn("mid", ZVT_COMPOSITION_TIMELINE)
        self.assertIn("late", ZVT_COMPOSITION_TIMELINE)


class TestZvTMicroAdjustments(unittest.TestCase):
    def test_banelings_attack_six_marine_clump(self):
        bot = FakeBot()
        bot.actions = []
        bot.townhalls = []
        bot.units = []
        bot.do = lambda action: bot.actions.append(action)
        marines = [
            FakeUnit(100 + index, UnitTypeId.MARINE, Point(index * 0.2, 0))
            for index in range(6)
        ]
        bane = FakeUnit(1, UnitTypeId.BANELING, Point(1, 1))

        handled = ZvTMicroAdjustments(bot).apply([bane], marines)

        self.assertIn(1, handled)
        self.assertTrue(any(action[0] == "attack" for action in bot.actions))


class TestZvTScoutingSystem(unittest.TestCase):
    def test_priorities_follow_phase_windows(self):
        bot = FakeBot()
        bot.enemy_start_locations = [Point(50, 50)]
        bot.expansion_locations_list = [Point(50, 50), Point(44, 44), Point(35, 35)]
        bot.game_info = SimpleNamespace(map_center=Point(25, 25))
        scout = ZvTScoutingSystem(bot)

        self.assertEqual(scout.get_priorities(100), ZVT_SCOUT_PRIORITIES["early"])
        self.assertEqual(scout.get_priorities(240), ZVT_SCOUT_PRIORITIES["mid"])
        self.assertEqual(scout.get_priorities(500), ZVT_SCOUT_PRIORITIES["late"])

    def test_terran_structures_update_blackboard(self):
        bot = FakeBot()
        bot.enemy_start_locations = [Point(50, 50)]
        bot.expansion_locations_list = [Point(50, 50), Point(44, 44)]
        bot.game_info = SimpleNamespace(map_center=Point(25, 25))
        scout = ZvTScoutingSystem(bot)

        scout.record_scouted_structure(FakeStructure("FACTORY", Point(50, 50)))
        scout.record_scouted_structure(FakeStructure("STARPORT", Point(50, 50)))
        scout.record_scouted_structure(FakeStructure("FUSIONCORE", Point(50, 50)))

        self.assertEqual(bot.blackboard.get("factory_count"), 1)
        self.assertTrue(bot.blackboard.get("starport_existence"))
        self.assertTrue(bot.blackboard.get("fusion_core"))
        self.assertTrue(bot.blackboard.get("AIR_THREAT_INCOMING"))


if __name__ == "__main__":
    unittest.main()
