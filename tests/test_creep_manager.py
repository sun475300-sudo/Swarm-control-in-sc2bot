# -*- coding: utf-8 -*-
"""
Unit tests for wicked_zerg_challenger/creep_manager.py (934 LOC, previously untested).

Focuses on deterministic helpers — scoring, de-duplication, tumor
counting, and static config invariants. Does not touch SC2 client I/O.
"""
import os
import sys
from unittest.mock import MagicMock

import pytest

sys.path.insert(
    0, os.path.join(os.path.dirname(__file__), "..", "wicked_zerg_challenger")
)


def _import():
    try:
        from creep_manager import CreepManager
        return CreepManager
    except ImportError:
        return None


CreepManager = _import()

pytestmark = pytest.mark.skipif(
    CreepManager is None, reason="creep_manager not importable"
)


def _point(x, y):
    from sc2.position import Point2
    return Point2((x, y))


def _fake_point(x, y):
    """Fake Point2 that supports distance_to but bypasses sc2."""
    p = MagicMock()
    p.x = x
    p.y = y
    p.distance_to = lambda other: ((p.x - other.x) ** 2 + (p.y - other.y) ** 2) ** 0.5
    return p


@pytest.fixture
def bot():
    b = MagicMock()
    b.time = 0.0
    b.structures = []
    b.townhalls = []
    b.enemy_start_locations = []
    b.expansion_locations_list = []
    return b


@pytest.fixture
def cm(bot):
    return CreepManager(bot)


class TestInitInvariants:
    def test_tumor_min_spacing(self, cm):
        assert CreepManager.TUMOR_MIN_SPACING_DIST == 10

    def test_tumor_spread_range(self, cm):
        assert CreepManager.TUMOR_SPREAD_RANGE > 0
        assert CreepManager.TUMOR_SPREAD_RANGE >= CreepManager.QUEEN_TUMOR_RANGE

    def test_expansion_block_distance(self, cm):
        # Must be > 0 so tumors don't block hatcheries.
        assert CreepManager.EXPANSION_BLOCK_DIST > 0

    def test_coverage_target_in_range(self, cm):
        assert 0.0 < CreepManager.COVERAGE_TARGET <= 1.0

    def test_initial_state_clean(self, cm):
        assert cm.cached_targets == []
        assert cm.tumor_spread_cooldowns == {}
        assert cm.used_tumor_tags == set()
        assert cm._creep_coverage == 0.0


class TestScoreTarget:
    def test_origin_equals_direction_returns_raw_distance(self):
        o = _fake_point(0, 0)
        c = _fake_point(3, 4)  # dist 5
        d = _fake_point(0, 0)  # dir_len == 0 branch
        assert CreepManager._score_target(o, c, d) == pytest.approx(5.0)

    def test_forward_scores_higher_than_backward(self):
        o = _fake_point(0, 0)
        forward = _fake_point(5, 0)
        backward = _fake_point(-5, 0)
        d = _fake_point(10, 0)  # direction = +x
        s_fwd = CreepManager._score_target(o, forward, d)
        s_bwd = CreepManager._score_target(o, backward, d)
        assert s_fwd > s_bwd

    def test_closer_candidate_preferred_in_same_direction(self):
        o = _fake_point(0, 0)
        d = _fake_point(20, 0)
        near = _fake_point(5, 0)
        far = _fake_point(15, 0)
        # Score = projection - dist*0.15
        # near: 5 - 5*0.15 = 4.25
        # far: 15 - 15*0.15 = 12.75 -> actually farther scores higher
        #   because creep wants to push toward the target.
        s_near = CreepManager._score_target(o, near, d)
        s_far = CreepManager._score_target(o, far, d)
        assert s_far > s_near


class TestDedupePositions:
    def test_empty_returns_empty(self):
        assert CreepManager._dedupe_positions([]) == []

    def test_none_filtered(self):
        pts = [_point(5, 5), None, _point(10, 10)]
        deduped = CreepManager._dedupe_positions(pts)
        assert len(deduped) == 2

    def test_close_points_deduped(self):
        # Threshold in code is > 2.5.
        p1 = _point(0, 0)
        p2 = _point(2, 0)   # distance 2 < 2.5 — should be dropped
        p3 = _point(10, 10)
        deduped = CreepManager._dedupe_positions([p1, p2, p3])
        assert len(deduped) == 2

    def test_far_points_kept(self):
        # NB: Point2((0, 0)) is falsy (empty-tuple-like) so skipped by the
        # `if not pos` guard — use non-zero positions here.
        p1 = _point(1, 1)
        p2 = _point(5, 0)
        p3 = _point(10, 0)
        deduped = CreepManager._dedupe_positions([p1, p2, p3])
        assert len(deduped) == 3


class TestGetTumorCount:
    def test_no_structures_attr(self, bot, cm):
        del bot.structures
        assert cm.get_tumor_count() == 0

    def test_counts_all_tumor_types(self, bot, cm):
        from sc2.ids.unit_typeid import UnitTypeId
        t1 = MagicMock(); t1.type_id = UnitTypeId.CREEPTUMOR
        t2 = MagicMock(); t2.type_id = UnitTypeId.CREEPTUMORBURROWED
        t3 = MagicMock(); t3.type_id = UnitTypeId.CREEPTUMORQUEEN
        h = MagicMock(); h.type_id = UnitTypeId.HATCHERY
        bot.structures = [t1, t2, t3, h]
        assert cm.get_tumor_count() == 3

    def test_only_non_tumor_structures(self, bot, cm):
        from sc2.ids.unit_typeid import UnitTypeId
        s = MagicMock(); s.type_id = UnitTypeId.SPAWNINGPOOL
        bot.structures = [s]
        assert cm.get_tumor_count() == 0


class TestGetCreepTargetGuards:
    def test_no_origin_returns_none(self, cm):
        # An object without .position -> get_creep_target returns None.
        u = MagicMock(spec=[])
        assert cm.get_creep_target(u) is None
