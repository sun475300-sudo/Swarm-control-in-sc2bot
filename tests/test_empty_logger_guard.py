# -*- coding: utf-8 -*-
"""Make the empty-logger() regression guard part of the unit test suite.

Mirrors `.github/workflows/empty-logger-guard.yml` so the bug class
fixed in commit 2e03d2f also surfaces during local `pytest` runs,
not just in CI.
"""

from __future__ import annotations

import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT / "scripts"))


def test_no_empty_logger_calls_in_bot_core() -> None:
    """`wicked_zerg_challenger/` must contain zero empty `logger.<level>()` calls."""
    from check_no_empty_logger_calls import find_offenders

    offenders = find_offenders([REPO_ROOT / "wicked_zerg_challenger"])
    assert not offenders, (
        "Empty logger() calls re-introduced (print→logger migration regression):\n"
        + "\n".join(f"  {p}:{ln}: {line}" for p, ln, line in offenders[:20])
    )
