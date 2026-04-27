"""Pytest mirror of scripts/check_no_empty_logger_calls.py.

The script is wired into CI via .github/workflows/empty-logger-guard.yml,
but mirroring it as a pytest test means a single `pytest tests/` run
locally catches the same regression without needing to remember to invoke
the script separately.

Background: commit 2e03d2f removed 131 empty `logger.info()/.debug()/...`
calls left over from the print->logger migration. This test prevents the
same bug class from recurring.
"""
from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent
SCRIPT_PATH = REPO_ROOT / "scripts" / "check_no_empty_logger_calls.py"


def _load_check_module():
    spec = importlib.util.spec_from_file_location(
        "_check_no_empty_logger_calls", SCRIPT_PATH
    )
    if spec is None or spec.loader is None:
        pytest.skip(f"cannot load {SCRIPT_PATH}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def test_no_empty_logger_calls_in_bot_core():
    """The bot core must not contain `logger.<level>()` (no-arg) calls."""
    if not SCRIPT_PATH.exists():
        pytest.skip(f"{SCRIPT_PATH} missing")

    check = _load_check_module()
    bot_core = REPO_ROOT / "wicked_zerg_challenger"
    if not bot_core.exists():
        pytest.skip(f"{bot_core} missing")

    offenders = check.find_offenders([bot_core])

    assert not offenders, (
        f"{len(offenders)} empty logger call(s) found — these were the bug "
        f"class fixed in 2e03d2f and must not regress:\n"
        + "\n".join(
            f"  {path.relative_to(REPO_ROOT)}:{lineno}: {line}"
            for path, lineno, line in offenders[:20]
        )
        + (f"\n  ... and {len(offenders) - 20} more" if len(offenders) > 20 else "")
    )
