# -*- coding: utf-8 -*-
"""
Regression test for BurrowController lurker burrow-to-attack logic.

Lurkers deal damage only while burrowed, so they must auto-burrow whenever
an enemy is within attack range (9). This was silently disabled by a bug
where handle_burrow() never forwarded enemy_units to
_handle_unburrowed_unit(), so the lurker branch was dead code.
"""

import os
import sys
from unittest.mock import MagicMock

import pytest

sys.path.insert(
    0, os.path.join(os.path.dirname(__file__), "..", "wicked_zerg_challenger")
)

try:
    from combat.formation_tactics import AbilityId, BurrowController
except ImportError:
    pytest.skip("BurrowController not available", allow_module_level=True)

if AbilityId is None:
    # formation_tactics falls back to a no-op (AbilityId=None) when sc2 isn't
    # installed; handle_burrow() short-circuits on that, so this behavioral
    # test needs the real sc2 package to be meaningful.
    pytest.skip(
        "BurrowController behavior requires the real sc2 package (AbilityId)",
        allow_module_level=True,
    )

from sc2.ids.unit_typeid import UnitTypeId


def _make_unit(
    type_id, tag=1, is_burrowed=False, is_idle=True, health=100, health_max=100
):
    u = MagicMock()
    u.tag = tag
    u.type_id = type_id
    u.is_burrowed = is_burrowed
    u.is_idle = is_idle
    u.health = health
    u.health_max = health_max
    return u


class TestLurkerBurrowToAttack:
    def _controller(self):
        ctrl = BurrowController()
        # Bypass the BURROW upgrade / frame-interval gates that aren't the
        # subject of this test.
        ctrl._can_burrow = MagicMock(return_value=True)
        ctrl.last_check_frame = -1000
        return ctrl

    def _distances(self, near_dist):
        def distance_to(other):
            return near_dist

        return distance_to

    @pytest.mark.asyncio
    async def test_lurker_burrows_when_enemy_in_attack_range(self):
        ctrl = self._controller()
        lurker = _make_unit(UnitTypeId.LURKERMP, tag=1, is_burrowed=False)
        lurker.distance_to = self._distances(5.0)  # within 9.0 attack range
        enemy = _make_unit("ENEMY", tag=2)

        actions = []

        async def do_actions(acts):
            actions.extend(acts)

        await ctrl.handle_burrow(
            [lurker], [enemy], iteration=0, do_actions_func=do_actions
        )

        # The mocked unit call captures the ability invocation as unit(ability)
        assert lurker.call_count >= 1, "Lurker should have been commanded to burrow"

    @pytest.mark.asyncio
    async def test_lurker_stays_unburrowed_when_no_enemy_in_range(self):
        ctrl = self._controller()
        lurker = _make_unit(UnitTypeId.LURKERMP, tag=1, is_burrowed=False)
        lurker.distance_to = self._distances(50.0)  # far outside 9.0 range
        enemy = _make_unit("ENEMY", tag=2)

        actions = []

        async def do_actions(acts):
            actions.extend(acts)

        await ctrl.handle_burrow(
            [lurker], [enemy], iteration=0, do_actions_func=do_actions
        )

        assert lurker.call_count == 0, "Lurker should not burrow with no enemy in range"

    @pytest.mark.asyncio
    async def test_lurker_stays_unburrowed_with_no_enemies(self):
        ctrl = self._controller()
        lurker = _make_unit(UnitTypeId.LURKERMP, tag=1, is_burrowed=False)
        lurker.distance_to = self._distances(5.0)

        actions = []

        async def do_actions(acts):
            actions.extend(acts)

        await ctrl.handle_burrow([lurker], [], iteration=0, do_actions_func=do_actions)

        assert (
            lurker.call_count == 0
        ), "Lurker should not burrow with an empty enemy list"
