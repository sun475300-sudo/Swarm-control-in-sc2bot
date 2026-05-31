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
_BOT_DIR = Path(__file__).resolve().parent.parent
_REPO_ROOT = _BOT_DIR.parent
_ROOT_TESTS = _REPO_ROOT / "tests"

for path in (_BOT_DIR, _REPO_ROOT, _ROOT_TESTS):
    p = str(path)
    if p not in sys.path:
        sys.path.insert(0, p)

# Install sc2 stub modules (no-op if real sc2 already imported).
try:
    from _sc2_stub import install as _install_sc2_stubs

    _install_sc2_stubs()
except ImportError:
    pass
