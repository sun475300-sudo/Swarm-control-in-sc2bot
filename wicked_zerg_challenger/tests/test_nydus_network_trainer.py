# -*- coding: utf-8 -*-
"""Regression tests for NydusNetworkTrainer._command_deployed_units.

The method was called from _manage_nydus_operations but never defined,
so it silently AttributeError'd every time a Nydus Network was active
(swallowed by the on_step try/except). See TODO.md priority list /
tools/check_missing_logic.py output.
"""

import asyncio
import os
import sys
import unittest

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from nydus_network_trainer import NydusNetworkTrainer
from sc2.position import Point2


class FakeUnits(list):
    @property
    def idle(self):
        return FakeUnits([u for u in self if not u.orders])

    @property
    def center(self):
        xs = [u.position.x for u in self]
        ys = [u.position.y for u in self]
        return Point2((sum(xs) / len(xs), sum(ys) / len(ys)))

    def filter(self, predicate):
        return FakeUnits([u for u in self if predicate(u)])

    def __call__(self, unit_type):
        return FakeUnits([u for u in self if getattr(u, "type_id", None) == unit_type])


class FakeUnit:
    def __init__(self, tag, position, orders=None, type_id=None):
        self.tag = tag
        self.position = position
        self.orders = orders if orders is not None else []
        self.type_id = type_id

    def attack(self, target):
        return ("attack", self.tag, target)


class FakeBot:
    def __init__(self, units):
        self.units = units
        self.time = 100.0
        self.enemy_units = FakeUnits()
        self.enemy_structures = FakeUnits()
        self.enemy_start_locations = [Point2((10, 10))]
        self.do_calls = []

    def do(self, action):
        self.do_calls.append(action)


class CommandDeployedUnitsTest(unittest.TestCase):
    def test_dead_unit_tags_are_pruned_from_tracking_sets(self):
        alive = FakeUnit(tag=1, position=Point2((0, 0)), orders=["moving"])
        bot = FakeBot(FakeUnits([alive]))
        trainer = NydusNetworkTrainer(bot)
        trainer.units_in_transit = {1, 2, 3}
        trainer.units_deployed = {1, 2}

        asyncio.run(trainer._command_deployed_units())

        self.assertEqual(trainer.units_in_transit, {1})
        self.assertEqual(trainer.units_deployed, {1})

    def test_idle_deployed_units_are_retargeted(self):
        idle_unit = FakeUnit(tag=1, position=Point2((0, 0)), orders=[])
        busy_unit = FakeUnit(tag=2, position=Point2((2, 2)), orders=["attacking"])
        bot = FakeBot(FakeUnits([idle_unit, busy_unit]))
        trainer = NydusNetworkTrainer(bot)
        trainer.units_deployed = {1, 2}

        asyncio.run(trainer._command_deployed_units())

        self.assertEqual(len(bot.do_calls), 1)
        action, tag, target = bot.do_calls[0]
        self.assertEqual(action, "attack")
        self.assertEqual(tag, 1)
        self.assertEqual(target, Point2((10, 10)))

    def test_no_deployed_units_is_a_noop(self):
        bot = FakeBot(FakeUnits([]))
        trainer = NydusNetworkTrainer(bot)

        asyncio.run(trainer._command_deployed_units())

        self.assertEqual(bot.do_calls, [])

    def test_all_deployed_units_busy_sends_no_orders(self):
        busy_unit = FakeUnit(tag=1, position=Point2((0, 0)), orders=["attacking"])
        bot = FakeBot(FakeUnits([busy_unit]))
        trainer = NydusNetworkTrainer(bot)
        trainer.units_deployed = {1}

        asyncio.run(trainer._command_deployed_units())

        self.assertEqual(bot.do_calls, [])


if __name__ == "__main__":
    unittest.main()
