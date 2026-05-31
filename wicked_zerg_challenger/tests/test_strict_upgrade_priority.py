# -*- coding: utf-8 -*-
import asyncio
import os
import sys
import unittest
from unittest.mock import MagicMock

os.environ["PROTOCOL_BUFFERS_PYTHON_IMPLEMENTATION"] = "python"
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from sc2.ids.unit_typeid import UnitTypeId
from sc2.ids.upgrade_id import UpgradeId
from strict_upgrade_priority import StrictUpgradePriority


class TestStrictUpgradePriorityExpansionReserve(unittest.TestCase):
    def test_metabolic_boost_waits_for_third_base_reserve(self):
        bot = MagicMock()
        bot.time = 150.0
        bot.minerals = 100
        bot.vespene = 100
        bot.townhalls.amount = 2
        bot.already_pending.return_value = 0
        bot.state.upgrades = set()

        manager = StrictUpgradePriority(bot)

        asyncio.run(manager._check_critical_upgrades())

        bot.structures.assert_not_called()
        self.assertNotIn(UpgradeId.ZERGLINGMOVEMENTSPEED, manager.upgrade_in_progress)

    def test_pending_third_releases_metabolic_boost(self):
        bot = MagicMock()
        bot.time = 150.0
        bot.minerals = 100
        bot.vespene = 100
        bot.townhalls.amount = 2
        bot.already_pending.side_effect = lambda unit_type: (
            1 if unit_type == UnitTypeId.HATCHERY else 0
        )
        bot.state.upgrades = set()

        pool = MagicMock()
        pool.research.return_value = True
        pools = MagicMock()
        pools.__bool__.return_value = True
        pools.idle.__bool__.return_value = True
        pools.idle.first = pool
        bot.structures.return_value.ready = pools

        manager = StrictUpgradePriority(bot)

        asyncio.run(manager._check_critical_upgrades())

        pool.research.assert_called_once_with(UpgradeId.ZERGLINGMOVEMENTSPEED)
        self.assertIn(UpgradeId.ZERGLINGMOVEMENTSPEED, manager.upgrade_in_progress)

    def test_pending_natural_still_reserves_metabolic_boost(self):
        bot = MagicMock()
        bot.time = 150.0
        bot.minerals = 100
        bot.vespene = 100
        bot.townhalls.amount = 1
        bot.already_pending.side_effect = lambda unit_type: (
            1 if unit_type == UnitTypeId.HATCHERY else 0
        )
        bot.state.upgrades = set()

        manager = StrictUpgradePriority(bot)

        asyncio.run(manager._check_critical_upgrades())

        bot.structures.assert_not_called()
        self.assertNotIn(UpgradeId.ZERGLINGMOVEMENTSPEED, manager.upgrade_in_progress)

    def test_pending_natural_in_townhall_amount_still_reserves_metabolic_boost(self):
        bot = MagicMock()
        bot.time = 150.0
        bot.minerals = 100
        bot.vespene = 100
        bot.townhalls.amount = 2
        bot.townhalls.ready.amount = 1
        bot.already_pending.side_effect = lambda unit_type: (
            1 if unit_type == UnitTypeId.HATCHERY else 0
        )
        bot.state.upgrades = set()

        manager = StrictUpgradePriority(bot)

        asyncio.run(manager._check_critical_upgrades())

        bot.structures.assert_not_called()
        self.assertNotIn(UpgradeId.ZERGLINGMOVEMENTSPEED, manager.upgrade_in_progress)

    def test_fourth_base_reserve_blocks_metabolic_boost_on_three_bases(self):
        bot = MagicMock()
        bot.time = 370.0
        bot.minerals = 100
        bot.vespene = 100
        bot.townhalls.amount = 3
        bot.townhalls.ready.amount = 3
        bot.already_pending.return_value = 0
        bot.state.upgrades = set()

        manager = StrictUpgradePriority(bot)

        asyncio.run(manager._check_critical_upgrades())

        bot.structures.assert_not_called()

    def test_pending_fourth_releases_metabolic_boost(self):
        bot = MagicMock()
        bot.time = 370.0
        bot.minerals = 100
        bot.vespene = 100
        bot.townhalls.amount = 3
        bot.townhalls.ready.amount = 3
        bot.already_pending.side_effect = lambda unit_type: (
            1 if unit_type == UnitTypeId.HATCHERY else 0
        )
        bot.state.upgrades = set()

        pool = MagicMock()
        pool.research.return_value = True
        pools = MagicMock()
        pools.__bool__.return_value = True
        pools.idle.__bool__.return_value = True
        pools.idle.first = pool
        bot.structures.return_value.ready = pools

        manager = StrictUpgradePriority(bot)

        asyncio.run(manager._check_critical_upgrades())

        pool.research.assert_called_once_with(UpgradeId.ZERGLINGMOVEMENTSPEED)


if __name__ == "__main__":
    unittest.main()
