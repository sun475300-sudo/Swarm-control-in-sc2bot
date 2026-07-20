# -*- coding: utf-8 -*-
"""Regression test for CreepDenialSystem's threat-level retreat gate."""

import asyncio
import os
import sys
import unittest
from unittest.mock import Mock

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from creep_denial_system import CreepDenialSystem


class TestCreepDenialThreatGate(unittest.TestCase):
    def setUp(self):
        self.bot = Mock()
        self.bot.units = Mock()
        self.bot.units.find_by_tag = Mock(return_value=None)
        self.system = CreepDenialSystem(self.bot)
        self.system.managed_units = {1}

    def _run(self, is_under_attack: bool, threat_level: str):
        self.bot.intel = Mock()
        self.bot.intel.is_under_attack = Mock(return_value=is_under_attack)
        self.bot.intel.get_threat_level = Mock(return_value=threat_level)
        asyncio.run(self.system._check_and_retreat_units(game_time=100.0))

    def test_high_threat_level_passes_the_gate(self):
        """ "high" is a real value get_threat_level() can return (via the
        data-cache path) and must trigger the same retreat-eligibility
        check as "critical" -- the gate must not require "heavy", which
        get_threat_level() never actually produces."""
        self._run(is_under_attack=False, threat_level="high")

        self.bot.units.find_by_tag.assert_called_once_with(1)

    def test_medium_threat_without_attack_does_not_pass_the_gate(self):
        self._run(is_under_attack=False, threat_level="medium")

        self.bot.units.find_by_tag.assert_not_called()


if __name__ == "__main__":
    unittest.main()
