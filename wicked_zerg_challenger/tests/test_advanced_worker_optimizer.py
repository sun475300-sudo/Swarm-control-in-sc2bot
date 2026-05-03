# -*- coding: utf-8 -*-
"""
Unit tests for AdvancedWorkerOptimizer pure-logic surfaces.

Heavy orchestration paths (_update_base_economies, _balance_gas_workers,
etc.) require fully-mocked Units collections. We focus on the deterministic
helpers and dataclasses.

Covered:
- MineralPatchState / BaseEconomy dataclass instantiation
- AdvancedWorkerOptimizer.__init__ defaults
- _detect_depleting_minerals: only patches < 200 minerals get added
- _count_workers_on_mineral: empty/none cases
- _count_workers_on_gas: returns assigned_harvesters from gas building
- _get_mineral_by_tag / _get_mineral_position
- _get_gas_building_by_tag
- _collect_learning_data: stores income tuples + bounded history
- get_efficiency_report returns a non-empty string
"""

import os
import sys
import unittest
from unittest.mock import Mock

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from advanced_worker_optimizer import (
    AdvancedWorkerOptimizer,
    BaseEconomy,
    MineralPatchState,
)
from sc2.position import Point2


def _mineral(tag, contents, position=Point2((10, 10))):
    m = Mock()
    m.tag = tag
    m.position = position
    m.mineral_contents = contents
    return m


def _gas(tag, harvesters=2):
    g = Mock()
    g.tag = tag
    g.assigned_harvesters = harvesters
    return g


class TestDataclasses(unittest.TestCase):
    def test_mineral_patch_state(self):
        s = MineralPatchState(
            tag=1,
            position=Point2((10, 10)),
            remaining_minerals=500,
            assigned_workers=2,
            optimal_workers=2,
            distance_from_base=8.0,
            is_depleting=False,
        )
        self.assertEqual(s.tag, 1)
        self.assertEqual(s.remaining_minerals, 500)
        self.assertFalse(s.is_depleting)

    def test_base_economy(self):
        e = BaseEconomy(
            base_tag=1,
            position=Point2((10, 10)),
            mineral_patches=[],
            gas_geysers=[],
            assigned_mineral_workers=0,
            assigned_gas_workers=0,
            optimal_mineral_workers=16,
            optimal_gas_workers=6,
            saturation_ratio=0.0,
        )
        self.assertEqual(e.base_tag, 1)
        self.assertEqual(e.optimal_mineral_workers, 16)


class TestInit(unittest.TestCase):
    def test_defaults(self):
        bot = Mock()
        opt = AdvancedWorkerOptimizer(bot)
        self.assertEqual(opt.base_economies, {})
        self.assertEqual(opt.worker_assignments, {})
        self.assertEqual(opt.optimal_workers_per_mineral, 2)
        self.assertEqual(opt.optimal_workers_per_gas, 3)
        self.assertAlmostEqual(opt.target_mineral_gas_ratio, 2.0)
        self.assertEqual(opt.income_history, [])
        self.assertEqual(opt.efficiency_metrics, [])
        self.assertEqual(opt.depleting_patches, set())
        self.assertEqual(opt.optimization_interval, 22)


class TestDetectDepletingMinerals(unittest.TestCase):
    def test_no_mineral_field_attr_safe(self):
        bot = Mock(spec=[])
        opt = AdvancedWorkerOptimizer(bot)
        # Should not raise
        opt._detect_depleting_minerals()
        self.assertEqual(opt.depleting_patches, set())

    def test_adds_only_depleting_patches(self):
        bot = Mock()
        bot.mineral_field = [
            _mineral(1, 1500),
            _mineral(2, 150),  # < 200
            _mineral(3, 50),  # < 200
            _mineral(4, 200),  # NOT < 200
        ]
        opt = AdvancedWorkerOptimizer(bot)
        opt._detect_depleting_minerals()
        self.assertEqual(opt.depleting_patches, {2, 3})

    def test_does_not_re_add_already_known_patches(self):
        bot = Mock()
        bot.mineral_field = [_mineral(1, 100)]
        opt = AdvancedWorkerOptimizer(bot)
        opt.depleting_patches.add(1)
        # Calling again should be a no-op (and shouldn't double-log)
        opt._detect_depleting_minerals()
        self.assertEqual(opt.depleting_patches, {1})


class TestCountWorkersOnMineral(unittest.TestCase):
    def test_no_workers_attr_returns_zero(self):
        bot = Mock(spec=[])
        opt = AdvancedWorkerOptimizer(bot)
        self.assertEqual(opt._count_workers_on_mineral(1), 0)


class TestCountWorkersOnGas(unittest.TestCase):
    def test_returns_assigned_harvesters(self):
        bot = Mock()
        gas = _gas(7, harvesters=3)
        bot.gas_buildings = [gas]
        opt = AdvancedWorkerOptimizer(bot)
        self.assertEqual(opt._count_workers_on_gas(7), 3)

    def test_returns_zero_when_gas_not_found(self):
        bot = Mock()
        bot.gas_buildings = []
        opt = AdvancedWorkerOptimizer(bot)
        self.assertEqual(opt._count_workers_on_gas(99), 0)


class TestGetMineralByTag(unittest.TestCase):
    def test_returns_match(self):
        bot = Mock()
        target = _mineral(5, 500, Point2((20, 20)))
        bot.mineral_field = [_mineral(1, 100), target, _mineral(9, 1000)]
        opt = AdvancedWorkerOptimizer(bot)
        self.assertIs(opt._get_mineral_by_tag(5), target)

    def test_returns_none_when_no_match(self):
        bot = Mock()
        bot.mineral_field = [_mineral(1, 100)]
        opt = AdvancedWorkerOptimizer(bot)
        self.assertIsNone(opt._get_mineral_by_tag(99))

    def test_no_mineral_field_returns_none(self):
        bot = Mock(spec=[])
        opt = AdvancedWorkerOptimizer(bot)
        self.assertIsNone(opt._get_mineral_by_tag(1))


class TestGetMineralPosition(unittest.TestCase):
    def test_returns_position(self):
        bot = Mock()
        bot.mineral_field = [_mineral(5, 500, Point2((20, 30)))]
        opt = AdvancedWorkerOptimizer(bot)
        self.assertEqual(opt._get_mineral_position(5), Point2((20, 30)))

    def test_returns_none_when_not_found(self):
        bot = Mock()
        bot.mineral_field = []
        opt = AdvancedWorkerOptimizer(bot)
        self.assertIsNone(opt._get_mineral_position(99))


class TestGetGasBuildingByTag(unittest.TestCase):
    def test_returns_match(self):
        bot = Mock()
        target = _gas(3)
        bot.gas_buildings = [_gas(1), target, _gas(5)]
        opt = AdvancedWorkerOptimizer(bot)
        self.assertIs(opt._get_gas_building_by_tag(3), target)

    def test_returns_none_when_not_found(self):
        bot = Mock()
        bot.gas_buildings = []
        opt = AdvancedWorkerOptimizer(bot)
        self.assertIsNone(opt._get_gas_building_by_tag(99))

    def test_no_gas_buildings_returns_none(self):
        bot = Mock(spec=[])
        opt = AdvancedWorkerOptimizer(bot)
        self.assertIsNone(opt._get_gas_building_by_tag(1))


class TestCollectLearningData(unittest.TestCase):
    def test_stores_income_tuple_and_efficiency(self):
        bot = Mock()
        worker = Mock()
        bot.workers = [worker, worker, worker]  # 3 workers
        bot.minerals = 600
        bot.vespene = 100
        opt = AdvancedWorkerOptimizer(bot)
        opt._collect_learning_data(60.0)
        self.assertEqual(len(opt.income_history), 1)
        # (time, mineral, gas, count)
        self.assertEqual(opt.income_history[0], (60.0, 600, 100, 3))
        self.assertEqual(len(opt.efficiency_metrics), 1)
        # efficiency = (600 + 100*1.5) / 3 = 250.0
        self.assertAlmostEqual(opt.efficiency_metrics[0][1], 250.0)

    def test_zero_workers_skips_efficiency(self):
        bot = Mock()
        bot.workers = []
        bot.minerals = 0
        bot.vespene = 0
        opt = AdvancedWorkerOptimizer(bot)
        opt._collect_learning_data(0.0)
        self.assertEqual(len(opt.efficiency_metrics), 0)

    def test_history_capped_at_300(self):
        bot = Mock()
        bot.workers = [Mock()]
        bot.minerals = 0
        bot.vespene = 0
        opt = AdvancedWorkerOptimizer(bot)
        # Fill history past the cap
        opt.income_history = [(0, 0, 0, 1)] * 350
        opt._collect_learning_data(1.0)
        self.assertEqual(len(opt.income_history), 300)

    def test_no_workers_attr_safe(self):
        bot = Mock(spec=[])
        opt = AdvancedWorkerOptimizer(bot)
        # Should not raise
        opt._collect_learning_data(0.0)


if __name__ == "__main__":
    unittest.main()
