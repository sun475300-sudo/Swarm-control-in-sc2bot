"""Deterministic tests for HarassmentMetrics (P1.2)."""
from __future__ import annotations

import math

import pytest

from wicked_zerg_challenger.combat.harassment_metrics import (
    HarassmentMetrics,
    distance2d,
    is_harass_unit,
    is_worker,
)


# ---------------------------------------------------------------------
# Pure functions
# ---------------------------------------------------------------------


class TestClassifiers:
    @pytest.mark.parametrize("name", ["SCV", "PROBE", "DRONE", "MULE", "scv"])
    def test_is_worker_true(self, name):
        assert is_worker(name) is True

    @pytest.mark.parametrize("name", ["ZERGLING", "MARINE", "STALKER", ""])
    def test_is_worker_false(self, name):
        assert is_worker(name) is False

    @pytest.mark.parametrize("name", ["ZERGLING", "MUTALISK", "BANELING", "ROACH"])
    def test_is_harass_true(self, name):
        assert is_harass_unit(name) is True

    def test_is_harass_false_for_worker(self):
        assert is_harass_unit("DRONE") is False


class TestDistance:
    def test_zero(self):
        assert distance2d((0, 0), (0, 0)) == 0

    def test_pythag_345(self):
        assert distance2d((0, 0), (3, 4)) == pytest.approx(5.0)


# ---------------------------------------------------------------------
# Penetration
# ---------------------------------------------------------------------


class TestPenetration:
    def test_penetration_flag_flips_on_first_close_approach(self):
        m = HarassmentMetrics(enemy_main_position=(100, 100), penetration_radius_m=15)
        # Position 50 units away — no penetration
        m.on_position(1, (50, 50))
        assert m.summary()["penetrations"] == 0.0

        # Position 10 units away — penetration
        m.on_position(1, (95, 100))
        assert m.summary()["penetrations"] == 1.0

    def test_penetration_only_counted_once(self):
        m = HarassmentMetrics(enemy_main_position=(100, 100), penetration_radius_m=15)
        for _ in range(10):
            m.on_position(1, (95, 100))
        assert m.summary()["penetrations"] == 1.0


# ---------------------------------------------------------------------
# Kill tracking
# ---------------------------------------------------------------------


class TestKillTracking:
    def test_worker_killed_by_zergling(self):
        m = HarassmentMetrics(enemy_main_position=(100, 100))
        m.on_unit_died(dead_tag=42, dead_type="SCV",
                       killer_type="ZERGLING", killer_tag=7)
        s = m.summary()
        assert s["workers_killed"] == 1.0
        assert m.episode_for(7).workers_killed == 1

    def test_worker_killed_by_non_harass_does_not_credit(self):
        m = HarassmentMetrics(enemy_main_position=(100, 100))
        # Marine kills a probe — not our harass
        m.on_unit_died(dead_tag=42, dead_type="PROBE", killer_type="MARINE",
                       killer_tag=99)
        assert m.summary()["workers_killed"] == 0.0

    def test_non_worker_death_ignored_for_kill_counter(self):
        m = HarassmentMetrics(enemy_main_position=(100, 100))
        m.on_unit_died(dead_tag=42, dead_type="MARINE",
                       killer_type="ZERGLING", killer_tag=7)
        assert m.summary()["workers_killed"] == 0.0


# ---------------------------------------------------------------------
# Retreat
# ---------------------------------------------------------------------


class TestRetreat:
    def test_retreat_success_flips_when_reaching_own_base(self):
        m = HarassmentMetrics(
            enemy_main_position=(100, 100),
            penetration_radius_m=15,
            retreat_zone_position=(0, 0),
            retreat_zone_radius_m=5,
        )
        # Send unit to enemy main
        m.on_position(1, (95, 100))
        assert m.summary()["retreats_alive"] == 0.0
        # Now return to base
        m.on_position(1, (2, 2))
        assert m.summary()["retreats_alive"] == 1.0

    def test_retreat_after_death_is_impossible(self):
        m = HarassmentMetrics(
            enemy_main_position=(100, 100),
            retreat_zone_position=(0, 0),
        )
        m.on_position(1, (95, 100))
        m.on_unit_died(dead_tag=1, dead_type="ZERGLING")
        # Even if a later position event comes in (bug simulation), no retreat
        m.on_position(1, (0, 0))
        assert m.summary()["retreats_alive"] == 0.0


# ---------------------------------------------------------------------
# Summary sanity
# ---------------------------------------------------------------------


class TestSummary:
    def test_kd_ratio_infinite_when_no_deaths_but_kills(self):
        m = HarassmentMetrics(enemy_main_position=(100, 100))
        m.on_unit_died(dead_tag=42, dead_type="DRONE",
                       killer_type="ZERGLING", killer_tag=1)
        assert math.isinf(m.summary()["kd_ratio"])

    def test_kd_ratio_zero_when_no_kills_no_deaths(self):
        m = HarassmentMetrics(enemy_main_position=(100, 100))
        assert m.summary()["kd_ratio"] == 0.0

    def test_reset_clears_everything(self):
        m = HarassmentMetrics(enemy_main_position=(100, 100))
        m.on_position(1, (95, 100))
        m.on_unit_died(dead_tag=42, dead_type="DRONE",
                       killer_type="ZERGLING", killer_tag=1)
        m.reset()
        s = m.summary()
        assert s["episodes"] == 0
        assert s["workers_killed"] == 0
        assert s["penetrations"] == 0
