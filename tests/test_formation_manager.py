# -*- coding: utf-8 -*-
"""Tests for `formation_manager.FormationManager` — focuses on pure helpers
that don't require Point2 vector arithmetic. sc2 미설치 환경에서도 통과한다.
"""
from __future__ import annotations

import importlib.util
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import MagicMock

import pytest


_FM_PATH = (
    Path(__file__).resolve().parent.parent
    / "wicked_zerg_challenger"
    / "combat"
    / "formation_manager.py"
)
try:
    _spec = importlib.util.spec_from_file_location("formation_manager_t", _FM_PATH)
    if _spec is None or _spec.loader is None:
        raise ImportError(f"cannot build spec for {_FM_PATH}")
    _mod = importlib.util.module_from_spec(_spec)
    _spec.loader.exec_module(_mod)
    FormationManager = _mod.FormationManager
except Exception as exc:  # pragma: no cover
    pytest.skip(f"formation_manager not importable: {exc}", allow_module_level=True)


# ---------------------------------------------------------------------------
# Test fakes
# ---------------------------------------------------------------------------
class _Pos:
    def __init__(self, x: float, y: float):
        self.x = float(x)
        self.y = float(y)

    def distance_to(self, other) -> float:
        return ((other.x - self.x) ** 2 + (other.y - self.y) ** 2) ** 0.5

    def towards(self, other, distance: float) -> "_Pos":
        d = self.distance_to(other) or 1.0
        ux = (other.x - self.x) / d
        uy = (other.y - self.y) / d
        return _Pos(self.x + ux * distance, self.y + uy * distance)


class _Unit:
    def __init__(self, x: float, y: float):
        self.position = _Pos(x, y)


class _Units(list):
    @property
    def exists(self) -> bool:
        return len(self) > 0

    @property
    def center(self) -> _Pos:
        if not self:
            return _Pos(0, 0)
        return _Pos(
            sum(u.position.x for u in self) / len(self),
            sum(u.position.y for u in self) / len(self),
        )


# ---------------------------------------------------------------------------
# _check_exists static helper
# ---------------------------------------------------------------------------
class TestCheckExists:
    def test_returns_true_for_units_with_exists_true(self):
        units = MagicMock()
        units.exists = True
        assert FormationManager._check_exists(units) is True

    def test_returns_false_for_units_with_exists_false(self):
        units = MagicMock()
        units.exists = False
        assert FormationManager._check_exists(units) is False

    def test_returns_true_for_nonempty_list(self):
        assert FormationManager._check_exists([1, 2, 3]) is True

    def test_returns_false_for_empty_list(self):
        assert FormationManager._check_exists([]) is False


# ---------------------------------------------------------------------------
# Construction
# ---------------------------------------------------------------------------
class TestInit:
    def test_ranged_and_melee_sets_populated(self):
        bot = MagicMock()
        fm = FormationManager(bot)
        # 핵심 종족 유닛이 양 집합에 들어 있어야 한다
        assert len(fm.ranged_units) >= 5
        assert len(fm.melee_units) >= 3
        # 교집합은 비어야 한다
        assert fm.ranged_units & fm.melee_units == set()


# ---------------------------------------------------------------------------
# find_chokepoint
# ---------------------------------------------------------------------------
class TestFindChokepoint:
    def test_returns_none_when_no_enemies(self):
        bot = MagicMock()
        fm = FormationManager(bot)
        result = fm.find_chokepoint(_Units([]), _Pos(0, 0))
        assert result is None

    def test_chokepoint_is_between_base_and_enemy_center(self):
        bot = MagicMock()
        fm = FormationManager(bot)
        enemies = _Units([_Unit(20, 0), _Unit(20, 4)])  # center (20, 2)
        our_base = _Pos(0, 0)
        cp = fm.find_chokepoint(enemies, our_base)
        # towards(enemy_center, 15.0): direction (20, 2) normalized → ~(0.995, 0.0995)
        # cp.x ≈ 14.93, cp.y ≈ 1.49
        assert 0 < cp.x < 20
        assert 0 < cp.y < 2


# ---------------------------------------------------------------------------
# should_avoid_choke
# ---------------------------------------------------------------------------
class TestShouldAvoidChoke:
    def test_returns_false_when_no_units(self):
        bot = MagicMock()
        fm = FormationManager(bot)
        assert fm.should_avoid_choke(_Units([]), _Units([_Unit(0, 0)])) is False

    def test_returns_false_when_no_enemies(self):
        bot = MagicMock()
        fm = FormationManager(bot)
        assert fm.should_avoid_choke(_Units([_Unit(0, 0)]), _Units([])) is False

    def test_returns_false_when_we_outnumber_enemy(self):
        bot = MagicMock()
        fm = FormationManager(bot)
        ours = _Units([_Unit(0, 0)] * 10)
        enemies = _Units([_Unit(5, 5)] * 3)
        assert fm.should_avoid_choke(ours, enemies) is False


class TestShouldAvoidChokepointAlias:
    def test_aliases_to_should_avoid_choke(self):
        bot = MagicMock()
        fm = FormationManager(bot)
        ours = _Units([_Unit(0, 0)])
        enemies = _Units([])
        # Alias → False (no enemies)
        assert fm.should_avoid_chokepoint(ours, _Pos(5, 5), enemies) is False


# ---------------------------------------------------------------------------
# get_retreat_position
# ---------------------------------------------------------------------------
class TestGetRetreatPosition:
    def test_retreats_to_our_base(self):
        bot = MagicMock()
        fm = FormationManager(bot)
        our_base = _Pos(7, 9)
        result = fm.get_retreat_position(_Units([]), _Units([]), our_base)
        assert result is our_base
