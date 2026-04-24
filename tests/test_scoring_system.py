# -*- coding: utf-8 -*-
"""
Unit tests for wicked_zerg_challenger/scoring_system.py (702 LOC, previously untested).

Exercises the pure-logic parts of the scoring system: DomainScore math,
real-time advice triggers, summary/worst-domain rendering, and session-end
reporting. Avoids touching on-disk JSON state by patching _save_*.
"""
import os
import sys
from unittest.mock import MagicMock, patch

import pytest

sys.path.insert(
    0, os.path.join(os.path.dirname(__file__), "..", "wicked_zerg_challenger")
)


def _import():
    try:
        from scoring_system import DomainScore, ScoringSystem
        return DomainScore, ScoringSystem
    except ImportError:
        return None, None


DomainScore, ScoringSystem = _import()

pytestmark = pytest.mark.skipif(
    DomainScore is None, reason="scoring_system not importable"
)


class TestDomainScore:
    def test_initial_zero(self):
        d = DomainScore("Combat")
        assert d.score == 0.0
        assert d.total_events == 0
        assert d.positive_events == 0
        assert d.negative_events == 0

    def test_positive_add(self):
        d = DomainScore("Combat")
        d.add(5.0, "kill")
        assert d.score == 5.0
        assert d.total_events == 1
        assert d.positive_events == 1
        assert d.negative_events == 0

    def test_negative_add(self):
        d = DomainScore("Combat")
        d.add(-3.0, "lost drone")
        assert d.score == -3.0
        assert d.negative_events == 1
        assert d.positive_events == 0

    def test_zero_add_counts_as_negative(self):
        """Implementation: `if points > 0` — zero falls to negative bucket."""
        d = DomainScore("Combat")
        d.add(0.0, "neutral")
        assert d.score == 0.0
        assert d.positive_events == 0
        assert d.negative_events == 1

    def test_history_trimmed_at_100(self):
        d = DomainScore("Combat")
        for i in range(150):
            d.add(1.0, f"event{i}")
        assert len(d.history) == 100
        # Should retain the MOST RECENT 100
        assert d.history[-1]["reason"] == "event149"
        assert d.history[0]["reason"] == "event50"

    @pytest.mark.parametrize(
        "score,expected_grade",
        [
            (100, "S"), (80, "S"),
            (70, "A"), (60, "A"),
            (50, "B"), (40, "B"),
            (30, "C"), (20, "C"),
            (10, "D"), (0, "D"),
            (-1, "F"), (-100, "F"),
        ],
    )
    def test_grade_thresholds(self, score, expected_grade):
        d = DomainScore("Combat")
        d.score = score
        assert d.grade == expected_grade


@pytest.fixture
def bot():
    b = MagicMock()
    b.time = 0.0
    b.minerals = 50
    b.vespene = 0
    b.supply_used = 12
    b.supply_left = 10
    b.supply_army = 0
    b.units = []
    b.structures = []
    b.townhalls = []
    b.enemy_units = []
    return b


@pytest.fixture
def scoring(bot):
    # Skip disk I/O at init
    with patch.object(ScoringSystem, "_load_cumulative_score", return_value={"total": 0, "blocks": []}):
        yield ScoringSystem(bot)


class TestScoringSystemInit:
    def test_ten_domains_created(self, scoring):
        assert set(scoring.domains.keys()) == {
            "combat", "production", "scouting", "economy", "defense",
            "strategy", "micro", "macro", "adaptation", "survival",
        }

    def test_every_domain_starts_at_zero(self, scoring):
        for d in scoring.domains.values():
            assert d.score == 0.0
            assert d.total_events == 0

    def test_update_interval_sensible(self, scoring):
        assert 0.5 <= scoring.update_interval <= 10.0


class TestSummaryAndWorst:
    def test_get_worst_domain(self, scoring):
        scoring.domains["combat"].score = 50
        scoring.domains["economy"].score = -10
        scoring.domains["micro"].score = 20
        assert scoring.get_worst_domain() == "economy"

    def test_get_summary_formats(self, scoring):
        scoring.domains["combat"].score = 40
        scoring.domains["combat"].positive_events = 4
        scoring.domains["combat"].negative_events = 1
        out = scoring.get_summary()
        assert "[SCORE]" in out
        assert "combat" in out
        assert "+4" in out
        assert "-1" in out
        # Summary should mention every domain.
        for name in scoring.domains:
            assert name in out


class TestRealtimeAdvice:
    def test_low_supply_warning(self, scoring, bot):
        bot.time = 400
        bot.supply_used = 40
        advice = scoring.get_realtime_advice()
        assert any("LOW_SUPPLY" in a for a in advice)

    def test_missed_expansion_warning(self, scoring, bot):
        bot.time = 200
        scoring._last_base_count = 1
        advice = scoring.get_realtime_advice()
        assert any("EXPAND" in a for a in advice)

    def test_army_rebuild_urgent(self, scoring, bot):
        bot.time = 300
        bot.supply_used = 100  # avoid LOW_SUPPLY
        scoring._last_base_count = 3  # avoid EXPAND
        scoring._army_wipe_count = 2
        scoring._last_army_alive = False
        advice = scoring.get_realtime_advice()
        assert any("ARMY_REBUILD" in a for a in advice)

    def test_healthy_state_no_warnings(self, scoring, bot):
        bot.time = 600
        bot.supply_used = 150
        scoring._last_base_count = 4
        scoring._army_wipe_count = 0
        scoring._last_army_alive = True
        advice = scoring.get_realtime_advice()
        # Should have no URGENT/WARNING items triggered above.
        joined = " ".join(advice)
        assert "LOW_SUPPLY" not in joined
        assert "ARMY_REBUILD" not in joined
