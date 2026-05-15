# -*- coding: utf-8 -*-
"""Test configuration - runs before test collection.

Also installs a stub ``sc2`` package on sys.path when the real
python-sc2 library is unavailable. This allows tests that import
``from sc2.ids.unit_typeid import UnitTypeId`` (and similar) to be
collected and executed in CI environments without the real library.
"""

import os
import sys

# Fix protobuf compatibility with sc2 library (s2clientprotocol)
os.environ["PROTOCOL_BUFFERS_PYTHON_IMPLEMENTATION"] = "python"


def _ensure_sc2_stub_available() -> None:
    try:
        import sc2  # noqa: F401
        return
    except Exception:
        pass
    stub_dir = os.path.join(os.path.dirname(__file__), "sc2_stub")
    if os.path.isdir(stub_dir) and stub_dir not in sys.path:
        sys.path.insert(0, stub_dir)


_ensure_sc2_stub_available()
