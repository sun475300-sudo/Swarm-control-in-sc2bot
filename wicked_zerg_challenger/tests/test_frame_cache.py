# -*- coding: utf-8 -*-
"""FrameCache 및 cached_per_frame 데코레이터 테스트."""

import os
import sys
import unittest

os.environ["PROTOCOL_BUFFERS_PYTHON_IMPLEMENTATION"] = "python"
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from utils.frame_cache import FrameCache, cached_per_frame


class TestFrameCache(unittest.TestCase):
    def test_set_get_basic(self):
        c = FrameCache()
        c.set("a", 1)
        self.assertEqual(c.get("a"), 1)

    def test_get_default(self):
        c = FrameCache()
        self.assertIsNone(c.get("missing"))
        self.assertEqual(c.get("missing", default=42), 42)

    def test_clear_if_new_frame_invalidates(self):
        c = FrameCache()
        c.clear_if_new_frame(1)
        c.set("a", 1)
        c.clear_if_new_frame(2)  # 새 frame → 캐시 무효화
        self.assertIsNone(c.get("a"))

    def test_clear_if_new_frame_same_frame_keeps_cache(self):
        c = FrameCache()
        c.clear_if_new_frame(1)
        c.set("a", 1)
        c.clear_if_new_frame(1)  # 같은 frame → 유지
        self.assertEqual(c.get("a"), 1)


class _Stub:
    """cached_per_frame을 사용하는 더미 매니저."""

    def __init__(self):
        self._frame_cache = FrameCache()
        self.call_count = 0

    @cached_per_frame
    def compute(self, x):
        self.call_count += 1
        return x * 2

    @cached_per_frame
    def compute_kw(self, *, top_n):
        self.call_count += 1
        return top_n + 100


class TestCachedPerFrame(unittest.TestCase):
    def test_first_call_executes(self):
        s = _Stub()
        self.assertEqual(s.compute(5), 10)
        self.assertEqual(s.call_count, 1)

    def test_repeat_same_args_uses_cache(self):
        s = _Stub()
        s.compute(5)
        s.compute(5)
        s.compute(5)
        self.assertEqual(s.call_count, 1)

    def test_different_positional_args_invalidate(self):
        s = _Stub()
        s.compute(5)
        s.compute(7)
        self.assertEqual(s.call_count, 2)

    def test_different_kwargs_invalidate(self):
        """버그 회귀: kwargs가 키에 포함되어야 같은 함수의 다른 호출이
        잘못 캐시 히트되지 않음."""
        s = _Stub()
        self.assertEqual(s.compute_kw(top_n=5), 105)
        self.assertEqual(s.compute_kw(top_n=10), 110)
        self.assertEqual(s.call_count, 2)

    def test_new_frame_clears_cache(self):
        s = _Stub()
        s._frame_cache.clear_if_new_frame(1)
        s.compute(5)
        s._frame_cache.clear_if_new_frame(2)
        s.compute(5)
        self.assertEqual(s.call_count, 2)

    def test_missing_frame_cache_falls_through(self):
        """_frame_cache가 없으면 함수가 매번 실행되어야 한다."""

        class Bare:
            call_count = 0

            @cached_per_frame
            def f(self, x):
                self.call_count += 1
                return x

        b = Bare()
        b.f(1)
        b.f(1)
        self.assertEqual(b.call_count, 2)


if __name__ == "__main__":
    unittest.main()
