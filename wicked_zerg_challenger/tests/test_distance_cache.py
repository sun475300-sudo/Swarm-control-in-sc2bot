# -*- coding: utf-8 -*-
import os
import sys
import unittest

os.environ["PROTOCOL_BUFFERS_PYTHON_IMPLEMENTATION"] = "python"
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from utils.distance_cache import DistanceCache, cached_distance


class FakePoint:
    def __init__(self, x, y):
        self.x = x
        self.y = y
        self.calls = 0

    def distance_to(self, other):
        self.calls += 1
        return ((self.x - other.x) ** 2 + (self.y - other.y) ** 2) ** 0.5


class TestDistanceCache(unittest.TestCase):
    def test_hit_rate_counts_reused_distance(self):
        cache = DistanceCache()
        a = FakePoint(0, 0)
        b = FakePoint(3, 4)

        self.assertEqual(cache.get(a, b, 7), 5.0)
        self.assertEqual(cache.get(b, a, 7), 5.0)

        self.assertEqual(a.calls, 1)
        self.assertEqual(cache.size, 1)
        self.assertEqual(cache.hit_rate, 0.5)

    def test_global_cached_distance_uses_same_api(self):
        a = FakePoint(1, 1)
        b = FakePoint(4, 5)

        self.assertEqual(cached_distance(a, b, 99), 5.0)
        self.assertEqual(cached_distance(a, b, 99), 5.0)
        self.assertEqual(a.calls, 1)


if __name__ == "__main__":
    unittest.main()
