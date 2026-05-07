"""Unit tests for QueenSpecializationManager — role assignment logic.

Covers `assign_roles`, `_find_by_tag`, role counting, and cleanup of
dead queens. The manager doesn't talk to the SC2 game loop in these
paths, so MagicMock units are sufficient.
"""

from __future__ import annotations

from unittest.mock import MagicMock

import pytest

try:
    from wicked_zerg_challenger.economy.queen_specialization import (
        QueenSpecialization,
        QueenSpecializationManager,
    )
except ImportError as exc:  # pragma: no cover - environment guard
    pytest.skip(f"queen_specialization import failed: {exc}", allow_module_level=True)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_queen(tag: int, position=(0.0, 0.0), distance: float = 1.0):
    q = MagicMock()
    q.tag = tag
    q.position = position
    q.energy = 100
    q.distance_to = MagicMock(return_value=distance)
    return q


def _make_hatch(tag: int, position=(0.0, 0.0)):
    h = MagicMock()
    h.tag = tag
    h.position = position
    return h


def _make_bot():
    bot = MagicMock()
    bot.time = 100.0
    bot.do = MagicMock()
    return bot


# ---------------------------------------------------------------------------
# Static helper
# ---------------------------------------------------------------------------


class TestFindByTag:
    def test_returns_unit_when_tag_present(self):
        a, b = _make_queen(1), _make_queen(2)
        result = QueenSpecializationManager._find_by_tag([a, b], 2)
        assert result is b

    def test_returns_none_when_tag_missing(self):
        result = QueenSpecializationManager._find_by_tag([_make_queen(1)], 99)
        assert result is None

    def test_returns_none_for_none_tag(self):
        result = QueenSpecializationManager._find_by_tag([_make_queen(1)], None)
        assert result is None

    def test_handles_empty_iterable(self):
        result = QueenSpecializationManager._find_by_tag([], 1)
        assert result is None


# ---------------------------------------------------------------------------
# assign_roles: PUMP allocation
# ---------------------------------------------------------------------------


class TestPumpAssignment:
    def test_one_hatch_one_pump_queen(self):
        """A single hatchery + single queen → that queen is PUMP."""
        mgr = QueenSpecializationManager(_make_bot())
        queens = [_make_queen(1)]
        hatches = [_make_hatch(10)]

        mgr.assign_roles(queens, hatches)

        assert mgr.get_role(1) == QueenSpecialization.PUMP
        assert mgr.pump_assignments == {1: 10}

    def test_pump_count_capped_at_hatchery_count(self):
        """With 2 hatcheries and 4 queens, only 2 are PUMP."""
        mgr = QueenSpecializationManager(_make_bot())
        queens = [_make_queen(t) for t in (1, 2, 3, 4)]
        hatches = [_make_hatch(t) for t in (10, 20)]

        mgr.assign_roles(queens, hatches)

        counts = mgr.get_role_counts()
        assert counts["pump"] == 2

    def test_unassigned_queen_picks_closest_hatchery(self):
        """The closer queen to a free hatchery becomes its PUMP."""
        mgr = QueenSpecializationManager(_make_bot())
        far = _make_queen(1, distance=20.0)
        near = _make_queen(2, distance=1.0)
        hatch = _make_hatch(10)

        mgr.assign_roles([far, near], [hatch])

        assert mgr.pump_assignments[2] == 10
        assert 1 not in mgr.pump_assignments


# ---------------------------------------------------------------------------
# assign_roles: CREEP / COMBAT allocation
# ---------------------------------------------------------------------------


class TestCreepAndCombatAssignment:
    def test_single_hatch_no_creep_role(self):
        """With only 1 hatchery (creep_count == 0), no CREEP role assigned."""
        mgr = QueenSpecializationManager(_make_bot())
        queens = [_make_queen(t) for t in (1, 2, 3)]

        mgr.assign_roles(queens, [_make_hatch(10)])

        counts = mgr.get_role_counts()
        assert counts["creep"] == 0
        assert counts["pump"] == 1
        assert counts["combat"] == 2

    def test_two_hatches_yield_one_creep(self):
        """2 hatcheries → max(1, 2//2) == 1 CREEP queen."""
        mgr = QueenSpecializationManager(_make_bot())
        queens = [_make_queen(t) for t in (1, 2, 3, 4)]
        hatches = [_make_hatch(t) for t in (10, 20)]

        mgr.assign_roles(queens, hatches)

        counts = mgr.get_role_counts()
        assert counts["pump"] == 2
        assert counts["creep"] == 1
        assert counts["combat"] == 1

    def test_remaining_queens_get_combat_role(self):
        """All queens beyond PUMP+CREEP allocations are COMBAT."""
        mgr = QueenSpecializationManager(_make_bot())
        queens = [_make_queen(t) for t in (1, 2, 3, 4, 5)]
        hatches = [_make_hatch(10)]  # 1 PUMP, 0 CREEP, 4 COMBAT

        mgr.assign_roles(queens, hatches)

        counts = mgr.get_role_counts()
        assert counts["combat"] == 4

    def test_role_counts_sum_to_total_queens(self):
        """Every queen receives exactly one specialization."""
        mgr = QueenSpecializationManager(_make_bot())
        queens = [_make_queen(t) for t in range(1, 8)]
        hatches = [_make_hatch(10), _make_hatch(20), _make_hatch(30)]

        mgr.assign_roles(queens, hatches)

        counts = mgr.get_role_counts()
        assert sum(counts.values()) == len(queens)


# ---------------------------------------------------------------------------
# Dead-queen cleanup
# ---------------------------------------------------------------------------


class TestDeadQueenCleanup:
    def test_dead_queen_removed_from_specializations(self):
        """A queen no longer in `queens` must drop its spec on next call."""
        mgr = QueenSpecializationManager(_make_bot())
        q1 = _make_queen(1)
        q2 = _make_queen(2)
        hatch = _make_hatch(10)

        mgr.assign_roles([q1, q2], [hatch])
        assert mgr.get_role(1) is not None
        assert mgr.get_role(2) is not None

        # q2 dies
        mgr.assign_roles([q1], [hatch])

        assert mgr.get_role(2) is None, "Dead queen must be purged"

    def test_dead_pump_queen_frees_assignment(self):
        """Killing the PUMP queen frees the hatchery for re-assignment."""
        mgr = QueenSpecializationManager(_make_bot())
        q1 = _make_queen(1)
        hatch = _make_hatch(10)

        mgr.assign_roles([q1], [hatch])
        assert mgr.pump_assignments == {1: 10}

        q2 = _make_queen(2)
        mgr.assign_roles([q2], [hatch])

        assert 1 not in mgr.pump_assignments
        assert mgr.pump_assignments == {2: 10}


# ---------------------------------------------------------------------------
# get_role_counts on empty state
# ---------------------------------------------------------------------------


class TestGetRoleCounts:
    def test_empty_manager_returns_zeros(self):
        mgr = QueenSpecializationManager(_make_bot())
        assert mgr.get_role_counts() == {"pump": 0, "creep": 0, "combat": 0}
