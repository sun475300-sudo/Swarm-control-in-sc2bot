# -*- coding: utf-8 -*-
"""Test configuration - runs before test collection."""

import os

# Fix protobuf compatibility with sc2 library (s2clientprotocol)
os.environ["PROTOCOL_BUFFERS_PYTHON_IMPLEMENTATION"] = "python"

try:
    import sc2  # noqa: F401

    _SC2_AVAILABLE = True
except ImportError:
    _SC2_AVAILABLE = False


def pytest_ignore_collect(collection_path, config):
    """Ignore test modules whose static import chain requires `sc2` when it is
    unavailable in the environment. Without this, `pytest` aborts the whole
    suite with a collection error."""
    if _SC2_AVAILABLE:
        return False
    path_str = str(collection_path)
    if not path_str.endswith(".py"):
        return False
    try:
        with open(path_str, encoding="utf-8", errors="ignore") as f:
            src = f.read()
    except OSError:
        return False
    if "from sc2" in src or "import sc2" in src:
        return True
    # Transitively-imported modules that themselves require sc2
    return "from run_mass_test" in src or "import run_mass_test" in src
