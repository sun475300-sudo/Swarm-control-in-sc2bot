# -*- coding: utf-8 -*-
"""
utils/frame_cache.py 단위 테스트.

FrameCache 의 frame invalidation 및 cached_per_frame 데코레이터 동작 검증.
"""

import os
import sys
import unittest

os.environ.setdefault("PROTOCOL_BUFFERS_PYTHON_IMPLEMENTATION", "python")
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from utils.frame_cache import FrameCache, cached_per_frame


class TestFrameCache(unittest.TestCase):
    def test_initial_state(self):
        cache = FrameCache()
        self.assertIsNone(cache.get("missing"))
        self.assertFalse(cache.has("any"))

    def test_set_and_get(self):
        cache = FrameCache()
        cache.set("k", 42)
        self.assertEqual(cache.get("k"), 42)
        self.assertTrue(cache.has("k"))

    def test_default_value(self):
        cache = FrameCache()
        self.assertEqual(cache.get("missing", "default"), "default")

    def test_clear_if_new_frame_invalidates(self):
        cache = FrameCache()
        cache.clear_if_new_frame(1)
        cache.set("k", "v")
        cache.clear_if_new_frame(2)  # 새 프레임 → 클리어
        self.assertFalse(cache.has("k"))

    def test_clear_if_new_frame_same_frame_keeps(self):
        cache = FrameCache()
        cache.clear_if_new_frame(1)
        cache.set("k", "v")
        cache.clear_if_new_frame(1)  # 같은 프레임 → 유지
        self.assertTrue(cache.has("k"))

    def test_explicit_clear(self):
        cache = FrameCache()
        cache.set("k", "v")
        cache.clear()
        self.assertFalse(cache.has("k"))


class _Target:
    def __init__(self):
        self._frame_cache = FrameCache()
        self.call_count = 0

    @cached_per_frame
    def compute(self, x):
        self.call_count += 1
        return x * 2

    @cached_per_frame
    def compute_kw(self, x=1):
        self.call_count += 1
        return x * 10


class TestCachedPerFrameDecorator(unittest.TestCase):
    def test_first_call_executes(self):
        t = _Target()
        self.assertEqual(t.compute(5), 10)
        self.assertEqual(t.call_count, 1)

    def test_second_call_cached(self):
        t = _Target()
        t.compute(5)
        t.compute(5)  # 같은 args → 캐시 적중
        self.assertEqual(t.call_count, 1)

    def test_different_args_separate_cache(self):
        t = _Target()
        t.compute(5)
        t.compute(7)
        self.assertEqual(t.call_count, 2)

    def test_frame_invalidation(self):
        t = _Target()
        t.compute(5)
        # 새 프레임 시작
        t._frame_cache.clear_if_new_frame(1)
        t._frame_cache.clear_if_new_frame(2)
        t.compute(5)
        # 새 프레임에서 재계산
        self.assertEqual(t.call_count, 2)

    def test_no_frame_cache_attr_still_works(self):
        """instance에 _frame_cache 가 없으면 그냥 함수 실행"""

        class _NoFrameCache:
            call_count = 0

            @cached_per_frame
            def compute(self, x):
                self.call_count += 1
                return x

        obj = _NoFrameCache()
        obj.compute(1)
        obj.compute(1)
        # 캐시 없으므로 매번 호출
        self.assertEqual(obj.call_count, 2)

    def test_kwargs_distinguished_in_cache_key(self):
        """기존 버그: kwargs 가 캐시 키에서 무시되어 다른 호출이 같은 결과로 매핑되던 문제"""
        t = _Target()
        result1 = t.compute_kw(x=1)
        result2 = t.compute_kw(x=2)
        # x=1 → 10, x=2 → 20 이어야 정상
        self.assertEqual(result1, 10)
        self.assertEqual(result2, 20)
        # 그리고 호출이 두 번 일어났어야 함 (캐시 충돌 X)
        self.assertEqual(t.call_count, 2)

    def test_kwargs_same_cached(self):
        """같은 kwargs 재호출은 캐시 적중"""
        t = _Target()
        t.compute_kw(x=5)
        t.compute_kw(x=5)
        self.assertEqual(t.call_count, 1)


if __name__ == "__main__":
    unittest.main()
