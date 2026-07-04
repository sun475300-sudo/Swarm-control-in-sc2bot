# -*- coding: utf-8 -*-
"""
Unit tests for the queen priority-heal request mechanism.

Covers:
- QueenManager.request_priority_heal / _transfuse_injured_units honoring requests
- IdleUnitManager._retreat_wounded_units requesting priority heals for
  critically wounded units under fire
"""

import os
import sys
import unittest
from unittest.mock import Mock

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from sc2.ids.unit_typeid import UnitTypeId
from sc2.position import Point2

from idle_unit_manager import IdleUnitManager
from queen_manager import QueenManager


def make_unit(tag, unit_type, health, health_max, position=None, is_biological=True):
    unit = Mock()
    unit.tag = tag
    unit.type_id = unit_type
    unit.health = health
    unit.health_max = health_max
    unit.is_biological = is_biological
    unit.position = position or Point2((0, 0))
    return unit


class TestQueenManagerPriorityHeal(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        self.bot = Mock()
        self.bot.time = 100.0
        self.bot.do = Mock()
        self.manager = QueenManager(self.bot)

    def test_request_priority_heal_tracks_tag(self):
        self.manager.request_priority_heal(1234)
        self.assertIn(1234, self.manager.priority_heal_tags)

    async def test_priority_requested_unit_skips_health_gate(self):
        # 28% HP: fails the CreepyBot gate (health_deficit < 125 and
        # health_ratio >= 0.25 is False here because 0.28 >= 0.25 is True,
        # so it's normally SKIPPED unless explicitly requested).
        wounded = make_unit(
            tag=555, unit_type=UnitTypeId.ZERGLING, health=14, health_max=50
        )
        self.bot.units = [wounded]
        queen = Mock()
        queen.tag = 999
        queen.energy = 100
        queen.distance_to = Mock(return_value=1.0)
        queen.can_cast = Mock(return_value=True)

        self.manager.request_priority_heal(555)
        await self.manager._transfuse_injured_units([queen], iteration=0)

        self.bot.do.assert_called_once()
        # The request is consumed after one pass.
        self.assertNotIn(555, self.manager.priority_heal_tags)

    async def test_unrequested_lightly_wounded_unit_is_not_healed(self):
        # Same 28% HP unit, but never flagged - should be skipped by the gate.
        wounded = make_unit(
            tag=556, unit_type=UnitTypeId.ZERGLING, health=14, health_max=50
        )
        self.bot.units = [wounded]
        queen = Mock()
        queen.tag = 999
        queen.energy = 100
        queen.distance_to = Mock(return_value=1.0)
        queen.can_cast = Mock(return_value=True)

        await self.manager._transfuse_injured_units([queen], iteration=0)

        self.bot.do.assert_not_called()


class TestIdleUnitManagerRetreatRequestsHeal(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        self.bot = Mock()
        self.bot.queen_manager = Mock()
        self.manager = IdleUnitManager(self.bot)

    async def test_retreat_requests_priority_heal_when_enemies_nearby(self):
        base = Mock()
        base.position = Point2((10, 10))
        self.bot.townhalls = Mock()
        self.bot.townhalls.exists = True
        self.bot.townhalls.first = base
        self.bot.townhalls.closest_to = Mock(return_value=base)

        wounded = make_unit(
            tag=42,
            unit_type=UnitTypeId.ROACH,
            health=20,
            health_max=100,  # 20% HP -> below the 30% retreat threshold
        )
        self.bot.units = Mock()
        self.bot.units.filter = Mock(return_value=[wounded])

        nearby_enemies = Mock()
        nearby_enemies.exists = True
        self.bot.enemy_units = Mock()
        self.bot.enemy_units.closer_than = Mock(return_value=nearby_enemies)
        self.bot.do = Mock()

        await self.manager._retreat_wounded_units()

        self.bot.queen_manager.request_priority_heal.assert_called_once_with(42)

    async def test_retreat_skips_heal_request_without_nearby_enemies(self):
        base = Mock()
        base.position = Point2((10, 10))
        self.bot.townhalls = Mock()
        self.bot.townhalls.exists = True
        self.bot.townhalls.first = base

        wounded = make_unit(
            tag=43, unit_type=UnitTypeId.ROACH, health=20, health_max=100
        )
        self.bot.units = Mock()
        self.bot.units.filter = Mock(return_value=[wounded])

        no_enemies = Mock()
        no_enemies.exists = False
        self.bot.enemy_units = Mock()
        self.bot.enemy_units.closer_than = Mock(return_value=no_enemies)

        await self.manager._retreat_wounded_units()

        self.bot.queen_manager.request_priority_heal.assert_not_called()


if __name__ == "__main__":
    unittest.main()
