#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Tests for STRATEGY_PLAN Phase 2 ZvP implementation."""

import os
import sys
import unittest
from types import SimpleNamespace

os.environ["PROTOCOL_BUFFERS_PYTHON_IMPLEMENTATION"] = "python"
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from build_order_system import ZVP_BUILDS, BuildOrderSystem, BuildOrderType
from combat.micro_combat import ZvPMicroAdjustments
from scouting_system import ZVP_SCOUT_PRIORITIES, ZvPScoutingSystem
from strategy_manager import (
    ZVP_COUNTER_RULES,
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
    def __init__(self, tag, name, position):
        self.tag = tag
        self.type_id = SimpleNamespace(name=name)
        self.position = position
        self.health_percentage = 1.0
        self.weapon_cooldown = 0
        self.ground_range = 1
        self.is_biological = True
        self.is_ground = name not in {"CORRUPTOR", "ORACLE", "VOIDRAY"}
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

    def distance_to(self, other):
        return self.position.distance_to(other)


class FakeBot:
    def __init__(self, blackboard=None):
        self.time = 120.0
        self.iteration = 22
        self.enemy_race = "Race.Protoss"
        self.enemy_units = []
        self.enemy_structures = []
        self.blackboard = blackboard or Blackboard()
        self.townhalls = []
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
        self.structures = []

    def do(self, action):
        self.actions.append(action)


class BuildBot(FakeBot):
    def __init__(self, blackboard=None):
        super().__init__(blackboard)
        self.supply_used = 12
        self.supply_cap = 14
        self.minerals = 50
        self.vespene = 0


class TestZvPBuildOrders(unittest.TestCase):
    def test_zvp_default_build_is_roach_rush(self):
        system = BuildOrderSystem(BuildBot())

        self.assertEqual(system.current_build_order, BuildOrderType.ROACH_RUSH)
        self.assertEqual(system.current_matchup_build_key, "roach_rush")
        self.assertEqual(system.current_build_transition, "roach_ravager_push")
        self.assertGreater(len(system.build_steps), 0)

    def test_zvp_cannon_rush_selects_ling_flood(self):
        system = BuildOrderSystem(
            BuildBot(Blackboard({"enemy_cannon_rush_detected": True}))
        )

        self.assertEqual(system._select_zvp_build(), "ling_flood_anti_cannon")
        self.assertEqual(system.current_matchup_build_key, "ling_flood_anti_cannon")

    def test_zvp_stargate_selects_hydra_lair_macro(self):
        system = BuildOrderSystem(BuildBot(Blackboard({"stargate_existence": True})))

        self.assertEqual(system._select_zvp_build(), "hydra_lair_macro")
        self.assertEqual(system.current_matchup_build_key, "hydra_lair_macro")
        self.assertIn("morph", {step.action for step in system.build_steps})

    def test_zvp_build_catalog_has_three_builds(self):
        self.assertEqual(
            set(ZVP_BUILDS),
            {"roach_rush", "ling_flood_anti_cannon", "hydra_lair_macro"},
        )


class TestZvPCounterRules(unittest.TestCase):
    def test_counter_rule_ratios_sum_to_one_after_alias_normalization(self):
        for rule_key, rule in ZVP_COUNTER_RULES.items():
            ratios = StrategyManager._normalize_ratio_keys(
                rule["response"]["composition"]
            )
            self.assertNotIn("hydra", ratios, rule_key)
            self.assertAlmostEqual(sum(ratios.values()), 1.0, places=2)

    def test_storm_templar_sets_split_micro_directive(self):
        bot = FakeBot()
        manager = StrategyManager(bot, bot.blackboard)
        manager.detected_enemy_race = EnemyRace.PROTOSS
        manager.game_phase = GamePhase.MID
        manager._cached_enemy_composition = {"HIGHTEMPLAR": 2}

        manager._apply_zvp_counter_rules()

        ratios = manager.get_unit_ratios()
        self.assertEqual(bot.blackboard.get("zvp_counter_rule"), "storm_templar")
        self.assertEqual(bot.blackboard.get("zvp_micro_directive"), "SPLIT_ON_STORM")
        self.assertAlmostEqual(ratios["zergling"], 0.40)

    def test_skytoss_rule_normalizes_hydra_alias(self):
        bot = FakeBot()
        manager = StrategyManager(bot, bot.blackboard)
        manager.detected_enemy_race = EnemyRace.PROTOSS
        manager.game_phase = GamePhase.LATE
        manager._cached_enemy_composition = {"CARRIER": 2}

        manager._apply_zvp_counter_rules()

        ratios = manager.get_unit_ratios()
        self.assertEqual(bot.blackboard.get("zvp_counter_rule"), "skytoss_transition")
        self.assertIn("hydralisk", ratios)
        self.assertNotIn("hydra", ratios)
        self.assertTrue(bot.blackboard.get("urgent_spore_all_bases"))


class TestZvPMicroAdjustments(unittest.TestCase):
    def test_storm_effect_moves_units_out_of_radius(self):
        bot = FakeBot()
        bot.state = SimpleNamespace(
            effects=[
                SimpleNamespace(
                    id=SimpleNamespace(name="PSYCHICSTORM"),
                    positions=[Point(10, 10)],
                )
            ]
        )
        zergling = FakeUnit(1, "ZERGLING", Point(11, 10))

        handled = ZvPMicroAdjustments(bot).apply([zergling], [])

        self.assertIn(1, handled)
        self.assertTrue(any(action[0] == "move" for action in bot.actions))
        self.assertTrue(bot.blackboard.get("zvp_storm_split_active"))

    def test_oracle_harass_focuses_queen_and_requests_spore(self):
        bot = FakeBot()
        base = FakeStructure("HATCHERY", Point(10, 10))
        queen = FakeUnit(2, "QUEEN", Point(12, 10))
        oracle = FakeUnit(30, "ORACLE", Point(14, 10))
        bot.townhalls = [base]

        handled = ZvPMicroAdjustments(bot).apply([queen], [oracle])

        self.assertIn(2, handled)
        self.assertTrue(any(action[0] == "attack" for action in bot.actions))
        self.assertEqual(bot.blackboard.get("need_spore_at"), base.position)


class TestZvPScoutingSystem(unittest.TestCase):
    def test_priorities_follow_phase_windows(self):
        scout = ZvPScoutingSystem(FakeBot())

        self.assertEqual(scout.get_priorities(100), ZVP_SCOUT_PRIORITIES["early"])
        self.assertEqual(scout.get_priorities(240), ZVP_SCOUT_PRIORITIES["mid"])
        self.assertEqual(scout.get_priorities(500), ZVP_SCOUT_PRIORITIES["late"])

    def test_protoss_tech_structures_update_blackboard(self):
        bot = FakeBot()
        scout = ZvPScoutingSystem(bot)

        scout.record_scouted_structure(FakeStructure("STARGATE", Point(100, 100)))
        scout.record_scouted_structure(
            FakeStructure("ROBOTICSFACILITY", Point(100, 100))
        )
        scout.record_scouted_structure(FakeStructure("DARKSHRINE", Point(100, 100)))
        scout.record_scouted_structure(FakeStructure("FLEETBEACON", Point(100, 100)))

        self.assertTrue(bot.blackboard.get("enemy_stargate_detected"))
        self.assertTrue(bot.blackboard.get("enemy_robo_detected"))
        self.assertTrue(bot.blackboard.get("cloak_tech_detected"))
        self.assertTrue(bot.blackboard.get("AIR_THREAT_INCOMING"))

    def test_cannon_rush_near_base_sets_emergency_flags(self):
        bot = FakeBot()
        scout = ZvPScoutingSystem(bot)

        scout.record_scouted_structure(FakeStructure("PHOTONCANNON", Point(14, 10)))

        self.assertTrue(bot.blackboard.get("enemy_cannon_rush_detected"))
        self.assertTrue(bot.blackboard.get("enemy_proxy_detected"))


if __name__ == "__main__":
    unittest.main()
