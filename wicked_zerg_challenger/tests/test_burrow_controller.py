# -*- coding: utf-8 -*-
"""Regression tests for BurrowController lurker burrow-to-attack logic."""

import os
import sys
from unittest.mock import Mock

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from combat.formation_tactics import BurrowController
from sc2.ids.unit_typeid import UnitTypeId


def _make_lurker(is_idle=True):
    unit = Mock()
    unit.type_id = UnitTypeId.LURKERMP
    unit.is_idle = is_idle
    return unit


class TestLurkerBurrowToAttack:
    def setup_method(self):
        self.controller = BurrowController()
        self.down_ability = "BURROWDOWN_LURKER"

    def test_lurker_burrows_when_enemy_in_range_and_idle(self):
        lurker = _make_lurker(is_idle=True)
        action = self.controller._handle_unburrowed_unit(
            lurker, health_ratio=1.0, enemy_nearby=True, down_ability=self.down_ability
        )
        assert action is not None
        lurker.assert_called_once_with(self.down_ability)

    def test_lurker_does_not_burrow_without_nearby_enemy(self):
        lurker = _make_lurker(is_idle=True)
        action = self.controller._handle_unburrowed_unit(
            lurker, health_ratio=1.0, enemy_nearby=False, down_ability=self.down_ability
        )
        assert action is None
        lurker.assert_not_called()

    def test_lurker_does_not_burrow_when_not_idle(self):
        lurker = _make_lurker(is_idle=False)
        action = self.controller._handle_unburrowed_unit(
            lurker, health_ratio=1.0, enemy_nearby=True, down_ability=self.down_ability
        )
        assert action is None
        lurker.assert_not_called()
