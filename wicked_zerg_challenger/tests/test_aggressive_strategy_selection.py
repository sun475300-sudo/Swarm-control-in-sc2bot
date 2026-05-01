# -*- coding: utf-8 -*-
"""
Unit tests for AggressiveStrategyExecutor.select_strategy.

Locks in the race-specific dispatch table and the early-game guard so it
can't silently regress. Random branches are tested by patching random.random.
"""

import os
import sys
import unittest
from unittest.mock import Mock, patch

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from aggressive_strategies import AggressiveStrategyExecutor, AggressiveStrategyType


def _make_executor(time=60.0):
    bot = Mock()
    bot.time = time
    bot.blackboard = None
    bot.unit_authority = None
    return AggressiveStrategyExecutor(bot)


class TestEarlyGameGuard(unittest.TestCase):
    def test_under_30_seconds_returns_none(self):
        ex = _make_executor(time=10.0)
        result = ex.select_strategy("Terran")
        self.assertEqual(result, AggressiveStrategyType.NONE)
        # Importantly, decision must NOT be locked yet.
        self.assertFalse(ex._strategy_decided)

    def test_at_30_seconds_decision_can_be_made(self):
        ex = _make_executor(time=30.0)
        with patch("random.random", side_effect=[0.0]):
            # First roll < 0.5 -> NONE (Standard Macro)
            result = ex.select_strategy("Terran")
        self.assertEqual(result, AggressiveStrategyType.NONE)
        self.assertTrue(ex._strategy_decided)


class TestStandardMacroBranch(unittest.TestCase):
    def test_first_roll_below_half_picks_none(self):
        ex = _make_executor()
        with patch("random.random", side_effect=[0.49]):
            result = ex.select_strategy("Terran")
        self.assertEqual(result, AggressiveStrategyType.NONE)
        self.assertTrue(ex._strategy_decided)


class TestRaceDispatch(unittest.TestCase):
    def test_terran_baneling_path(self):
        ex = _make_executor()
        # 1st roll >= 0.5 (special tactics), 2nd roll < 0.5 (BANELING).
        with patch("random.random", side_effect=[0.6, 0.3]):
            result = ex.select_strategy("Terran")
        self.assertEqual(result, AggressiveStrategyType.BANELING_BUST)

    def test_terran_ravager_path(self):
        ex = _make_executor()
        with patch("random.random", side_effect=[0.6, 0.7]):
            result = ex.select_strategy("Terran")
        self.assertEqual(result, AggressiveStrategyType.RAVAGER_RUSH)

    def test_protoss_ravager_path(self):
        ex = _make_executor()
        with patch("random.random", side_effect=[0.6, 0.3]):
            result = ex.select_strategy("Protoss")
        self.assertEqual(result, AggressiveStrategyType.RAVAGER_RUSH)

    def test_protoss_nydus_path(self):
        ex = _make_executor()
        with patch("random.random", side_effect=[0.6, 0.5]):
            result = ex.select_strategy("Protoss")
        self.assertEqual(result, AggressiveStrategyType.NYDUS_ALLIN)

    def test_protoss_twelvepool_path(self):
        ex = _make_executor()
        with patch("random.random", side_effect=[0.6, 0.99]):
            result = ex.select_strategy("Protoss")
        self.assertEqual(result, AggressiveStrategyType.TWELVE_POOL)

    def test_zerg_twelvepool_path(self):
        ex = _make_executor()
        with patch("random.random", side_effect=[0.6, 0.0]):
            result = ex.select_strategy("Zerg")
        self.assertEqual(result, AggressiveStrategyType.TWELVE_POOL)

    def test_zerg_baneling_path(self):
        ex = _make_executor()
        with patch("random.random", side_effect=[0.6, 0.99]):
            result = ex.select_strategy("Zerg")
        self.assertEqual(result, AggressiveStrategyType.BANELING_BUST)

    def test_unknown_race_falls_back_to_twelvepool(self):
        ex = _make_executor()
        with patch("random.random", side_effect=[0.6]):
            result = ex.select_strategy("Random")
        self.assertEqual(result, AggressiveStrategyType.TWELVE_POOL)


class TestDecisionStickiness(unittest.TestCase):
    def test_already_decided_returns_active_strategy_unchanged(self):
        ex = _make_executor()
        ex._strategy_decided = True
        ex.active_strategy = AggressiveStrategyType.RAVAGER_RUSH
        result = ex.select_strategy("Terran")
        self.assertEqual(result, AggressiveStrategyType.RAVAGER_RUSH)

    def test_decision_time_recorded(self):
        ex = _make_executor(time=42.0)
        with patch("random.random", side_effect=[0.6, 0.3]):
            ex.select_strategy("Terran")
        self.assertEqual(ex._strategy_decision_time, 42.0)


if __name__ == "__main__":
    unittest.main()
