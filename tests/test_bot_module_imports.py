# -*- coding: utf-8 -*-
"""Smoke-test that every top-level module under ``wicked_zerg_challenger/``
imports without raising. Catches the bug class where:

* a module performs side-effects at import time (e.g. ``sys.exit``)
* a refactor leaves a dangling ``from X import Y`` for a removed name

Modules that hard-require an unavailable dependency (e.g. ``psutil``) are
allowed to fail with ``ModuleNotFoundError`` for that *specific* missing
package, but every other failure mode is a regression.
"""

from __future__ import annotations

import importlib
import os
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
BOT_DIR = REPO_ROOT / "wicked_zerg_challenger"

# Optional 3rd-party packages: a missing one is environmental, not a bug.
ALLOWED_MISSING = {"psutil", "torch", "yaml", "google", "ray"}


def _is_env_failure(exc: BaseException) -> bool:
    if isinstance(exc, ModuleNotFoundError):
        head = (exc.name or "").split(".", 1)[0]
        return head in ALLOWED_MISSING
    return False


def test_every_bot_core_module_imports() -> None:
    failures: list[tuple[str, str, str]] = []
    for fname in sorted(os.listdir(BOT_DIR)):
        if not fname.endswith(".py") or fname.startswith("__"):
            continue
        mod = "wicked_zerg_challenger." + fname[:-3]
        try:
            importlib.import_module(mod)
        except SystemExit as exc:  # noqa: PERF203
            failures.append((mod, "SystemExit", f"sys.exit({exc.code})"))
        except BaseException as exc:  # noqa: BLE001
            if _is_env_failure(exc):
                continue
            failures.append((mod, type(exc).__name__,
                             str(exc).split("\n", 1)[0][:160]))

    assert not failures, (
        "Bot-core module(s) fail to import:\n"
        + "\n".join(f"  {m}: [{t}] {e}" for m, t, e in failures)
    )
