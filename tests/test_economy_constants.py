"""Sanity tests for wicked_zerg_challenger.economy.constants.

Locks down economy-side magic-number values so accidental tuning
surfaces in CI rather than silently changing bot behavior.
"""
from __future__ import annotations

import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
WZC_ROOT = PROJECT_ROOT / "wicked_zerg_challenger"
for p in (str(PROJECT_ROOT), str(WZC_ROOT)):
    if p not in sys.path:
        sys.path.insert(0, p)

from economy.constants import (  # noqa: E402
    RACE_GAS_TIMING_SECONDS,
    EconomyDefaults,
    GasBoostDefaults,
)


def test_economy_defaults_locked() -> None:
    d = EconomyDefaults
    assert d.MACRO_HATCHERY_MINERAL_THRESHOLD == 600
    assert d.MACRO_HATCHERY_MINERAL_THRESHOLD_TUNED == 550
    assert d.MACRO_HATCHERY_LARVA_THRESHOLD == 3
    assert d.MACRO_HATCH_CHECK_INTERVAL_FRAMES == 50
    assert d.EXPANSION_COOLDOWN_SECONDS == 3.0


def test_tuned_threshold_is_lower_than_default() -> None:
    """Phase 16 tuning lowers the macro-hatch trigger threshold."""
    assert (
        EconomyDefaults.MACRO_HATCHERY_MINERAL_THRESHOLD_TUNED
        < EconomyDefaults.MACRO_HATCHERY_MINERAL_THRESHOLD
    )


def test_race_gas_timing_keys() -> None:
    expected_races = {"Terran", "Protoss", "Zerg", "Random", "Unknown"}
    assert set(RACE_GAS_TIMING_SECONDS.keys()) == expected_races


def test_race_gas_timing_values() -> None:
    g = RACE_GAS_TIMING_SECONDS
    # Protoss takes gas earliest, Zerg latest
    assert g["Protoss"] < g["Terran"] < g["Zerg"]
    assert g["Random"] == g["Terran"]  # default to Terran timing
    assert g["Unknown"] == g["Terran"]


def test_gas_boost_duration() -> None:
    assert GasBoostDefaults.DURATION_SECONDS == 120
