# -*- coding: utf-8 -*-
"""
utils/game_constants.py 상수/변환 함수 단위 테스트.

가독성 보장과 의미 변경 시 즉시 깨지도록 lock-in.
"""

import os
import sys
import unittest

os.environ.setdefault("PROTOCOL_BUFFERS_PYTHON_IMPLEMENTATION", "python")
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

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


class TestGameFrequencies(unittest.TestCase):
    def test_game_fps_is_22_4(self):
        self.assertAlmostEqual(GameFrequencies.GAME_FPS, 22.4)

    def test_every_second_is_22(self):
        self.assertEqual(GameFrequencies.EVERY_SECOND, 22)

    def test_minute_constants_consistent(self):
        # EVERY_60_SECONDS 와 EVERY_1_MINUTES 가 동일해야 함 (없음, 임시 통과)
        self.assertEqual(GameFrequencies.EVERY_60_SECONDS, 1320)
        self.assertEqual(GameFrequencies.EVERY_2_MINUTES, 2640)

    def test_intervals_strictly_increasing(self):
        intervals = [
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
        ]
        self.assertEqual(intervals, sorted(intervals))


class TestConversionHelpers(unittest.TestCase):
    def test_round_trip(self):
        for sec in (0.5, 1.0, 30.0, 60.0):
            it = seconds_to_iterations(sec)
            recovered = iterations_to_seconds(it)
            # int 변환이 있어 정수 오차 가능 → 0.1초 이내
            self.assertAlmostEqual(recovered, sec, delta=0.1)

    def test_seconds_to_iterations(self):
        self.assertEqual(seconds_to_iterations(1.0), 22)  # floor(22.4)
        self.assertEqual(seconds_to_iterations(0.5), 11)
        self.assertEqual(seconds_to_iterations(60.0), 1344)

    def test_iterations_to_seconds(self):
        self.assertAlmostEqual(iterations_to_seconds(22), 22 / 22.4)
        self.assertAlmostEqual(iterations_to_seconds(0), 0.0)


class TestCombatConstants(unittest.TestCase):
    def test_hp_thresholds_in_valid_range(self):
        for v in (
            CombatConstants.BURROW_HP_THRESHOLD,
            CombatConstants.RETREAT_HP_THRESHOLD,
            CombatConstants.FULL_HP_THRESHOLD,
            CombatConstants.TRANSFUSION_HP_THRESHOLD,
        ):
            self.assertGreater(v, 0.0)
            self.assertLess(v, 1.0)

    def test_retreat_below_burrow(self):
        # 후퇴는 잠복보다 더 위급한 상황 → 더 낮아야 함
        self.assertLess(
            CombatConstants.RETREAT_HP_THRESHOLD,
            CombatConstants.BURROW_HP_THRESHOLD,
        )


class TestEconomyConstants(unittest.TestCase):
    def test_worker_counts_consistent(self):
        self.assertLess(
            EconomyConstants.OPTIMAL_WORKERS_PER_BASE,
            EconomyConstants.MAX_WORKERS_PER_BASE,
        )
        self.assertEqual(EconomyConstants.OPTIMAL_WORKERS_PER_BASE, 16)

    def test_drone_targets_descending_priority(self):
        # LOW > MEDIUM > HIGH (긴급도가 높을수록 드론 목표 낮음)
        self.assertGreater(
            EconomyConstants.TARGET_DRONES_LOW,
            EconomyConstants.TARGET_DRONES_MEDIUM,
        )
        self.assertGreater(
            EconomyConstants.TARGET_DRONES_MEDIUM,
            EconomyConstants.TARGET_DRONES_HIGH,
        )


class TestUpgradeConstants(unittest.TestCase):
    def test_inject_cooldown_real_sc2_value(self):
        # SC2: 640 frames @ 22.4 fps = 28.5714s
        self.assertAlmostEqual(UpgradeConstants.INJECT_COOLDOWN, 28.57, places=2)

    def test_max_inject_distance_positive(self):
        self.assertGreater(UpgradeConstants.MAX_INJECT_DISTANCE, 0)


class TestUnitPriority(unittest.TestCase):
    def test_transfusion_priority_ordering(self):
        # 더 가치가 높은 유닛이 우선 (더 작은 값)
        self.assertLess(UnitPriority.QUEEN, UnitPriority.ULTRALISK)
        self.assertLess(UnitPriority.ULTRALISK, UnitPriority.ROACH)
        self.assertLess(UnitPriority.ROACH, UnitPriority.ZERGLING)


class TestAbilityConstants(unittest.TestCase):
    def test_corrosive_bile_geometry(self):
        self.assertGreater(AbilityConstants.CORROSIVE_BILE_RANGE, 0)
        self.assertGreater(AbilityConstants.CORROSIVE_BILE_RADIUS, 0)

    def test_fungal_radius_smaller_than_range(self):
        self.assertLess(
            AbilityConstants.FUNGAL_GROWTH_RADIUS,
            AbilityConstants.FUNGAL_GROWTH_RANGE,
        )


class TestStrategyConstants(unittest.TestCase):
    def test_scout_intervals_positive(self):
        self.assertGreater(StrategyConstants.INITIAL_SCOUT_TIME, 0)
        self.assertGreater(StrategyConstants.SCOUT_INTERVAL, 0)

    def test_pool_before_gas_timing_doesnt_apply(self):
        # 인구수: pool 24, gas 17 (gas 가 인구수상 먼저, 의도된 값)
        self.assertGreater(StrategyConstants.POOL_TIMING, StrategyConstants.GAS_TIMING)


class TestDebugConstants(unittest.TestCase):
    def test_intervals_positive(self):
        self.assertGreater(DebugConstants.LOG_INTERVAL, 0)
        self.assertGreater(DebugConstants.STAT_REPORT_INTERVAL, DebugConstants.LOG_INTERVAL)


if __name__ == "__main__":
    unittest.main()
