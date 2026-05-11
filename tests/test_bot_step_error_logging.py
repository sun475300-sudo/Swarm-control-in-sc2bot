"""Tests for BotStepIntegrator._log_step_error rate-limited error reporting.

The integrator wraps every per-system on_step call in try/except. Previously
those handlers silently swallowed exceptions outside of debug mode, hiding
real bugs from production logs. The `_log_step_error` helper now reports the
first N failures per system through the logger (with traceback) and then
suppresses further messages to avoid spam.
"""
from __future__ import annotations

import sys
from pathlib import Path
from unittest.mock import MagicMock

import pytest

PROJECT_ROOT = Path(__file__).resolve().parent.parent
WZC_ROOT = PROJECT_ROOT / "wicked_zerg_challenger"
for p in (PROJECT_ROOT, WZC_ROOT):
    sp = str(p)
    if sp not in sys.path:
        sys.path.insert(0, sp)

try:
    from bot_step_integration import BotStepIntegrator
    from error_handler import error_handler
except Exception as exc:  # pragma: no cover - import guard
    pytest.skip(f"bot_step_integration unavailable: {exc}", allow_module_level=True)


def _make_integrator():
    bot = MagicMock()
    bot.logger = MagicMock()
    integrator = BotStepIntegrator.__new__(BotStepIntegrator)
    integrator.bot = bot
    integrator.logger = bot.logger
    return integrator, bot


def test_debug_mode_reraises(monkeypatch):
    integrator, _ = _make_integrator()
    monkeypatch.setattr(error_handler, "debug_mode", True)
    with pytest.raises(RuntimeError):
        integrator._log_step_error("UnitTest", RuntimeError("boom"))


def test_production_mode_logs_first_n_then_suppresses(monkeypatch):
    integrator, _ = _make_integrator()
    monkeypatch.setattr(error_handler, "debug_mode", False)
    error_handler.error_counts["UnitTestProd"] = 0
    monkeypatch.setattr(error_handler, "max_error_logs", 2, raising=False)

    for _ in range(5):
        integrator._log_step_error("UnitTestProd", ValueError("x"))

    # 2 error reports + 1 suppression notice = 3 calls
    assert integrator.logger.warning.call_count == 3
    last_msg = integrator.logger.warning.call_args_list[-1].args[0]
    assert "suppressed" in last_msg


def test_each_key_counted_separately(monkeypatch):
    integrator, _ = _make_integrator()
    monkeypatch.setattr(error_handler, "debug_mode", False)
    error_handler.error_counts["KeyA"] = 0
    error_handler.error_counts["KeyB"] = 0
    monkeypatch.setattr(error_handler, "max_error_logs", 1, raising=False)

    integrator._log_step_error("KeyA", ValueError("a"))
    integrator._log_step_error("KeyB", ValueError("b"))

    # Each key triggers: 1 error log + 1 suppression notice (since max=1)
    assert integrator.logger.warning.call_count == 4
