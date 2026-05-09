# -*- coding: utf-8 -*-
"""Tests for `stutter_step_kiting.StutterStepKiting` — kite eligibility,
weapon-cooldown branching, dead-unit cleanup. sc2-free via file-loading.
"""
from __future__ import annotations

import importlib.util
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import MagicMock

import pytest


_SS_PATH = (
    Path(__file__).resolve().parent.parent
    / "wicked_zerg_challenger"
    / "combat"
    / "stutter_step_kiting.py"
)
try:
    _spec = importlib.util.spec_from_file_location("stutter_step_kiting_t", _SS_PATH)
    if _spec is None or _spec.loader is None:
        raise ImportError(f"cannot build spec for {_SS_PATH}")
    _mod = importlib.util.module_from_spec(_spec)
    _spec.loader.exec_module(_mod)
    StutterStepKiting = _mod.StutterStepKiting
    UnitTypeId = _mod.UnitTypeId
except Exception as exc:  # pragma: no cover
    pytest.skip(f"stutter_step_kiting not importable: {exc}", allow_module_level=True)


# ---------------------------------------------------------------------------
# Fakes
# ---------------------------------------------------------------------------
class _Pos:
    def __init__(self, x: float, y: float):
        self.x = float(x)
        self.y = float(y)

    def __sub__(self, other) -> "_Vec":
        return _Vec(self.x - other.x, self.y - other.y)

    def __add__(self, other) -> "_Pos":
        return _Pos(self.x + other.x, self.y + other.y)

    def distance_to(self, other) -> float:
        return ((other.x - self.x) ** 2 + (other.y - self.y) ** 2) ** 0.5


class _Vec(_Pos):
    @property
    def normalized(self) -> "_Vec":
        m = (self.x**2 + self.y**2) ** 0.5 or 1.0
        return _Vec(self.x / m, self.y / m)

    def __mul__(self, scalar: float) -> "_Vec":
        return _Vec(self.x * scalar, self.y * scalar)


class _Unit:
    def __init__(
        self,
        x: float = 0,
        y: float = 0,
        type_id=UnitTypeId.HYDRALISK,
        tag: int = 1,
        weapon_cooldown: float = 0.0,
    ):
        self.position = _Pos(x, y)
        self.type_id = type_id
        self.tag = tag
        self.weapon_cooldown = weapon_cooldown

    def attack(self, target):
        return ("attack", self.tag, getattr(target, "tag", None))

    def move(self, pos):
        return ("move", self.tag, (pos.x, pos.y))


class _Units(list):
    def closest_to(self, position):
        if not self:
            return None
        return min(self, key=lambda u: u.position.distance_to(position))


def _make_bot():
    bot = SimpleNamespace()
    bot.iteration = 0
    bot.do_calls = []
    bot.do = lambda action: bot.do_calls.append(action)
    return bot


# ---------------------------------------------------------------------------
# should_kite — type whitelist
# ---------------------------------------------------------------------------
class TestShouldKite:
    def test_hydralisk_kites(self):
        ssk = StutterStepKiting(_make_bot())
        assert ssk.should_kite(_Unit(type_id=UnitTypeId.HYDRALISK)) is True

    def test_roach_kites(self):
        ssk = StutterStepKiting(_make_bot())
        assert ssk.should_kite(_Unit(type_id=UnitTypeId.ROACH)) is True

    def test_zergling_does_not_kite(self):
        ssk = StutterStepKiting(_make_bot())
        # ZERGLING is not in KITING_UNITS — must be False.
        # Fallback stub UnitTypeId may not have ZERGLING; use a sentinel
        sentinel = object()
        assert ssk.should_kite(_Unit(type_id=sentinel)) is False


# ---------------------------------------------------------------------------
# execute_kiting branches
# ---------------------------------------------------------------------------
class TestExecuteKiting:
    def test_returns_false_for_non_kiting_unit(self):
        ssk = StutterStepKiting(_make_bot())
        non_kiter = _Unit(type_id=object())
        enemy = _Unit(5, 0, type_id=object(), tag=99)
        assert ssk.execute_kiting(non_kiter, None, _Units([enemy])) is False

    def test_returns_false_when_no_enemies(self):
        ssk = StutterStepKiting(_make_bot())
        u = _Unit(type_id=UnitTypeId.HYDRALISK)
        assert ssk.execute_kiting(u, None, _Units([])) is False

    def test_attacks_when_weapon_ready_and_in_range(self):
        bot = _make_bot()
        ssk = StutterStepKiting(bot)
        u = _Unit(0, 0, type_id=UnitTypeId.HYDRALISK, tag=1, weapon_cooldown=0.0)
        target = _Unit(3, 0, type_id=object(), tag=99)
        result = ssk.execute_kiting(u, target, _Units([target]))
        assert result is True
        # Should have issued an attack
        assert any(call[0] == "attack" for call in bot.do_calls)
        assert ssk.unit_states[1] == "attacking"

    def test_retreats_when_weapon_on_cooldown(self):
        bot = _make_bot()
        # Fake game_info for clamp_to_map
        bot.game_info = SimpleNamespace(
            map_center=_Pos(50, 50),
            playable_area=SimpleNamespace(x=0, y=0, width=100, height=100),
        )
        ssk = StutterStepKiting(bot)
        u = _Unit(0, 0, type_id=UnitTypeId.HYDRALISK, tag=1, weapon_cooldown=5.0)
        target = _Unit(3, 0, type_id=object(), tag=99)
        result = ssk.execute_kiting(u, target, _Units([target]))
        assert result is True
        assert any(call[0] == "move" for call in bot.do_calls)
        assert ssk.unit_states[1] == "retreating"
        assert 1 in ssk.retreat_positions

    def test_auto_selects_closest_enemy_when_no_target(self):
        bot = _make_bot()
        ssk = StutterStepKiting(bot)
        u = _Unit(0, 0, type_id=UnitTypeId.HYDRALISK, tag=1, weapon_cooldown=0.0)
        # Two enemies; near at (3,0), far at (50,50)
        near = _Unit(3, 0, type_id=object(), tag=10)
        far = _Unit(50, 50, type_id=object(), tag=11)
        result = ssk.execute_kiting(u, None, _Units([far, near]))
        assert result is True
        # Verify the closer enemy was attacked
        attacks = [c for c in bot.do_calls if c[0] == "attack"]
        assert attacks
        assert attacks[0][2] == 10  # tag of `near`


# ---------------------------------------------------------------------------
# get_kiting_status / cleanup_dead_units
# ---------------------------------------------------------------------------
class TestStateTracking:
    def test_status_returns_none_for_unknown(self):
        ssk = StutterStepKiting(_make_bot())
        u = _Unit(tag=42)
        assert ssk.get_kiting_status(u) is None

    def test_cleanup_keeps_only_alive_tags(self):
        ssk = StutterStepKiting(_make_bot())
        ssk.unit_states = {1: "attacking", 2: "retreating", 3: "approaching"}
        ssk.last_attack_frame = {1: 100, 2: 105, 3: 110}
        ssk.retreat_positions = {2: _Pos(5, 5)}

        ssk.cleanup_dead_units(alive_tags={1, 3})

        assert set(ssk.unit_states.keys()) == {1, 3}
        assert set(ssk.last_attack_frame.keys()) == {1, 3}
        assert set(ssk.retreat_positions.keys()) == set()  # 2 was removed

    def test_cleanup_with_all_dead(self):
        ssk = StutterStepKiting(_make_bot())
        ssk.unit_states = {1: "attacking", 2: "retreating"}
        ssk.cleanup_dead_units(alive_tags=set())
        assert ssk.unit_states == {}
