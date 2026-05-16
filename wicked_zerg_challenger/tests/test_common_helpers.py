# -*- coding: utf-8 -*-
"""
utils/common_helpers.py 유틸리티 함수 단위 테스트.
"""

import os
import sys
import unittest
from unittest.mock import MagicMock

os.environ.setdefault("PROTOCOL_BUFFERS_PYTHON_IMPLEMENTATION", "python")
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from utils.common_helpers import (
    clamp,
    has_units,
    percentage,
    safe_amount,
    safe_closest,
    safe_first,
)


class TestHasUnits(unittest.TestCase):
    def test_none_returns_false(self):
        self.assertFalse(has_units(None))

    def test_empty_list_returns_false(self):
        self.assertFalse(has_units([]))

    def test_non_empty_list_returns_true(self):
        self.assertTrue(has_units([1, 2, 3]))

    def test_sc2_units_collection_with_exists_attr(self):
        units = MagicMock()
        units.exists = True
        self.assertTrue(has_units(units))

    def test_sc2_units_collection_empty(self):
        units = MagicMock()
        units.exists = False
        self.assertFalse(has_units(units))

    def test_no_len_no_exists_returns_false(self):
        """has_units 는 __len__ 도 exists 도 없는 객체에 대해 False"""

        class _NoLen:
            pass

        self.assertFalse(has_units(_NoLen()))


class TestSafeFirst(unittest.TestCase):
    def test_returns_none_for_empty(self):
        self.assertIsNone(safe_first([]))

    def test_returns_none_for_none(self):
        self.assertIsNone(safe_first(None))

    def test_returns_first_element(self):
        self.assertEqual(safe_first([10, 20, 30]), 10)

    def test_sc2_first_attribute_preferred(self):
        units = MagicMock()
        units.exists = True
        units.first = "first_unit"
        self.assertEqual(safe_first(units), "first_unit")


class TestSafeClosest(unittest.TestCase):
    def test_returns_none_for_empty_units(self):
        self.assertIsNone(safe_closest([], (5, 5)))

    def test_returns_none_for_none_position(self):
        units = [MagicMock()]
        self.assertIsNone(safe_closest(units, None))

    def test_uses_closest_to_when_available(self):
        units = MagicMock()
        units.exists = True
        units.closest_to.return_value = "closest"
        position = (0, 0)
        self.assertEqual(safe_closest(units, position), "closest")
        units.closest_to.assert_called_once_with(position)

    def test_fallback_to_min_distance(self):
        """closest_to가 없으면 distance_to 기반으로 fallback"""

        class _U:
            def __init__(self, name, distance):
                self.name = name
                self._distance = distance

            def distance_to(self, _pos):
                return self._distance

        units = [_U("a", 10), _U("b", 5), _U("c", 8)]
        result = safe_closest(units, "anywhere")
        self.assertEqual(result.name, "b")


class TestSafeAmount(unittest.TestCase):
    def test_none_returns_zero(self):
        self.assertEqual(safe_amount(None), 0)

    def test_empty_returns_zero(self):
        self.assertEqual(safe_amount([]), 0)

    def test_uses_amount_attribute(self):
        units = MagicMock()
        units.exists = True
        units.amount = 42
        self.assertEqual(safe_amount(units), 42)

    def test_falls_back_to_len(self):
        self.assertEqual(safe_amount([1, 2, 3, 4]), 4)


class TestClamp(unittest.TestCase):
    def test_within_range(self):
        self.assertEqual(clamp(5, 0, 10), 5)

    def test_below_min(self):
        self.assertEqual(clamp(-5, 0, 10), 0)

    def test_above_max(self):
        self.assertEqual(clamp(15, 0, 10), 10)

    def test_exact_min(self):
        self.assertEqual(clamp(0, 0, 10), 0)

    def test_exact_max(self):
        self.assertEqual(clamp(10, 0, 10), 10)

    def test_inverted_range_behaviour(self):
        """min>max인 경우 동작: max를 반환 (min(value, max_value) 결과)"""
        # clamp(5, 10, 0) → max(10, min(5,0)) = max(10, 0) = 10
        self.assertEqual(clamp(5, 10, 0), 10)


class TestPercentage(unittest.TestCase):
    def test_normal_ratio(self):
        self.assertAlmostEqual(percentage(50, 100), 0.5)

    def test_total_zero_returns_zero(self):
        self.assertEqual(percentage(50, 0), 0.0)

    def test_total_negative_returns_zero(self):
        self.assertEqual(percentage(50, -10), 0.0)

    def test_overflow_clamped_to_one(self):
        self.assertEqual(percentage(150, 100), 1.0)

    def test_negative_value_clamped_to_zero(self):
        self.assertEqual(percentage(-10, 100), 0.0)


if __name__ == "__main__":
    unittest.main()
