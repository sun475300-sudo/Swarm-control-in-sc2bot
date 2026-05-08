"""Tests for utils.sc2_stubs — fallback shim used when python-sc2 is missing."""

import os
import sys
import unittest

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from utils.sc2_stubs import (
    SC2_AVAILABLE,
    AbilityId,
    BotAI,
    BuffId,
    Difficulty,
    EffectId,
    Point2,
    Point3,
    Race,
    Unit,
    UnitTypeId,
    UpgradeId,
)


class TestStubEnums(unittest.TestCase):
    def test_unit_typeid_attribute_returns_name(self):
        # Stub uses __getattr__ to return the attribute name
        self.assertEqual(UnitTypeId.ZERGLING, "ZERGLING")
        self.assertEqual(UnitTypeId.QUEEN, "QUEEN")
        self.assertEqual(UnitTypeId.HATCHERY, "HATCHERY")

    def test_ability_id_attribute_returns_name(self):
        self.assertEqual(AbilityId.TRANSFUSION_TRANSFUSION, "TRANSFUSION_TRANSFUSION")

    def test_upgrade_id_attribute(self):
        self.assertEqual(UpgradeId.ZERGLINGMOVEMENTSPEED, "ZERGLINGMOVEMENTSPEED")

    def test_buff_and_effect_ids_work(self):
        self.assertEqual(BuffId.LURKERHOLDFLEEING, "LURKERHOLDFLEEING")
        self.assertEqual(EffectId.PSISTORMPERSISTENT, "PSISTORMPERSISTENT")


class TestPoint2(unittest.TestCase):
    def test_default_zero(self):
        p = Point2()
        self.assertEqual(p.x, 0)
        self.assertEqual(p.y, 0)

    def test_two_tuple(self):
        p = Point2((3, 4))
        self.assertEqual(p.x, 3)
        self.assertEqual(p.y, 4)

    def test_distance_to(self):
        a = Point2((0, 0))
        b = Point2((3, 4))
        self.assertEqual(a.distance_to(b), 5.0)

    def test_distance_to_self_is_zero(self):
        p = Point2((10, 10))
        self.assertEqual(p.distance_to(p), 0.0)


class TestRaceDifficulty(unittest.TestCase):
    def test_race_members_present(self):
        for name in ["NoRace", "Terran", "Zerg", "Protoss", "Random"]:
            self.assertTrue(hasattr(Race, name))

    def test_difficulty_ladder_intact(self):
        # The ladder must contain entries from VeryEasy → CheatInsane
        for name in ["VeryEasy", "Easy", "Medium", "Hard", "VeryHard", "CheatInsane"]:
            self.assertTrue(hasattr(Difficulty, name))

    def test_race_name_round_trip(self):
        # Race[name] must be able to recover the enum from its name
        self.assertIs(Race["Zerg"], Race.Zerg)
        self.assertIs(Difficulty["Hard"], Difficulty.Hard)


class TestStubClasses(unittest.TestCase):
    def test_botai_is_class(self):
        self.assertTrue(isinstance(BotAI, type))

    def test_unit_is_class(self):
        self.assertTrue(isinstance(Unit, type))

    def test_point3_is_class(self):
        self.assertTrue(isinstance(Point3, type))

    def test_sc2_unavailable_marker(self):
        self.assertFalse(SC2_AVAILABLE)


if __name__ == "__main__":
    unittest.main()
