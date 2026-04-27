# -*- coding: utf-8 -*-
"""Tests for DataCacheManager - TTL-based caching with auto-cleanup."""

import sys
import time
import pytest

sys.path.insert(0, "wicked_zerg_challenger")

from data_cache_manager import DataCacheManager, CacheEntry


class _FakeBot:
    pass


class TestCacheEntry:
    def test_is_valid_immediately(self):
        entry = CacheEntry("value", ttl=10.0)
        assert entry.is_valid()

    def test_is_invalid_after_ttl(self):
        entry = CacheEntry("value", ttl=0.01)
        time.sleep(0.02)
        assert not entry.is_valid()

    def test_get_value_increments_access(self):
        entry = CacheEntry("hello", ttl=10.0)
        entry.get_value()
        entry.get_value()
        assert entry.access_count == 2

    def test_get_value_returns_stored(self):
        entry = CacheEntry({"key": 42}, ttl=10.0)
        assert entry.get_value() == {"key": 42}


class TestBasicCaching:
    def setup_method(self):
        self.mgr = DataCacheManager(_FakeBot())

    def test_get_miss_without_compute(self):
        assert self.mgr.get("missing_key") is None

    def test_get_miss_with_compute(self):
        result = self.mgr.get("key", lambda: 42, ttl=10.0)
        assert result == 42

    def test_hit_returns_cached(self):
        self.mgr.set("key", 100, ttl=10.0)
        assert self.mgr.get("key") == 100

    def test_ttl_expiry_recomputes(self):
        calls = [0]

        def compute():
            calls[0] += 1
            return calls[0]

        self.mgr.get("k", compute, ttl=0.01)
        time.sleep(0.02)
        result = self.mgr.get("k", compute, ttl=10.0)
        assert result == 2  # recomputed after expiry

    def test_stats_tracks_hits_misses(self):
        self.mgr.get("a", lambda: 1)  # miss
        self.mgr.get("a")  # hit
        assert self.mgr.cache_misses == 1
        assert self.mgr.cache_hits == 1


class TestCacheInvalidation:
    def setup_method(self):
        self.mgr = DataCacheManager(_FakeBot())

    def test_invalidate_removes_key(self):
        self.mgr.set("foo", 1, ttl=10.0)
        self.mgr.invalidate("foo")
        assert self.mgr.get("foo") is None

    def test_invalidate_missing_key_does_not_raise(self):
        self.mgr.invalidate("nonexistent")  # should not raise

    def test_invalidate_pattern_matches_prefix(self):
        self.mgr.set("enemy_build", "4pool", ttl=10.0)
        self.mgr.set("enemy_units", ["ling"], ttl=10.0)
        self.mgr.set("friendly_army", 10, ttl=10.0)

        self.mgr.invalidate_pattern("enemy_*")

        assert self.mgr.get("enemy_build") is None
        assert self.mgr.get("enemy_units") is None
        assert self.mgr.get("friendly_army") == 10

    def test_clear_removes_all(self):
        self.mgr.set("a", 1, ttl=10.0)
        self.mgr.set("b", 2, ttl=10.0)
        self.mgr.clear()
        assert len(self.mgr.cache) == 0


class TestCleanupExpired:
    def test_cleanup_removes_expired(self):
        mgr = DataCacheManager(_FakeBot())
        mgr.set("short", 1, ttl=0.01)
        mgr.set("long", 2, ttl=10.0)
        time.sleep(0.02)

        mgr._cleanup_expired()

        assert "short" not in mgr.cache
        assert "long" in mgr.cache


class TestComputeErrorHandling:
    def test_compute_exception_returns_none(self):
        mgr = DataCacheManager(_FakeBot())

        def bad_compute():
            raise RuntimeError("boom")

        result = mgr.get("error_key", bad_compute, ttl=10.0)
        assert result is None


class TestDefaultTTLs:
    def test_default_ttls_defined(self):
        mgr = DataCacheManager(_FakeBot())
        assert "QUICK" in mgr.default_ttl
        assert "NORMAL" in mgr.default_ttl
        assert "SLOW" in mgr.default_ttl
        assert "VERY_SLOW" in mgr.default_ttl

    def test_ttl_ordering(self):
        mgr = DataCacheManager(_FakeBot())
        assert mgr.default_ttl["QUICK"] < mgr.default_ttl["NORMAL"]
        assert mgr.default_ttl["NORMAL"] < mgr.default_ttl["SLOW"]
        assert mgr.default_ttl["SLOW"] < mgr.default_ttl["VERY_SLOW"]
