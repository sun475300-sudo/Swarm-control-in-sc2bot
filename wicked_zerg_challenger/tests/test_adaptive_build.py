# -*- coding: utf-8 -*-
"""AdaptiveBuildOrderManager 단위 테스트.

빌드 선택, 전환 쿨다운, 정찰 정보 기반 전환, 시간 기반 자동 전환,
빌드 스텝 진행을 검증한다. 실제 SC2 봇 없이 동작하도록 _StubBot 사용.
"""

import os
import sys
import unittest

os.environ["PROTOCOL_BUFFERS_PYTHON_IMPLEMENTATION"] = "python"
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from adaptive_build import AdaptiveBuildOrderManager, BuildOrderType, BuildStep


class _StubBot:
    def __init__(self, supply_used=0, time=0.0, enemy_race=None):
        self.supply_used = supply_used
        self.time = time
        self.enemy_race = enemy_race


class TestInitialBuildSelection(unittest.TestCase):
    def test_default_for_unknown(self):
        mgr = AdaptiveBuildOrderManager(_StubBot())
        build = mgr.select_initial_build("Unknown")
        # Unknown → fallback HATCH_FIRST
        self.assertEqual(build, BuildOrderType.HATCH_FIRST)

    def test_terran_default(self):
        mgr = AdaptiveBuildOrderManager(_StubBot())
        build = mgr.select_initial_build("Terran")
        self.assertEqual(build, BuildOrderType.ROACH_HYDRA)

    def test_protoss_default(self):
        mgr = AdaptiveBuildOrderManager(_StubBot())
        build = mgr.select_initial_build("Protoss")
        self.assertEqual(build, BuildOrderType.ROACH_HYDRA)

    def test_zerg_default(self):
        mgr = AdaptiveBuildOrderManager(_StubBot())
        build = mgr.select_initial_build("Zerg")
        self.assertEqual(build, BuildOrderType.HATCH_FIRST)

    def test_steps_populated_after_select(self):
        mgr = AdaptiveBuildOrderManager(_StubBot())
        mgr.select_initial_build("Terran")
        self.assertGreater(len(mgr.build_steps), 0)


class TestTransitionCooldown(unittest.TestCase):
    def test_cannot_transition_during_cooldown(self):
        bot = _StubBot(time=100.0)  # cooldown(60) 보다 큰 게임 시간으로 시작
        mgr = AdaptiveBuildOrderManager(bot)
        mgr.select_initial_build("Terran")
        ok1 = mgr.transition_build(BuildOrderType.POOL_FIRST, "test1")
        self.assertTrue(ok1)
        # 첫 전환 직후, cooldown 안에 또 전환 시도 → 거부
        bot.time = 110.0
        ok2 = mgr.transition_build(BuildOrderType.LING_BANE, "test2")
        self.assertFalse(ok2)

    def test_can_transition_after_cooldown(self):
        bot = _StubBot(time=100.0)
        mgr = AdaptiveBuildOrderManager(bot)
        mgr.select_initial_build("Terran")
        mgr.transition_build(BuildOrderType.POOL_FIRST, "first")
        bot.time = 100.0 + mgr.transition_cooldown + 1.0
        ok = mgr.transition_build(BuildOrderType.ROACH_RUSH, "after-cooldown")
        self.assertTrue(ok)

    def test_same_build_does_not_transition(self):
        bot = _StubBot(time=10.0)
        mgr = AdaptiveBuildOrderManager(bot)
        mgr.select_initial_build("Terran")
        bot.time = 200.0  # well past cooldown
        ok = mgr.transition_build(mgr.current_build_type, "same")
        self.assertFalse(ok)


class TestScoutDrivenTransitions(unittest.TestCase):
    def test_rush_detected_switches_to_pool_first(self):
        bot = _StubBot(time=100.0)
        mgr = AdaptiveBuildOrderManager(bot)
        mgr.select_initial_build("Terran")
        # Force out of cooldown
        mgr.last_transition_time = 0.0
        mgr.update({"detected_strategy": "rush_marine"})
        self.assertEqual(mgr.current_build_type, BuildOrderType.POOL_FIRST)
        self.assertTrue(mgr.rush_defense_active)

    def test_air_threat_switches_to_hydra(self):
        bot = _StubBot(time=100.0)
        mgr = AdaptiveBuildOrderManager(bot)
        mgr.select_initial_build("Protoss")
        mgr.last_transition_time = 0.0
        mgr.update({"detected_strategy": "stargate_oracle"})
        self.assertEqual(mgr.current_build_type, BuildOrderType.HYDRA_TIMING)
        self.assertTrue(mgr.air_response_active)

    def test_same_strategy_does_not_retransition(self):
        bot = _StubBot(time=100.0)
        mgr = AdaptiveBuildOrderManager(bot)
        mgr.select_initial_build("Terran")
        mgr.last_transition_time = 0.0
        mgr.update({"detected_strategy": "rush_marine"})
        count_before = mgr.transition_count
        mgr.update({"detected_strategy": "rush_marine"})
        self.assertEqual(mgr.transition_count, count_before)


class TestBuildStep(unittest.TestCase):
    def test_to_dict_roundtrip(self):
        step = BuildStep(
            supply=14, action="build", unit_or_building="HATCHERY", priority=10
        )
        d = step.to_dict()
        self.assertEqual(d["supply"], 14)
        self.assertEqual(d["action"], "build")
        # to_dict는 unit_or_building을 "target"으로 노출 (변경 시 회귀 알람용)
        self.assertEqual(d["target"], "HATCHERY")
        self.assertEqual(d["priority"], 10)
        self.assertFalse(d["completed"])


class TestStepProgression(unittest.TestCase):
    def test_completed_steps_skipped(self):
        bot = _StubBot(supply_used=15)
        mgr = AdaptiveBuildOrderManager(bot)
        mgr.select_initial_build("Terran")
        # 모두 강제로 완료 표시 → 다음 스텝 없음
        for step in mgr.build_steps:
            step.completed = True
        self.assertIsNone(mgr.get_next_build_step())


if __name__ == "__main__":
    unittest.main()
