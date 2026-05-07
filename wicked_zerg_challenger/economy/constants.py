# -*- coding: utf-8 -*-
"""Economy module — named constants.

Centralizes economy-side magic numbers from ``economy_manager.py`` so
that tuning sits in one place and the units are obvious at the call
site.
"""
from __future__ import annotations

from typing import Dict


class EconomyDefaults:
    """Default economy thresholds used when no game_config is loaded."""

    # Mineral surplus that triggers a macro hatchery (no-config fallback).
    MACRO_HATCHERY_MINERAL_THRESHOLD: int = 600
    # Phase 16-tuned threshold when game_config IS available.
    MACRO_HATCHERY_MINERAL_THRESHOLD_TUNED: int = 550
    # Larva count below which macro hatchery becomes desirable.
    MACRO_HATCHERY_LARVA_THRESHOLD: int = 3

    # Macro-hatch decision is checked once every N frames.
    MACRO_HATCH_CHECK_INTERVAL_FRAMES: int = 50

    # Cooldown (seconds) between expansion attempts to prevent duplicate
    # build orders from racing.
    EXPANSION_COOLDOWN_SECONDS: float = 3.0


# ---------------------------------------------------------------------
# Race-keyed gas timing (seconds)
# ---------------------------------------------------------------------
#
# When to take first gas vs. opponent race. Earlier gas trades drone
# count for tech access — Protoss tends to need an early counter, Zerg
# tends to drone first.

RACE_GAS_TIMING_SECONDS: Dict[str, int] = {
    "Terran": 90,    # 1:30 — balanced timing
    "Protoss": 75,   # 1:15 — earlier in case of all-in
    "Zerg": 105,     # 1:45 — later, drone-pumping priority
    "Random": 90,    # default to Terran timing
    "Unknown": 90,   # before scouting reveals race
}


class GasBoostDefaults:
    """Tunables for the gas-boost (rush-tech) mode."""

    DURATION_SECONDS: int = 120  # 2 minutes


__all__ = [
    "EconomyDefaults",
    "RACE_GAS_TIMING_SECONDS",
    "GasBoostDefaults",
]
