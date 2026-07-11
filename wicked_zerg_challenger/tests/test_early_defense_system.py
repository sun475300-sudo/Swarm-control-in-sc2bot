# -*- coding: utf-8 -*-
"""Regression tests for EarlyDefenseSystem emergency defense."""

import asyncio
import os
import sys
import unittest

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from early_defense_system import EarlyDefenseSystem
from sc2.ids.unit_typeid import UnitTypeId
from sc2.position import Point2


class FakeUnits(list):
    @property
    def exists(self):
        return bool(self)

    @property
    def amount(self):
        return len(self)

    @property
    def first(self):
        return self[0]

    def filter(self, predicate):
        return FakeUnits([unit for unit in self if predicate(unit)])

    def closest_to(self, target):
        return min(self, key=lambda unit: unit.distance_to(target))

    def closest_n_units(self, target, count):
        return FakeUnits(
            sorted(self, key=lambda unit: unit.distance_to(target))[:count]
        )


class UnitSource(FakeUnits):
    def __call__(self, unit_type):
        return FakeUnits([unit for unit in self if unit.type_id == unit_type])


class FakeUnit:
    def __init__(self, tag, unit_type, position, is_idle=True, is_moving=False):
        self.tag = tag
        self.type_id = unit_type
        self.position = position
        self.is_idle = is_idle
        self.is_moving = is_moving
        self.orders = []

    def distance_to(self, target):
        target_pos = getattr(target, "position", target)
        return self.position.distance_to(target_pos)

    def attack(self, target):
        return ("attack", self.tag, target)


class FakeBot:
    def __init__(self):
        self.time = 60.0
        self.iteration = 22
        self.actions = []
        self.townhalls = FakeUnits([FakeUnit(1, UnitTypeId.HATCHERY, Point2((50, 50)))])
        self.workers = FakeUnits([])
        zergling = FakeUnit(10, UnitTypeId.ZERGLING, Point2((51, 50)))
        self.units = UnitSource([zergling])
        enemy = FakeUnit(100, UnitTypeId.ZEALOT, Point2((55, 55)))
        self.enemy_units = FakeUnits([enemy])
        self.enemy_structures = FakeUnits()
        self.mineral_field = FakeUnits()
        self.supply_used = 12
        self.structures = UnitSource([])

    def do(self, action):
        self.actions.append(action)


class TestEmergencyDefenseZerglingAttack(unittest.TestCase):
    """Regression: idle/moving zerglings must be ordered to attack
    individually via bot.do(unit.attack(...)), not by calling .attack()
    directly on the Units collection (sc2.units.Units has no such method
    and previously raised AttributeError every time this path ran)."""

    def test_idle_zerglings_receive_individual_attack_orders(self):
        bot = FakeBot()
        defense = EarlyDefenseSystem(bot)
        defense.early_threats = {u.tag for u in bot.enemy_units}
        defense.emergency_mode = True

        asyncio.run(defense._emergency_defense())

        attack_actions = [a for a in bot.actions if a[0] == "attack"]
        self.assertEqual(len(attack_actions), 1)
        self.assertEqual(attack_actions[0][1], 10)  # zergling tag


if __name__ == "__main__":
    unittest.main(verbosity=2)
