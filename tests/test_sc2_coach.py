"""
Tests for SC2 Coach (sc2_coach.py)

Covers:
- Pattern matching for known SC2 issues
- Statistical analysis (game time, losses, workers, minerals)
- Severity ordering
- Empty/missing log handling
- Coaching history tracking
- Format output
"""

import os
import sys

import pytest

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from sc2_coach import SC2Coach


class TestPatternMatching:
    def setup_method(self):
        self.coach = SC2Coach()

    def test_supply_block_detected(self):
        advices = self.coach.get_coaching_advice("supply blocked at 36/36")
        assert any(a["category"] == "macro" for a in advices)
        assert any("오버로드" in a["advice"] for a in advices)

    def test_idle_worker_detected(self):
        advices = self.coach.get_coaching_advice("idle worker count: 5")
        assert any(a["category"] == "economy" for a in advices)

    def test_mineral_overflow_detected(self):
        advices = self.coach.get_coaching_advice("mineral bank: 2500")
        assert any(a["category"] == "economy" for a in advices)

    def test_late_expand_detected(self):
        advices = self.coach.get_coaching_advice("late expand at 6:00")
        assert any(a["category"] == "expansion" for a in advices)

    def test_no_scout_detected(self):
        advices = self.coach.get_coaching_advice("no scout sent")
        assert any(a["category"] == "scouting" for a in advices)

    def test_army_wipe_detected(self):
        advices = self.coach.get_coaching_advice("army wipe at 8:30")
        assert any(a["severity"] == "critical" for a in advices)

    def test_missing_inject_detected(self):
        advices = self.coach.get_coaching_advice("missed inject on hatchery #2")
        assert any("인젝트" in a["advice"] for a in advices)

    def test_korean_pattern_detected(self):
        advices = self.coach.get_coaching_advice("인구 부족 발생")
        assert any(a["category"] == "macro" for a in advices)

    def test_creep_spread_pattern_detected(self):
        advices = self.coach.get_coaching_advice("creep spread low at 8 minutes")
        assert any("크립" in a["advice"] for a in advices)

    def test_no_queen_detected(self):
        advices = self.coach.get_coaching_advice("no queen detected")
        assert any(a["category"] == "macro" for a in advices)
        assert any("퀸" in a["advice"] for a in advices)

    def test_no_anti_air_detected(self):
        advices = self.coach.get_coaching_advice("no anti air available")
        assert any(a["category"] == "army" for a in advices)

    def test_proxy_build_detected(self):
        advices = self.coach.get_coaching_advice("proxy gateway scouted")
        assert any(a["category"] == "scouting" for a in advices)

    def test_unit_clump_detected(self):
        advices = self.coach.get_coaching_advice("units clumped, focus fired")
        assert any(a["category"] == "micro" for a in advices)


class TestStatisticalAnalysis:
    def setup_method(self):
        self.coach = SC2Coach()

    def test_short_game_warning(self):
        advices = self.coach.get_coaching_advice("game time: 3")
        assert any(a["category"] == "timing" for a in advices)

    def test_long_game_warning(self):
        advices = self.coach.get_coaching_advice("game time: 30")
        assert any(a["category"] == "timing" for a in advices)

    def test_high_losses_warning(self):
        advices = self.coach.get_coaching_advice("lost 30 lost 25 lost 10")
        assert any(a["category"] == "army" for a in advices)

    def test_low_worker_count_warning(self):
        advices = self.coach.get_coaching_advice("workers: 8")
        assert any(a["category"] == "economy" for a in advices)
        assert any("일꾼 수" in a["advice"] for a in advices)

    def test_high_mineral_bank_warning(self):
        advices = self.coach.get_coaching_advice("minerals: 2000")
        assert any(a["category"] == "economy" for a in advices)


class TestSeverityOrdering:
    def setup_method(self):
        self.coach = SC2Coach()

    def test_severity_sorted_critical_first(self):
        advices = self.coach.get_coaching_advice(
            "army wipe; idle workers: 3; supply block"
        )
        severities = [a["severity"] for a in advices]
        order = {"critical": 0, "high": 1, "medium": 2, "low": 3, "info": 4}
        for i in range(len(severities) - 1):
            assert order[severities[i]] <= order[severities[i + 1]]


class TestEmptyAndMissingLog:
    def setup_method(self):
        self.coach = SC2Coach()

    def test_empty_log_returns_info(self):
        advices = self.coach.get_coaching_advice("")
        assert len(advices) == 1
        assert advices[0]["severity"] == "info"

    def test_no_match_returns_default(self):
        advices = self.coach.get_coaching_advice("normal game played without issues")
        assert len(advices) >= 1
        # First (or only) should be the default general info
        general = [a for a in advices if a["category"] == "general"]
        assert len(general) >= 1


class TestCoachingHistory:
    def setup_method(self):
        self.coach = SC2Coach()

    def test_history_recorded(self):
        self.coach.get_coaching_advice("supply block")
        self.coach.get_coaching_advice("idle worker")
        history = self.coach.get_coaching_history()
        assert len(history) == 2
        assert "timestamp" in history[0]
        assert "advice_count" in history[0]
        assert "categories" in history[0]


class TestFormatAdvice:
    def setup_method(self):
        self.coach = SC2Coach()

    def test_format_empty(self):
        result = self.coach.format_advice([])
        assert result == "코칭 조언 없음"

    def test_format_includes_severity_icon(self):
        advices = [
            {
                "category": "army",
                "category_name": "군대 운용",
                "advice": "test advice",
                "severity": "critical",
            }
        ]
        result = self.coach.format_advice(advices)
        assert "[!!!]" in result
        assert "test advice" in result


class TestAnalyzeBotLog:
    def setup_method(self):
        self.coach = SC2Coach()

    def test_missing_bot_log_returns_info(self):
        # 봇 로그가 없을 때 안전하게 처리되는지
        result = self.coach.analyze_bot_log()
        # 로그가 있을 수도, 없을 수도 있음 (환경 의존)
        assert isinstance(result, list)
        assert len(result) >= 1
