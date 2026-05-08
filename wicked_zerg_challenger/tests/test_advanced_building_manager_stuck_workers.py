# -*- coding: utf-8 -*-
"""Regression tests for AdvancedBuildingManager._is_worker_position_stuck.

Covers the position-history-based stuck detector that supplements the
existing is_idle path in rescue_stuck_workers.
"""

from __future__ import annotations

import os
import sys
import unittest
from unittest.mock import MagicMock

import pytest

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

try:
    from local_training.advanced_building_manager import AdvancedBuildingManager
except ImportError:
    pytest.skip(
        "advanced_building_manager unavailable (sc2 missing)",
        allow_module_level=True,
    )


def _make_worker(tag: int, pos):
    w = MagicMock()
    w.tag = tag
    w.position = pos
    w.orders = ["mock_order"]
    return w


class TestStuckWorkerDetector(unittest.TestCase):
    def setUp(self):
        bot = MagicMock()
        bot.iteration = 0
        self.bot = bot
        self.mgr = AdvancedBuildingManager.__new__(AdvancedBuildingManager)
        self.mgr.bot = bot
        self.mgr._worker_position_history = {}
        self.mgr._stuck_movement_radius = 0.5
        self.mgr._stuck_check_interval = 25

    def test_first_observation_never_stuck(self):
        worker = _make_worker(1, (10.0, 10.0))
        self.assertFalse(self.mgr._is_worker_position_stuck(worker))

    def test_within_check_interval_never_stuck(self):
        worker = _make_worker(1, (10.0, 10.0))
        self.bot.iteration = 0
        self.mgr._is_worker_position_stuck(worker)
        self.bot.iteration = 5
        self.assertFalse(self.mgr._is_worker_position_stuck(worker))

    def test_position_not_drifted_after_interval_is_stuck(self):
        worker = _make_worker(1, (10.0, 10.0))
        self.bot.iteration = 0
        self.mgr._is_worker_position_stuck(worker)
        self.bot.iteration = 30
        worker.position = (10.1, 10.05)  # < 0.5 movement
        self.assertTrue(self.mgr._is_worker_position_stuck(worker))

    def test_position_drifted_enough_is_not_stuck(self):
        worker = _make_worker(1, (10.0, 10.0))
        self.bot.iteration = 0
        self.mgr._is_worker_position_stuck(worker)
        self.bot.iteration = 30
        worker.position = (12.0, 14.0)  # > 0.5 movement
        self.assertFalse(self.mgr._is_worker_position_stuck(worker))

    def test_missing_position_is_not_stuck(self):
        worker = MagicMock()
        worker.tag = 1
        worker.position = None
        worker.orders = ["x"]
        self.assertFalse(self.mgr._is_worker_position_stuck(worker))

    def test_has_orders_helper(self):
        with_orders = MagicMock()
        with_orders.orders = ["a"]
        without = MagicMock()
        without.orders = []
        self.assertTrue(AdvancedBuildingManager._has_orders(with_orders))
        self.assertFalse(AdvancedBuildingManager._has_orders(without))


if __name__ == "__main__":
    unittest.main()
