# -*- coding: utf-8 -*-
"""SC2Coach 단위 테스트.

패턴 매칭 기반 조언 생성, 통계 분석, 심각도 정렬, 코칭 히스토리 등
sc2_coach.SC2Coach의 핵심 동작을 검증한다.
"""

import os
import sys
import unittest

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from sc2_coach import SC2Coach


class TestCoachPatternMatching(unittest.TestCase):
    def setUp(self):
        self.coach = SC2Coach()

    def _categories(self, advices):
        return {a["category"] for a in advices}

    def test_supply_block_detected(self):
        advices = self.coach.get_coaching_advice("[12:03] supply blocked at 36/36")
        self.assertIn("macro", self._categories(advices))

    def test_idle_workers_detected(self):
        advices = self.coach.get_coaching_advice("[10:00] idle workers detected: 5")
        self.assertIn("economy", self._categories(advices))

    def test_mineral_float_detected(self):
        advices = self.coach.get_coaching_advice("[15:00] mineral bank: 2500")
        self.assertIn("economy", self._categories(advices))

    def test_late_expand_detected_korean(self):
        advices = self.coach.get_coaching_advice("[5:00] 확장 지연")
        self.assertIn("expansion", self._categories(advices))

    def test_no_scout_detected(self):
        advices = self.coach.get_coaching_advice("Warning: no scout sent yet")
        self.assertIn("scouting", self._categories(advices))

    def test_army_wipe_critical_severity(self):
        advices = self.coach.get_coaching_advice("ARMY WIPE at 8:00")
        crits = [a for a in advices if a["severity"] == "critical"]
        self.assertTrue(any(c["category"] == "army" for c in crits))

    def test_no_creep_detected(self):
        advices = self.coach.get_coaching_advice("crep coverage warning: no creep")
        self.assertIn("macro", self._categories(advices))

    def test_cloak_detection_failure_critical(self):
        advices = self.coach.get_coaching_advice("Detector missed cloak units")
        crits = [a for a in advices if a["severity"] == "critical"]
        self.assertTrue(any(c["category"] == "scouting" for c in crits))

    def test_no_upgrade_detected(self):
        advices = self.coach.get_coaching_advice("Missing upgrade: ground attack 1")
        self.assertIn("macro", self._categories(advices))

    def test_runby_detected(self):
        advices = self.coach.get_coaching_advice("Runby attack on third base")
        self.assertIn("defense", self._categories(advices))


class TestCoachStatistics(unittest.TestCase):
    def setUp(self):
        self.coach = SC2Coach()

    def test_short_game_advice(self):
        advices = self.coach.get_coaching_advice("Game time: 3 minutes - GG")
        self.assertTrue(any(a["category"] == "timing" for a in advices))

    def test_long_game_no_short_game_advice(self):
        advices = self.coach.get_coaching_advice("Game time: 20 minutes")
        self.assertFalse(any(a["category"] == "timing" for a in advices))

    def test_unit_loss_advice(self):
        advices = self.coach.get_coaching_advice(
            "lost: 30 zerglings\nlost: 25 roaches\nlost: 10 hydras"
        )
        self.assertTrue(any(a["category"] == "army" for a in advices))


class TestCoachSeverityOrdering(unittest.TestCase):
    def test_critical_first(self):
        coach = SC2Coach()
        advices = coach.get_coaching_advice(
            "army wipe\nidle worker\nsupply block\nbad engagement"
        )
        severities = [a["severity"] for a in advices]
        order = {"critical": 0, "high": 1, "medium": 2, "low": 3, "info": 4}
        prev = -1
        for sev in severities:
            cur = order[sev]
            self.assertGreaterEqual(cur, prev)
            prev = cur


class TestCoachHistory(unittest.TestCase):
    def test_history_records_each_call(self):
        coach = SC2Coach()
        self.assertEqual(len(coach.get_coaching_history()), 0)
        coach.get_coaching_advice("supply block")
        coach.get_coaching_advice("idle worker")
        self.assertEqual(len(coach.get_coaching_history()), 2)

    def test_history_contains_metadata(self):
        coach = SC2Coach()
        coach.get_coaching_advice("supply block")
        entry = coach.get_coaching_history()[0]
        self.assertIn("timestamp", entry)
        self.assertIn("advice_count", entry)
        self.assertIn("categories", entry)


class TestCoachEdgeCases(unittest.TestCase):
    def setUp(self):
        self.coach = SC2Coach()

    def test_empty_log_returns_info(self):
        advices = self.coach.get_coaching_advice("")
        self.assertEqual(len(advices), 1)
        self.assertEqual(advices[0]["severity"], "info")

    def test_no_pattern_match_returns_default(self):
        advices = self.coach.get_coaching_advice("Game ran smoothly")
        self.assertEqual(len(advices), 1)
        self.assertEqual(advices[0]["category"], "general")

    def test_format_advice_outputs_string(self):
        advices = self.coach.get_coaching_advice("supply block")
        report = self.coach.format_advice(advices)
        self.assertIsInstance(report, str)
        self.assertIn("SC2", report)


if __name__ == "__main__":
    unittest.main()
