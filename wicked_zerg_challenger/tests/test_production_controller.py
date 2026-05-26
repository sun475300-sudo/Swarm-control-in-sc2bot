# -*- coding: utf-8 -*-
import asyncio
import os
import sys
import unittest
from unittest.mock import MagicMock

os.environ["PROTOCOL_BUFFERS_PYTHON_IMPLEMENTATION"] = "python"
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

import pytest

try:
    from sc2.ids.unit_typeid import UnitTypeId
except ImportError:  # pragma: no cover
    pytest.skip("sc2 library not available", allow_module_level=True)
from production_controller import ProductionController


class TestProductionControllerThirdBaseReserve(unittest.TestCase):
    def _make_bot(self, time=150.0, ready_bases=1, pending_hatcheries=1):
        bot = MagicMock()
        bot.time = time
        bot.minerals = 200
        bot.vespene = 100
        bot.supply_left = 8
        bot.supply_cap = 30
        bot.can_afford.return_value = True
        bot.supply_army = 0

        larva_unit = MagicMock()
        larva_unit.train.side_effect = lambda unit_type: ("train", unit_type)
        larvae = MagicMock()
        larvae.__bool__.return_value = True
        larvae.__len__.return_value = 1
        larvae.__iter__.return_value = iter([larva_unit])
        bot.larva = larvae

        townhalls = MagicMock()
        townhalls.amount = ready_bases
        townhalls.ready.amount = ready_bases
        townhalls.__iter__.return_value = iter([])
        bot.townhalls = townhalls
        bot.already_pending.side_effect = lambda unit_type: (
            pending_hatcheries if unit_type == UnitTypeId.HATCHERY else 0
        )
        bot.enemy_units.closer_than.return_value.amount = 0

        def units_by_type(unit_type):
            group = MagicMock()
            group.amount = 0
            return group

        bot.units.side_effect = units_by_type
        return bot

    def _make_blackboard(self, request):
        blackboard = MagicMock()
        blackboard.build_order_complete = False
        blackboard.get_next_production.side_effect = [request, None]
        blackboard.get_authority_priority.return_value = 0
        return blackboard

    def test_reserve_blocks_queen_while_natural_is_pending(self):
        bot = self._make_bot(time=150.0, ready_bases=1, pending_hatcheries=1)
        blackboard = self._make_blackboard((UnitTypeId.QUEEN, 1, "DefenseCoordinator"))
        controller = ProductionController(bot, blackboard)

        asyncio.run(controller._process_production_queue())

        bot.can_afford.assert_not_called()
        blackboard.request_production.assert_called_with(
            UnitTypeId.QUEEN, 1, "DefenseCoordinator", 0
        )

    def test_pending_natural_in_townhall_amount_still_blocks_queen(self):
        bot = self._make_bot(time=150.0, ready_bases=1, pending_hatcheries=1)
        bot.townhalls.amount = 2
        bot.townhalls.ready.amount = 1
        blackboard = self._make_blackboard((UnitTypeId.QUEEN, 1, "DefenseCoordinator"))
        controller = ProductionController(bot, blackboard)

        asyncio.run(controller._process_production_queue())

        bot.can_afford.assert_not_called()
        blackboard.request_production.assert_called_with(
            UnitTypeId.QUEEN, 1, "DefenseCoordinator", 0
        )

    def test_pending_third_releases_queen_production(self):
        bot = self._make_bot(time=190.0, ready_bases=2, pending_hatcheries=1)
        townhall = MagicMock()
        bot.townhalls.ready.idle = [townhall]
        blackboard = self._make_blackboard((UnitTypeId.QUEEN, 1, "DefenseCoordinator"))
        controller = ProductionController(bot, blackboard)

        asyncio.run(controller._process_production_queue())

        townhall.train.assert_called_once_with(UnitTypeId.QUEEN)
        bot.do.assert_called_once()

    def test_fourth_base_reserve_blocks_queen_on_three_bases(self):
        bot = self._make_bot(time=370.0, ready_bases=3, pending_hatcheries=0)
        blackboard = self._make_blackboard((UnitTypeId.QUEEN, 1, "DefenseCoordinator"))
        controller = ProductionController(bot, blackboard)

        asyncio.run(controller._process_production_queue())

        bot.can_afford.assert_not_called()
        blackboard.request_production.assert_called_with(
            UnitTypeId.QUEEN, 1, "DefenseCoordinator", 0
        )

    def test_pending_fourth_releases_queen_production(self):
        bot = self._make_bot(time=370.0, ready_bases=3, pending_hatcheries=1)
        townhall = MagicMock()
        bot.townhalls.ready.idle = [townhall]
        blackboard = self._make_blackboard((UnitTypeId.QUEEN, 1, "DefenseCoordinator"))
        controller = ProductionController(bot, blackboard)

        asyncio.run(controller._process_production_queue())

        townhall.train.assert_called_once_with(UnitTypeId.QUEEN)

    def test_overlord_is_allowed_during_third_base_reserve(self):
        bot = self._make_bot(time=150.0, ready_bases=1, pending_hatcheries=1)
        blackboard = self._make_blackboard((UnitTypeId.OVERLORD, 1, "UnitFactory"))
        controller = ProductionController(bot, blackboard)

        self.assertTrue(controller._should_reserve_third_base_minerals())
        self.assertTrue(
            controller._can_spend_during_third_base_reserve(
                UnitTypeId.OVERLORD, "UnitFactory"
            )
        )

    def test_zergling_is_allowed_to_restore_minimum_defense(self):
        bot = self._make_bot(time=230.0, ready_bases=2, pending_hatcheries=0)
        blackboard = self._make_blackboard((UnitTypeId.ZERGLING, 1, "UnitFactory"))
        controller = ProductionController(bot, blackboard)

        asyncio.run(controller._process_production_queue())

        bot.do.assert_called_once_with(("train", UnitTypeId.ZERGLING))
        blackboard.request_production.assert_not_called()

    def test_zergling_is_blocked_after_minimum_defense_is_met(self):
        bot = self._make_bot(time=230.0, ready_bases=2, pending_hatcheries=0)
        bot.supply_army = 10
        blackboard = self._make_blackboard((UnitTypeId.ZERGLING, 1, "UnitFactory"))
        controller = ProductionController(bot, blackboard)

        asyncio.run(controller._process_production_queue())

        bot.do.assert_not_called()
        blackboard.request_production.assert_called_with(
            UnitTypeId.ZERGLING, 1, "UnitFactory", 0
        )


if __name__ == "__main__":
    unittest.main()
