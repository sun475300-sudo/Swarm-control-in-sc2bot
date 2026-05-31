# -*- coding: utf-8 -*-
"""Tests for `potential_fields.PotentialFieldController` — repulsion model.

sc2 미설치 환경에서도 동작하도록 file-loading + Point2 sentinel patch 사용.
"""
from __future__ import annotations

import importlib.util
from pathlib import Path
from types import SimpleNamespace

import pytest


_PF_PATH = (
    Path(__file__).resolve().parent.parent
    / "wicked_zerg_challenger"
    / "combat"
    / "potential_fields.py"
)
try:
    _spec = importlib.util.spec_from_file_location("potential_fields_t", _PF_PATH)
    if _spec is None or _spec.loader is None:
        raise ImportError(f"cannot build spec for {_PF_PATH}")
    _mod = importlib.util.module_from_spec(_spec)
    _spec.loader.exec_module(_mod)
    PotentialFieldController = _mod.PotentialFieldController
except Exception as exc:  # pragma: no cover
    pytest.skip(f"potential_fields not importable: {exc}", allow_module_level=True)


# Point2 가 None 이면 get_repulsion_vector 가 조기 반환하도록 설계되어 있어,
# 모든 테스트에서 truthy sentinel 로 패치한다.
@pytest.fixture(autouse=True)
def _patch_point2(monkeypatch):
    monkeypatch.setattr(_mod, "Point2", object, raising=False)


# ---------------------------------------------------------------------------
# Fakes
# ---------------------------------------------------------------------------
class _Pos(SimpleNamespace):
    def __init__(self, x: float, y: float):
        super().__init__(x=float(x), y=float(y))

    def distance_to(self, other) -> float:
        ox, oy = (other.x, other.y) if hasattr(other, "x") else (other.position.x, other.position.y)
        return ((ox - self.x) ** 2 + (oy - self.y) ** 2) ** 0.5


class _TypeId:
    def __init__(self, name: str):
        self.name = name


class _Unit:
    def __init__(self, x: float, y: float, type_name: str = "ZERGLING", is_flying: bool = False):
        self.position = _Pos(x, y)
        self.type_id = _TypeId(type_name)
        self.is_flying = is_flying

    def distance_to(self, other) -> float:
        return self.position.distance_to(other.position if hasattr(other, "position") else other)


# ---------------------------------------------------------------------------
# Construction
# ---------------------------------------------------------------------------
class TestInit:
    def test_default_weights(self):
        c = PotentialFieldController()
        assert c.enemy_weight == 1.0
        assert c.structure_weight == 1.4
        assert c.splash_weight == 2.5

    def test_custom_radii_propagate(self):
        c = PotentialFieldController(enemy_radius=10.0, structure_radius=12.0, terrain_radius=4.0)
        assert c.enemy_radius == 10.0
        assert c.structure_radius == 12.0
        assert c.terrain_radius == 4.0


# ---------------------------------------------------------------------------
# get_repulsion_vector
# ---------------------------------------------------------------------------
class TestRepulsionVector:
    def test_no_obstacles_returns_zero(self):
        c = PotentialFieldController()
        u = _Unit(0, 0)
        rx, ry = c.get_repulsion_vector(u, [])
        assert (rx, ry) == (0.0, 0.0)

    def test_enemy_pushes_away(self):
        c = PotentialFieldController()
        u = _Unit(0, 0)
        enemy = _Unit(2, 0, type_name="MARINE")
        rx, ry = c.get_repulsion_vector(u, [enemy])
        # Enemy is east → repulsion should be west (negative x)
        assert rx < 0
        assert abs(ry) < 1e-9

    def test_far_enemy_ignored(self):
        c = PotentialFieldController(enemy_radius=5.0)
        u = _Unit(0, 0)
        far = _Unit(50, 50, type_name="MARINE")
        rx, ry = c.get_repulsion_vector(u, [far])
        assert (rx, ry) == (0.0, 0.0)

    def test_splash_unit_amplifies_repulsion(self):
        """Splash 유닛은 일반 유닛보다 더 강한 repulsion 을 만들어야 한다."""
        c = PotentialFieldController()
        u = _Unit(0, 0)
        marine = _Unit(2, 0, type_name="MARINE")
        widow = _Unit(2, 0, type_name="WIDOWMINE")

        rx_m, _ = c.get_repulsion_vector(u, [marine])
        rx_w, _ = c.get_repulsion_vector(u, [widow])

        # 둘 다 음수, widowmine 의 절댓값이 더 커야 함
        assert rx_m < 0 and rx_w < 0
        assert abs(rx_w) > abs(rx_m)

    def test_structure_repulsion_uses_structure_weight(self):
        c = PotentialFieldController(structure_weight=2.0, enemy_weight=1.0)
        u = _Unit(0, 0)
        struct = _Unit(3, 0)
        rx, ry = c.get_repulsion_vector(u, [], structure_units=[struct])
        assert rx < 0  # pushed away
        assert abs(ry) < 1e-9

    def test_air_unit_ignores_terrain(self):
        c = PotentialFieldController(terrain_radius=10.0, terrain_weight=5.0)
        flyer = _Unit(0, 0, is_flying=True)
        terrain = _Pos(2, 0)
        rx, ry = c.get_repulsion_vector(flyer, [], terrain_points=[terrain])
        # Air unit must not be repelled by terrain
        assert (rx, ry) == (0.0, 0.0)

    def test_ground_unit_repelled_by_terrain(self):
        c = PotentialFieldController(terrain_radius=10.0, terrain_weight=1.0)
        u = _Unit(0, 0, is_flying=False)
        terrain = _Pos(2, 0)
        rx, ry = c.get_repulsion_vector(u, [], terrain_points=[terrain])
        assert rx < 0
        assert abs(ry) < 1e-9

    def test_zero_distance_ignored(self):
        """Overlapping units (dist=0) must not produce NaN/inf."""
        c = PotentialFieldController()
        u = _Unit(0, 0)
        same = _Unit(0, 0, type_name="MARINE")
        rx, ry = c.get_repulsion_vector(u, [same])
        assert (rx, ry) == (0.0, 0.0)


class TestEarlyReturnGuard:
    def test_returns_zero_when_point2_unavailable(self, monkeypatch):
        """Point2 sentinel가 None 이면 (sc2 미설치) 안전한 no-op 반환."""
        monkeypatch.setattr(_mod, "Point2", None, raising=False)
        c = PotentialFieldController()
        u = _Unit(0, 0)
        enemy = _Unit(2, 0, type_name="MARINE")
        # Even with a close enemy, returns zero because Point2 is None
        assert c.get_repulsion_vector(u, [enemy]) == (0.0, 0.0)
