# -*- coding: utf-8 -*-
"""GameConstants 단위 테스트.

GameFrequencies, EconomyConstants, CombatConstants, UpgradeConstants,
StrategyConstants 등의 상수 값과 helper 함수(seconds_to_iterations,
iterations_to_seconds)의 정합성을 검증한다.

목적:
- 매직 넘버를 모듈 상수로 옮긴 의도가 유지되도록(상수가 바뀌면 명시적
  변경 인지) 회귀를 잡는 안전망 제공.
- SC2 FPS(22.4) 기반의 frame ↔ second 변환이 라운드트립하는지 확인.
"""

import os
import sys
import unittest

os.environ["PROTOCOL_BUFFERS_PYTHON_IMPLEMENTATION"] = "python"
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from utils.game_constants import (
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
    def test_fps_value(self):
        # SC2 Faster speed는 22.4 FPS, 모든 frame 상수의 기준점.
        self.assertEqual(GameFrequencies.GAME_FPS, 22.4)

    def test_one_second_matches_fps(self):
        # EVERY_SECOND는 GAME_FPS를 정수 반올림한 값과 일치해야 한다.
        self.assertEqual(GameFrequencies.EVERY_SECOND, round(GameFrequencies.GAME_FPS))

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
            GameFrequencies.EVERY_2_MINUTES,
            GameFrequencies.EVERY_3_MINUTES,
            GameFrequencies.EVERY_5_MINUTES,
        ]
        for prev, nxt in zip(intervals, intervals[1:]):
            self.assertLess(prev, nxt)


class TestSecondsIterationsRoundtrip(unittest.TestCase):
    def test_seconds_to_iterations_integer(self):
        self.assertIsInstance(seconds_to_iterations(1.0), int)

    def test_one_second_round_trip(self):
        # 22.4 * 1 = 22.4 → int → 22, /22.4 → 0.982... (반올림 오차 허용)
        it = seconds_to_iterations(1.0)
        back = iterations_to_seconds(it)
        self.assertAlmostEqual(back, 1.0, delta=0.05)

    def test_minute_round_trip(self):
        it = seconds_to_iterations(60.0)
        back = iterations_to_seconds(it)
        self.assertAlmostEqual(back, 60.0, delta=0.05)


class TestEconomyConstantsSanity(unittest.TestCase):
    def test_workers_per_base_within_limits(self):
        self.assertLess(
            EconomyConstants.OPTIMAL_WORKERS_PER_BASE,
            EconomyConstants.MAX_WORKERS_PER_BASE,
        )

    def test_drone_targets_strictly_decreasing(self):
        # LOW → HIGH 난이도로 갈수록 드론 목표는 더 작아야 한다 (경제 ↓ 군대 ↑).
        self.assertGreater(
            EconomyConstants.TARGET_DRONES_LOW, EconomyConstants.TARGET_DRONES_MEDIUM
        )
        self.assertGreater(
            EconomyConstants.TARGET_DRONES_MEDIUM, EconomyConstants.TARGET_DRONES_HIGH
        )

    def test_expansion_threshold_above_hatchery_cost(self):
        # 해처리 비용 300 미네랄보다 buffer를 두고 시작해야 안전.
        self.assertGreaterEqual(EconomyConstants.EXPANSION_MINERAL_THRESHOLD, 300)


class TestCombatConstantsSanity(unittest.TestCase):
    def test_hp_thresholds_ordered(self):
        self.assertLess(
            CombatConstants.RETREAT_HP_THRESHOLD, CombatConstants.BURROW_HP_THRESHOLD
        )
        self.assertLess(
            CombatConstants.BURROW_HP_THRESHOLD,
            CombatConstants.TRANSFUSION_HP_THRESHOLD,
        )
        self.assertLess(
            CombatConstants.TRANSFUSION_HP_THRESHOLD,
            CombatConstants.FULL_HP_THRESHOLD,
        )

    def test_retreat_distance_above_melee(self):
        self.assertGreater(
            CombatConstants.RETREAT_DISTANCE, CombatConstants.MELEE_RANGE
        )

    def test_min_army_positive(self):
        self.assertGreater(CombatConstants.MIN_ARMY_FOR_ATTACK, 0)
        self.assertGreater(CombatConstants.MIN_ROACH_FOR_RUSH, 0)


class TestUpgradeConstants(unittest.TestCase):
    def test_inject_cooldown_matches_game(self):
        # SC2 정확값: 640 frames / 22.4 fps ≈ 28.57s
        self.assertAlmostEqual(
            UpgradeConstants.INJECT_COOLDOWN, 640 / GameFrequencies.GAME_FPS, places=2
        )

    def test_inject_max_distance_positive(self):
        self.assertGreater(UpgradeConstants.MAX_INJECT_DISTANCE, 0)


class TestStrategyConstants(unittest.TestCase):
    def test_scout_interval_positive(self):
        self.assertGreater(StrategyConstants.SCOUT_INTERVAL, 0)

    def test_pool_timing_supply_range(self):
        # 산란못 빌드 타이밍은 인구수 단위 → 12~36 사이가 합리적
        self.assertGreaterEqual(StrategyConstants.POOL_TIMING, 12)
        self.assertLessEqual(StrategyConstants.POOL_TIMING, 36)


class TestUnitPriority(unittest.TestCase):
    def test_queen_highest_priority(self):
        # 수혈 우선순위는 음수일수록 우선. Queen이 가장 우선이어야 함.
        priorities = {
            "queen": UnitPriority.QUEEN,
            "ultra": UnitPriority.ULTRALISK,
            "brood": UnitPriority.BROODLORD,
            "ravager": UnitPriority.RAVAGER,
            "roach": UnitPriority.ROACH,
            "ling": UnitPriority.ZERGLING,
        }
        most_priority = min(priorities, key=priorities.get)
        self.assertEqual(most_priority, "queen")


class TestDebugConstants(unittest.TestCase):
    def test_log_interval_smaller_than_stat_report(self):
        self.assertLess(
            DebugConstants.LOG_INTERVAL, DebugConstants.STAT_REPORT_INTERVAL
        )


if __name__ == "__main__":
    unittest.main()
