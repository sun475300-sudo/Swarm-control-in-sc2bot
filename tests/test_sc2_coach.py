# -*- coding: utf-8 -*-
"""Tests for sc2_coach.SC2Coach pattern detection and severity sorting."""

import os
import sys
import unittest

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from sc2_coach import SC2Coach


class TestSC2CoachPatterns(unittest.TestCase):
    def setUp(self):
        self.coach = SC2Coach()

    def _categories(self, advices):
        return {a["category"] for a in advices}

    def test_supply_block_detected(self):
        advices = self.coach.get_coaching_advice("[12:03] supply blocked at 36/36")
        self.assertIn("macro", self._categories(advices))

    def test_idle_workers_detected(self):
        advices = self.coach.get_coaching_advice("idle workers detected: 3")
        self.assertIn("economy", self._categories(advices))

    def test_no_detection_is_critical(self):
        advices = self.coach.get_coaching_advice("no detection vs cloaked banshee")
        critical = [a for a in advices if a["severity"] == "critical"]
        self.assertTrue(critical, "no_detection should produce critical advice")
        self.assertEqual(critical[0]["category"], "defense")

    def test_korean_pattern_matches(self):
        advices = self.coach.get_coaching_advice("인구 부족이 감지됨")
        self.assertIn("macro", self._categories(advices))

    def test_severity_sort_critical_first(self):
        log = "no detection vs banshee, idle workers detected: 5"
        advices = self.coach.get_coaching_advice(log)
        self.assertEqual(advices[0]["severity"], "critical")

    def test_empty_log_returns_info_advice(self):
        advices = self.coach.get_coaching_advice("")
        self.assertEqual(len(advices), 1)
        self.assertEqual(advices[0]["severity"], "info")

    def test_no_match_falls_back_to_info(self):
        advices = self.coach.get_coaching_advice("nothing notable here")
        self.assertEqual(len(advices), 1)
        self.assertEqual(advices[0]["severity"], "info")

    def test_short_game_timing_advice(self):
        advices = self.coach.get_coaching_advice("game time: 3:42")
        self.assertIn("timing", self._categories(advices))

    def test_high_unit_loss_advice(self):
        log = "lost: 30\nlost: 25"
        advices = self.coach.get_coaching_advice(log)
        self.assertIn("army", self._categories(advices))

    def test_format_advice_contains_severity_marker(self):
        advices = self.coach.get_coaching_advice("idle workers detected")
        formatted = self.coach.format_advice(advices)
        self.assertIn("SC2 코칭 리포트", formatted)
        self.assertIn("[!]", formatted)  # medium-severity icon

    def test_history_records_each_call(self):
        self.coach.get_coaching_advice("supply blocked")
        self.coach.get_coaching_advice("idle workers detected")
        self.assertEqual(len(self.coach.get_coaching_history()), 2)


if __name__ == "__main__":
    unittest.main(verbosity=2)
