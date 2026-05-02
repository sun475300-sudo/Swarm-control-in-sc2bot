# -*- coding: utf-8 -*-
"""
Regression tests for utils.game_constants

Goal: catch accidental edits to magic numbers that downstream managers rely on
(e.g. 22.4 FPS, gas threshold, transfusion energy, queen inject cooldown).
"""

import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

import pytest
from utils.game_constants import (
    AbilityConstants,
    CombatConstants,
    DebugConstants,
    EconomyConstants,
    GameFrequencies,
    StrategyConstants,
    UnitPriority,
    UpgradeConstants,
    iterations_to_seconds,
    seconds_to_iterations,
)


class TestGameFrequencies:
    def test_fps_matches_sc2_faster_speed(self):
        assert GameFrequencies.GAME_FPS == pytest.approx(22.4)

    def test_every_second_constants_are_monotonic(self):
        # Each successive bucket should be larger than the previous one
        ordered = [
            GameFrequencies.EVERY_HALF_SECOND,
            GameFrequencies.EVERY_SECOND,
            GameFrequencies.EVERY_1_5_SECONDS,
            GameFrequencies.EVERY_2_SECONDS,
            GameFrequencies.EVERY_3_SECONDS,
            GameFrequencies.EVERY_4_SECONDS,
            GameFrequencies.EVERY_5_SECONDS,
            GameFrequencies.EVERY_10_SECONDS,
            GameFrequencies.EVERY_15_SECONDS,
            GameFrequencies.EVERY_30_SECONDS,
            GameFrequencies.EVERY_45_SECONDS,
            GameFrequencies.EVERY_60_SECONDS,
            GameFrequencies.EVERY_2_MINUTES,
            GameFrequencies.EVERY_3_MINUTES,
            GameFrequencies.EVERY_5_MINUTES,
        ]
        assert ordered == sorted(ordered)
        assert all(isinstance(x, int) for x in ordered)

    def test_every_minute_equals_60_seconds(self):
        # 60s @ 22.4fps ≈ 1320, roughly EVERY_60_SECONDS
        expected = int(60 * GameFrequencies.GAME_FPS)
        assert abs(GameFrequencies.EVERY_60_SECONDS - expected) <= 24


class TestEconomyConstants:
    def test_workers_per_base_relationship(self):
        assert (
            EconomyConstants.OPTIMAL_WORKERS_PER_BASE
            < EconomyConstants.MAX_WORKERS_PER_BASE
        )

    def test_gas_thresholds_are_positive(self):
        assert EconomyConstants.GAS_RESERVE_THRESHOLD > 0
        assert EconomyConstants.GAS_WORKER_TRANSITION > 0

    def test_resource_bank_caps_balanced(self):
        # Mineral and gas caps should both be set; stale 0/None would silently
        # disable banking prevention.
        assert EconomyConstants.MAX_MINERAL_BANK > 0
        assert EconomyConstants.MAX_GAS_BANK > 0


class TestCombatConstants:
    def test_health_thresholds_are_ordered(self):
        assert (
            CombatConstants.RETREAT_HP_THRESHOLD
            < CombatConstants.BURROW_HP_THRESHOLD
            < CombatConstants.TRANSFUSION_HP_THRESHOLD
            < CombatConstants.FULL_HP_THRESHOLD
        )

    def test_health_thresholds_in_unit_interval(self):
        for value in [
            CombatConstants.BURROW_HP_THRESHOLD,
            CombatConstants.RETREAT_HP_THRESHOLD,
            CombatConstants.FULL_HP_THRESHOLD,
            CombatConstants.TRANSFUSION_HP_THRESHOLD,
        ]:
            assert 0.0 < value < 1.0

    def test_distance_thresholds_are_ordered(self):
        # Melee should be tighter than detector range, which should be tighter
        # than retreat distance, which should be tighter than base defense.
        assert (
            CombatConstants.MELEE_RANGE
            < CombatConstants.DETECTOR_THREAT_RANGE
            < CombatConstants.RETREAT_DISTANCE
            < CombatConstants.BASE_DEFENSE_RANGE
        )

    def test_min_army_for_attack_reasonable(self):
        assert (
            1 < CombatConstants.MIN_ARMY_FOR_ATTACK < CombatConstants.MIN_ROACH_FOR_RUSH
        )


class TestUpgradeConstants:
    def test_inject_cooldown_matches_sc2_value(self):
        # SC2 Spawn Larva cooldown == 640 frames at 22.4 fps
        expected = 640 / 22.4
        assert UpgradeConstants.INJECT_COOLDOWN == pytest.approx(expected, rel=1e-3)

    def test_transfusion_constants(self):
        assert UpgradeConstants.TRANSFUSION_ENERGY == 50
        assert UpgradeConstants.TRANSFUSION_RANGE == 7

    def test_creep_energy_below_inject(self):
        # Creep tumors should be cheaper than spawn larva, never inverted.
        assert (
            UpgradeConstants.CREEP_ENERGY_THRESHOLD
            < UpgradeConstants.INJECT_ENERGY_THRESHOLD
            <= UpgradeConstants.TRANSFUSION_ENERGY
        )


class TestStrategyConstants:
    def test_scout_ordering(self):
        assert (
            StrategyConstants.INITIAL_SCOUT_TIME
            < StrategyConstants.SCOUT_INTERVAL
            <= StrategyConstants.OVERLORD_SCOUT_TIME
        )

    def test_lair_timing_is_pro_value(self):
        # Pro players hit Lair around 4:30 (270s); allow ±15s drift.
        assert 255 <= StrategyConstants.LAIR_TIMING <= 285


class TestAbilityConstants:
    def test_corrosive_bile(self):
        assert AbilityConstants.CORROSIVE_BILE_RANGE == 9
        assert AbilityConstants.CORROSIVE_BILE_RADIUS == 2

    def test_fungal_growth(self):
        assert AbilityConstants.FUNGAL_GROWTH_RANGE == 10
        assert AbilityConstants.FUNGAL_ENERGY == 75


class TestUnitPriority:
    def test_queen_has_highest_priority(self):
        # Lower number == higher priority for transfusion.
        assert UnitPriority.QUEEN < UnitPriority.ULTRALISK
        assert UnitPriority.QUEEN < UnitPriority.BROODLORD
        assert UnitPriority.QUEEN < UnitPriority.ZERGLING

    def test_supply_outranks_other_production(self):
        assert UnitPriority.SUPPLY > UnitPriority.ARMY
        assert UnitPriority.ARMY > UnitPriority.WORKERS
        assert UnitPriority.WORKERS > UnitPriority.TECH


class TestDebugConstants:
    def test_intervals_are_positive(self):
        assert DebugConstants.LOG_INTERVAL > 0
        assert DebugConstants.STAT_REPORT_INTERVAL > DebugConstants.LOG_INTERVAL


class TestConversions:
    def test_seconds_to_iterations_roundtrip(self):
        for seconds in [0.5, 1.0, 5.0, 60.0]:
            iters = seconds_to_iterations(seconds)
            back = iterations_to_seconds(iters)
            # Allow ≤1 frame drift due to int truncation.
            assert abs(back - seconds) <= 1 / GameFrequencies.GAME_FPS

    def test_seconds_to_iterations_is_int(self):
        assert isinstance(seconds_to_iterations(1.5), int)

    def test_zero_seconds_zero_iterations(self):
        assert seconds_to_iterations(0) == 0
        assert iterations_to_seconds(0) == 0.0
