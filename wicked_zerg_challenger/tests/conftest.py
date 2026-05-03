# -*- coding: utf-8 -*-
"""Test configuration - runs before test collection."""

import importlib.util
import os

# Fix protobuf compatibility with sc2 library (s2clientprotocol)
os.environ["PROTOCOL_BUFFERS_PYTHON_IMPLEMENTATION"] = "python"


# Tests that import sc2 at module load time. When burnysc2 isn't installed
# (CI without the SC2 client) these would otherwise fail at collection and
# block the rest of the suite.
_SC2_DEPENDENT = {
    "test_combat_manager",
    "test_difficulty_progression",
    "test_economy_manager",
    "test_opponent_modeling",
    "test_production_resilience",
}


def _sc2_available() -> bool:
    return importlib.util.find_spec("sc2") is not None


def pytest_ignore_collect(collection_path, config):
    """Skip sc2-dependent test files when sc2 isn't importable."""
    if _sc2_available():
        return None
    stem = collection_path.stem if hasattr(collection_path, "stem") else ""
    if stem in _SC2_DEPENDENT:
        return True
    return None
