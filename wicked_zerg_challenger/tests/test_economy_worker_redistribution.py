# -*- coding: utf-8 -*-
"""
Regression tests for EconomyManager worker-redistribution bugs found during
the 2026-07 audit:

1. `_redistribute_mineral_workers` removed a list entry by value using a
   locally-mutated `deficit`, which never matches the original tuple still
   held in the list (tuples are immutable) -> ValueError, silently
   swallowed by the enclosing except, truncating redistribution to a single
   over/under-saturated pair per call.

2. `_optimize_mineral_assignments` pushed `Mineral` field objects into
   `surplus_workers` instead of the actual over-assigned `Worker` units, so
   surplus workers were never fed into the deficit-patch reassignment loop.
"""

import os
import sys
import unittest
from unittest.mock import Mock

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from economy_manager import EconomyManager


class FakeUnits(list):
    """Minimal stand-in for sc2.units.Units supporting the subset of the API
    _redistribute_mineral_workers / _optimize_mineral_assignments rely on."""

    @property
    def amount(self):
        return len(self)

    @property
    def exists(self):
        return len(self) > 0

    def filter(self, fn):
        return FakeUnits(u for u in self if fn(u))

    def closer_than(self, distance, point):
        return FakeUnits(u for u in self if u.distance_to(point) < distance)

    def furthest_to(self, point):
        return max(self, key=lambda u: u.distance_to(point)) if self else None

    def closest_to(self, point):
        return min(self, key=lambda u: u.distance_to(point)) if self else None


class FakeTownhall:
    def __init__(self, tag, assigned, ideal):
        self.tag = tag
        self.assigned_harvesters = assigned
        self.ideal_harvesters = ideal

    def distance_to(self, other):
        return 0


class FakeMineral:
    def __init__(self, tag, mineral_contents=1500):
        self.tag = tag
        self.mineral_contents = mineral_contents

    def distance_to(self, other):
        return 0


class FakeWorker:
    def __init__(self, tag, dist=5.0):
        self.tag = tag
        self.is_gathering = True
        self.is_idle = False
        self.is_carrying_minerals = False
        self.is_carrying_vespene = False
        self.order_target = None
        self._dist = dist

    def distance_to(self, other):
        return self._dist

    def gather(self, target):
        return ("gather", self.tag, target)


class TestRedistributeMineralWorkers(unittest.IsolatedAsyncioTestCase):
    """Covers bug #1: tuple-identity removal crash truncating redistribution."""

    def _make_bot(self):
        bot = Mock()
        bot.iteration = 0
        bot.time = 100.0
        bot.do = Mock()

        # Over-saturated base: assigned 24 vs ideal 16 -> excess 8
        th_over = FakeTownhall(tag=1, assigned=24, ideal=16)
        # Under-saturated bases: deficits 6 and 3.
        # Pre-fix: filling th_under1 exactly (deficit -> 0) crashes the
        # `.remove()` call, so th_under2 is never reached at all.
        th_under1 = FakeTownhall(tag=2, assigned=10, ideal=16)
        th_under2 = FakeTownhall(tag=3, assigned=13, ideal=16)

        bot.townhalls = Mock()
        bot.townhalls.ready = FakeUnits([th_over, th_under1, th_under2])

        # Plenty of healthy minerals near every base -> nothing depleted.
        bot.mineral_field = Mock()
        bot.mineral_field.closer_than = Mock(
            return_value=FakeUnits(
                [
                    FakeMineral(tag=100, mineral_contents=1500),
                    FakeMineral(tag=101, mineral_contents=1500),
                ]
            )
        )

        # 10 idle-gathering workers near the over-saturated base - enough to
        # cover both transfers (6 + 2 = 8).
        bot.workers = FakeUnits(
            [FakeWorker(tag=200 + i, dist=5.0 + i * 0.01) for i in range(10)]
        )
        bot.gas_buildings = FakeUnits([])
        return bot, th_under1, th_under2

    async def test_redistribution_reaches_every_under_saturated_base(self):
        bot, th_under1, th_under2 = self._make_bot()
        manager = EconomyManager(bot)
        manager.logger.warning = Mock()

        await manager._redistribute_mineral_workers()

        # The bug swallowed a ValueError here and logged a warning instead
        # of completing the redistribution - assert it never fires.
        manager.logger.warning.assert_not_called()

        # bot.do should have been called once per worker actually moved:
        # 6 workers to th_under1 + 2 workers to th_under2 = 8 total.
        self.assertEqual(bot.do.call_count, 8)

    async def test_second_call_is_not_blocked_by_cooldown_bug(self):
        # Cooldown guard should not be affected by the fix; a second call
        # within 2s should simply no-op instead of raising.
        bot, _, _ = self._make_bot()
        manager = EconomyManager(bot)
        await manager._redistribute_mineral_workers()
        call_count_after_first = bot.do.call_count
        await manager._redistribute_mineral_workers()
        self.assertEqual(bot.do.call_count, call_count_after_first)


class TestOptimizeMineralAssignmentsSurplus(unittest.IsolatedAsyncioTestCase):
    """Covers bug #2: surplus_workers held Mineral objects, not Worker units,
    so over-assigned drones were never reassigned to deficit patches."""

    async def test_surplus_worker_is_reassigned_to_deficit_patch(self):
        bot = Mock()
        bot.iteration = 0
        bot.time = 100.0
        bot.do = Mock()

        townhall = FakeTownhall(tag=1, assigned=3, ideal=3)

        bot.townhalls = Mock()
        bot.townhalls.ready = FakeUnits([townhall])

        # Two healthy mineral patches: patch A gets 3 workers assigned but
        # only needs 2 (surplus 1); patch B gets 0 but needs 1 (deficit 1).
        patch_a = FakeMineral(tag=10)
        patch_b = FakeMineral(tag=11)

        nearby_minerals = FakeUnits([patch_a, patch_b])
        bot.mineral_field = Mock()
        bot.mineral_field.closer_than = Mock(return_value=nearby_minerals)
        # sorted() over FakeUnits distance is used inside the function;
        # patch_a should land in the "near" half (target 2), patch_b in the
        # "far" half (target 1) given len==2 -> half=1.

        workers_on_patch_a = [FakeWorker(tag=300 + i) for i in range(3)]
        for w in workers_on_patch_a:
            w.order_target = patch_a.tag

        bot.workers = Mock()
        bot.workers.closer_than = Mock(return_value=FakeUnits(workers_on_patch_a))

        manager = EconomyManager(bot)
        manager.logger.warning = Mock()

        await manager._optimize_mineral_assignments()

        manager.logger.warning.assert_not_called()
        # The surplus worker from patch_a must be re-gathered onto patch_b.
        self.assertEqual(bot.do.call_count, 1)
        gather_call = bot.do.call_args[0][0]
        self.assertEqual(gather_call, ("gather", 302, patch_b))


if __name__ == "__main__":
    unittest.main()
