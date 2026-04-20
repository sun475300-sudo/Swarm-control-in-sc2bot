# -*- coding: utf-8 -*-
"""Tests for utils/frame_cache.py - per-frame caching."""

import sys
import pytest

sys.path.insert(0, "wicked_zerg_challenger")

from utils.frame_cache import FrameCache, cached_per_frame


class TestFrameCacheBasics:
    def test_initial_state(self):
        cache = FrameCache()
        assert not cache.has("anything")

    def test_set_and_get(self):
        cache = FrameCache()
        cache.set("key", "value")
        assert cache.get("key") == "value"

    def test_get_with_default(self):
        cache = FrameCache()
        assert cache.get("missing", default="fallback") == "fallback"

    def test_has_returns_true_after_set(self):
        cache = FrameCache()
        cache.set("key", 42)
        assert cache.has("key")

    def test_clear_removes_all(self):
        cache = FrameCache()
        cache.set("a", 1)
        cache.set("b", 2)
        cache.clear()
        assert not cache.has("a")
        assert not cache.has("b")


class TestClearIfNewFrame:
    def test_same_frame_preserves(self):
        cache = FrameCache()
        cache.clear_if_new_frame(10)
        cache.set("x", 100)
        cache.clear_if_new_frame(10)
        assert cache.has("x")

    def test_new_frame_clears(self):
        cache = FrameCache()
        cache.clear_if_new_frame(10)
        cache.set("x", 100)
        cache.clear_if_new_frame(11)
        assert not cache.has("x")

    def test_first_clear_initializes(self):
        cache = FrameCache()
        cache.clear_if_new_frame(0)
        assert cache._last_iteration == 0


class TestCachedPerFrameDecorator:
    def test_cached_method_computes_once_per_frame(self):
        call_count = [0]

        class Manager:
            def __init__(self):
                self._frame_cache = FrameCache()

            @cached_per_frame
            def expensive(self):
                call_count[0] += 1
                return 42

        mgr = Manager()
        mgr._frame_cache.clear_if_new_frame(1)
        mgr.expensive()
        mgr.expensive()
        mgr.expensive()
        assert call_count[0] == 1

    def test_new_frame_recomputes(self):
        call_count = [0]

        class Manager:
            def __init__(self):
                self._frame_cache = FrameCache()

            @cached_per_frame
            def expensive(self):
                call_count[0] += 1
                return "result"

        mgr = Manager()
        mgr._frame_cache.clear_if_new_frame(1)
        mgr.expensive()
        mgr._frame_cache.clear_if_new_frame(2)
        mgr.expensive()
        assert call_count[0] == 2

    def test_cached_returns_correct_value(self):
        class Manager:
            def __init__(self, v):
                self._frame_cache = FrameCache()
                self.v = v

            @cached_per_frame
            def get(self):
                return self.v

        mgr = Manager("hello")
        assert mgr.get() == "hello"
        assert mgr.get() == "hello"

    def test_decorator_falls_back_without_cache(self):
        class Manager:
            @cached_per_frame
            def get(self):
                return 99

        # No _frame_cache attr - should still work
        mgr = Manager()
        assert mgr.get() == 99


class TestDistinctKeys:
    def test_different_args_cached_separately(self):
        class Manager:
            def __init__(self):
                self._frame_cache = FrameCache()

            @cached_per_frame
            def double(self, x):
                return x * 2

        mgr = Manager()
        assert mgr.double(5) == 10
        assert mgr.double(6) == 12
        assert mgr.double(5) == 10  # cached
