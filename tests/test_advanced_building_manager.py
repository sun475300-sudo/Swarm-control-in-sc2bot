# -*- coding: utf-8 -*-
"""
Unit Tests for AdvancedBuildingManager.rescue_stuck_workers

정찰: 일꾼이 idle 상태가 아니어도, 여러 프레임 동안 위치가 거의 변하지
않으면(건물 사이에 끼여 이동 명령이 계속 실패하는 경우) "끼인 것"으로
간주해 강제로 채집 명령을 재발행해야 한다.
"""

import asyncio
import os
import sys
from unittest.mock import MagicMock

import pytest

sys.path.insert(
    0, os.path.join(os.path.dirname(__file__), "..", "wicked_zerg_challenger")
)

try:
    from local_training.advanced_building_manager import AdvancedBuildingManager
except ImportError:
    pytest.skip("AdvancedBuildingManager not available", allow_module_level=True)


class FakePosition:
    def __init__(self, x, y):
        self.x = x
        self.y = y


def _make_worker(tag, x, y, is_idle=False):
    w = MagicMock()
    w.tag = tag
    w.position = FakePosition(x, y)
    w.is_idle = is_idle
    return w


def _make_bot(workers, nearby_structure_count=2):
    bot = MagicMock()
    bot.workers = workers
    bot.iteration = 0

    nearby = MagicMock()
    nearby.amount = nearby_structure_count
    bot.structures.closer_than = MagicMock(return_value=nearby)

    bot.mineral_field.exists = True
    bot.mineral_field.closest_to = MagicMock(return_value=MagicMock())
    bot.do = MagicMock()
    return bot


class TestStuckWorkerPositionTracking:
    def test_worker_not_stuck_on_first_observation(self):
        """A worker's first position sample can't be judged stuck yet."""
        worker = _make_worker(tag=1, x=10.0, y=10.0)
        bot = _make_bot([worker])
        mgr = AdvancedBuildingManager(bot)

        rescued = asyncio.run(mgr.rescue_stuck_workers())
        assert rescued == 0

    def test_worker_flagged_after_consecutive_stationary_checks(self):
        """A non-idle worker whose position barely changes across
        stuck_check_threshold calls must be rescued."""
        worker = _make_worker(tag=2, x=10.0, y=10.0)
        bot = _make_bot([worker])
        mgr = AdvancedBuildingManager(bot)

        rescued_counts = [asyncio.run(mgr.rescue_stuck_workers()) for _ in range(4)]

        assert rescued_counts[-1] == 1
        bot.do.assert_called()

    def test_worker_not_flagged_when_actually_moving(self):
        """A worker whose position changes each step must never be rescued."""
        worker = _make_worker(tag=3, x=0.0, y=0.0)
        bot = _make_bot([worker])
        mgr = AdvancedBuildingManager(bot)

        for i in range(5):
            worker.position = FakePosition(float(i) * 2.0, 0.0)
            rescued = asyncio.run(mgr.rescue_stuck_workers())
            assert rescued == 0

    def test_stuck_counter_resets_after_rescue(self):
        """Once rescued, the counter must reset instead of re-triggering
        every subsequent call while the position sample lags behind."""
        worker = _make_worker(tag=4, x=5.0, y=5.0)
        bot = _make_bot([worker])
        mgr = AdvancedBuildingManager(bot)

        for _ in range(4):
            asyncio.run(mgr.rescue_stuck_workers())

        assert mgr._worker_stuck_counter[worker.tag] == 0

    def test_stale_worker_history_is_pruned(self):
        """Workers no longer present (died) must not leak in tracking dicts."""
        worker = _make_worker(tag=5, x=1.0, y=1.0)
        bot = _make_bot([worker])
        mgr = AdvancedBuildingManager(bot)

        asyncio.run(mgr.rescue_stuck_workers())
        assert 5 in mgr._worker_position_history

        bot.workers = []
        asyncio.run(mgr.rescue_stuck_workers())
        assert 5 not in mgr._worker_position_history
        assert 5 not in mgr._worker_stuck_counter
