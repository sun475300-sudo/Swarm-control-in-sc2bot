"""
Unit tests for ``scripts/check_no_empty_logger_calls.py``.

The script is the CI tripwire that enforces the lessons from commit 2e03d2f
(131 empty ``logger.info()`` calls removed) and the cycle-2 follow-up
(7 empty-string ``logger.info("")`` calls removed). It is a regex-based
guard, so the regex itself is the contract — pin it.
"""

from __future__ import annotations

import importlib.util
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent
SCRIPT = REPO_ROOT / "scripts" / "check_no_empty_logger_calls.py"


def _load_module():
    spec = importlib.util.spec_from_file_location("check_no_empty_logger_calls", SCRIPT)
    assert spec and spec.loader, "could not load CI guard script"
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


@pytest.fixture(scope="module")
def regex():
    return _load_module().EMPTY_CALL_RE


@pytest.mark.parametrize(
    "line",
    [
        # Original 131-call regression class
        "logger.info()",
        "logger.debug()",
        "logger.warning()",
        "logger.warn()",
        "logger.error()",
        "logger.critical()",
        "logger.exception()",
        "logger.info(  )",
        # Cycle 2 follow-up: empty-string calls
        'logger.info("")',
        "logger.info('')",
        'logger.info(f"")',
        "logger.info(f'')",
        'logger.warning("")',
        # Indented contexts (real code is indented)
        '            logger.info("")',
        "\tlogger.debug()",
    ],
)
def test_offenders_are_caught(regex, line):
    assert regex.search(line) is not None, f"should flag: {line!r}"


@pytest.mark.parametrize(
    "line",
    [
        # Real, useful log lines must NOT trip the guard
        'logger.info("hello")',
        'logger.warning(f"x={x}")',
        'logger.error("failed: %s", err)',
        'logger.info("Game finished: %s", result)',
        # Other identifiers ending in "logger" must not match
        "mylogger.info()",
        "self.logger.info()",  # `self.logger` is a separate convention; out of scope
        # An empty-arg call that's clearly not a logger
        "foo.info()",
        # Format-string with content
        'logger.info(f"score={s}")',
    ],
)
def test_legitimate_lines_are_not_flagged(regex, line):
    # `\blogger\.` matches inside `self.logger.` too (word boundary lives between
    # `.` and `l`), so `self.logger.info()` is intentionally caught. The migration
    # that motivated this guard left both module-level `logger` and `self.logger`
    # variants, so this is desired behavior.
    if line.startswith("self.logger"):
        assert regex.search(line) is not None
        return
    assert regex.search(line) is None, f"should NOT flag: {line!r}"


def test_commented_out_offenders_are_still_flagged(regex):
    """A comment isn't an escape hatch — the regex is line-based by design,
    so silencing the guard with `#` should still trip it. This prevents the
    'fix' of just commenting out the bad line."""
    assert regex.search("# logger.info() is the call we forbid") is not None


def test_repo_is_currently_clean():
    """The wicked_zerg_challenger tree must contain zero offenders right now."""
    mod = _load_module()
    offenders = mod.find_offenders([REPO_ROOT / "wicked_zerg_challenger"])
    assert offenders == [], "Empty logger calls reappeared:\n" + "\n".join(
        f"  {p}:{ln}: {src}" for p, ln, src in offenders
    )
