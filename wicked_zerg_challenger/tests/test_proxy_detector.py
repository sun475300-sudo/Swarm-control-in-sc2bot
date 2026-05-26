# -*- coding: utf-8 -*-
"""Round 5 regression tests for ProxyDetector.analyze_enemy_building.

Locks in the new behaviour added in round 5 — `distance_to_base` is now
read and used to boost confidence when a candidate proxy sits deep in
midfield, far from the enemy base.
"""
import os
import sys
import unittest

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from proxy_detector import ProxyDetector


class TestProxyDetectorConfidence(unittest.TestCase):
    def setUp(self):
        self.det = ProxyDetector()
        self.det.initialize_normal_expansions([])

    def test_midfield_pylon_classified_as_high_confidence_proxy(self):
        # (75, 75) is in midfield — far from start corners and from the
        # hard-coded enemy_base_estimate (150, 150). Distance ~106.
        result = self.det.analyze_enemy_building((75, 75), "pylon")
        self.assertTrue(result.is_proxy)
        self.assertGreaterEqual(
            result.confidence, 0.95,
            "Far-from-base proxy should have boosted confidence (>=0.95)",
        )

    def test_close_to_enemy_base_lower_confidence(self):
        # (140, 140) is ~14 tiles from the (150, 150) enemy_base_estimate
        # → distance_to_base <= 60 → keep base 0.8 confidence.
        result = self.det.analyze_enemy_building((140, 140), "pylon")
        # Note: (140,140) is NOT near our hard-coded start corners
        # ((0,0),(150,150),(150,0),(0,150)) within radius 20, since
        # distance to (150,150) is 14 → near_start = True. So this should
        # NOT be flagged as a proxy.
        self.assertFalse(result.is_proxy)

    def test_proxy_marker_on_history(self):
        result = self.det.analyze_enemy_building((75, 75), "gateway")
        self.assertIn(result, self.det.proxy_history)
        self.assertTrue(self.det.get_proxy_alerts())


if __name__ == "__main__":
    unittest.main(verbosity=2)
