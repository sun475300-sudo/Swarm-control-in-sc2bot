# -*- coding: utf-8 -*-
"""
Regression tests for RealtimeAwarenessEngine error containment.

Locks in the contract that on_step() never raises out of the per-frame
tick even when bot.* attribute access fails, and that previously-silent
failures now emit a debug log (no longer swallowed).
"""

import logging
import sys
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import MagicMock

import pytest

sys.path.insert(
    0, str(Path(__file__).parent.parent / "wicked_zerg_challenger")
)

try:
    from realtime_awareness_engine import RealtimeAwarenessEngine
except ImportError as e:
    pytest.skip(
        f"realtime_awareness_engine not importable: {e!r}",
        allow_module_level=True,
    )


class _ExplodingBot:
    """Every attribute access raises -- exercises the engine's try/except hot-path guards."""

    time = 10.0  # last_update gate needs a numeric time

    def __getattr__(self, name):
        raise RuntimeError(f"explode on attr={name!r}")


def test_on_step_does_not_raise_when_bot_attributes_explode():
    bot = _ExplodingBot()
    engine = RealtimeAwarenessEngine(bot)
    # First tick must not raise. The internal try-blocks now log at debug,
    # but the outer contract (return list, no exception) is preserved.
    result = engine.on_step(iteration=1)
    assert isinstance(result, list)


def test_on_step_returns_overrides_list_when_bot_attributes_explode():
    bot = _ExplodingBot()
    engine = RealtimeAwarenessEngine(bot)
    # active_overrides is initialized to []; engine should still expose it.
    out = engine.on_step(iteration=1)
    assert out == engine.active_overrides


def test_on_step_failure_logs_at_debug_not_silent(caplog):
    bot = _ExplodingBot()
    engine = RealtimeAwarenessEngine(bot)
    # Engine logger is "RealtimeAwarenessEngine".
    with caplog.at_level(logging.DEBUG, logger="RealtimeAwarenessEngine"):
        engine.on_step(iteration=1)
    # We don't pin the exact message (it may come from any of the internal
    # guards), only that at least one debug record fired -- the previous
    # bare `except: pass` would have produced zero log records.
    assert any(
        rec.name == "RealtimeAwarenessEngine" and rec.levelno == logging.DEBUG
        for rec in caplog.records
    ), f"expected a debug log on internal failure, got: {[r.message for r in caplog.records]}"
