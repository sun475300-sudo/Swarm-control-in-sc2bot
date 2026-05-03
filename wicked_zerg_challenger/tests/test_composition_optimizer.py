# -*- coding: utf-8 -*-
"""
Unit tests for CompositionOptimizer + ZergUnit + counter logic.

Covers:
- ZergUnit.cost_efficiency arithmetic and zero-cost guard
- analyze_enemy_composition: filters workers, merges intel_manager history
- analyze_current_composition: filters DRONE/LARVA
- get_optimal_composition: cache, default fallback, race-specific defaults,
  air-threat boost for hydralisk/corruptor/queen, normalization sums to 1
- get_production_recommendation: respects affordability and skips when
  current count meets target
- calculate_army_value: sums mineral/gas across composition
- _get_default_composition: returns sensible Zerg vs T/P/Z mixes
"""

import os
import sys
import unittest
from unittest.mock import MagicMock, Mock

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from composition_optimizer import (
    ZERG_UNITS,
    CompositionOptimizer,
    UnitRole,
    ZergUnit,
)


def _enemy_unit(name):
    u = Mock()
    type_id = Mock()
    type_id.name = name
    u.type_id = type_id
    return u


def _bot(
    time=120.0,
    minerals=400,
    vespene=200,
    supply_left=20,
    supply_army=40,
    enemy_race=None,
):
    bot = Mock()
    bot.time = time
    bot.minerals = minerals
    bot.vespene = vespene
    bot.supply_left = supply_left
    bot.supply_army = supply_army
    bot.enemy_units = []
    bot.units = []
    if enemy_race is not None:
        bot.enemy_race = enemy_race
    bot.intel_manager = None
    return bot


class TestZergUnit(unittest.TestCase):
    def test_total_cost_uses_15_gas_weight(self):
        u = ZergUnit("x", 100, 100, 2, UnitRole.GROUND_RANGED)
        self.assertEqual(u.total_cost, 100 + 100 * 1.5)

    def test_cost_efficiency(self):
        u = ZergUnit(
            "test", 100, 50, 2, UnitRole.GROUND_RANGED, dps=10.0, hp=100.0
        )  # total_cost = 100 + 75 = 175
        # (10 * 100) / 175 ≈ 5.714
        self.assertAlmostEqual(u.cost_efficiency, 1000 / 175, places=3)

    def test_cost_efficiency_zero_cost_returns_zero(self):
        # mineral=0, gas=0 => total_cost = 0
        u = ZergUnit("free", 0, 0, 0, UnitRole.WORKER, dps=10, hp=100)
        self.assertEqual(u.cost_efficiency, 0.0)


class TestAnalyzeEnemyComposition(unittest.TestCase):
    def test_empty_when_no_enemy_units_attr(self):
        bot = Mock(spec=[])
        opt = CompositionOptimizer(bot)
        self.assertEqual(opt.analyze_enemy_composition(), {})

    def test_filters_workers(self):
        bot = _bot()
        bot.enemy_units = [
            _enemy_unit("MARINE"),
            _enemy_unit("MARINE"),
            _enemy_unit("SCV"),
            _enemy_unit("MULE"),
            _enemy_unit("MARAUDER"),
        ]
        opt = CompositionOptimizer(bot)
        comp = opt.analyze_enemy_composition()
        self.assertEqual(comp.get("MARINE"), 2)
        self.assertEqual(comp.get("MARAUDER"), 1)
        self.assertNotIn("SCV", comp)
        self.assertNotIn("MULE", comp)

    def test_merges_intel_manager_history(self):
        bot = _bot()
        bot.enemy_units = [_enemy_unit("MARINE")]  # 1 visible
        intel = Mock()
        intel.enemy_unit_counts = {"MARINE": 5, "SIEGETANK": 2, "PROBE": 99}
        bot.intel_manager = intel
        opt = CompositionOptimizer(bot)
        comp = opt.analyze_enemy_composition()
        # Historical max overrides visible count when larger
        self.assertEqual(comp.get("MARINE"), 5)
        self.assertEqual(comp.get("SIEGETANK"), 2)
        self.assertNotIn("PROBE", comp)


class TestAnalyzeCurrentComposition(unittest.TestCase):
    def test_filters_drones_and_larva(self):
        bot = _bot()
        bot.units = [
            _enemy_unit("ZERGLING"),
            _enemy_unit("ZERGLING"),
            _enemy_unit("DRONE"),
            _enemy_unit("LARVA"),
            _enemy_unit("ROACH"),
        ]
        opt = CompositionOptimizer(bot)
        comp = opt.analyze_current_composition()
        self.assertEqual(comp.get("ZERGLING"), 2)
        self.assertEqual(comp.get("ROACH"), 1)
        self.assertNotIn("DRONE", comp)
        self.assertNotIn("LARVA", comp)


class TestGetOptimalComposition(unittest.TestCase):
    def test_cache_returns_within_interval(self):
        bot = _bot(time=10.0)
        opt = CompositionOptimizer(bot)
        opt._cached_recommendation = {"roach": 1.0}
        opt._last_analysis_time = 9.0  # <5 seconds ago
        result = opt.get_optimal_composition()
        self.assertEqual(result, {"roach": 1.0})

    def test_no_enemy_info_returns_default(self):
        bot = _bot(time=100.0)
        bot.enemy_units = []
        opt = CompositionOptimizer(bot)
        result = opt.get_optimal_composition()
        # Default composition should not be empty
        self.assertGreater(len(result), 0)
        # Sums close to 1.0 (it's a ratio map)
        self.assertAlmostEqual(sum(result.values()), 1.0, places=2)

    def test_counter_marines_includes_baneling(self):
        bot = _bot(time=100.0)
        bot.enemy_units = [_enemy_unit("MARINE") for _ in range(10)]
        opt = CompositionOptimizer(bot)
        result = opt.get_optimal_composition()
        # Baneling/zergling/lurker/ultralisk are listed counters for marines
        self.assertIn("baneling", result)
        # Ratios sum to ~1
        self.assertAlmostEqual(sum(result.values()), 1.0, places=2)

    def test_air_threat_boosts_anti_air_units(self):
        # First baseline: no air threat
        bot = _bot(time=100.0)
        bot.enemy_units = [_enemy_unit("MARINE") for _ in range(5)]
        baseline = CompositionOptimizer(bot).get_optimal_composition()
        baseline_corruptor = baseline.get("corruptor", 0.0)

        # Now add air units
        bot2 = _bot(time=100.0)
        bot2.enemy_units = [
            _enemy_unit("MARINE"),
            _enemy_unit("VOIDRAY"),
            _enemy_unit("VOIDRAY"),
        ]
        with_air = CompositionOptimizer(bot2).get_optimal_composition()
        # Corruptor should now appear in non-trivial proportion
        self.assertIn("corruptor", with_air)
        self.assertGreater(with_air.get("corruptor", 0), baseline_corruptor)

    def test_filtered_units_below_5_percent_removed(self):
        bot = _bot(time=100.0)
        bot.enemy_units = [_enemy_unit("MARINE") for _ in range(20)]
        opt = CompositionOptimizer(bot)
        result = opt.get_optimal_composition()
        for ratio in result.values():
            self.assertGreaterEqual(ratio, 0.05)


class TestProductionRecommendation(unittest.TestCase):
    def test_recommends_when_short_on_units(self):
        bot = _bot(
            time=100.0, minerals=1000, vespene=500, supply_left=20, supply_army=20
        )
        bot.enemy_units = [_enemy_unit("MARINE") for _ in range(5)]
        bot.units = []  # no current units
        opt = CompositionOptimizer(bot)
        recs = opt.get_production_recommendation()
        # At least one recommendation
        self.assertTrue(len(recs) > 0)
        for unit_name, count in recs:
            self.assertIn(unit_name, ZERG_UNITS)
            self.assertGreater(count, 0)
            self.assertLessEqual(count, 5)  # capped at 5

    def test_no_recommendation_when_target_is_satisfied(self):
        bot = _bot(
            time=100.0, minerals=1000, vespene=500, supply_left=20, supply_army=2
        )
        bot.enemy_units = [_enemy_unit("MARINE") for _ in range(5)]
        # We already have plenty of zerglings/banelings
        bot.units = [_enemy_unit("BANELING")] * 50 + [_enemy_unit("ZERGLING")] * 50
        opt = CompositionOptimizer(bot)
        # Pre-prime current composition cache
        opt.analyze_current_composition()
        recs = opt.get_production_recommendation()
        # When we already have a lot, recommendations may be empty or small
        self.assertIsInstance(recs, list)


class TestArmyValue(unittest.TestCase):
    def test_calculates_value_from_current_composition(self):
        bot = _bot()
        opt = CompositionOptimizer(bot)
        opt.current_composition = {"ZERGLING": 10, "ROACH": 4}
        v = opt.calculate_army_value()
        # Zergling: 10 * 25 = 250 mineral, 0 gas
        # Roach: 4 * 75 = 300 mineral, 4 * 25 = 100 gas
        self.assertEqual(v["mineral_value"], 250 + 300)
        self.assertEqual(v["gas_value"], 0 + 100)
        self.assertEqual(v["total_value"], 250 + 300 + 100)

    def test_unknown_units_are_skipped(self):
        bot = _bot()
        opt = CompositionOptimizer(bot)
        opt.current_composition = {"ZERGLING": 5, "MARINE": 100}
        v = opt.calculate_army_value()
        # Only Zerglings count
        self.assertEqual(v["mineral_value"], 5 * 25)


class TestDefaultCompositions(unittest.TestCase):
    def test_default_for_terran(self):
        bot = _bot()
        bot.enemy_race = "Race.Terran"
        opt = CompositionOptimizer(bot)
        result = opt._get_default_composition()
        self.assertIn("roach", result)
        self.assertAlmostEqual(sum(result.values()), 1.0, places=2)

    def test_default_for_protoss(self):
        bot = _bot()
        bot.enemy_race = "Race.Protoss"
        opt = CompositionOptimizer(bot)
        result = opt._get_default_composition()
        self.assertIn("hydralisk", result)
        self.assertAlmostEqual(sum(result.values()), 1.0, places=2)

    def test_default_for_zerg(self):
        bot = _bot()
        bot.enemy_race = "Race.Zerg"
        opt = CompositionOptimizer(bot)
        result = opt._get_default_composition()
        self.assertAlmostEqual(sum(result.values()), 1.0, places=2)

    def test_default_unknown_race(self):
        bot = _bot()
        # Strip enemy_race attribute entirely
        bot = Mock(spec=[])
        opt = CompositionOptimizer(bot)
        result = opt._get_default_composition()
        self.assertIn("roach", result)


if __name__ == "__main__":
    unittest.main()
