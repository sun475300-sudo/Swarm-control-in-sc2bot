# -*- coding: utf-8 -*-
"""Regression tests for CreepAutomationV2 tumor-relay cooldown.

The relay cooldown previously read ``getattr(self.bot, "_game_loop", 0)`` which
always returned 0 (BotAI exposes the frame counter as ``self.state.game_loop``),
so the 50-frame cooldown never engaged and burrowed tumors were re-issued spread
orders every cycle. These tests lock in the corrected behaviour.
"""

import asyncio
import os
import sys

import pytest

sys.path.insert(
    0, os.path.join(os.path.dirname(__file__), "..", "wicked_zerg_challenger")
)

try:
    from creep_automation_v2 import CreepAutomationV2
    from sc2.ids.ability_id import AbilityId
    from sc2.position import Point2
except ImportError:
    pytest.skip("creep_automation_v2 / sc2 not available", allow_module_level=True)


class _Tumor:
    def __init__(self, tag, pos):
        self.tag = tag
        self.position = Point2(pos)

    def distance_to(self, other):
        pos = other.position if hasattr(other, "position") else other
        return self.position.distance_to(pos)

    def __call__(self, ability, target):
        return ("tumor_cmd", self.tag, ability, target)


class _TumorGroup:
    def __init__(self, tumors):
        self._t = list(tumors)

    @property
    def exists(self):
        return len(self._t) > 0

    def sorted(self, key):
        return sorted(self._t, key=key)


class _Structures:
    def __init__(self, tumors):
        self._tumors = tumors

    def of_type(self, _types):
        return _TumorGroup(self._tumors)


class _State:
    def __init__(self, game_loop):
        self.game_loop = game_loop


class _Bot:
    def __init__(self, tumors, game_loop):
        self.enemy_start_locations = [Point2((100, 100))]
        self.structures = _Structures(tumors)
        self.state = _State(game_loop)
        self.actions = []

    def has_creep(self, _pos):
        return True

    async def get_available_abilities(self, _unit):
        return [AbilityId.BUILD_CREEPTUMOR_TUMOR]

    def do(self, action):
        self.actions.append(action)


def _run(coro):
    return asyncio.run(coro)


def test_cooldown_records_real_game_loop():
    """Spreading must stamp the cooldown with the live game_loop (not 0)."""
    bot = _Bot([_Tumor(1, (50, 50))], game_loop=100)
    auto = CreepAutomationV2(bot)

    _run(auto._tumor_relay_toward_enemy())

    assert len(bot.actions) == 1
    assert auto._tumor_cooldowns[1] == 100  # was always 0 before the fix


def test_cooldown_blocks_within_50_frames():
    bot = _Bot([_Tumor(1, (50, 50))], game_loop=100)
    auto = CreepAutomationV2(bot)
    _run(auto._tumor_relay_toward_enemy())

    # Only 30 frames later -> still on cooldown. Clear the position-dedup set so
    # the cooldown gate is the only thing that can block the second spread.
    bot.state.game_loop = 130
    bot.actions.clear()
    auto.tumor_positions.clear()
    _run(auto._tumor_relay_toward_enemy())

    assert bot.actions == []  # blocked by the (now working) cooldown


def test_cooldown_allows_after_50_frames():
    bot = _Bot([_Tumor(1, (50, 50))], game_loop=100)
    auto = CreepAutomationV2(bot)
    _run(auto._tumor_relay_toward_enemy())

    bot.state.game_loop = 160  # 60 frames later -> cooldown expired
    bot.actions.clear()
    auto.tumor_positions.clear()
    _run(auto._tumor_relay_toward_enemy())

    assert len(bot.actions) == 1


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
