# -*- coding: utf-8 -*-
"""Unit tests for `core.resource_manager.ResourceManager`.

The ResourceManager exists to fix Issue #4 in REMAINING_ISSUES.md
(race condition where multiple managers reserve the same resources
simultaneously). These tests pin its behaviour:

* `try_reserve` is atomic - it returns False (and reserves nothing) when
  insufficient resources remain.
* Concurrent `try_reserve` calls under a single lock cannot over-commit.
* `release` / `release_partial` correctly subtract from global reserves.
* `clear_stale_reservations` removes entries older than ~10 seconds.

Implemented as plain `unittest.TestCase` (no `pytest-asyncio` required) by
running each coroutine on its own event loop with `_async_run`.
"""

import asyncio
import os
import sys
import unittest
from unittest.mock import Mock

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

# core.resource_manager uses absolute import `wicked_zerg_challenger.utils.logger`,
# so the project parent has to be importable as well.
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))

from core.resource_manager import ResourceManager  # noqa: E402


def _async_run(coro):
    """Run a coroutine on a fresh event loop for the duration of one test."""
    loop = asyncio.new_event_loop()
    try:
        return loop.run_until_complete(coro)
    finally:
        loop.close()


class TestResourceManagerReservation(unittest.TestCase):
    def setUp(self):
        self.bot = Mock()
        self.bot.minerals = 1000
        self.bot.vespene = 500
        self.rm = ResourceManager(self.bot)

    def test_try_reserve_within_budget_succeeds(self):
        ok = _async_run(self.rm.try_reserve(200, 100, "BuildingManager"))
        self.assertTrue(ok)
        self.assertEqual(self.rm.get_reserved_resources(), (200, 100))
        self.assertEqual(self.rm.get_available_resources(), (800, 400))

    def test_try_reserve_exceeding_budget_fails(self):
        ok = _async_run(self.rm.try_reserve(1500, 0, "Greedy"))
        self.assertFalse(ok)
        self.assertEqual(self.rm.get_reserved_resources(), (0, 0))
        self.assertEqual(self.rm.failed_reservations, 1)

    def test_concurrent_reserves_cannot_over_commit(self):
        """Two managers each ask for 600M when only 1000M is available.
        Only the first should succeed; otherwise the lock is broken."""

        async def race():
            return await asyncio.gather(
                self.rm.try_reserve(600, 0, "ManagerA"),
                self.rm.try_reserve(600, 0, "ManagerB"),
            )

        results = _async_run(race())
        # Exactly one True, one False.
        self.assertEqual(sorted(results), [False, True])
        reserved_m, _ = self.rm.get_reserved_resources()
        self.assertEqual(reserved_m, 600)

    def test_release_returns_resources(self):
        _async_run(self.rm.try_reserve(300, 50, "X"))
        _async_run(self.rm.release("X"))
        self.assertEqual(self.rm.get_reserved_resources(), (0, 0))
        self.assertFalse(self.rm.has_reservation("X"))

    def test_release_partial_keeps_remainder(self):
        _async_run(self.rm.try_reserve(300, 100, "X"))
        _async_run(self.rm.release_partial("X", 100, 50))
        self.assertEqual(self.rm.get_reserved_resources(), (200, 50))
        self.assertEqual(self.rm.get_manager_reservation("X"), (200, 50))

    def test_release_partial_drains_to_zero_removes_entry(self):
        _async_run(self.rm.try_reserve(200, 0, "X"))
        _async_run(self.rm.release_partial("X", 200, 0))
        self.assertEqual(self.rm.get_reserved_resources(), (0, 0))
        self.assertFalse(self.rm.has_reservation("X"))

    def test_replacing_reservation_replaces_in_place(self):
        _async_run(self.rm.try_reserve(100, 0, "X"))
        _async_run(self.rm.try_reserve(150, 0, "X"))
        # The 100M is released and 150M is held, NOT 250M.
        self.assertEqual(self.rm.get_reserved_resources(), (150, 0))


class TestResourceManagerStats(unittest.TestCase):
    def test_statistics_track_attempts(self):
        bot = Mock()
        bot.minerals = 100
        bot.vespene = 0
        rm = ResourceManager(bot)

        _async_run(rm.try_reserve(50, 0, "A"))
        _async_run(rm.try_reserve(500, 0, "B"))  # fails
        stats = rm.get_statistics()
        self.assertEqual(stats["total_reservations"], 1)
        self.assertEqual(stats["failed_reservations"], 1)
        self.assertEqual(stats["active_reservations"], 1)
        # success_rate = 1 / (1 + 1) = 0.5
        self.assertEqual(stats["success_rate"], 0.5)


class TestStaleReservations(unittest.TestCase):
    def test_clear_stale_removes_old_entries(self):
        bot = Mock()
        bot.minerals = 500
        bot.vespene = 200
        rm = ResourceManager(bot)
        _async_run(rm.try_reserve(100, 50, "Forgetful"))

        # First sweep at iteration 0 - records start time, nothing cleared.
        _async_run(rm.clear_stale_reservations(0))
        self.assertTrue(rm.has_reservation("Forgetful"))

        # 250 frames later (>220 stale threshold) -> released.
        _async_run(rm.clear_stale_reservations(250))
        self.assertFalse(rm.has_reservation("Forgetful"))
        self.assertEqual(rm.get_reserved_resources(), (0, 0))


if __name__ == "__main__":
    unittest.main()
