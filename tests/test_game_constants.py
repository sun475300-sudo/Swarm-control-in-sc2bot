# -*- coding: utf-8 -*-
"""Tests for game_constants.py — timing/economy/combat/upgrade constants."""

import sys
import pytest

sys.path.insert(0, "wicked_zerg_challenger")

from utils.game_constants import (
    GameFrequencies,
    EconomyConstants,
    CombatConstants,
    UpgradeConstants,
    StrategyConstants,
    UnitPriority,
    AbilityConstants,
    DebugConstants,
    seconds_to_iterations,
    iterations_to_seconds,
)


class TestGameFrequencies:
    def test_fps_is_sc2_faster_speed(self):
        assert GameFrequencies.GAME_FPS == 22.4

    def test_every_second_equals_fps_rounded(self):
        assert GameFrequencies.EVERY_SECOND == 22  # floor of 22.4

    def test_intervals_are_ordered(self):
        assert GameFrequencies.EVERY_HALF_SECOND < GameFrequencies.EVERY_SECOND
        assert GameFrequencies.EVERY_SECOND < GameFrequencies.EVERY_2_SECONDS
        assert GameFrequencies.EVERY_2_SECONDS < GameFrequencies.EVERY_5_SECONDS
        assert GameFrequencies.EVERY_30_SECONDS < GameFrequencies.EVERY_60_SECONDS

    def test_minute_intervals_consistent(self):
        assert GameFrequencies.EVERY_2_MINUTES == GameFrequencies.EVERY_60_SECONDS * 2
        assert GameFrequencies.EVERY_5_MINUTES == GameFrequencies.EVERY_60_SECONDS * 5

    def test_all_intervals_positive(self):
        attrs = [a for a in dir(GameFrequencies) if not a.startswith("_")]
        for name in attrs:
            value = getattr(GameFrequencies, name)
            if isinstance(value, (int, float)):
                assert value > 0, f"{name}={value} not positive"


class TestEconomyConstants:
    def test_worker_saturation_ordering(self):
        assert EconomyConstants.OPTIMAL_WORKERS_PER_BASE < EconomyConstants.MAX_WORKERS_PER_BASE

    def test_gas_workers_lower_than_mineral(self):
        assert EconomyConstants.OPTIMAL_WORKERS_PER_GAS < EconomyConstants.OPTIMAL_WORKERS_PER_BASE

    def test_mineral_bank_reasonable(self):
        assert EconomyConstants.MAX_MINERAL_BANK > EconomyConstants.EXPANSION_MINERAL_THRESHOLD


class TestCombatConstants:
    def test_hp_thresholds_ordered(self):
        assert CombatConstants.RETREAT_HP_THRESHOLD < CombatConstants.BURROW_HP_THRESHOLD
        assert CombatConstants.BURROW_HP_THRESHOLD < CombatConstants.TRANSFUSION_HP_THRESHOLD
        assert CombatConstants.TRANSFUSION_HP_THRESHOLD < CombatConstants.FULL_HP_THRESHOLD

    def test_all_hp_thresholds_in_0_1(self):
        assert 0 <= CombatConstants.BURROW_HP_THRESHOLD <= 1
        assert 0 <= CombatConstants.RETREAT_HP_THRESHOLD <= 1
        assert 0 <= CombatConstants.FULL_HP_THRESHOLD <= 1
        assert 0 <= CombatConstants.TRANSFUSION_HP_THRESHOLD <= 1

    def test_melee_shorter_than_retreat_distance(self):
        assert CombatConstants.MELEE_RANGE < CombatConstants.RETREAT_DISTANCE

    def test_army_thresholds_positive(self):
        assert CombatConstants.MIN_ARMY_FOR_ATTACK > 0
        assert CombatConstants.MIN_ROACH_FOR_RUSH > 0


class TestUpgradeConstants:
    def test_inject_cooldown_is_sc2_accurate(self):
        # 640 frames / 22.4 fps = 28.57s (SC2 spec)
        assert abs(UpgradeConstants.INJECT_COOLDOWN - 28.57) < 0.1

    def test_energy_thresholds_positive(self):
        assert UpgradeConstants.INJECT_ENERGY_THRESHOLD > 0
        assert UpgradeConstants.TRANSFUSION_ENERGY > 0
        assert UpgradeConstants.CREEP_ENERGY_THRESHOLD > 0

    def test_transfusion_range_reasonable(self):
        assert 0 < UpgradeConstants.TRANSFUSION_RANGE <= 10


class TestStrategyConstants:
    def test_scout_timings_ordered(self):
        assert StrategyConstants.INITIAL_SCOUT_TIME < StrategyConstants.OVERLORD_SCOUT_TIME

    def test_supply_buffer_positive(self):
        assert StrategyConstants.SUPPLY_BUFFER > 0


class TestUnitPriority:
    def test_high_value_units_negative_priority(self):
        # Negative values = higher transfusion priority
        assert UnitPriority.QUEEN < 0
        assert UnitPriority.ULTRALISK < 0
        assert UnitPriority.BROODLORD < 0

    def test_queen_has_highest_priority(self):
        assert UnitPriority.QUEEN <= UnitPriority.ULTRALISK
        assert UnitPriority.QUEEN <= UnitPriority.ZERGLING

    def test_production_priorities_ordered(self):
        assert UnitPriority.SUPPLY > UnitPriority.ARMY
        assert UnitPriority.ARMY > UnitPriority.WORKERS
        assert UnitPriority.WORKERS > UnitPriority.TECH


class TestAbilityConstants:
    def test_ability_ranges_positive(self):
        assert AbilityConstants.CORROSIVE_BILE_RANGE > 0
        assert AbilityConstants.FUNGAL_GROWTH_RANGE > 0
        assert AbilityConstants.ABDUCT_RANGE > 0
        assert AbilityConstants.BLINDING_CLOUD_RANGE > 0


class TestConversionHelpers:
    def test_seconds_to_iterations_zero(self):
        assert seconds_to_iterations(0) == 0

    def test_seconds_to_iterations_one_second(self):
        assert seconds_to_iterations(1.0) == 22  # floor of 22.4

    def test_iterations_to_seconds_zero(self):
        assert iterations_to_seconds(0) == 0.0

    def test_round_trip_approximation(self):
        for seconds in [1.0, 5.0, 10.0, 30.0]:
            iterations = seconds_to_iterations(seconds)
            back = iterations_to_seconds(iterations)
            # Small loss due to int-truncation, but should be close
            assert abs(back - seconds) < 0.1


class TestDebugConstants:
    def test_intervals_ordered(self):
        assert DebugConstants.ERROR_LOG_THROTTLE < DebugConstants.LOG_INTERVAL
        assert DebugConstants.LOG_INTERVAL < DebugConstants.STAT_REPORT_INTERVAL
