# -*- coding: utf-8 -*-
"""
Unit tests -- DefenseCoordinator army reserve split (P1-5)

Locks in the behaviour: when defending, only up to 50% of the total
combat army is committed to the threatened base. The rest is left in
place (implicitly staged for the next attack) instead of being pulled
in wholesale.
"""

import asyncio
import os
import sys
import unittest
from types import SimpleNamespace
from unittest.mock import Mock

os.environ["PROTOCOL_BUFFERS_PYTHON_IMPLEMENTATION"] = "python"
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from defense_coordinator import DefenseCoordinator
from sc2.ids.unit_typeid import UnitTypeId


class FakePoint:
    def __init__(self, x=0, y=0):
        self.x = x
        self.y = y

    def distance_to(self, other):
        other = getattr(other, "position", other)
        return ((self.x - other.x) ** 2 + (self.y - other.y) ** 2) ** 0.5

    def towards(self, other, distance):
        return FakePoint(self.x + distance, self.y)


class FakeUnit:
    def __init__(self, position, tag):
        self.position = position
        self.tag = tag

    def distance_to(self, other):
        return self.position.distance_to(other)

    def move(self, target):
        return ("move", self.tag, target)


class FakeUnits(list):
    @property
    def idle(self):
        return self

    @property
    def first(self):
        return self[0] if self else None

    def closer_than(self, distance, target):
        return FakeUnits([u for u in self if u.distance_to(target) < distance])


def _make_bot(zergling_count, base_pos=FakePoint(0, 0)):
    townhall = FakeUnit(base_pos, tag="th")
    zerglings = FakeUnits(
        [FakeUnit(FakePoint(20 + i, 0), tag=f"ling{i}") for i in range(zergling_count)]
    )

    def units(unit_type):
        if unit_type == UnitTypeId.ZERGLING:
            return zerglings
        return FakeUnits()

    bot = Mock()
    bot.townhalls = FakeUnits([townhall])
    bot.units = Mock(side_effect=units)
    bot.game_info = SimpleNamespace(map_center=FakePoint(100, 100))
    bot.do = Mock()
    return bot, zerglings


class TestDefenseReserveSplit(unittest.TestCase):
    def test_only_half_the_army_is_committed_to_defense(self):
        bot, zerglings = _make_bot(zergling_count=10)
        blackboard = SimpleNamespace(
            should_defend=Mock(return_value=True),
            attacked_bases=set(),
            get=Mock(return_value=set()),
            set=Mock(),
        )
        coordinator = DefenseCoordinator(bot, blackboard)

        asyncio.run(coordinator._position_defense_units())

        # 10 zerglings total -> at most 5 should be ordered to move.
        self.assertEqual(bot.do.call_count, 5)

    def test_small_army_still_sends_at_least_one_defender(self):
        bot, zerglings = _make_bot(zergling_count=1)
        blackboard = SimpleNamespace(
            should_defend=Mock(return_value=True),
            attacked_bases=set(),
            get=Mock(return_value=set()),
            set=Mock(),
        )
        coordinator = DefenseCoordinator(bot, blackboard)

        asyncio.run(coordinator._position_defense_units())

        self.assertEqual(bot.do.call_count, 1)

    def test_no_army_sends_no_defenders(self):
        bot, zerglings = _make_bot(zergling_count=0)
        blackboard = SimpleNamespace(
            should_defend=Mock(return_value=True),
            attacked_bases=set(),
            get=Mock(return_value=set()),
            set=Mock(),
        )
        coordinator = DefenseCoordinator(bot, blackboard)

        asyncio.run(coordinator._position_defense_units())

        self.assertEqual(bot.do.call_count, 0)


if __name__ == "__main__":
    unittest.main()
