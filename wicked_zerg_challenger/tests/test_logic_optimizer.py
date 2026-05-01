# -*- coding: utf-8 -*-
"""
Unit tests for LogicOptimizer.apply_economy_improvements

These tests guard against silent drift between
EconomyManager.macro_hatchery_mineral_threshold (Phase 16 baseline = 550)
and the optimizer's "more aggressive" override that previously hard-coded 500.
"""

import os
import sys
import unittest
from unittest.mock import Mock

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from logic_optimizer import LogicOptimizer


class TestApplyEconomyImprovements(unittest.TestCase):
    def _make_bot(self, baseline_threshold):
        bot = Mock()
        bot.economy_manager = Mock()
        bot.economy_manager.macro_hatchery_mineral_threshold = baseline_threshold
        return bot

    def test_makes_threshold_more_aggressive_relative_to_baseline(self):
        """Optimizer should drop the threshold by 50 below current baseline."""
        bot = self._make_bot(550)
        opt = LogicOptimizer(bot)
        opt.apply_economy_improvements()
        self.assertEqual(bot.economy_manager.macro_hatchery_mineral_threshold, 500)

    def test_keeps_floor_when_baseline_is_low(self):
        """Optimizer should not push threshold below the 400 floor."""
        bot = self._make_bot(420)
        opt = LogicOptimizer(bot)
        opt.apply_economy_improvements()
        self.assertEqual(bot.economy_manager.macro_hatchery_mineral_threshold, 400)

    def test_handles_legacy_baseline(self):
        """If running against the historical 600 baseline, optimizer drops to 550."""
        bot = self._make_bot(600)
        opt = LogicOptimizer(bot)
        opt.apply_economy_improvements()
        self.assertEqual(bot.economy_manager.macro_hatchery_mineral_threshold, 550)

    def test_sets_gas_worker_adjustment_interval(self):
        bot = self._make_bot(550)
        opt = LogicOptimizer(bot)
        opt.apply_economy_improvements()
        self.assertEqual(bot.economy_manager.gas_worker_adjustment_interval, 22)

    def test_no_op_when_no_economy_manager(self):
        """Should silently no-op if the bot has no economy_manager."""
        bot = Mock(spec=[])  # no attributes
        opt = LogicOptimizer(bot)
        opt.apply_economy_improvements()  # must not raise


if __name__ == "__main__":
    unittest.main()
