# -*- coding: utf-8 -*-
import os
import sys
import unittest

os.environ["PROTOCOL_BUFFERS_PYTHON_IMPLEMENTATION"] = "python"
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

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


if __name__ == "__main__":
    unittest.main()
