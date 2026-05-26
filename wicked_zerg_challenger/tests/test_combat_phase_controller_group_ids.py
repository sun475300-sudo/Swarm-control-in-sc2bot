# -*- coding: utf-8 -*-
"""Regression: group_id collision when combat groups are deleted then recreated."""

import os
import sys
import unittest
from unittest.mock import Mock

os.environ["PROTOCOL_BUFFERS_PYTHON_IMPLEMENTATION"] = "python"
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from combat_phase_controller import CombatPhaseController


class _FakeUnit:
    def __init__(self, tag):
        self.tag = tag
        self.health = 50
        self.shield = 0


class TestGroupIdsAreUnique(unittest.TestCase):
    def setUp(self):
        self.bot = Mock()
        self.bot.time = 100.0
        # bypass real __init__ deps
        self.ctrl = CombatPhaseController.__new__(CombatPhaseController)
        self.ctrl.bot = self.bot
        self.ctrl.combat_groups = {}
        self.ctrl._next_group_seq = 0
        self.ctrl.logger = Mock()

    def test_group_ids_do_not_collide_after_deletion(self):
        ids = set()
        # Create 3 groups
        for i in range(3):
            gid = self.ctrl._create_new_group([_FakeUnit(i)], 100.0)
            ids.add(gid)
        self.assertEqual(len(ids), 3)
        self.assertEqual(len(self.ctrl.combat_groups), 3)

        # Delete the middle group, simulating natural cleanup
        del self.ctrl.combat_groups["group_1"]
        self.assertEqual(len(self.ctrl.combat_groups), 2)

        # Now create a new group — naive `len(combat_groups)` would have
        # reused "group_2" and clobbered the existing entry.
        new_gid = self.ctrl._create_new_group([_FakeUnit(99)], 100.0)
        self.assertNotIn(new_gid, ids)
        self.assertEqual(new_gid, "group_3")
        self.assertEqual(len(self.ctrl.combat_groups), 3)


if __name__ == "__main__":
    unittest.main()
