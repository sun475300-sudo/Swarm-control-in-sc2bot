# -*- coding: utf-8 -*-
"""Regression test for NydusNetworkTrainer._command_deployed_units.

_manage_nydus_operations() called self._command_deployed_units() every 5
seconds, but the method was never defined -- any nydus deployment would
crash with AttributeError as soon as a worm went active.
"""

import asyncio
import os
import sys
import unittest

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from nydus_network_trainer import NydusNetworkTrainer
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
    def idle(self):
        return FakeUnits([u for u in self if not u.orders])

    @property
    def center(self):
        if not self:
            return Point2((0, 0))
        x = sum(u.position.x for u in self) / len(self)
        y = sum(u.position.y for u in self) / len(self)
        return Point2((x, y))

    def filter(self, predicate):
        return FakeUnits([u for u in self if predicate(u)])

    def closest_to(self, target):
        target_pos = getattr(target, "position", target)
        return min(self, key=lambda u: u.distance_to(target_pos))


class UnitSource(FakeUnits):
    def __call__(self, unit_type):
        return FakeUnits([u for u in self if u.type_id == unit_type])


class FakeUnit:
    def __init__(self, tag, unit_type, position, orders=None):
        self.tag = tag
        self.type_id = unit_type
        self.position = position
        self.orders = orders or []

    def distance_to(self, target):
        target_pos = getattr(target, "position", target)
        return self.position.distance_to(target_pos)

    def attack(self, target):
        return ("attack", self.tag, getattr(target, "tag", target))


class FakeBot:
    def __init__(self, units):
        self.units = UnitSource(units)
        self.enemy_units = FakeUnits()
        self.enemy_structures = FakeUnits()
        self.enemy_start_locations = [Point2((100, 100))]
        self.actions = []

    def do(self, action):
        self.actions.append(action)


class TestCommandDeployedUnits(unittest.TestCase):
    def test_method_exists(self):
        bot = FakeBot([])
        trainer = NydusNetworkTrainer(bot)
        self.assertTrue(hasattr(trainer, "_command_deployed_units"))

    def test_removes_dead_units_from_deployed_set(self):
        alive = FakeUnit(1, UnitTypeId.ROACH, Point2((10, 10)))
        bot = FakeBot([alive])
        trainer = NydusNetworkTrainer(bot)
        trainer.units_deployed = {1, 999}

        asyncio.run(trainer._command_deployed_units())

        self.assertEqual(trainer.units_deployed, {1})

    def test_retargets_idle_deployed_units_toward_enemy(self):
        idle_unit = FakeUnit(1, UnitTypeId.ROACH, Point2((10, 10)))
        busy_unit = FakeUnit(2, UnitTypeId.ROACH, Point2((11, 11)), orders=["ATTACK"])
        bot = FakeBot([idle_unit, busy_unit])
        bot.enemy_units = FakeUnits([FakeUnit(50, UnitTypeId.SCV, Point2((12, 12)))])
        trainer = NydusNetworkTrainer(bot)
        trainer.units_deployed = {1, 2}

        asyncio.run(trainer._command_deployed_units())

        attack_actions = [a for a in bot.actions if a[0] == "attack"]
        self.assertEqual(len(attack_actions), 1)
        self.assertEqual(attack_actions[0][1], 1)

    def test_noop_when_nothing_deployed(self):
        bot = FakeBot([])
        trainer = NydusNetworkTrainer(bot)

        asyncio.run(trainer._command_deployed_units())

        self.assertEqual(bot.actions, [])


if __name__ == "__main__":
    unittest.main()
