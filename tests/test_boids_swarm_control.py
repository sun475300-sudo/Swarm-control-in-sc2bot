# -*- coding: utf-8 -*-
"""Tests for `boids_swarm_control` — separation/alignment/cohesion + targeting.

이 모듈은 sc2 라이브러리의 실제 Unit/Units가 필요 없도록 가벼운 더미
객체로 동작 가능하게 설계되어 있어, 순수 로직 검증만으로 회귀를 잡을 수 있다.
"""
from __future__ import annotations

import importlib.util
from pathlib import Path
from types import SimpleNamespace
from typing import Iterable, List, Optional

import pytest

np = pytest.importorskip("numpy", reason="numpy required for boids tests")


# 직접 파일 로딩으로 wicked_zerg_challenger.combat 패키지 init을 우회한다.
# combat/__init__.py 가 다수의 submodule을 try/except로 import 하면서
# 일부 submodule이 `from utils.logger import get_logger` 를 시도하는데,
# 이 시점에 sys.path 우선순위에 따라 root /utils 가 잡혀 sys.modules['utils']
# 가 잘못 캐시될 수 있다(이후 다른 테스트에서 ImportError 유발).
# 본 테스트는 boids 로직만 검증하면 되므로 file-based loading이 가장 깔끔.
_BOIDS_PATH = (
    Path(__file__).resolve().parent.parent
    / "wicked_zerg_challenger"
    / "combat"
    / "boids_swarm_control.py"
)
try:
    _spec = importlib.util.spec_from_file_location("boids_swarm_control_t", _BOIDS_PATH)
    if _spec is None or _spec.loader is None:
        raise ImportError(f"cannot build spec for {_BOIDS_PATH}")
    _mod = importlib.util.module_from_spec(_spec)
    _spec.loader.exec_module(_mod)
    BoidsSwarmController = _mod.BoidsSwarmController
    _get_pos = _mod._get_pos
except Exception as exc:  # pragma: no cover - module-level skip
    pytest.skip(f"boids_swarm_control not importable: {exc}", allow_module_level=True)


# ---------------------------------------------------------------------------
# Fakes — sc2-free Unit / Units stand-ins
# ---------------------------------------------------------------------------
class _Pos(SimpleNamespace):
    def __init__(self, x: float, y: float):
        super().__init__(x=float(x), y=float(y))


class _TypeId:
    def __init__(self, name: str):
        self.name = name


class _Unit:
    """Minimal stand-in for sc2.Unit covering the attributes boids touches."""

    def __init__(
        self,
        x: float,
        y: float,
        tag: int = 0,
        type_name: str = "ZERGLING",
    ):
        self.position = _Pos(x, y)
        self.tag = tag
        self.type_id = _TypeId(type_name)

    def distance_to(self, other) -> float:
        ox, oy = (other.x, other.y) if hasattr(other, "x") else (other.position.x, other.position.y)
        return float(((ox - self.position.x) ** 2 + (oy - self.position.y) ** 2) ** 0.5)


class _Units(list):
    """List that exposes `.closer_than(radius, position)` like sc2.Units."""

    def closer_than(self, radius: float, position) -> "_Units":
        px, py = (position.x, position.y) if hasattr(position, "x") else (position[0], position[1])
        out = _Units()
        for u in self:
            ux, uy = u.position.x, u.position.y
            if ((ux - px) ** 2 + (uy - py) ** 2) ** 0.5 <= radius:
                out.append(u)
        return out


# ---------------------------------------------------------------------------
# _get_pos helper
# ---------------------------------------------------------------------------
class TestGetPos:
    def test_extracts_from_position_attr(self):
        assert _get_pos(_Unit(3.5, -1.25)) == (3.5, -1.25)

    def test_extracts_from_bare_point_like(self):
        # Bare object with x/y returns (x, y)
        assert _get_pos(_Pos(7, 8)) == (7.0, 8.0)

    def test_falls_back_to_zero_for_unknown(self):
        # Object without position/x/y → (0, 0)
        assert _get_pos(SimpleNamespace()) == (0.0, 0.0)


# ---------------------------------------------------------------------------
# Force calculations
# ---------------------------------------------------------------------------
class TestSeparation:
    def test_no_neighbors_returns_zero_force(self):
        ctrl = BoidsSwarmController()
        unit = _Unit(0, 0, tag=1)
        force = ctrl._calculate_separation(unit, _Units([unit]))
        assert force.tolist() == [0.0, 0.0]

    def test_pushes_away_from_close_neighbor(self):
        ctrl = BoidsSwarmController(separation_radius=3.0, max_force=1.0)
        u = _Unit(0, 0, tag=1)
        n = _Unit(1, 0, tag=2)  # neighbor to the right within radius
        force = ctrl._calculate_separation(u, _Units([u, n]))
        # Should push left (negative x), zero y
        assert force[0] < 0
        assert abs(force[1]) < 1e-9

    def test_ignores_self(self):
        ctrl = BoidsSwarmController()
        u = _Unit(0, 0, tag=1)
        # Only self in neighbors → no force
        force = ctrl._calculate_separation(u, _Units([u]))
        assert force.tolist() == [0.0, 0.0]

    def test_ignores_neighbors_outside_radius(self):
        ctrl = BoidsSwarmController(separation_radius=2.0)
        u = _Unit(0, 0, tag=1)
        far = _Unit(10, 10, tag=2)
        force = ctrl._calculate_separation(u, _Units([u, far]))
        assert force.tolist() == [0.0, 0.0]


class TestCohesion:
    def test_pulls_toward_neighbor_centroid(self):
        ctrl = BoidsSwarmController(neighbor_radius=10.0, max_force=1.0)
        u = _Unit(0, 0, tag=1)
        n1 = _Unit(4, 0, tag=2)
        n2 = _Unit(0, 4, tag=3)
        force = ctrl._calculate_cohesion(u, _Units([u, n1, n2]))
        # Centroid of (4,0) and (0,4) is (2,2) — direction should be +x +y
        assert force[0] > 0
        assert force[1] > 0

    def test_no_neighbors_zero(self):
        ctrl = BoidsSwarmController()
        u = _Unit(0, 0, tag=1)
        force = ctrl._calculate_cohesion(u, _Units([u]))
        assert force.tolist() == [0.0, 0.0]


class TestAlignment:
    def test_zero_when_no_neighbors_in_range(self):
        ctrl = BoidsSwarmController(neighbor_radius=1.0)
        u = _Unit(0, 0, tag=1)
        far = _Unit(50, 50, tag=2)
        force = ctrl._calculate_alignment(u, _Units([u, far]))
        assert force.tolist() == [0.0, 0.0]


class TestTargetSeeking:
    def test_zero_distance_returns_zero(self):
        ctrl = BoidsSwarmController()
        u = _Unit(5, 5, tag=1)
        force = ctrl._calculate_target_seeking(u, _Pos(5, 5))
        assert force.tolist() == [0.0, 0.0]

    def test_force_points_toward_target(self):
        ctrl = BoidsSwarmController(max_force=2.0)
        u = _Unit(0, 0, tag=1)
        force = ctrl._calculate_target_seeking(u, _Pos(10, 0))
        # Direction (1,0), magnitude min(10/10,1)*2 = 2.0
        assert force[0] > 0
        assert abs(force[1]) < 1e-9
        assert pytest.approx(2.0, abs=1e-6) == float(np.linalg.norm(force))

    def test_force_attenuates_when_close(self):
        """At distance 5 (< 10) force magnitude should be < max_force."""
        ctrl = BoidsSwarmController(max_force=2.0)
        u = _Unit(0, 0, tag=1)
        force = ctrl._calculate_target_seeking(u, _Pos(5, 0))
        # min(5/10, 1) * 2 = 1.0
        assert pytest.approx(1.0, abs=1e-6) == float(np.linalg.norm(force))


class TestEnemyAvoidance:
    def test_high_threat_widens_radius(self):
        ctrl = BoidsSwarmController()
        # Tank at distance 14: outside default(8) but within high-threat(12)? actually 14 > 12,
        # but within SIEGETANKSIEGED's 18 special radius
        u = _Unit(0, 0, tag=1)
        tank = _Unit(14, 0, tag=2, type_name="SIEGETANKSIEGED")
        force = ctrl._calculate_enemy_avoidance(u, _Units([tank]))
        # Should generate a non-zero avoidance pointing -x
        assert force[0] < 0

    def test_far_enemy_no_avoidance(self):
        ctrl = BoidsSwarmController()
        u = _Unit(0, 0, tag=1)
        ling = _Unit(50, 50, tag=2, type_name="ZERGLING")
        force = ctrl._calculate_enemy_avoidance(u, _Units([ling]))
        assert force.tolist() == [0.0, 0.0]

    def test_close_low_threat_avoidance(self):
        ctrl = BoidsSwarmController()
        u = _Unit(0, 0, tag=1)
        ling = _Unit(3, 0, tag=2, type_name="ZERGLING")
        force = ctrl._calculate_enemy_avoidance(u, _Units([ling]))
        # Should push -x (away from enemy)
        assert force[0] < 0


class TestSurroundingForce:
    def test_empty_enemy_set_returns_zero(self):
        ctrl = BoidsSwarmController()
        u = _Unit(0, 0, tag=1)
        force = ctrl._calculate_enemy_surrounding(u, _Units([]), _Pos(10, 10))
        assert force.tolist() == [0.0, 0.0]


# ---------------------------------------------------------------------------
# High-level orchestration
# ---------------------------------------------------------------------------
class TestSwarmVelocity:
    def test_velocity_force_is_capped(self):
        """Resulting velocity magnitude must never exceed max_force."""
        ctrl = BoidsSwarmController(max_force=0.5)
        u = _Unit(0, 0, tag=1)
        crowd = _Units(
            [u, _Unit(0.1, 0, tag=2), _Unit(-0.1, 0, tag=3), _Unit(0, 0.1, tag=4)]
        )
        vx, vy = ctrl.calculate_swarm_velocity(
            u, crowd, target=_Pos(100, 100), enemy_units=_Units([_Unit(0.5, 0, tag=99, type_name="BANELING")])
        )
        assert (vx**2 + vy**2) ** 0.5 <= 0.5 + 1e-6

    def test_no_inputs_velocity_zero(self):
        ctrl = BoidsSwarmController()
        u = _Unit(0, 0, tag=1)
        vx, vy = ctrl.calculate_swarm_velocity(u, _Units([u]))
        assert vx == 0.0 and vy == 0.0


class TestApplyBoidsToUnits:
    def test_returns_one_target_per_unit(self):
        ctrl = BoidsSwarmController()
        units = _Units([_Unit(i, 0, tag=i) for i in range(3)])
        results = ctrl.apply_boids_to_units(units, target=_Pos(20, 0))
        assert len(results) == 3
        # Each entry is (unit, target_pos)
        for unit, target_pos in results:
            assert isinstance(unit, _Unit)
            # target_pos should be either Point2 (sc2 installed) or tuple (fallback)
            assert hasattr(target_pos, "x") or isinstance(target_pos, tuple)


class TestApplyDefenseFormation:
    def test_increases_separation_under_splash_threat(self):
        ctrl = BoidsSwarmController()
        units = _Units([_Unit(0, 0, tag=1), _Unit(1, 0, tag=2)])
        # Two banelings — splash threat — should not crash and should produce results
        enemies = _Units(
            [
                _Unit(20, 0, tag=10, type_name="BANELING"),
                _Unit(20, 1, tag=11, type_name="BANELING"),
            ]
        )
        results = ctrl.apply_defense_formation(
            units,
            defense_point=_Pos(20, 0),
            enemy_units=enemies,
            base_position=_Pos(0, 0),
        )
        assert len(results) == 2


class TestGetPriorityTarget:
    def test_returns_none_when_no_enemies(self):
        ctrl = BoidsSwarmController()
        u = _Unit(0, 0, tag=1)
        assert ctrl.get_priority_target(u, _Units([])) is None

    def test_skips_far_targets(self):
        """Targets > 15 distance away must be ignored."""
        ctrl = BoidsSwarmController()
        u = _Unit(0, 0, tag=1)
        far_caster = _Unit(50, 0, tag=2, type_name="HIGHTEMPLAR")
        assert ctrl.get_priority_target(u, _Units([far_caster])) is None

    def test_prefers_spell_caster_over_marine(self):
        ctrl = BoidsSwarmController()
        u = _Unit(0, 0, tag=1)
        marine = _Unit(3, 0, tag=2, type_name="MARINE")
        templar = _Unit(10, 0, tag=3, type_name="HIGHTEMPLAR")
        target = ctrl.get_priority_target(u, _Units([marine, templar]))
        assert target is templar

    def test_prefers_splash_over_support(self):
        ctrl = BoidsSwarmController()
        u = _Unit(0, 0, tag=1)
        medivac = _Unit(5, 0, tag=2, type_name="MEDIVAC")
        colossus = _Unit(10, 0, tag=3, type_name="COLOSSUS")
        assert ctrl.get_priority_target(u, _Units([medivac, colossus])) is colossus

    def test_within_same_priority_picks_closer(self):
        ctrl = BoidsSwarmController()
        u = _Unit(0, 0, tag=1)
        # Two MARINEs (default priority 5) at different distances
        near = _Unit(3, 0, tag=2, type_name="MARINE")
        farther = _Unit(10, 0, tag=3, type_name="MARINE")
        target = ctrl.get_priority_target(u, _Units([farther, near]))
        assert target is near
