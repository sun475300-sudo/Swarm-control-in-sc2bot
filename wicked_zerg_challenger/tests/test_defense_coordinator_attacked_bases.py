# -*- coding: utf-8 -*-
"""Regression: attacked_bases stale-tag accumulation in DefenseCoordinator."""

import os
import sys
import unittest
from types import SimpleNamespace
from unittest.mock import Mock

os.environ["PROTOCOL_BUFFERS_PYTHON_IMPLEMENTATION"] = "python"
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from defense_coordinator import DefenseCoordinator


class _FakePoint:
    def __init__(self, x=0.0, y=0.0):
        self.x = x
        self.y = y

    def distance_to(self, other):
        other = getattr(other, "position", other)
        return ((self.x - other.x) ** 2 + (self.y - other.y) ** 2) ** 0.5


class _FakeUnit:
    def __init__(self, tag, position=None):
        self.tag = tag
        self.position = position or _FakePoint()

    def distance_to(self, other):
        return self.position.distance_to(other)


class _FakeUnits(list):
    def closer_than(self, distance, target):
        target = getattr(target, "position", target)
        return _FakeUnits([u for u in self if u.distance_to(target) < distance])


class _Blackboard:
    def __init__(self):
        self.is_under_attack = False
        self.attacked_bases = set()


class TestAttackedBasesRefresh(unittest.TestCase):
    def setUp(self):
        self.main = _FakeUnit(1, _FakePoint(0, 0))
        self.natural = _FakeUnit(2, _FakePoint(50, 0))

        self.bot = Mock()
        self.bot.time = 200.0
        self.bot.townhalls = _FakeUnits([self.main, self.natural])
        self.bot.enemy_units = _FakeUnits()

        self.blackboard = _Blackboard()

        # Bypass __init__ — we only need _update_blackboard_threat
        self.coord = DefenseCoordinator.__new__(DefenseCoordinator)
        self.coord.bot = self.bot
        self.coord.blackboard = self.blackboard
        self.coord.detected_threats = []

    def test_no_threats_clears_attacked_bases(self):
        # Pre-populate with stale tags from a prior frame
        self.blackboard.attacked_bases = {1, 2, 999}

        self.coord.detected_threats = []
        self.coord._update_blackboard_threat()

        self.assertFalse(self.blackboard.is_under_attack)
        self.assertEqual(self.blackboard.attacked_bases, set())

    def test_only_currently_attacked_bases_remain(self):
        self.blackboard.attacked_bases = {2, 999}  # stale tag 999

        self.coord.detected_threats = [Mock()]
        # Enemy only near the main hatchery, not the natural
        self.bot.enemy_units = _FakeUnits([_FakeUnit(100, _FakePoint(1, 0))])

        self.coord._update_blackboard_threat()

        self.assertTrue(self.blackboard.is_under_attack)
        self.assertEqual(self.blackboard.attacked_bases, {self.main.tag})


if __name__ == "__main__":
    unittest.main()
