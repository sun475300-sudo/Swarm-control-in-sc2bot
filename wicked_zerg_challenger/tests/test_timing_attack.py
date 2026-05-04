# -*- coding: utf-8 -*-
"""Unit tests for AttackPlan timing helpers in timing_attack.py."""

from __future__ import annotations

import os
import sys

# Add parent directory to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from timing_attack import AttackPlan, AttackPhase, TimingWindow


def _make_plan(start_time: float = 100.0, max_time: float = 60.0) -> AttackPlan:
    window = TimingWindow(
        name="roach-timing",
        min_supply=20,
        required_units={"roach": 10},
        max_time=max_time,
    )
    return AttackPlan(window, start_time=start_time)


def test_duration_is_zero_at_start():
    plan = _make_plan(start_time=100.0)
    assert plan.duration == 0.0
    assert plan.is_timed_out() is False


def test_duration_advances_with_update():
    plan = _make_plan(start_time=100.0)
    plan.update(115.5)
    assert plan.duration == 15.5
    assert plan.is_timed_out() is False


def test_duration_clamped_to_zero_for_past_time():
    plan = _make_plan(start_time=100.0)
    plan.update(95.0)  # earlier than start (e.g. clock anomaly)
    assert plan.duration == 0.0


def test_is_timed_out_when_max_time_exceeded():
    plan = _make_plan(start_time=100.0, max_time=60.0)
    plan.update(170.0)  # 70s elapsed > 60s max
    assert plan.duration == 70.0
    assert plan.is_timed_out() is True


def test_is_timed_out_disabled_when_max_time_zero():
    plan = _make_plan(start_time=100.0, max_time=0.0)
    plan.update(10_000.0)
    assert plan.duration > 0.0
    assert plan.is_timed_out() is False


def test_is_successful_requires_army_at_start_and_kills():
    plan = _make_plan()
    # No army at start → not successful regardless of kills
    plan.army_supply_at_start = 0
    plan.enemies_killed = 5
    assert plan.is_successful() is False

    # With army and low loss + kills → successful
    plan.army_supply_at_start = 20
    plan.units_lost = 4  # 20% loss
    plan.enemies_killed = 3
    assert plan.is_successful() is True

    # High loss → not successful
    plan.units_lost = 8  # 40% loss
    assert plan.is_successful() is False


def test_phase_starts_as_launching():
    plan = _make_plan()
    assert plan.phase == AttackPhase.LAUNCHING
