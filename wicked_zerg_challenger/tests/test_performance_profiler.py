# -*- coding: utf-8 -*-
import os
import sys
import unittest

os.environ["PROTOCOL_BUFFERS_PYTHON_IMPLEMENTATION"] = "python"
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from utils.performance_profiler import PerformanceProfiler


class TestPerformanceProfiler(unittest.TestCase):
    def test_measure_records_named_operation(self):
        profiler = PerformanceProfiler()

        with profiler.measure("strategy_manager"):
            sum(range(10))

        stats = profiler.get_stats()
        self.assertIn("strategy_manager", stats)
        self.assertEqual(stats["strategy_manager"]["call_count"], 1)

    def test_frame_stats_after_start_end(self):
        profiler = PerformanceProfiler()

        profiler.start_frame()
        profiler.end_frame()

        stats = profiler.get_frame_stats()
        self.assertIn("avg_frame_ms", stats)
        self.assertGreaterEqual(stats["avg_frame_ms"], 0.0)


if __name__ == "__main__":
    unittest.main()
