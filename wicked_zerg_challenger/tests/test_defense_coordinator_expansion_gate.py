# -*- coding: utf-8 -*-
import asyncio
import os
import sys
import unittest
from types import SimpleNamespace
from unittest.mock import AsyncMock, Mock

os.environ["PROTOCOL_BUFFERS_PYTHON_IMPLEMENTATION"] = "python"
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from defense_coordinator import DefenseCoordinator
import pytest as _sc2_pytest
_sc2_pytest.importorskip("sc2", reason="python-sc2 library not installed")
from sc2.ids.unit_typeid import UnitTypeId


class FakePoint:
    def __init__(self, x=0, y=0):
        self.x = x
        self.y = y

    def distance_to(self, other):
        other = getattr(other, "position", other)
        return ((self.x - other.x) ** 2 + (self.y - other.y) ** 2) ** 0.5

    def towards(self, other, distance):
        return FakePoint(self.x + distance, self.y)


class FakeUnit:
    def __init__(self, position=None):
        self.position = position or FakePoint()
        self.tag = id(self)
        self.is_flying = False
        self.build = Mock(return_value=("build", self.position))

    def distance_to(self, other):
        return self.position.distance_to(other)


class FakeUnits(list):
    @property
    def ready(self):
        return self

    @property
    def exists(self):
        return bool(self)

    @property
    def amount(self):
        return len(self)

    @property
    def first(self):
        return self[0]

    def closer_than(self, distance, target):
        return FakeUnits([unit for unit in self if unit.distance_to(target) < distance])

    def closest_to(self, target):
        return self[0]


class TestDefenseCoordinatorExpansionGate(unittest.TestCase):
    def setUp(self):
        self.main = FakeUnit(FakePoint(0, 0))
        self.natural = FakeUnit(FakePoint(80, 0))
        self.worker = FakeUnit(FakePoint(4, 0))

        self.bot = Mock()
        self.bot.time = 210.0
        self.bot.townhalls = FakeUnits([self.main, self.natural])
        self.bot.enemy_units = FakeUnits()
        self.bot.workers = FakeUnits([self.worker])
        self.bot.game_info = SimpleNamespace(map_center=FakePoint(100, 100))
        self.bot.do = Mock()
        self.bot.can_afford = Mock(return_value=True)
        self.bot.calculate_cost = Mock(return_value=SimpleNamespace(minerals=100, vespene=0))
        self.bot.resource_manager = SimpleNamespace(try_reserve=AsyncMock(return_value=True))

        pool = FakeUnits([FakeUnit(FakePoint(5, 5))])
        empty = FakeUnits()
        self.structures = {
            UnitTypeId.SPAWNINGPOOL: pool,
            UnitTypeId.SPINECRAWLER: empty,
            UnitTypeId.SPORECRAWLER: empty,
        }
        self.bot.structures = Mock(side_effect=lambda unit_type: self.structures[unit_type])

        self.blackboard = SimpleNamespace(
            threat=None,
            get_unit_count=Mock(return_value=SimpleNamespace(total=0)),
            request_production=Mock(),
        )
        self.manager = DefenseCoordinator(self.bot, self.blackboard)

    def test_static_defense_waits_for_third_without_base_threat(self):
        asyncio.run(self.manager._build_defense_structures())

        self.bot.resource_manager.try_reserve.assert_not_awaited()
        self.bot.do.assert_not_called()

    def test_single_scout_does_not_release_third_reserve(self):
        self.bot.enemy_units = FakeUnits([FakeUnit(FakePoint(8, 0))])

        asyncio.run(self.manager._build_defense_structures())

        self.bot.resource_manager.try_reserve.assert_not_awaited()
        self.bot.do.assert_not_called()

    def test_base_threat_allows_spine_before_third(self):
        self.bot.enemy_units = FakeUnits(
            [FakeUnit(FakePoint(8 + offset, 0)) for offset in range(4)]
        )

        asyncio.run(self.manager._build_defense_structures())

        self.bot.resource_manager.try_reserve.assert_awaited_once()
        self.worker.build.assert_called_once()
        self.bot.do.assert_called_once()

    def test_false_emergency_units_wait_for_third_without_base_threat(self):
        asyncio.run(self.manager._request_emergency_units())

        self.blackboard.request_production.assert_not_called()

    def test_single_scout_does_not_release_emergency_units(self):
        self.bot.enemy_units = FakeUnits([FakeUnit(FakePoint(8, 0))])

        asyncio.run(self.manager._request_emergency_units())

        self.blackboard.request_production.assert_not_called()

    def test_real_base_threat_allows_emergency_units_before_third(self):
        self.bot.enemy_units = FakeUnits(
            [FakeUnit(FakePoint(8 + offset, 0)) for offset in range(4)]
        )

        asyncio.run(self.manager._request_emergency_units())

        self.blackboard.request_production.assert_called()

    def test_proactive_spore_waits_for_third_without_air_threat(self):
        asyncio.run(self.manager._proactive_air_defense())

        self.assertFalse(self.manager.proactive_spore_requested)
        self.bot.do.assert_not_called()

    def test_static_defense_waits_for_fourth_without_base_threat(self):
        self.bot.time = 370.0
        self.bot.townhalls = FakeUnits(
            [self.main, self.natural, FakeUnit(FakePoint(120, 0))]
        )

        asyncio.run(self.manager._build_defense_structures())

        self.bot.resource_manager.try_reserve.assert_not_awaited()
        self.bot.do.assert_not_called()

    def test_pending_fourth_releases_static_defense_reserve(self):
        self.bot.time = 370.0
        self.bot.townhalls = FakeUnits(
            [self.main, self.natural, FakeUnit(FakePoint(120, 0))]
        )
        self.bot.already_pending = Mock(
            side_effect=lambda unit_type: 1
            if unit_type == UnitTypeId.HATCHERY
            else 0
        )

        self.assertFalse(self.manager._should_preserve_third_base_minerals())


if __name__ == "__main__":
    unittest.main()
