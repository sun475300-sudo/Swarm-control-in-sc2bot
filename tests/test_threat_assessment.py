# -*- coding: utf-8 -*-
"""Tests for `threat_assessment.ThreatAssessment` — base attack detection,
counter-attack windows, threat scoring, retreat heuristic. sc2-free.
"""
from __future__ import annotations

import importlib.util
import logging
import sys
from pathlib import Path
from types import ModuleType, SimpleNamespace
from unittest.mock import MagicMock

import pytest


# threat_assessment.py 가 `from utils.logger import get_logger` 를 하므로
# sys.path 에 wicked_zerg_challenger 를 넣지 않고도 통과시키기 위해
# 가벼운 utils.logger 더미를 sys.modules 에 미리 주입한다.
def _stub_utils_logger():
    if "utils" not in sys.modules:
        utils_mod = ModuleType("utils")
        utils_mod.__path__ = []  # mark as namespace pkg
        sys.modules["utils"] = utils_mod
    if "utils.logger" not in sys.modules:
        logger_mod = ModuleType("utils.logger")
        logger_mod.get_logger = lambda name=None: logging.getLogger(name or "stub")
        logger_mod.setup_logger = lambda *a, **k: logging.getLogger("stub")
        sys.modules["utils.logger"] = logger_mod
        sys.modules["utils"].logger = logger_mod  # type: ignore[attr-defined]


_stub_utils_logger()

_TA_PATH = (
    Path(__file__).resolve().parent.parent
    / "wicked_zerg_challenger"
    / "combat"
    / "threat_assessment.py"
)
try:
    _spec = importlib.util.spec_from_file_location("threat_assessment_t", _TA_PATH)
    if _spec is None or _spec.loader is None:
        raise ImportError(f"cannot build spec for {_TA_PATH}")
    _mod = importlib.util.module_from_spec(_spec)
    _spec.loader.exec_module(_mod)
    ThreatAssessment = _mod.ThreatAssessment
except Exception as exc:  # pragma: no cover
    pytest.skip(f"threat_assessment not importable: {exc}", allow_module_level=True)


# ---------------------------------------------------------------------------
# Fakes
# ---------------------------------------------------------------------------
class _Pos:
    def __init__(self, x: float, y: float):
        self.x = float(x)
        self.y = float(y)

    def distance_to(self, other) -> float:
        return ((other.x - self.x) ** 2 + (other.y - self.y) ** 2) ** 0.5


class _TypeId:
    def __init__(self, name: str):
        self.name = name


class _Unit:
    def __init__(
        self,
        x: float = 0,
        y: float = 0,
        type_name: str = "ZERGLING",
        supply_cost: float = 1,
        health_pct: float = 1.0,
        is_flying: bool = False,
        can_attack: bool = True,
    ):
        self.position = _Pos(x, y)
        self.type_id = _TypeId(type_name)
        self.supply_cost = supply_cost
        self.health_percentage = health_pct
        self.is_flying = is_flying
        self.can_attack = can_attack

    def distance_to(self, other) -> float:
        ox, oy = (other.x, other.y) if hasattr(other, "x") else (other.position.x, other.position.y)
        return ((ox - self.position.x) ** 2 + (oy - self.position.y) ** 2) ** 0.5


class _Units(list):
    @property
    def exists(self) -> bool:
        return len(self) > 0

    def closer_than(self, radius: float, position) -> "_Units":
        out = _Units()
        for u in self:
            if u.distance_to(position) < radius:
                out.append(u)
        return out


def _make_bot(townhalls=None, enemy_units=None, time: float = 0.0):
    bot = SimpleNamespace()
    bot.townhalls = townhalls if townhalls is not None else _Units()
    bot.enemy_units = enemy_units if enemy_units is not None else _Units()
    bot.time = time
    return bot


# ---------------------------------------------------------------------------
# get_army_power — 가장 단순한 순수 계산
# ---------------------------------------------------------------------------
class TestGetArmyPower:
    def test_empty_returns_zero(self):
        ta = ThreatAssessment(_make_bot())
        assert ta.get_army_power([]) == 0.0

    def test_basic_supply_times_health(self):
        ta = ThreatAssessment(_make_bot())
        units = [_Unit(type_name="ZERGLING", supply_cost=0.5, health_pct=1.0)]
        # 0.5 * 1.0 = 0.5
        assert ta.get_army_power(units) == pytest.approx(0.5)

    def test_health_percentage_scales_power(self):
        ta = ThreatAssessment(_make_bot())
        full = [_Unit(supply_cost=2, health_pct=1.0)]
        half = [_Unit(supply_cost=2, health_pct=0.5)]
        assert ta.get_army_power(full) == 2.0
        assert ta.get_army_power(half) == 1.0

    def test_ultralisk_gets_15x_multiplier(self):
        ta = ThreatAssessment(_make_bot())
        ling = [_Unit(type_name="ZERGLING", supply_cost=2, health_pct=1.0)]
        ultra = [_Unit(type_name="ULTRALISK", supply_cost=2, health_pct=1.0)]
        # 2.0 vs 2.0 * 1.5 = 3.0
        assert ta.get_army_power(ultra) == pytest.approx(3.0)
        assert ta.get_army_power(ling) == pytest.approx(2.0)

    def test_baneling_gets_12x_multiplier(self):
        ta = ThreatAssessment(_make_bot())
        bane = [_Unit(type_name="BANELING", supply_cost=1, health_pct=1.0)]
        # 1 * 1.2 = 1.2
        assert ta.get_army_power(bane) == pytest.approx(1.2)


# ---------------------------------------------------------------------------
# should_retreat
# ---------------------------------------------------------------------------
class TestShouldRetreat:
    def test_no_army_retreats(self):
        ta = ThreatAssessment(_make_bot())
        assert ta.should_retreat([], _Units()) is True

    def test_tiny_army_retreats(self):
        ta = ThreatAssessment(_make_bot())
        small_army = [_Unit() for _ in range(3)]
        assert ta.should_retreat(small_army, _Units()) is True

    def test_balanced_army_does_not_retreat(self):
        ta = ThreatAssessment(_make_bot())
        ours = [_Unit(supply_cost=2) for _ in range(10)]
        theirs = [_Unit(supply_cost=2) for _ in range(8)]
        assert ta.should_retreat(ours, theirs) is False

    def test_retreats_when_enemy_2x_stronger(self):
        ta = ThreatAssessment(_make_bot())
        ours = [_Unit(supply_cost=1) for _ in range(10)]
        theirs = [_Unit(supply_cost=4) for _ in range(10)]  # 4x supply
        assert ta.should_retreat(ours, theirs) is True


# ---------------------------------------------------------------------------
# calculate_threat_score
# ---------------------------------------------------------------------------
class TestCalculateThreatScore:
    def test_empty_enemies_zero(self):
        ta = ThreatAssessment(_make_bot())
        assert ta.calculate_threat_score(_Units(), _Pos(0, 0)) == 0

    def test_far_enemies_ignored(self):
        ta = ThreatAssessment(_make_bot())
        far = _Units([_Unit(100, 100, type_name="MARINE")])
        assert ta.calculate_threat_score(far, _Pos(0, 0)) == 0

    def test_high_threat_unit_scores_3(self):
        ta = ThreatAssessment(_make_bot())
        zerg = _Units([_Unit(5, 0, type_name="ZERGLING")])
        # ZERGLING is in high_threat_names → +3
        assert ta.calculate_threat_score(zerg, _Pos(0, 0)) == 3

    def test_flying_high_threat_scores_4(self):
        """high-threat (3) + flying bonus (1) = 4."""
        ta = ThreatAssessment(_make_bot())
        muta = _Units([_Unit(5, 0, type_name="MARINE", is_flying=True)])
        assert ta.calculate_threat_score(muta, _Pos(0, 0)) == 4

    def test_attack_capable_scores_2(self):
        ta = ThreatAssessment(_make_bot())
        unknown = _Units([_Unit(5, 0, type_name="UNKNOWN", can_attack=True)])
        assert ta.calculate_threat_score(unknown, _Pos(0, 0)) == 2


# ---------------------------------------------------------------------------
# is_base_under_attack
# ---------------------------------------------------------------------------
class TestIsBaseUnderAttack:
    def test_no_townhalls_returns_false(self):
        bot = _make_bot(townhalls=_Units())
        ta = ThreatAssessment(bot)
        assert ta.is_base_under_attack() is False

    def test_no_enemies_returns_false(self):
        bot = _make_bot(
            townhalls=_Units([_Unit()]),
            enemy_units=_Units(),
        )
        ta = ThreatAssessment(bot)
        assert ta.is_base_under_attack() is False

    def test_close_enemy_triggers_alert(self):
        bot = _make_bot(
            townhalls=_Units([_Unit(0, 0)]),
            enemy_units=_Units([_Unit(5, 0, type_name="MARINE")]),
            time=0.0,
        )
        ta = ThreatAssessment(bot)
        assert ta.is_base_under_attack() is True

    def test_distant_low_threat_enemy_does_not_trigger(self):
        bot = _make_bot(
            townhalls=_Units([_Unit(0, 0)]),
            # 50 cells away, plain marine — outside both base ranges
            enemy_units=_Units([_Unit(50, 0, type_name="OVERLORD", can_attack=False)]),
        )
        ta = ThreatAssessment(bot)
        assert ta.is_base_under_attack() is False


# ---------------------------------------------------------------------------
# check_counterattack_opportunity
# ---------------------------------------------------------------------------
class TestCounterattackOpportunity:
    def test_no_recent_combat_blocks_counter(self):
        ta = ThreatAssessment(_make_bot())
        # Force no combat ever, then call at t=10 — should be False
        ours = [_Unit(supply_cost=2) for _ in range(10)]
        theirs = []
        assert ta.check_counterattack_opportunity(ours, theirs, game_time=10.0) is False

    def test_supply_advantage_triggers_counter(self):
        ta = ThreatAssessment(_make_bot())
        ours = [_Unit(supply_cost=2) for _ in range(10)]  # 20 supply
        # First call at t=0 records combat
        theirs = [_Unit(supply_cost=1) for _ in range(5)]  # 5 supply
        # Force last counter time far in past so cooldown doesn't block
        ta._last_counter_attack_time = -100
        assert ta.check_counterattack_opportunity(ours, theirs, game_time=1.0) is True
