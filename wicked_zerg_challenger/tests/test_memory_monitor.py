# -*- coding: utf-8 -*-
import os
import sys
import unittest

os.environ["PROTOCOL_BUFFERS_PYTHON_IMPLEMENTATION"] = "python"
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from utils.memory_monitor import MemoryMonitor


class TestMemoryMonitor(unittest.TestCase):
    def test_check_skips_non_interval_frame(self):
        monitor = MemoryMonitor(leak_check_interval=5)
        try:
            self.assertEqual(monitor.check(4), {})
        finally:
            monitor.stop()

    def test_check_returns_memory_snapshot(self):
        monitor = MemoryMonitor(warn_threshold_mb=1024, leak_check_interval=1)
        try:
            result = monitor.check(1)
        finally:
            monitor.stop()

        self.assertIn("current_bytes", result)
        self.assertFalse(result["over_threshold"])


if __name__ == "__main__":
    unittest.main()
