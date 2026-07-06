# -*- coding: utf-8 -*-
"""Regression tests for BurrowController lurker burrow-to-attack logic."""

import os
import sys
from unittest.mock import Mock

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from combat.formation_tactics import BurrowController
from sc2.ids.unit_typeid import UnitTypeId


class TestLurkerBurrowToAttack:
    """Lurkers must burrow when an enemy is within their attack range."""

    def setup_method(self):
        self.controller = BurrowController()
        self.down_ability = Mock(name="burrow_down")

    def _make_lurker(self, distance):
        unit = Mock()
        unit.type_id = UnitTypeId.LURKERMP
        unit.distance_to = Mock(return_value=distance)
        unit.is_idle = True
        return unit

    def test_lurker_burrows_when_enemy_in_attack_range(self):
        lurker = self._make_lurker(distance=5.0)
        enemy = Mock()
        action = self.controller._handle_unburrowed_unit(
            lurker,
            enemy_units=[enemy],
            health_ratio=1.0,
            enemy_nearby=True,
            down_ability=self.down_ability,
        )

        assert action is not None
        lurker.assert_called_once_with(self.down_ability)

    def test_lurker_stays_unburrowed_when_no_enemy_in_range(self):
        lurker = self._make_lurker(distance=20.0)
        enemy = Mock()
        action = self.controller._handle_unburrowed_unit(
            lurker,
            enemy_units=[enemy],
            health_ratio=1.0,
            enemy_nearby=False,
            down_ability=self.down_ability,
        )

        assert action is None
        lurker.assert_not_called()
