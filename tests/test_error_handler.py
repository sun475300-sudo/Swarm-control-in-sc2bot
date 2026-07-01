"""
ErrorHandler tests - production / debug mode behaviour.

Coverage:
- safe_execute: success path, default_return on failure (production),
  re-raise in debug mode, error counting + suppression after 3 logs
- safe_coroutine: same semantics for async functions
- get_error_summary / reset_error_counts
"""

import asyncio
import sys
from pathlib import Path

import pytest

_PKG_ROOT = Path(__file__).resolve().parent.parent / "wicked_zerg_challenger"
if str(_PKG_ROOT) not in sys.path:
    sys.path.insert(0, str(_PKG_ROOT))

try:
    from error_handler import ErrorHandler
except ImportError:
    pytest.skip("error_handler unavailable", allow_module_level=True)


# ---------------------------------------------------------------------------
# safe_execute
# ---------------------------------------------------------------------------


def test_safe_execute_returns_function_result_on_success():
    h = ErrorHandler(debug_mode=False)
    assert h.safe_execute(lambda: 42) == 42


def test_safe_execute_passes_args_and_kwargs():
    h = ErrorHandler(debug_mode=False)
    assert h.safe_execute(lambda a, b=0: a + b, 10, b=5) == 15


def test_safe_execute_returns_default_on_failure_in_production():
    h = ErrorHandler(debug_mode=False)

    def boom():
        raise RuntimeError("nope")

    assert h.safe_execute(boom, default_return="fallback") == "fallback"


def test_safe_execute_default_return_is_none_when_unspecified():
    h = ErrorHandler(debug_mode=False)
    assert h.safe_execute(lambda: 1 / 0) is None


def test_safe_execute_increments_error_count():
    h = ErrorHandler(debug_mode=False)
    for _ in range(5):
        h.safe_execute(lambda: 1 / 0, log_key="div0")
    assert h.error_counts["div0"] == 5


def test_safe_execute_uses_function_name_when_log_key_missing():
    h = ErrorHandler(debug_mode=False)

    def some_named_function():
        raise RuntimeError("x")

    h.safe_execute(some_named_function)
    assert h.error_counts["some_named_function"] == 1


def test_safe_execute_debug_mode_reraises():
    h = ErrorHandler(debug_mode=True)
    with pytest.raises(ValueError, match="boom"):
        h.safe_execute(lambda: (_ for _ in ()).throw(ValueError("boom")))


# ---------------------------------------------------------------------------
# safe_coroutine
# ---------------------------------------------------------------------------


def _run(coro):
    return asyncio.run(coro)


def test_safe_coroutine_returns_result_on_success():
    h = ErrorHandler(debug_mode=False)

    @h.safe_coroutine(log_key="ok")
    async def good():
        return "ok-value"

    assert _run(good()) == "ok-value"


def test_safe_coroutine_returns_default_on_failure_in_production():
    h = ErrorHandler(debug_mode=False)

    @h.safe_coroutine(log_key="fail", default_return="fallback")
    async def boom():
        raise RuntimeError("nope")

    assert _run(boom()) == "fallback"
    assert h.error_counts["fail"] == 1


def test_safe_coroutine_default_return_is_none_when_unspecified():
    h = ErrorHandler(debug_mode=False)

    @h.safe_coroutine()
    async def boom():
        raise RuntimeError("nope")

    assert _run(boom()) is None


def test_safe_coroutine_uses_function_name_when_log_key_missing():
    h = ErrorHandler(debug_mode=False)

    @h.safe_coroutine()
    async def specific_name():
        raise RuntimeError("x")

    _run(specific_name())
    assert h.error_counts["specific_name"] == 1


def test_safe_coroutine_debug_mode_reraises():
    h = ErrorHandler(debug_mode=True)

    @h.safe_coroutine()
    async def boom():
        raise ValueError("debug-boom")

    with pytest.raises(ValueError, match="debug-boom"):
        _run(boom())


# ---------------------------------------------------------------------------
# Suppression past max_error_logs
# ---------------------------------------------------------------------------


def test_safe_execute_logs_first_three_then_suppresses(caplog):
    h = ErrorHandler(debug_mode=False)
    caplog.set_level("ERROR")
    for _ in range(10):
        h.safe_execute(lambda: 1 / 0, log_key="div0")

    # Count "div0 failed:" log entries — should be 3 (max_error_logs).
    failed_logs = [r for r in caplog.records if "div0 failed:" in r.getMessage()]
    assert len(failed_logs) == 3
    # And one "suppressing" message at the cap.
    suppressing = [r for r in caplog.records if "Suppressing" in r.getMessage()]
    assert len(suppressing) == 1


# ---------------------------------------------------------------------------
# Summary / reset
# ---------------------------------------------------------------------------


def test_get_error_summary_returns_copy():
    h = ErrorHandler(debug_mode=False)
    h.safe_execute(lambda: 1 / 0, log_key="a")
    h.safe_execute(lambda: 1 / 0, log_key="b")
    h.safe_execute(lambda: 1 / 0, log_key="b")
    summary = h.get_error_summary()
    assert summary == {"a": 1, "b": 2}
    # Mutating the returned dict must not affect the handler.
    summary["a"] = 999
    assert h.error_counts["a"] == 1


def test_reset_error_counts_clears_state():
    h = ErrorHandler(debug_mode=False)
    for _ in range(3):
        h.safe_execute(lambda: 1 / 0, log_key="x")
    assert h.error_counts["x"] == 3
    h.reset_error_counts()
    assert h.get_error_summary() == {}
