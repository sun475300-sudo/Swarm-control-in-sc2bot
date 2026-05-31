"""Tests for wicked_zerg_challenger/utils/frame_skip.py."""
from __future__ import annotations

import pytest

from wicked_zerg_challenger.utils.frame_skip import FrameSkipManager


# ---------------------------------------------------------------------------
# Default interval behaviour
# ---------------------------------------------------------------------------

def test_combat_manager_always_runs_outside_combat():
    fsm = FrameSkipManager()
    for it in range(20):
        assert fsm.should_execute("combat_manager", it) is True


def test_economy_manager_runs_every_3_frames_by_default():
    fsm = FrameSkipManager()
    assert fsm.should_execute("economy_manager", 0) is True
    assert fsm.should_execute("economy_manager", 1) is False
    assert fsm.should_execute("economy_manager", 2) is False
    assert fsm.should_execute("economy_manager", 3) is True


def test_unknown_manager_runs_every_frame():
    fsm = FrameSkipManager()
    for it in range(5):
        assert fsm.should_execute("unknown_manager", it) is True


# ---------------------------------------------------------------------------
# Combat mode swaps interval table
# ---------------------------------------------------------------------------

def test_combat_mode_uses_combat_intervals():
    fsm = FrameSkipManager()
    fsm.set_combat_mode(True)
    assert fsm.in_combat is True
    # economy under combat: interval=5
    assert fsm.should_execute("economy_manager", 0) is True
    assert fsm.should_execute("economy_manager", 4) is False
    assert fsm.should_execute("economy_manager", 5) is True


def test_combat_mode_off_restores_default():
    fsm = FrameSkipManager()
    fsm.set_combat_mode(True)
    fsm.set_combat_mode(False)
    assert fsm.in_combat is False
    # economy back to interval=3
    assert fsm.should_execute("economy_manager", 3) is True


# ---------------------------------------------------------------------------
# Overload doubles non-combat intervals
# ---------------------------------------------------------------------------

def test_overload_doubles_interval_for_noncombat():
    fsm = FrameSkipManager()
    fsm.set_overloaded(True)
    # economy default=3 → doubled to 6
    assert fsm.should_execute("economy_manager", 0) is True
    assert fsm.should_execute("economy_manager", 3) is False
    assert fsm.should_execute("economy_manager", 6) is True


def test_overload_does_not_throttle_combat_manager():
    fsm = FrameSkipManager()
    fsm.set_overloaded(True)
    for it in range(20):
        assert fsm.should_execute("combat_manager", it) is True


def test_set_overloaded_coerces_to_bool():
    fsm = FrameSkipManager()
    fsm.set_overloaded(1)  # truthy non-bool
    assert fsm._overloaded is True
    fsm.set_overloaded(0)
    assert fsm._overloaded is False


def test_set_combat_mode_coerces_to_bool():
    fsm = FrameSkipManager()
    fsm.set_combat_mode("yes")
    assert fsm.in_combat is True


# ---------------------------------------------------------------------------
# Defensive: malformed interval entries
# ---------------------------------------------------------------------------

def test_interval_clamped_to_minimum_1(monkeypatch):
    fsm = FrameSkipManager()
    fsm.DEFAULT_INTERVALS = dict(FrameSkipManager.DEFAULT_INTERVALS)
    fsm.DEFAULT_INTERVALS["bogus"] = 0
    # Even with interval=0 in config, should still execute (clamped to 1).
    for it in range(5):
        assert fsm.should_execute("bogus", it) is True
