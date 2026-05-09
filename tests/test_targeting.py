# -*- coding: utf-8 -*-
"""Tests for `targeting` — score / prioritize / select. sc2-free.

This module is already sc2-guarded so we can import it normally if the
project root is on sys.path (conftest takes care of that).
"""
from __future__ import annotations

import importlib.util
from pathlib import Path
from types import SimpleNamespace
from typing import Iterable, List

import pytest


_TG_PATH = (
    Path(__file__).resolve().parent.parent
    / "wicked_zerg_challenger"
    / "combat"
    / "targeting.py"
)
try:
    _spec = importlib.util.spec_from_file_location("targeting_t", _TG_PATH)
    if _spec is None or _spec.loader is None:
        raise ImportError(f"cannot build spec for {_TG_PATH}")
    _mod = importlib.util.module_from_spec(_spec)
    _spec.loader.exec_module(_mod)
except Exception as exc:  # pragma: no cover
    pytest.skip(f"targeting not importable: {exc}", allow_module_level=True)

prioritize_targets = _mod.prioritize_targets
select_target = _mod.select_target
Targeting = _mod.Targeting
_score_target = _mod._score_target


# ---------------------------------------------------------------------------
# Fakes
# ---------------------------------------------------------------------------
class _FakeUnit:
    """A unit with the attributes _score_target reads."""

    def __init__(
        self,
        tag: int,
        type_id=None,
        health: int = 100,
        health_max: int = 100,
        shield: int = 0,
        shield_max: int = 0,
        ground_dps: float = 0.0,
        air_dps: float = 0.0,
        is_flying: bool = False,
        is_cloaked: bool = False,
        x: float = 0,
        y: float = 0,
    ):
        self.tag = tag
        self.type_id = type_id
        self.health = health
        self.health_max = health_max
        self.shield = shield
        self.shield_max = shield_max
        self.ground_dps = ground_dps
        self.air_dps = air_dps
        self.is_flying = is_flying
        self.is_cloaked = is_cloaked
        self.position = SimpleNamespace(x=float(x), y=float(y))


class _Enemies(list):
    def closer_than(self, radius: float, position) -> "_Enemies":
        out = _Enemies()
        for u in self:
            dx = u.position.x - position.x
            dy = u.position.y - position.y
            if (dx * dx + dy * dy) ** 0.5 <= radius:
                out.append(u)
        return out


# ---------------------------------------------------------------------------
# _score_target — pure scoring
# ---------------------------------------------------------------------------
class TestScoreTarget:
    def test_none_returns_sentinel(self):
        assert _score_target(None) == -999.0

    def test_low_priority_returns_negative(self):
        # Synthetic LOW_PRIORITY_TYPES membership using a sentinel
        sentinel = object()
        # Inject sentinel into LOW_PRIORITY_TYPES for this test
        _mod.LOW_PRIORITY_TYPES.add(sentinel)
        try:
            u = _FakeUnit(tag=1, type_id=sentinel)
            assert _score_target(u) == -100.0
        finally:
            _mod.LOW_PRIORITY_TYPES.discard(sentinel)

    def test_low_health_increases_score(self):
        full = _FakeUnit(tag=1, health=100, health_max=100)
        low = _FakeUnit(tag=2, health=10, health_max=100)
        assert _score_target(low) > _score_target(full)

    def test_high_dps_increases_score(self):
        slow = _FakeUnit(tag=1, ground_dps=0.0)
        fast = _FakeUnit(tag=2, ground_dps=30.0)
        assert _score_target(fast) > _score_target(slow)

    def test_high_value_unit_bonus(self):
        sentinel = object()
        _mod.HIGH_VALUE_TYPES.add(sentinel)
        try:
            normal = _FakeUnit(tag=1, type_id=None)
            elite = _FakeUnit(tag=2, type_id=sentinel)
            assert _score_target(elite) > _score_target(normal) + 4  # +5 bonus minus other deltas
        finally:
            _mod.HIGH_VALUE_TYPES.discard(sentinel)

    def test_kill_secure_bonus_when_below_30_pct(self):
        almost_dead = _FakeUnit(tag=1, health=20, health_max=100)
        half = _FakeUnit(tag=2, health=50, health_max=100)
        # Both lose health-pct bonus, but almost_dead also gets +2 kill bonus
        assert _score_target(almost_dead) > _score_target(half) + 1.5

    def test_flying_and_cloaked_bonuses_stack(self):
        plain = _FakeUnit(tag=1)
        flying = _FakeUnit(tag=2, is_flying=True)
        cloaked = _FakeUnit(tag=3, is_cloaked=True)
        assert _score_target(flying) > _score_target(plain)
        assert _score_target(cloaked) > _score_target(plain)


# ---------------------------------------------------------------------------
# prioritize_targets
# ---------------------------------------------------------------------------
class TestPrioritizeTargets:
    def test_none_returns_empty(self):
        assert prioritize_targets(None) == []

    def test_empty_returns_empty(self):
        assert prioritize_targets([]) == []

    def test_filters_none_units(self):
        u = _FakeUnit(tag=1)
        assert prioritize_targets([None, u, None]) == [u]

    def test_sorts_by_score_descending(self):
        full_health = _FakeUnit(tag=1, health=100, health_max=100)
        low_health = _FakeUnit(tag=2, health=10, health_max=100)
        result = prioritize_targets([full_health, low_health])
        assert result[0] is low_health  # higher score first

    def test_uses_cache_for_same_frame_and_enemies(self):
        # Reset cache
        _mod._prioritized_cache.update({"enemies_id": None, "result": [], "frame": -1})
        u1 = _FakeUnit(tag=1)
        u2 = _FakeUnit(tag=2)
        first = prioritize_targets([u1, u2], current_frame=10)
        # Mutate one unit's stats — cache should still return original ranking
        u1.health = 1
        cached = prioritize_targets([u1, u2], current_frame=10)
        assert cached is first or cached == first

    def test_cache_invalidates_on_new_frame(self):
        _mod._prioritized_cache.update({"enemies_id": None, "result": [], "frame": -1})
        u1 = _FakeUnit(tag=1, health=100, health_max=100)
        u2 = _FakeUnit(tag=2, health=100, health_max=100)
        _ = prioritize_targets([u1, u2], current_frame=10)
        # Same enemies, but frame moved — cache miss → re-sort
        u2.health = 5  # u2 should now win
        result = prioritize_targets([u1, u2], current_frame=11)
        assert result[0] is u2


# ---------------------------------------------------------------------------
# select_target
# ---------------------------------------------------------------------------
class TestSelectTarget:
    def test_unit_none_returns_none(self):
        assert select_target(None, [_FakeUnit(tag=1)]) is None

    def test_enemies_none_returns_none(self):
        assert select_target(_FakeUnit(tag=1), None) is None

    def test_no_enemies_returns_none(self):
        assert select_target(_FakeUnit(tag=1), []) is None

    def test_uses_closer_than_for_range_filter(self):
        u = _FakeUnit(tag=99, x=0, y=0)
        near = _FakeUnit(tag=1, x=3, y=0, health=10, health_max=100)
        far = _FakeUnit(tag=2, x=50, y=50, health=10, health_max=100)
        enemies = _Enemies([near, far])
        # Default max_range=12 → only `near` in scope
        target = select_target(u, enemies, max_range=12.0)
        assert target is near

    def test_picks_highest_priority_in_range(self):
        u = _FakeUnit(tag=99, x=0, y=0)
        full = _FakeUnit(tag=1, x=2, y=0, health=100, health_max=100)
        wounded = _FakeUnit(tag=2, x=3, y=0, health=10, health_max=100)
        enemies = _Enemies([full, wounded])
        # wounded has higher priority due to low health bonus
        target = select_target(u, enemies, max_range=20.0)
        assert target is wounded


# ---------------------------------------------------------------------------
# Targeting wrapper class
# ---------------------------------------------------------------------------
class TestTargetingClass:
    def test_score_none_returns_sentinel(self):
        t = Targeting(bot=SimpleNamespace())
        assert t.score(None) == -999.0

    def test_prioritize_returns_sorted_list(self):
        t = Targeting(bot=SimpleNamespace())
        u1 = _FakeUnit(tag=1, health=100, health_max=100)
        u2 = _FakeUnit(tag=2, health=10, health_max=100)
        result = t.prioritize([u1, u2])
        assert result[0] is u2

    def test_legacy_get_priority_target_with_enemies_and_position(self):
        t = Targeting(bot=SimpleNamespace())
        u1 = _FakeUnit(tag=1, health=10, health_max=100)
        u2 = _FakeUnit(tag=2, health=100, health_max=100)
        # Legacy signature: (enemies, position_tuple)
        result = t.get_priority_target([u1, u2], (0, 0))
        assert result is u1

    def test_new_api_get_priority_target_with_unit_and_enemies(self):
        t = Targeting(bot=SimpleNamespace())
        u = _FakeUnit(tag=99, x=0, y=0)
        wounded = _FakeUnit(tag=1, x=3, y=0, health=10, health_max=100)
        # New signature: (unit, enemies)
        result = t.get_priority_target(u, _Enemies([wounded]))
        assert result is wounded

    def test_focus_fire_target_aliases(self):
        t = Targeting(bot=SimpleNamespace())
        u1 = _FakeUnit(tag=1, health=10, health_max=100)
        u2 = _FakeUnit(tag=2, health=100, health_max=100)
        assert t.get_focus_fire_target([u1, u2]) is u1
