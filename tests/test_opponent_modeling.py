# -*- coding: utf-8 -*-
"""
Unit tests for wicked_zerg_challenger/opponent_modeling.py (737 LOC, previously untested).

Exercises the pure data-science parts: OpponentModel.update_from_game,
predict_strategy, get_expected_timing_attacks, serialization roundtrip.
"""
import os
import sys

import pytest

sys.path.insert(
    0, os.path.join(os.path.dirname(__file__), "..", "wicked_zerg_challenger")
)


def _import():
    try:
        from opponent_modeling import (
            GameHistory,
            OpponentModel,
            OpponentStyle,
            StrategySignal,
        )
        return OpponentModel, GameHistory, OpponentStyle, StrategySignal
    except ImportError:
        return None, None, None, None


OpponentModel, GameHistory, OpponentStyle, StrategySignal = _import()

pytestmark = pytest.mark.skipif(
    OpponentModel is None, reason="opponent_modeling not importable"
)


def _history(
    game_id="g1",
    opponent_style="aggressive",
    detected_strategy="roach_rush",
    result="loss",
    build_order=None,
    timing_attacks=None,
    composition=None,
    early_signals=None,
):
    return GameHistory(
        game_id=game_id,
        opponent_race="Zerg",
        opponent_style=opponent_style,
        detected_strategy=detected_strategy,
        build_order_observed=build_order or ["spawningpool", "roachwarren"],
        timing_attacks=timing_attacks or [180.0],
        final_composition=composition or {"zergling": 20, "roach": 10},
        game_result=result,
        game_duration=420.0,
        early_signals=early_signals or ["early_pool"],
        tech_progression=[(120.0, "lair")],
    )


class TestUpdateFromGame:
    def test_games_played_incremented(self):
        m = OpponentModel("enemy-1")
        m.update_from_game(_history())
        assert m.games_played == 1

    def test_loss_means_opponent_won(self):
        m = OpponentModel("enemy-1")
        m.update_from_game(_history(result="loss"))
        assert m.games_won == 1  # opponent's wins
        assert m.games_lost == 0

    def test_win_means_opponent_lost(self):
        m = OpponentModel("enemy-1")
        m.update_from_game(_history(result="win"))
        assert m.games_won == 0
        assert m.games_lost == 1

    def test_dominant_style_updated(self):
        m = OpponentModel("e")
        for _ in range(3):
            m.update_from_game(_history(opponent_style="aggressive"))
        m.update_from_game(_history(opponent_style="macro"))
        assert m.dominant_style == OpponentStyle.AGGRESSIVE

    def test_build_patterns_trimmed_at_20(self):
        m = OpponentModel("e")
        for i in range(25):
            m.update_from_game(_history(build_order=[f"building_{i}"]))
        assert len(m.build_order_patterns) == 20
        # Retains newest
        assert m.build_order_patterns[-1] == ["building_24"]

    def test_timing_attacks_trimmed_at_50(self):
        m = OpponentModel("e")
        # Each history contributes 1 timing. 60 iterations → 50 retained.
        for i in range(60):
            m.update_from_game(_history(timing_attacks=[float(i)]))
        assert len(m.timing_attack_history) == 50
        assert m.timing_attack_history[-1] == 59.0

    def test_signal_correlations_accumulate(self):
        m = OpponentModel("e")
        m.update_from_game(_history(early_signals=["early_pool"],
                                    detected_strategy="rush"))
        m.update_from_game(_history(early_signals=["early_pool"],
                                    detected_strategy="rush"))
        m.update_from_game(_history(early_signals=["early_pool"],
                                    detected_strategy="macro"))
        assert m.early_signal_correlations["early_pool"]["rush"] == 2
        assert m.early_signal_correlations["early_pool"]["macro"] == 1


class TestPredictStrategy:
    def test_empty_signals_returns_unknown(self):
        m = OpponentModel("e")
        assert m.predict_strategy([]) == ("unknown", 0.0)

    def test_no_model_yet_returns_unknown(self):
        m = OpponentModel("e")
        # Predict on a fresh model (no early_signal_correlations).
        assert m.predict_strategy(["early_pool"]) == ("unknown", 0.0)

    def test_single_signal_strong_correlation(self):
        m = OpponentModel("e")
        # Feed 5 games with early_pool→rush.
        for _ in range(5):
            m.update_from_game(_history(early_signals=["early_pool"],
                                        detected_strategy="rush"))
        strategy, confidence = m.predict_strategy(["early_pool"])
        assert strategy == "rush"
        assert confidence == pytest.approx(1.0)

    def test_unknown_signal_falls_back_to_frequent(self):
        m = OpponentModel("e")
        for _ in range(3):
            m.update_from_game(_history(early_signals=["early_pool"],
                                        detected_strategy="rush"))
        m.update_from_game(_history(early_signals=["early_pool"],
                                    detected_strategy="macro"))
        # Predict with a signal the model has never seen.
        strategy, confidence = m.predict_strategy(["never_seen"])
        # Falls back to most-common strategy (rush: 3/4).
        assert strategy == "rush"
        assert confidence == pytest.approx(3 / 4)


class TestExpectedTimingAttacks:
    def test_no_history_empty(self):
        m = OpponentModel("e")
        assert m.get_expected_timing_attacks() == []

    def test_consistent_timing_captured(self):
        m = OpponentModel("e")
        # 5 games each producing timing 180s — all round to 180.
        for _ in range(5):
            m.update_from_game(_history(timing_attacks=[180.0]))
        expected = m.get_expected_timing_attacks()
        assert 180 in expected

    def test_rare_timing_filtered(self):
        m = OpponentModel("e")
        # 10 games mostly at 180, one outlier at 600. Only 180 survives.
        for _ in range(10):
            m.update_from_game(_history(timing_attacks=[180.0]))
        m.update_from_game(_history(timing_attacks=[600.0]))
        expected = m.get_expected_timing_attacks()
        assert 180 in expected
        # 600 appeared in 1/11 games (<30% threshold): must be filtered.
        assert 600 not in expected


class TestSerialization:
    def test_roundtrip_preserves_core_fields(self):
        m = OpponentModel("enemy-42")
        for _ in range(4):
            m.update_from_game(_history(opponent_style="macro",
                                        detected_strategy="hydra_timing",
                                        early_signals=["fast_expand"]))
        data = m.to_dict()
        restored = OpponentModel.from_dict(data)
        assert restored.opponent_id == "enemy-42"
        assert restored.games_played == 4
        assert restored.dominant_style == OpponentStyle.MACRO
        # Signal correlations survive json-like dict round-trip.
        assert restored.early_signal_correlations["fast_expand"]["hydra_timing"] == 4

    def test_from_dict_defaults(self):
        restored = OpponentModel.from_dict({"opponent_id": "fresh"})
        assert restored.games_played == 0
        assert restored.dominant_style == OpponentStyle.UNKNOWN
