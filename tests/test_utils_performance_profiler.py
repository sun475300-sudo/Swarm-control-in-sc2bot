# -*- coding: utf-8 -*-
"""utils.performance_profiler 테스트"""

import sys
import time
import importlib.util
from pathlib import Path
from unittest.mock import MagicMock

import pytest

PROJECT_ROOT = Path(__file__).parent.parent
BOT_ROOT = PROJECT_ROOT / "wicked_zerg_challenger"
if str(BOT_ROOT) not in sys.path:
    sys.path.insert(0, str(BOT_ROOT))


def _load():
    if "bot_perf_profiler" in sys.modules:
        return sys.modules["bot_perf_profiler"]
    spec = importlib.util.spec_from_file_location(
        "bot_perf_profiler", BOT_ROOT / "utils" / "performance_profiler.py"
    )
    mod = importlib.util.module_from_spec(spec)
    sys.modules["bot_perf_profiler"] = mod
    spec.loader.exec_module(mod)
    return mod


class TestInit:
    def test_default(self):
        p = _load().PerformanceProfiler()
        assert p.enabled is True
        assert len(p.timing_data) == 0


class TestProfileDecorator:
    def test_tracks_calls(self):
        p = _load().PerformanceProfiler()
        @p.profile
        def f(x):
            return x + 1
        f(5); f(10)
        keys = list(p.call_counts.keys())
        assert p.call_counts[keys[0]] == 2

    def test_disabled_skips(self):
        p = _load().PerformanceProfiler()
        p.enabled = False
        @p.profile
        def f():
            return 42
        f()
        assert len(p.call_counts) == 0

    def test_returns_value(self):
        p = _load().PerformanceProfiler()
        @p.profile
        def double(x):
            return x * 2
        assert double(5) == 10


class TestFrameTiming:
    def test_start_end(self):
        p = _load().PerformanceProfiler()
        p.start_frame()
        time.sleep(0.001)
        p.end_frame()
        assert len(p.frame_times) == 1

    def test_end_without_start(self):
        p = _load().PerformanceProfiler()
        p.end_frame()
        assert len(p.frame_times) == 0


class TestStats:
    def test_empty(self):
        assert isinstance(_load().PerformanceProfiler().get_stats(), dict)

    def test_bottlenecks(self):
        p = _load().PerformanceProfiler()
        @p.profile
        def f():
            time.sleep(0.001)
        f()
        assert isinstance(p.get_top_bottlenecks(n=5), list)

    def test_frame_stats(self):
        assert isinstance(_load().PerformanceProfiler().get_frame_stats(), dict)


class TestEnableDisableReset:
    def test_disable(self):
        p = _load().PerformanceProfiler()
        p.disable()
        assert p.enabled is False

    def test_enable(self):
        p = _load().PerformanceProfiler()
        p.disable(); p.enable()
        assert p.enabled is True

    def test_reset(self):
        p = _load().PerformanceProfiler()
        @p.profile
        def f():
            pass
        f()
        p.reset()
        assert len(p.call_counts) == 0
