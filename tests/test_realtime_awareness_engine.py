# -*- coding: utf-8 -*-
"""
Unit tests for wicked_zerg_challenger/realtime_awareness_engine.py (624 LOC).

Covers Situation/Problem/Override dataclasses, engine init, summary rendering,
emergency/force-army flag properties, and the on_step throttle behaviour.
"""
import os
import sys
from unittest.mock import MagicMock

import pytest

sys.path.insert(
    0, os.path.join(os.path.dirname(__file__), "..", "wicked_zerg_challenger")
)


def _import():
    try:
        from realtime_awareness_engine import (
            Override,
            Problem,
            RealtimeAwarenessEngine,
            Situation,
        )
        return RealtimeAwarenessEngine, Situation, Problem, Override
    except ImportError:
        return None, None, None, None


RealtimeAwarenessEngine, Situation, Problem, Override = _import()

pytestmark = pytest.mark.skipif(
    RealtimeAwarenessEngine is None,
    reason="realtime_awareness_engine not importable",
)


@pytest.fixture
def bot():
    b = MagicMock()
    b.time = 0.0
    b.minerals = 0
    b.vespene = 0
    b.supply_used = 0
    b.supply_cap = 0
    b.supply_left = 0
    b.workers = []
    b.townhalls = []
    b.units = []
    b.structures = []
    b.enemy_units = []
    return b


@pytest.fixture
def engine(bot):
    return RealtimeAwarenessEngine(bot)


class TestDataclasses:
    def test_situation_defaults(self):
        s = Situation()
        assert s.game_time == 0.0
        assert s.phase == "opening"
        assert s.minerals == 0
        assert s.threat_level == "none"

    def test_problem_required_fields(self):
        p = Problem(
            category="cat", severity="critical",
            description="d", prescription="p", priority=1,
        )
        assert p.severity == "critical"

    def test_override_required_fields(self):
        o = Override(
            action="train", unit_type="ZERGLING",
            count=5, reason="test", priority=1, expires_at=120.0,
        )
        assert o.unit_type == "ZERGLING"
        assert o.count == 5


class TestInit:
    def test_empty_problems_and_overrides(self, engine):
        assert engine.active_problems == []
        assert engine.active_overrides == []
        assert engine.problem_history == []

    def test_emergency_modes_off(self, engine):
        assert engine._emergency_mode is False
        assert engine._force_army_mode is False

    def test_update_interval_sensible(self, engine):
        assert 0.1 <= engine.update_interval <= 5.0


class TestIsEmergency:
    def test_no_problems(self, engine):
        assert engine.is_emergency is False

    def test_medium_severity_not_emergency(self, engine):
        engine.active_problems = [Problem("c", "medium", "d", "p", 2)]
        assert engine.is_emergency is False

    def test_critical_is_emergency(self, engine):
        engine.active_problems = [Problem("c", "critical", "d", "p", 1)]
        assert engine.is_emergency is True

    def test_mixed_severity_is_emergency_if_any_critical(self, engine):
        engine.active_problems = [
            Problem("a", "medium", "d", "p", 2),
            Problem("b", "critical", "d", "p", 1),
        ]
        assert engine.is_emergency is True


class TestForceArmy:
    def test_default_false(self, engine):
        assert engine.should_force_army is False

    def test_set_true(self, engine):
        engine._force_army_mode = True
        assert engine.should_force_army is True


class TestSituationSummary:
    def test_summary_has_key_fields(self, engine):
        engine.situation = Situation(
            game_time=300.0, phase="mid",
            minerals=400, vespene=200,
            supply_used=50, supply_cap=70,
            worker_count=25, army_supply=20,
            base_count=3, threat_level="medium",
        )
        out = engine.get_situation_summary()
        assert "MID" in out
        assert "300" in out
        assert "50/70" in out
        assert "Workers: 25" in out
        assert "Bases: 3" in out
        assert "M:400" in out
        assert "G:200" in out
        assert "medium" in out

    def test_summary_with_problems(self, engine):
        engine.situation = Situation(phase="early")
        engine.active_problems = [
            Problem("supply_block", "high", "d", "p", 1),
            Problem("mineral_overflow", "medium", "d", "p", 2),
        ]
        out = engine.get_situation_summary()
        assert "supply_block" in out
        assert "mineral_overflow" in out

    def test_summary_no_problems_says_none(self, engine):
        engine.situation = Situation(phase="opening")
        out = engine.get_situation_summary()
        assert "Problems: none" in out


class TestOnStepThrottle:
    def test_throttles_within_interval(self, bot, engine):
        bot.time = 0.0
        engine.on_step(0)  # first call
        first_last = engine.last_update

        bot.time = 0.5  # only half a second passed
        engine.on_step(1)
        # Throttle: last_update should be unchanged
        assert engine.last_update == first_last

    def test_runs_when_interval_elapses(self, bot, engine):
        bot.time = 0.0
        engine.on_step(0)

        bot.time = 2.0  # past 1-second interval
        engine.on_step(1)
        assert engine.last_update == 2.0

    def test_returns_list_not_none(self, bot, engine):
        bot.time = 0.0
        out = engine.on_step(0)
        assert isinstance(out, list)
