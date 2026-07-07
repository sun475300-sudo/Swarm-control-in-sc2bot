# -*- coding: utf-8 -*-
"""
Unit tests for AdvancedBuildingManager.rescue_stuck_workers's
stuck-in-place detection (a worker that is moving but not actually
making progress, wedged between buildings).
"""

import os
import sys
import unittest
from unittest.mock import Mock

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from local_training.advanced_building_manager import AdvancedBuildingManager
from sc2.position import Point2


def make_worker(tag, position, is_idle=False):
    worker = Mock()
    worker.tag = tag
    worker.position = position
    worker.is_idle = is_idle
    worker.stop = Mock(return_value="stop_action")
    worker.gather = Mock(return_value="gather_action")
    return worker


def make_bot(workers):
    bot = Mock()
    bot.workers = workers
    bot.iteration = 0
    bot.do = Mock()
    bot.structures = Mock()
    bot.structures.closer_than = Mock(return_value=Mock(amount=2))
    bot.mineral_field = Mock()
    bot.mineral_field.exists = True
    bot.mineral_field.closest_to = Mock(return_value=Mock())
    return bot


class TestRescueStuckWorkers(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        self.worker = make_worker("w1", Point2((10.0, 10.0)))
        self.bot = make_bot([self.worker])
        self.manager = AdvancedBuildingManager(self.bot)

    async def test_worker_not_flagged_before_threshold(self):
        for _ in range(self.manager.stuck_in_place_threshold - 1):
            rescued = await self.manager.rescue_stuck_workers()
        self.assertEqual(rescued, 0)

    async def test_worker_wedged_in_place_is_rescued_after_threshold(self):
        rescued = 0
        for _ in range(self.manager.stuck_in_place_threshold + 1):
            rescued = await self.manager.rescue_stuck_workers()

        self.assertEqual(rescued, 1)
        self.bot.do.assert_any_call("stop_action")
        self.bot.do.assert_any_call("gather_action")

    async def test_moving_worker_is_never_flagged(self):
        positions = [Point2((10.0 + i, 10.0)) for i in range(6)]
        for pos in positions:
            self.worker.position = pos
            rescued = await self.manager.rescue_stuck_workers()

        self.assertEqual(rescued, 0)

    async def test_dead_worker_tracking_is_pruned(self):
        await self.manager.rescue_stuck_workers()
        self.assertIn("w1", self.manager._worker_last_positions)

        self.bot.workers = []
        await self.manager.rescue_stuck_workers()

        self.assertNotIn("w1", self.manager._worker_last_positions)
        self.assertNotIn("w1", self.manager._worker_stuck_ticks)


if __name__ == "__main__":
    unittest.main()
