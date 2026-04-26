#!/usr/bin/env python3
"""Smoke-test that every Python module under `wicked_zerg_challenger/` imports.

Run with the repo root as the working directory:

    python scripts/smoke_imports.py

Exit code 0 if every top-level module imports cleanly, 1 otherwise.
"""
from __future__ import annotations

import importlib
import os
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent


def main() -> int:
    sys.path.insert(0, str(REPO_ROOT))
    sys.path.insert(0, str(REPO_ROOT / "tests"))
    # Pull in the lightweight sc2 stub so modules guarded with
    # `from sc2.* import ...` still load when python-sc2 isn't installed.
    from tests import conftest  # noqa: F401

    bot_dir = REPO_ROOT / "wicked_zerg_challenger"
    failures: list[tuple[str, str, str]] = []
    ok = 0

    for fname in sorted(os.listdir(bot_dir)):
        if not fname.endswith(".py") or fname.startswith("__"):
            continue
        mod = "wicked_zerg_challenger." + fname[:-3]
        try:
            importlib.import_module(mod)
            ok += 1
        except Exception as exc:  # noqa: BLE001 - we want every failure
            short = str(exc).split("\n", 1)[0][:140]
            failures.append((mod, type(exc).__name__, short))

    print(f"OK: {ok}, FAILED: {len(failures)}")
    for mod, etype, msg in failures:
        print(f"  {mod}: [{etype}] {msg}")
    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(main())
