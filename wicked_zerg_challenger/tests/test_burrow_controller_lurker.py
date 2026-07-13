#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Regression test for BurrowController Lurker burrow-to-attack logic.

Covers the bug where _handle_unburrowed_unit's Lurker branch referenced an
out-of-scope `enemy_units` and was stubbed out to a no-op `pass`, so Lurkers
never burrowed to attack.
"""

import os
import sys
import unittest

os.environ["PROTOCOL_BUFFERS_PYTHON_IMPLEMENTATION"] = "python"
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from combat.formation_tactics import BurrowController

try:
    from sc2.ids.unit_typeid import UnitTypeId

    LURKERMP = UnitTypeId.LURKERMP
except ImportError:
    LURKERMP = None


class Point:
    def __init__(self, x, y):
        self.x = float(x)
        self.y = float(y)

    def distance_to(self, other):
        return ((self.x - other.x) ** 2 + (self.y - other.y) ** 2) ** 0.5


class FakeUnit:
    def __init__(self, tag, type_id, position, is_idle=False):
        self.tag = tag
        self.type_id = type_id
        self.position = position
        self.is_idle = is_idle
        self.issued_ability = None

    def distance_to(self, other):
        return self.position.distance_to(other.position)

    def __call__(self, ability):
        self.issued_ability = ability
        return ("order", self.tag, ability)


class TestLurkerBurrowToAttack(unittest.TestCase):
    def setUp(self):
        if LURKERMP is None:
            self.skipTest("sc2 library not available")
        self.controller = BurrowController()

    def test_lurker_burrows_when_enemy_within_attack_range(self):
        lurker = FakeUnit(1, LURKERMP, Point(0, 0))
        enemy = FakeUnit(2, LURKERMP, Point(8, 0))  # distance 8 < 9.0 range
        action = self.controller._handle_unburrowed_unit(
            lurker, [enemy], health_ratio=1.0, enemy_nearby=True, down_ability="BURROWDOWN_LURKER"
        )
        self.assertIsNotNone(action)
        self.assertEqual(lurker.issued_ability, "BURROWDOWN_LURKER")

    def test_lurker_stays_unburrowed_when_no_enemy_in_range(self):
        lurker = FakeUnit(1, LURKERMP, Point(0, 0))
        enemy = FakeUnit(2, LURKERMP, Point(50, 0))  # far away
        action = self.controller._handle_unburrowed_unit(
            lurker, [enemy], health_ratio=1.0, enemy_nearby=False, down_ability="BURROWDOWN_LURKER"
        )
        self.assertIsNone(action)
        self.assertIsNone(lurker.issued_ability)

    def test_lurker_ignores_idle_state(self):
        # Lurkers must burrow to attack regardless of idle state, unlike Banelings.
        lurker = FakeUnit(1, LURKERMP, Point(0, 0), is_idle=False)
        enemy = FakeUnit(2, LURKERMP, Point(5, 0))
        action = self.controller._handle_unburrowed_unit(
            lurker, [enemy], health_ratio=1.0, enemy_nearby=True, down_ability="BURROWDOWN_LURKER"
        )
        self.assertIsNotNone(action)


if __name__ == "__main__":
    unittest.main()
