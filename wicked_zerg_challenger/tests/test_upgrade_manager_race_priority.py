# -*- coding: utf-8 -*-
"""
Regression test for Phase 18 race-specific upgrade priority.

Bug: EvolutionUpgradeManager._get_upgrade_priority() computed
`race_modifiers` from `self.race_priority_modifiers` but (a) looked the
value up with a lower-cased race name against capitalized dict keys
(always missed) and (b) never applied the modifiers to the `priorities`
list even if the lookup had succeeded. As a result the "종족별 우선순위
조정" (race-specific priority adjustment) feature never actually ran.
"""

import os
import sys
import unittest
from unittest.mock import MagicMock

os.environ["PROTOCOL_BUFFERS_PYTHON_IMPLEMENTATION"] = "python"
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from sc2.ids.unit_typeid import UnitTypeId
from sc2.ids.upgrade_id import UpgradeId
from upgrade_manager import EvolutionUpgradeManager


def _make_melee_heavy_bot(enemy_race: str) -> MagicMock:
    bot = MagicMock()
    bot.time = 200.0  # "early" matchup phase -> only ZERGLINGMOVEMENTSPEED prefixed
    bot.enemy_race = enemy_race
    bot.enemy_units = []
    bot.state.upgrades = set()
    bot.already_pending_upgrade.return_value = 0

    unit_counts = {
        UnitTypeId.ZERGLING: 20,
        UnitTypeId.BANELING: 0,
        UnitTypeId.ROACH: 0,
        UnitTypeId.HYDRALISK: 0,
        UnitTypeId.MUTALISK: 0,
        UnitTypeId.CORRUPTOR: 0,
        UnitTypeId.ULTRALISK: 0,
    }

    def units_side_effect(unit_type):
        result = MagicMock()
        result.amount = unit_counts.get(unit_type, 0)
        return result

    bot.units.side_effect = units_side_effect
    return bot


class TestUpgradeManagerRacePriority(unittest.TestCase):
    def test_terran_prioritizes_armor_over_melee(self):
        manager = EvolutionUpgradeManager(_make_melee_heavy_bot("Terran"))
        order = manager._get_upgrade_priority()

        self.assertIn(UpgradeId.ZERGGROUNDARMORSLEVEL1, order)
        self.assertIn(UpgradeId.ZERGMELEEWEAPONSLEVEL1, order)
        self.assertLess(
            order.index(UpgradeId.ZERGGROUNDARMORSLEVEL1),
            order.index(UpgradeId.ZERGMELEEWEAPONSLEVEL1),
            "vs Terran, armor (modifier 1.3) should be prioritized over melee (1.0)",
        )

    def test_zerg_prioritizes_melee_over_armor(self):
        manager = EvolutionUpgradeManager(_make_melee_heavy_bot("Zerg"))
        order = manager._get_upgrade_priority()

        self.assertIn(UpgradeId.ZERGGROUNDARMORSLEVEL1, order)
        self.assertIn(UpgradeId.ZERGMELEEWEAPONSLEVEL1, order)
        self.assertLess(
            order.index(UpgradeId.ZERGMELEEWEAPONSLEVEL1),
            order.index(UpgradeId.ZERGGROUNDARMORSLEVEL1),
            "vs Zerg, melee (modifier 1.3) should be prioritized over armor (1.0)",
        )

    def test_race_modifiers_lookup_matches_capitalized_keys(self):
        manager = EvolutionUpgradeManager(_make_melee_heavy_bot("Terran"))
        normalized = manager._normalize_enemy_race(manager.bot.enemy_race)

        self.assertEqual(normalized, "terran")
        self.assertIn(normalized.capitalize(), manager.race_priority_modifiers)


if __name__ == "__main__":
    unittest.main()
