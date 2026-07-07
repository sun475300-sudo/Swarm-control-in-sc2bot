# -*- coding: utf-8 -*-
"""
Regression tests for combat_manager.py bugs found during the 2026-07 audit:

1. `_is_base_under_attack` / `_evaluate_base_threat` checked for the string
   "LURKER", which does not exist as a python-sc2 UnitTypeId name (ladder
   Lurkers are LURKERMP / LURKERMPBURROWED) - so Lurker-only attacks were
   never classified as a combat threat.

2. `_evaluate_army_retreat` computed `enemy_supply` from *all* nearby
   `enemy_units` with no can_attack filter, while `our_supply` was computed
   only from combat-typed units - inflating the enemy side with workers/
   overlords/observers and triggering unwarranted retreats.
"""

import os
import sys
import unittest
from unittest.mock import AsyncMock, Mock

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from combat_manager import CombatManager
from sc2.ids.unit_typeid import UnitTypeId
from sc2.position import Point2


class FakeUnit:
    def __init__(self, type_id, position, tag=1, can_attack=True):
        self.type_id = type_id
        self.position = position
        self.tag = tag
        self.can_attack = can_attack
        self.can_attack_air = can_attack
        self.can_attack_ground = can_attack
        self.health = 100
        self.shield = 0

    def distance_to(self, other):
        pos = getattr(other, "position", other)
        return ((self.position.x - pos.x) ** 2 + (self.position.y - pos.y) ** 2) ** 0.5


class FakeTownhall(FakeUnit):
    def __init__(self, position, tag=1):
        super().__init__(UnitTypeId.HATCHERY, position, tag=tag)


class FakeUnitList(list):
    @property
    def exists(self):
        return len(self) > 0


class TestLurkerIsRecognizedAsCombatThreat(unittest.TestCase):
    def setUp(self):
        self.bot = Mock()
        th = FakeTownhall(Point2((50, 50)))
        self.bot.townhalls = FakeUnitList([th])
        self.bot.iteration = 0
        self.bot.time = 200
        self.manager = CombatManager(self.bot)

    def test_single_lurker_triggers_base_under_attack(self):
        lurker = FakeUnit(UnitTypeId.LURKERMP, Point2((55, 50)), tag=99)
        self.bot.enemy_units = [lurker]

        self.assertTrue(self.manager._is_base_under_attack())

    def test_single_burrowed_lurker_triggers_base_under_attack(self):
        lurker = FakeUnit(UnitTypeId.LURKERMPBURROWED, Point2((55, 50)), tag=100)
        self.bot.enemy_units = [lurker]

        self.assertTrue(self.manager._is_base_under_attack())

    def test_single_scv_alone_does_not_trigger(self):
        # Sanity check: a lone non-combat scout should NOT be a threat,
        # confirming the fix didn't loosen detection generally.
        scv = FakeUnit(UnitTypeId.SCV, Point2((55, 50)), tag=101)
        self.bot.enemy_units = [scv]

        self.assertFalse(self.manager._is_base_under_attack())


class TestRetreatEvaluationIgnoresNonCombatEnemies(unittest.IsolatedAsyncioTestCase):
    async def test_worker_and_overlord_do_not_inflate_enemy_supply(self):
        bot = Mock()
        bot.time = 300
        bot.do = AsyncMock()

        manager = CombatManager(bot)
        manager._victory_push_active = False

        # 5 roaches (supply 2 each -> our_supply 10, clears the `< 5` early
        # return) as our army, facing a swarm of non-combat enemy units that
        # should NOT count towards "enemy supply".
        our_units = [
            FakeUnit(UnitTypeId.ROACH, Point2((10, 10)), tag=i, can_attack=True)
            for i in range(5)
        ]

        class FakeUnitsCollection(list):
            @property
            def exists(self):
                return len(self) > 0

            def filter(self, fn):
                return FakeUnitsCollection(u for u in self if fn(u))

            def closer_than(self, distance, point):
                return FakeUnitsCollection(
                    u for u in self if u.distance_to(point) < distance
                )

            @property
            def center(self):
                xs = [u.position.x for u in self]
                ys = [u.position.y for u in self]
                return Point2((sum(xs) / len(xs), sum(ys) / len(ys)))

        bot.units = FakeUnitsCollection(our_units)

        # Enemy side: mostly non-attacking units (workers/overlords) that
        # should be excluded from the enemy_supply calculation, plus zero
        # actual combat units - so no retreat should be warranted at all.
        non_combat_enemies = [
            FakeUnit(UnitTypeId.SCV, Point2((11, 10)), tag=200 + i, can_attack=False)
            for i in range(20)
        ]
        bot.enemy_units = FakeUnitsCollection(non_combat_enemies)

        manager._retreat_to_base = AsyncMock()
        manager._retreat_to_closest_base = AsyncMock()
        manager._retreat_to_rally = AsyncMock()

        await manager._evaluate_army_retreat(iteration=0)

        # A pile of harmless workers must not trigger any retreat behavior.
        manager._retreat_to_base.assert_not_called()
        manager._retreat_to_closest_base.assert_not_called()
        manager._retreat_to_rally.assert_not_called()


if __name__ == "__main__":
    unittest.main()
