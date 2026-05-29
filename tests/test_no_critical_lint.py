# -*- coding: utf-8 -*-
"""Guard against critical lint errors in the SC2 bot core.

Mirrors the blocking flake8 gate in sc2bot-ci.yml
(``flake8 --select=E9,F63,F7,F82``), which catches syntax errors and
undefined names — e.g. assignments accidentally merged into a comment line,
which previously left ``strategy`` / ``unit_requests`` / ``game_time``
undefined in the bot core. Running it here surfaces such regressions in the
unit test suite instead of only at CI time.
"""
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

BOT_CORE = Path(__file__).resolve().parent.parent / "wicked_zerg_challenger"

# E9: runtime/syntax errors, F63: invalid comparisons, F7: misplaced statements,
# F82: undefined names. These are real bugs, never style nits.
CRITICAL_CODES = "E9,F63,F7,F82"


@pytest.mark.skipif(shutil.which("flake8") is None, reason="flake8 not installed")
def test_bot_core_has_no_critical_lint_errors():
    result = subprocess.run(
        [
            sys.executable,
            "-m",
            "flake8",
            str(BOT_CORE),
            f"--select={CRITICAL_CODES}",
            "--exclude=__pycache__",
        ],
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0, (
        "flake8 critical checks failed in the bot core "
        f"(--select={CRITICAL_CODES}):\n{result.stdout}{result.stderr}"
    )
