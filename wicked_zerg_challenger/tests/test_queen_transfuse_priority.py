# -*- coding: utf-8 -*-
"""
Unit tests for QueenManager Transfusion priority helpers.

Verifies the extracted CreepyBot-inspired priority/scoring helpers so they
can't silently regress (used by `_transfuse_injured_units` to pick targets).
"""

import os
import sys
import unittest

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from queen_manager import QueenManager
from sc2.ids.unit_typeid import UnitTypeId


class TestTransfusePriorityMap(unittest.TestCase):
    def test_priority_map_resolves_known_units(self):
        m = QueenManager._build_transfuse_priority_map()
        self.assertEqual(m[UnitTypeId.QUEEN], 0)
        self.assertEqual(m[UnitTypeId.BROODLORD], 1)
        self.assertEqual(m[UnitTypeId.CORRUPTOR], 2)
        self.assertEqual(m[UnitTypeId.VIPER], 2)
        self.assertEqual(m[UnitTypeId.SPINECRAWLER], 3)
        self.assertEqual(m[UnitTypeId.OVERSEER], 4)
        self.assertEqual(m[UnitTypeId.ULTRALISK], 5)

    def test_priority_map_skips_unknown_names_silently(self):
        # Robust against UnitTypeId stub or renamed enum values.
        m = QueenManager._build_transfuse_priority_map()
        # Map must always contain at least the core priorities — sanity check.
        self.assertGreaterEqual(len(m), 5)


class TestUnhealableSet(unittest.TestCase):
    def test_unhealable_includes_baneling_broodling(self):
        s = QueenManager._build_unhealable_set()
        self.assertIn(UnitTypeId.BANELING, s)
        self.assertIn(UnitTypeId.BROODLING, s)


class TestIsInjuredForTransfuse(unittest.TestCase):
    def test_zero_health_max_is_not_injured(self):
        self.assertFalse(QueenManager._is_injured_for_transfuse(0, 0))
        self.assertFalse(QueenManager._is_injured_for_transfuse(50, 0))

    def test_full_hp_is_not_injured(self):
        self.assertFalse(QueenManager._is_injured_for_transfuse(200, 200))

    def test_deficit_threshold_triggers(self):
        # Deficit exactly at the threshold counts as injured.
        # 200 - 75 = 125 deficit.
        self.assertTrue(QueenManager._is_injured_for_transfuse(75, 200))
        # 200 - 76 = 124 deficit (and ratio 38% > 25%) — NOT injured.
        self.assertFalse(QueenManager._is_injured_for_transfuse(76, 200))

    def test_ratio_threshold_triggers(self):
        # 24% of 100 (= 24 HP) — injured by ratio rule even if deficit < 125.
        self.assertTrue(QueenManager._is_injured_for_transfuse(24, 100))
        # 25% exactly is NOT below 25 — not injured.
        self.assertFalse(QueenManager._is_injured_for_transfuse(25, 100))


class TestTransfuseScore(unittest.TestCase):
    def test_higher_priority_unit_scores_lower(self):
        priority_map = QueenManager._build_transfuse_priority_map()
        queen_score = QueenManager._transfuse_score(
            UnitTypeId.QUEEN, 1, 200, priority_map
        )
        zergling_score = QueenManager._transfuse_score(
            UnitTypeId.ZERGLING, 1, 200, priority_map
        )
        self.assertLess(queen_score, zergling_score)

    def test_more_wounded_same_class_wins_tiebreak(self):
        m = QueenManager._build_transfuse_priority_map()
        more_wounded = QueenManager._transfuse_score(UnitTypeId.ROACH, 10, 200, m)
        less_wounded = QueenManager._transfuse_score(UnitTypeId.ROACH, 100, 200, m)
        self.assertLess(more_wounded, less_wounded)

    def test_default_priority_for_unmapped_units(self):
        m = QueenManager._build_transfuse_priority_map()
        # ZERGLING isn't in the priority table → falls back to default (15).
        score = QueenManager._transfuse_score(UnitTypeId.ZERGLING, 100, 100, m)
        self.assertAlmostEqual(score, 15 + 0.5)  # ratio 1.0 → +0.5

    def test_zero_health_max_does_not_divide_by_zero(self):
        m = QueenManager._build_transfuse_priority_map()
        # Should not raise; should fall back to ratio 1.0 (i.e., not "extra urgent").
        score = QueenManager._transfuse_score(UnitTypeId.ROACH, 0, 0, m)
        # type prio = 7, ratio fallback = 1.0 → 7 + 0.5 = 7.5
        self.assertAlmostEqual(score, 7.5)


if __name__ == "__main__":
    unittest.main()
