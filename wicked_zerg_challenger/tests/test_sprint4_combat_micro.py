#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Tests for ROADMAP Sprint 4 combat and micro upgrades."""

import asyncio
import os
import sys
import unittest
from types import SimpleNamespace

os.environ["PROTOCOL_BUFFERS_PYTHON_IMPLEMENTATION"] = "python"
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from combat.micro_combat import MicroCombat
from combat.mutalisk_micro import MutaliskMicroController
from combat_manager import CombatManager


class Blackboard:
    def __init__(self):
        self.values = {}

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
    def __init__(self, tag, name, position, supply_cost=1, health=100, health_max=100):
        self.tag = tag
        self.type_id = SimpleNamespace(name=name)
        self.position = position
        self.supply_cost = supply_cost
        self.health = health
        self.health_max = health_max
        self.health_percentage = health / health_max if health_max else 1.0
        self.can_attack = True
        self.is_burrowed = False
        self.air_range = 5
        self.ground_range = 1

    def distance_to(self, other):
        return self.position.distance_to(other)

    def attack(self, target):
        return ("attack", self.tag, target)

    def move(self, target):
        return ("move", self.tag, target)

    def __call__(self, ability, target=None):
        return ("ability", self.tag, ability, target)


class FakeBot:
    def __init__(self):
        self.actions = []
        self.units = []
        self.enemy_units = []
        self.townhalls = []
        self.start_location = Point(0, 0)
        self.blackboard = Blackboard()
        self.game_info = SimpleNamespace(
            map_ramps=[
                SimpleNamespace(top_center=Point(12, 10), bottom_center=Point(18, 10))
            ]
        )

    def do(self, action):
        self.actions.append(action)


def make_manager(bot):
    manager = CombatManager.__new__(CombatManager)
    manager.bot = bot
    manager._combat_is_emergency = False
    return manager


class TestSprint4LurkerMicro(unittest.TestCase):
    def test_lurker_burrows_when_at_nearest_choke(self):
        bot = FakeBot()
        lurker = FakeUnit(1, "LURKERMP", Point(11, 10))
        bot.units = [lurker]
        micro = MicroCombat(bot)

        handled = micro.manage_lurker_positioning(100)

        self.assertIn(1, handled)
        self.assertTrue(any(action[0] == "ability" for action in bot.actions))


class TestSprint4MutaliskMicro(unittest.TestCase):
    def test_mutalisk_retreats_from_anti_air_range(self):
        bot = FakeBot()
        muta = FakeUnit(2, "MUTALISK", Point(10, 10), health=80, health_max=100)
        marine = FakeUnit(30, "MARINE", Point(14, 10))
        controller = MutaliskMicroController()

        handled = asyncio.run(
            controller.execute_hit_and_run([muta], [marine], bot, current_time=120.0)
        )

        self.assertTrue(handled)
        self.assertTrue(any(action[0] == "move" for action in bot.actions))

    def test_low_health_mutalisk_uses_regen_threshold_50_percent(self):
        bot = FakeBot()
        muta = FakeUnit(3, "MUTALISK", Point(20, 20), health=40, health_max=100)
        controller = MutaliskMicroController()

        asyncio.run(controller.execute_hit_and_run([muta], [], bot, current_time=90.0))

        self.assertIn(3, controller.regenerating_units)
        self.assertTrue(any(action[0] == "move" for action in bot.actions))


class TestSprint4CombatManager(unittest.TestCase):
    def test_roach_hydra_formation_places_hydras_behind_target(self):
        bot = FakeBot()
        manager = make_manager(bot)
        target = Point(100, 100)
        roach = FakeUnit(1, "ROACH", Point(80, 100))
        hydra = FakeUnit(2, "HYDRALISK", Point(70, 100))

        handled = manager._execute_roach_hydra_formation([roach, hydra], target)

        self.assertEqual(handled, {1, 2})
        hydra_action = [action for action in bot.actions if action[1] == 2][0]
        self.assertLess(hydra_action[2].x, target.x)

    def test_multi_prong_splits_large_army_into_three_groups(self):
        bot = FakeBot()
        manager = make_manager(bot)
        # 10 Ultralisks = 60 supply, the multi-prong trigger threshold.
        army = [
            FakeUnit(index, "ULTRALISK", Point(index, 0)) for index in range(10)
        ]

        result = manager._execute_multi_prong_attack(army, [Point(100, 100)], 200)

        self.assertTrue(result)
        self.assertEqual(len(bot.actions), 10)
        groups = bot.blackboard.get("multi_prong_groups")
        self.assertEqual(sum(groups), 10)
        self.assertEqual(len(groups), 3)

    def test_frame_skip_uses_five_two_and_emergency_rules(self):
        bot = FakeBot()
        manager = make_manager(bot)

        self.assertTrue(manager._should_skip_combat_frame(1))
        self.assertFalse(manager._should_skip_combat_frame(5))

        bot.units = [FakeUnit(1, "ROACH", Point(10, 10))]
        bot.enemy_units = [FakeUnit(50, "MARINE", Point(12, 10))]
        self.assertTrue(manager._should_skip_combat_frame(3))
        self.assertFalse(manager._should_skip_combat_frame(4))

        bot.blackboard.set("enemy_all_in_detected", True)
        self.assertFalse(manager._should_skip_combat_frame(3))


if __name__ == "__main__":
    unittest.main()
