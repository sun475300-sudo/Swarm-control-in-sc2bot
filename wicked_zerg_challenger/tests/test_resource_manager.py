# -*- coding: utf-8 -*-
"""
Unit tests for core.resource_manager.ResourceManager.

Focus areas:
- Basic reserve/release flow
- Insufficient resources rejection
- Re-reservation (cycle-6 regression: manager raising its own reservation
  must not be rejected when (current + own_old) would cover it)
- Partial release accounting
- Stale reservation cleanup
"""

import os
import sys
import unittest
from unittest.mock import Mock

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from core.resource_manager import ResourceManager


class TestResourceManagerReserve(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        self.bot = Mock()
        self.bot.minerals = 500
        self.bot.vespene = 200
        self.rm = ResourceManager(self.bot)

    async def test_basic_reserve_within_budget(self):
        ok = await self.rm.try_reserve(100, 50, "Builder")
        self.assertTrue(ok)
        self.assertEqual(self.rm.get_reserved_resources(), (100, 50))
        self.assertEqual(self.rm.get_available_resources(), (400, 150))

    async def test_reserve_rejects_when_insufficient(self):
        ok = await self.rm.try_reserve(600, 0, "Builder")
        self.assertFalse(ok)
        self.assertEqual(self.rm.get_reserved_resources(), (0, 0))

    async def test_reserve_rejects_when_other_manager_already_reserved(self):
        await self.rm.try_reserve(400, 0, "A")
        ok = await self.rm.try_reserve(150, 0, "B")
        self.assertFalse(ok)

    async def test_re_reservation_replaces_previous_atomically(self):
        # Cycle-6 regression: try_reserve(150) by manager X must succeed
        # when bot.minerals=200 and X already has 100 reserved
        # (because the old reservation will be released by this very call).
        self.bot.minerals = 200
        self.bot.vespene = 0
        await self.rm.try_reserve(100, 0, "Builder")
        self.assertEqual(self.rm.get_reserved_resources(), (100, 0))

        ok = await self.rm.try_reserve(150, 0, "Builder")
        self.assertTrue(
            ok, "re-reservation that fits within (avail+own_old) must succeed"
        )
        # Total reserved is exactly the new amount (replace, not add)
        self.assertEqual(self.rm.get_reserved_resources(), (150, 0))
        # Manager's reservation reflects the latest amount
        self.assertEqual(self.rm.get_manager_reservation("Builder"), (150, 0))

    async def test_re_reservation_cannot_exceed_total_when_others_reserved(self):
        self.bot.minerals = 200
        self.bot.vespene = 0
        await self.rm.try_reserve(100, 0, "Builder")
        await self.rm.try_reserve(50, 0, "Other")
        # Builder tries to raise to 200 — but Other holds 50, so only 150 should be free.
        ok = await self.rm.try_reserve(200, 0, "Builder")
        self.assertFalse(ok)
        # State remains the same
        self.assertEqual(self.rm.get_manager_reservation("Builder"), (100, 0))
        self.assertEqual(self.rm.get_reserved_resources(), (150, 0))

    async def test_release_clears_reservation(self):
        await self.rm.try_reserve(100, 50, "Builder")
        await self.rm.release("Builder")
        self.assertEqual(self.rm.get_reserved_resources(), (0, 0))
        self.assertIsNone(self.rm.get_manager_reservation("Builder"))

    async def test_release_partial(self):
        await self.rm.try_reserve(200, 100, "Builder")
        await self.rm.release_partial("Builder", 50, 30)
        self.assertEqual(self.rm.get_reserved_resources(), (150, 70))
        self.assertEqual(self.rm.get_manager_reservation("Builder"), (150, 70))

    async def test_release_partial_to_zero_clears_entry(self):
        await self.rm.try_reserve(50, 30, "Builder")
        await self.rm.release_partial("Builder", 50, 30)
        self.assertIsNone(self.rm.get_manager_reservation("Builder"))


class TestResourceManagerStatistics(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        self.bot = Mock()
        self.bot.minerals = 1000
        self.bot.vespene = 500
        self.rm = ResourceManager(self.bot)

    async def test_statistics_track_success_and_failure(self):
        await self.rm.try_reserve(100, 0, "A")
        await self.rm.try_reserve(2000, 0, "B")
        stats = self.rm.get_statistics()
        self.assertEqual(stats["total_reservations"], 1)
        self.assertEqual(stats["failed_reservations"], 1)
        self.assertAlmostEqual(stats["success_rate"], 0.5)


if __name__ == "__main__":
    unittest.main(verbosity=2)
