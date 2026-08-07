"""Tests for wicked_zerg_challenger/utils/distance_cache.py."""
from __future__ import annotations

from math import hypot
from types import SimpleNamespace

import pytest

from wicked_zerg_challenger.utils.distance_cache import (
    DistanceCache,
    cached_distance,
)


class P:
    __slots__ = ("x", "y")

    def __init__(self, x: float, y: float):
        self.x = float(x)
        self.y = float(y)

    def distance_to(self, other) -> float:
        return hypot(self.x - other.x, self.y - other.y)


# ---------------------------------------------------------------------------
# DistanceCache primitive
# ---------------------------------------------------------------------------

def test_first_call_is_miss_returns_correct_distance():
    cache = DistanceCache()
    d = cache.get(P(0, 0), P(3, 4), current_frame=1)
    assert d == pytest.approx(5.0)
    assert cache._misses == 1
    assert cache._hits == 0


def test_repeated_same_frame_hits():
    cache = DistanceCache()
    cache.get(P(0, 0), P(3, 4), current_frame=1)
    cache.get(P(0, 0), P(3, 4), current_frame=1)
    cache.get(P(0, 0), P(3, 4), current_frame=1)
    assert cache._hits == 2
    assert cache._misses == 1


def test_new_frame_resets_cache_and_stats():
    cache = DistanceCache()
    cache.get(P(0, 0), P(3, 4), current_frame=1)
    cache.get(P(0, 0), P(3, 4), current_frame=2)
    assert cache.size == 1  # one entry under new frame
    assert cache._hits == 0
    assert cache._misses == 1


def test_key_is_unordered():
    """get(a, b) and get(b, a) should hit the same cache slot."""
    cache = DistanceCache()
    cache.get(P(0, 0), P(3, 4), current_frame=1)
    cache.get(P(3, 4), P(0, 0), current_frame=1)
    # second call should be a HIT, not a miss
    assert cache._hits == 1
    assert cache._misses == 1


def test_extracts_position_attribute_from_units():
    """If passed an object with .position, that position is used."""
    cache = DistanceCache()
    unit_a = SimpleNamespace(position=P(0, 0))
    unit_b = SimpleNamespace(position=P(6, 8))
    d = cache.get(unit_a, unit_b, current_frame=1)
    assert d == pytest.approx(10.0)


def test_hit_rate_property():
    cache = DistanceCache()
    cache.get(P(0, 0), P(1, 0), current_frame=1)  # miss
    cache.get(P(0, 0), P(1, 0), current_frame=1)  # hit
    cache.get(P(0, 0), P(1, 0), current_frame=1)  # hit
    assert cache.hit_rate == pytest.approx(2 / 3)


def test_hit_rate_zero_when_no_calls():
    cache = DistanceCache()
    assert cache.hit_rate == 0.0


def test_size_grows_with_unique_pairs():
    cache = DistanceCache()
    cache.get(P(0, 0), P(1, 0), current_frame=1)
    cache.get(P(0, 0), P(2, 0), current_frame=1)
    cache.get(P(0, 0), P(3, 0), current_frame=1)
    assert cache.size == 3


def test_key_rounds_to_one_decimal():
    """Positions within 0.05 should collide on cache key (1-decimal rounding)."""
    cache = DistanceCache()
    cache.get(P(0.00, 0), P(1.00, 0), current_frame=1)
    # 0.04 difference rounds away → same key as above
    cache.get(P(0.04, 0), P(1.04, 0), current_frame=1)
    assert cache._hits == 1


# ---------------------------------------------------------------------------
# Module-level convenience
# ---------------------------------------------------------------------------

def test_cached_distance_uses_shared_cache():
    # Use a unique frame to avoid contention with other tests
    d = cached_distance(P(0, 0), P(3, 4), frame=987654)
    assert d == pytest.approx(5.0)
