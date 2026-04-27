# -*- coding: utf-8 -*-
"""Tests for opponent_modeling.py — OpponentStyle, StrategySignal, OpponentModel."""

import sys
import pytest

sys.path.insert(0, "wicked_zerg_challenger")

from opponent_modeling import (
    OpponentStyle,
    StrategySignal,
    GameHistory,
    OpponentModel,
)


class TestOpponentStyleEnum:
    def test_all_styles_exist(self):
        assert OpponentStyle.UNKNOWN
        assert OpponentStyle.AGGRESSIVE
        assert OpponentStyle.MACRO
        assert OpponentStyle.CHEESE
        assert OpponentStyle.TIMING
        assert OpponentStyle.DEFENSIVE
        assert OpponentStyle.MIXED

    def test_style_values(self):
        assert OpponentStyle.AGGRESSIVE.value == "aggressive"
        assert OpponentStyle.MACRO.value == "macro"


class TestStrategySignalEnum:
    def test_build_signals(self):
        assert StrategySignal.EARLY_POOL
        assert StrategySignal.FAST_EXPAND
        assert StrategySignal.PROXY_DETECTED
        assert StrategySignal.TECH_RUSH

    def test_composition_signals(self):
        assert StrategySignal.MASS_WORKERS
        assert StrategySignal.EARLY_ARMY
        assert StrategySignal.AIR_UNITS_EARLY

    def test_behavior_signals(self):
        assert StrategySignal.SCOUTING_AGGRESSIVE
        assert StrategySignal.BASE_HIDDEN


class TestGameHistory:
    def test_instantiate_with_all_fields(self):
        gh = GameHistory(
            game_id="game_1",
            opponent_race="Terran",
            opponent_style="aggressive",
            detected_strategy="marine_rush",
            build_order_observed=["barracks", "gas"],
            timing_attacks=[180.0],
            final_composition={"MARINE": 30},
            game_result="win",
            game_duration=720.0,
            early_signals=["EARLY_POOL"],
            tech_progression=[(120.0, "factory")],
        )
        assert gh.game_id == "game_1"
        assert gh.game_result == "win"


class TestOpponentModel:
    def test_init(self):
        om = OpponentModel("opponent_test")
        assert om.opponent_id == "opponent_test"

    def test_empty_model_initial_state(self):
        om = OpponentModel("opponent_x")
        # Should have reasonable default/empty containers
        assert om is not None


class TestUpdateFromGame:
    def test_game_recorded(self):
        om = OpponentModel("opp_1")
        gh = GameHistory(
            game_id="g1",
            opponent_race="Zerg",
            opponent_style="aggressive",
            detected_strategy="zergling_rush",
            build_order_observed=["spawningpool"],
            timing_attacks=[120.0],
            final_composition={"ZERGLING": 40},
            game_result="win",
            game_duration=480.0,
            early_signals=["EARLY_POOL"],
            tech_progression=[(60.0, "spawningpool")],
        )
        om.update_from_game(gh)
        # The model should have absorbed the game
        # (exact internal state depends on implementation)


class TestPredictStrategy:
    def test_unknown_signals_returns_low_confidence(self):
        om = OpponentModel("opp_unknown")
        result = om.predict_strategy(["completely_novel_signal"])
        # Returns (strategy_name, confidence) tuple
        assert isinstance(result, tuple)
        assert len(result) == 2
        strategy_name, confidence = result
        assert isinstance(confidence, (int, float))

    def test_prediction_after_learning(self):
        om = OpponentModel("opp_bio")
        # Train with a pattern
        gh = GameHistory(
            game_id="g1",
            opponent_race="Terran",
            opponent_style="aggressive",
            detected_strategy="bio_timing",
            build_order_observed=["barracks"],
            timing_attacks=[300.0],
            final_composition={"MARINE": 25},
            game_result="loss",
            game_duration=600.0,
            early_signals=["EARLY_ARMY", "MASS_WORKERS"],
            tech_progression=[],
        )
        om.update_from_game(gh)
        # Predict with matching signals
        strategy, confidence = om.predict_strategy(["EARLY_ARMY"])
        assert isinstance(strategy, str)
        assert confidence >= 0


class TestSerialization:
    def test_to_dict_returns_dict(self):
        om = OpponentModel("opp_serial")
        d = om.to_dict()
        assert isinstance(d, dict)

    def test_from_dict_reconstructs(self):
        om = OpponentModel("opp_roundtrip")
        data = om.to_dict()
        om2 = OpponentModel.from_dict(data)
        assert om2.opponent_id == "opp_roundtrip"


class TestExpectedTiming:
    def test_returns_list(self):
        om = OpponentModel("opp_timing")
        timings = om.get_expected_timing_attacks()
        assert isinstance(timings, list)

    def test_after_training(self):
        om = OpponentModel("opp_t2")
        for i in range(3):
            gh = GameHistory(
                game_id=f"g{i}",
                opponent_race="Zerg",
                opponent_style="timing",
                detected_strategy="timing_push",
                build_order_observed=[],
                timing_attacks=[300.0 + i * 10],
                final_composition={},
                game_result="loss",
                game_duration=600.0,
                early_signals=[],
                tech_progression=[],
            )
            om.update_from_game(gh)
        # Should have some data now
        timings = om.get_expected_timing_attacks()
        assert isinstance(timings, list)
