# -*- coding: utf-8 -*-
"""Unit tests for ErrorHandler.log_step_error.

Covers the count-then-rate-limit logging path used by every manager
on_step block in bot_step_integration to surface (rather than silently
swallow) per-frame manager failures.
"""
from __future__ import annotations

import os
import sys
import unittest
from unittest.mock import MagicMock

os.environ["PROTOCOL_BUFFERS_PYTHON_IMPLEMENTATION"] = "python"
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from error_handler import ErrorHandler


class TestLogStepError(unittest.TestCase):
    def _handler(self, debug=False):
        h = ErrorHandler(debug_mode=debug)
        h.max_error_logs = 3
        return h

    def test_debug_mode_reraises(self):
        h = self._handler(debug=True)
        log = MagicMock()
        boom = RuntimeError("boom")
        with self.assertRaises(RuntimeError):
            h.log_step_error("Combat", boom, log)
        # debug-mode path must not log nor count
        log.error.assert_not_called()
        self.assertEqual(h.error_counts["Combat"], 0)

    def test_non_debug_logs_and_counts(self):
        h = self._handler(debug=False)
        log = MagicMock()
        h.log_step_error("Combat", RuntimeError("x"), log)
        self.assertEqual(h.error_counts["Combat"], 1)
        log.error.assert_called_once()
        msg = log.error.call_args[0][0]
        self.assertIn("Combat", msg)
        self.assertIn("x", msg)

    def test_rate_limit_caps_at_max_error_logs(self):
        h = self._handler(debug=False)
        log = MagicMock()
        for _ in range(h.max_error_logs + 5):
            h.log_step_error("Eco", RuntimeError("y"), log)
        self.assertEqual(log.error.call_count, h.max_error_logs)
        self.assertEqual(h.error_counts["Eco"], h.max_error_logs + 5)

    def test_independent_keys_have_independent_counters(self):
        h = self._handler(debug=False)
        log = MagicMock()
        for _ in range(2):
            h.log_step_error("A", RuntimeError("e"), log)
        for _ in range(5):
            h.log_step_error("B", RuntimeError("e"), log)
        self.assertEqual(h.error_counts["A"], 2)
        self.assertEqual(h.error_counts["B"], 5)
        # A logged twice (under cap), B capped at 3
        self.assertEqual(log.error.call_count, 2 + h.max_error_logs)


if __name__ == "__main__":
    unittest.main()
