# -*- coding: utf-8 -*-
import asyncio
import os
import sys
import unittest
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock

os.environ["PROTOCOL_BUFFERS_PYTHON_IMPLEMENTATION"] = "python"
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

import pytest as _sc2_pytest

_sc2_pytest.importorskip("sc2", reason="python-sc2 library not installed")
from sc2.ids.unit_typeid import UnitTypeId
from sc2.ids.upgrade_id import UpgradeId
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

    def test_expand_now_attempt_without_pending_keeps_pool_and_gas_blocked(self):
        bot = MagicMock()
        bot.time = 85.0
        bot.supply_used = 18
        bot.minerals = 300
        bot.vespene = 0
        bot.townhalls.amount = 1
        bot.already_pending.return_value = 0
        bot.expand_now = AsyncMock(return_value=None)

        optimizer = BuildOrderOptimizer(bot)
        optimizer.first_overlord_made = True
        optimizer.expansion_placed = True

        asyncio.run(optimizer._execute_early_build_order())

        bot.structures.assert_not_called()
        self.assertFalse(optimizer.pool_placed)
        self.assertFalse(optimizer.gas_placed)

    def test_second_extractor_waits_until_third_base(self):
        bot = MagicMock()
        bot.time = 150.0
        bot.supply_used = 28
        bot.minerals = 300
        bot.townhalls.amount = 2
        bot.already_pending.return_value = 0
        bot.structures.return_value = SimpleNamespace(amount=1, exists=True)

        optimizer = BuildOrderOptimizer(bot)

        asyncio.run(optimizer._build_extractor())

        bot.do.assert_not_called()
        self.assertFalse(optimizer.gas_placed)

    def test_drone_saturation_waits_for_third_base(self):
        bot = MagicMock()
        bot.time = 190.0
        bot.minerals = 250
        bot.townhalls.amount = 2
        bot.townhalls.ready.amount = 2
        bot.already_pending.return_value = 0
        bot.structures.return_value.ready.amount = 1
        bot.units.side_effect = (
            lambda unit_type: SimpleNamespace(amount=20)
            if unit_type == UnitTypeId.DRONE
            else MagicMock()
        )

        optimizer = BuildOrderOptimizer(bot)

        asyncio.run(optimizer._manage_drone_saturation())

        bot.do.assert_not_called()

    def test_pending_third_unblocks_drone_saturation(self):
        bot = MagicMock()
        bot.time = 190.0
        bot.townhalls.amount = 2
        bot.townhalls.ready.amount = 2
        bot.already_pending.side_effect = (
            lambda unit_type: 1 if unit_type == UnitTypeId.HATCHERY else 0
        )

        optimizer = BuildOrderOptimizer(bot)

        self.assertFalse(optimizer._should_reserve_third_base())

    def test_fourth_base_reserve_blocks_on_three_bases(self):
        bot = MagicMock()
        bot.time = 370.0
        bot.townhalls.amount = 3
        bot.townhalls.ready.amount = 3
        bot.already_pending.return_value = 0

        optimizer = BuildOrderOptimizer(bot)

        self.assertTrue(optimizer._should_reserve_third_base())

    def test_pending_fourth_unblocks_reserve(self):
        bot = MagicMock()
        bot.time = 370.0
        bot.townhalls.amount = 3
        bot.townhalls.ready.amount = 3
        bot.already_pending.side_effect = (
            lambda unit_type: 1 if unit_type == UnitTypeId.HATCHERY else 0
        )

        optimizer = BuildOrderOptimizer(bot)

        self.assertFalse(optimizer._should_reserve_third_base())

    def test_pending_natural_still_reserves_for_third(self):
        bot = MagicMock()
        bot.time = 150.0
        bot.townhalls.amount = 1
        bot.townhalls.ready.amount = 1
        bot.already_pending.side_effect = (
            lambda unit_type: 1 if unit_type == UnitTypeId.HATCHERY else 0
        )

        optimizer = BuildOrderOptimizer(bot)

        self.assertTrue(optimizer._should_reserve_third_base())

    def test_pending_natural_in_townhall_amount_still_reserves_for_third(self):
        bot = MagicMock()
        bot.time = 150.0
        bot.townhalls.amount = 2
        bot.townhalls.ready.amount = 1
        bot.already_pending.side_effect = (
            lambda unit_type: 1 if unit_type == UnitTypeId.HATCHERY else 0
        )

        optimizer = BuildOrderOptimizer(bot)

        self.assertTrue(optimizer._should_reserve_third_base())

    def test_metabolic_boost_is_requested_only_once(self):
        bot = MagicMock()
        bot.time = 155.0
        bot.minerals = 100
        bot.vespene = 100
        bot.state.upgrades = set()
        bot.townhalls.amount = 3
        bot.townhalls.ready.amount = 3
        bot.already_pending.return_value = 0
        bot.already_pending_upgrade.return_value = 0

        pool = MagicMock()
        pool.research.return_value = ("research", UpgradeId.ZERGLINGMOVEMENTSPEED)
        pools = MagicMock()
        pools.__bool__.return_value = True
        pools.first = pool
        pools.idle = None
        bot.structures.return_value.ready = pools

        optimizer = BuildOrderOptimizer(bot)
        optimizer.first_queen_made = True

        optimizer._manage_gas_priority()
        optimizer._manage_gas_priority()

        self.assertTrue(optimizer.metabolic_boost_requested)
        pool.research.assert_called_once_with(UpgradeId.ZERGLINGMOVEMENTSPEED)
        bot.do.assert_called_once_with(("research", UpgradeId.ZERGLINGMOVEMENTSPEED))

    def test_metabolic_boost_pending_blocks_duplicate_request(self):
        bot = MagicMock()
        bot.time = 170.0
        bot.minerals = 100
        bot.vespene = 100
        bot.state.upgrades = set()
        bot.townhalls.amount = 3
        bot.townhalls.ready.amount = 3
        bot.already_pending.return_value = 0
        bot.already_pending_upgrade.return_value = 1

        pool = MagicMock()
        pools = MagicMock()
        pools.__bool__.return_value = True
        pools.first = pool
        bot.structures.return_value.ready = pools

        optimizer = BuildOrderOptimizer(bot)
        optimizer.first_queen_made = True

        optimizer._manage_gas_priority()

        self.assertTrue(optimizer.metabolic_boost_requested)
        pool.research.assert_not_called()
        bot.do.assert_not_called()

    def test_first_queen_waits_while_third_base_is_reserved(self):
        bot = MagicMock()
        bot.time = 190.0
        bot.townhalls.amount = 2
        bot.townhalls.ready.amount = 2
        bot.already_pending.return_value = 0

        optimizer = BuildOrderOptimizer(bot)

        self.assertFalse(optimizer._can_build_queen())
        bot.structures.assert_not_called()

    def test_metabolic_boost_waits_while_third_base_is_reserved(self):
        bot = MagicMock()
        bot.time = 190.0
        bot.minerals = 100
        bot.vespene = 100
        bot.townhalls.amount = 2
        bot.townhalls.ready.amount = 2
        bot.already_pending.return_value = 0
        bot.state.upgrades = set()

        optimizer = BuildOrderOptimizer(bot)
        optimizer.first_queen_made = True

        optimizer._manage_gas_priority()

        bot.structures.assert_not_called()
        bot.do.assert_not_called()


if __name__ == "__main__":
    unittest.main()
