# -*- coding: utf-8 -*-
"""Regression test for NydusNetworkTrainer._command_deployed_units.

The method was called from _manage_nydus_operations but never defined,
so every _manage_nydus_operations() call raised AttributeError (silently
swallowed by the on_step try/except) whenever a Nydus Network was active.
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
    def center(self):
        return Point2(
            (
                sum(u.position.x for u in self) / len(self),
                sum(u.position.y for u in self) / len(self),
            )
        )

    def filter(self, predicate):
        return FakeUnits([unit for unit in self if predicate(unit)])

    def closest_to(self, target):
        return min(self, key=lambda unit: unit.distance_to(target))


class FakeUnit:
    def __init__(self, tag, unit_type, position, is_idle=True):
        self.tag = tag
        self.type_id = unit_type
        self.position = position
        self.is_idle = is_idle

    def distance_to(self, target):
        target_pos = getattr(target, "position", target)
        return self.position.distance_to(target_pos)

    def attack(self, target):
        return ("attack", self.tag, getattr(target, "tag", target))


class FakeBot:
    def __init__(self):
        self.time = 300
        self.actions = []
        self.start_location = Point2((10, 10))
        self.enemy_start_locations = [Point2((150, 150))]
        self.units = FakeUnits()
        self.enemy_units = FakeUnits()
        self.enemy_structures = FakeUnits()

    def do(self, action):
        self.actions.append(action)


class TestNydusCommandDeployedUnits(unittest.TestCase):
    def test_command_deployed_units_attacks_idle_units(self):
        bot = FakeBot()
        roach = FakeUnit(1, UnitTypeId.ROACH, Point2((100, 100)), is_idle=True)
        bot.units = FakeUnits([roach])
        bot.enemy_units = FakeUnits(
            [FakeUnit(999, UnitTypeId.SCV, Point2((101, 101)))]
        )
        trainer = NydusNetworkTrainer(bot)
        trainer.units_deployed = {1}

        asyncio.run(trainer._command_deployed_units())

        self.assertIn(("attack", 1, Point2((101, 101))), bot.actions)

    def test_command_deployed_units_prunes_dead_unit_tags(self):
        bot = FakeBot()
        trainer = NydusNetworkTrainer(bot)
        trainer.units_in_transit = {5, 6}
        trainer.units_deployed = {7, 8}

        asyncio.run(trainer._command_deployed_units())

        self.assertEqual(trainer.units_in_transit, set())
        self.assertEqual(trainer.units_deployed, set())

    def test_command_deployed_units_skips_non_idle_units(self):
        bot = FakeBot()
        roach = FakeUnit(1, UnitTypeId.ROACH, Point2((100, 100)), is_idle=False)
        bot.units = FakeUnits([roach])
        trainer = NydusNetworkTrainer(bot)
        trainer.units_deployed = {1}

        asyncio.run(trainer._command_deployed_units())

        self.assertEqual(bot.actions, [])
        self.assertEqual(trainer.units_deployed, {1})


if __name__ == "__main__":
    unittest.main()
