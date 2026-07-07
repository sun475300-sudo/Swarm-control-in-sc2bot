# -*- coding: utf-8 -*-
"""
Unit tests for BurrowController, focused on the Lurker burrow-to-attack
regression: Lurkers only deal damage while burrowed, so an idle Lurker
with an enemy inside its 9.0 attack range must burrow.
"""

import os
import sys
import unittest
from unittest.mock import Mock

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from combat.formation_tactics import BurrowController
from sc2.ids.unit_typeid import UnitTypeId
from sc2.ids.upgrade_id import UpgradeId


def make_unit(
    type_id, tag=1, is_idle=True, is_burrowed=False, health=100, health_max=100
):
    unit = Mock()
    unit.type_id = type_id
    unit.tag = tag
    unit.is_idle = is_idle
    unit.is_burrowed = is_burrowed
    unit.health = health
    unit.health_max = health_max
    unit.distance_to = Mock(return_value=5.0)
    return unit


def make_bot():
    bot = Mock()
    bot.state = Mock()
    bot.state.upgrades = {UpgradeId.BURROW}
    return bot


class TestBurrowControllerLurker(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        self.controller = BurrowController()
        self.bot = make_bot()
        self.actions = []

        async def do_actions_func(actions):
            self.actions.extend(actions)

        self.do_actions_func = do_actions_func

    async def test_idle_lurker_burrows_when_enemy_in_range(self):
        lurker = make_unit(UnitTypeId.LURKERMP, is_idle=True, is_burrowed=False)
        enemy = make_unit(UnitTypeId.MARINE, tag=2)
        enemy.distance_to = Mock(return_value=6.0)  # within lurker_burrow_range (8.0)
        lurker.distance_to = Mock(return_value=6.0)

        skip_units = await self.controller.handle_burrow(
            [lurker],
            [enemy],
            iteration=100,
            do_actions_func=self.do_actions_func,
            bot=self.bot,
        )

        self.assertEqual(len(self.actions), 1)
        self.assertIn(lurker.tag, skip_units)

    async def test_idle_lurker_stays_unburrowed_when_no_enemy_in_range(self):
        lurker = make_unit(UnitTypeId.LURKERMP, is_idle=True, is_burrowed=False)
        enemy = make_unit(UnitTypeId.MARINE, tag=2)
        enemy.distance_to = Mock(return_value=20.0)  # beyond lurker_burrow_range
        lurker.distance_to = Mock(return_value=20.0)

        skip_units = await self.controller.handle_burrow(
            [lurker],
            [enemy],
            iteration=100,
            do_actions_func=self.do_actions_func,
            bot=self.bot,
        )

        self.assertEqual(len(self.actions), 0)
        self.assertNotIn(lurker.tag, skip_units)

    async def test_non_idle_lurker_does_not_burrow(self):
        lurker = make_unit(UnitTypeId.LURKERMP, is_idle=False, is_burrowed=False)
        enemy = make_unit(UnitTypeId.MARINE, tag=2)
        enemy.distance_to = Mock(return_value=6.0)
        lurker.distance_to = Mock(return_value=6.0)

        skip_units = await self.controller.handle_burrow(
            [lurker],
            [enemy],
            iteration=100,
            do_actions_func=self.do_actions_func,
            bot=self.bot,
        )

        self.assertEqual(len(self.actions), 0)
        self.assertNotIn(lurker.tag, skip_units)

    async def test_burrowed_lurker_unburrows_when_no_enemy_within_hysteresis_range(
        self,
    ):
        lurker = make_unit(UnitTypeId.LURKERMPBURROWED, is_idle=True, is_burrowed=True)
        enemy = make_unit(UnitTypeId.MARINE, tag=2)
        enemy.distance_to = Mock(return_value=15.0)  # beyond 10.0 hysteresis range
        lurker.distance_to = Mock(return_value=15.0)

        skip_units = await self.controller.handle_burrow(
            [lurker],
            [enemy],
            iteration=100,
            do_actions_func=self.do_actions_func,
            bot=self.bot,
        )

        self.assertEqual(len(self.actions), 1)
        self.assertIn(lurker.tag, skip_units)


if __name__ == "__main__":
    unittest.main()
