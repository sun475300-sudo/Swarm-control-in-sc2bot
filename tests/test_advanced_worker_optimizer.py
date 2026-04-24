# -*- coding: utf-8 -*-
"""
Unit tests for wicked_zerg_challenger/advanced_worker_optimizer.py
(570 LOC, previously untested).

Exercises initialization, defaults, depletion detection, learning-data
collection, gas/mineral worker counting, and efficiency-report formatting
without a running SC2 client.
"""
import os
import sys
from unittest.mock import MagicMock

import pytest

sys.path.insert(
    0, os.path.join(os.path.dirname(__file__), "..", "wicked_zerg_challenger")
)


def _import():
    try:
        from advanced_worker_optimizer import AdvancedWorkerOptimizer, BaseEconomy
        return AdvancedWorkerOptimizer, BaseEconomy
    except ImportError:
        return None, None


AdvancedWorkerOptimizer, BaseEconomy = _import()

pytestmark = pytest.mark.skipif(
    AdvancedWorkerOptimizer is None,
    reason="advanced_worker_optimizer not importable",
)


@pytest.fixture
def bot():
    b = MagicMock()
    b.time = 0.0
    b.minerals = 0
    b.vespene = 0
    b.workers = []
    b.mineral_field = []
    b.gas_buildings = []
    return b


@pytest.fixture
def optimizer(bot):
    return AdvancedWorkerOptimizer(bot)


class TestInit:
    def test_defaults(self, optimizer):
        assert optimizer.optimal_workers_per_mineral == 2
        assert optimizer.optimal_workers_per_gas == 3
        assert optimizer.target_mineral_gas_ratio == pytest.approx(2.0)
        assert optimizer.total_worker_moves == 0
        assert optimizer.unnecessary_moves == 0
        assert optimizer.base_economies == {}
        assert optimizer.depleting_patches == set()

    def test_optimization_interval_sensible(self, optimizer):
        # 22 frames ≈ 1 real-time second at SC2 normal speed.
        assert optimizer.optimization_interval > 0


class TestDetectDepletingMinerals:
    def _mf(self, tag, contents):
        m = MagicMock()
        m.tag = tag
        m.mineral_contents = contents
        return m

    def test_none_depleting(self, bot, optimizer):
        bot.mineral_field = [self._mf(1, 1500), self._mf(2, 1200)]
        optimizer._detect_depleting_minerals()
        assert optimizer.depleting_patches == set()

    def test_one_depleting(self, bot, optimizer):
        bot.mineral_field = [self._mf(1, 150), self._mf(2, 1200)]
        optimizer._detect_depleting_minerals()
        assert optimizer.depleting_patches == {1}

    def test_repeat_does_not_double_count(self, bot, optimizer):
        bot.mineral_field = [self._mf(5, 100)]
        optimizer._detect_depleting_minerals()
        optimizer._detect_depleting_minerals()  # second tick
        assert optimizer.depleting_patches == {5}

    def test_no_mineral_field_attribute_is_safe(self, bot, optimizer):
        del bot.mineral_field
        optimizer._detect_depleting_minerals()  # must not raise
        assert optimizer.depleting_patches == set()


class TestCountWorkersOnGas:
    def test_returns_assigned_harvesters(self, bot, optimizer):
        gas = MagicMock()
        gas.tag = 42
        gas.assigned_harvesters = 3
        bot.gas_buildings = [gas]
        assert optimizer._count_workers_on_gas(42) == 3

    def test_missing_gas_returns_zero(self, bot, optimizer):
        bot.gas_buildings = []
        assert optimizer._count_workers_on_gas(99) == 0


class TestCollectLearningData:
    def test_no_workers_attr_is_safe(self, bot, optimizer):
        del bot.workers
        optimizer._collect_learning_data(60.0)
        assert optimizer.income_history == []

    def test_appends_and_computes_efficiency(self, bot, optimizer):
        bot.workers = [MagicMock() for _ in range(10)]
        bot.minerals = 500
        bot.vespene = 100
        optimizer._collect_learning_data(60.0)
        assert len(optimizer.income_history) == 1
        assert optimizer.income_history[0] == (60.0, 500, 100, 10)
        assert len(optimizer.efficiency_metrics) == 1
        # efficiency = (500 + 100*1.5) / 10 = 65
        assert optimizer.efficiency_metrics[0][1] == pytest.approx(65.0)

    def test_history_trimmed_at_300(self, bot, optimizer):
        bot.workers = [MagicMock()]
        bot.minerals = 1
        bot.vespene = 0
        for i in range(350):
            optimizer._collect_learning_data(float(i))
        assert len(optimizer.income_history) == 300
        # Retains newest
        assert optimizer.income_history[-1][0] == 349.0


class TestGetMineralByTag:
    def test_lookup(self, bot, optimizer):
        m1 = MagicMock()
        m1.tag = 1
        m2 = MagicMock()
        m2.tag = 2
        bot.mineral_field = [m1, m2]
        assert optimizer._get_mineral_by_tag(2) is m2

    def test_missing(self, bot, optimizer):
        bot.mineral_field = []
        assert optimizer._get_mineral_by_tag(7) is None

    def test_no_mineral_field_attr(self, bot, optimizer):
        del bot.mineral_field
        assert optimizer._get_mineral_by_tag(1) is None


class TestEfficiencyReport:
    def test_empty_report_mentions_zero_bases(self, optimizer):
        report = optimizer.get_efficiency_report()
        assert "WORKER OPTIMIZER" in report
        assert "Active Bases: 0" in report
