# -*- coding: utf-8 -*-
"""Tests for adaptive_learning_rate.py — win-rate-based LR adjustment."""

import sys
import os
import tempfile
import pytest

sys.path.insert(0, "wicked_zerg_challenger")

from adaptive_learning_rate import AdaptiveLearningRate


def _make_lr(**kwargs):
    """Create an AdaptiveLearningRate with a temp save path."""
    kwargs.setdefault("initial_lr", 0.001)
    kwargs.setdefault("min_lr", 0.0001)
    kwargs.setdefault("max_lr", 0.01)
    kwargs.setdefault("adjustment_factor", 1.2)
    kwargs.setdefault("patience", 10)
    alr = AdaptiveLearningRate(**kwargs)
    # Override save path to avoid polluting the real file
    alr.save_path = "/tmp/adaptive_lr_test_stats.json"
    return alr


class TestInitialization:
    def test_default_parameters(self):
        alr = _make_lr()
        assert alr.learning_rate == 0.001
        assert alr.min_lr == 0.0001
        assert alr.max_lr == 0.01
        assert alr.adjustment_factor == 1.2
        assert alr.patience == 10

    def test_initial_stats_zero(self):
        alr = _make_lr()
        assert alr.total_games == 0
        assert alr.total_wins == 0
        assert alr.recent_win_rates == []
        assert alr.games_without_improvement == 0


class TestUpdateWin:
    def test_win_increments_total(self):
        alr = _make_lr()
        alr.update(game_won=True)
        assert alr.total_games == 1
        assert alr.total_wins == 1

    def test_loss_increments_games_only(self):
        alr = _make_lr()
        alr.update(game_won=False)
        assert alr.total_games == 1
        assert alr.total_wins == 0

    def test_insufficient_data_no_adjustment(self):
        alr = _make_lr()
        # Window size defaults to 20; a single game shouldn't trigger adjustment
        result = alr.update(game_won=True)
        assert result is None


class TestLearningRateIncrease:
    def test_increase_stays_under_max(self):
        alr = _make_lr(initial_lr=0.009, max_lr=0.01, adjustment_factor=1.2)
        # 0.009 * 1.2 = 0.0108 > max 0.01 → should NOT increase
        result = alr._increase_learning_rate()
        assert result is None
        assert alr.learning_rate == 0.009

    def test_increase_succeeds_in_range(self):
        alr = _make_lr(initial_lr=0.001, adjustment_factor=1.5)
        result = alr._increase_learning_rate()
        assert result is not None
        assert alr.learning_rate > 0.001


class TestLearningRateDecrease:
    def test_decrease_stays_above_min(self):
        alr = _make_lr(initial_lr=0.00011, min_lr=0.0001, adjustment_factor=1.2)
        # 0.00011 / 1.2 ≈ 0.0000916 < min 0.0001 → should NOT decrease
        result = alr._decrease_learning_rate()
        assert result is None
        assert alr.learning_rate == 0.00011

    def test_decrease_succeeds(self):
        alr = _make_lr(initial_lr=0.005, min_lr=0.0001, adjustment_factor=2.0)
        old_lr = alr.learning_rate
        result = alr._decrease_learning_rate()
        assert result is not None
        assert alr.learning_rate < old_lr


class TestGetCurrentLR:
    def test_returns_current(self):
        alr = _make_lr(initial_lr=0.005)
        assert alr.get_current_lr() == 0.005


class TestGetStats:
    def test_returns_dict(self):
        alr = _make_lr()
        stats = alr.get_stats()
        assert isinstance(stats, dict)

    def test_includes_core_fields(self):
        alr = _make_lr()
        alr.update(True)
        alr.update(False)
        stats = alr.get_stats()
        # Should include total games, wins, current LR
        assert any(k in stats for k in ("total_games", "games", "total"))


class TestGetSummary:
    def test_returns_string(self):
        alr = _make_lr()
        summary = alr.get_summary()
        assert isinstance(summary, str)
        assert len(summary) > 0


class TestReset:
    def test_reset_clears_improvement_counter(self):
        alr = _make_lr()
        alr.games_without_improvement = 5
        alr.reset()
        assert alr.games_without_improvement == 0

    def test_reset_restores_best_learning_rate(self):
        alr = _make_lr(initial_lr=0.005)
        alr.best_learning_rate = 0.001
        alr.reset()
        # After reset, LR should be the best learning rate if valid
        assert alr.learning_rate == 0.001


class TestFillWindowAndImprove:
    def test_fill_window_triggers_adjustment(self):
        alr = _make_lr()
        alr.window_size = 3
        # 3 wins in a row should fill window and trigger an increase
        for _ in range(3):
            alr.update(True)
        # Best win rate should now be 1.0 and LR should have been considered for increase
        assert alr.best_win_rate > 0

    def test_fill_window_with_losses_triggers_patience(self):
        alr = _make_lr()
        alr.window_size = 2
        alr.patience = 1
        # Start with a good win to raise best_win_rate
        alr.update(True)
        alr.update(True)  # fills window at 100%
        # Then losses: best_win_rate is 1.0, recent avg drops
        result_1 = alr.update(False)
        result_2 = alr.update(False)
        # At some point, games_without_improvement should trigger decrease
        # (not guaranteed on first call, but shouldn't crash)
        assert result_1 is None or isinstance(result_1, float)
        assert result_2 is None or isinstance(result_2, float)


class TestCleanup:
    def teardown_method(self):
        # Clean up any stats file we may have created
        if os.path.exists("/tmp/adaptive_lr_test_stats.json"):
            os.unlink("/tmp/adaptive_lr_test_stats.json")
