# -*- coding: utf-8 -*-
"""Regression tests for OpponentModeling.on_step.

A degraded stub on_step once shadowed the full implementation, silently
disabling build-order / timing-attack / tech-progression tracking. These
tests lock in that the rich on_step is the live one (it dispatches to the
continuous-tracking helpers) and that it tolerates a missing bot reference.

No SC2 game instance is required — the bot is mocked.
"""
import os
import sys

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "wicked_zerg_challenger"))

try:
    import opponent_modeling as om
except ImportError:
    pytest.skip("opponent_modeling not importable", allow_module_level=True)


def _make_bot(game_time=200.0):
    bot = type("FakeBot", (), {})()
    bot.time = game_time
    bot.blackboard = None  # skip blackboard branch
    bot.enemy_structures = []
    bot.enemy_units = []
    return bot


def _make_modeling(tmp_path, game_time=200.0):
    bot = _make_bot(game_time)
    return om.OpponentModeling(
        bot=bot,
        intel_manager=None,
        data_file=str(tmp_path / "opponent_models.json"),
    )


def test_on_step_dispatches_to_continuous_trackers(tmp_path, monkeypatch):
    """The live on_step must drive the continuous-tracking helpers; the old
    shadowing stub only called _detect_early_signals."""
    import asyncio
    from unittest.mock import AsyncMock

    modeling = _make_modeling(tmp_path, game_time=200.0)

    for name in (
        "_detect_early_signals",
        "_make_strategy_prediction",
        "_track_build_order",
        "_detect_timing_attacks",
        "_track_tech_progression",
    ):
        monkeypatch.setattr(modeling, name, AsyncMock())

    # iteration far past update_interval so the throttle does not short-circuit
    asyncio.run(modeling.on_step(iteration=10_000))

    # game_time >= 180 with early_game_phase True triggers the transition
    modeling._make_strategy_prediction.assert_awaited()
    # continuous trackers run every active step — these were dead under the stub
    modeling._track_build_order.assert_awaited()
    modeling._detect_timing_attacks.assert_awaited()
    modeling._track_tech_progression.assert_awaited()


def test_on_step_returns_early_without_bot(tmp_path):
    import asyncio

    modeling = _make_modeling(tmp_path)
    modeling.bot = None
    # Must not raise despite self.bot.time access in the body.
    asyncio.run(modeling.on_step(iteration=10_000))


def test_single_on_step_definition():
    """Guard against a second on_step being re-added and silently shadowing."""
    import inspect

    src = inspect.getsource(om.OpponentModeling)
    assert src.count("async def on_step(") == 1, "OpponentModeling must define on_step exactly once"
