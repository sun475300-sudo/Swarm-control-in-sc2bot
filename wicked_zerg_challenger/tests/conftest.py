# -*- coding: utf-8 -*-
"""Test configuration - runs before test collection."""

import os
import sys
from pathlib import Path

os.environ["PROTOCOL_BUFFERS_PYTHON_IMPLEMENTATION"] = "python"

_PKG_ROOT = Path(__file__).resolve().parent.parent
if str(_PKG_ROOT) not in sys.path:
    sys.path.insert(0, str(_PKG_ROOT))

try:  # pragma: no cover - real burnysc2 wins when present
    import sc2  # noqa: F401
except ImportError:
    _STUB_DIR = Path(__file__).resolve().parent
    if str(_STUB_DIR) not in sys.path:
        sys.path.insert(0, str(_STUB_DIR))
    import _sc2_stub  # noqa: E402

    _sc2_stub.install_into_sys_modules()
