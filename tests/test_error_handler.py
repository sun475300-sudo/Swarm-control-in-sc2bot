# -*- coding: utf-8 -*-
"""Tests for wicked_zerg_challenger/error_handler.py."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "wicked_zerg_challenger"))

from error_handler import ErrorHandler  # noqa: E402


def test_log_error_records_count_without_raising():
    handler = ErrorHandler(debug_mode=False)
    try:
        raise ValueError("boom")
    except ValueError as exc:
        handler.log_error("subsystem_x", exc)

    assert handler.get_error_summary() == {"subsystem_x": 1}


def test_log_error_rate_limits_repeated_failures(caplog):
    handler = ErrorHandler(debug_mode=False)
    handler.max_error_logs = 3

    for _ in range(5):
        try:
            raise ValueError("boom")
        except ValueError as exc:
            with caplog.at_level("ERROR", logger="ErrorHandler"):
                handler.log_error("subsystem_x", exc)

    assert handler.get_error_summary()["subsystem_x"] == 5
    error_lines = [r for r in caplog.records if r.message.startswith("subsystem_x failed")]
    assert len(error_lines) == handler.max_error_logs
