# -*- coding: utf-8 -*-
"""
position_utils 단위 테스트

`sc2.position.Point2` 가 실제로 없어도 동작하도록 간단한 Point2 스텁을
sys.modules에 주입한 뒤 importlib로 로드한다.
"""

import importlib.util
import math
import sys
import types
from pathlib import Path

import pytest

BOT_ROOT = Path(__file__).resolve().parent.parent / "wicked_zerg_challenger"


class _Point2:
    """Minimal Point2 stand-in with tuple constructor and x/y accessors."""

    def __init__(self, xy):
        self.x, self.y = float(xy[0]), float(xy[1])

    def distance_to(self, other):
        return math.hypot(self.x - other.x, self.y - other.y)

    def __eq__(self, other):
        return abs(self.x - other.x) < 1e-9 and abs(self.y - other.y) < 1e-9

    def __repr__(self):
        return f"Point2({self.x}, {self.y})"


def _ensure_sc2_stub():
    """Install lightweight sc2 package stubs so `from sc2.position import Point2` resolves."""
    if "sc2" not in sys.modules:
        sc2 = types.ModuleType("sc2")
        sys.modules["sc2"] = sc2
    if "sc2.position" not in sys.modules:
        position = types.ModuleType("sc2.position")
        position.Point2 = _Point2
        sys.modules["sc2.position"] = position
        sys.modules["sc2"].position = position
    if "sc2.units" not in sys.modules:
        units = types.ModuleType("sc2.units")
        units.Units = list
        sys.modules["sc2.units"] = units
    if "sc2.unit" not in sys.modules:
        unit = types.ModuleType("sc2.unit")
        unit.Unit = object
        sys.modules["sc2.unit"] = unit


@pytest.fixture(scope="module")
def pu_mod():
    _ensure_sc2_stub()
    path = BOT_ROOT / "utils" / "position_utils.py"
    spec = importlib.util.spec_from_file_location("wzc_position_utils", str(path))
    module = importlib.util.module_from_spec(spec)
    sys.modules["wzc_position_utils"] = module
    spec.loader.exec_module(module)
    return module


class _MockPos:
    def __init__(self, x, y):
        self.x = float(x)
        self.y = float(y)

    def distance_to(self, other):
        return math.hypot(self.x - other.x, self.y - other.y)


class _MockUnit:
    def __init__(self, x, y, health=100, supply_cost=2):
        self.position = _MockPos(x, y)
        self.health = health
        self.supply_cost = supply_cost


class TestGetCenterPosition:
    def test_empty_returns_origin(self, pu_mod):
        p = pu_mod.get_center_position([])
        assert (p.x, p.y) == (0, 0)

    def test_single_unit_returns_its_position(self, pu_mod):
        u = _MockUnit(5, 7)
        p = pu_mod.get_center_position([u])
        assert (p.x, p.y) == (5, 7)

    def test_multiple_units_average(self, pu_mod):
        units = [_MockUnit(0, 0), _MockUnit(10, 0), _MockUnit(0, 10)]
        p = pu_mod.get_center_position(units)
        assert p.x == pytest.approx(10 / 3)
        assert p.y == pytest.approx(10 / 3)


class TestGetWeightedCenter:
    def test_health_weighted(self, pu_mod):
        # Heavier unit should pull center toward (10, 0)
        units = [_MockUnit(0, 0, health=10), _MockUnit(10, 0, health=90)]
        p = pu_mod.get_weighted_center(units, weight_by_health=True)
        assert p.x == pytest.approx(9.0)

    def test_supply_weighted(self, pu_mod):
        # Supply-weighted toward the higher-supply unit
        units = [_MockUnit(0, 0, supply_cost=1), _MockUnit(10, 0, supply_cost=4)]
        p = pu_mod.get_weighted_center(units, weight_by_supply=True)
        assert p.x == pytest.approx(8.0)

    def test_zero_total_health_falls_back_to_center(self, pu_mod):
        units = [_MockUnit(0, 0, health=0), _MockUnit(10, 0, health=0)]
        p = pu_mod.get_weighted_center(units, weight_by_health=True)
        assert p.x == pytest.approx(5.0)

    def test_unweighted_defaults_to_geometric(self, pu_mod):
        units = [_MockUnit(0, 0), _MockUnit(4, 0)]
        p = pu_mod.get_weighted_center(units)
        assert p.x == pytest.approx(2.0)


class TestClosestFurthest:
    def test_closest_from_list(self, pu_mod):
        units = [_MockUnit(0, 0), _MockUnit(5, 0), _MockUnit(10, 0)]
        closest = pu_mod.get_closest_unit(units, _MockPos(4, 0))
        assert closest.position.x == 5

    def test_closest_empty(self, pu_mod):
        assert pu_mod.get_closest_unit([], _MockPos(0, 0)) is None

    def test_furthest_from_list(self, pu_mod):
        units = [_MockUnit(0, 0), _MockUnit(5, 0), _MockUnit(10, 0)]
        furthest = pu_mod.get_furthest_unit(units, _MockPos(0, 0))
        assert furthest.position.x == 10

    def test_furthest_empty(self, pu_mod):
        assert pu_mod.get_furthest_unit([], _MockPos(0, 0)) is None


class TestDistancesAndSpread:
    def test_average_distance(self, pu_mod):
        units = [_MockUnit(0, 0), _MockUnit(2, 0)]
        avg = pu_mod.get_average_distance(units, _MockPos(0, 0))
        assert avg == pytest.approx(1.0)

    def test_average_distance_empty(self, pu_mod):
        assert pu_mod.get_average_distance([], _MockPos(0, 0)) == 0.0

    def test_spread_radius(self, pu_mod):
        units = [_MockUnit(0, 0), _MockUnit(10, 0), _MockUnit(0, 10)]
        spread = pu_mod.get_spread_radius(units)
        # Max distance from geometric center (10/3, 10/3)
        cx, cy = 10 / 3, 10 / 3
        expected = max(
            math.hypot(0 - cx, 0 - cy),
            math.hypot(10 - cx, 0 - cy),
            math.hypot(0 - cx, 10 - cy),
        )
        assert spread == pytest.approx(expected)

    def test_spread_single_unit_zero(self, pu_mod):
        assert pu_mod.get_spread_radius([_MockUnit(0, 0)]) == 0.0

    def test_spread_empty_zero(self, pu_mod):
        assert pu_mod.get_spread_radius([]) == 0.0


class TestIsPositionSafe:
    def test_no_enemies_safe(self, pu_mod):
        assert pu_mod.is_position_safe(_MockPos(0, 0), [], safe_distance=10) is True

    def test_enemies_far_safe(self, pu_mod):
        assert (
            pu_mod.is_position_safe(_MockPos(0, 0), [_MockUnit(100, 100)], safe_distance=10)
            is True
        )

    def test_enemies_near_unsafe(self, pu_mod):
        assert (
            pu_mod.is_position_safe(_MockPos(0, 0), [_MockUnit(3, 0)], safe_distance=10)
            is False
        )


class TestPerimeterInterpolateClamp:
    def test_perimeter_count(self, pu_mod):
        positions = pu_mod.get_perimeter_positions(_MockPos(0, 0), radius=5, count=8)
        assert len(positions) == 8
        # All points should be at distance ~5 from center
        for p in positions:
            assert math.hypot(p.x, p.y) == pytest.approx(5.0)

    def test_interpolate_endpoints(self, pu_mod):
        start = _MockPos(0, 0)
        end = _MockPos(10, 20)
        p0 = pu_mod.interpolate_position(start, end, 0.0)
        p1 = pu_mod.interpolate_position(start, end, 1.0)
        p_mid = pu_mod.interpolate_position(start, end, 0.5)
        assert (p0.x, p0.y) == (0, 0)
        assert (p1.x, p1.y) == (10, 20)
        assert (p_mid.x, p_mid.y) == (5, 10)

    def test_clamp_inside(self, pu_mod):
        p = pu_mod.clamp_position(_MockPos(5, 5), 0, 10, 0, 10)
        assert (p.x, p.y) == (5, 5)

    def test_clamp_below(self, pu_mod):
        p = pu_mod.clamp_position(_MockPos(-1, -1), 0, 10, 0, 10)
        assert (p.x, p.y) == (0, 0)

    def test_clamp_above(self, pu_mod):
        p = pu_mod.clamp_position(_MockPos(100, 100), 0, 10, 0, 10)
        assert (p.x, p.y) == (10, 10)


class TestBoundingBox:
    def test_bbox_multiple(self, pu_mod):
        units = [_MockUnit(0, 0), _MockUnit(5, 10), _MockUnit(-3, 2)]
        lo, hi = pu_mod.get_bounding_box(units)
        assert (lo.x, lo.y) == (-3, 0)
        assert (hi.x, hi.y) == (5, 10)

    def test_bbox_empty(self, pu_mod):
        lo, hi = pu_mod.get_bounding_box([])
        assert (lo.x, lo.y) == (0, 0)
        assert (hi.x, hi.y) == (0, 0)
