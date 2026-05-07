# -*- coding: utf-8 -*-
"""Combat module — named constants.

Centralizes the magic numbers that previously lived inline across
``combat_manager.py`` so that tuning is a single-file change and so the
units are obvious at the call site.

A SC2 game tick (``iteration``) is roughly 22.4 frames per real-time
second on Faster game speed, so ``iteration`` math here is in *frames*,
not seconds. ``game_time`` (in seconds) is used for phase thresholds.
"""
from __future__ import annotations

# ---------------------------------------------------------------------
# Tick cadences (denominated in `iteration` frames)
# ---------------------------------------------------------------------

# Approximately once per second on Faster — used for periodic combat
# checks (Roach-rush timing, retreat evaluation, etc.).
COMBAT_TICK_FRAMES: int = 22

# Logging cadence — fires roughly every ~2.2 game-seconds. Used to
# rate-limit user-facing log lines so the chat/console doesn't flood.
LOG_CADENCE_FRAMES: int = 50

# Slower logging cadence — used for high-noise events.
LOG_CADENCE_LONG_FRAMES: int = 100

# ---------------------------------------------------------------------
# Game-time phase thresholds (seconds)
# ---------------------------------------------------------------------


class CombatPhaseSeconds:
    """Game-time thresholds (seconds) referenced by combat triggers."""

    EARLY_HARASS_START: int = 60      # 1:00 — earliest zergling harass
    EARLY_PRESSURE_START: int = 180   # 3:00 — early ground pressure window
    EARLY_PRESSURE_END: int = 270     # 4:30 — end of early pressure
    MID_TIMING_START: int = 300       # 5:00 — mid-game timing attack window
    EARLY_HARASS_END: int = 420       # 7:00 — end of early harass window
    MID_TIMING_END: int = 480         # 8:00 — end of mid-game timing window
    MAJOR_TIMING_START: int = 600     # 10:00 — major timing attack window
    MAJOR_TIMING_END: int = 900       # 15:00 — end of major timing window


# ---------------------------------------------------------------------
# Unit-count thresholds for composition-based triggers
# ---------------------------------------------------------------------


class CombatCompositionThresholds:
    """Minimum unit counts required for various combat triggers."""

    EARLY_HARASS_LINGS_MIN: int = 6
    EARLY_HARASS_LINGS_MAX: int = 24
    EARLY_PRESSURE_LINGS_MIN: int = 4
    MID_TIMING_LINGS_MIN: int = 12
    MID_TIMING_ROACHES_MIN: int = 5
    MID_TIMING_BANELINGS_MIN: int = 4
    MAJOR_TIMING_SUPPLY_MIN: int = 40


__all__ = [
    "COMBAT_TICK_FRAMES",
    "LOG_CADENCE_FRAMES",
    "LOG_CADENCE_LONG_FRAMES",
    "CombatPhaseSeconds",
    "CombatCompositionThresholds",
]
