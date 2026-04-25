# -*- coding: utf-8 -*-
"""
Unit tests for ``utils.common_helpers``.

The helpers were missing before this regression — combat_manager imported
``centroid``/``units_amount``/``filter_by_type``/``closest_enemy`` and
silently fell back to inline implementations because the imports raised.
These tests pin the expected behaviour so the fallback path stays
exercised correctly and a future deletion is caught.
"""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT / "wicked_zerg_challenger"))

from utils.common_helpers import (  # noqa: E402
    centroid,
    closest_enemy,
    filter_by_type,
    has_units,
    safe_amount,
    safe_closest,
    safe_first,
    units_amount,
)


class _FakeTypeId:
    def __init__(self, name: str) -> None:
        self.name = name

    def __eq__(self, other) -> bool:
        return isinstance(other, _FakeTypeId) and self.name == other.name

    def __hash__(self) -> int:
        return hash(self.name)


class _FakePosition:
    def __init__(self, x: float, y: float) -> None:
        self.x = float(x)
        self.y = float(y)

    def distance_to(self, other) -> float:
        return ((self.x - other.x) ** 2 + (self.y - other.y) ** 2) ** 0.5


class _FakeUnit:
    def __init__(self, type_name: str, x: float = 0.0, y: float = 0.0) -> None:
        self.type_id = _FakeTypeId(type_name)
        self.position = _FakePosition(x, y)

    def distance_to(self, other) -> float:
        # Mirror burnysc2 Unit.distance_to which accepts both units and points.
        target_pos = getattr(other, "position", other)
        return self.position.distance_to(target_pos)


@pytest.fixture
def fake_units():
    return [
        _FakeUnit("ZERGLING", 0, 0),
        _FakeUnit("ZERGLING", 1, 0),
        _FakeUnit("MUTALISK", 5, 5),
    ]


class TestHasUnits:
    def test_empty_list_is_false(self):
        assert has_units([]) is False

    def test_none_is_false(self):
        assert has_units(None) is False

    def test_populated_list_is_true(self, fake_units):
        assert has_units(fake_units) is True


class TestSafeAmount:
    def test_empty(self):
        assert safe_amount([]) == 0
        assert units_amount([]) == 0

    def test_list(self, fake_units):
        assert safe_amount(fake_units) == 3
        assert units_amount(fake_units) == 3


class TestSafeFirst:
    def test_empty_returns_none(self):
        assert safe_first([]) is None

    def test_returns_first_element(self, fake_units):
        assert safe_first(fake_units) is fake_units[0]


class TestSafeClosest:
    def test_returns_closest_unit(self, fake_units):
        target = _FakePosition(0.1, 0.0)
        assert safe_closest(fake_units, target) is fake_units[0]

    def test_empty_returns_none(self):
        assert safe_closest([], _FakePosition(0, 0)) is None


class TestClosestEnemy:
    def test_returns_closest(self, fake_units):
        ref = _FakeUnit("OVERLORD", 5.1, 5.0)
        assert closest_enemy(ref, fake_units) is fake_units[2]

    def test_no_unit_returns_none(self, fake_units):
        assert closest_enemy(None, fake_units) is None


class TestCentroid:
    def test_geometric_center(self, fake_units):
        result = centroid(fake_units)
        # Skip if Point2 isn't importable (CI without burnysc2)
        if result is None:
            pytest.skip("Point2 not available in this environment")
        assert pytest.approx(result.x, rel=1e-6) == (0 + 1 + 5) / 3
        assert pytest.approx(result.y, rel=1e-6) == (0 + 0 + 5) / 3

    def test_empty_returns_none(self):
        assert centroid([]) is None


class TestFilterByType:
    def test_single_string_name(self, fake_units):
        result = filter_by_type(fake_units, "ZERGLING")
        assert len(list(result)) == 2

    def test_list_of_string_names_combat_manager_style(self, fake_units):
        # Mirrors combat_manager.py call site:
        # self._filter_units_by_type(air_units, ["MUTALISK", "CORRUPTOR"])
        result = filter_by_type(fake_units, ["MUTALISK", "CORRUPTOR"])
        names = [u.type_id.name for u in result]
        assert names == ["MUTALISK"]

    def test_unit_type_id_object(self, fake_units):
        target = _FakeTypeId("ZERGLING")
        result = filter_by_type(fake_units, target)
        assert all(u.type_id == target for u in result)
        assert len(list(result)) == 2

    def test_none_unit_types_returns_empty(self, fake_units):
        assert filter_by_type(fake_units, None) == []

    def test_empty_units_returns_empty(self):
        assert filter_by_type([], "ZERGLING") == []
