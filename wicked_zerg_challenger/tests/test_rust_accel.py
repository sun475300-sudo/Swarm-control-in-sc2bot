# -*- coding: utf-8 -*-
import os
import sys
import unittest

os.environ["PROTOCOL_BUFFERS_PYTHON_IMPLEMENTATION"] = "python"
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from rust_accel import (
    batch_nearest_points,
    calculate_retreat_path,
    find_unit_clusters,
    nearest_point_index,
    threat_assessment,
)


class TestRustAccelFallback(unittest.TestCase):
    def test_nearest_point_fallback(self):
        points = [(10.0, 10.0), (2.0, 1.0), (5.0, 5.0)]

        self.assertEqual(nearest_point_index((0.0, 0.0), points), 1)
        self.assertEqual(batch_nearest_points([(0.0, 0.0)], points), [1])

    def test_cluster_and_threat_helpers(self):
        clusters = find_unit_clusters(
            [(0.0, 0.0), (0.5, 0.5), (8.0, 8.0)], radius=1.0, min_count=2
        )
        self.assertGreaterEqual(clusters[0][2], 2)

        score = threat_assessment(
            [(1.0, 1.0, 100.0, 10.0, 6.0), (50.0, 50.0, 100.0, 10.0, 6.0)],
            (0.0, 0.0),
            10.0,
        )
        self.assertGreater(score, 0.0)

    def test_retreat_path_prefers_spine_bonus(self):
        result = calculate_retreat_path(
            unit_pos=(10.0, 10.0),
            base_positions=[(0.0, 0.0), (8.0, 8.0)],
            spine_positions=[(0.0, 1.0)],
        )

        self.assertEqual(result, (0.0, 0.0))


if __name__ == "__main__":
    unittest.main()
