# -*- coding: utf-8 -*-
"""Tests for `rally_point.RallyPointManager` — rally update cadence,
army gather threshold, attack readiness. sc2-free via file-loading.
"""
from __future__ import annotations

import importlib.util
import logging
import sys
from pathlib import Path
from types import ModuleType, SimpleNamespace
from unittest.mock import MagicMock

import pytest


def _stub_utils_logger():
    if "utils" not in sys.modules:
        m = ModuleType("utils")
        m.__path__ = []
        sys.modules["utils"] = m
    if "utils.logger" not in sys.modules:
        lm = ModuleType("utils.logger")
        lm.get_logger = lambda name=None: logging.getLogger(name or "stub")
        lm.setup_logger = lambda *a, **k: logging.getLogger("stub")
        sys.modules["utils.logger"] = lm
        sys.modules["utils"].logger = lm  # type: ignore[attr-defined]


_stub_utils_logger()

_RP_PATH = (
    Path(__file__).resolve().parent.parent
    / "wicked_zerg_challenger"
    / "combat"
    / "rally_point.py"
)
try:
    _spec = importlib.util.spec_from_file_location("rally_point_t", _RP_PATH)
    if _spec is None or _spec.loader is None:
        raise ImportError(f"cannot build spec for {_RP_PATH}")
    _mod = importlib.util.module_from_spec(_spec)
    _spec.loader.exec_module(_mod)
    RallyPointManager = _mod.RallyPointManager
except Exception as exc:  # pragma: no cover
    pytest.skip(f"rally_point not importable: {exc}", allow_module_level=True)


# ---------------------------------------------------------------------------
# Fakes
# ---------------------------------------------------------------------------
class _Pos:
    def __init__(self, x: float, y: float):
        self.x = float(x)
        self.y = float(y)

    def distance_to(self, other) -> float:
        return ((other.x - self.x) ** 2 + (other.y - self.y) ** 2) ** 0.5


class _Unit:
    def __init__(self, x: float = 0, y: float = 0):
        self.position = _Pos(x, y)

    def distance_to(self, other) -> float:
        ox, oy = (other.x, other.y) if hasattr(other, "x") else (other.position.x, other.position.y)
        return ((ox - self.position.x) ** 2 + (oy - self.position.y) ** 2) ** 0.5


class _Units(list):
    @property
    def exists(self) -> bool:
        return len(self) > 0

    @property
    def amount(self) -> int:
        return len(self)

    @property
    def first(self):
        return self[0]


def _make_bot(townhalls=None, time: float = 0.0):
    bot = SimpleNamespace()
    bot.townhalls = townhalls if townhalls is not None else _Units()
    bot.time = time
    return bot


# ---------------------------------------------------------------------------
# rally_point property + initial state
# ---------------------------------------------------------------------------
class TestInitialState:
    def test_starts_with_no_rally_point(self):
        rp = RallyPointManager(_make_bot())
        assert rp.rally_point is None

    def test_should_update_when_no_rally_yet(self):
        rp = RallyPointManager(_make_bot())
        assert rp.should_update_rally_point(0.0) is True


# ---------------------------------------------------------------------------
# min_army_for_attack — game-time aware threshold
# ---------------------------------------------------------------------------
class TestMinArmyForAttack:
    def test_early_game_low_threshold(self):
        rp = RallyPointManager(_make_bot(time=120.0))  # 2분
        # < 5분 → early_game_min_attack = 12
        assert rp.min_army_for_attack == 12

    def test_late_game_high_threshold(self):
        rp = RallyPointManager(_make_bot(time=600.0))  # 10분
        # ≥ 5분 → min_army_for_attack = 20
        assert rp.min_army_for_attack == 20

    def test_boundary_at_300_seconds(self):
        rp = RallyPointManager(_make_bot(time=300.0))
        # 정확히 5분 → late game
        assert rp.min_army_for_attack == 20


# ---------------------------------------------------------------------------
# should_update_rally_point — interval gating
# ---------------------------------------------------------------------------
class TestShouldUpdateRallyPoint:
    def test_stale_rally_triggers_update(self):
        rp = RallyPointManager(_make_bot())
        rp._rally_point = _Pos(0, 0)
        rp._last_rally_update = 0
        # 31초 후 → 30초 interval 초과 → True
        assert rp.should_update_rally_point(31.0) is True

    def test_fresh_rally_does_not_trigger(self):
        rp = RallyPointManager(_make_bot())
        rp._rally_point = _Pos(0, 0)
        rp._last_rally_update = 100
        # 100초에 마지막 업데이트, 110초 호출 → False
        assert rp.should_update_rally_point(110.0) is False


# ---------------------------------------------------------------------------
# is_army_gathered
# ---------------------------------------------------------------------------
class TestIsArmyGathered:
    def test_no_rally_point_considered_gathered(self):
        rp = RallyPointManager(_make_bot())
        # rally_point is None → returns True
        assert rp.is_army_gathered([_Unit(0, 0)]) is True

    def test_no_units_considered_gathered(self):
        rp = RallyPointManager(_make_bot())
        rp._rally_point = _Pos(10, 10)
        assert rp.is_army_gathered([]) is True

    def test_all_units_near_rally_returns_true(self):
        rp = RallyPointManager(_make_bot())
        rp._rally_point = _Pos(0, 0)
        units = [_Unit(1, 1), _Unit(2, 0), _Unit(0, 3)]  # all within 15
        assert rp.is_army_gathered(units) is True

    def test_majority_far_returns_false(self):
        rp = RallyPointManager(_make_bot())
        rp._rally_point = _Pos(0, 0)
        # 1 close, 4 far — 20% gathered < 70% → False
        units = [
            _Unit(1, 1),
            _Unit(50, 50),
            _Unit(50, 50),
            _Unit(50, 50),
            _Unit(50, 50),
        ]
        assert rp.is_army_gathered(units) is False

    def test_70_percent_threshold(self):
        rp = RallyPointManager(_make_bot())
        rp._rally_point = _Pos(0, 0)
        # 7 close, 3 far — 70% exactly → True (>= threshold)
        units = [_Unit(1, 1) for _ in range(7)] + [_Unit(100, 100) for _ in range(3)]
        assert rp.is_army_gathered(units) is True


# ---------------------------------------------------------------------------
# has_minimum_army
# ---------------------------------------------------------------------------
class TestHasMinimumArmy:
    def test_below_threshold_returns_false_late_game(self):
        rp = RallyPointManager(_make_bot(time=600.0))
        # need 20, have 19
        assert rp.has_minimum_army([_Unit() for _ in range(19)]) is False

    def test_meets_threshold_returns_true_late_game(self):
        rp = RallyPointManager(_make_bot(time=600.0))
        assert rp.has_minimum_army([_Unit() for _ in range(20)]) is True

    def test_early_game_lower_threshold_passes(self):
        rp = RallyPointManager(_make_bot(time=60.0))
        # early game needs only 12
        assert rp.has_minimum_army([_Unit() for _ in range(12)]) is True


# ---------------------------------------------------------------------------
# update_rally_point — defensive guards
# ---------------------------------------------------------------------------
class TestUpdateRallyPoint:
    def test_no_townhalls_is_safe_noop(self):
        rp = RallyPointManager(_make_bot(townhalls=_Units()))
        # Should not raise
        rp.update_rally_point()
        assert rp.rally_point is None
