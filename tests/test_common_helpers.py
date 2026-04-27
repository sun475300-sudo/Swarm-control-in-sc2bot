# -*- coding: utf-8 -*-
"""Tests for common_helpers.py utility functions."""

import sys
import pytest

sys.path.insert(0, "wicked_zerg_challenger")

from utils.common_helpers import (
    has_units,
    safe_first,
    safe_closest,
    safe_amount,
    clamp,
    percentage,
)


class _FakeUnits:
    """Mimics SC2 Units collection with .exists, .amount, .first, and indexing."""

    def __init__(self, items):
        self._items = list(items)

    @property
    def exists(self):
        return len(self._items) > 0

    @property
    def amount(self):
        return len(self._items)

    @property
    def first(self):
        return self._items[0] if self._items else None

    def __len__(self):
        return len(self._items)

    def __iter__(self):
        return iter(self._items)

    def __getitem__(self, idx):
        return self._items[idx]


class TestHasUnits:
    def test_none_returns_false(self):
        assert not has_units(None)

    def test_empty_list_returns_false(self):
        assert not has_units([])

    def test_populated_list_returns_true(self):
        assert has_units([1, 2, 3])

    def test_sc2_units_exists_false(self):
        assert not has_units(_FakeUnits([]))

    def test_sc2_units_exists_true(self):
        assert has_units(_FakeUnits(["unit1"]))


class TestSafeFirst:
    def test_none_returns_none(self):
        assert safe_first(None) is None

    def test_empty_returns_none(self):
        assert safe_first([]) is None

    def test_populated_returns_first(self):
        assert safe_first([10, 20, 30]) == 10

    def test_fake_units_returns_first(self):
        units = _FakeUnits(["a", "b", "c"])
        assert safe_first(units) == "a"


class TestSafeAmount:
    def test_none_returns_zero(self):
        assert safe_amount(None) == 0

    def test_empty_returns_zero(self):
        assert safe_amount([]) == 0

    def test_list_returns_length(self):
        assert safe_amount([1, 2, 3, 4]) == 4

    def test_fake_units_returns_amount(self):
        units = _FakeUnits(["x", "y"])
        assert safe_amount(units) == 2


class TestSafeClosest:
    def test_none_returns_none(self):
        assert safe_closest(None, (0, 0)) is None

    def test_no_position_returns_none(self):
        assert safe_closest([1, 2, 3], None) is None

    def test_empty_returns_none(self):
        assert safe_closest([], (0, 0)) is None


class TestClamp:
    def test_within_range(self):
        assert clamp(5, 0, 10) == 5

    def test_below_min(self):
        assert clamp(-5, 0, 10) == 0

    def test_above_max(self):
        assert clamp(100, 0, 10) == 10

    def test_at_boundary(self):
        assert clamp(0, 0, 10) == 0
        assert clamp(10, 0, 10) == 10

    def test_float_values(self):
        assert clamp(0.5, 0.0, 1.0) == 0.5
        assert clamp(1.5, 0.0, 1.0) == 1.0


class TestPercentage:
    def test_half(self):
        assert percentage(50, 100) == 0.5

    def test_full(self):
        assert percentage(100, 100) == 1.0

    def test_zero_value(self):
        assert percentage(0, 100) == 0.0

    def test_zero_total_returns_zero(self):
        assert percentage(50, 0) == 0.0

    def test_negative_total_returns_zero(self):
        assert percentage(50, -10) == 0.0

    def test_over_clamp(self):
        # Should not exceed 1.0 even if value > total
        assert percentage(200, 100) == 1.0
