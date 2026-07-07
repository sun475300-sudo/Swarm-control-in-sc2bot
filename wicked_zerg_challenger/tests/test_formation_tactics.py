#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Tests for combat.formation_tactics.BurrowController.

Regression coverage for the Lurker burrow-on-approach bug: `_handle_unburrowed_unit`
used to have a `pass`-placeholder for LURKERMP burrow-in that claimed `enemy_units`
was "not in scope", even though the caller already passes a precomputed
`enemy_nearby` bool for exactly this purpose. Left unburrowed, Lurkers can't attack.
"""

import os
import sys
from unittest.mock import Mock

os.environ["PROTOCOL_BUFFERS_PYTHON_IMPLEMENTATION"] = "python"
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from sc2.ids.ability_id import AbilityId
from sc2.ids.unit_typeid import UnitTypeId

from combat.formation_tactics import BurrowController


def make_lurker(is_idle=True):
    unit = Mock()
    unit.type_id = UnitTypeId.LURKERMP
    unit.health = 200
    unit.health_max = 200
    unit.is_idle = is_idle
    unit.tag = 1
    return unit


class TestBurrowControllerLurker:
    def setup_method(self):
        self.controller = BurrowController()

    def test_lurker_burrows_when_enemy_nearby(self):
        lurker = make_lurker()
        action = self.controller._handle_unburrowed_unit(
            lurker, health_ratio=1.0, enemy_nearby=True, down_ability=AbilityId.BURROWDOWN_LURKER
        )
        assert action is not None
        lurker.assert_called_once_with(AbilityId.BURROWDOWN_LURKER)

    def test_lurker_stays_unburrowed_without_enemies(self):
        lurker = make_lurker()
        action = self.controller._handle_unburrowed_unit(
            lurker, health_ratio=1.0, enemy_nearby=False, down_ability=AbilityId.BURROWDOWN_LURKER
        )
        assert action is None
        lurker.assert_not_called()
