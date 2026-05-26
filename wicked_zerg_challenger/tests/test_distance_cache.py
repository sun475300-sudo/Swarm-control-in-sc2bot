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

    def test_frame_change_invalidates_cache(self):
        cache = DistanceCache()
        a = FakePoint(0, 0)
        b = FakePoint(3, 4)

        cache.get(a, b, 1)  # frame 1
        cache.get(a, b, 2)  # frame 2 → invalidate
        # a.distance_to 가 두 번 호출되어야 함
        self.assertEqual(a.calls, 2)
        # cache reset 후 hit_rate 가 0.0 (둘 다 miss 후 1번만 들어옴)
        self.assertEqual(cache.size, 1)

    def test_key_is_order_independent(self):
        """get(a, b) 와 get(b, a) 는 같은 캐시 키"""
        cache = DistanceCache()
        a = FakePoint(0, 0)
        b = FakePoint(3, 4)
        cache.get(a, b, 5)
        cache.get(b, a, 5)
        self.assertEqual(cache.size, 1)
        # 두 번째는 hit
        self.assertEqual(cache.hit_rate, 0.5)

    def test_unit_like_object_uses_position(self):
        """getattr(pos_a, 'position', pos_a) 패턴으로 Unit-like 객체도 지원"""
        cache = DistanceCache()

        class _Unit:
            def __init__(self, x, y):
                self.position = FakePoint(x, y)

        u1 = _Unit(0, 0)
        u2 = _Unit(3, 4)
        result = cache.get(u1, u2, 1)
        self.assertEqual(result, 5.0)

    def test_hit_rate_zero_no_queries(self):
        cache = DistanceCache()
        self.assertEqual(cache.hit_rate, 0.0)

    def test_position_rounded_to_0_1(self):
        """좌표는 소수점 첫째자리까지 라운딩"""
        cache = DistanceCache()
        a = FakePoint(0.01, 0)
        b = FakePoint(3.01, 4)
        c = FakePoint(0.02, 0)
        d = FakePoint(3.02, 4)
        cache.get(a, b, 1)
        # 0.01, 0.02 은 round(_, 1) 동일 → 같은 캐시 키
        cache.get(c, d, 1)
        self.assertEqual(cache.size, 1)


if __name__ == "__main__":
    unittest.main()
