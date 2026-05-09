# -*- coding: utf-8 -*-
import asyncio
import os
import sys
import unittest
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock

os.environ["PROTOCOL_BUFFERS_PYTHON_IMPLEMENTATION"] = "python"
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from sc2.ids.unit_typeid import UnitTypeId
from strategy.build_order_optimizer import BuildOrderOptimizer


class TestBuildOrderOptimizerOpeningExpansion(unittest.TestCase):
    def test_blocks_pool_and_gas_while_saving_for_first_hatchery(self):
        bot = MagicMock()
        bot.time = 65.0
        bot.supply_used = 18
        bot.minerals = 250
        bot.vespene = 0
        bot.townhalls.amount = 1
        bot.already_pending.return_value = 0

        optimizer = BuildOrderOptimizer(bot)
        optimizer.first_overlord_made = True

        asyncio.run(optimizer._execute_early_build_order())

        bot.structures.assert_not_called()
        bot.do.assert_not_called()
        self.assertFalse(optimizer.pool_placed)
        self.assertFalse(optimizer.gas_placed)

    def test_pending_hatchery_unblocks_followup_builds(self):
        bot = MagicMock()
        bot.time = 65.0
        bot.supply_used = 18
        bot.minerals = 250
        bot.vespene = 0
        bot.townhalls.amount = 1
        bot.townhalls.exists = True
        bot.townhalls.first = SimpleNamespace(position=MagicMock())
        bot.already_pending.side_effect = (
            lambda unit_type: 1 if unit_type == UnitTypeId.HATCHERY else 0
        )
        bot.find_placement = AsyncMock(return_value=None)
        bot.vespene_geyser.closer_than.return_value = []

        optimizer = BuildOrderOptimizer(bot)
        optimizer.first_overlord_made = True

        asyncio.run(optimizer._execute_early_build_order())

        self.assertTrue(optimizer.expansion_placed)
        bot.structures.assert_called()


if __name__ == "__main__":
    unittest.main()
