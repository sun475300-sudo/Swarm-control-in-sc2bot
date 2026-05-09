#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Tests for ROADMAP Sprint 5 defense systems."""

import asyncio
import os
import sys
import unittest
from types import SimpleNamespace

os.environ["PROTOCOL_BUFFERS_PYTHON_IMPLEMENTATION"] = "python"
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from combat.base_defense import BaseDefenseSystem
from early_defense_system import EarlyDefenseSystem
from intel_manager import IntelManager
from strategy_manager import EnemyRace, StrategyManager


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
        total = self.distance_to(other) or 1.0
        return Point(
            self.x + (other.x - self.x) / total * distance,
            self.y + (other.y - self.y) / total * distance,
        )


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

    def attack(self, target):
        return ("attack", self.tag, target)

    def move(self, target):
        return ("move", self.tag, target)

    def build(self, structure_type, location):
        return ("build", self.tag, structure_type, location)


class FakeLarva:
    def __init__(self, tag):
        self.tag = tag

    def train(self, unit_type):
        return ("train", self.tag, unit_type)


class FakeStructure(FakeUnit):
    pass


class TownhallList(list):
    @property
    def first(self):
        return self[0] if self else None

    @property
    def exists(self):
        return bool(self)


class WorkerList(list):
    @property
    def amount(self):
        return len(self)

    def closest_n_units(self, position, count):
        return sorted(self, key=lambda unit: unit.distance_to(position))[:count]

    def closest_to(self, position):
        return self.closest_n_units(position, 1)[0] if self else None


class FakeTechCoordinator:
    def __init__(self):
        self.requests = []

    def request_structure(self, *args):
        self.requests.append(args)


class FakeBot:
    def __init__(self, blackboard=None):
        self.time = 90.0
        self.iteration = 22
        self.blackboard = blackboard or Blackboard()
        self.enemy_race = "Race.Terran"
        self.start_location = Point(10, 10)
        self.enemy_start_locations = [Point(100, 100)]
        self.game_info = SimpleNamespace(map_center=Point(50, 50))
        self.townhalls = TownhallList([FakeStructure(900, "HATCHERY", Point(10, 10))])
        self.enemy_structures = []
        self.enemy_units = []
        self.units = []
        self.workers = WorkerList(
            [FakeUnit(i, "DRONE", Point(11 + i, 10)) for i in range(10)]
        )
        self.larva = [FakeLarva(i) for i in range(3)]
        self.minerals = 500
        self.supply_army = 0
        # supply_left guards _train_all_larva_as_zerglings (each larva morphs
        # into 2 zerglings = 2 supply); leave generous head-room in tests.
        self.supply_left = 20
        self.actions = []
        self.tech_coordinator = FakeTechCoordinator()

    def do(self, action):
        self.actions.append(action)


class TestProxyCannonDefense(unittest.TestCase):
    def test_proxy_structure_triggers_spines_workers_and_larva_army(self):
        blackboard = Blackboard()
        bot = FakeBot(blackboard)
        bot.enemy_structures = [
            FakeStructure(300, "PHOTONCANNON", Point(18, 18)),
        ]
        defense = EarlyDefenseSystem(bot)

        asyncio.run(defense._detect_proxy_structure_rush())
        asyncio.run(defense._proxy_structure_response())

        self.assertTrue(defense.proxy_response_active)
        self.assertTrue(blackboard.get("cheese_detected"))
        self.assertEqual(blackboard.get("drone_production_policy"), "HALT")
        self.assertEqual(len(bot.tech_coordinator.requests), 2)
        self.assertEqual(
            len([action for action in bot.actions if action[0] == "attack"]), 6
        )
        self.assertEqual(
            len([action for action in bot.actions if action[0] == "train"]), 3
        )

    def test_proxy_response_clears_after_structure_destroyed(self):
        blackboard = Blackboard()
        bot = FakeBot(blackboard)
        cannon = FakeStructure(300, "PHOTONCANNON", Point(18, 18))
        bot.enemy_structures = [cannon]
        defense = EarlyDefenseSystem(bot)

        asyncio.run(defense._detect_proxy_structure_rush())
        bot.enemy_structures = []
        defense._clear_proxy_response_if_destroyed()

        self.assertFalse(defense.proxy_response_active)
        self.assertFalse(blackboard.get("cheese_detected"))
        self.assertEqual(blackboard.get("drone_production_policy"), "NORMAL")


class TestDropDefense(unittest.TestCase):
    def test_drop_transport_uses_garrison_and_reinforcements(self):
        blackboard = Blackboard()
        bot = FakeBot(blackboard)
        bot.time = 180.0
        bot.units = [FakeUnit(10, "QUEEN", Point(12, 10))]
        bot.units += [FakeUnit(20 + i, "ZERGLING", Point(13 + i, 10)) for i in range(5)]
        bot.units += [FakeUnit(100 + i, "ROACH", Point(40 + i, 40)) for i in range(12)]
        bot.enemy_units = [FakeUnit(500, "MEDIVAC", Point(16, 16))]
        defense = BaseDefenseSystem(bot)

        asyncio.run(defense.handle_multi_base_drop_defense(110))

        self.assertTrue(blackboard.get("drop_defense_active"))
        self.assertEqual(blackboard.get("drop_defense_target"), "MEDIVAC")
        self.assertEqual(len(defense.base_defender_tags[0]), 5)
        self.assertGreaterEqual(
            len([action for action in bot.actions if action[0] == "attack"]), 13
        )

    def test_repeated_air_harass_requests_spores(self):
        blackboard = Blackboard()
        bot = FakeBot(blackboard)
        bot.time = 180.0
        bot.units = [FakeUnit(10, "QUEEN", Point(12, 10))]
        bot.units += [FakeUnit(20 + i, "ZERGLING", Point(13 + i, 10)) for i in range(4)]
        bot.enemy_units = [FakeUnit(500, "WARPPRISM", Point(16, 16))]
        defense = BaseDefenseSystem(bot)

        asyncio.run(defense.handle_multi_base_drop_defense(110))
        bot.time = 195.0
        asyncio.run(defense.handle_multi_base_drop_defense(220))

        self.assertEqual(blackboard.get("air_harass_count"), 2)
        self.assertTrue(blackboard.get("urgent_spore_all_bases"))
        self.assertTrue(blackboard.get("drop_spore_response"))


class TestAllInDetection(unittest.TestCase):
    def test_strategy_detects_no_expand_all_in_and_halts_drones(self):
        blackboard = Blackboard()
        bot = FakeBot(blackboard)
        bot.time = 360.0
        bot.units = [FakeUnit(i, "ZERGLING", Point(12, 12), health=35) for i in range(4)]
        bot.enemy_units = [
            FakeUnit(100 + i, "MARINE", Point(35, 35), health=45) for i in range(12)
        ]
        manager = StrategyManager(bot, blackboard)
        manager.detected_enemy_race = EnemyRace.TERRAN

        manager._detect_all_in_pressure()
        manager._apply_emergency_response_table()

        self.assertTrue(blackboard.get("enemy_all_in"))
        self.assertEqual(blackboard.get("emergency_response_key"), "enemy_all_in")
        self.assertEqual(blackboard.get("urgent_spine_count"), 4)
        self.assertTrue(blackboard.get("spend_larva_on_army"))
        self.assertTrue(blackboard.get("queen_defense_mode"))
        self.assertFalse(manager.should_produce_drone())

    def test_intel_manager_publishes_all_in_flags(self):
        blackboard = Blackboard()
        bot = FakeBot(blackboard)
        bot.time = 360.0
        bot.units = [FakeUnit(i, "ZERGLING", Point(12, 12), health=35) for i in range(4)]
        bot.enemy_units = [
            FakeUnit(100 + i, "STALKER", Point(35, 35), health=80, shield=80)
            for i in range(8)
        ]
        intel = IntelManager(bot)
        intel.enemy_base_count = 1

        intel._detect_all_in_pressure()

        self.assertTrue(intel.enemy_all_in_detected)
        self.assertTrue(blackboard.get("enemy_all_in"))
        self.assertEqual(blackboard.get("drone_production_policy"), "HALT")


if __name__ == "__main__":
    unittest.main()
