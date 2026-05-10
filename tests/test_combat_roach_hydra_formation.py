"""Regression tests for CombatManager._execute_roach_hydra_formation.

Locks in the cycle-2 fix: when called with retreat=True the roach branch must
attack-move to the retreat anchor (closest own base), not the original
attack target. Prior to the fix both branches dispatched
`roach.attack(target)`, which meant the "retreat" command was indistinguishable
from a normal attack — pulling armies back was effectively a no-op.

The test bypasses CombatManager.__init__ (which pulls in sc2 and other heavy
modules) and exercises the bound method directly on a minimal stub.
"""

from __future__ import annotations

import os
import sys
from unittest.mock import MagicMock

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "wicked_zerg_challenger"))

try:
    from combat_manager import CombatManager
except ImportError:
    pytest.skip("CombatManager not importable (sc2 env required)", allow_module_level=True)


def _make_unit(name: str, tag: int):
    u = MagicMock()
    u.tag = tag
    u._stub_name = name
    u.position = MagicMock()
    return u


def _new_manager(retreat_anchor):
    """Build a CombatManager without running its real __init__."""
    mgr = object.__new__(CombatManager)
    mgr.bot = MagicMock()
    mgr.bot.do = MagicMock()
    mgr._unit_name = lambda unit: unit._stub_name
    mgr._closest_own_base_position = lambda: retreat_anchor
    # When not retreating, hydras compute "behind target"; we just echo target so
    # the assertion stays straightforward.
    mgr._position_behind_target = lambda target, _pos, _dist: target
    return mgr


def _attack_targets_for(do_mock):
    """Inspect bot.do(...) calls and return the unit each call attacked.

    `unit.attack(target)` is what the production code passes into `bot.do`; the
    MagicMock records it as a call on the unit's `attack` mock. We can read the
    call args back from there.
    """
    targets = []
    for unit_call in do_mock.call_args_list:
        # `unit.attack(target)` returns a MagicMock; bot.do receives that mock.
        # The original target is recorded on unit.attack.call_args.
        attack_result = unit_call.args[0]
        # `attack_result` is the MagicMock returned by `unit.attack(target)`;
        # the parent's call args are on attack_result._mock_parent.call_args.
        parent_call = attack_result._mock_parent.call_args
        if parent_call is not None:
            targets.append(parent_call.args[0])
    return targets


class TestRoachHydraFormationRetreat:
    def test_retreat_sends_roaches_to_retreat_anchor_not_target(self):
        """Regression: cycle 2 fix. retreat=True must reroute roaches to the anchor."""
        retreat_anchor = "OWN_BASE_POSITION"
        attack_target = "ENEMY_POSITION"
        mgr = _new_manager(retreat_anchor)

        roach = _make_unit("ROACH", tag=1)
        mgr._execute_roach_hydra_formation([roach], target=attack_target, retreat=True)

        roach.attack.assert_called_once_with(retreat_anchor)
        # And bot.do received that attack action exactly once.
        assert mgr.bot.do.call_count == 1

    def test_attack_sends_roaches_to_target(self):
        retreat_anchor = "OWN_BASE_POSITION"
        attack_target = "ENEMY_POSITION"
        mgr = _new_manager(retreat_anchor)

        roach = _make_unit("ROACH", tag=2)
        mgr._execute_roach_hydra_formation([roach], target=attack_target, retreat=False)

        roach.attack.assert_called_once_with(attack_target)

    def test_retreat_anchor_unavailable_falls_back_to_target(self):
        """When retreat_anchor is None we cannot retreat — keep attacking."""
        mgr = _new_manager(retreat_anchor=None)

        roach = _make_unit("ROACH", tag=3)
        mgr._execute_roach_hydra_formation([roach], target="X", retreat=True)

        roach.attack.assert_called_once_with("X")

    def test_hydra_retreat_path_unchanged(self):
        """Hydra branch was already correct; ensure the cycle-2 edit didn't regress it."""
        retreat_anchor = "OWN_BASE_POSITION"
        mgr = _new_manager(retreat_anchor)

        hydra = _make_unit("HYDRALISK", tag=4)
        mgr._execute_roach_hydra_formation([hydra], target="ENEMY", retreat=True)

        hydra.attack.assert_called_once_with(retreat_anchor)

    def test_hydra_attack_path_uses_position_behind_target(self):
        mgr = _new_manager(retreat_anchor="OWN_BASE")
        # Override _position_behind_target to a sentinel so we can verify it was used.
        mgr._position_behind_target = lambda target, _pos, _dist: ("BEHIND", target)

        hydra = _make_unit("HYDRALISK", tag=5)
        mgr._execute_roach_hydra_formation([hydra], target="ENEMY", retreat=False)

        hydra.attack.assert_called_once_with(("BEHIND", "ENEMY"))

    def test_empty_army_returns_empty_set(self):
        mgr = _new_manager(retreat_anchor="OWN_BASE")
        result = mgr._execute_roach_hydra_formation([], target="X", retreat=False)
        assert result == set()
        mgr.bot.do.assert_not_called()
