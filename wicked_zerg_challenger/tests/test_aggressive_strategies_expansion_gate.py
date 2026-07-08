# -*- coding: utf-8 -*-
import asyncio
import os
import sys
import unittest
from unittest.mock import Mock

os.environ["PROTOCOL_BUFFERS_PYTHON_IMPLEMENTATION"] = "python"
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from aggressive_strategies import AggressiveStrategyExecutor, AggressiveStrategyType
from sc2.ids.unit_typeid import UnitTypeId


class FakeUnits(list):
    @property
    def ready(self):
        return self

    @property
    def amount(self):
        return len(self)


class TestAggressiveStrategiesExpansionGate(unittest.TestCase):
    def make_executor(self, ready_bases=2, pending_hatcheries=0, game_time=180.0):
        bot = Mock()
        bot.time = game_time
        bot.townhalls = FakeUnits([object() for _ in range(ready_bases)])
        bot.already_pending = Mock(
            side_effect=lambda unit_type: (
                pending_hatcheries if unit_type == UnitTypeId.HATCHERY else 0
            )
        )
        bot.do = Mock()
        bot.structures = Mock()

        executor = AggressiveStrategyExecutor.__new__(AggressiveStrategyExecutor)
        executor.bot = bot
        executor.blackboard = None
        executor.active_strategy = AggressiveStrategyType.BANELING_BUST
        executor.strategy_configs = {
            AggressiveStrategyType.BANELING_BUST: {"drone_limit": 13}
        }
        return executor, bot

    def test_execute_waits_for_third_hatchery_before_aggressive_spending(self):
        executor, bot = self.make_executor(ready_bases=2, pending_hatcheries=0)

        asyncio.run(executor.execute(22))

        bot.structures.assert_not_called()
        bot.do.assert_not_called()

    def test_drone_limit_is_removed_while_third_is_not_started(self):
        executor, _ = self.make_executor(ready_bases=2, pending_hatcheries=0)

        self.assertEqual(executor.get_drone_limit(), 80)
        self.assertFalse(executor.is_active())

    def test_pending_third_releases_aggressive_gate(self):
        executor, _ = self.make_executor(ready_bases=2, pending_hatcheries=1)

        self.assertFalse(executor._should_preserve_third_base_minerals())
        self.assertEqual(executor.get_drone_limit(), 13)
        self.assertTrue(executor.is_active())


if __name__ == "__main__":
    unittest.main()
