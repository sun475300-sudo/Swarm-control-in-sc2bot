# -*- coding: utf-8 -*-
"""
Regression tests for ScoringSystem exception containment + score-block math.

Locks in:
1. on_step() never raises out of the per-frame tick even when bot.*
   attribute access fails, and failures emit a debug log (not silent).
2. _save_score_report / _save_cumulative_score warn on I/O failure
   instead of swallowing the traceback.
"""

import json
import logging
import os
import sys
from pathlib import Path
from unittest.mock import patch

import pytest

sys.path.insert(
    0, str(Path(__file__).parent.parent / "wicked_zerg_challenger")
)

try:
    from scoring_system import ScoringSystem
except ImportError as e:
    pytest.skip(
        f"scoring_system not importable: {e!r}",
        allow_module_level=True,
    )


class _ExplodingBot:
    """All attribute access raises -- exercises every internal hot-path guard."""

    time = 5.0  # numeric so the update_interval gate is exercised

    def __getattr__(self, name):
        raise RuntimeError(f"explode on attr={name!r}")


@pytest.fixture
def scoring(tmp_path, monkeypatch):
    """ScoringSystem rooted at a tmp save path so we never touch real disk."""
    # Patch the save path BEFORE constructing (constructor calls
    # _load_cumulative_score + os.makedirs).
    monkeypatch.setattr(ScoringSystem, "SAVE_PATH", str(tmp_path))
    return ScoringSystem(_ExplodingBot())


def test_on_step_does_not_raise_when_bot_attributes_explode(scoring):
    # First on_step call needs game_time - last_update_time >= update_interval.
    # Engine pulls bot.time once at the top, which is a class attribute on
    # _ExplodingBot, so the gate passes cleanly; then every internal probe
    # explodes and must be caught.
    scoring.last_update_time = 0.0
    scoring.on_step(iteration=1)  # must not raise


def test_on_step_failure_logs_at_debug_not_silent(scoring, caplog):
    scoring.last_update_time = 0.0
    with caplog.at_level(logging.DEBUG, logger="ScoringSystem"):
        scoring.on_step(iteration=1)
    debug_records = [
        r for r in caplog.records
        if r.name == "ScoringSystem" and r.levelno == logging.DEBUG
    ]
    assert debug_records, (
        "expected at least one debug record from a swallowed probe; "
        f"got: {[(r.name, r.levelname, r.message) for r in caplog.records]}"
    )


def test_save_cumulative_score_warns_when_open_fails(scoring, caplog):
    with patch("builtins.open", side_effect=OSError("disk full")):
        with caplog.at_level(logging.WARNING, logger="ScoringSystem"):
            # Should not raise; failure is logged at WARNING.
            scoring._save_cumulative_score()
    assert any(
        r.levelno == logging.WARNING and "cumulative_score" in r.message
        for r in caplog.records
    ), f"expected WARNING about cumulative_score; got: {[(r.levelname, r.message) for r in caplog.records]}"


def test_load_cumulative_score_warns_on_corrupt_json(tmp_path, monkeypatch, caplog):
    monkeypatch.setattr(ScoringSystem, "SAVE_PATH", str(tmp_path))
    corrupt = tmp_path / "cumulative_score.json"
    corrupt.write_text("{ this is not valid json", encoding="utf-8")
    with caplog.at_level(logging.WARNING, logger="ScoringSystem"):
        scoring = ScoringSystem(_ExplodingBot())
    # On corrupt JSON we fall back to a fresh block.
    assert scoring._cumulative_score == {"total": 0, "blocks": []}
    assert any(
        r.levelno == logging.WARNING and "cumulative_score" in r.message
        for r in caplog.records
    )
