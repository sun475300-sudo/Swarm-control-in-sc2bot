# -*- coding: utf-8 -*-
"""
Regression test for upgrade_manager.py's race-priority-modifier bug found
during the 2026-07 audit:

`_get_upgrade_priority` fetched `self.race_priority_modifiers` keyed by
capitalized race name ("Terran"/"Protoss"/"Zerg") using the *lowercase*
string returned by `_normalize_enemy_race()`, so the lookup always missed
and the fetched `race_modifiers` dict was never applied to the upgrade
lane order - matchup-aware upgrade tuning silently never fired.
"""

import os
import sys
import unittest
from unittest.mock import Mock

os.environ["PROTOCOL_BUFFERS_PYTHON_IMPLEMENTATION"] = "python"
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
sys.modules.pop("utils", None)

from sc2.ids.upgrade_id import UpgradeId
from upgrade_manager import EvolutionUpgradeManager


class TestRacePriorityModifiersApplied(unittest.TestCase):
    def setUp(self):
        self.bot = Mock()
        self.bot.time = 300
        self.bot.structures = Mock()
        self.bot.state = Mock()
        self.bot.state.upgrades = []
        self.bot.already_pending_upgrade = Mock(return_value=0)
        self.bot.units = Mock(return_value=Mock(amount=0))

        self.manager = EvolutionUpgradeManager(self.bot)
        # Isolate the race-modifier reordering from the separate
        # matchup-upgrade-priority-table feature and unit-composition
        # scanning, which are not part of this bug.
        self.manager._update_intel_based_priorities = Mock()
        self.manager.get_matchup_upgrade_priority = Mock(return_value=[])

    def test_terran_prioritizes_armor_over_missile_when_ranged_heavy(self):
        # Ranged-heavy composition (8+ roaches) with no active enemy Terran
        # modifier applied would normally research missile before armor;
        # Terran's armor weight (1.3) should now flip that order.
        self.manager._get_unit_composition = Mock(
            return_value={
                "zergling": 0,
                "baneling": 0,
                "roach": 10,
                "hydralisk": 0,
                "mutalisk": 0,
                "corruptor": 0,
            }
        )
        self.bot.enemy_race = "Terran"

        order = self.manager._get_upgrade_priority()

        armor_idx = order.index(UpgradeId.ZERGGROUNDARMORSLEVEL1)
        missile_idx = order.index(UpgradeId.ZERGMISSILEWEAPONSLEVEL1)
        self.assertLess(
            armor_idx,
            missile_idx,
            "vs Terran (armor modifier 1.3 > missile 1.1), armor should be "
            "researched before missile, but race modifiers were not applied",
        )

    def test_zerg_prioritizes_melee_over_armor_when_melee_heavy(self):
        # Melee-heavy composition; vs Zerg, melee weight (1.3) should place
        # melee ahead of armor (1.0) in the base melee/armor alternation.
        self.manager._get_unit_composition = Mock(
            return_value={
                "zergling": 20,
                "baneling": 0,
                "roach": 0,
                "hydralisk": 0,
                "mutalisk": 0,
                "corruptor": 0,
            }
        )
        self.bot.enemy_race = "Zerg"

        order = self.manager._get_upgrade_priority()

        melee_idx = order.index(UpgradeId.ZERGMELEEWEAPONSLEVEL1)
        armor_idx = order.index(UpgradeId.ZERGGROUNDARMORSLEVEL1)
        self.assertLess(
            melee_idx,
            armor_idx,
            "vs Zerg (melee modifier 1.3 > armor 1.0), melee should be "
            "researched before armor, but race modifiers were not applied",
        )


if __name__ == "__main__":
    unittest.main()
