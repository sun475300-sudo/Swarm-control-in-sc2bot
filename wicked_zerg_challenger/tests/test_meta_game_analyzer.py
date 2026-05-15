# -*- coding: utf-8 -*-
"""MetaGameAnalyzer 단위 테스트.

게임 기록(승/패 양쪽 카운팅), 전략 승률 계산, 메타 전략 정렬,
카운터 픽 매핑, 트렌드 분석 회귀 가드.
"""

import os
import sys
import unittest

os.environ["PROTOCOL_BUFFERS_PYTHON_IMPLEMENTATION"] = "python"
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from meta_game_analyzer import MetaGameAnalyzer, MetaStrategy, create_meta_analyzer


class TestRecordGame(unittest.TestCase):
    def test_records_win(self):
        a = MetaGameAnalyzer()
        a.record_game(
            {"strategy": "rush", "enemy_race": "terran", "map": "M1", "win": 1}
        )
        self.assertEqual(a.strategy_performance["rush"]["wins"], 1)
        self.assertEqual(a.strategy_performance["rush"]["losses"], 0)

    def test_records_loss(self):
        a = MetaGameAnalyzer()
        a.record_game(
            {"strategy": "rush", "enemy_race": "terran", "map": "M1", "win": 0}
        )
        self.assertEqual(a.strategy_performance["rush"]["wins"], 0)
        self.assertEqual(a.strategy_performance["rush"]["losses"], 1)

    def test_race_performance_records_losses_regression(self):
        """이전 버전 회귀: race_performance.losses가 갱신되지 않던 결함."""
        a = MetaGameAnalyzer()
        for _ in range(3):
            a.record_game({"enemy_race": "zerg", "win": 0})
        self.assertEqual(a.race_performance["zerg"]["losses"], 3)
        self.assertEqual(a.race_performance["zerg"]["wins"], 0)

    def test_map_performance_records_losses_regression(self):
        """이전 버전 회귀: map_performance.losses가 갱신되지 않던 결함."""
        a = MetaGameAnalyzer()
        a.record_game({"map": "AbyssalReef", "win": 0})
        a.record_game({"map": "AbyssalReef", "win": 1})
        self.assertEqual(a.map_performance["AbyssalReef"]["wins"], 1)
        self.assertEqual(a.map_performance["AbyssalReef"]["losses"], 1)

    def test_falsy_win_treated_as_loss(self):
        a = MetaGameAnalyzer()
        a.record_game({"strategy": "macro"})  # 'win' 누락 → 패배 취급
        self.assertEqual(a.strategy_performance["macro"]["losses"], 1)


class TestWinRateCalculation(unittest.TestCase):
    def test_unknown_strategy_returns_50(self):
        a = MetaGameAnalyzer()
        self.assertEqual(a._calculate_win_rate("nonexistent"), 50.0)

    def test_three_wins_one_loss(self):
        a = MetaGameAnalyzer()
        for _ in range(3):
            a.record_game({"strategy": "macro", "win": 1})
        a.record_game({"strategy": "macro", "win": 0})
        self.assertAlmostEqual(a._calculate_win_rate("macro"), 75.0)


class TestMetaStrategies(unittest.TestCase):
    def test_returns_five_strategies(self):
        a = MetaGameAnalyzer()
        strategies = a.get_current_meta_strategies()
        self.assertEqual(len(strategies), 5)
        for s in strategies:
            self.assertIsInstance(s, MetaStrategy)

    def test_sorted_by_win_rate_desc(self):
        a = MetaGameAnalyzer()
        for _ in range(10):
            a.record_game({"strategy": "macro", "win": 1})  # 100% macro
        for _ in range(10):
            a.record_game({"strategy": "rush", "win": 0})  # 0% rush
        strategies = a.get_current_meta_strategies()
        for prev, cur in zip(strategies, strategies[1:]):
            self.assertGreaterEqual(prev.win_rate, cur.win_rate)


class TestRecommendStrategy(unittest.TestCase):
    def test_terran_small_map_recommends_rush(self):
        a = MetaGameAnalyzer()
        rec = a.recommend_strategy("terran", "GroundZero")
        self.assertEqual(rec["recommended_strategy"], "RUSH")

    def test_zerg_large_recommends_tech(self):
        a = MetaGameAnalyzer()
        rec = a.recommend_strategy("zerg", "AbyssalReef")
        self.assertEqual(rec["recommended_strategy"], "TECH")

    def test_recommendation_contains_meta_analysis(self):
        a = MetaGameAnalyzer()
        rec = a.recommend_strategy("terran", "Corridor")
        self.assertIn("meta_analysis", rec)
        self.assertLessEqual(len(rec["meta_analysis"]), 3)


class TestCounterPicks(unittest.TestCase):
    def setUp(self):
        self.a = MetaGameAnalyzer()

    def test_rush_counters(self):
        self.assertIn("DEFENSIVE", self.a.get_counter_picks("rush"))

    def test_unknown_falls_back_to_macro(self):
        self.assertEqual(self.a.get_counter_picks("???"), ["MACRO"])


class TestTrends(unittest.TestCase):
    def test_no_data(self):
        a = MetaGameAnalyzer()
        self.assertEqual(a.analyze_trends()["trend"], "NO_DATA")

    def test_improving_trend(self):
        a = MetaGameAnalyzer()
        for _ in range(20):
            a.record_game({"win": 1})
        trend = a.analyze_trends()
        self.assertEqual(trend["trend"], "IMPROVING")
        self.assertEqual(trend["games_analyzed"], 20)

    def test_declining_trend(self):
        a = MetaGameAnalyzer()
        for _ in range(15):
            a.record_game({"win": 0})
        self.assertEqual(a.analyze_trends()["trend"], "DECLINING")


class TestFactory(unittest.TestCase):
    def test_create_meta_analyzer(self):
        self.assertIsInstance(create_meta_analyzer(), MetaGameAnalyzer)


if __name__ == "__main__":
    unittest.main()
