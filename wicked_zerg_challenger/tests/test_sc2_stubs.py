# -*- coding: utf-8 -*-
"""Unit tests for utils.sc2_stubs."""

import os
import sys
import unittest

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from utils.sc2_stubs import (
    UnitTypeId,
    AbilityId,
    UpgradeId,
    Race,
    Difficulty,
    Point2,
    Point3,
    Units,
    Unit,
    BotAI,
)


class TestEnumLikeStubs(unittest.TestCase):
    def test_unit_type_arbitrary_attribute_returns_name(self):
        self.assertEqual(UnitTypeId.OVERLORD, "OVERLORD")
        self.assertEqual(UnitTypeId.ZERGLING.name, "ZERGLING")
        self.assertEqual(UnitTypeId.ZERGLING.value, "ZERGLING")

    def test_ability_id_attribute_access(self):
        self.assertEqual(AbilityId.ATTACK.name, "ATTACK")
        self.assertEqual(str(AbilityId.MOVE_MOVE), "MOVE_MOVE")

    def test_upgrade_and_race_and_difficulty(self):
        self.assertEqual(UpgradeId.ZERGLINGATTACKSPEED.name, "ZERGLINGATTACKSPEED")
        self.assertEqual(Race.Zerg.name, "Zerg")
        self.assertEqual(Difficulty.Medium.name, "Medium")

    def test_same_name_cached(self):
        # Same attribute must return the same object (cached)
        self.assertIs(UnitTypeId.ZERGLING, UnitTypeId.ZERGLING)

    def test_double_underscore_raises(self):
        # Dunders should raise — important for isinstance checks etc.
        with self.assertRaises(AttributeError):
            _ = UnitTypeId._private

    def test_is_str_subclass(self):
        self.assertIsInstance(UnitTypeId.MUTALISK, str)

    def test_used_as_dict_key(self):
        d = {UnitTypeId.ROACH: 1, UnitTypeId.HYDRALISK: 2}
        self.assertEqual(d[UnitTypeId.ROACH], 1)
        # Same name must hash identically
        self.assertEqual(d["ROACH"], 1)  # str equality works

    def test_subscript_lookup(self):
        # `Race["Zerg"]` 같은 enum-style lookup 지원
        member = Race["Zerg"]
        self.assertEqual(member.name, "Zerg")
        self.assertIs(member, Race.Zerg)

    def test_subscript_non_string_raises(self):
        with self.assertRaises(KeyError):
            _ = Race[42]  # type: ignore[misc]

    def test_contains_operator(self):
        m = Difficulty.Medium
        self.assertIn(m, Difficulty)
        # 평범한 문자열은 stub 멤버가 아니므로 False
        self.assertNotIn("Medium", Difficulty)

    def test_round_trip_serialize_via_name(self):
        # difficulty_progression.py가 하는 패턴: enum → name → enum
        original = Difficulty.Harder
        name = original.name
        restored = Difficulty[name]
        self.assertIs(restored, original)


class TestPoint2(unittest.TestCase):
    def test_construction_from_iterable(self):
        p = Point2((3.0, 4.0))
        self.assertEqual(p.x, 3.0)
        self.assertEqual(p.y, 4.0)

    def test_default_construction(self):
        p = Point2()
        self.assertEqual(p.x, 0.0)
        self.assertEqual(p.y, 0.0)

    def test_distance_to(self):
        p1 = Point2((0.0, 0.0))
        p2 = Point2((3.0, 4.0))
        self.assertEqual(p1.distance_to(p2), 5.0)

    def test_tuple_compatible(self):
        p = Point2((1.0, 2.0))
        self.assertEqual(tuple(p), (1.0, 2.0))
        self.assertEqual(p[0], 1.0)

    def test_point3_has_z(self):
        p = Point3((1.0, 2.0, 3.0))
        self.assertEqual(p.z, 3.0)


class TestUnits(unittest.TestCase):
    def test_construction_empty(self):
        units = Units([], None)
        self.assertEqual(len(units), 0)

    def test_construction_with_items(self):
        items = [1, 2, 3]
        units = Units(items, None)
        self.assertEqual(len(units), 3)
        self.assertEqual(list(units), items)

    def test_filter(self):
        units = Units([1, 2, 3, 4, 5], None)
        result = units.filter(lambda u: u % 2 == 0)
        self.assertEqual(list(result), [2, 4])
        # filter returns a Units, not a list
        self.assertIsInstance(result, Units)

    def test_amount_method(self):
        units = Units([1, 2, 3], None)
        self.assertEqual(units.amount(), 3)

    def test_closer_than(self):
        class FakeUnit:
            def __init__(self, d):
                self._d = d

            def distance_to(self, _pos):
                return self._d

        units = Units([FakeUnit(1.0), FakeUnit(5.0), FakeUnit(10.0)], None)
        result = units.closer_than(3.0, object())
        self.assertEqual(len(result), 1)


class TestPlaceholderClasses(unittest.TestCase):
    def test_unit_and_botai_instantiable(self):
        # Must at least be safe to instantiate / reference
        self.assertIsNotNone(Unit)
        self.assertIsNotNone(BotAI)
        u = Unit()
        b = BotAI()
        self.assertIsInstance(u, Unit)
        self.assertIsInstance(b, BotAI)


if __name__ == "__main__":
    unittest.main()
