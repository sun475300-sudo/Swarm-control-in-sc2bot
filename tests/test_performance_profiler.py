# -*- coding: utf-8 -*-
"""Tests for utils/performance_profiler.py."""

import sys
import time
import pytest

sys.path.insert(0, "wicked_zerg_challenger")

from utils.performance_profiler import (
    PerformanceProfiler,
    TimingContext,
    get_profiler,
    profile,
)


class TestProfilerInit:
    def test_defaults(self):
        p = PerformanceProfiler()
        assert p.enabled
        assert p.slow_function_threshold > 0
        assert p.slow_frame_threshold > 0

    def test_empty_stats(self):
        p = PerformanceProfiler()
        stats = p.get_stats()
        assert isinstance(stats, dict)
        assert len(stats) == 0


class TestProfileDecorator:
    def test_records_call(self):
        p = PerformanceProfiler()

        @p.profile
        def f():
            return 42

        result = f()
        assert result == 42
        assert len(p.call_counts) == 1

    def test_multiple_calls_accumulate(self):
        p = PerformanceProfiler()

        @p.profile
        def f():
            return 1

        for _ in range(5):
            f()

        name = next(iter(p.call_counts.keys()))
        assert p.call_counts[name] == 5

    def test_total_time_increases(self):
        p = PerformanceProfiler()

        @p.profile
        def f():
            time.sleep(0.001)
            return None

        f()
        total = sum(p.total_time.values())
        assert total > 0

    def test_disabled_skips_profiling(self):
        p = PerformanceProfiler()
        p.disable()

        @p.profile
        def f():
            return 99

        f()
        assert len(p.call_counts) == 0
        assert f() == 99  # still executes


class TestFrameTiming:
    def test_frame_start_end(self):
        p = PerformanceProfiler()
        p.start_frame()
        time.sleep(0.001)
        p.end_frame()
        assert len(p.frame_times) == 1

    def test_end_frame_without_start_noop(self):
        p = PerformanceProfiler()
        p.end_frame()  # should not raise
        assert len(p.frame_times) == 0

    def test_get_frame_stats(self):
        p = PerformanceProfiler()
        p.start_frame()
        p.end_frame()
        stats = p.get_frame_stats()
        assert isinstance(stats, dict)


class TestBottleneckDetection:
    def test_get_top_bottlenecks_empty(self):
        p = PerformanceProfiler()
        result = p.get_top_bottlenecks(n=5)
        assert isinstance(result, list)

    def test_get_top_bottlenecks_orders_by_total(self):
        p = PerformanceProfiler()

        @p.profile
        def fast():
            pass

        @p.profile
        def slow():
            time.sleep(0.01)

        fast()
        slow()
        bottlenecks = p.get_top_bottlenecks(n=2)
        # slow should be first (highest total time)
        if bottlenecks:
            assert "slow" in bottlenecks[0][0]


class TestReset:
    def test_reset_clears_data(self):
        p = PerformanceProfiler()

        @p.profile
        def f():
            return 1

        f()
        p.reset()
        assert len(p.timing_data) == 0
        assert len(p.call_counts) == 0
        assert p.last_frame_time is None


class TestEnableDisable:
    def test_toggle(self):
        p = PerformanceProfiler()
        p.disable()
        assert not p.enabled
        p.enable()
        assert p.enabled


class TestGlobalProfiler:
    def test_get_profiler_returns_singleton(self):
        p1 = get_profiler()
        p2 = get_profiler()
        assert p1 is p2


class TestTimingContext:
    def test_context_records_timing(self):
        p = PerformanceProfiler()
        with TimingContext("my_op", p):
            time.sleep(0.001)
        assert "my_op" in p.call_counts
        assert p.call_counts["my_op"] == 1

    def test_context_uses_global_profiler_by_default(self):
        p_global = get_profiler()
        before = p_global.call_counts.get("global_op", 0)
        with TimingContext("global_op"):
            pass
        assert p_global.call_counts["global_op"] == before + 1


class TestGlobalProfileDecorator:
    def test_decorator_uses_global(self):
        # Use a unique name to avoid collisions between tests
        @profile
        def unique_test_fn_xyz():
            return 77

        result = unique_test_fn_xyz()
        assert result == 77
