"""Regression tests for the combat-timing constants used by CombatManager.

These pin the named constants that combat_manager.py reads at runtime so
intentional tuning shows up in a diff and accidental drift is caught.

Constants live in wicked_zerg_challenger.game_config.GameConfig and are
re-declared as a fallback class (_CombatTimings) inside combat_manager.py.
We assert both surfaces stay in sync with the deployed values.
"""

from __future__ import annotations

import importlib

import pytest


def _load_game_config():
    try:
        return importlib.import_module("wicked_zerg_challenger.game_config")
    except ImportError:
        pytest.skip("wicked_zerg_challenger.game_config not importable in this env")


def _load_combat_manager_constants():
    try:
        return importlib.import_module(
            "wicked_zerg_challenger.combat_manager"
        )._CombatTimings
    except (ImportError, AttributeError):
        pytest.skip("combat_manager._CombatTimings not available (sc2 dep missing)")


class TestCombatTimingWindows:
    """Game-time windows (seconds) that gate each combat task."""

    def test_early_harass_window(self):
        gc = _load_game_config()
        assert gc.config.EARLY_HARASS_WINDOW_START == 60
        assert gc.config.EARLY_HARASS_WINDOW_END == 420
        assert gc.config.EARLY_HARASS_MIN_LINGS == 6
        assert gc.config.EARLY_HARASS_MAX_LINGS == 24

    def test_early_pressure_window(self):
        gc = _load_game_config()
        assert gc.config.EARLY_PRESSURE_WINDOW_START == 180
        assert gc.config.EARLY_PRESSURE_WINDOW_END == 270
        assert gc.config.EARLY_PRESSURE_MIN_LINGS == 4

    def test_mid_timing_window(self):
        gc = _load_game_config()
        assert gc.config.MID_TIMING_WINDOW_START == 300
        assert gc.config.MID_TIMING_WINDOW_END == 480
        assert gc.config.MID_TIMING_MIN_ROACHES == 5
        assert gc.config.MID_TIMING_MIN_LINGS == 12
        assert gc.config.MID_TIMING_MIN_BANELINGS == 4

    def test_major_timing_window(self):
        gc = _load_game_config()
        assert gc.config.MAJOR_TIMING_WINDOW_START == 600
        assert gc.config.MAJOR_TIMING_WINDOW_END == 900
        assert gc.config.MAJOR_TIMING_MIN_ARMY_SUPPLY == 40

    def test_windows_are_monotonic(self):
        """Sanity: each successive window starts after the previous one starts."""
        gc = _load_game_config()
        c = gc.config
        starts = [
            c.EARLY_HARASS_WINDOW_START,
            c.EARLY_PRESSURE_WINDOW_START,
            c.MID_TIMING_WINDOW_START,
            c.MAJOR_TIMING_WINDOW_START,
        ]
        assert starts == sorted(starts), f"timing window starts not monotonic: {starts}"

    def test_each_window_has_positive_duration(self):
        gc = _load_game_config()
        c = gc.config
        for start, end, name in [
            (c.EARLY_HARASS_WINDOW_START, c.EARLY_HARASS_WINDOW_END, "early_harass"),
            (c.EARLY_PRESSURE_WINDOW_START, c.EARLY_PRESSURE_WINDOW_END, "early_pressure"),
            (c.MID_TIMING_WINDOW_START, c.MID_TIMING_WINDOW_END, "mid_timing"),
            (c.MAJOR_TIMING_WINDOW_START, c.MAJOR_TIMING_WINDOW_END, "major_timing"),
        ]:
            assert end > start, f"{name} window is non-positive: [{start}, {end}]"


class TestCombatPriorities:
    def test_base_defense_outranks_attacks(self):
        gc = _load_game_config()
        c = gc.config
        assert c.PRIORITY_BASE_DEFENSE > c.PRIORITY_MAIN_ATTACK_DEFAULT
        assert c.PRIORITY_BASE_DEFENSE > c.PRIORITY_EARLY_HARASS
        assert c.PRIORITY_BASE_DEFENSE > c.PRIORITY_MID_TIMING

    def test_strategy_boost_increases_harass_priority(self):
        gc = _load_game_config()
        c = gc.config
        assert c.PRIORITY_EARLY_HARASS_STRATEGY > c.PRIORITY_EARLY_HARASS

    def test_aggressive_mode_lowers_base_defense(self):
        gc = _load_game_config()
        c = gc.config
        assert c.PRIORITY_BASE_DEFENSE_AGGRESSIVE < c.PRIORITY_BASE_DEFENSE
        assert c.PRIORITY_BASE_DEFENSE_ALL_IN < c.PRIORITY_BASE_DEFENSE_AGGRESSIVE

    def test_main_attack_aggressive_outranks_harass(self):
        gc = _load_game_config()
        c = gc.config
        assert c.PRIORITY_MAIN_ATTACK_AGGRESSIVE > c.PRIORITY_EARLY_HARASS_STRATEGY


class TestCombatManagerFallback:
    """combat_manager._CombatTimings is the safety net when game_config is missing."""

    def test_fallback_matches_config(self):
        gc = _load_game_config()
        fb = _load_combat_manager_constants()
        for name in [
            "EARLY_HARASS_WINDOW_START",
            "EARLY_HARASS_WINDOW_END",
            "EARLY_HARASS_MIN_LINGS",
            "EARLY_HARASS_MAX_LINGS",
            "EARLY_PRESSURE_WINDOW_START",
            "EARLY_PRESSURE_WINDOW_END",
            "EARLY_PRESSURE_MIN_LINGS",
            "MID_TIMING_WINDOW_START",
            "MID_TIMING_WINDOW_END",
            "MID_TIMING_MIN_ROACHES",
            "MID_TIMING_MIN_LINGS",
            "MID_TIMING_MIN_BANELINGS",
            "MAJOR_TIMING_WINDOW_START",
            "MAJOR_TIMING_WINDOW_END",
            "MAJOR_TIMING_MIN_ARMY_SUPPLY",
            "PRIORITY_BASE_DEFENSE",
            "PRIORITY_MAIN_ATTACK_DEFAULT",
            "PRIORITY_MAIN_ATTACK_AGGRESSIVE",
            "PRIORITY_BASE_DEFENSE_AGGRESSIVE",
            "PRIORITY_BASE_DEFENSE_ALL_IN",
            "PRIORITY_WORKER_HARASS_ALL_IN",
            "PRIORITY_COMPLETE_DESTRUCTION",
            "PRIORITY_KILL_SQUAD",
            "PRIORITY_EARLY_HARASS",
            "PRIORITY_EARLY_HARASS_STRATEGY",
            "PRIORITY_EARLY_PRESSURE",
            "PRIORITY_MID_TIMING",
            "PRIORITY_MAJOR_TIMING",
        ]:
            assert getattr(gc.config, name) == getattr(fb, name), (
                f"combat_manager._CombatTimings.{name} "
                f"({getattr(fb, name)}) != GameConfig.{name} ({getattr(gc.config, name)})"
            )
