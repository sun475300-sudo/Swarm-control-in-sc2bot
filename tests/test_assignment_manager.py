"""Tests for wicked_zerg_challenger/combat/assignment_manager.py.

These are pure-Python tests — no SC2 game instance needed.
The module operates on a CombatManager-like object via attribute access,
so we use a SimpleNamespace stand-in.
"""
from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import MagicMock

import pytest

from wicked_zerg_challenger.combat import assignment_manager as am


# --------------------------------------------------------------------------
# helpers
# --------------------------------------------------------------------------

def _make_manager():
    """Return a stand-in CombatManager exposing the attributes used by the module."""
    mgr = SimpleNamespace()
    mgr._unit_assignments = {}
    mgr._active_tasks = {}
    mgr.bot = SimpleNamespace(units=[])
    return mgr


def _make_unit(tag: int):
    return SimpleNamespace(tag=tag)


# --------------------------------------------------------------------------
# assign_unit_to_task
# --------------------------------------------------------------------------

def test_assign_creates_task_entry():
    mgr = _make_manager()
    am.assign_unit_to_task(mgr, 1, "attack")
    assert mgr._unit_assignments[1] == "attack"
    assert 1 in mgr._active_tasks["attack"]["units"]


def test_assign_multiple_units_to_same_task():
    mgr = _make_manager()
    am.assign_unit_to_task(mgr, 1, "defend")
    am.assign_unit_to_task(mgr, 2, "defend")
    assert mgr._active_tasks["defend"]["units"] == {1, 2}


def test_assign_overwrites_unit_in_lookup_but_keeps_old_task_entry():
    """If a unit is reassigned, _unit_assignments updates but old task still
    knows about the unit-tag until unassign_unit() is called. This documents
    current behavior — call unassign_unit first when reassigning."""
    mgr = _make_manager()
    am.assign_unit_to_task(mgr, 1, "attack")
    am.assign_unit_to_task(mgr, 1, "defend")
    assert mgr._unit_assignments[1] == "defend"
    # Both task entries may exist — documenting current behavior
    assert 1 in mgr._active_tasks["defend"]["units"]


# --------------------------------------------------------------------------
# unassign_unit
# --------------------------------------------------------------------------

def test_unassign_removes_from_lookup_and_task():
    mgr = _make_manager()
    am.assign_unit_to_task(mgr, 1, "attack")
    am.unassign_unit(mgr, 1)
    assert 1 not in mgr._unit_assignments
    assert "attack" not in mgr._active_tasks  # task removed when empty


def test_unassign_keeps_task_when_other_units_remain():
    mgr = _make_manager()
    am.assign_unit_to_task(mgr, 1, "attack")
    am.assign_unit_to_task(mgr, 2, "attack")
    am.unassign_unit(mgr, 1)
    assert "attack" in mgr._active_tasks
    assert mgr._active_tasks["attack"]["units"] == {2}


def test_unassign_unknown_unit_is_noop():
    mgr = _make_manager()
    am.unassign_unit(mgr, 999)  # should not raise
    assert mgr._unit_assignments == {}


# --------------------------------------------------------------------------
# get_unit_task
# --------------------------------------------------------------------------

def test_get_unit_task_returns_assignment():
    mgr = _make_manager()
    am.assign_unit_to_task(mgr, 1, "scout")
    assert am.get_unit_task(mgr, 1) == "scout"


def test_get_unit_task_unknown_returns_none():
    mgr = _make_manager()
    assert am.get_unit_task(mgr, 1) is None


# --------------------------------------------------------------------------
# get_unassigned_units
# --------------------------------------------------------------------------

def test_get_unassigned_filters_assigned():
    mgr = _make_manager()
    am.assign_unit_to_task(mgr, 2, "attack")
    units = [_make_unit(1), _make_unit(2), _make_unit(3)]
    result = am.get_unassigned_units(mgr, units)
    assert [u.tag for u in result] == [1, 3]


def test_get_unassigned_empty_input():
    mgr = _make_manager()
    assert am.get_unassigned_units(mgr, []) == []


# --------------------------------------------------------------------------
# get_units_by_task
# --------------------------------------------------------------------------

def test_get_units_by_task_returns_copy_not_reference():
    mgr = _make_manager()
    am.assign_unit_to_task(mgr, 1, "attack")
    result = am.get_units_by_task(mgr, "attack")
    result.add(999)
    # Mutating returned set must not affect internal state
    assert 999 not in mgr._active_tasks["attack"]["units"]


def test_get_units_by_task_unknown_returns_empty_set():
    mgr = _make_manager()
    assert am.get_units_by_task(mgr, "ghost_task") == set()


# --------------------------------------------------------------------------
# set_task_target / get_task_target
# --------------------------------------------------------------------------

def test_set_target_creates_task_when_missing():
    mgr = _make_manager()
    am.set_task_target(mgr, "attack", (10, 20))
    assert mgr._active_tasks["attack"]["target"] == (10, 20)
    assert mgr._active_tasks["attack"]["units"] == set()


def test_set_target_updates_existing_task_without_clearing_units():
    mgr = _make_manager()
    am.assign_unit_to_task(mgr, 1, "attack")
    am.set_task_target(mgr, "attack", (5, 5))
    assert mgr._active_tasks["attack"]["target"] == (5, 5)
    assert 1 in mgr._active_tasks["attack"]["units"]


def test_get_target_unknown_returns_none():
    mgr = _make_manager()
    assert am.get_task_target(mgr, "nope") is None


# --------------------------------------------------------------------------
# clear_task
# --------------------------------------------------------------------------

def test_clear_task_removes_task_and_unit_lookups():
    mgr = _make_manager()
    am.assign_unit_to_task(mgr, 1, "attack")
    am.assign_unit_to_task(mgr, 2, "attack")
    am.clear_task(mgr, "attack")
    assert "attack" not in mgr._active_tasks
    assert 1 not in mgr._unit_assignments
    assert 2 not in mgr._unit_assignments


def test_clear_unknown_task_is_noop():
    mgr = _make_manager()
    am.clear_task(mgr, "ghost")  # should not raise


# --------------------------------------------------------------------------
# get_all_active_tasks
# --------------------------------------------------------------------------

def test_get_all_active_tasks_returns_copy():
    mgr = _make_manager()
    am.assign_unit_to_task(mgr, 1, "attack")
    result = am.get_all_active_tasks(mgr)
    result["fake"] = {"units": set(), "target": None}
    assert "fake" not in mgr._active_tasks


# --------------------------------------------------------------------------
# count_units_in_task
# --------------------------------------------------------------------------

def test_count_units_in_task():
    mgr = _make_manager()
    am.assign_unit_to_task(mgr, 1, "attack")
    am.assign_unit_to_task(mgr, 2, "attack")
    assert am.count_units_in_task(mgr, "attack") == 2


def test_count_units_in_unknown_task_returns_zero():
    mgr = _make_manager()
    assert am.count_units_in_task(mgr, "ghost") == 0


# --------------------------------------------------------------------------
# cleanup_assignments
# --------------------------------------------------------------------------

def test_cleanup_assignments_removes_dead_unit_lookups():
    mgr = _make_manager()
    am.assign_unit_to_task(mgr, 1, "attack")
    am.assign_unit_to_task(mgr, 2, "attack")
    # only unit 1 is still alive
    mgr.bot.units = [_make_unit(1)]
    am.cleanup_assignments(mgr)
    assert 1 in mgr._unit_assignments
    assert 2 not in mgr._unit_assignments


def test_cleanup_assignments_when_bot_has_no_units_attr_is_noop():
    mgr = _make_manager()
    am.assign_unit_to_task(mgr, 1, "attack")
    mgr.bot = SimpleNamespace()  # no 'units' attr
    am.cleanup_assignments(mgr)
    # original assignment preserved (no-op)
    assert 1 in mgr._unit_assignments


def test_full_lifecycle_assign_unassign_clear():
    mgr = _make_manager()
    am.assign_unit_to_task(mgr, 1, "attack")
    am.assign_unit_to_task(mgr, 2, "attack")
    am.set_task_target(mgr, "attack", (50, 50))
    assert am.count_units_in_task(mgr, "attack") == 2
    am.unassign_unit(mgr, 1)
    assert am.count_units_in_task(mgr, "attack") == 1
    am.clear_task(mgr, "attack")
    assert am.get_units_by_task(mgr, "attack") == set()
    assert am.get_task_target(mgr, "attack") is None
