#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Roadmap Sprint 2.5: changelings must auto-deploy once an overseer has
>=50 energy, instead of relying on a manual caller that never existed in
production (see REMAINING_ISSUES.md / roadmap audit 2026-07-07)."""
import os
import sys
import unittest
from unittest.mock import MagicMock, Mock

os.environ["PROTOCOL_BUFFERS_PYTHON_IMPLEMENTATION"] = "python"
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from scouting_system import CHANGELING_ENERGY_COST, CHANGELING_REDEPLOY_INTERVAL, ScoutingSystem, UnitTypeId


class FakePoint:
    def __init__(self, x, y):
        self.x = float(x)
        self.y = float(y)

    def distance_to(self, other):
        return ((self.x - other.x) ** 2 + (self.y - other.y) ** 2) ** 0.5


class FakeOverseer:
    def __init__(self, tag, energy):
        self.tag = tag
        self.energy = energy
        self.position = FakePoint(10, 10)

    def __call__(self, ability):
        return f"ability-{ability}-{self.tag}"


class FakeUnits(list):
    @property
    def amount(self):
        return len(self)

    def closest_to(self, _target):
        return self[0] if self else None


class TestChangelingAutoDeploy(unittest.TestCase):
    def setUp(self):
        self.bot = MagicMock()
        self.bot.time = 120.0
        self.bot.blackboard = None
        self.bot.enemy_start_locations = [FakePoint(100, 100)]
        self.bot.do = Mock()
        self.scouting = ScoutingSystem(self.bot)

    def _with_overseer(self, energy):
        overseer = FakeOverseer(tag=1, energy=energy)
        self.bot.units = lambda unit_type: FakeUnits([overseer]) if unit_type == UnitTypeId.OVERSEER else FakeUnits([])
        return overseer

    def test_deploy_changeling_requires_enough_energy(self):
        self._with_overseer(energy=CHANGELING_ENERGY_COST - 1)

        result = self.scouting.deploy_changeling()

        self.assertFalse(result)
        self.bot.do.assert_not_called()

    def test_deploy_changeling_fires_with_enough_energy(self):
        self._with_overseer(energy=CHANGELING_ENERGY_COST)

        result = self.scouting.deploy_changeling()

        self.assertTrue(result)
        self.bot.do.assert_called_once()

    def test_maybe_deploy_changeling_respects_cooldown(self):
        self._with_overseer(energy=CHANGELING_ENERGY_COST)

        self.assertTrue(self.scouting.maybe_deploy_changeling(100.0))
        self.assertEqual(self.bot.do.call_count, 1)

        # Still within the redeploy cooldown -> no second cast.
        self.assertFalse(self.scouting.maybe_deploy_changeling(100.0 + CHANGELING_REDEPLOY_INTERVAL - 1))
        self.assertEqual(self.bot.do.call_count, 1)

        # Cooldown elapsed -> casts again.
        self.assertTrue(self.scouting.maybe_deploy_changeling(100.0 + CHANGELING_REDEPLOY_INTERVAL))
        self.assertEqual(self.bot.do.call_count, 2)

    def test_maybe_deploy_changeling_does_not_advance_cooldown_on_failure(self):
        self._with_overseer(energy=0)

        result = self.scouting.maybe_deploy_changeling(100.0)

        self.assertFalse(result)
        self.assertEqual(self.scouting.last_changeling_time, 0.0)


if __name__ == "__main__":
    unittest.main()
