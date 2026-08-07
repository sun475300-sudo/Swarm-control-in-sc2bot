# -*- coding: utf-8 -*-
"""
Unit tests for AdvancedBuildingManager.rescue_stuck_workers position-history
based "moving but stuck" detection.
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
    return worker


def make_bot_with_worker(worker, jammed=True):
    bot = Mock()
    bot.workers = [worker]
    bot.iteration = 0
    bot.do = Mock()

    nearby_structures = Mock()
    nearby_structures.amount = 2 if jammed else 0
    bot.structures = Mock()
    bot.structures.closer_than = Mock(return_value=nearby_structures)

    bot.mineral_field = Mock()
    bot.mineral_field.exists = True
    bot.mineral_field.closest_to = Mock(return_value=Mock())

    return bot


class TestRescueStuckWorkers(unittest.IsolatedAsyncioTestCase):
    async def test_worker_frozen_between_buildings_is_rescued_after_streak(self):
        worker = make_worker(tag=1, position=Point2((5, 5)))
        bot = make_bot_with_worker(worker, jammed=True)
        manager = AdvancedBuildingManager(bot)

        # First check just establishes the position baseline, then each
        # subsequent unchanged check increments the stuck streak.
        self.assertEqual(await manager.rescue_stuck_workers(), 0)
        self.assertEqual(await manager.rescue_stuck_workers(), 0)
        self.assertEqual(await manager.rescue_stuck_workers(), 0)
        # Fourth check crosses STUCK_CHECK_STREAK (3 consecutive no-movement
        # observations after the baseline).
        rescued = await manager.rescue_stuck_workers()

        self.assertEqual(rescued, 1)
        bot.do.assert_called()

    async def test_worker_actually_moving_is_never_flagged_stuck(self):
        worker = make_worker(tag=2, position=Point2((0, 0)))
        bot = make_bot_with_worker(worker, jammed=True)
        manager = AdvancedBuildingManager(bot)

        for i in range(1, 6):
            worker.position = Point2((i * 2.0, 0))  # moves well past the threshold
            rescued = await manager.rescue_stuck_workers()
            self.assertEqual(rescued, 0)

    async def test_stationary_worker_without_nearby_buildings_is_not_rescued(self):
        # Not physically jammed between structures - just standing still.
        worker = make_worker(tag=3, position=Point2((5, 5)))
        bot = make_bot_with_worker(worker, jammed=False)
        manager = AdvancedBuildingManager(bot)

        for _ in range(4):
            rescued = await manager.rescue_stuck_workers()

        self.assertEqual(rescued, 0)
        bot.do.assert_not_called()

    async def test_position_history_is_pruned_for_workers_no_longer_present(self):
        worker = make_worker(tag=4, position=Point2((5, 5)))
        bot = make_bot_with_worker(worker, jammed=True)
        manager = AdvancedBuildingManager(bot)

        await manager.rescue_stuck_workers()
        self.assertIn(4, manager._worker_position_history)

        bot.workers = []  # worker died / morphed away
        await manager.rescue_stuck_workers()

        self.assertNotIn(4, manager._worker_position_history)


if __name__ == "__main__":
    unittest.main()
