#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Tests for BurrowController (combat/formation_tactics.py).

Covers ROADMAP Sprint 4.1: Lurkers must burrow to attack when an enemy
enters their attack range. Regression test for a bug where the burrow
call was a no-op placeholder because `enemy_units` was never passed to
`_handle_unburrowed_unit`.
"""

import os
import sys

import pytest

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

try:
    from sc2.ids.ability_id import AbilityId
    from sc2.ids.unit_typeid import UnitTypeId
except ImportError:
    pytest.skip("sc2 library not available", allow_module_level=True)

from combat.formation_tactics import BurrowController


class FakeUnit:
    def __init__(
        self, type_id, tag=1, position=(0, 0), health=100, health_max=100, is_idle=True
    ):
        self.type_id = type_id
        self.tag = tag
        self.position = position
        self.health = health
        self.health_max = health_max
        self.is_idle = is_idle
        self.calls = []

    def distance_to(self, other):
        other_pos = getattr(other, "position", other)
        return (
            (self.position[0] - other_pos[0]) ** 2
            + (self.position[1] - other_pos[1]) ** 2
        ) ** 0.5

    def __call__(self, ability):
        self.calls.append(ability)
        return ("ability", self.tag, ability)


class FakeEnemy:
    def __init__(self, position):
        self.position = position


def test_lurker_burrows_when_enemy_within_attack_range():
    controller = BurrowController()
    lurker = FakeUnit(UnitTypeId.LURKERMP, tag=1, position=(0, 0))
    enemy = FakeEnemy(position=(8, 0))  # distance 8, inside the 9.0 attack range

    action = controller._handle_unburrowed_unit(
        lurker,
        enemy_units=[enemy],
        health_ratio=1.0,
        enemy_nearby=True,
        down_ability=AbilityId.BURROWDOWN_LURKER,
    )

    assert action == ("ability", 1, AbilityId.BURROWDOWN_LURKER)


def test_lurker_stays_unburrowed_when_no_enemy_in_attack_range():
    controller = BurrowController()
    lurker = FakeUnit(UnitTypeId.LURKERMP, tag=1, position=(0, 0))
    enemy = FakeEnemy(position=(20, 0))  # distance 20, outside the 9.0 attack range

    action = controller._handle_unburrowed_unit(
        lurker,
        enemy_units=[enemy],
        health_ratio=1.0,
        enemy_nearby=False,
        down_ability=AbilityId.BURROWDOWN_LURKER,
    )

    assert action is None


def test_baneling_ambush_burrow_still_works():
    controller = BurrowController()
    baneling = FakeUnit(UnitTypeId.BANELING, tag=2, position=(0, 0), is_idle=True)

    action = controller._handle_unburrowed_unit(
        baneling,
        enemy_units=[FakeEnemy(position=(5, 0))],
        health_ratio=1.0,
        enemy_nearby=True,
        down_ability=AbilityId.BURROWDOWN_BANELING,
    )

    assert action == ("ability", 2, AbilityId.BURROWDOWN_BANELING)


def test_generic_unit_still_burrows_at_low_health():
    controller = BurrowController()
    roach = FakeUnit(UnitTypeId.ROACH, tag=3, position=(0, 0))

    action = controller._handle_unburrowed_unit(
        roach,
        enemy_units=[FakeEnemy(position=(5, 0))],
        health_ratio=0.2,
        enemy_nearby=True,
        down_ability=AbilityId.BURROWDOWN_ROACH,
    )

    assert action == ("ability", 3, AbilityId.BURROWDOWN_ROACH)
