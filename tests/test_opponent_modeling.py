# -*- coding: utf-8 -*-
"""
Unit tests for OpponentModeling — the live (on_game_start / on_step /
on_game_end) lifecycle that the main bot actually wires up.

These lock in the contract that wicked_zerg_bot_pro_impl relies on:
the per-opponent records live under ``opponent_models`` (keyed by
``current_opponent``), and a finished game bumps ``games_played``.
"""

import os
import sys

import pytest

sys.path.insert(
    0, os.path.join(os.path.dirname(__file__), "..", "wicked_zerg_challenger")
)

try:
    import opponent_modeling as om_mod
except ImportError:  # pragma: no cover - module is sc2-free, but stay defensive
    pytest.skip("opponent_modeling not importable", allow_module_level=True)

OpponentModeling = om_mod.OpponentModeling


@pytest.fixture
def om(tmp_path):
    from unittest.mock import MagicMock

    bot = MagicMock()
    bot.time = 0.0
    data_file = tmp_path / "opponent_models.json"
    return OpponentModeling(bot=bot, data_file=str(data_file))


class TestLiveLifecycle:
    def test_on_game_start_registers_opponent(self, om):
        om.on_game_start("TestOpponent", None)
        assert om.current_opponent == "TestOpponent"
        # The dict the main bot reads is `opponent_models` (not `models`).
        assert "TestOpponent" in om.opponent_models

    def test_models_attribute_is_opponent_models(self, om):
        # pro_impl reads `opponent_modeling.opponent_models`; guard the name so a
        # rename/typo (the old `.models` bug) is caught here, not silently in-game.
        assert hasattr(om, "opponent_models")

    def test_game_end_increments_games_played(self, om):
        om.on_game_start("Rival", None)
        before = om.opponent_models["Rival"].games_played
        om.on_game_end(won=True, lost=False)
        assert om.opponent_models["Rival"].games_played == before + 1

    def test_win_is_recorded_as_opponent_loss(self, om):
        # We won -> from the opponent model's perspective the opponent lost.
        om.on_game_start("Rival", None)
        om.on_game_end(won=True, lost=False)
        model = om.opponent_models["Rival"]
        assert model.games_lost == 1
        assert model.games_won == 0

    def test_loss_is_recorded_as_opponent_win(self, om):
        # We lost -> the opponent won.
        om.on_game_start("Rival", None)
        om.on_game_end(won=False, lost=True)
        model = om.opponent_models["Rival"]
        assert model.games_won == 1
        assert model.games_lost == 0

    def test_game_end_without_start_is_noop(self, om):
        # No current opponent yet -> must not raise.
        om.on_game_end(won=False, lost=True)

    def test_models_persisted_to_data_file(self, om):
        om.on_game_start("Persisted", None)
        om.on_game_end(won=True, lost=False)
        assert os.path.exists(om.data_file)


class TestOpponentStats:
    """get_opponent_stats is keyed by `current_opponent` (the live attribute
    personality_module reads); ensure that lookup path returns real data."""

    def test_stats_for_live_current_opponent(self, om):
        om.on_game_start("StatRival", None)
        om.on_game_end(won=False, lost=True)  # opponent won
        stats = om.get_opponent_stats(om.current_opponent)
        assert stats is not None
        assert stats["games_played"] == 1
        assert stats["win_rate"] == 1.0  # opponent's win rate against us

    def test_stats_none_for_unknown_opponent(self, om):
        assert om.get_opponent_stats("NeverSeen") is None
