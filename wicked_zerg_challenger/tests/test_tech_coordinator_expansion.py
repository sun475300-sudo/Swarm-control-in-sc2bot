# -*- coding: utf-8 -*-
import asyncio
import os
import sys
import unittest
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock

os.environ["PROTOCOL_BUFFERS_PYTHON_IMPLEMENTATION"] = "python"
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

import pytest

try:
    from sc2.ids.unit_typeid import UnitTypeId
    from sc2.position import Point2
except ImportError:  # pragma: no cover
    pytest.skip("sc2 library not available", allow_module_level=True)
from tech_coordinator import TechCoordinator


class TestTechCoordinatorExpansion(unittest.TestCase):
    def test_request_structure_accepts_requester_keyword(self):
        """EconomyManager keyword calls are accepted and requester is recorded."""
        bot = SimpleNamespace(iteration=12)
        coordinator = TechCoordinator(bot)
        target = Point2((60, 60))

        accepted = coordinator.request_structure(
            UnitTypeId.HATCHERY,
            target,
            priority=100,
            requester="EconomyManager",
        )

        self.assertTrue(accepted)
        self.assertEqual(
            coordinator.pending_requests[UnitTypeId.HATCHERY],
            (100, target, 12, "EconomyManager"),
        )

    def test_ready_starting_hatchery_does_not_clear_expansion_request(self):
        """A ready main Hatchery must not delete a pending natural expansion."""
        target = Point2((60, 60))
        worker = MagicMock()
        build_action = ("build", UnitTypeId.HATCHERY, target)
        worker.build.return_value = build_action

        bot = MagicMock()
        bot.iteration = 100
        bot.already_pending.return_value = 0
        bot.can_afford.return_value = True
        bot.do = MagicMock()
        bot.workers.exists = True
        bot.workers.closest_to.return_value = worker

        def structures(unit_type):
            if unit_type == UnitTypeId.HATCHERY:
                return SimpleNamespace(ready=SimpleNamespace(exists=True))
            return SimpleNamespace(ready=SimpleNamespace(exists=False))

        bot.structures.side_effect = structures

        coordinator = TechCoordinator(bot)
        coordinator.request_structure(
            UnitTypeId.HATCHERY,
            target,
            priority=100,
            requester="EconomyManager",
        )

        asyncio.run(coordinator.update())

        worker.build.assert_called_once_with(UnitTypeId.HATCHERY, target)
        bot.do.assert_called_once_with(build_action)
        self.assertNotIn(UnitTypeId.HATCHERY, coordinator.pending_requests)

    def test_opening_hatchery_reserves_minerals_before_other_structures(self):
        """While saving for first natural, lower structures must not spend minerals."""
        target = Point2((60, 60))
        bot = MagicMock()
        bot.time = 55.0
        bot.iteration = 100
        bot.townhalls.amount = 1
        bot.already_pending.return_value = 0
        bot.can_afford.side_effect = lambda unit_type: unit_type != UnitTypeId.HATCHERY
        bot.do = MagicMock()
        bot.build = MagicMock()
        bot.workers.exists = True

        def structures(unit_type):
            return SimpleNamespace(ready=SimpleNamespace(exists=False))

        bot.structures.side_effect = structures

        coordinator = TechCoordinator(bot)
        coordinator.request_structure(UnitTypeId.HATCHERY, target, 55, "BuildOrder")
        coordinator.request_structure(
            UnitTypeId.EXTRACTOR, Point2((52, 52)), 50, "BuildOrder"
        )

        asyncio.run(coordinator.update())

        bot.do.assert_not_called()
        bot.build.assert_not_called()
        self.assertIn(UnitTypeId.HATCHERY, coordinator.pending_requests)
        self.assertIn(UnitTypeId.EXTRACTOR, coordinator.pending_requests)

    def test_opening_hatchery_priority_beats_pool_when_affordable(self):
        """The first natural is executed before a higher-priority non-rush pool."""
        target = Point2((60, 60))
        worker = MagicMock()
        build_action = ("build", UnitTypeId.HATCHERY, target)
        worker.build.return_value = build_action

        bot = MagicMock()
        bot.time = 55.0
        bot.iteration = 100
        bot.townhalls.amount = 1
        bot.already_pending.return_value = 0
        bot.can_afford.return_value = True
        bot.do = MagicMock()
        bot.build = MagicMock()
        bot.workers.exists = True
        bot.workers.closest_to.return_value = worker

        def structures(unit_type):
            ready = unit_type == UnitTypeId.HATCHERY
            return SimpleNamespace(ready=SimpleNamespace(exists=ready))

        bot.structures.side_effect = structures

        coordinator = TechCoordinator(bot)
        coordinator.request_structure(UnitTypeId.HATCHERY, target, 55, "BuildOrder")
        coordinator.request_structure(
            UnitTypeId.SPAWNINGPOOL, Point2((52, 52)), 85, "Defense"
        )

        asyncio.run(coordinator.update())

        bot.do.assert_called_once_with(build_action)
        bot.build.assert_not_called()
        self.assertNotIn(UnitTypeId.HATCHERY, coordinator.pending_requests)
        self.assertIn(UnitTypeId.SPAWNINGPOOL, coordinator.pending_requests)

    def test_opening_natural_reserve_blocks_pool_before_hatch_request(self):
        """Before the natural is queued, pool requests wait behind hatch minerals."""
        bot = MagicMock()
        bot.time = 55.0
        bot.iteration = 100
        bot.townhalls.amount = 1
        bot.townhalls.ready.amount = 1
        bot.workers.amount = 15
        bot.blackboard = None
        bot.already_pending.return_value = 0
        bot.can_afford.return_value = True
        bot.do = MagicMock()
        bot.build = AsyncMock()
        bot.workers.exists = True

        def structures(unit_type):
            return SimpleNamespace(ready=SimpleNamespace(exists=False))

        bot.structures.side_effect = structures

        coordinator = TechCoordinator(bot)
        coordinator.request_structure(
            UnitTypeId.SPAWNINGPOOL, Point2((52, 52)), 85, "Defense"
        )

        asyncio.run(coordinator.update())

        bot.build.assert_not_called()
        self.assertIn(UnitTypeId.SPAWNINGPOOL, coordinator.pending_requests)

    def test_opening_natural_reserve_releases_after_hatch_pending(self):
        """Once the natural has started, queued pool requests can execute."""
        bot = MagicMock()
        bot.time = 75.0
        bot.iteration = 130
        bot.townhalls.amount = 1
        bot.townhalls.ready.amount = 1
        bot.workers.amount = 16
        bot.blackboard = None
        bot.already_pending.side_effect = lambda unit_type: (
            1 if unit_type == UnitTypeId.HATCHERY else 0
        )
        bot.can_afford.return_value = True
        bot.do = MagicMock()
        bot.build = AsyncMock()
        bot.workers.exists = True

        def structures(unit_type):
            return SimpleNamespace(ready=SimpleNamespace(exists=False))

        bot.structures.side_effect = structures

        coordinator = TechCoordinator(bot)
        coordinator.request_structure(
            UnitTypeId.SPAWNINGPOOL, Point2((52, 52)), 85, "Defense"
        )

        asyncio.run(coordinator.update())

        bot.build.assert_awaited_once()
        self.assertNotIn(UnitTypeId.SPAWNINGPOOL, coordinator.pending_requests)

    def test_under_expanded_reserve_blocks_non_hatchery_tech(self):
        """When below four bases, tech requests wait so minerals can reach 300."""
        bot = MagicMock()
        bot.time = 170.0
        bot.iteration = 250
        bot.townhalls.amount = 2
        bot.already_pending.return_value = 0
        bot.can_afford.return_value = True
        bot.do = MagicMock()
        bot.build = MagicMock()
        bot.workers.exists = True

        def structures(unit_type):
            return SimpleNamespace(ready=SimpleNamespace(exists=False))

        bot.structures.side_effect = structures

        coordinator = TechCoordinator(bot)
        coordinator.request_structure(
            UnitTypeId.SPAWNINGPOOL, Point2((52, 52)), 85, "Defense"
        )

        asyncio.run(coordinator.update())

        bot.do.assert_not_called()
        bot.build.assert_not_called()
        self.assertIn(UnitTypeId.SPAWNINGPOOL, coordinator.pending_requests)

    def test_single_scout_does_not_release_under_expanded_reserve(self):
        """A lone scout near a base must not spend minerals reserved for the third."""
        bot = MagicMock()
        bot.time = 170.0
        bot.iteration = 250
        bot.townhalls = [SimpleNamespace(), SimpleNamespace()]
        bot.blackboard = None
        bot.already_pending.return_value = 0
        bot.can_afford.return_value = True
        bot.do = MagicMock()
        bot.build = AsyncMock()
        bot.workers.exists = True
        bot.enemy_units.closer_than.return_value = SimpleNamespace(amount=1)

        def structures(unit_type):
            return SimpleNamespace(ready=SimpleNamespace(exists=False))

        bot.structures.side_effect = structures

        coordinator = TechCoordinator(bot)
        coordinator.request_structure(
            UnitTypeId.SPAWNINGPOOL, Point2((52, 52)), 85, "Defense"
        )

        asyncio.run(coordinator.update())

        bot.build.assert_not_called()
        self.assertIn(UnitTypeId.SPAWNINGPOOL, coordinator.pending_requests)

    def test_real_base_threat_releases_under_expanded_reserve(self):
        """A real rush near the base can spend reserved minerals on defense."""
        bot = MagicMock()
        bot.time = 170.0
        bot.iteration = 250
        bot.townhalls = [SimpleNamespace(), SimpleNamespace()]
        bot.blackboard = None
        bot.already_pending.return_value = 0
        bot.can_afford.return_value = True
        bot.do = MagicMock()
        bot.build = AsyncMock()
        bot.workers.exists = True
        bot.enemy_units.closer_than.return_value = SimpleNamespace(amount=4)

        def structures(unit_type):
            return SimpleNamespace(ready=SimpleNamespace(exists=False))

        bot.structures.side_effect = structures

        coordinator = TechCoordinator(bot)
        coordinator.request_structure(
            UnitTypeId.SPAWNINGPOOL, Point2((52, 52)), 85, "Defense"
        )

        asyncio.run(coordinator.update())

        bot.build.assert_awaited_once()
        self.assertNotIn(UnitTypeId.SPAWNINGPOOL, coordinator.pending_requests)

    def test_pending_natural_still_blocks_non_hatchery_tech(self):
        """A pending natural counted in total townhalls still reserves the third."""
        bot = MagicMock()
        bot.time = 170.0
        bot.iteration = 250
        bot.townhalls.amount = 2
        bot.townhalls.ready.amount = 1
        bot.already_pending.side_effect = lambda unit_type: (
            1 if unit_type == UnitTypeId.HATCHERY else 0
        )
        bot.can_afford.return_value = True
        bot.do = MagicMock()
        bot.build = AsyncMock()
        bot.workers.exists = True

        def structures(unit_type):
            return SimpleNamespace(ready=SimpleNamespace(exists=False))

        bot.structures.side_effect = structures

        coordinator = TechCoordinator(bot)
        coordinator.request_structure(
            UnitTypeId.SPINECRAWLER, Point2((52, 52)), 80, "EarlyDefense"
        )

        asyncio.run(coordinator.update())

        bot.do.assert_not_called()
        bot.build.assert_not_called()
        self.assertIn(UnitTypeId.SPINECRAWLER, coordinator.pending_requests)

    def test_pending_third_releases_non_hatchery_tech(self):
        """Once the third Hatchery is pending, other tech can resume."""
        bot = MagicMock()
        bot.time = 220.0
        bot.iteration = 320
        bot.townhalls.amount = 3
        bot.townhalls.ready.amount = 2
        bot.already_pending.side_effect = lambda unit_type: (
            1 if unit_type == UnitTypeId.HATCHERY else 0
        )
        bot.can_afford.return_value = True
        bot.do = MagicMock()
        bot.build = AsyncMock()
        bot.workers.exists = True

        def structures(unit_type):
            return SimpleNamespace(ready=SimpleNamespace(exists=False))

        bot.structures.side_effect = structures

        coordinator = TechCoordinator(bot)
        coordinator.request_structure(
            UnitTypeId.SPAWNINGPOOL, Point2((52, 52)), 85, "Defense"
        )

        asyncio.run(coordinator.update())

        bot.build.assert_awaited_once()
        self.assertNotIn(UnitTypeId.SPAWNINGPOOL, coordinator.pending_requests)

    def test_extractor_waits_until_opening_hatchery_started(self):
        """Gas requests cannot spend the first natural Hatchery minerals."""
        bot = MagicMock()
        bot.time = 70.0
        bot.iteration = 120
        bot.townhalls.amount = 1
        bot.already_pending.return_value = 0
        bot.can_afford.return_value = True
        bot.do = MagicMock()
        bot.build = MagicMock()
        bot.workers.exists = True

        def structures(unit_type):
            return SimpleNamespace(amount=0, ready=SimpleNamespace(exists=False))

        bot.structures.side_effect = structures

        coordinator = TechCoordinator(bot)
        coordinator.request_structure(
            UnitTypeId.EXTRACTOR, Point2((52, 52)), 50, "BuildOrder"
        )

        asyncio.run(coordinator.update())

        bot.do.assert_not_called()
        bot.build.assert_not_called()
        self.assertIn(UnitTypeId.EXTRACTOR, coordinator.pending_requests)

    def test_second_extractor_waits_until_third_base(self):
        """At two bases, the second gas waits behind the third Hatchery."""
        bot = MagicMock()
        bot.time = 150.0
        bot.iteration = 180
        bot.townhalls.amount = 2
        bot.already_pending.return_value = 0
        bot.can_afford.return_value = True
        bot.do = MagicMock()
        bot.build = MagicMock()
        bot.workers.exists = True

        def structures(unit_type):
            amount = 1 if unit_type == UnitTypeId.EXTRACTOR else 0
            return SimpleNamespace(amount=amount, ready=SimpleNamespace(exists=False))

        bot.structures.side_effect = structures

        coordinator = TechCoordinator(bot)
        coordinator.request_structure(
            UnitTypeId.EXTRACTOR, Point2((52, 52)), 50, "BuildOrder"
        )

        asyncio.run(coordinator.update())

        bot.do.assert_not_called()
        bot.build.assert_not_called()
        self.assertIn(UnitTypeId.EXTRACTOR, coordinator.pending_requests)


if __name__ == "__main__":
    unittest.main()
