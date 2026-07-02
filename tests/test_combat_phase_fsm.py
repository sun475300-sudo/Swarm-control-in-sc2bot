# -*- coding: utf-8 -*-
"""
Unit Tests -- CombatPhaseController FSM Transitions (P2.1)

Tests lock the phase-transition rules so regressions are caught immediately.

Phase graph (happy path):
  IDLE -> GATHERING -> POSITIONING -> ENGAGEMENT -> ACTIVE_COMBAT -> REGROUPING -> IDLE
  Any (not RETREAT/REGROUPING) -> RETREAT  (HP low + outnumbered)
  RETREAT -> REGROUPING                    (enemies clear)
  REGROUPING -> IDLE                       (health restored)
"""

import os
import sys
from dataclasses import dataclass, field
from typing import List, Optional, Set
from unittest.mock import MagicMock
from unittest.mock import patch
from unittest.mock import patch as mock_patch

import pytest

# ---------------------------------------------------------------------------
# Path setup
# ---------------------------------------------------------------------------
sys.path.insert(
    0, os.path.join(os.path.dirname(__file__), "..", "wicked_zerg_challenger")
)

try:
    from combat_phase_controller import CombatGroup, CombatPhase, CombatPhaseController
except ImportError:
    pytest.skip(
        "combat_phase_controller not importable (SC2 env required)",
        allow_module_level=True,
    )


# ---------------------------------------------------------------------------
# Minimal fakes
# ---------------------------------------------------------------------------


class FakePoint2:
    def __init__(self, x=0.0, y=0.0):
        self.x = float(x)
        self.y = float(y)

    def _xy(self, other):
        if isinstance(other, FakePoint2):
            return other.x, other.y
        # plain tuple / namedtuple (Point2 = tuple fallback in combat_phase_controller)
        try:
            return float(other[0]), float(other[1])
        except (TypeError, KeyError):
            return float(other.x), float(other.y)

    def __sub__(self, other):
        ox, oy = self._xy(other)
        return FakePoint2(self.x - ox, self.y - oy)

    def __add__(self, other):
        ox, oy = self._xy(other)
        return FakePoint2(self.x + ox, self.y + oy)

    def __mul__(self, scalar):
        return FakePoint2(self.x * scalar, self.y * scalar)

    def __rmul__(self, scalar):
        return self.__mul__(scalar)

    @property
    def normalized(self):
        length = (self.x**2 + self.y**2) ** 0.5 or 1.0
        return FakePoint2(self.x / length, self.y / length)

    def __iter__(self):
        return iter((self.x, self.y))

    def __getitem__(self, idx):
        return (self.x, self.y)[idx]

    def __repr__(self):
        return "FakePoint2({}, {})".format(self.x, self.y)


class FakeUnit:
    def __init__(
        self, tag, position, health=100.0, health_max=100.0, weapon_cooldown=0.0
    ):
        self.tag = tag
        self.position = position
        self.health = health
        self.health_max = health_max
        self.shield = 0.0
        self.weapon_cooldown = weapon_cooldown

    @property
    def health_percentage(self):
        return self.health / self.health_max if self.health_max > 0 else 0.0

    def distance_to(self, other):
        if hasattr(other, "position"):
            ox, oy = other.position.x, other.position.y
        else:
            try:
                ox, oy = float(other[0]), float(other[1])
            except (TypeError, KeyError):
                ox, oy = float(other.x), float(other.y)
        return ((self.position.x - ox) ** 2 + (self.position.y - oy) ** 2) ** 0.5

    def move(self, pos):
        return MagicMock()

    def attack(self, target):
        return MagicMock()


class FakeUnits:
    """Minimal Units collection."""

    def __init__(self, units):
        self._units = list(units)

    def __iter__(self):
        return iter(self._units)

    def __len__(self):
        return len(self._units)

    def __bool__(self):
        return bool(self._units)

    def closest_distance_to(self, point):
        if not self._units:
            return float("inf")
        return min(u.distance_to(point) for u in self._units)

    def filter(self, predicate):
        return FakeUnits([u for u in self._units if predicate(u)])


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def bot():
    b = MagicMock()
    b.do = MagicMock()
    b.units = FakeUnits([])
    b.enemy_units = FakeUnits([])
    b.game_info = MagicMock()
    b.game_info.map_center = FakePoint2(50, 50)
    return b


@pytest.fixture
def controller(bot):
    with patch("combat_phase_controller.get_logger", return_value=MagicMock()):
        ctrl = CombatPhaseController(bot)
    return ctrl


def _make_group(
    phase,
    unit_tags,
    rally=None,
    target=None,
    engagement_time=0.0,
    last_phase_change=0.0,
):
    return CombatGroup(
        units=set(unit_tags),
        phase=phase,
        rally_point=rally,
        target_position=target,
        formation_type="ball",
        engagement_time=engagement_time,
        last_phase_change=last_phase_change,
        initial_unit_count=len(unit_tags),
        initial_total_hp=len(unit_tags) * 100.0,
        enemies_killed=0,
        damage_taken=0.0,
    )


def last_transition(ctrl):
    assert ctrl.phase_transitions, "No transitions recorded"
    entry = ctrl.phase_transitions[-1]
    return entry[0], entry[1]


# ---------------------------------------------------------------------------
# _transition_phase -- low-level record keeping
# ---------------------------------------------------------------------------


class TestTransitionPhaseRecording:
    def test_records_old_and_new_phase(self, controller):
        group = _make_group(CombatPhase.IDLE, {1, 2})
        controller._transition_phase("g1", group, CombatPhase.GATHERING, 10.0)
        assert group.phase == CombatPhase.GATHERING
        assert group.last_phase_change == 10.0
        frm, to = last_transition(controller)
        assert frm == CombatPhase.IDLE
        assert to == CombatPhase.GATHERING

    def test_multiple_transitions_all_recorded(self, controller):
        group = _make_group(CombatPhase.IDLE, {1})
        controller._transition_phase("g1", group, CombatPhase.GATHERING, 1.0)
        controller._transition_phase("g1", group, CombatPhase.POSITIONING, 2.0)
        controller._transition_phase("g1", group, CombatPhase.ENGAGEMENT, 3.0)
        assert len(controller.phase_transitions) == 3
        phases = [t[1] for t in controller.phase_transitions]
        assert phases == [
            CombatPhase.GATHERING,
            CombatPhase.POSITIONING,
            CombatPhase.ENGAGEMENT,
        ]

    def test_last_phase_change_updated(self, controller):
        group = _make_group(CombatPhase.GATHERING, {1})
        controller._transition_phase("g1", group, CombatPhase.POSITIONING, 42.5)
        assert group.last_phase_change == 42.5


# ---------------------------------------------------------------------------
# _check_phase_transitions -- retreat trigger
# ---------------------------------------------------------------------------


class TestRetreatTrigger:
    """HP < threshold AND enemies > 1.5x our units -> RETREAT."""

    def _check(self, controller, group, our_units, enemies, health_ratio):
        controller._check_phase_transitions(
            "g1", group, our_units, enemies, health_ratio, game_time=30.0
        )

    def test_retreat_triggered_when_hp_low_and_outnumbered(self, controller):
        our = FakeUnits([FakeUnit(i, FakePoint2(0, 0)) for i in range(4)])
        enemies = FakeUnits([FakeUnit(100 + i, FakePoint2(5, 5)) for i in range(7)])
        group = _make_group(CombatPhase.ACTIVE_COMBAT, {u.tag for u in our})
        self._check(controller, group, our, enemies, 0.25)
        assert group.phase == CombatPhase.RETREAT
        frm, to = last_transition(controller)
        assert frm == CombatPhase.ACTIVE_COMBAT
        assert to == CombatPhase.RETREAT

    def test_retreat_not_triggered_when_hp_high(self, controller):
        our = FakeUnits([FakeUnit(i, FakePoint2(0, 0)) for i in range(4)])
        enemies = FakeUnits([FakeUnit(100 + i, FakePoint2(5, 5)) for i in range(7)])
        group = _make_group(CombatPhase.ACTIVE_COMBAT, {u.tag for u in our})
        self._check(controller, group, our, enemies, 0.60)
        assert group.phase == CombatPhase.ACTIVE_COMBAT
        assert not controller.phase_transitions

    def test_retreat_not_triggered_when_not_outnumbered(self, controller):
        our = FakeUnits([FakeUnit(i, FakePoint2(0, 0)) for i in range(6)])
        # 8 < 6*1.5=9 -> not outnumbered
        enemies = FakeUnits([FakeUnit(100 + i, FakePoint2(5, 5)) for i in range(8)])
        group = _make_group(CombatPhase.ACTIVE_COMBAT, {u.tag for u in our})
        self._check(controller, group, our, enemies, 0.20)
        assert group.phase == CombatPhase.ACTIVE_COMBAT

    def test_retreat_not_triggered_when_no_enemies(self, controller):
        our = FakeUnits([FakeUnit(i, FakePoint2(0, 0)) for i in range(4)])
        enemies = FakeUnits([])
        group = _make_group(CombatPhase.ACTIVE_COMBAT, {u.tag for u in our})
        self._check(controller, group, our, enemies, 0.10)
        assert group.phase == CombatPhase.ACTIVE_COMBAT

    @pytest.mark.parametrize("phase", [CombatPhase.RETREAT, CombatPhase.REGROUPING])
    def test_retreat_not_re_triggered_in_exempt_phases(self, controller, phase):
        our = FakeUnits([FakeUnit(i, FakePoint2(0, 0)) for i in range(2)])
        enemies = FakeUnits([FakeUnit(100 + i, FakePoint2(5, 5)) for i in range(10)])
        group = _make_group(phase, {u.tag for u in our})
        self._check(controller, group, our, enemies, 0.05)
        assert group.phase == phase
        assert not controller.phase_transitions


# ---------------------------------------------------------------------------
# Idle -> Gathering
# ---------------------------------------------------------------------------


class TestIdleToGathering:
    def _run(self, controller, group, our, enemies, game_time=5.0):
        import asyncio

        asyncio.run(
            controller._handle_idle_phase(
                "g1", group, FakeUnits(our), enemies, game_time
            )
        )

    def test_transitions_to_gathering_when_enemy_detected(self, controller):
        our = [FakeUnit(i, FakePoint2(0, 0)) for i in range(10)]
        enemies = FakeUnits([FakeUnit(100, FakePoint2(10, 10))])
        group = _make_group(CombatPhase.IDLE, {u.tag for u in our})
        self._run(controller, group, our, enemies)
        assert group.phase == CombatPhase.GATHERING

    def test_stays_idle_without_enemies_or_target(self, controller):
        our = [FakeUnit(i, FakePoint2(0, 0)) for i in range(10)]
        enemies = FakeUnits([])
        group = _make_group(CombatPhase.IDLE, {u.tag for u in our}, target=None)
        self._run(controller, group, our, enemies)
        assert group.phase == CombatPhase.IDLE

    def test_transitions_when_sufficient_units_and_target(self, controller):
        our = [FakeUnit(i, FakePoint2(0, 0)) for i in range(8)]
        enemies = FakeUnits([])
        group = _make_group(
            CombatPhase.IDLE, {u.tag for u in our}, target=FakePoint2(100, 100)
        )
        self._run(controller, group, our, enemies)
        assert group.phase == CombatPhase.GATHERING

    def test_stays_idle_when_insufficient_units(self, controller):
        our = [FakeUnit(i, FakePoint2(0, 0)) for i in range(7)]
        enemies = FakeUnits([])
        group = _make_group(
            CombatPhase.IDLE, {u.tag for u in our}, target=FakePoint2(100, 100)
        )
        self._run(controller, group, our, enemies)
        assert group.phase == CombatPhase.IDLE


# ---------------------------------------------------------------------------
# Gathering -> Positioning
# ---------------------------------------------------------------------------


class TestGatheringToPositioning:
    def _run(self, controller, group, all_units, game_time=10.0):
        import asyncio

        asyncio.run(
            controller._handle_gathering_phase(
                "g1", group, FakeUnits(all_units), game_time
            )
        )

    def test_transitions_when_70pct_at_rally(self, controller):
        rally = FakePoint2(10, 10)
        near = [FakeUnit(i, FakePoint2(10, 10)) for i in range(8)]
        far = [FakeUnit(10 + i, FakePoint2(100, 100)) for i in range(2)]
        all_units = near + far
        group = _make_group(
            CombatPhase.GATHERING, {u.tag for u in all_units}, rally=rally
        )
        self._run(controller, group, all_units)
        assert group.phase == CombatPhase.POSITIONING

    def test_stays_gathering_when_less_than_70pct_arrived(self, controller):
        rally = FakePoint2(10, 10)
        near = [FakeUnit(i, FakePoint2(10, 10)) for i in range(5)]
        far = [FakeUnit(10 + i, FakePoint2(100, 100)) for i in range(5)]
        all_units = near + far
        group = _make_group(
            CombatPhase.GATHERING, {u.tag for u in all_units}, rally=rally
        )
        self._run(controller, group, all_units)
        assert group.phase == CombatPhase.GATHERING


# ---------------------------------------------------------------------------
# Positioning -> Engagement
# (patch _calculate_formation_positions to avoid sc2 Point2 dependency)
# ---------------------------------------------------------------------------


class TestPositioningToEngagement:
    def _run(self, controller, group, our, enemies, game_time=15.0):
        import asyncio

        with patch.object(
            controller, "_calculate_formation_positions", return_value=[]
        ):
            asyncio.run(
                controller._handle_positioning_phase(
                    "g1", group, FakeUnits(our), enemies, game_time
                )
            )

    def test_transitions_when_enemy_within_10(self, controller):
        our = [FakeUnit(i, FakePoint2(0, 0)) for i in range(5)]
        enemies = FakeUnits([FakeUnit(100, FakePoint2(8, 0))])  # dist=8 < 10
        group = _make_group(
            CombatPhase.POSITIONING, {u.tag for u in our}, target=FakePoint2(20, 0)
        )
        self._run(controller, group, our, enemies)
        assert group.phase == CombatPhase.ENGAGEMENT

    def test_stays_positioning_when_enemy_far(self, controller):
        our = [FakeUnit(i, FakePoint2(0, 0)) for i in range(5)]
        enemies = FakeUnits([FakeUnit(100, FakePoint2(20, 0))])  # dist=20 > 10
        group = _make_group(
            CombatPhase.POSITIONING, {u.tag for u in our}, target=FakePoint2(30, 0)
        )
        self._run(controller, group, our, enemies)
        assert group.phase == CombatPhase.POSITIONING


# ---------------------------------------------------------------------------
# Engagement -> Active Combat
# (patch _get_priority_target to avoid sc2 Unit.health_percentage dependency)
# ---------------------------------------------------------------------------


class TestEngagementToActiveCombat:
    def _run(self, controller, group, our, enemies, game_time):
        import asyncio

        with patch.object(controller, "_get_priority_target", return_value=None):
            asyncio.run(
                controller._handle_engagement_phase(
                    "g1", group, FakeUnits(our), enemies, game_time
                )
            )

    def test_transitions_after_2s(self, controller):
        our = [FakeUnit(i, FakePoint2(0, 0)) for i in range(5)]
        enemies = FakeUnits([FakeUnit(100, FakePoint2(3, 0))])
        group = _make_group(
            CombatPhase.ENGAGEMENT, {u.tag for u in our}, engagement_time=10.0
        )
        self._run(controller, group, our, enemies, game_time=12.1)
        assert group.phase == CombatPhase.ACTIVE_COMBAT

    def test_stays_engagement_before_2s(self, controller):
        our = [FakeUnit(i, FakePoint2(0, 0)) for i in range(5)]
        enemies = FakeUnits([FakeUnit(100, FakePoint2(3, 0))])
        group = _make_group(
            CombatPhase.ENGAGEMENT, {u.tag for u in our}, engagement_time=10.0
        )
        self._run(controller, group, our, enemies, game_time=11.0)
        assert group.phase == CombatPhase.ENGAGEMENT

    def test_transitions_to_positioning_when_no_enemies(self, controller):
        our = [FakeUnit(i, FakePoint2(0, 0)) for i in range(5)]
        enemies = FakeUnits([])
        group = _make_group(
            CombatPhase.ENGAGEMENT, {u.tag for u in our}, engagement_time=10.0
        )
        self._run(controller, group, our, enemies, game_time=12.5)
        assert group.phase == CombatPhase.POSITIONING


# ---------------------------------------------------------------------------
# Active Combat -> Regrouping
# ---------------------------------------------------------------------------


class TestActiveCombatToRegrouping:
    def test_transitions_to_regrouping_when_enemies_cleared(self, controller):
        our = [FakeUnit(i, FakePoint2(0, 0)) for i in range(5)]
        enemies = FakeUnits([])
        group = _make_group(CombatPhase.ACTIVE_COMBAT, {u.tag for u in our})
        import asyncio

        asyncio.run(
            controller._handle_active_combat_phase(
                "g1", group, FakeUnits(our), enemies, 20.0, iteration=100
            )
        )
        assert group.phase == CombatPhase.REGROUPING


# ---------------------------------------------------------------------------
# Full happy-path sequence smoke test (no async needed)
# ---------------------------------------------------------------------------


class TestFullPhaseSequence:
    """Smoke tests using _transition_phase directly."""

    def test_happy_path_transition_chain(self, controller):
        group = _make_group(CombatPhase.IDLE, {1, 2, 3})
        seq = [
            CombatPhase.GATHERING,
            CombatPhase.POSITIONING,
            CombatPhase.ENGAGEMENT,
            CombatPhase.ACTIVE_COMBAT,
            CombatPhase.REGROUPING,
            CombatPhase.IDLE,
        ]
        for t, phase in enumerate(seq):
            controller._transition_phase("g1", group, phase, float(t))
        assert group.phase == CombatPhase.IDLE
        assert len(controller.phase_transitions) == len(seq)
        recorded = [t[1] for t in controller.phase_transitions]
        assert recorded == seq

    def test_retreat_from_active_combat_then_regroup(self, controller):
        group = _make_group(CombatPhase.ACTIVE_COMBAT, {1, 2, 3})
        controller._transition_phase("g1", group, CombatPhase.RETREAT, 10.0)
        controller._transition_phase("g1", group, CombatPhase.REGROUPING, 15.0)
        assert group.phase == CombatPhase.REGROUPING
        recorded = [t[1] for t in controller.phase_transitions]
        assert CombatPhase.RETREAT in recorded
        assert CombatPhase.REGROUPING in recorded
