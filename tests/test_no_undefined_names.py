"""Regression guard: zero F8xx undefined-name bugs in the bot core.

Why this lives in the test suite (not just CI lint):

The fixes in commit 71459fb covered 14 real undefined-name bugs that
pytest didn't catch because each one sat on a rarely-exercised branch
(Lurker burrow, expansion-check error path, etc). Lint runs in CI but
that lint is on the strict path that already fails for unrelated
reasons (mypy --strict, black). This test forces the same check to
run on the developer's machine before push, gated on the same fast
flake8 subset (E9,F63,F7,F82) that CI uses for blocking errors.
"""
from __future__ import annotations

import shutil
import subprocess
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent
BOT_CORE = REPO_ROOT / "wicked_zerg_challenger"


def _flake8_path():
    """Find a flake8 executable; skip cleanly if none is available."""
    for name in ("flake8", "python -m flake8"):
        exe = shutil.which(name.split()[0])
        if exe:
            return [exe] if " " not in name else name.split()
    return None


@pytest.fixture(scope="module")
def flake8_cmd():
    cmd = _flake8_path()
    if not cmd:
        pytest.skip("flake8 is not installed in this environment")
    return cmd


def test_no_undefined_names_in_bot_core(flake8_cmd):
    """`flake8 --select=E9,F63,F7,F82` must report zero offenders.

    The same subset is what .github/workflows/ci.yml line 56 runs as
    its blocking lint pass. Keep them aligned — if you need to allow
    a new error class, update both this test and the workflow.
    """
    result = subprocess.run(
        [
            *flake8_cmd,
            str(BOT_CORE),
            "--select=E9,F63,F7,F82",
            "--no-show-source",
        ],
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode == 0, (
        f"flake8 found {result.stdout.count(chr(10))} undefined-name "
        f"offender(s):\n{result.stdout or result.stderr}"
    )
