# -*- coding: utf-8 -*-
"""Tests for CombatPhaseController.

Locks in behavior of `_update_combat_groups` after the O(N²) -> O(N)
liveness-check optimization.
"""

import os
import sys
import unittest
from unittest.mock import Mock

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from combat_phase_controller import CombatGroup, CombatPhase, CombatPhaseController


def _unit(tag):
    u = Mock()
    u.tag = tag
    return u


def _bot_with_units(unit_tags):
    bot = Mock()
    bot.units = [_unit(t) for t in unit_tags]
    bot.time = 0.0
    return bot


def _group(units, phase=CombatPhase.IDLE):
    return CombatGroup(
        units=set(units),
        phase=phase,
        rally_point=None,
        target_position=None,
        formation_type="ball",
        engagement_time=0.0,
        last_phase_change=0.0,
        initial_unit_count=len(units),
        initial_total_hp=0.0,
        enemies_killed=0,
        damage_taken=0.0,
    )


class TestUpdateCombatGroups(unittest.TestCase):
    def setUp(self):
        self.bot = _bot_with_units([1, 2, 3, 4, 5])
        # Stub out the auto-grouping path so it doesn't try to create groups.
        self.controller = CombatPhaseController(self.bot)
        self.controller._get_combat_units = Mock(return_value=[])

    def test_disbands_group_when_all_units_dead(self):
        self.controller.combat_groups["g1"] = _group({99, 100})
        self.controller._update_combat_groups(0.0)
        self.assertNotIn("g1", self.controller.combat_groups)

    def test_keeps_group_with_some_alive_units_and_drops_dead_tags(self):
        self.controller.combat_groups["g1"] = _group({1, 2, 99})
        self.controller._update_combat_groups(0.0)
        self.assertIn("g1", self.controller.combat_groups)
        self.assertEqual(self.controller.combat_groups["g1"].units, {1, 2})

    def test_handles_bot_without_units_attribute(self):
        self.controller.bot = Mock(spec=[])  # no .units
        self.controller.combat_groups["g1"] = _group({1, 2})
        self.controller._update_combat_groups(0.0)
        # Without units attribute, all groups disband (alive_tags is empty).
        self.assertNotIn("g1", self.controller.combat_groups)

    def test_uses_alive_set_only_once_per_call(self):
        # If we previously called _is_unit_alive per tag, accessing
        # self.bot.units would happen N*K times. After the optimization it
        # happens exactly once per _update_combat_groups call regardless of
        # group count.
        self.controller.combat_groups["g1"] = _group({1, 2, 3})
        self.controller.combat_groups["g2"] = _group({4, 5})
        self.controller.combat_groups["g3"] = _group({1, 99})

        access_count = {"n": 0}
        original = self.controller.bot.units

        class _UnitsProxy:
            def __iter__(_self):
                access_count["n"] += 1
                return iter(original)

            def __bool__(_self):
                return True

        self.controller.bot.units = _UnitsProxy()
        self.controller._update_combat_groups(0.0)
        # Build of alive_tags iterates self.bot.units exactly once.
        self.assertEqual(access_count["n"], 1)


if __name__ == "__main__":
    unittest.main()
