"""Pytest mirror of the CI tripwire in ``scripts/check_no_empty_logger_calls.py``.

Background
----------
Commit ``2e03d2f`` cleaned up 131 empty ``logger.<level>()`` calls left
behind by a print->logger migration. There is already a CI workflow
(``.github/workflows/empty-logger-guard.yml``) that calls the script,
but local devs running ``pytest tests/`` did not get the same guard
until the change reached CI.

This test simply re-uses the same script so the same regression is
caught in the same place developers already run their suite.
"""
from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

import pytest

PROJECT_ROOT = Path(__file__).resolve().parent.parent
SCRIPT_PATH = PROJECT_ROOT / "scripts" / "check_no_empty_logger_calls.py"


def _load_check_module():
    spec = importlib.util.spec_from_file_location(
        "check_no_empty_logger_calls", SCRIPT_PATH
    )
    if spec is None or spec.loader is None:
        pytest.skip(f"check script not found at {SCRIPT_PATH}")
    mod = importlib.util.module_from_spec(spec)
    sys.modules.setdefault(spec.name, mod)
    spec.loader.exec_module(mod)
    return mod


def test_no_empty_logger_calls_in_bot_source() -> None:
    mod = _load_check_module()
    roots = [PROJECT_ROOT / "wicked_zerg_challenger"]
    offenders = mod.find_offenders(roots)

    assert offenders == [], (
        "Found empty logger.<level>() calls — the bug class fixed in "
        f"commit 2e03d2f has resurfaced. Offenders:\n"
        + "\n".join(f"  {p}:{ln}: {src}" for p, ln, src in offenders[:20])
    )


def test_regex_matches_typical_offenders() -> None:
    """Belt-and-braces: confirm the regex itself still works."""
    mod = _load_check_module()
    rx = mod.EMPTY_CALL_RE

    for sample in (
        "logger.info()",
        "logger.debug( )",
        "logger.warning(  )",
        "logger.error()",
        "logger.exception()",
    ):
        assert rx.search(sample), f"regex missed: {sample!r}"

    # And does NOT trip on real calls
    for sample in (
        'logger.info("hi")',
        "logger.debug(f'x={x}')",
        "logger.warning('!')",
    ):
        assert not rx.search(sample), f"regex false-positive: {sample!r}"
