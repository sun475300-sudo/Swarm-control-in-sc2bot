# -*- coding: utf-8 -*-
import asyncio
import os
import sys
import unittest
from types import SimpleNamespace
from unittest.mock import AsyncMock, Mock

os.environ["PROTOCOL_BUFFERS_PYTHON_IMPLEMENTATION"] = "python"
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from bot_step_integration import BotStepIntegrator

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


class TestBotStepEmergencyExpansionGate(unittest.TestCase):
    def make_integrator(self, enemy_units=None):
        strategy = SimpleNamespace(
            emergency_spine_requested=True,
            emergency_spore_requested=True,
            is_air_threat_detected=Mock(return_value=False),
        )
        bot = SimpleNamespace(
            time=165.0,
            strategy_manager=strategy,
            townhalls=FakeUnits([FakeUnit(FakePoint(0, 0)), FakeUnit(FakePoint(80, 0))]),
            enemy_units=FakeUnits(enemy_units or []),
            build=AsyncMock(),
            can_afford=Mock(return_value=True),
            already_pending=Mock(return_value=0),
            game_info=SimpleNamespace(map_center=FakePoint(100, 100)),
        )
        empty = FakeUnits()
        pool = FakeUnits([FakeUnit(FakePoint(5, 5))])
        bot.structures = Mock(
            side_effect=lambda unit_type: {
                UnitTypeId.SPAWNINGPOOL: pool,
                UnitTypeId.SPINECRAWLER: empty,
                UnitTypeId.SPORECRAWLER: empty,
            }[unit_type]
        )

        integrator = BotStepIntegrator.__new__(BotStepIntegrator)
        integrator.bot = bot
        integrator.logger = Mock()
        return integrator, bot, strategy

    def test_emergency_static_defense_waits_for_third_without_base_threat(self):
        integrator, bot, strategy = self.make_integrator()

        asyncio.run(integrator._handle_emergency_defense(22))

        bot.build.assert_not_awaited()
        self.assertFalse(strategy.emergency_spine_requested)
        self.assertFalse(strategy.emergency_spore_requested)

    def test_single_scout_does_not_allow_emergency_spine_before_third(self):
        integrator, bot, strategy = self.make_integrator(
            enemy_units=[FakeUnit(FakePoint(8, 0))]
        )
        strategy.emergency_spore_requested = False

        asyncio.run(integrator._handle_emergency_defense(22))

        bot.build.assert_not_awaited()
        self.assertFalse(strategy.emergency_spine_requested)

    def test_emergency_spine_allowed_for_real_base_threat(self):
        integrator, bot, strategy = self.make_integrator(
            enemy_units=[FakeUnit(FakePoint(8 + offset, 0)) for offset in range(4)]
        )
        strategy.emergency_spore_requested = False

        asyncio.run(integrator._handle_emergency_defense(22))

        bot.build.assert_awaited_once()
        self.assertFalse(strategy.emergency_spine_requested)

    def test_low_air_threat_does_not_spend_spore_before_third(self):
        air_unit = FakeUnit(FakePoint(8, 0))
        air_unit.is_flying = True
        integrator, bot, strategy = self.make_integrator(enemy_units=[air_unit])
        strategy.emergency_spine_requested = False
        strategy.emergency_spore_requested = False
        strategy.is_air_threat_detected.return_value = True

        asyncio.run(integrator._handle_emergency_defense(22))

        bot.build.assert_not_awaited()


if __name__ == "__main__":
    unittest.main()
