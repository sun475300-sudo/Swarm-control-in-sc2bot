# -*- coding: utf-8 -*-
import asyncio
import os
import sys
import unittest
from types import SimpleNamespace
from unittest.mock import AsyncMock, Mock

os.environ["PROTOCOL_BUFFERS_PYTHON_IMPLEMENTATION"] = "python"
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

import pytest as _sc2_pytest

_sc2_pytest.importorskip("sc2", reason="python-sc2 library not installed")
from creep_expansion_system import CreepExpansionSystem
from sc2.ids.unit_typeid import UnitTypeId


class FakePoint:
    def __init__(self, x=50.0, y=50.0):
        self.x = x
        self.y = y


class FakeUnit:
    def __init__(self, tag=1, energy=50):
        self.tag = tag
        self.energy = energy
        self.position = FakePoint()

    def distance_to(self, target):
        return 5.0


class FailingCommandUnit(FakeUnit):
    def __call__(self, ability, target):
        raise AssertionError()


class FakeUnits(list):
    @property
    def amount(self):
        return len(self)

    @property
    def ready(self):
        return self

    def filter(self, predicate):
        return FakeUnits([unit for unit in self if predicate(unit)])


class TestCreepExpansionSystemGuards(unittest.TestCase):
    def _make_bot(self, unit):
        bot = Mock()
        bot.do = Mock()
        bot.has_creep = Mock(return_value=False)
        bot.get_available_abilities = AsyncMock(side_effect=AssertionError())
        bot.units = Mock(
            side_effect=lambda unit_type: (
                FakeUnits([unit]) if unit_type == UnitTypeId.QUEEN else FakeUnits()
            )
        )
        bot.structures = Mock(
            return_value=SimpleNamespace(amount=0, ready=FakeUnits([unit]))
        )
        return bot

    def test_queen_creep_skips_stale_ability_query(self):
        queen = FakeUnit(tag=11)
        bot = self._make_bot(queen)
        creep = CreepExpansionSystem(bot)
        creep.target_creep_positions = [FakePoint(55.0, 55.0)]

        asyncio.run(creep._queen_creep_tumors())

        bot.do.assert_not_called()
        bot.get_available_abilities.assert_awaited_once_with(queen)

    def test_tumor_spread_skips_stale_ability_query(self):
        tumor = FakeUnit(tag=22)
        bot = self._make_bot(tumor)
        creep = CreepExpansionSystem(bot)
        creep.target_creep_positions = [FakePoint(55.0, 55.0)]

        asyncio.run(creep._spread_creep_tumors())

        bot.do.assert_not_called()
        bot.get_available_abilities.assert_awaited_once_with(tumor)

    def test_creep_check_assertion_is_treated_as_no_creep(self):
        bot = Mock()
        bot.has_creep = Mock(side_effect=AssertionError())
        creep = CreepExpansionSystem(bot)

        self.assertFalse(creep._safe_has_creep(FakePoint()))

    def test_creep_command_assertion_is_skipped(self):
        bot = Mock()
        bot.do = Mock()
        creep = CreepExpansionSystem(bot)

        result = creep._issue_creep_command(
            FailingCommandUnit(tag=33), Mock(name="ability"), FakePoint()
        )

        self.assertFalse(result)
        bot.do.assert_not_called()

    def test_on_step_skips_transient_assertion(self):
        bot = Mock()
        bot.time = 220.0
        creep = CreepExpansionSystem(bot)
        creep._calculate_creep_targets = Mock(side_effect=AssertionError())
        creep._queen_creep_tumors = AsyncMock()
        creep._spread_creep_tumors = AsyncMock()

        asyncio.run(creep.on_step(220))

        creep._queen_creep_tumors.assert_not_awaited()


if __name__ == "__main__":
    unittest.main()
