# -*- coding: utf-8 -*-
"""Sprint 1 worker defense and harassment regression tests."""

import asyncio
import os
import sys
import unittest

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from combat_manager import CombatManager
from sc2.ids.unit_typeid import UnitTypeId
from sc2.position import Point2


class FakeUnits(list):
    @property
    def exists(self):
        return bool(self)

    @property
    def amount(self):
        return len(self)

    @property
    def ready(self):
        return self

    @property
    def tags(self):
        return {unit.tag for unit in self}

    @property
    def first(self):
        return self[0]

    def filter(self, predicate):
        return FakeUnits([unit for unit in self if predicate(unit)])

    def closer_than(self, distance, target):
        return FakeUnits([unit for unit in self if unit.distance_to(target) < distance])

    def closest_to(self, target):
        return min(self, key=lambda unit: unit.distance_to(target))

    def closest_n_units(self, target, count):
        return FakeUnits(
            sorted(self, key=lambda unit: unit.distance_to(target))[:count]
        )


class UnitSource(FakeUnits):
    def __call__(self, unit_type):
        return FakeUnits([unit for unit in self if unit.type_id == unit_type])


class FakeUnit:
    def __init__(self, tag, unit_type, position, can_attack=False, health=100):
        self.tag = tag
        self.type_id = unit_type
        self.position = position
        self.can_attack = can_attack
        self.health = health
        self.health_max = 100
        self.health_percentage = health / 100
        self.is_attacking = False

    def distance_to(self, target):
        target_pos = getattr(target, "position", target)
        return self.position.distance_to(target_pos)

    def attack(self, target):
        self.is_attacking = True
        return ("attack", self.tag, getattr(target, "tag", target))

    def move(self, target):
        return ("move", self.tag, target)

    def gather(self, target):
        self.is_attacking = False
        return ("gather", self.tag, getattr(target, "tag", target))


class FakeBot:
    def __init__(self):
        self.time = 60
        self.iteration = 22
        self.actions = []
        self.start_location = Point2((50, 50))
        self.enemy_start_locations = [Point2((100, 100))]
        self.townhalls = FakeUnits([FakeUnit(1, UnitTypeId.HATCHERY, Point2((50, 50)))])
        self.workers = FakeUnits(
            [FakeUnit(10 + i, UnitTypeId.DRONE, Point2((52 + i, 50))) for i in range(5)]
        )
        self.queen = FakeUnit(30, UnitTypeId.QUEEN, Point2((51, 51)))
        self.units = UnitSource([self.queen])
        self.enemy_units = FakeUnits()
        self.enemy_structures = FakeUnits()
        self.mineral_field = FakeUnits(
            [FakeUnit(100, UnitTypeId.MINERALFIELD, Point2((49, 49)))]
        )

    def do(self, action):
        self.actions.append(action)


class TestWorkerHarassmentDefense(unittest.TestCase):
    def test_air_harassment_evacuates_workers_and_uses_anti_air_queen(self):
        bot = FakeBot()
        oracle = FakeUnit(200, UnitTypeId.ORACLE, Point2((55, 55)), can_attack=True)
        oracle.is_flying = True
        oracle.can_attack_ground = True
        bot.queen.can_attack_air = True
        bot.enemy_units = FakeUnits([oracle])
        manager = CombatManager(bot)

        asyncio.run(manager.respond_to_worker_harassment())

        self.assertIn(("attack", 30, 200), bot.actions)
        worker_actions = [action for action in bot.actions if 10 <= action[1] < 20]
        self.assertEqual(len(worker_actions), len(bot.workers))
        self.assertTrue(all(action[0] == "move" for action in worker_actions))
        for worker, action in zip(bot.workers, worker_actions):
            self.assertGreater(
                action[2].distance_to(oracle.position), worker.distance_to(oracle)
            )

        bot.actions.clear()
        bot.enemy_units.clear()
        asyncio.run(manager.respond_to_worker_harassment())
        self.assertEqual(
            len([action for action in bot.actions if action[0] == "gather"]), 5
        )
        self.assertEqual(manager._worker_harass_defender_tags, set())

    def test_air_harassment_evacuates_to_minerals_at_safe_base(self):
        bot = FakeBot()
        oracle = FakeUnit(200, UnitTypeId.ORACLE, Point2((55, 55)), can_attack=True)
        oracle.is_flying = True
        bot.enemy_units = FakeUnits([oracle])
        bot.townhalls.append(FakeUnit(2, UnitTypeId.HATCHERY, Point2((90, 50))))
        bot.mineral_field.append(
            FakeUnit(101, UnitTypeId.MINERALFIELD, Point2((92, 50)))
        )
        bot.queen.can_attack_air = True
        manager = CombatManager(bot)

        asyncio.run(manager.respond_to_worker_harassment())

        worker_actions = [action for action in bot.actions if 10 <= action[1] < 20]
        self.assertEqual(
            worker_actions, [("gather", worker.tag, 101) for worker in bot.workers]
        )

    def test_queen_without_air_attack_does_not_attack_flyer(self):
        bot = FakeBot()
        oracle = FakeUnit(200, UnitTypeId.ORACLE, Point2((55, 55)), can_attack=True)
        oracle.is_flying = True
        bot.enemy_units = FakeUnits([oracle])
        bot.queen.can_attack_air = False

        asyncio.run(CombatManager(bot).respond_to_worker_harassment())

        self.assertFalse(any(action[0] == "attack" for action in bot.actions))

    def test_mixed_harassment_workers_attack_only_ground_threats(self):
        bot = FakeBot()
        oracle = FakeUnit(200, UnitTypeId.ORACLE, Point2((53, 51)), can_attack=True)
        oracle.is_flying = True
        marine = FakeUnit(201, UnitTypeId.MARINE, Point2((55, 55)), can_attack=True)
        bot.enemy_units = FakeUnits([oracle, marine])
        bot.queen.can_attack_air = True

        asyncio.run(CombatManager(bot).respond_to_worker_harassment())

        worker_attacks = [
            action
            for action in bot.actions
            if action[0] == "attack" and 10 <= action[1] < 20
        ]
        self.assertEqual(len(worker_attacks), 3)
        self.assertTrue(all(action[2] == 201 for action in worker_attacks))

    def test_air_only_weapon_does_not_trigger_worker_pull(self):
        bot = FakeBot()
        phoenix = FakeUnit(200, UnitTypeId.PHOENIX, Point2((55, 55)), can_attack=True)
        phoenix.is_flying = True
        phoenix.can_attack_ground = False
        bot.enemy_units = FakeUnits([phoenix])

        asyncio.run(CombatManager(bot).respond_to_worker_harassment())

        self.assertEqual(bot.actions, [])

    def test_worker_harassment_pulls_three_workers_per_threat_and_queen(self):
        bot = FakeBot()
        bot.enemy_units = FakeUnits(
            [FakeUnit(200, UnitTypeId.MARINE, Point2((55, 55)), can_attack=True)]
        )
        manager = CombatManager(bot)

        asyncio.run(manager.respond_to_worker_harassment())

        attack_actions = [action for action in bot.actions if action[0] == "attack"]
        worker_attacks = [action for action in attack_actions if 10 <= action[1] < 20]
        queen_attacks = [action for action in attack_actions if action[1] == 30]

        self.assertEqual(len(worker_attacks), 3)
        self.assertEqual(len(queen_attacks), 1)
        self.assertEqual(len(manager._worker_harass_defender_tags), 3)

    def test_worker_harassment_returns_tagged_workers_when_clear(self):
        bot = FakeBot()
        manager = CombatManager(bot)
        manager._worker_harass_defender_tags = {10, 11}
        bot.workers[0].is_attacking = True
        bot.workers[1].is_attacking = True

        asyncio.run(manager.respond_to_worker_harassment())

        gather_actions = [action for action in bot.actions if action[0] == "gather"]
        self.assertEqual(len(gather_actions), 2)
        self.assertEqual(manager._worker_harass_defender_tags, set())

    def test_tagged_harass_units_attack_workers_then_return_after_three_kills(self):
        bot = FakeBot()
        ling = FakeUnit(40, UnitTypeId.ZERGLING, Point2((95, 95)), can_attack=True)
        bot.units = UnitSource([bot.queen, ling])
        bot.enemy_units = FakeUnits(
            [FakeUnit(300, UnitTypeId.SCV, Point2((98, 98)), can_attack=False)]
        )
        manager = CombatManager(bot)
        manager.harass_units = {ling.tag}

        asyncio.run(manager.manage_harass_units(22))
        self.assertIn(("attack", 40, 300), bot.actions)

        bot.actions.clear()
        bot.enemy_units = FakeUnits()
        manager._harass_last_enemy_workers = 3
        asyncio.run(manager.manage_harass_units(23))

        move_actions = [action for action in bot.actions if action[0] == "move"]
        self.assertEqual(manager.harass_kill_count, 3)
        self.assertEqual(len(move_actions), 1)
        self.assertIn(40, manager.harass_returning_units)


if __name__ == "__main__":
    unittest.main()
