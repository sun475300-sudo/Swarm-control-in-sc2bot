# -*- coding: utf-8 -*-
"""DomainScore + ScoringSystem 단위 테스트.

도메인 점수 추가/등급 매핑, 이력 100개 유지, 도메인 초기화 정합성 확인.
"""

import os
import sys
import unittest

os.environ["PROTOCOL_BUFFERS_PYTHON_IMPLEMENTATION"] = "python"
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from scoring_system import DomainScore, ScoringSystem


class TestDomainScore(unittest.TestCase):
    def test_initial_zero_score(self):
        d = DomainScore("Combat")
        self.assertEqual(d.score, 0.0)
        self.assertEqual(d.total_events, 0)
        self.assertEqual(d.positive_events, 0)
        self.assertEqual(d.negative_events, 0)

    def test_add_positive(self):
        d = DomainScore("Combat")
        d.add(5.0, "win")
        self.assertEqual(d.score, 5.0)
        self.assertEqual(d.positive_events, 1)
        self.assertEqual(d.negative_events, 0)

    def test_add_negative(self):
        d = DomainScore("Combat")
        d.add(-3.0, "loss")
        self.assertEqual(d.score, -3.0)
        self.assertEqual(d.negative_events, 1)
        self.assertEqual(d.positive_events, 0)

    def test_history_capped_at_100(self):
        d = DomainScore("Combat")
        for i in range(120):
            d.add(1.0, f"e{i}")
        self.assertEqual(len(d.history), 100)
        # 마지막 100개만 유지: 가장 첫 항목은 e20
        self.assertEqual(d.history[0]["reason"], "e20")

    def test_grade_boundaries(self):
        d = DomainScore("X")
        for score, expected in [
            (90.0, "S"),
            (80.0, "S"),
            (79.9, "A"),
            (60.0, "A"),
            (40.0, "B"),
            (20.0, "C"),
            (0.0, "D"),
            (-1.0, "F"),
        ]:
            d.score = score
            self.assertEqual(d.grade, expected, f"score={score}")


class _StubBot:
    def __init__(self):
        self.time = 0.0


class TestScoringSystemInit(unittest.TestCase):
    def test_ten_domains(self):
        s = ScoringSystem(_StubBot())
        self.assertEqual(len(s.domains), 10)
        # 모든 도메인이 DomainScore 인스턴스
        for d in s.domains.values():
            self.assertIsInstance(d, DomainScore)

    def test_all_domains_start_at_zero(self):
        s = ScoringSystem(_StubBot())
        for name, d in s.domains.items():
            self.assertEqual(d.score, 0.0, f"{name} not zero")

    def test_domain_names_match(self):
        s = ScoringSystem(_StubBot())
        expected = {
            "combat",
            "production",
            "scouting",
            "economy",
            "defense",
            "strategy",
            "micro",
            "macro",
            "adaptation",
            "survival",
        }
        self.assertEqual(set(s.domains.keys()), expected)


class TestScoringHelperMethods(unittest.TestCase):
    def test_get_worst_domain(self):
        s = ScoringSystem(_StubBot())
        # 모든 도메인을 양수로 채운 뒤 economy만 -10 → economy가 최저
        for name in s.domains:
            s.domains[name].score = 50.0
        s.domains["economy"].score = -10.0
        self.assertEqual(s.get_worst_domain(), "economy")

    def test_get_summary_returns_string(self):
        s = ScoringSystem(_StubBot())
        s.domains["combat"].score = 30.0
        summary = s.get_summary()
        self.assertIsInstance(summary, str)
        self.assertGreater(len(summary), 0)


if __name__ == "__main__":
    unittest.main()
