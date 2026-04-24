# -*- coding: utf-8 -*-
"""
Unit tests for wicked_zerg_challenger/combat_phase_controller.py (554 LOC).

Covers deterministic helpers: combat-unit classification (LURKER regression),
group center/health ratio, priority targeting, alive check, report rendering.
Excludes async phase-transition logic which needs extensive mocking.
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
        from combat_phase_controller import (
            CombatPhase,
            CombatGroup,
            CombatPhaseController,
        )
        return CombatPhaseController, CombatPhase, CombatGroup
    except ImportError:
        return None, None, None


CombatPhaseController, CombatPhase, CombatGroup = _import()

pytestmark = pytest.mark.skipif(
    CombatPhaseController is None,
    reason="combat_phase_controller not importable",
)


def _unit(tag, type_id, x=0.0, y=0.0, hp=100, hp_max=100, shield=0, shield_max=0):
    u = MagicMock()
    u.tag = tag
    u.type_id = type_id
    from sc2.position import Point2
    u.position = Point2((x, y))
    u.health = hp
    u.health_max = hp_max
    u.shield = shield
    u.shield_max = shield_max
    u.health_percentage = hp / hp_max if hp_max > 0 else 1.0
    u.distance_to = lambda other: (
        (u.position.x - other.position.x) ** 2
        + (u.position.y - other.position.y) ** 2
    ) ** 0.5
    return u


@pytest.fixture
def bot():
    b = MagicMock()
    b.time = 0.0
    b.units = None
    b.enemy_units = None
    return b


@pytest.fixture
def ctrl(bot):
    return CombatPhaseController(bot)


class TestInit:
    def test_default_thresholds(self, ctrl):
        assert ctrl.min_army_for_attack > 0
        assert 0.0 < ctrl.retreat_hp_threshold < 1.0
        assert ctrl.regroup_distance > 0

    def test_counters_zero(self, ctrl):
        assert ctrl.total_engagements == 0
        assert ctrl.successful_engagements == 0
        assert ctrl.total_units_lost == 0
        assert ctrl.total_enemies_killed == 0

    def test_history_empty(self, ctrl):
        assert ctrl.combat_history == []
        assert ctrl.phase_transitions == []


class TestGetGroupCenter:
    def test_empty_returns_origin(self, ctrl):
        from sc2.position import Point2
        center = ctrl._get_group_center([])
        assert center == Point2((0, 0))

    def test_arithmetic_mean(self, ctrl):
        from sc2.ids.unit_typeid import UnitTypeId
        units = [
            _unit(1, UnitTypeId.ZERGLING, 0, 0),
            _unit(2, UnitTypeId.ZERGLING, 10, 0),
            _unit(3, UnitTypeId.ZERGLING, 5, 15),
        ]
        center = ctrl._get_group_center(units)
        # mean(x) = 5, mean(y) = 5
        assert center.x == pytest.approx(5.0)
        assert center.y == pytest.approx(5.0)


class TestGetGroupHealthRatio:
    def test_empty_is_zero(self, ctrl):
        assert ctrl._get_group_health_ratio([]) == 0.0

    def test_full_health(self, ctrl):
        from sc2.ids.unit_typeid import UnitTypeId
        u1 = _unit(1, UnitTypeId.ROACH, hp=145, hp_max=145)
        u2 = _unit(2, UnitTypeId.ROACH, hp=145, hp_max=145)
        assert ctrl._get_group_health_ratio([u1, u2]) == pytest.approx(1.0)

    def test_half_health(self, ctrl):
        from sc2.ids.unit_typeid import UnitTypeId
        u1 = _unit(1, UnitTypeId.ROACH, hp=50, hp_max=100)
        u2 = _unit(2, UnitTypeId.ROACH, hp=50, hp_max=100)
        assert ctrl._get_group_health_ratio([u1, u2]) == pytest.approx(0.5)

    def test_includes_shields(self, ctrl):
        from sc2.ids.unit_typeid import UnitTypeId
        # stalker-ish unit with shields.
        u = _unit(1, UnitTypeId.STALKER, hp=80, hp_max=80, shield=40, shield_max=80)
        # (80 + 40) / (80 + 80) = 120/160 = 0.75
        assert ctrl._get_group_health_ratio([u]) == pytest.approx(0.75)

    def test_zero_max_hp_is_zero(self, ctrl):
        u = MagicMock()
        u.health = 0
        u.health_max = 0
        u.shield = 0
        u.shield_max = 0
        assert ctrl._get_group_health_ratio([u]) == 0.0


class TestIsUnitAlive:
    def test_no_units_attr(self, bot, ctrl):
        del bot.units
        assert ctrl._is_unit_alive(1) is False

    def test_found(self, bot, ctrl):
        from sc2.ids.unit_typeid import UnitTypeId
        bot.units = [_unit(1, UnitTypeId.ZERGLING), _unit(2, UnitTypeId.ROACH)]
        assert ctrl._is_unit_alive(1) is True

    def test_not_found(self, bot, ctrl):
        from sc2.ids.unit_typeid import UnitTypeId
        bot.units = [_unit(1, UnitTypeId.ZERGLING)]
        assert ctrl._is_unit_alive(99) is False


class TestGetPriorityTarget:
    def test_no_enemies_returns_none(self, ctrl):
        assert ctrl._get_priority_target([], []) is None

    def test_picks_weakest_when_enough_friendly_in_range(self, ctrl):
        from sc2.ids.unit_typeid import UnitTypeId
        weak = _unit(100, UnitTypeId.MARINE, 5, 5, hp=10, hp_max=100)
        strong = _unit(101, UnitTypeId.MARINE, 5, 5, hp=80, hp_max=100)
        friendly = [
            _unit(i, UnitTypeId.ZERGLING, 5, 5)
            for i in range(5)  # 5 friendly units within range
        ]
        assert ctrl._get_priority_target([weak, strong], friendly) is weak


class TestGetCombatUnits:
    def test_no_units_attr(self, bot, ctrl):
        del bot.units
        out = ctrl._get_combat_units()
        # Should return an empty units collection (no crash).
        assert len(out) == 0

    def test_lurkermp_included_lurker_excluded(self, bot, ctrl):
        """Regression for the LURKER->LURKERMP fix."""
        from sc2.ids.unit_typeid import UnitTypeId
        u_lurker = _unit(1, UnitTypeId.LURKER)
        u_lurkermp = _unit(2, UnitTypeId.LURKERMP)
        u_ling = _unit(3, UnitTypeId.ZERGLING)

        class FakeUnits(list):
            def filter(self, pred):
                return FakeUnits(u for u in self if pred(u))

        bot.units = FakeUnits([u_lurker, u_lurkermp, u_ling])
        combat = ctrl._get_combat_units()
        tags = {u.tag for u in combat}
        assert 2 in tags, "LURKERMP should be included in combat units"
        assert 1 not in tags, "LURKER (id 911) is not a playable lurker"
        assert 3 in tags


class TestGetCombatReport:
    def test_empty_report_has_expected_sections(self, ctrl):
        report = ctrl.get_combat_report()
        assert "COMBAT PHASE CONTROLLER" in report
        assert "Active Groups: 0" in report
        assert "Total Engagements: 0" in report

    def test_k_d_ratio_rendered(self, ctrl):
        ctrl.total_enemies_killed = 7
        ctrl.total_units_lost = 3
        report = ctrl.get_combat_report()
        assert "7/3" in report

    def test_success_rate_after_engagements(self, ctrl):
        ctrl.total_engagements = 4
        ctrl.successful_engagements = 3
        report = ctrl.get_combat_report()
        assert "75.0%" in report
