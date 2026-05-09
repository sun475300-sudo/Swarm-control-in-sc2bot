# -*- coding: utf-8 -*-
import asyncio
import os
import sys
import unittest
from unittest.mock import AsyncMock, Mock

os.environ["PROTOCOL_BUFFERS_PYTHON_IMPLEMENTATION"] = "python"
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
sys.path.insert(
    0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "local_training"))
)

from local_training.resource_manager import ResourceManager
from sc2.ids.unit_typeid import UnitTypeId


class UnitList(list):
    @property
    def ready(self):
        return self

    @property
    def idle(self):
        return self

    @property
    def amount(self):
        return len(self)

    def filter(self, predicate):
        return UnitList([unit for unit in self if predicate(unit)])

    def closest_to(self, target):
        return self[0] if self else None

    def closer_than(self, distance, target):
        return self


class TestResourceManagerExpansionGate(unittest.TestCase):
    def setUp(self):
        self.bot = Mock()
        self.bot.workers.amount = 30
        self.bot.gas_buildings = []
        self.bot.townhalls.amount = 1
        self.bot.already_pending = Mock(return_value=0)
        self.bot.can_afford = Mock(return_value=True)
        self.manager = ResourceManager(self.bot)
        self.manager._build_extractor = AsyncMock()

    def test_auto_extractors_wait_for_opening_hatchery(self):
        """ResourceManager cannot build gas before the natural starts."""
        asyncio.run(self.manager._auto_build_extractors())

        self.manager._build_extractor.assert_not_awaited()

    def test_auto_second_extractor_waits_for_third_base(self):
        """ResourceManager caps gas at one Extractor until third base."""
        self.bot.townhalls.amount = 2
        self.bot.gas_buildings = [Mock()]
        self.bot.already_pending = Mock(return_value=0)

        asyncio.run(self.manager._auto_build_extractors())

        self.manager._build_extractor.assert_not_awaited()

    def test_first_extractor_allowed_after_hatchery_pending(self):
        """A pending natural unlocks the first gas."""
        self.bot.already_pending = Mock(
            side_effect=lambda unit_type: 1 if unit_type == UnitTypeId.HATCHERY else 0
        )

        asyncio.run(self.manager._auto_build_extractors())

        self.manager._build_extractor.assert_awaited_once()

    def test_gas_workers_not_refilled_when_mineral_starved(self):
        """Gas overflow blocks ResourceManager from pulling mineral workers back to gas."""
        extractor = Mock()
        extractor.tag = 100
        extractor.assigned_harvesters = 0

        worker = Mock()
        worker.tag = 1
        worker.is_gathering = True
        worker.is_carrying_vespene = False
        worker.order_target = Mock()
        worker.distance_to = Mock(return_value=5)
        worker.gather = Mock(return_value=("gather", "gas"))

        self.bot.minerals = 50
        self.bot.vespene = 1500
        self.bot.gas_buildings = Mock()
        self.bot.gas_buildings.ready = UnitList([extractor])
        self.bot.workers = UnitList([worker])
        self.bot.do = Mock()

        asyncio.run(self.manager._optimize_gas_workers())

        self.bot.do.assert_not_called()

    def test_gas_overflow_moves_existing_gas_workers_to_minerals(self):
        """Gas overflow actively sends gas workers back to mineral patches."""
        extractor = Mock()
        extractor.tag = 100
        extractor.assigned_harvesters = 3

        mineral = Mock()
        worker = Mock()
        worker.tag = 1
        worker.is_gathering = True
        worker.is_carrying_vespene = False
        worker.order_target = extractor.tag
        worker.gather = Mock(return_value=("gather", "mineral"))

        self.bot.minerals = 40
        self.bot.vespene = 2200
        self.bot.gas_buildings = Mock()
        self.bot.gas_buildings.ready = UnitList([extractor])
        self.bot.workers = UnitList([worker])
        self.bot.townhalls = UnitList([Mock()])
        self.bot.mineral_field = UnitList([mineral])
        self.bot.do = Mock()

        asyncio.run(self.manager._optimize_gas_workers())

        worker.gather.assert_called_once_with(mineral)
        self.bot.do.assert_called_once()


if __name__ == "__main__":
    unittest.main()
