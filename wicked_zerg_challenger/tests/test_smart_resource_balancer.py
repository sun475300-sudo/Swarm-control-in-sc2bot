# -*- coding: utf-8 -*-
import asyncio
import os
import sys
import unittest
from unittest.mock import Mock

os.environ["PROTOCOL_BUFFERS_PYTHON_IMPLEMENTATION"] = "python"
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

import pytest as _sc2_pytest
_sc2_pytest.importorskip("sc2", reason="python-sc2 library not installed")
from sc2.ids.unit_typeid import UnitTypeId
from smart_resource_balancer import SmartResourceBalancer


class UnitList(list):
    @property
    def ready(self):
        return self

    def closest_to(self, target):
        return self[0] if self else None

    def closer_than(self, distance, target):
        return self


def make_target(type_name):
    target = Mock()
    target.type_id = Mock()
    target.type_id.name = type_name
    return target


class TestSmartResourceBalancer(unittest.TestCase):
    def setUp(self):
        self.bot = Mock()
        self.bot.minerals = 50
        self.bot.vespene = 2500
        self.bot.time = 500
        self.bot.gas_buildings = Mock()
        self.bot.gas_buildings.ready = UnitList()
        self.bot.do = Mock()
        self.balancer = SmartResourceBalancer(self.bot)

    def test_initializes_mineral_critical_threshold(self):
        """Critical mineral threshold exists despite legacy comment corruption."""
        self.assertEqual(self.balancer.mineral_critical_threshold, 100)

    def test_order_target_tag_counts_as_gas_worker(self):
        """Workers targeting an extractor tag count as gas workers."""
        extractor = Mock()
        extractor.tag = 100
        self.bot.gas_buildings.ready = UnitList([extractor])

        gas_worker = Mock()
        gas_worker.is_gathering = True
        gas_worker.is_carrying_vespene = False
        gas_worker.order_target = extractor.tag

        mineral_worker = Mock()
        mineral_worker.is_gathering = True
        mineral_worker.is_carrying_vespene = False
        mineral_worker.order_target = make_target("MINERALFIELD")

        self.bot.workers = UnitList([gas_worker, mineral_worker])

        self.assertEqual(self.balancer._get_current_worker_ratio(), 1.0)

    def test_gas_overflow_moves_tagged_gas_worker_to_minerals(self):
        """Critical gas overflow pulls workers from extractor tags to minerals."""
        extractor = Mock()
        extractor.tag = 100
        self.bot.gas_buildings.ready = UnitList([extractor])

        mineral = Mock()
        worker = Mock()
        worker.is_gathering = True
        worker.is_carrying_vespene = False
        worker.order_target = extractor.tag
        worker.gather = Mock(return_value=("gather", "mineral"))

        self.bot.workers = UnitList([worker])
        self.bot.townhalls = UnitList([Mock()])
        self.bot.mineral_field = UnitList([mineral])

        asyncio.run(self.balancer.on_step(30))

        worker.gather.assert_called_once_with(mineral)
        self.bot.do.assert_called_once()

    def test_mineral_to_gas_locked_under_gas_overflow(self):
        """Mineral starvation prevents any mineral-to-gas rebalance."""
        self.bot.workers = UnitList()
        self.bot.structures = Mock()

        moved = asyncio.run(self.balancer._move_workers_to_gas())

        self.assertEqual(moved, 0)
        self.bot.structures.assert_not_called()


if __name__ == "__main__":
    unittest.main()
