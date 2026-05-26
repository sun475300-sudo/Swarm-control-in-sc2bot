"""Tests for QueenSpecializationManager.assign_roles.

Covers the Batch 2d regression where Phase 2 CREEP assignment captured
``unassigned`` BEFORE the existing-creep loop ran. After the loop, the slice
``unassigned[:creep_count]`` still pointed at the just-confirmed CREEP queens
and the ``if queen.tag in assigned`` guard skipped them all — so no new CREEP
queen was added even when fresh queens were available.
"""

from __future__ import annotations

import os
import sys
from unittest.mock import MagicMock

import pytest

_WZC = os.path.join(os.path.dirname(__file__), "..", "wicked_zerg_challenger")
if os.path.isdir(_WZC) and _WZC not in sys.path:
    sys.path.insert(0, _WZC)

try:
    from sc2.ids.ability_id import AbilityId  # noqa: F401

    from wicked_zerg_challenger.economy.queen_specialization import (
        QueenSpecialization,
        QueenSpecializationManager,
    )
except ImportError:
    pytest.skip(
        "sc2 library or QueenSpecializationManager not available",
        allow_module_level=True,
    )


def _make_queen(tag, x=0, y=0):
    q = MagicMock()
    q.tag = tag
    q.position = MagicMock()
    q.position.x = float(x)
    q.position.y = float(y)
    q.distance_to = (
        lambda other: (
            (q.position.x - getattr(other, "position", other).x) ** 2
            + (q.position.y - getattr(other, "position", other).y) ** 2
        )
        ** 0.5
    )
    return q


def _make_hatch(tag, x=0, y=0):
    h = MagicMock()
    h.tag = tag
    h.position = MagicMock()
    h.position.x = float(x)
    h.position.y = float(y)
    return h


def _make_mgr():
    bot = MagicMock()
    bot.time = 240.0
    return QueenSpecializationManager(bot)


def test_assign_roles_promotes_fresh_queen_to_creep_when_existing_creep_already_kept():
    """Regression: with an existing-CREEP queen retained, the creep-count budget
    must still leave room for a freshly-promoted CREEP queen when one is needed."""
    mgr = _make_mgr()
    # 4 hatcheries -> creep_count = max(1, 4//2) = 2
    hatcheries = [_make_hatch(100 + i, i * 5, 0) for i in range(4)]
    # 6 queens. q0..q3 are PUMP-eligible (closest to hatcheries),
    # q4 is the *existing* CREEP, q5 is fresh.
    queens = [_make_queen(i, i * 5, 0) for i in range(4)] + [
        _make_queen(4, 50, 0),
        _make_queen(5, 60, 0),
    ]

    # Pre-mark q4 as existing CREEP.
    mgr.specializations[4] = QueenSpecialization.CREEP

    mgr.assign_roles(queens, hatcheries)

    creep_queens = {
        tag
        for tag, spec in mgr.specializations.items()
        if spec == QueenSpecialization.CREEP
    }
    # Both budget slots must be filled: existing q4 + a fresh promotion (q5).
    assert 4 in creep_queens, "existing creep queen must be retained"
    assert len(creep_queens) == 2, (
        f"expected 2 CREEP queens, got {sorted(creep_queens)} "
        f"(specializations={dict((k, s.value) for k, s in mgr.specializations.items())})"
    )


def test_assign_roles_assigns_creep_when_no_existing_creep():
    """Sanity: with no existing creep, the budget is filled from fresh queens."""
    mgr = _make_mgr()
    hatcheries = [_make_hatch(100 + i, i * 5, 0) for i in range(4)]
    queens = [_make_queen(i, i * 5, 0) for i in range(6)]

    mgr.assign_roles(queens, hatcheries)

    creep_count = sum(
        1 for spec in mgr.specializations.values() if spec == QueenSpecialization.CREEP
    )
    assert creep_count == 2, f"expected 2 CREEP queens, got {creep_count}"


def test_assign_roles_no_creep_when_only_one_hatch():
    """With <2 hatcheries, no CREEP queen should be assigned."""
    mgr = _make_mgr()
    hatcheries = [_make_hatch(100, 0, 0)]
    queens = [_make_queen(i, i * 5, 0) for i in range(3)]

    mgr.assign_roles(queens, hatcheries)

    creep_count = sum(
        1 for spec in mgr.specializations.values() if spec == QueenSpecialization.CREEP
    )
    assert (
        creep_count == 0
    ), f"single base should yield 0 CREEP queens, got {creep_count}"
