# -*- coding: utf-8 -*-
"""
sc2 Import Fallback Contract Test
=================================

Verifies that production modules can be imported in environments where the
``sc2`` (burnysc2) package is unavailable. The hardened modules wrap the
``from sc2.* import ...`` statement in ``try/except ImportError`` and provide
stub classes so the module body still loads.

This test prevents regression: if someone removes the fallback, the import
fails here. Run with ``sc2`` ABSENT from ``sys.modules`` to exercise the
ImportError path.
"""

from __future__ import annotations

import importlib
import os
import sys
from typing import List, Tuple

import pytest

# Ensure wicked_zerg_challenger/ is importable, mirroring sibling tests.
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

# (module name, attributes that must be importable / referenced as defaults)
HARDENED_MODULES: List[Tuple[str, List[str]]] = [
    ("difficulty_progression", []),
    ("game_statistics", []),
    ("idle_unit_manager", []),
    ("defeat_detection", []),
    ("overlord_safety_manager", []),
    ("base_destruction_coordinator", []),
    ("building_coordination", []),
    ("building_placement_helper", ["CREEP_REQUIRED", "CREEP_NOT_REQUIRED"]),
    ("building_destroyer", []),
    ("tech_coordinator", []),
    ("worker_combat_system", []),
    ("map_memory_system", []),
    ("battle_preparation_system", []),
    ("comprehensive_unit_abilities", []),
    ("destructible_awareness_system", []),
    ("hive_tech_maximizer", []),
    ("strict_upgrade_priority", []),
]


def _purge_sc2_modules() -> dict:
    """Remove cached sc2 entries from sys.modules and shadow them with None
    so a fresh ``from sc2.* import`` raises ImportError. Returns a snapshot
    that ``_restore_sc2_modules`` can use."""
    snapshot: dict = {}
    for name in list(sys.modules):
        if name == "sc2" or name.startswith("sc2."):
            snapshot[name] = sys.modules[name]
            sys.modules[name] = None  # type: ignore[assignment]
    return snapshot


def _restore_sc2_modules(snapshot: dict) -> None:
    for name in list(sys.modules):
        if name == "sc2" or name.startswith("sc2."):
            del sys.modules[name]
    for name, mod in snapshot.items():
        if mod is not None:
            sys.modules[name] = mod


@pytest.mark.parametrize("module_name,required_attrs", HARDENED_MODULES)
def test_imports_without_sc2(module_name: str, required_attrs: List[str]):
    """Each hardened module must import cleanly even when sc2 is missing."""
    snapshot = _purge_sc2_modules()
    # Drop any cached version of the module under test so it re-evaluates the
    # import path with sc2 shadowed.
    if module_name in sys.modules:
        del sys.modules[module_name]
    try:
        mod = importlib.import_module(module_name)
        for attr in required_attrs:
            assert hasattr(mod, attr), (
                f"{module_name} missing required attribute {attr!r} "
                f"after sc2-less import"
            )
    finally:
        # Drop the just-imported (stub-backed) module so subsequent tests in
        # the same session re-import it against the real sc2 if available.
        if module_name in sys.modules:
            del sys.modules[module_name]
        _restore_sc2_modules(snapshot)
