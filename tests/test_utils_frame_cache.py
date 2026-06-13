# -*- coding: utf-8 -*-
"""utils.frame_cache 테스트 - 프레임 기반 캐싱"""

import sys
import importlib.util
from pathlib import Path

import pytest

PROJECT_ROOT = Path(__file__).parent.parent
BOT_ROOT = PROJECT_ROOT / "wicked_zerg_challenger"
if str(BOT_ROOT) not in sys.path:
    sys.path.insert(0, str(BOT_ROOT))


def _load():
    if "bot_frame_cache" in sys.modules:
        return sys.modules["bot_frame_cache"]
    spec = importlib.util.spec_from_file_location(
        "bot_frame_cache", BOT_ROOT / "utils" / "frame_cache.py"
    )
    mod = importlib.util.module_from_spec(spec)
    sys.modules["bot_frame_cache"] = mod
    spec.loader.exec_module(mod)
    return mod


class TestFrameCache:
    def test_init_empty(self):
        c = _load().FrameCache()
        assert c._cache == {}
        assert c._last_iteration == -1

    def test_set_get(self):
        c = _load().FrameCache()
        c.set("k", "v")
        assert c.get("k") == "v"

    def test_get_default(self):
        c = _load().FrameCache()
        assert c.get("x", "default") == "default"

    def test_has(self):
        c = _load().FrameCache()
        assert c.has("k") is False
        c.set("k", 1)
        assert c.has("k") is True

    def test_clear(self):
        c = _load().FrameCache()
        c.set("a", 1)
        c.clear()
        assert c._cache == {}

    def test_same_iteration_keeps(self):
        c = _load().FrameCache()
        c.clear_if_new_frame(100)
        c.set("k", "v")
        c.clear_if_new_frame(100)
        assert c.has("k")

    def test_new_iteration_clears(self):
        c = _load().FrameCache()
        c.clear_if_new_frame(100)
        c.set("k", "v")
        c.clear_if_new_frame(101)
        assert not c.has("k")


class TestCachedPerFrame:
    def test_caches_result(self):
        mod = _load()
        class M:
            def __init__(self):
                self._frame_cache = mod.FrameCache()
                self.count = 0
            @mod.cached_per_frame
            def expensive(self):
                self.count += 1
                return self.count
        m = M()
        assert m.expensive() == m.expensive()
        assert m.count == 1

    def test_clears_on_new_frame(self):
        mod = _load()
        class M:
            def __init__(self):
                self._frame_cache = mod.FrameCache()
                self.count = 0
            @mod.cached_per_frame
            def expensive(self):
                self.count += 1
                return self.count
        m = M()
        m.expensive()
        m._frame_cache.clear_if_new_frame(1)
        m.expensive()
        assert m.count == 2

    def test_no_cache_falls_through(self):
        mod = _load()
        class NC:
            @mod.cached_per_frame
            def f(self):
                return 42
        assert NC().f() == 42
