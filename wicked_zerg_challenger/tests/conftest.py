# -*- coding: utf-8 -*-
"""Test configuration - runs before test collection.

Skips collection of any test module that requires the optional ``sc2`` library
when it is not installed in the current environment, allowing the rest of the
suite (which doesn't need a live SC2 install) to run cleanly.
"""

import glob
import importlib
import os
import sys

# Fix protobuf compatibility with sc2 library (s2clientprotocol)
os.environ["PROTOCOL_BUFFERS_PYTHON_IMPLEMENTATION"] = "python"

# Ensure the project root is on sys.path so root-level packages (e.g.
# ``scripts.meta_adapter``) resolve before the in-package ``wicked_zerg_challenger/scripts``
# namespace fragment that gets added by some sibling tests.
_PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
if _PROJECT_ROOT not in sys.path:
    sys.path.insert(0, _PROJECT_ROOT)

# Invalidate any cached ``scripts`` namespace package so freshly added paths
# from earlier-collected tests don't shadow the project root one.
if "scripts" in sys.modules:
    del sys.modules["scripts"]


def _module_available(name: str) -> bool:
    try:
        importlib.import_module(name)
        return True
    except Exception:
        return False


# Mapping of import marker -> probe module name. If the probe is missing we
# treat any test that uses that marker as optional and skip collection.
_OPTIONAL_DEPENDENCY_PROBES = {
    "sc2": "sc2.ids.unit_typeid",
    "numpy": "numpy",
    "torch": "torch",
    "pandas": "pandas",
    "tensorflow": "tensorflow",
    "stable_baselines3": "stable_baselines3",
    "gym": "gym",
    "gymnasium": "gymnasium",
}


def _missing_markers() -> set[str]:
    return {
        marker
        for marker, probe in _OPTIONAL_DEPENDENCY_PROBES.items()
        if not _module_available(probe)
    }


def _scan_dependent_tests(markers: set[str]):
    """Return module filenames that import any unavailable optional dep."""
    if not markers:
        return []
    here = os.path.dirname(os.path.abspath(__file__))
    needles = []
    for m in markers:
        needles.extend((f"from {m}", f"import {m}", f".{m}", f"{m}_env", f"{m}_bot"))
    # Test modules that pull in sc2 transitively via project modules.
    transitive_sc2_modules = {
        "test_blackboard.py",  # imports `blackboard` which imports sc2
        "test_sprint8_qa.py",  # imports `run_mass_test` which imports sc2
    }
    skipped = []
    for path in glob.glob(os.path.join(here, "test_*.py")):
        name = os.path.basename(path)
        if "sc2" in markers and name in transitive_sc2_modules:
            skipped.append(name)
            continue
        try:
            with open(path, "r", encoding="utf-8", errors="ignore") as f:
                source = f.read()
        except OSError:
            continue
        if any(n in source for n in needles):
            skipped.append(name)
    return skipped


# When optional dependencies are missing, instruct pytest to ignore the
# test modules that need them. ``collect_ignore`` is consulted by pytest
# before importing tests, so this avoids ImportError noise.
collect_ignore = _scan_dependent_tests(_missing_markers())
