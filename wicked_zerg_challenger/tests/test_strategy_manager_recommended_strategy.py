# -*- coding: utf-8 -*-
"""
Regression test for the OpponentModeling -> StrategyManager dead-end found
during the 2026-07 audit:

`OpponentModeling._send_prediction_to_strategy_manager` published a counter
composition to `blackboard.set("recommended_strategy", [...])`, but nothing
in the codebase ever read that key back - `StrategyManager.get_unit_ratios()`
now consumes it and biases the returned ratios towards the recommended
counter units.
"""

import os
import sys
import unittest

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from strategy_manager import StrategyManager


class Blackboard:
    def __init__(self, values=None):
        self.values = dict(values or {})

    def get(self, key, default=None):
        return self.values.get(key, default)

    def set(self, key, value):
        self.values[key] = value


class FakeBot:
    def __init__(self, blackboard=None):
        self.time = 0.0
        self.enemy_race = "Race.Terran"
        self.enemy_units = []
        self.enemy_structures = []
        self.blackboard = blackboard or Blackboard()


class TestRecommendedStrategyConsumption(unittest.TestCase):
    def test_no_recommendation_leaves_ratios_unchanged(self):
        blackboard = Blackboard()
        bot = FakeBot(blackboard)
        manager = StrategyManager(bot, blackboard)

        baseline = manager.get_unit_ratios()
        # Publishing nothing should be a pure no-op.
        self.assertEqual(manager.get_unit_ratios(), baseline)

    def test_recommended_units_are_boosted_and_normalized(self):
        blackboard = Blackboard()
        bot = FakeBot(blackboard)
        manager = StrategyManager(bot, blackboard)

        baseline = manager.get_unit_ratios()
        self.assertIn("roach", baseline)
        self.assertGreater(baseline["roach"], 0)

        # Simulate what OpponentModeling._send_prediction_to_strategy_manager
        # publishes after predicting a Terran mech push (roach is in the
        # default ratio table and gets boosted; the others are not part of
        # the table and must simply be ignored, not raise a KeyError).
        blackboard.set("recommended_strategy", ["roach", "corruptor", "viper"])

        boosted = manager.get_unit_ratios()

        # Ratios must still sum to 1 (renormalized).
        self.assertAlmostEqual(sum(boosted.values()), 1.0, places=6)

        # Pre-fix, get_unit_ratios() never reads the blackboard at all, so
        # this is the assertion that actually distinguishes fixed vs buggy.
        self.assertGreater(boosted["roach"], baseline["roach"])

    def test_custom_unit_weights_still_take_priority(self):
        # Feature 89 (JARVIS custom_unit_weights) must keep overriding
        # everything else - it returns early, so a blackboard recommendation
        # must have zero effect once custom weights are set.
        blackboard = Blackboard()
        bot = FakeBot(blackboard)
        manager = StrategyManager(bot, blackboard)
        manager.custom_unit_weights = {"zergling": 1.0}

        without_recommendation = manager.get_unit_ratios()

        blackboard.set("recommended_strategy", ["roach"])
        with_recommendation = manager.get_unit_ratios()

        self.assertEqual(with_recommendation, without_recommendation)


if __name__ == "__main__":
    unittest.main()
