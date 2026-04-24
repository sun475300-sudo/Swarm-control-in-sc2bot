# -*- coding: utf-8 -*-
"""
Unit tests for wicked_zerg_challenger/queen_manager.py (1292 LOC, previously untested).

Covers the purely-computational helpers that have no SC2-client
dependency: creep-target scoring, queen lookup, tumor counting, and
static config invariants.
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
        from queen_manager import QueenManager
        return QueenManager
    except ImportError:
        return None


QueenManager = _import()

pytestmark = pytest.mark.skipif(
    QueenManager is None, reason="queen_manager not importable"
)


def _point(x, y):
    p = MagicMock()
    p.x = x
    p.y = y
    return p


def _queen(tag, x=0.0, y=0.0):
    q = MagicMock()
    q.tag = tag
    q.position = _point(x, y)
    # distance_to uses Euclidean in the helper — make it real.
    q.distance_to = lambda target: (
        (q.position.x - target.x) ** 2 + (q.position.y - target.y) ** 2
    ) ** 0.5
    return q


@pytest.fixture
def bot():
    b = MagicMock()
    b.time = 0.0
    b.structures = []
    b.units = []
    b.townhalls = []
    return b


@pytest.fixture
def qm(bot):
    return QueenManager(bot)


class TestInit:
    def test_inject_cooldown_matches_sc2(self, qm):
        # SC2 Spawn Larva cooldown is 28.57s — comment says +0.43 margin.
        assert qm.inject_cooldown == pytest.approx(29.0)

    def test_energy_thresholds_sensible(self, qm):
        assert 0 < qm.inject_energy_threshold < 200
        assert 0 < qm.creep_energy_threshold < 200
        # Injection should cost less energy than the "inject queen can also
        # drop creep" bonus threshold.
        assert qm.creep_energy_threshold < qm.inject_queen_creep_threshold

    def test_queen_caps_reasonable(self, qm):
        assert qm.max_queens_per_base >= 1
        assert qm.creep_queen_bonus >= 0

    def test_assignment_dicts_empty(self, qm):
        assert qm.inject_assignments == {}
        assert qm.last_inject_time == {}
        assert qm.last_creep_time == {}


class TestCountCreepTumors:
    def test_no_structures_attr(self, bot, qm):
        del bot.structures
        assert qm._count_creep_tumors() == 0

    def test_counts_all_three_tumor_types(self, bot, qm):
        # Import the real UnitTypeId so we hit the real matching path.
        from sc2.ids.unit_typeid import UnitTypeId
        s1 = MagicMock(); s1.type_id = UnitTypeId.CREEPTUMOR
        s2 = MagicMock(); s2.type_id = UnitTypeId.CREEPTUMORBURROWED
        s3 = MagicMock(); s3.type_id = UnitTypeId.CREEPTUMORQUEEN
        s4 = MagicMock(); s4.type_id = UnitTypeId.HATCHERY  # not a tumor
        bot.structures = [s1, s2, s3, s4]
        assert qm._count_creep_tumors() == 3

    def test_swallows_exception(self, bot, qm):
        # Iterating a non-iterable should NOT crash the caller.
        bot.structures = MagicMock()
        bot.structures.__iter__ = MagicMock(side_effect=RuntimeError("boom"))
        assert qm._count_creep_tumors() == 0


class TestIsValidCreepPosition:
    def test_none_target_is_invalid(self, qm):
        assert qm._is_valid_creep_position(None) is False

    def test_uses_has_creep_when_present(self, bot, qm):
        bot.has_creep = MagicMock(return_value=True)
        assert qm._is_valid_creep_position(_point(10, 10)) is True
        bot.has_creep.return_value = False
        assert qm._is_valid_creep_position(_point(10, 10)) is False

    def test_missing_has_creep_returns_false(self, bot, qm):
        # Per in-code comment: absence of has_creep should fail-closed.
        del bot.has_creep
        assert qm._is_valid_creep_position(_point(10, 10)) is False

    def test_exception_returns_false(self, bot, qm):
        bot.has_creep = MagicMock(side_effect=RuntimeError("bad"))
        assert qm._is_valid_creep_position(_point(10, 10)) is False


class TestScoreCreepTarget:
    def test_zero_distance_direction_returns_distance(self):
        origin = _point(0, 0)
        candidate = _point(3, 4)  # dist=5
        # direction_target == origin => dir_len == 0 branch
        direction = _point(0, 0)
        score = QueenManager._score_creep_target(origin, candidate, direction)
        assert score == pytest.approx(5.0)

    def test_projection_along_direction(self):
        # Direction purely along +x; candidate at +5x, +0y.
        origin = _point(0, 0)
        candidate = _point(5, 0)
        direction = _point(10, 0)
        # projection = 5, dist = 5, total = 5 + 1.25 = 6.25
        score = QueenManager._score_creep_target(origin, candidate, direction)
        assert score == pytest.approx(6.25)

    def test_opposite_direction_has_lower_score(self):
        origin = _point(0, 0)
        forward = _point(5, 0)
        backward = _point(-5, 0)
        direction = _point(10, 0)
        s_forward = QueenManager._score_creep_target(origin, forward, direction)
        s_backward = QueenManager._score_creep_target(origin, backward, direction)
        # Same distance term, opposite projection.
        assert s_forward > s_backward


class TestFindClosestQueen:
    def test_no_queens_returns_none(self):
        assert QueenManager._find_closest_queen(_point(0, 0), [], set()) is None

    def test_all_excluded_returns_none(self):
        q1 = _queen(1, 0, 0)
        q2 = _queen(2, 10, 0)
        result = QueenManager._find_closest_queen(
            _point(5, 0), [q1, q2], {1, 2}
        )
        assert result is None

    def test_picks_closest(self):
        near = _queen(1, 1, 0)
        far = _queen(2, 10, 0)
        result = QueenManager._find_closest_queen(
            _point(0, 0), [far, near], set()
        )
        assert result is near

    def test_excluded_skipped(self):
        near = _queen(1, 1, 0)   # excluded
        mid = _queen(2, 3, 0)
        result = QueenManager._find_closest_queen(
            _point(0, 0), [near, mid], {1}
        )
        assert result is mid


class TestFindQueenByTag:
    def test_none_tag_returns_none(self):
        queens = [_queen(1), _queen(2)]
        assert QueenManager._find_queen_by_tag(queens, None) is None

    def test_found(self):
        q1 = _queen(1)
        q2 = _queen(2)
        assert QueenManager._find_queen_by_tag([q1, q2], 2) is q2

    def test_not_found(self):
        assert QueenManager._find_queen_by_tag([_queen(1)], 99) is None
