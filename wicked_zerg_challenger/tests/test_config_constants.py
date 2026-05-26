# -*- coding: utf-8 -*-
"""
config/constants.py 단위 테스트 — 의미론적 invariant lock-in.

magic-number 추출 시점의 값과 관계를 보존한다.
"""

import os
import sys
import unittest

os.environ.setdefault("PROTOCOL_BUFFERS_PYTHON_IMPLEMENTATION", "python")
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from config import constants as C


class TestTiming(unittest.TestCase):
    def test_early_game_window_positive(self):
        self.assertGreater(C.EARLY_GAME_END_SECONDS, 0)

    def test_roach_rush_after_early_game(self):
        self.assertGreater(C.ROACH_RUSH_TIMING, C.EARLY_GAME_END_SECONDS)

    def test_spine_build_within_early_window(self):
        self.assertLessEqual(C.SPINE_BUILD_TIME, C.EARLY_GAME_END_SECONDS + 60)


class TestDefenseRadii(unittest.TestCase):
    def test_proxy_radius_larger_than_enemy(self):
        # 프록시는 더 멀리서 감지해야 의미가 있음
        self.assertGreater(C.PROXY_DETECT_RADIUS, C.ENEMY_DETECT_RADIUS)

    def test_radii_positive(self):
        for v in (
            C.ENEMY_DETECT_RADIUS,
            C.PROXY_DETECT_RADIUS,
            C.WORKER_DEFEND_RADIUS,
            C.BASE_THREAT_RADIUS,
        ):
            self.assertGreater(v, 0)


class TestUnitCounts(unittest.TestCase):
    def test_defense_worker_consistency(self):
        # 프록시 방어 일꾼 수가 cap 을 초과하지 않음
        self.assertLessEqual(C.PROXY_DEFENSE_WORKERS, C.MAX_WORKER_DEFENSE)

    def test_emergency_spine_positive(self):
        self.assertGreater(C.EMERGENCY_SPINE_COUNT, 0)

    def test_roach_rush_min_reasonable(self):
        self.assertGreaterEqual(C.ROACH_RUSH_MIN_COUNT, 6)


class TestEconomy(unittest.TestCase):
    def test_spine_cost_positive(self):
        self.assertGreater(C.SPINE_CRAWLER_COST, 0)

    def test_zergling_speed_cost(self):
        self.assertGreater(C.ZERGLING_SPEED_GAS_COST, 0)


class TestBuildOrder(unittest.TestCase):
    def test_build_order_end_after_natural(self):
        self.assertGreater(C.BUILD_ORDER_END_TIME, C.EXPANSION_TIMING_TARGET)

    def test_step_retries_positive(self):
        self.assertGreater(C.MAX_STEP_RETRIES, 0)


class TestRL(unittest.TestCase):
    def test_reward_scale_positive(self):
        self.assertGreater(C.REWARD_NORM_SCALE, 0)

    def test_win_rate_floor_in_unit_range(self):
        self.assertGreaterEqual(C.MIN_WIN_RATE_FOR_PROMOTION, 0.0)
        self.assertLessEqual(C.MIN_WIN_RATE_FOR_PROMOTION, 1.0)

    def test_threat_cache_ttl_positive(self):
        self.assertGreater(C.THREAT_CACHE_TTL, 0)


if __name__ == "__main__":
    unittest.main()
