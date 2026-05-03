# -*- coding: utf-8 -*-
"""
Unit tests for DataCacheManager and CacheEntry.

Tests cover:
- TTL expiration and validity
- Cache hit / miss / invalidate / pattern-invalidate
- Statistics tracking
- Convenience helpers (threat level, resource ratio, army composition)
- Periodic cleanup via on_step
- Robustness against compute_func raising
"""

import asyncio
import os
import sys
import time
import unittest
from unittest.mock import MagicMock, Mock

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from data_cache_manager import CacheEntry, DataCacheManager


class TestCacheEntry(unittest.TestCase):
    def test_value_is_returned(self):
        entry = CacheEntry("hello", ttl=10.0)
        self.assertEqual(entry.get_value(), "hello")

    def test_access_count_increments(self):
        entry = CacheEntry(1, ttl=1.0)
        entry.get_value()
        entry.get_value()
        self.assertEqual(entry.access_count, 2)

    def test_is_valid_true_within_ttl(self):
        entry = CacheEntry(1, ttl=10.0)
        self.assertTrue(entry.is_valid())

    def test_is_valid_false_after_ttl(self):
        entry = CacheEntry(1, ttl=0.0)
        # ttl=0 means expired immediately
        time.sleep(0.001)
        self.assertFalse(entry.is_valid())

    def test_zero_ttl_expired(self):
        entry = CacheEntry("x", ttl=-1.0)
        self.assertFalse(entry.is_valid())


class TestDataCacheManagerBasics(unittest.TestCase):
    def setUp(self):
        self.bot = Mock()
        self.cache = DataCacheManager(self.bot)

    def test_default_ttl_keys_present(self):
        for key in ("QUICK", "NORMAL", "SLOW", "VERY_SLOW"):
            self.assertIn(key, self.cache.default_ttl)

    def test_set_and_get_returns_cached_value(self):
        self.cache.set("k", 42, ttl=5.0)
        self.assertEqual(self.cache.get("k"), 42)

    def test_get_missing_returns_none(self):
        self.assertIsNone(self.cache.get("missing"))
        self.assertEqual(self.cache.cache_misses, 1)

    def test_get_with_compute_func(self):
        calls = {"n": 0}

        def compute():
            calls["n"] += 1
            return "computed"

        result = self.cache.get("k", compute, ttl=5.0)
        self.assertEqual(result, "computed")
        self.assertEqual(calls["n"], 1)
        # Second call should hit cache
        result2 = self.cache.get("k", compute, ttl=5.0)
        self.assertEqual(result2, "computed")
        self.assertEqual(calls["n"], 1)
        self.assertGreaterEqual(self.cache.cache_hits, 1)

    def test_compute_func_exception_returns_none(self):
        def boom():
            raise RuntimeError("nope")

        # logger.error is invoked but should not raise
        result = self.cache.get("err", boom, ttl=5.0)
        self.assertIsNone(result)

    def test_invalidate_removes_entry(self):
        self.cache.set("k", "v", ttl=5.0)
        self.cache.invalidate("k")
        self.assertIsNone(self.cache.get("k"))

    def test_invalidate_missing_key_is_safe(self):
        # Should not raise
        self.cache.invalidate("nope")

    def test_invalidate_pattern_removes_matching(self):
        self.cache.set("enemy_a", 1, 5.0)
        self.cache.set("enemy_b", 2, 5.0)
        self.cache.set("self_a", 3, 5.0)
        self.cache.invalidate_pattern("enemy_*")
        self.assertIsNone(self.cache.get("enemy_a"))
        self.assertIsNone(self.cache.get("enemy_b"))
        self.assertEqual(self.cache.get("self_a"), 3)

    def test_clear_empties_cache(self):
        self.cache.set("a", 1, 5.0)
        self.cache.set("b", 2, 5.0)
        self.cache.clear()
        self.assertEqual(len(self.cache.cache), 0)

    def test_expired_entry_is_evicted_on_get(self):
        self.cache.set("k", "v", ttl=-1.0)  # already expired
        # Calling get on expired should miss and evict
        self.assertIsNone(self.cache.get("k"))
        self.assertNotIn("k", self.cache.cache)

    def test_statistics_hit_rate(self):
        self.cache.set("k", 1, 5.0)
        self.cache.get("k")  # hit
        self.cache.get("k")  # hit
        self.cache.get("missing")  # miss
        stats = self.cache.get_statistics()
        self.assertEqual(stats["cache_hits"], 2)
        self.assertEqual(stats["cache_misses"], 1)
        self.assertEqual(stats["total_requests"], 3)
        self.assertIn("%", stats["hit_rate"])

    def test_statistics_zero_requests(self):
        stats = self.cache.get_statistics()
        self.assertEqual(stats["total_requests"], 0)
        self.assertEqual(stats["hit_rate"], "0.0%")

    def test_get_cache_info_structure(self):
        self.cache.set("k", "v", ttl=5.0)
        info = self.cache.get_cache_info()
        self.assertEqual(len(info), 1)
        entry = info[0]
        self.assertEqual(entry["key"], "k")
        self.assertTrue(entry["valid"])
        self.assertIn("age", entry)
        self.assertIn("remaining", entry)


class TestDataCacheManagerCleanup(unittest.TestCase):
    def setUp(self):
        self.bot = Mock()
        self.cache = DataCacheManager(self.bot)

    def test_cleanup_removes_expired(self):
        self.cache.set("alive", 1, ttl=60.0)
        self.cache.set("dead", 2, ttl=-1.0)
        self.cache._cleanup_expired()
        self.assertIn("alive", self.cache.cache)
        self.assertNotIn("dead", self.cache.cache)

    def test_on_step_runs_periodic_cleanup(self):
        self.cache.set("dead", 1, ttl=-1.0)
        # Force cleanup by setting last_cleanup far in the past
        self.cache.last_cleanup = 0
        asyncio.run(self.cache.on_step(0))
        self.assertNotIn("dead", self.cache.cache)

    def test_on_step_does_not_raise_when_bot_attr_missing(self):
        # Even if compute funcs fail, on_step should swallow errors
        asyncio.run(self.cache.on_step(0))


class TestDataCacheManagerHelpers(unittest.TestCase):
    def setUp(self):
        self.bot = Mock()
        self.cache = DataCacheManager(self.bot)

    def test_compute_threat_level_no_intel(self):
        self.bot.intel = None
        self.assertEqual(self.cache._compute_threat_level(), "NONE")

    def test_compute_threat_level_critical(self):
        intel = Mock()
        intel._under_attack = True
        intel.enemy_army_supply = 80
        self.bot.intel = intel
        self.assertEqual(self.cache._compute_threat_level(), "CRITICAL")

    def test_compute_threat_level_high(self):
        intel = Mock()
        intel._under_attack = True
        intel.enemy_army_supply = 35
        self.bot.intel = intel
        self.assertEqual(self.cache._compute_threat_level(), "HIGH")

    def test_compute_threat_level_medium(self):
        intel = Mock()
        intel._under_attack = True
        intel.enemy_army_supply = 20
        self.bot.intel = intel
        self.assertEqual(self.cache._compute_threat_level(), "MEDIUM")

    def test_compute_threat_level_low(self):
        intel = Mock()
        intel._under_attack = True
        intel.enemy_army_supply = 5
        self.bot.intel = intel
        self.assertEqual(self.cache._compute_threat_level(), "LOW")

    def test_compute_threat_level_not_under_attack_is_none(self):
        intel = Mock()
        intel._under_attack = False
        intel.enemy_army_supply = 100
        self.bot.intel = intel
        self.assertEqual(self.cache._compute_threat_level(), "NONE")

    def test_compute_resource_ratio_no_gas(self):
        self.bot.minerals = 500
        self.bot.vespene = 0
        self.assertEqual(self.cache._compute_resource_ratio(), 10.0)

    def test_compute_resource_ratio_normal(self):
        self.bot.minerals = 600
        self.bot.vespene = 200
        self.assertEqual(self.cache._compute_resource_ratio(), 3.0)

    def test_compute_enemy_build_pattern_unknown(self):
        # No intel attribute -> UNKNOWN
        # Mock returns truthy for hasattr check, so explicitly delete
        del self.bot.intel
        # Explicitly set to None for the second branch
        self.bot.intel = None
        self.assertEqual(self.cache._compute_enemy_build_pattern(), "UNKNOWN")

    def test_compute_enemy_build_pattern_air(self):
        intel = Mock()
        intel.enemy_tech_buildings = {"STARGATE"}
        self.bot.intel = intel
        self.assertEqual(self.cache._compute_enemy_build_pattern(), "AIR")

    def test_compute_enemy_build_pattern_ground_mech(self):
        intel = Mock()
        intel.enemy_tech_buildings = {"FACTORY"}
        self.bot.intel = intel
        self.assertEqual(self.cache._compute_enemy_build_pattern(), "GROUND_MECH")

    def test_compute_enemy_build_pattern_gateway(self):
        intel = Mock()
        intel.enemy_tech_buildings = {"TWILIGHTCOUNCIL"}
        self.bot.intel = intel
        self.assertEqual(self.cache._compute_enemy_build_pattern(), "GATEWAY")

    def test_compute_enemy_build_pattern_standard_when_empty_set(self):
        intel = Mock()
        intel.enemy_tech_buildings = set()
        self.bot.intel = intel
        self.assertEqual(self.cache._compute_enemy_build_pattern(), "STANDARD")

    def test_compute_army_composition_counts(self):
        u1 = Mock()
        u1.type_id = MagicMock()
        u1.type_id.name = "Zergling"
        u2 = Mock()
        u2.type_id = MagicMock()
        u2.type_id.name = "Zergling"
        u3 = Mock()
        u3.type_id = MagicMock()
        u3.type_id.name = "Drone"  # not an army type
        self.bot.units = [u1, u2, u3]
        comp = self.cache._compute_army_composition()
        self.assertEqual(comp.get("ZERGLING"), 2)
        self.assertNotIn("DRONE", comp)

    def test_compute_enemy_army_composition_counts(self):
        u1 = Mock()
        u1.type_id = MagicMock()
        u1.type_id.name = "Marine"
        u2 = Mock()
        u2.type_id = MagicMock()
        u2.type_id.name = "Marine"
        self.bot.enemy_units = [u1, u2]
        comp = self.cache._compute_enemy_army_composition()
        self.assertEqual(comp.get("MARINE"), 2)


if __name__ == "__main__":
    unittest.main()
