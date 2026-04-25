"""
Static-quality regression guards.

These are cheap whole-tree checks that catch bug classes which are easy to
re-introduce and hard to notice in review:

  * F821 — `undefined name 'X'`. We had 14 of these on `main` (wrong
    parameter name, missing import, broken forward reference). Each one
    is a runtime crash waiting to happen on whichever code path executes.
  * F822 — `undefined name 'X' in __all__`. The `chat_manager.py` shim
    exported `ChatManager` from a module that never existed in the repo.

  * `tools/check_missing_logic.py` — used `Path.rglob('*.py')` as if it
    returned `(root, dirs, files)` tuples. Now smoke-tested.

Run all guards with: `pytest tests/test_static_quality.py -v`
"""

from __future__ import annotations

import shutil
import subprocess
import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent
PACKAGE_ROOT = REPO_ROOT / "wicked_zerg_challenger"


@pytest.mark.skipif(shutil.which("flake8") is None, reason="flake8 not installed")
def test_no_f821_or_f822_in_package() -> None:
    """Package must stay free of `F821` (undefined name) and `F822`."""
    result = subprocess.run(
        [
            "flake8",
            str(PACKAGE_ROOT),
            "--select=F821,F822",
            "--exclude=__pycache__,.venv",
        ],
        capture_output=True,
        text=True,
        cwd=str(REPO_ROOT),
    )
    assert result.returncode == 0, (
        "flake8 found undefined-name errors:\n" + result.stdout + result.stderr
    )


def test_check_missing_logic_runs_without_error() -> None:
    """tools/check_missing_logic.py crashed on `Path.rglob` unpacking; guard it."""
    script = PACKAGE_ROOT / "tools" / "check_missing_logic.py"
    assert script.exists(), f"missing: {script}"
    result = subprocess.run(
        [sys.executable, str(script)],
        capture_output=True,
        text=True,
        timeout=120,
    )
    assert result.returncode == 0, (
        "check_missing_logic.py exited non-zero:\n"
        f"stdout:\n{result.stdout}\nstderr:\n{result.stderr}"
    )


def test_no_path_rglob_unpacked_as_tuple() -> None:
    """`for a, b, c in path.rglob(...)` is always wrong (rglob yields Paths)."""
    import re

    pattern = re.compile(r"for\s+\w+\s*,\s*\w+\s*,\s*\w+\s+in\s+.+\.rglob\(")
    offenders: list[str] = []
    for path in PACKAGE_ROOT.rglob("*.py"):
        if "__pycache__" in path.parts:
            continue
        try:
            text = path.read_text(encoding="utf-8", errors="replace")
        except OSError:
            continue
        for i, line in enumerate(text.splitlines(), 1):
            if pattern.search(line):
                offenders.append(f"{path.relative_to(REPO_ROOT)}:{i}: {line.strip()}")
    assert not offenders, "rglob unpacked as os.walk-style tuple:\n" + "\n".join(
        offenders
    )
