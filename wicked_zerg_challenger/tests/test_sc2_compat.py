# -*- coding: utf-8 -*-
"""Unit tests for `utils.sc2_compat`.

The compat shim lets every module import cleanly when burnysc2 is not
installed. These tests pin its contract:

* Stub IDs (UnitTypeId, AbilityId, UpgradeId, BuffId, EffectId) accept
  arbitrary attribute access and return cached `_Sentinel` objects.
* Sentinels expose `.name`, support equality with each other and with
  strings, and are hashable for use in sets / dict keys.
* `Race[name]` / `Difficulty[name]`-style subscript lookup works even
  on the stub (used by `_deserialize_stats` in difficulty_progression).
* Point2 has value-based equality and a working `distance_to`.

These contracts are exactly the bugs we hit while running the existing
test suite, so they are worth pinning so they don't regress.
"""

import os
import sys
import unittest

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from utils.sc2_compat import (  # noqa: E402
    AbilityId,
    Point2,
    Point3,
    Race,
    UnitTypeId,
    UpgradeId,
    _Sentinel,
)


class TestStubIds(unittest.TestCase):
    def test_attribute_access_returns_sentinel(self):
        zergling = UnitTypeId.ZERGLING
        self.assertIsInstance(zergling, _Sentinel)
        self.assertEqual(zergling.name, "ZERGLING")

    def test_repeated_access_returns_same_object(self):
        # Cached per attribute name to make `in {set}` checks cheap.
        self.assertIs(UnitTypeId.ROACH, UnitTypeId.ROACH)

    def test_sentinels_hashable_and_set_membership_works(self):
        bag = {UnitTypeId.ZERGLING, UnitTypeId.ROACH, UnitTypeId.ZERGLING}
        # Set should de-dupe to two entries.
        self.assertEqual(len(bag), 2)
        self.assertIn(UnitTypeId.ZERGLING, bag)

    def test_equality_with_string_name(self):
        # Some legacy code compares directly with the name string.
        self.assertEqual(UnitTypeId.HYDRALISK, "HYDRALISK")
        self.assertNotEqual(UnitTypeId.HYDRALISK, "ZERGLING")

    def test_equality_across_id_classes_is_false(self):
        # An UnitTypeId.X must never compare equal to AbilityId.X.
        self.assertNotEqual(UnitTypeId.QUEEN, AbilityId.QUEEN)

    def test_subscript_access_for_serialized_lookup(self):
        # difficulty_progression._deserialize_stats does Race[serialized_str].
        zerg_via_attr = Race.Zerg
        zerg_via_subscript = Race["Zerg"]
        self.assertEqual(zerg_via_attr, zerg_via_subscript)

    def test_str_returns_just_the_name(self):
        self.assertEqual(str(UpgradeId.METABOLICBOOST), "METABOLICBOOST")


class TestPoint2(unittest.TestCase):
    def test_value_equality(self):
        self.assertEqual(Point2((3.0, 4.0)), Point2((3.0, 4.0)))

    def test_inequality_different_coords(self):
        self.assertNotEqual(Point2((3, 4)), Point2((3, 5)))

    def test_distance_to_pythagorean(self):
        p1 = Point2((0, 0))
        p2 = Point2((3, 4))
        self.assertAlmostEqual(p1.distance_to(p2), 5.0)

    def test_distance_to_invalid_other_returns_zero(self):
        # Defensive: callers sometimes pass arbitrary objects.
        self.assertEqual(Point2((1, 2)).distance_to(object()), 0.0)

    def test_iter_yields_x_then_y(self):
        x, y = Point2((7, 9))
        self.assertEqual((x, y), (7.0, 9.0))

    def test_hashable_can_live_in_set(self):
        s = {Point2((1, 2)), Point2((1, 2)), Point2((3, 4))}
        self.assertEqual(len(s), 2)


class TestPoint3(unittest.TestCase):
    def test_constructed_from_3tuple(self):
        p = Point3((1, 2, 3))
        self.assertEqual((p.x, p.y, p.z), (1.0, 2.0, 3.0))

    def test_short_tuple_falls_back_to_zero_z(self):
        p = Point3((1, 2))  # type: ignore[arg-type]
        self.assertEqual(p.z, 0.0)


if __name__ == "__main__":
    unittest.main()
