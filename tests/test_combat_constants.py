"""Sanity tests for wicked_zerg_challenger.combat.constants.

Locks down the named-constant values so accidental edits surface in CI.
"""
from __future__ import annotations

import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
WZC_ROOT = PROJECT_ROOT / "wicked_zerg_challenger"
for p in (str(PROJECT_ROOT), str(WZC_ROOT)):
    if p not in sys.path:
        sys.path.insert(0, p)

from combat.constants import (  # noqa: E402
    COMBAT_TICK_FRAMES,
    LOG_CADENCE_FRAMES,
    LOG_CADENCE_LONG_FRAMES,
    CombatCompositionThresholds,
    CombatPhaseSeconds,
)


def test_tick_cadence_values() -> None:
    assert COMBAT_TICK_FRAMES == 22
    assert LOG_CADENCE_FRAMES == 50
    assert LOG_CADENCE_LONG_FRAMES == 100


def test_combat_phase_ordering() -> None:
    p = CombatPhaseSeconds
    # Phases must be monotonically increasing
    assert p.EARLY_HARASS_START < p.EARLY_PRESSURE_START
    assert p.EARLY_PRESSURE_START < p.EARLY_PRESSURE_END
    assert p.EARLY_PRESSURE_END < p.MID_TIMING_START
    assert p.MID_TIMING_START < p.EARLY_HARASS_END
    assert p.EARLY_HARASS_END < p.MID_TIMING_END
    assert p.MID_TIMING_END < p.MAJOR_TIMING_START
    assert p.MAJOR_TIMING_START < p.MAJOR_TIMING_END


def test_combat_phase_locked_values() -> None:
    p = CombatPhaseSeconds
    assert (p.EARLY_HARASS_START, p.EARLY_HARASS_END) == (60, 420)
    assert (p.EARLY_PRESSURE_START, p.EARLY_PRESSURE_END) == (180, 270)
    assert (p.MID_TIMING_START, p.MID_TIMING_END) == (300, 480)
    assert (p.MAJOR_TIMING_START, p.MAJOR_TIMING_END) == (600, 900)


def test_composition_thresholds() -> None:
    c = CombatCompositionThresholds
    assert c.EARLY_HARASS_LINGS_MIN == 6
    assert c.EARLY_HARASS_LINGS_MAX == 24
    assert c.EARLY_HARASS_LINGS_MIN < c.EARLY_HARASS_LINGS_MAX
    assert c.EARLY_PRESSURE_LINGS_MIN == 4
    assert c.MID_TIMING_LINGS_MIN == 12
    assert c.MID_TIMING_ROACHES_MIN == 5
    assert c.MID_TIMING_BANELINGS_MIN == 4
    assert c.MAJOR_TIMING_SUPPLY_MIN == 40
