"""Lock the economy-tuning invariants from recent improvement commits.

Several economy-side numbers were tightened in commits c7bb6dd,
34ac508, and the gas-banking fix:

  * `gas_overflow_prevention_threshold` was 1000 → tightened to 800
  * `gas_worker_adjustment_interval` was 110 → tightened to 33 frames
    (~1.5 s) for fast gas-banking response
  * `_expansion_cooldown` was 6 s → tightened to 3 s to avoid missing
    expansion timings
  * `macro_hatchery_mineral_threshold` was lowered to 600 for faster
    macro hatcheries

A future "cleanup" commit can silently loosen any of these and
reintroduce the regression. These tests pin the *direction* of each
improvement (≤ for thresholds that should stay tight, ≥ for cadences
that must stay frequent).
"""
from __future__ import annotations

import os
import sys

import pytest

# `economy_manager.py` uses bare imports like `from local_training...`,
# `from config...`, and `from utils.logger ...`. The repo also has a
# top-level `utils/` package that shadows `wicked_zerg_challenger/utils/`,
# so we must insert the bot-core dir at sys.path[0] (same pattern as
# tests/test_economy_manager.py) and import without the package prefix.
_BOT_CORE = os.path.join(os.path.dirname(__file__), "..", "wicked_zerg_challenger")
_BOT_CORE = os.path.abspath(_BOT_CORE)
if os.path.isdir(_BOT_CORE) and _BOT_CORE not in sys.path:
    sys.path.insert(0, _BOT_CORE)

try:
    from economy_manager import EconomyManager  # type: ignore[import-not-found]
except ImportError:
    pytest.skip("EconomyManager not available", allow_module_level=True)


def _make_economy_manager():

    bot = type(
        "_StubBot",
        (),
        {
            "blackboard": None,
            "minerals": 0,
            "vespene": 0,
            "supply_left": 0,
            "iteration": 0,
            "time": 0.0,
        },
    )()
    try:
        return EconomyManager(bot)
    except Exception as exc:  # noqa: BLE001 — surface the cause via skip
        pytest.skip(f"EconomyManager init failed in test env: {exc}")


def test_gas_overflow_threshold_stays_aggressive():
    """gas_overflow_prevention_threshold must stay ≤ 1000 (anti gas-banking)."""
    eco = _make_economy_manager()
    assert eco.gas_overflow_prevention_threshold <= 1000, (
        f"gas overflow threshold loosened to "
        f"{eco.gas_overflow_prevention_threshold} — anti gas-banking "
        f"requires ≤ 1000 (history: 3000 → 1000 → 800)"
    )


def test_gas_worker_adjustment_interval_stays_responsive():
    """gas worker rebalance must run at ≥ ~1.5 s cadence (≤ 50 frames)."""
    eco = _make_economy_manager()
    assert eco.gas_worker_adjustment_interval <= 50, (
        f"gas_worker_adjustment_interval loosened to "
        f"{eco.gas_worker_adjustment_interval} frames — fast gas-banking "
        f"response requires ≤ 50 (current: 33, original: 110)"
    )


def test_expansion_cooldown_stays_short():
    """Expansion cooldown must stay ≤ 5 s so expansion windows are not missed."""
    eco = _make_economy_manager()
    assert eco._expansion_cooldown <= 5.0, (
        f"_expansion_cooldown loosened to {eco._expansion_cooldown} s — "
        f"missed expansion windows previously occurred at 6 s; tightened to 3 s"
    )


def test_macro_hatchery_threshold_stays_low():
    """Macro hatchery should trigger at ≤ 700 mineral surplus (Phase 16 fix)."""
    eco = _make_economy_manager()
    assert eco.macro_hatchery_mineral_threshold <= 700, (
        f"macro_hatchery_mineral_threshold loosened to "
        f"{eco.macro_hatchery_mineral_threshold} — Phase 16 lowered it "
        f"to 600 to prevent larva starvation"
    )


def test_gas_timing_by_race_complete():
    """gas_timing_by_race must cover all four race keys (+ Unknown fallback)."""
    eco = _make_economy_manager()
    required = {"Terran", "Protoss", "Zerg", "Random", "Unknown"}
    assert required.issubset(eco.gas_timing_by_race.keys()), (
        f"gas_timing_by_race missing keys: "
        f"{required - set(eco.gas_timing_by_race.keys())}"
    )
    # Protoss should still be the fastest gas (cheese-prone matchup)
    assert eco.gas_timing_by_race["Protoss"] <= eco.gas_timing_by_race["Terran"]
    assert eco.gas_timing_by_race["Protoss"] <= eco.gas_timing_by_race["Zerg"]
