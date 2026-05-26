# -*- coding: utf-8 -*-
"""common_helpers 단위 테스트.

has_units / safe_first / safe_closest / safe_amount / clamp / percentage
헬퍼들의 정상/엣지 케이스(None, 빈 컬렉션, SC2 Units 인터페이스 mock,
일반 리스트 fallback)를 모두 확인한다.
"""

import os
import sys
import unittest

os.environ["PROTOCOL_BUFFERS_PYTHON_IMPLEMENTATION"] = "python"
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from utils.common_helpers import (
    clamp,
    has_units,
    percentage,
    safe_amount,
    safe_closest,
    safe_first,
)


class _SC2UnitsLike:
    """SC2 Units collection을 흉내 내는 stub."""

    def __init__(self, items, sc2_first=None):
        self._items = list(items)
        self._sc2_first = sc2_first

    @property
    def exists(self):
        return len(self._items) > 0

    @property
    def amount(self):
        return len(self._items)

    @property
    def first(self):
        return self._sc2_first if self._sc2_first is not None else self._items[0]

    def closest_to(self, position):
        return min(
            self._items,
            key=lambda u: ((u.x - position[0]) ** 2 + (u.y - position[1]) ** 2),
        )


class _Point:
    def __init__(self, x, y):
        self.x = x
        self.y = y

    def distance_to(self, other):
        return ((self.x - other[0]) ** 2 + (self.y - other[1]) ** 2) ** 0.5


class TestHasUnits(unittest.TestCase):
    def test_none(self):
        self.assertFalse(has_units(None))

    def test_empty_sc2_units(self):
        self.assertFalse(has_units(_SC2UnitsLike([])))

    def test_non_empty_sc2_units(self):
        self.assertTrue(has_units(_SC2UnitsLike([1, 2])))

    def test_empty_list_fallback(self):
        self.assertFalse(has_units([]))

    def test_non_empty_list_fallback(self):
        self.assertTrue(has_units([1]))

    def test_unknown_object_returns_false(self):
        self.assertFalse(has_units(object()))


class TestSafeFirst(unittest.TestCase):
    def test_none(self):
        self.assertIsNone(safe_first(None))

    def test_empty(self):
        self.assertIsNone(safe_first([]))

    def test_sc2_units_uses_first_property(self):
        sentinel = object()
        coll = _SC2UnitsLike(["x"], sc2_first=sentinel)
        self.assertIs(safe_first(coll), sentinel)

    def test_list_uses_index_0(self):
        self.assertEqual(safe_first([7, 8, 9]), 7)


class TestSafeClosest(unittest.TestCase):
    def test_none_units(self):
        self.assertIsNone(safe_closest(None, (0, 0)))

    def test_no_position(self):
        self.assertIsNone(safe_closest(_SC2UnitsLike([1]), None))

    def test_uses_sc2_closest_to(self):
        coll = _SC2UnitsLike([_Point(0, 0), _Point(10, 10), _Point(3, 3)])
        result = safe_closest(coll, (4, 4))
        self.assertEqual((result.x, result.y), (3, 3))

    def test_fallback_min_by_distance(self):
        items = [_Point(0, 0), _Point(10, 10), _Point(3, 3)]
        result = safe_closest(items, (4, 4))
        self.assertEqual((result.x, result.y), (3, 3))


class TestSafeAmount(unittest.TestCase):
    def test_none(self):
        self.assertEqual(safe_amount(None), 0)

    def test_empty(self):
        self.assertEqual(safe_amount([]), 0)

    def test_sc2_units_amount(self):
        self.assertEqual(safe_amount(_SC2UnitsLike([1, 2, 3])), 3)

    def test_list_fallback(self):
        self.assertEqual(safe_amount([1, 2]), 2)


class TestClamp(unittest.TestCase):
    def test_within_range(self):
        self.assertEqual(clamp(5, 0, 10), 5)

    def test_below_min(self):
        self.assertEqual(clamp(-3, 0, 10), 0)

    def test_above_max(self):
        self.assertEqual(clamp(99, 0, 10), 10)

    def test_at_boundaries(self):
        self.assertEqual(clamp(0, 0, 10), 0)
        self.assertEqual(clamp(10, 0, 10), 10)


class TestPercentage(unittest.TestCase):
    def test_normal(self):
        self.assertAlmostEqual(percentage(50, 100), 0.5)

    def test_full(self):
        self.assertEqual(percentage(100, 100), 1.0)

    def test_zero_total(self):
        self.assertEqual(percentage(50, 0), 0.0)

    def test_negative_total(self):
        # total <= 0 가드 → 0.0 반환
        self.assertEqual(percentage(50, -1), 0.0)

    def test_over_one_clamped(self):
        # value > total일 때 1.0으로 clamp되는지 (HP 계산 안전망)
        self.assertEqual(percentage(150, 100), 1.0)


if __name__ == "__main__":
    unittest.main()
