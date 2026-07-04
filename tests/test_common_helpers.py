# -*- coding: utf-8 -*-
"""
Regression tests for wicked_zerg_challenger.utils.common_helpers

These lock in the exact function names/signatures that combat_manager.py
imports as a tuple (`from utils.common_helpers import centroid,
closest_enemy, filter_by_type, has_units, units_amount`). A single missing
name makes that import fail and silently disables the whole
HELPERS_AVAILABLE fast-path in combat_manager.py without any test failure
elsewhere -- these tests exist so that regression is caught here instead.
"""

import os
import sys

sys.path.insert(
    0, os.path.join(os.path.dirname(__file__), "..", "wicked_zerg_challenger")
)

from utils.common_helpers import (  # noqa: E402
    centroid,
    closest_enemy,
    filter_by_type,
    has_units,
    units_amount,
)


class FakeUnit:
    def __init__(self, x, y, type_name="ZERGLING"):
        self.position = FakePoint(x, y)
        self.type_id = type("T", (), {"name": type_name})()

    def distance_to(self, other):
        ox, oy = other.position.x, other.position.y
        return ((self.position.x - ox) ** 2 + (self.position.y - oy) ** 2) ** 0.5


class FakePoint:
    def __init__(self, x, y):
        self.x = x
        self.y = y


class TestUnitsAmount:
    def test_counts_list(self):
        assert units_amount([FakeUnit(0, 0), FakeUnit(1, 1)]) == 2

    def test_none_is_zero(self):
        assert units_amount(None) == 0

    def test_empty_list_is_zero(self):
        assert units_amount([]) == 0


class TestFilterByType:
    def test_filters_matching_names(self):
        units = [FakeUnit(0, 0, "ZERGLING"), FakeUnit(1, 1, "ROACH")]
        result = filter_by_type(units, {"ZERGLING"})
        assert len(result) == 1
        assert result[0].type_id.name == "ZERGLING"

    def test_no_match_returns_empty(self):
        units = [FakeUnit(0, 0, "ZERGLING")]
        assert filter_by_type(units, {"ROACH"}) == []


class TestClosestEnemy:
    def test_returns_nearest(self):
        unit = FakeUnit(0, 0)
        far = FakeUnit(100, 100)
        near = FakeUnit(1, 0)
        result = closest_enemy(unit, [far, near])
        assert result is near

    def test_empty_returns_none(self):
        assert closest_enemy(FakeUnit(0, 0), []) is None


class TestHasUnits:
    def test_nonempty_list_true(self):
        assert has_units([FakeUnit(0, 0)]) is True

    def test_empty_list_false(self):
        assert has_units([]) is False

    def test_none_false(self):
        assert has_units(None) is False


class TestCentroid:
    def test_empty_returns_none(self):
        assert centroid([]) is None
        assert centroid(None) is None

    def test_single_unit_is_its_own_position(self):
        try:
            result = centroid([FakeUnit(5, 7)])
        except ModuleNotFoundError:
            import pytest

            pytest.skip("sc2 library not available")
        assert result.x == 5
        assert result.y == 7

    def test_average_of_two_units(self):
        try:
            result = centroid([FakeUnit(0, 0), FakeUnit(10, 0)])
        except ModuleNotFoundError:
            import pytest

            pytest.skip("sc2 library not available")
        assert result.x == 5
        assert result.y == 0
