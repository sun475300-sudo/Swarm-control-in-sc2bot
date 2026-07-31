# -*- coding: utf-8 -*-
"""
Distance cache rollout tests (Roadmap Sprint 7 / Task 7.2).

Covers:
1. DistanceCache correctness + per-frame invalidation + hit-rate tracking
2. CombatManager/EconomyManager `_distance_between` wiring actually uses the
   shared per-instance cache (not just falling back to raw distance_to every call)
"""

import os
import sys

import pytest

sys.path.insert(
    0, os.path.join(os.path.dirname(__file__), "..", "wicked_zerg_challenger")
)

try:
    from combat_manager import CombatManager
    from economy_manager import EconomyManager
    from sc2.position import Point2

    from utils.distance_cache import DistanceCache
except ImportError:
    pytest.skip("SC2 bot modules not available", allow_module_level=True)

from tests.test_combat_manager import MockBot


class TestDistanceCache:
    def test_correctness(self):
        cache = DistanceCache()
        a = Point2((0, 0))
        b = Point2((3, 4))
        assert cache.get(a, b, current_frame=1) == pytest.approx(5.0)

    def test_repeated_lookup_hits_cache(self):
        cache = DistanceCache()
        a = Point2((0, 0))
        b = Point2((3, 4))
        cache.get(a, b, current_frame=1)
        cache.get(a, b, current_frame=1)
        cache.get(b, a, current_frame=1)  # order-independent key
        assert cache.hit_rate == pytest.approx(2 / 3)
        assert cache.size == 1

    def test_new_frame_invalidates_cache(self):
        cache = DistanceCache()
        a = Point2((0, 0))
        b = Point2((3, 4))
        cache.get(a, b, current_frame=1)
        cache.get(a, b, current_frame=2)
        assert cache.size == 1
        assert cache.hit_rate == 0.0  # frame 2 started with a fresh miss


class TestManagerDistanceCacheWiring:
    def test_combat_manager_reuses_cache_within_frame(self):
        bot = MockBot()
        bot.iteration = 10
        combat = CombatManager(bot)

        a = Point2((0, 0))
        b = Point2((3, 4))
        combat._distance_between(a, b)
        combat._distance_between(a, b)

        assert combat.distance_cache.size == 1
        assert combat.distance_cache.hit_rate == pytest.approx(0.5)

    def test_economy_manager_reuses_cache_within_frame(self):
        bot = MockBot()
        bot.iteration = 10
        economy = EconomyManager(bot)

        a = Point2((0, 0))
        b = Point2((3, 4))
        economy._distance_between(a, b)
        economy._distance_between(a, b)
        economy._distance_between(a, b)

        assert economy.distance_cache.size == 1
        assert economy.distance_cache.hit_rate == pytest.approx(2 / 3)
