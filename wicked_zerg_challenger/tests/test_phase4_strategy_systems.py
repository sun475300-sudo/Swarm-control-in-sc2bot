#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Tests for STRATEGY_PLAN Phase 4 common strategy systems."""

import asyncio
import os
import sys
import unittest
from types import SimpleNamespace

os.environ["PROTOCOL_BUFFERS_PYTHON_IMPLEMENTATION"] = "python"
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from build_order_system import BuildOrderTransition
from strategy_manager import (
    EMERGENCY_RESPONSES,
    TIMING_ATTACKS,
    EnemyRace,
    StrategyManager,
)
from upgrade_manager import MATCHUP_UPGRADE_PRIORITY, EvolutionUpgradeManager


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


class FakeUnit:
    def __init__(self, tag, name, position, health=100, shield=0):
        self.tag = tag
        self.type_id = SimpleNamespace(name=name)
        self.name = name
        self.position = position
        self.health = health
        self.shield = shield

    def distance_to(self, other):
        return self.position.distance_to(other)


class FakeStructure:
    def __init__(self, name, position):
        self.type_id = SimpleNamespace(name=name)
        self.name = name
        self.position = position

    def distance_to(self, other):
        return self.position.distance_to(other)


class FakeWorkers:
    amount = 30


class FakeBot:
    def __init__(self, blackboard=None, enemy_race="Race.Terran"):
        self.time = 120.0
        self.iteration = 22
        self.enemy_race = enemy_race
        self.blackboard = blackboard or Blackboard()
        self.units = []
        self.enemy_units = []
        self.enemy_structures = []
        self.structures = []
        self.townhalls = [FakeStructure("HATCHERY", Point(10, 10))]
        self.start_location = Point(10, 10)
        self.enemy_start_locations = [Point(100, 100)]
        self.workers = FakeWorkers()
        self.state = SimpleNamespace(upgrades=[])


def upgrade_name(upgrade):
    return getattr(upgrade, "name", str(upgrade))


class TestBuildOrderTransition(unittest.TestCase):
    def test_cheese_switches_to_locked_defense_build(self):
        blackboard = Blackboard({"cheese_detected": True})
        transition = BuildOrderTransition()

        result = asyncio.run(transition.check_transition(90, blackboard))

        self.assertEqual(result, "emergency_defense")
        self.assertEqual(transition.current_build, "emergency_defense")
        self.assertTrue(transition.transition_triggered)
        self.assertEqual(transition.last_reason, "cheese_detected")

    def test_enemy_expand_switches_to_unlocked_greedy_build(self):
        blackboard = Blackboard({"enemy_expand_confirmed": True})
        transition = BuildOrderTransition()

        result = asyncio.run(transition.check_transition(220, blackboard))

        self.assertEqual(result, "greedy_macro")
        self.assertEqual(transition.current_build, "greedy_macro")
        self.assertFalse(transition.transition_triggered)


class TestMatchupUpgradePriority(unittest.TestCase):
    def test_priority_catalog_has_all_matchups_and_phases(self):
        self.assertEqual(set(MATCHUP_UPGRADE_PRIORITY), {"ZvT", "ZvP", "ZvZ"})
        for matchup in ("ZvT", "ZvP", "ZvZ"):
            self.assertEqual(
                set(MATCHUP_UPGRADE_PRIORITY[matchup]), {"early", "mid", "late"}
            )

    def test_zvp_midgame_prioritizes_missile_and_hydra_range(self):
        bot = FakeBot(enemy_race="Race.Protoss")
        bot.time = 360.0
        manager = EvolutionUpgradeManager(bot)

        names = [upgrade_name(upgrade) for upgrade in manager.get_matchup_upgrade_priority()]

        self.assertEqual(names[0], "ZERGMISSILEWEAPONSLEVEL1")
        self.assertIn("EVOLVEGROOVEDSPINES", names)


class TestTimingAttackSystem(unittest.TestCase):
    def test_zvz_ling_bane_timing_sets_attack_target(self):
        blackboard = Blackboard({"army_power_ratio": 1.5})
        bot = FakeBot(blackboard, enemy_race="Race.Zerg")
        bot.time = 220.0
        bot.units = [FakeUnit(i, "ZERGLING", Point(20, 20)) for i in range(12)]
        bot.units += [FakeUnit(100 + i, "BANELING", Point(20, 20)) for i in range(6)]
        bot.state.upgrades = [SimpleNamespace(name="ZERGLINGMOVEMENTSPEED")]
        manager = StrategyManager(bot, blackboard)
        manager.detected_enemy_race = EnemyRace.ZERG
        manager._cached_enemy_composition = {}

        manager._apply_timing_attack_system()

        self.assertTrue(blackboard.get("timing_attack_active"))
        self.assertEqual(blackboard.get("timing_attack_key"), "ling_bane_allin")
        self.assertEqual(blackboard.get("timing_attack_target"), "enemy_natural")

    def test_zvp_roach_timing_retreats_from_immortal_count(self):
        blackboard = Blackboard({"roach_speed_done": True, "army_power_ratio": 1.8})
        bot = FakeBot(blackboard, enemy_race="Race.Protoss")
        bot.time = 360.0
        bot.units = [FakeUnit(i, "ROACH", Point(20, 20)) for i in range(10)]
        manager = StrategyManager(bot, blackboard)
        manager.detected_enemy_race = EnemyRace.PROTOSS
        manager._cached_enemy_composition = {"IMMORTAL": 3}

        manager._apply_timing_attack_system()

        self.assertFalse(blackboard.get("timing_attack_active"))
        self.assertTrue(blackboard.get("timing_attack_retreat"))
        self.assertEqual(blackboard.get("timing_attack_key"), "roach_timing")

    def test_timing_attack_catalog_has_required_entries(self):
        self.assertIn("ling_speed_timing", TIMING_ATTACKS["ZvT"])
        self.assertIn("roach_timing", TIMING_ATTACKS["ZvP"])
        self.assertIn("roach_push", TIMING_ATTACKS["ZvZ"])


class TestEmergencyResponseTable(unittest.TestCase):
    def test_cannon_rush_sets_worker_pull_and_halts_drones(self):
        blackboard = Blackboard()
        bot = FakeBot(blackboard, enemy_race="Race.Protoss")
        bot.time = 90.0
        bot.enemy_structures = [FakeStructure("PHOTONCANNON", Point(18, 18))]
        manager = StrategyManager(bot, blackboard)
        manager.detected_enemy_race = EnemyRace.PROTOSS
        manager._cached_enemy_composition = {}

        manager._apply_emergency_response_table()

        self.assertEqual(blackboard.get("emergency_response_key"), "cannon_rush")
        self.assertTrue(blackboard.get("worker_pull_requested"))
        self.assertEqual(blackboard.get("drone_production_policy"), "HALT")
        self.assertFalse(manager.should_produce_drone())

    def test_dark_templar_response_requests_detection(self):
        blackboard = Blackboard({"dark_shrine_scouted": True})
        bot = FakeBot(blackboard, enemy_race="Race.Protoss")
        bot.time = 320.0
        manager = StrategyManager(bot, blackboard)
        manager.detected_enemy_race = EnemyRace.PROTOSS
        manager._cached_enemy_composition = {}

        manager._apply_emergency_response_table()

        self.assertEqual(blackboard.get("emergency_response_key"), "dt_rush")
        self.assertTrue(blackboard.get("urgent_overseer"))
        self.assertTrue(blackboard.get("urgent_spore_all_bases"))

    def test_response_catalog_contains_required_scenarios(self):
        self.assertIn("proxy_barracks", EMERGENCY_RESPONSES)
        self.assertIn("void_ray_rush", EMERGENCY_RESPONSES)
        self.assertIn("baneling_bust", EMERGENCY_RESPONSES)


if __name__ == "__main__":
    unittest.main()
