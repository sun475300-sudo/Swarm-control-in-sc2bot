# -*- coding: utf-8 -*-
"""Test configuration - runs before test collection."""

import importlib
import os
import sys
from pathlib import Path

# Fix protobuf compatibility with sc2 library (s2clientprotocol)
os.environ["PROTOCOL_BUFFERS_PYTHON_IMPLEMENTATION"] = "python"


def _ensure_sc2_stub() -> None:
    """If burnysc2 is not installed, expose the local ``_sc2_stub`` package as ``sc2``.

    This lets tests that ``import sc2.ids.unit_typeid`` etc. collect on machines
    where the upstream ``mpyq`` wheel cannot be built.
    """
    try:
        importlib.import_module("sc2.ids.unit_typeid")
        return
    except ImportError:
        pass

    stub_root = Path(__file__).parent / "_sc2_stub"
    if not stub_root.exists():
        return
    sys.path.insert(0, str(stub_root))


_ensure_sc2_stub()
