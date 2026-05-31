"""Tests for wicked_zerg_challenger/utils/common_helpers.py."""
from __future__ import annotations

from math import hypot
from types import SimpleNamespace

import pytest

from wicked_zerg_challenger.utils.common_helpers import (
    clamp,
    has_units,
    percentage,
    safe_amount,
    safe_closest,
    safe_first,
)


class _SC2Units:
    """Mimic sc2.units.Units enough for has_units/safe_first/safe_amount."""

    def __init__(self, items):
        self._items = list(items)

    @property
    def exists(self) -> bool:
        return bool(self._items)

    @property
    def amount(self) -> int:
        return len(self._items)

    @property
    def first(self):
        return self._items[0] if self._items else None

    def closest_to(self, position):
        return min(self._items, key=lambda u: u.position.distance_to(position))

    def __iter__(self):
        return iter(self._items)

    def __len__(self):
        return len(self._items)


class P:
    __slots__ = ("x", "y")

    def __init__(self, x, y):
        self.x = float(x)
        self.y = float(y)

    def distance_to(self, other) -> float:
        return hypot(self.x - other.x, self.y - other.y)


def _unit(x, y, tag=1):
    return SimpleNamespace(tag=tag, position=P(x, y), distance_to=P(x, y).distance_to)


# ---------------------------------------------------------------------------
# has_units
# ---------------------------------------------------------------------------

def test_has_units_none():
    assert has_units(None) is False


def test_has_units_sc2_collection_exists_true():
    assert has_units(_SC2Units([_unit(0, 0)])) is True


def test_has_units_sc2_collection_exists_false():
    assert has_units(_SC2Units([])) is False


def test_has_units_python_list_truthy():
    assert has_units([1, 2, 3]) is True


def test_has_units_python_list_empty():
    assert has_units([]) is False


def test_has_units_object_without_len_or_exists():
    """Bare object with neither `.exists` nor `__len__` is treated as empty."""
    assert has_units(object()) is False


# ---------------------------------------------------------------------------
# safe_first
# ---------------------------------------------------------------------------

def test_safe_first_sc2_collection():
    u = _unit(0, 0, tag=42)
    assert safe_first(_SC2Units([u])).tag == 42


def test_safe_first_empty_sc2_collection():
    assert safe_first(_SC2Units([])) is None


def test_safe_first_list():
    assert safe_first([1, 2, 3]) == 1


def test_safe_first_empty_list():
    assert safe_first([]) is None


def test_safe_first_none():
    assert safe_first(None) is None


# ---------------------------------------------------------------------------
# safe_closest
# ---------------------------------------------------------------------------

def test_safe_closest_uses_native_closest_to():
    units = _SC2Units([_unit(0, 0, tag=1), _unit(10, 10, tag=2)])
    target = P(1, 1)
    assert safe_closest(units, target).tag == 1


def test_safe_closest_falls_back_to_min_for_plain_list():
    units = [_unit(0, 0, tag=1), _unit(10, 10, tag=2)]
    target = P(8, 8)
    assert safe_closest(units, target).tag == 2


def test_safe_closest_empty_collection_returns_none():
    assert safe_closest([], P(0, 0)) is None


def test_safe_closest_none_collection_returns_none():
    assert safe_closest(None, P(0, 0)) is None


def test_safe_closest_falsy_position_returns_none():
    """A None position guard prevents passing None into distance_to."""
    units = [_unit(0, 0)]
    assert safe_closest(units, None) is None


def test_safe_closest_units_without_distance_to_returns_none():
    """Broken unit-like objects without distance_to → caught → None."""
    broken = [SimpleNamespace(tag=1)]
    assert safe_closest(broken, P(0, 0)) is None


# ---------------------------------------------------------------------------
# safe_amount
# ---------------------------------------------------------------------------

def test_safe_amount_sc2_collection_uses_amount_property():
    assert safe_amount(_SC2Units([_unit(0, 0), _unit(1, 1)])) == 2


def test_safe_amount_plain_list():
    assert safe_amount([1, 2, 3, 4]) == 4


def test_safe_amount_empty_is_zero():
    assert safe_amount([]) == 0
    assert safe_amount(None) == 0


# ---------------------------------------------------------------------------
# clamp
# ---------------------------------------------------------------------------

def test_clamp_within_range():
    assert clamp(5, 0, 10) == 5


def test_clamp_below_min():
    assert clamp(-5, 0, 10) == 0


def test_clamp_above_max():
    assert clamp(15, 0, 10) == 10


def test_clamp_floats():
    assert clamp(0.7, 0.0, 1.0) == pytest.approx(0.7)
    assert clamp(1.5, 0.0, 1.0) == 1.0
    assert clamp(-0.1, 0.0, 1.0) == 0.0


# ---------------------------------------------------------------------------
# percentage
# ---------------------------------------------------------------------------

def test_percentage_basic():
    assert percentage(50, 200) == pytest.approx(0.25)


def test_percentage_clamps_above_1():
    """A value > total still clamps to 1.0 (e.g. shield overflow)."""
    assert percentage(150, 100) == 1.0


def test_percentage_zero_total_returns_zero():
    assert percentage(50, 0) == 0.0


def test_percentage_negative_total_returns_zero():
    assert percentage(50, -10) == 0.0


def test_percentage_clamps_negative_to_zero():
    """A negative input clamps to 0 (e.g. corrupted health value)."""
    assert percentage(-10, 100) == 0.0
