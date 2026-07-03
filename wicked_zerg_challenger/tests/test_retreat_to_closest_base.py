# -*- coding: utf-8 -*-
"""Regression test for CombatManager._retreat_to_closest_base (rust_accel wiring)."""

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


class FakeUnit:
    def __init__(self, tag, position):
        self.tag = tag
        self.type_id = UnitTypeId.DRONE
        self.position = position
        self.move_target = None

    def move(self, target):
        self.move_target = target
        return ("move", self.tag, target)


class FakeBot:
    def __init__(self):
        self.time = 60
        self.iteration = 1
        self.actions = []
        self.start_location = Point2((10, 10))
        self.townhalls = FakeUnits(
            [
                FakeUnit(1, Point2((0, 0))),
                FakeUnit(2, Point2((100, 100))),
                FakeUnit(3, Point2((50, 0))),
            ]
        )

    def do(self, action):
        self.actions.append(action)


class TestRetreatToClosestBase(unittest.TestCase):
    def test_each_unit_moves_to_its_own_nearest_townhall(self):
        bot = FakeBot()
        manager = CombatManager(bot)

        near_first = FakeUnit(10, Point2((1, 1)))
        near_third = FakeUnit(11, Point2((49, 1)))
        near_second = FakeUnit(12, Point2((99, 99)))

        asyncio.run(
            manager._retreat_to_closest_base([near_first, near_third, near_second])
        )

        self.assertEqual(near_first.move_target, bot.townhalls[0].position)
        self.assertEqual(near_third.move_target, bot.townhalls[2].position)
        self.assertEqual(near_second.move_target, bot.townhalls[1].position)

    def test_falls_back_to_main_base_when_no_townhalls(self):
        bot = FakeBot()
        bot.townhalls = FakeUnits([])
        manager = CombatManager(bot)

        unit = FakeUnit(20, Point2((5, 5)))
        asyncio.run(manager._retreat_to_closest_base([unit]))

        self.assertEqual(unit.move_target, bot.start_location)

    def test_empty_unit_list_is_a_no_op(self):
        bot = FakeBot()
        manager = CombatManager(bot)

        asyncio.run(manager._retreat_to_closest_base([]))

        self.assertEqual(bot.actions, [])


if __name__ == "__main__":
    unittest.main()
