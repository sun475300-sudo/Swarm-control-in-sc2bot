# -*- coding: utf-8 -*-
"""
Unit tests for EvolutionUpgradeManager pure helpers.

Targets static / nearly-pure methods that have no async or live game state:
- _normalize_enemy_race
- _melee_unit_types / _ranged_unit_types / _air_unit_types
- _has_unit
- _is_upgrade_done
- _tech_requirement_met
- _can_research
- _next_upgrade (with a mock bot)
"""

import os
import sys
import unittest
from unittest.mock import MagicMock, Mock

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from sc2.ids.unit_typeid import UnitTypeId
from sc2.ids.upgrade_id import UpgradeId
from upgrade_manager import EvolutionUpgradeManager


def _make_manager():
    bot = Mock()
    bot.state = Mock()
    bot.state.upgrades = set()
    bot.already_pending_upgrade = Mock(return_value=0)
    bot.structures = Mock(return_value=Mock(ready=Mock(__bool__=lambda self: False)))
    return EvolutionUpgradeManager(bot), bot


class TestNormalizeEnemyRace(unittest.TestCase):
    def test_none_returns_empty(self):
        self.assertEqual(EvolutionUpgradeManager._normalize_enemy_race(None), "")

    def test_string_lowered(self):
        self.assertEqual(
            EvolutionUpgradeManager._normalize_enemy_race("Terran"), "terran"
        )

    def test_strips_race_prefix(self):
        self.assertEqual(
            EvolutionUpgradeManager._normalize_enemy_race("Race.Protoss"), "protoss"
        )

    def test_uses_name_attribute_when_available(self):
        race = MagicMock()
        race.name = "Zerg"
        self.assertEqual(EvolutionUpgradeManager._normalize_enemy_race(race), "zerg")


class TestUnitTypeBuckets(unittest.TestCase):
    def test_melee_includes_zergling_baneling_ultra(self):
        types = EvolutionUpgradeManager._melee_unit_types()
        self.assertIn(UnitTypeId.ZERGLING, types)
        self.assertIn(UnitTypeId.BANELING, types)
        self.assertIn(UnitTypeId.ULTRALISK, types)

    def test_ranged_includes_roach_hydra(self):
        types = EvolutionUpgradeManager._ranged_unit_types()
        self.assertIn(UnitTypeId.ROACH, types)
        self.assertIn(UnitTypeId.HYDRALISK, types)

    def test_air_includes_mutalisk_corruptor(self):
        types = EvolutionUpgradeManager._air_unit_types()
        self.assertIn(UnitTypeId.MUTALISK, types)
        self.assertIn(UnitTypeId.CORRUPTOR, types)
        self.assertIn(UnitTypeId.BROODLORD, types)


class TestHasUnit(unittest.TestCase):
    def test_empty_enemy_units_returns_false(self):
        self.assertFalse(EvolutionUpgradeManager._has_unit([], ["MARINE"]))
        self.assertFalse(EvolutionUpgradeManager._has_unit(None, ["MARINE"]))

    def test_match_by_name(self):
        e = Mock()
        e.type_id = UnitTypeId.MARINE
        self.assertTrue(EvolutionUpgradeManager._has_unit([e], ["MARINE"]))

    def test_no_match(self):
        e = Mock()
        e.type_id = UnitTypeId.MARINE
        self.assertFalse(EvolutionUpgradeManager._has_unit([e], ["MARAUDER"]))

    def test_unknown_name_silently_skipped(self):
        e = Mock()
        e.type_id = UnitTypeId.MARINE
        # _NOPE_NOT_A_UNIT_ doesn't exist on UnitTypeId — must not raise.
        self.assertTrue(
            EvolutionUpgradeManager._has_unit([e], ["_NOPE_NOT_A_UNIT_", "MARINE"])
        )


class TestUpgradeStateChecks(unittest.TestCase):
    def test_is_upgrade_done_true_when_in_state(self):
        m, bot = _make_manager()
        bot.state.upgrades = {UpgradeId.ZERGMELEEWEAPONSLEVEL1}
        self.assertTrue(m._is_upgrade_done(UpgradeId.ZERGMELEEWEAPONSLEVEL1))

    def test_is_upgrade_done_false_when_absent(self):
        m, _ = _make_manager()
        self.assertFalse(m._is_upgrade_done(UpgradeId.ZERGMELEEWEAPONSLEVEL1))

    def test_can_research_true_for_fresh_lvl1(self):
        m, _ = _make_manager()
        self.assertTrue(m._can_research(UpgradeId.ZERGMELEEWEAPONSLEVEL1))

    def test_can_research_false_when_already_done(self):
        m, bot = _make_manager()
        bot.state.upgrades = {UpgradeId.ZERGMELEEWEAPONSLEVEL1}
        self.assertFalse(m._can_research(UpgradeId.ZERGMELEEWEAPONSLEVEL1))

    def test_can_research_false_when_pending(self):
        m, bot = _make_manager()
        bot.already_pending_upgrade = Mock(return_value=1)
        self.assertFalse(m._can_research(UpgradeId.ZERGMELEEWEAPONSLEVEL1))


class TestTechRequirement(unittest.TestCase):
    def test_level1_always_true(self):
        m, _ = _make_manager()
        self.assertTrue(m._tech_requirement_met(UpgradeId.ZERGMELEEWEAPONSLEVEL1))

    def test_level2_requires_lair(self):
        m, bot = _make_manager()
        # No lair / hive
        self.assertFalse(m._tech_requirement_met(UpgradeId.ZERGMELEEWEAPONSLEVEL2))

    def test_level2_passes_with_lair(self):
        m, bot = _make_manager()

        # Mock structures: LAIR ready, HIVE not.
        def structures(unit_type):
            res = Mock()
            ready = Mock()
            ready.__bool__ = lambda self: unit_type == UnitTypeId.LAIR
            res.ready = ready
            res.__bool__ = lambda self: unit_type == UnitTypeId.LAIR
            return res

        bot.structures = Mock(side_effect=structures)
        self.assertTrue(m._tech_requirement_met(UpgradeId.ZERGMELEEWEAPONSLEVEL2))

    def test_level3_requires_hive(self):
        m, bot = _make_manager()

        # Lair exists, hive doesn't
        def structures(unit_type):
            res = Mock()
            ready = Mock()
            ready.__bool__ = lambda self: unit_type == UnitTypeId.LAIR
            res.ready = ready
            res.__bool__ = lambda self: unit_type == UnitTypeId.LAIR
            return res

        bot.structures = Mock(side_effect=structures)
        self.assertFalse(m._tech_requirement_met(UpgradeId.ZERGMELEEWEAPONSLEVEL3))


class TestNextUpgrade(unittest.TestCase):
    def test_returns_lvl1_when_nothing_done(self):
        m, _ = _make_manager()
        self.assertEqual(m._next_upgrade("melee"), UpgradeId.ZERGMELEEWEAPONSLEVEL1)

    def test_skips_done_upgrades(self):
        m, bot = _make_manager()
        bot.state.upgrades = {UpgradeId.ZERGMELEEWEAPONSLEVEL1}
        # lvl2 needs lair; we don't have one, so it should fall through to None.
        self.assertIsNone(m._next_upgrade("melee"))

    def test_skips_pending(self):
        m, bot = _make_manager()
        bot.already_pending_upgrade = Mock(
            side_effect=lambda u: 1 if u == UpgradeId.ZERGMELEEWEAPONSLEVEL1 else 0
        )
        # lvl1 pending → skip; lvl2 needs lair, none → None
        self.assertIsNone(m._next_upgrade("melee"))

    def test_unknown_lane_returns_none(self):
        m, _ = _make_manager()
        self.assertIsNone(m._next_upgrade("nonexistent_lane"))


if __name__ == "__main__":
    unittest.main()
