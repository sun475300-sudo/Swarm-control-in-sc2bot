"""Regression tests for the meta_game_analyzer fixes shipped in this PR.

These guard against regression of:
  * race_performance / map_performance losses being incremented (was
    silently dropped, making per-race/map win-rates always read as 100%)
  * recommend_strategy returning sample-aware confidence + race+map history
    in the reasoning string (was hardcoded to 0.75 with race_perf/map_perf
    fetched-then-discarded)
"""

from __future__ import annotations

from wicked_zerg_challenger.meta_game_analyzer import (
    MetaGameAnalyzer,
    create_meta_analyzer,
)


def _record(
    analyzer, *, win: int, race: str = "terran", map_name: str = "Acropolis"
) -> None:
    analyzer.record_game(
        {
            "strategy": "macro",
            "win": win,
            "enemy_race": race,
            "map": map_name,
        }
    )


class TestRaceMapLossesIncrement:
    """The bug: losses counter was never bumped on race / map → 100% win rate."""

    def test_race_losses_counter_bumped_on_loss(self):
        a = create_meta_analyzer()
        _record(a, win=0, race="terran")
        assert a.race_performance["terran"]["wins"] == 0
        assert a.race_performance["terran"]["losses"] == 1, (
            "Pre-fix bug: losses counter on race_performance was never "
            "incremented, so win-rate would compute as 0/0 → 50% sentinel "
            "or NaN, never reflecting actual losses."
        )

    def test_map_losses_counter_bumped_on_loss(self):
        a = create_meta_analyzer()
        _record(a, win=0, map_name="GroundZero")
        assert a.map_performance["GroundZero"]["wins"] == 0
        assert a.map_performance["GroundZero"]["losses"] == 1

    def test_mixed_record_balanced(self):
        a = create_meta_analyzer()
        for w in (1, 1, 0, 0, 1):
            _record(a, win=w, race="zerg", map_name="Corridor")
        assert a.race_performance["zerg"] == {"wins": 3, "losses": 2}
        assert a.map_performance["Corridor"] == {"wins": 3, "losses": 2}


class TestSampleAwareConfidence:
    """recommend_strategy now scales confidence with sample size."""

    def test_zero_history_baseline_confidence(self):
        a = create_meta_analyzer()
        rec = a.recommend_strategy("terran", "Acropolis")
        assert rec["confidence"] == 0.5, (
            "With no recorded games, confidence should be coin-flip "
            "baseline (0.5), not the pre-fix hardcoded 0.75."
        )

    def test_confidence_climbs_with_history(self):
        a = create_meta_analyzer()
        for _ in range(5):
            _record(a, win=1, race="terran", map_name="Acropolis")
        rec = a.recommend_strategy("terran", "Acropolis")
        # 5 race games + 5 map games = 10 sample → 0.5 + min(0.4, 10*0.04) = 0.9
        assert rec["confidence"] == 0.9

    def test_confidence_capped_at_0_9(self):
        a = create_meta_analyzer()
        for _ in range(50):
            _record(a, win=1)
        rec = a.recommend_strategy("terran", "Acropolis")
        assert (
            rec["confidence"] == 0.9
        ), "Confidence must cap at 0.9 even with huge sample"

    def test_reasoning_surfaces_history(self):
        a = create_meta_analyzer()
        _record(a, win=1, race="terran", map_name="Acropolis")
        _record(a, win=0, race="terran", map_name="Acropolis")
        rec = a.recommend_strategy("terran", "Acropolis")
        assert "1W/1L" in rec["reasoning"], (
            "Reasoning string should expose the actual race+map history; "
            "pre-fix it was a static 'Based on vs X on Y' template."
        )


class TestRecommendStrategyShape:
    """recommend_strategy contract — keys callers depend on."""

    def test_all_keys_present(self):
        a = create_meta_analyzer()
        rec = a.recommend_strategy("zerg", "Corridor")
        for key in (
            "recommended_strategy",
            "confidence",
            "reasoning",
            "alternatives",
            "meta_analysis",
        ):
            assert key in rec

    def test_defaults_to_macro_for_unknown_race(self):
        a = create_meta_analyzer()
        rec = a.recommend_strategy("alien", "Acropolis")
        assert rec["recommended_strategy"] == "MACRO"
