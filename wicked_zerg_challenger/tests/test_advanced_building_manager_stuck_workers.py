# -*- coding: utf-8 -*-
"""Regression tests for AdvancedBuildingManager.rescue_stuck_workers position tracking."""

import asyncio
import os
import sys
import unittest

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from local_training.advanced_building_manager import AdvancedBuildingManager
from sc2.position import Point2


class FakeUnits(list):
    @property
    def exists(self):
        return bool(self)

    @property
    def amount(self):
        return len(self)

    def closer_than(self, distance, target):
        return FakeUnits([unit for unit in self if unit.distance_to(target) < distance])

    def closest_to(self, target):
        return min(self, key=lambda unit: unit.distance_to(target))


class FakeUnit:
    def __init__(self, tag, position, is_idle=False):
        self.tag = tag
        self.position = position
        self.is_idle = is_idle
        self.stopped = False
        self.gathered = None

    def distance_to(self, target):
        target_pos = getattr(target, "position", target)
        return self.position.distance_to(target_pos)

    def stop(self):
        self.stopped = True
        return ("stop", self.tag)

    def gather(self, target):
        self.gathered = getattr(target, "tag", target)
        return ("gather", self.tag, self.gathered)


class FakeBot:
    def __init__(self, workers):
        self.iteration = 0
        self.actions = []
        self.workers = FakeUnits(workers)
        # Two structures within 2.0 of every worker so the "wedged" branch fires.
        self.structures = FakeUnits(
            [FakeUnit(900, Point2((50, 50))), FakeUnit(901, Point2((50.5, 50)))]
        )
        self.mineral_field = FakeUnits([FakeUnit(902, Point2((48, 48)))])

    def do(self, action):
        self.actions.append(action)


class TestRescueStuckWorkers(unittest.TestCase):
    def test_idle_worker_rescued_immediately(self):
        bot = FakeBot([FakeUnit(1, Point2((51, 51)), is_idle=True)])
        manager = AdvancedBuildingManager(bot)

        rescued = asyncio.run(manager.rescue_stuck_workers())

        self.assertEqual(rescued, 1)
        self.assertTrue(bot.workers[0].stopped)

    def test_moving_but_stationary_worker_rescued_after_threshold(self):
        worker = FakeUnit(2, Point2((51, 51)), is_idle=False)
        bot = FakeBot([worker])
        manager = AdvancedBuildingManager(bot)

        # First few checks just record position / build up stall count
        # (threshold is 3 *consecutive stalled intervals*, i.e. the 4th check).
        self.assertEqual(asyncio.run(manager.rescue_stuck_workers()), 0)
        self.assertEqual(asyncio.run(manager.rescue_stuck_workers()), 0)
        self.assertEqual(asyncio.run(manager.rescue_stuck_workers()), 0)
        rescued = asyncio.run(manager.rescue_stuck_workers())

        self.assertEqual(rescued, 1)
        self.assertTrue(worker.stopped)

    def test_worker_actually_moving_is_never_flagged_stuck(self):
        worker = FakeUnit(3, Point2((51, 51)), is_idle=False)
        bot = FakeBot([worker])
        manager = AdvancedBuildingManager(bot)

        for i in range(5):
            worker.position = Point2((51 + i, 51))
            rescued = asyncio.run(manager.rescue_stuck_workers())
            self.assertEqual(rescued, 0)

    def test_stall_history_pruned_when_worker_disappears(self):
        worker = FakeUnit(4, Point2((51, 51)), is_idle=False)
        bot = FakeBot([worker])
        manager = AdvancedBuildingManager(bot)

        asyncio.run(manager.rescue_stuck_workers())
        self.assertIn(4, manager._worker_last_position)

        bot.workers = FakeUnits([])
        asyncio.run(manager.rescue_stuck_workers())
        self.assertNotIn(4, manager._worker_last_position)
        self.assertNotIn(4, manager._worker_stall_ticks)


if __name__ == "__main__":
    unittest.main()
