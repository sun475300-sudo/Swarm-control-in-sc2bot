# -*- coding: utf-8 -*-
"""
unit_helpers 단위 테스트

sc2 미설치 환경에서도 테스트할 수 있도록 sys.modules에 sc2 스텁을
주입하고 importlib 로 파일 경로에서 모듈을 로드한다.
"""

import importlib.util
import sys
import types
from pathlib import Path

import pytest

BOT_ROOT = Path(__file__).resolve().parent.parent / "wicked_zerg_challenger"


class _UnitsStub(list):
    """Minimal Units stand-in: acts like list, supports closer_than/filter."""

    def __init__(self, items, _bot=None):
        super().__init__(items)

    def closer_than(self, distance, target):
        return _UnitsStub([u for u in self if u.distance_to(target) < distance])

    def filter(self, fn):
        return _UnitsStub([u for u in self if fn(u)])


def _ensure_sc2_stubs():
    if "sc2" not in sys.modules:
        sys.modules["sc2"] = types.ModuleType("sc2")
    mod = sys.modules.get("sc2.unit") or types.ModuleType("sc2.unit")
    mod.Unit = getattr(mod, "Unit", object)
    sys.modules["sc2.unit"] = mod
    # Units stub must accept 2-arg constructor (items, bot) — override even if cached
    mod = sys.modules.get("sc2.units") or types.ModuleType("sc2.units")
    mod.Units = _UnitsStub
    sys.modules["sc2.units"] = mod
    if "sc2.position" not in sys.modules:
        mod = types.ModuleType("sc2.position")
        mod.Point2 = tuple
        sys.modules["sc2.position"] = mod


@pytest.fixture(scope="module")
def uh_mod():
    _ensure_sc2_stubs()
    # Ensure wicked_zerg_challenger dir is on sys.path so `from utils.logger` resolves
    bot_root_str = str(BOT_ROOT)
    if bot_root_str not in sys.path:
        sys.path.insert(0, bot_root_str)
    path = BOT_ROOT / "utils" / "unit_helpers.py"
    spec = importlib.util.spec_from_file_location("wzc_unit_helpers", str(path))
    module = importlib.util.module_from_spec(spec)
    sys.modules["wzc_unit_helpers"] = module
    spec.loader.exec_module(module)
    return module


class _MockUnit:
    def __init__(
        self,
        type_id="ZERGLING",
        health=100,
        health_max=100,
        shield=0,
        shield_max=0,
        supply_cost=1,
        is_idle=False,
        is_attacking=False,
        ground_range=0.0,
        air_range=0.0,
        x=0,
        y=0,
    ):
        self.type_id = type_id
        self.health = health
        self.health_max = health_max
        self.shield = shield
        self.shield_max = shield_max
        self.supply_cost = supply_cost
        self.is_idle = is_idle
        self.is_attacking = is_attacking
        self.ground_range = ground_range
        self.air_range = air_range
        self.x = x
        self.y = y

    def distance_to(self, other):
        return ((self.x - other.x) ** 2 + (self.y - other.y) ** 2) ** 0.5

    def can_attack(self, target):
        return True


class TestFindNearbyEnemies:
    def test_no_unit_returns_empty(self, uh_mod):
        result = uh_mod.find_nearby_enemies(None, _UnitsStub([]), 10)
        assert len(list(result)) == 0

    def test_no_enemies_returns_empty(self, uh_mod):
        u = _MockUnit()
        result = uh_mod.find_nearby_enemies(u, _UnitsStub([]), 10)
        assert len(list(result)) == 0

    def test_filter_by_distance(self, uh_mod):
        unit = _MockUnit(x=0, y=0)
        enemies = _UnitsStub([
            _MockUnit(type_id="E1", x=1, y=0),
            _MockUnit(type_id="E2", x=20, y=0),
            _MockUnit(type_id="E3", x=5, y=0),
        ])
        result = list(uh_mod.find_nearby_enemies(unit, enemies, 10))
        tids = {e.type_id for e in result}
        assert tids == {"E1", "E3"}


class TestHealthShieldRatios:
    def test_health_ratio_full(self, uh_mod):
        assert uh_mod.get_health_ratio(_MockUnit(health=100, health_max=100)) == 1.0

    def test_health_ratio_half(self, uh_mod):
        assert uh_mod.get_health_ratio(_MockUnit(health=50, health_max=100)) == 0.5

    def test_health_ratio_none_unit(self, uh_mod):
        assert uh_mod.get_health_ratio(None) == 0.0

    def test_health_ratio_zero_max(self, uh_mod):
        assert uh_mod.get_health_ratio(_MockUnit(health=0, health_max=0)) == 0.0

    def test_shield_ratio(self, uh_mod):
        assert uh_mod.get_shield_ratio(_MockUnit(shield=80, shield_max=100)) == 0.8

    def test_shield_ratio_no_shield(self, uh_mod):
        # unit without shield_max
        assert uh_mod.get_shield_ratio(_MockUnit(shield=0, shield_max=0)) == 0.0

    def test_shield_ratio_none_unit(self, uh_mod):
        assert uh_mod.get_shield_ratio(None) == 0.0


class TestFilterWorkersByTask:
    def test_empty_workers(self, uh_mod):
        result = uh_mod.filter_workers_by_task(_UnitsStub([]), lambda w: True)
        assert len(list(result)) == 0

    def test_filter_gathering(self, uh_mod):
        workers = _UnitsStub([
            _MockUnit(type_id="W1", is_idle=False),
            _MockUnit(type_id="W2", is_idle=True),
        ])
        result = list(uh_mod.filter_workers_by_task(workers, lambda w: not w.is_idle))
        assert len(result) == 1
        assert result[0].type_id == "W1"


class TestExecuteUnitAction:
    def test_success(self, uh_mod):
        calls = []
        unit = _MockUnit()

        def act():
            calls.append("called")

        assert uh_mod.execute_unit_action(unit, act) is True
        assert calls == ["called"]

    def test_none_unit_returns_false(self, uh_mod):
        assert uh_mod.execute_unit_action(None, lambda: None) is False

    def test_type_error_swallowed(self, uh_mod):
        def fail():
            raise TypeError("bad")

        assert uh_mod.execute_unit_action(_MockUnit(), fail) is False


class TestCalculateUnitSupply:
    def test_empty(self, uh_mod):
        assert uh_mod.calculate_unit_supply(_UnitsStub([])) == 0

    def test_sum_supply(self, uh_mod):
        units = _UnitsStub([
            _MockUnit(supply_cost=1),
            _MockUnit(supply_cost=2),
            _MockUnit(supply_cost=4),
        ])
        assert uh_mod.calculate_unit_supply(units) == 7

    def test_fallback_for_missing_supply_cost(self, uh_mod):
        class Bare:
            pass

        units = _UnitsStub([Bare(), Bare(), Bare()])
        # Each unit without supply_cost defaults to 1
        assert uh_mod.calculate_unit_supply(units) == 3


class TestIdleAndAttacking:
    def test_is_unit_idle_true(self, uh_mod):
        assert uh_mod.is_unit_idle(_MockUnit(is_idle=True)) is True

    def test_is_unit_idle_false(self, uh_mod):
        assert uh_mod.is_unit_idle(_MockUnit(is_idle=False)) is False

    def test_is_unit_idle_none(self, uh_mod):
        assert uh_mod.is_unit_idle(None) is False

    def test_is_unit_attacking(self, uh_mod):
        assert uh_mod.is_unit_attacking(_MockUnit(is_attacking=True)) is True
        assert uh_mod.is_unit_attacking(_MockUnit(is_attacking=False)) is False
        assert uh_mod.is_unit_attacking(None) is False


class TestGetUnitRange:
    def test_ground_range(self, uh_mod):
        assert uh_mod.get_unit_range(_MockUnit(ground_range=5.0)) == 5.0

    def test_none_returns_zero(self, uh_mod):
        assert uh_mod.get_unit_range(None) == 0.0

    def test_air_only(self, uh_mod):
        class AirOnly:
            air_range = 7.0

        # get_unit_range checks ground_range first; if absent, falls back to air_range
        assert uh_mod.get_unit_range(AirOnly()) == 7.0


class TestCanUnitAttack:
    def test_none_unit(self, uh_mod):
        assert uh_mod.can_unit_attack(None, _MockUnit()) is False
        assert uh_mod.can_unit_attack(_MockUnit(), None) is False

    def test_zero_range_cant_attack(self, uh_mod):
        u = _MockUnit(ground_range=0.0)
        t = _MockUnit(x=5, y=0)
        assert uh_mod.can_unit_attack(u, t) is False

    def test_within_range(self, uh_mod):
        u = _MockUnit(ground_range=5.0, x=0, y=0)
        t = _MockUnit(x=3, y=0)
        assert uh_mod.can_unit_attack(u, t) is True

    def test_beyond_range_and_buffer(self, uh_mod):
        u = _MockUnit(ground_range=5.0, x=0, y=0)
        t = _MockUnit(x=20, y=0)
        assert uh_mod.can_unit_attack(u, t) is False
