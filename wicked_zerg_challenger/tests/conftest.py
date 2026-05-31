# -*- coding: utf-8 -*-
"""Test configuration - runs before test collection.

* Sets protobuf to the pure-python impl so the sc2 library protocol bindings
  load on systems where the C++ extension was compiled against a different
  protobuf version.
* Installs lightweight sc2 stub modules so tests can be collected even when
  the real `burnysc2` package isn't installed.
"""

import os
import sys
from pathlib import Path

# Fix protobuf compatibility with sc2 library (s2clientprotocol)
os.environ.setdefault("PROTOCOL_BUFFERS_PYTHON_IMPLEMENTATION", "python")

# Ensure the bot package and the repo-root tests directory are importable.
# Order matters: repo root must outrank the bot dir so that
# ``scripts.ladder_tracker`` resolves to the root ``scripts/`` package
# rather than the bot's own (unrelated) ``scripts/`` directory.
_BOT_DIR = Path(__file__).resolve().parent.parent
_REPO_ROOT = _BOT_DIR.parent
_ROOT_TESTS = _REPO_ROOT / "tests"

# Add in reverse priority — last insert wins position 0.
for path in (_BOT_DIR, _ROOT_TESTS, _REPO_ROOT):
    p = str(path)
    if p in sys.path:
        sys.path.remove(p)
    sys.path.insert(0, p)

def _scrub_wrong_scripts_cache():
    """Drop a wrongly-cached ``scripts`` package before wicked tests run.

    Earlier root tests can prime ``sys.modules['scripts']`` to point at
    ``wicked_zerg_challenger/local_training/scripts/`` (a regular package
    with an ``__init__.py``). That caches the wrong path and shadows the
    repo-root ``scripts/`` namespace, breaking imports like
    ``from scripts.ladder_tracker import LadderTracker``.
    """
    cached = sys.modules.get("scripts")
    if cached is None:
        return
    expected = str(_REPO_ROOT / "scripts")
    if expected in list(getattr(cached, "__path__", ())):
        return
    for key in [k for k in sys.modules if k == "scripts" or k.startswith("scripts.")]:
        sys.modules.pop(key, None)


_scrub_wrong_scripts_cache()


def pytest_collectstart(collector):
    """Re-scrub before each wicked-test collection in case a later module
    primed the cache between conftest load and collection."""
    if str(_BOT_DIR) in str(getattr(collector, "fspath", "")):
        _scrub_wrong_scripts_cache()

# Install sc2 stub modules (no-op if real sc2 already imported).
try:
    from _sc2_stub import install as _install_sc2_stubs

    _install_sc2_stubs()
except ImportError:
    pass
