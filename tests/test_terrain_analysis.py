# -*- coding: utf-8 -*-
"""Tests for `terrain_analysis.ChokePointDetector` — chokepoint cache,
position queries, cohesion modifier, avoidance vector. sc2-free.
"""
from __future__ import annotations

import importlib.util
from pathlib import Path
from types import SimpleNamespace

import pytest


_TA_PATH = (
    Path(__file__).resolve().parent.parent
    / "wicked_zerg_challenger"
    / "combat"
    / "terrain_analysis.py"
)
try:
    _spec = importlib.util.spec_from_file_location("terrain_analysis_t", _TA_PATH)
    if _spec is None or _spec.loader is None:
        raise ImportError(f"cannot build spec for {_TA_PATH}")
    _mod = importlib.util.module_from_spec(_spec)
    _spec.loader.exec_module(_mod)
    ChokePointDetector = _mod.ChokePointDetector
except Exception as exc:  # pragma: no cover
    pytest.skip(f"terrain_analysis not importable: {exc}", allow_module_level=True)


# Patch Point2 to truthy so get_chokepoint_avoidance_vector doesn't early-return
@pytest.fixture(autouse=True)
def _patch_point2(monkeypatch):
    monkeypatch.setattr(_mod, "Point2", object, raising=False)


# ---------------------------------------------------------------------------
# Fakes
# ---------------------------------------------------------------------------
class _Pos:
    def __init__(self, x: float, y: float):
        self.x = float(x)
        self.y = float(y)

    def distance_to(self, other) -> float:
        return ((other.x - self.x) ** 2 + (other.y - self.y) ** 2) ** 0.5


class _Ramp:
    def __init__(self, top, bottom):
        self.top_center = top
        self.bottom_center = bottom


def _make_bot(ramps=None):
    bot = SimpleNamespace()
    if ramps is not None:
        bot.game_info = SimpleNamespace(map_ramps=ramps)
    return bot


# ---------------------------------------------------------------------------
# update_chokepoints — cache logic
# ---------------------------------------------------------------------------
class TestUpdateChokepoints:
    def test_initial_state_empty(self):
        d = ChokePointDetector(_make_bot(), cache_update_interval=100)
        assert d.chokepoints == []
        # 초기값은 -cache_update_interval (첫 update 가 즉시 캐시 미스가 되도록)
        assert d.chokepoint_cache_frame == -100

    def test_first_update_populates_immediately_at_iter0(self):
        """잠복 버그 회귀 테스트: 첫 호출이 frame=0 이어도 cache miss 로 처리되어야 함."""
        ramps = [_Ramp(_Pos(10, 10), _Pos(15, 10))]
        d = ChokePointDetector(_make_bot(ramps=ramps), cache_update_interval=100)
        d.update_chokepoints(iteration=0)
        assert len(d.chokepoints) == 2

    def test_populates_from_ramps(self):
        # 알려진 quirk: 초기 chokepoint_cache_frame=-1 + cache_update_interval=100
        # 이라 iter < 99 호출은 캐시 갱신을 하지 않음. 100 이후로 호출.
        ramps = [_Ramp(_Pos(10, 10), _Pos(15, 10))]
        d = ChokePointDetector(_make_bot(ramps=ramps))
        d.update_chokepoints(iteration=200)
        # Each ramp contributes top_center + bottom_center
        assert len(d.chokepoints) == 2

    def test_respects_cache_interval(self):
        ramps = [_Ramp(_Pos(0, 0), _Pos(5, 0))]
        d = ChokePointDetector(_make_bot(ramps=ramps), cache_update_interval=100)
        d.update_chokepoints(iteration=0)
        first_count = len(d.chokepoints)
        # Add a ramp; call within cache interval — should NOT re-scan
        ramps.append(_Ramp(_Pos(20, 0), _Pos(25, 0)))
        d.update_chokepoints(iteration=50)
        assert len(d.chokepoints) == first_count

    def test_re_scans_after_interval_expires(self):
        ramps = [_Ramp(_Pos(0, 0), _Pos(5, 0))]
        d = ChokePointDetector(_make_bot(ramps=ramps), cache_update_interval=100)
        d.update_chokepoints(iteration=0)
        ramps.append(_Ramp(_Pos(20, 0), _Pos(25, 0)))
        d.update_chokepoints(iteration=200)
        # Now should reflect 2 ramps × 2 entries = 4
        assert len(d.chokepoints) == 4


# ---------------------------------------------------------------------------
# is_in_chokepoint
# ---------------------------------------------------------------------------
class TestIsInChokepoint:
    def test_no_chokepoints_returns_false(self):
        d = ChokePointDetector(_make_bot())
        assert d.is_in_chokepoint(_Pos(0, 0)) is False

    def test_none_position_returns_false(self):
        d = ChokePointDetector(_make_bot())
        d.chokepoints = [_Pos(5, 5)]
        assert d.is_in_chokepoint(None) is False

    def test_position_within_radius_true(self):
        d = ChokePointDetector(_make_bot(), chokepoint_radius=5.0)
        d.chokepoints = [_Pos(0, 0)]
        assert d.is_in_chokepoint(_Pos(3, 0)) is True

    def test_position_outside_radius_false(self):
        d = ChokePointDetector(_make_bot(), chokepoint_radius=5.0)
        d.chokepoints = [_Pos(0, 0)]
        assert d.is_in_chokepoint(_Pos(10, 0)) is False


# ---------------------------------------------------------------------------
# get_cohesion_modifier
# ---------------------------------------------------------------------------
class TestGetCohesionModifier:
    def test_no_chokepoint_returns_one(self):
        d = ChokePointDetector(_make_bot())
        assert d.get_cohesion_modifier(_Pos(0, 0)) == 1.0

    def test_in_chokepoint_returns_quarter(self):
        d = ChokePointDetector(_make_bot(), chokepoint_radius=5.0)
        d.chokepoints = [_Pos(0, 0)]
        assert d.get_cohesion_modifier(_Pos(2, 0)) == 0.25


# ---------------------------------------------------------------------------
# get_nearest_chokepoint
# ---------------------------------------------------------------------------
class TestGetNearestChokepoint:
    def test_no_chokepoints_returns_none(self):
        d = ChokePointDetector(_make_bot())
        assert d.get_nearest_chokepoint(_Pos(0, 0)) is None

    def test_picks_closest(self):
        d = ChokePointDetector(_make_bot())
        c1 = _Pos(10, 0)
        c2 = _Pos(3, 0)
        c3 = _Pos(50, 0)
        d.chokepoints = [c1, c2, c3]
        assert d.get_nearest_chokepoint(_Pos(0, 0)) is c2


# ---------------------------------------------------------------------------
# get_chokepoint_avoidance_vector
# ---------------------------------------------------------------------------
class TestAvoidanceVector:
    def test_no_chokepoints_returns_zero(self):
        d = ChokePointDetector(_make_bot())
        assert d.get_chokepoint_avoidance_vector(_Pos(0, 0)) == (0.0, 0.0)

    def test_pushes_away_from_close_chokepoint(self):
        d = ChokePointDetector(_make_bot(), chokepoint_radius=5.0)
        d.chokepoints = [_Pos(2, 0)]  # east of position
        ax, ay = d.get_chokepoint_avoidance_vector(_Pos(0, 0))
        # Should push west (negative x)
        assert ax < 0
        assert abs(ay) < 1e-9

    def test_far_chokepoint_no_force(self):
        d = ChokePointDetector(_make_bot(), chokepoint_radius=5.0)
        d.chokepoints = [_Pos(50, 50)]  # outside radius
        assert d.get_chokepoint_avoidance_vector(_Pos(0, 0)) == (0.0, 0.0)

    def test_avoidance_weight_scales_force(self):
        d = ChokePointDetector(_make_bot(), chokepoint_radius=5.0)
        d.chokepoints = [_Pos(2, 0)]
        weak, _ = d.get_chokepoint_avoidance_vector(_Pos(0, 0), avoidance_weight=1.0)
        strong, _ = d.get_chokepoint_avoidance_vector(_Pos(0, 0), avoidance_weight=3.0)
        # 3x weight → 3x larger magnitude (negative direction → smaller value)
        assert strong < weak

    def test_point2_none_returns_zero(self, monkeypatch):
        """sc2 미설치 sentinel — Point2 가 falsy 면 (0, 0) 폴백."""
        monkeypatch.setattr(_mod, "Point2", None, raising=False)
        d = ChokePointDetector(_make_bot(), chokepoint_radius=5.0)
        d.chokepoints = [_Pos(2, 0)]
        assert d.get_chokepoint_avoidance_vector(_Pos(0, 0)) == (0.0, 0.0)
