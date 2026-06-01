# -*- coding: utf-8 -*-
"""Test configuration - runs before test collection."""

import os
import sys
from pathlib import Path

# Fix protobuf compatibility with sc2 library (s2clientprotocol)
os.environ["PROTOCOL_BUFFERS_PYTHON_IMPLEMENTATION"] = "python"

# Load the offline sc2 stub if the real library isn't installed. The stub
# lives under <repo>/tests/_sc2_stub and is shared with the root test suite.
try:
    import sc2  # noqa: F401
except ImportError:
    _STUB_ROOT = Path(__file__).resolve().parents[2] / "tests" / "_sc2_stub"
    if _STUB_ROOT.exists() and str(_STUB_ROOT) not in sys.path:
        sys.path.insert(0, str(_STUB_ROOT))
