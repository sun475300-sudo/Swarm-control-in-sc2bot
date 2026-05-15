# -*- coding: utf-8 -*-
import os
import sys
import unittest

os.environ["PROTOCOL_BUFFERS_PYTHON_IMPLEMENTATION"] = "python"
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from blackboard import GameStateBlackboard, ThreatLevel

from utils.frame_skip import FrameSkipManager


class TestFrameSkipManager(unittest.TestCase):
    def test_default_intervals_gate_manager_execution(self):
        manager = FrameSkipManager()

        self.assertTrue(manager.should_execute("economy_manager", 6))
        self.assertFalse(manager.should_execute("economy_manager", 7))

    def test_combat_and_overload_adjust_intervals(self):
        manager = FrameSkipManager()
        manager.set_combat_mode(True)
        self.assertTrue(manager.should_execute("strategy_manager", 6))
        self.assertFalse(manager.should_execute("strategy_manager", 5))

        manager.set_overloaded(True)
        self.assertFalse(manager.should_execute("strategy_manager", 3))
        self.assertTrue(manager.should_execute("strategy_manager", 6))

    def test_overload_doubles_interval_for_non_combat_managers(self):
        """경부하 모드: combat_manager는 영향 없음, 나머지는 인터벌 2배"""
        manager = FrameSkipManager()
        manager.set_overloaded(True)
        # combat_manager interval is 1 → still always executes
        self.assertTrue(manager.should_execute("combat_manager", 0))
        self.assertTrue(manager.should_execute("combat_manager", 1))
        # economy_manager default interval 3 → doubled to 6
        self.assertTrue(manager.should_execute("economy_manager", 6))
        self.assertFalse(manager.should_execute("economy_manager", 3))

    def test_unknown_manager_runs_every_frame(self):
        """등록되지 않은 매니저는 매 프레임 실행 (interval=1 기본값)"""
        manager = FrameSkipManager()
        self.assertTrue(manager.should_execute("unknown_xyz", 0))
        self.assertTrue(manager.should_execute("unknown_xyz", 7))


class TestFrameSkipBlackboardIntegration(unittest.TestCase):
    """FrameSkipManager가 Blackboard 위협 상태와 함께 쓰일 때 동작 검증"""

    def setUp(self):
        self.frame_skip = FrameSkipManager()
        self.bb = GameStateBlackboard()

    def _sync_from_blackboard(self):
        # Mirrors wicked_zerg_bot_pro_impl.on_step combat-mode sync.
        in_combat = bool(self.bb.is_under_attack or self.bb.threat.is_rushing)
        self.frame_skip.set_combat_mode(in_combat)

    def test_peace_uses_default_intervals(self):
        self.bb.update_threat(ThreatLevel.NONE)
        self._sync_from_blackboard()
        # default scouting_system interval = 11
        self.assertTrue(self.frame_skip.should_execute("scouting_system", 11))
        self.assertFalse(self.frame_skip.should_execute("scouting_system", 10))

    def test_under_attack_flips_to_combat_intervals(self):
        self.bb.is_under_attack = True
        self._sync_from_blackboard()
        # combat scouting_system interval = 22
        self.assertTrue(self.frame_skip.should_execute("scouting_system", 22))
        self.assertFalse(self.frame_skip.should_execute("scouting_system", 11))

    def test_rush_detection_triggers_combat_mode(self):
        self.bb.threat.is_rushing = True
        self._sync_from_blackboard()
        self.assertTrue(self.frame_skip.in_combat)


if __name__ == "__main__":
    unittest.main()
