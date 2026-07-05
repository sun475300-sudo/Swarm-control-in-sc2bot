# -*- coding: utf-8 -*-
"""
Unit tests -- BurrowController Lurker burrow-to-attack logic.

Regression test for a bug where `_handle_unburrowed_unit` never received
`enemy_units`, so the Lurker "burrow to attack when enemy in range" branch
was unreachable dead code (`pass  # placeholder`).
"""

import os
import sys

from unittest.mock import MagicMock

import pytest

sys.path.insert(
    0, os.path.join(os.path.dirname(__file__), "..", "wicked_zerg_challenger")
)

try:
    from combat.formation_tactics import BurrowController
    from sc2.ids.unit_typeid import UnitTypeId
except ImportError:
    pytest.skip("combat.formation_tactics not importable (SC2 env required)", allow_module_level=True)


def _make_unit(tag, type_id, distance_map):
    unit = MagicMock()
    unit.tag = tag
    unit.type_id = type_id
    unit.health = 100.0
    unit.health_max = 100.0
    unit.distance_to = lambda other: distance_map[other]
    return unit


class TestLurkerBurrowToAttack:
    def setup_method(self):
        self.controller = BurrowController()

    def test_burrows_when_enemy_within_attack_range(self):
        lurker = _make_unit("lurker", UnitTypeId.LURKERMP, {})
        enemy = object()
        lurker.distance_to = lambda other: 7.0  # inside 9.0 attack range
        down_ability = "BURROWDOWN_LURKER"

        action = self.controller._handle_unburrowed_unit(
            lurker, [enemy], health_ratio=1.0, enemy_nearby=True, down_ability=down_ability
        )

        lurker.assert_called_once_with(down_ability)
        assert action is not None

    def test_stays_unburrowed_when_enemy_out_of_attack_range(self):
        lurker = _make_unit("lurker", UnitTypeId.LURKERMP, {})
        enemy = object()
        lurker.distance_to = lambda other: 15.0  # outside 9.0 attack range
        down_ability = "BURROWDOWN_LURKER"

        action = self.controller._handle_unburrowed_unit(
            lurker, [enemy], health_ratio=1.0, enemy_nearby=True, down_ability=down_ability
        )

        lurker.assert_not_called()
        assert action is None

    def test_no_action_without_enemies(self):
        lurker = _make_unit("lurker", UnitTypeId.LURKERMP, {})
        down_ability = "BURROWDOWN_LURKER"

        action = self.controller._handle_unburrowed_unit(
            lurker, [], health_ratio=1.0, enemy_nearby=False, down_ability=down_ability
        )

        lurker.assert_not_called()
        assert action is None
