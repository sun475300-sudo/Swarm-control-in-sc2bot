"""Unit tests for AdvancedBuildingManager.

Focused on the rescue_stuck_workers position-tracking logic.
"""

from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import MagicMock

import pytest

try:
    from sc2.ids.unit_typeid import UnitTypeId  # noqa: F401
except ImportError:
    pytest.skip("sc2 library not available", allow_module_level=True)


from wicked_zerg_challenger.local_training.advanced_building_manager import (
    AdvancedBuildingManager,
)


def _make_pos(x: float, y: float):
    return SimpleNamespace(x=float(x), y=float(y))


def _make_worker(tag: int, x: float, y: float, is_idle: bool = False):
    w = MagicMock()
    w.tag = tag
    w.position = _make_pos(x, y)
    w.is_idle = is_idle
    return w


def _make_bot(workers, iteration: int = 0):
    bot = MagicMock()
    bot.iteration = iteration
    bot.workers = workers
    # No structures / mineral_field — rescue body short-circuits at structures
    # check, so we still exercise the position-tracking path.
    bot.structures = MagicMock()
    bot.structures.closer_than = MagicMock(return_value=MagicMock(amount=0))
    bot.mineral_field = MagicMock()
    bot.mineral_field.exists = False
    return bot


class TestStuckWorkerTracking:
    async def test_first_call_records_baseline(self):
        worker = _make_worker(tag=1, x=10.0, y=10.0)
        bot = _make_bot([worker], iteration=0)
        mgr = AdvancedBuildingManager(bot)

        await mgr.rescue_stuck_workers()

        assert 1 in mgr._worker_positions
        pos, it = mgr._worker_positions[1]
        assert (pos.x, pos.y) == (10.0, 10.0)
        assert it == 0

    async def test_stationary_worker_flagged_after_window(self):
        worker = _make_worker(tag=1, x=10.0, y=10.0)
        bot = _make_bot([worker], iteration=0)
        mgr = AdvancedBuildingManager(bot)

        # First call records baseline at iteration 0
        await mgr.rescue_stuck_workers()
        # Advance bot iteration past the window without moving the worker
        bot.iteration = mgr._stuck_iteration_window + 1
        # Second call: the worker has not moved → stuck-detection should fire
        # and reset baseline for next window.
        await mgr.rescue_stuck_workers()

        # After detection, baseline iteration is updated to current iteration
        _, it = mgr._worker_positions[1]
        assert it == bot.iteration

    async def test_moving_worker_updates_baseline(self):
        worker = _make_worker(tag=1, x=10.0, y=10.0)
        bot = _make_bot([worker], iteration=0)
        mgr = AdvancedBuildingManager(bot)

        await mgr.rescue_stuck_workers()
        # Move the worker beyond eps and advance iteration
        worker.position = _make_pos(15.0, 15.0)
        bot.iteration = 10
        await mgr.rescue_stuck_workers()

        pos, it = mgr._worker_positions[1]
        assert (pos.x, pos.y) == (15.0, 15.0)
        assert it == 10

    async def test_dead_worker_tag_pruned(self):
        worker = _make_worker(tag=1, x=10.0, y=10.0)
        bot = _make_bot([worker], iteration=0)
        mgr = AdvancedBuildingManager(bot)

        await mgr.rescue_stuck_workers()
        assert 1 in mgr._worker_positions

        # Worker dies — bot.workers no longer contains tag 1
        bot.workers = []
        await mgr.rescue_stuck_workers()

        assert 1 not in mgr._worker_positions
