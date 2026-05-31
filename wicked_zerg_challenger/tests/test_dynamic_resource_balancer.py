# -*- coding: utf-8 -*-
"""Regression tests for DynamicResourceBalancer.

These tests guard the fixes from commit "rescue assignments swallowed by
Korean comments + logic gaps" — specifically that the threshold attributes
are actually initialized and that the CRITICAL state path can fire.
"""

import os

os.environ["PROTOCOL_BUFFERS_PYTHON_IMPLEMENTATION"] = "python"

import sys
import unittest
from unittest.mock import Mock

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from dynamic_resource_balancer import DynamicResourceBalancer


def _make_bot(minerals=0, vespene=0, time=0.0):
    bot = Mock()
    bot.minerals = minerals
    bot.vespene = vespene
    bot.time = time
    return bot


class TestThresholdAttributes(unittest.TestCase):
    """The CRITICAL branch references self.high_mineral_threshold; if the
    attribute were swallowed by the surrounding comment line the balancer
    would AttributeError the moment a game reached this state."""

    def setUp(self):
        self.balancer = DynamicResourceBalancer(_make_bot())

    def test_high_mineral_threshold_defined(self):
        self.assertEqual(self.balancer.high_mineral_threshold, 1500)

    def test_gas_shortage_threshold_defined(self):
        self.assertEqual(self.balancer.gas_shortage_threshold, 100)

    def test_mineral_excess_threshold_defined(self):
        self.assertEqual(self.balancer.mineral_excess_threshold, 1000)


class TestResourceStateTransitions(unittest.TestCase):
    def setUp(self):
        self.bot = _make_bot()
        self.balancer = DynamicResourceBalancer(self.bot)

    def _state_for(self, minerals, vespene, time=200.0):
        self.bot.minerals = minerals
        self.bot.vespene = vespene
        self.bot.time = time
        state, _ = self.balancer._analyze_resource_imbalance(minerals, vespene, time)
        return state

    def test_early_game_is_balanced(self):
        self.assertEqual(self._state_for(2000, 50, time=120.0), "BALANCED")

    def test_critical_when_minerals_high_and_gas_low(self):
        # minerals >= 1500 and gas < 100 → CRITICAL
        self.assertEqual(self._state_for(1500, 50), "CRITICAL")

    def test_critical_target_ratio_increases_gas_share(self):
        starting_ratio = self.balancer.current_gas_ratio
        _, target = self.balancer._analyze_resource_imbalance(1500, 50, 200.0)
        self.assertGreater(target, starting_ratio)


class TestCriticalCompositionReturn(unittest.TestCase):
    """The CRITICAL branch in get_unit_composition_ratios previously had
    a duplicated `return {` wedged inside a garbled comment. Make sure the
    actual return delivers a non-empty mapping for that state."""

    def setUp(self):
        self.balancer = DynamicResourceBalancer(_make_bot())
        self.balancer.resource_state = "CRITICAL"
        self.balancer.current_gas_ratio = 0.55

    def test_critical_returns_unit_mix(self):
        ratios = self.balancer.get_unit_ratio_adjustments()
        self.assertIn("hydralisk", ratios)
        self.assertIn("zergling", ratios)
        self.assertGreater(sum(ratios.values()), 0)


if __name__ == "__main__":
    unittest.main()
