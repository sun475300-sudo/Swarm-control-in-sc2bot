# -*- coding: utf-8 -*-
"""
Unit tests for BurrowController (combat/formation_tactics.py).

Covers the lurker burrow-to-attack fix: lurkers must burrow whenever an
enemy is within attack range, instead of the previous no-op placeholder
that never burrowed lurkers at all (existing bug referencing an
out-of-scope `enemy_units`).
"""

import os
import sys
import unittest
from unittest.mock import Mock

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from combat.formation_tactics import BurrowController
from sc2.ids.ability_id import AbilityId
from sc2.ids.unit_typeid import UnitTypeId
from sc2.position import Point2


def _make_unit(
    unit_type, position, is_burrowed=False, is_idle=False, health=100, health_max=100
):
    unit = Mock()
    unit.type_id = unit_type
    unit.position = Point2(position)
    unit.is_burrowed = is_burrowed
    unit.is_idle = is_idle
    unit.health = health
    unit.health_max = health_max
    unit.tag = id(unit)
    unit.distance_to = lambda other: unit.position.distance_to(
        other.position if hasattr(other, "position") else other
    )
    return unit


class TestLurkerBurrowToAttack(unittest.TestCase):
    def setUp(self):
        self.controller = BurrowController()

    def test_lurker_burrows_when_enemy_within_attack_range(self):
        lurker = _make_unit(UnitTypeId.LURKERMP, (10, 10))
        enemy = _make_unit(UnitTypeId.MARINE, (15, 10))  # distance 5 < 9 range

        action = self.controller._handle_unburrowed_unit(
            lurker,
            enemy_units=[enemy],
            health_ratio=1.0,
            enemy_nearby=True,
            down_ability=AbilityId.BURROWDOWN_LURKER,
        )

        self.assertIsNotNone(action)

    def test_lurker_stays_unburrowed_when_no_enemy_in_range(self):
        lurker = _make_unit(UnitTypeId.LURKERMP, (10, 10))
        enemy = _make_unit(UnitTypeId.MARINE, (30, 10))  # distance 20 > 9 range

        action = self.controller._handle_unburrowed_unit(
            lurker,
            enemy_units=[enemy],
            health_ratio=1.0,
            enemy_nearby=False,
            down_ability=AbilityId.BURROWDOWN_LURKER,
        )

        self.assertIsNone(action)

    def test_lurker_stays_unburrowed_with_no_enemies(self):
        lurker = _make_unit(UnitTypeId.LURKERMP, (10, 10))

        action = self.controller._handle_unburrowed_unit(
            lurker,
            enemy_units=[],
            health_ratio=1.0,
            enemy_nearby=False,
            down_ability=AbilityId.BURROWDOWN_LURKER,
        )

        self.assertIsNone(action)


if __name__ == "__main__":
    unittest.main()
