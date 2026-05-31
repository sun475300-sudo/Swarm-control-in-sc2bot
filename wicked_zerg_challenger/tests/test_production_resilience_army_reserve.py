# -*- coding: utf-8 -*-
"""Coverage for the army-larva third-base reserve gate.

Companion to ``test_production_resilience.test_third_base_reserve_blocks_army_larva_when_defense_ready``:
exercises the gate from a few different conditions to lock in the behaviour
(min-defense met → hold; min-defense missing → still produce; ignore_caps →
still produce; reserve inactive → still produce).
"""

from __future__ import annotations

import asyncio
import os
import sys
from types import SimpleNamespace
from unittest.mock import AsyncMock, Mock

import pytest

# Make wicked package importable without polluting sys.path with
# wicked_zerg_challenger/local_training/ (would prime sys.modules['scripts']).
_HERE = os.path.dirname(__file__)
_BOT_DIR = os.path.abspath(os.path.join(_HERE, ".."))
if _BOT_DIR not in sys.path:
    sys.path.insert(0, _BOT_DIR)

from sc2.ids.unit_typeid import UnitTypeId

try:
    from local_training.production_resilience import ProductionResilience
except ImportError:
    pytest.skip("ProductionResilience not importable", allow_module_level=True)


def _make_bot(time, minerals, base_count, zerglings=0, roaches=0, hydras=0, mutas=0):
    bot = Mock()
    bot.time = time
    bot.minerals = minerals
    bot.vespene = 100
    bot.supply_left = 5
    bot.supply_used = 30
    bot.supply_cap = 50
    bot.townhalls = Mock(amount=base_count, exists=True)
    bot.townhalls.ready = Mock(amount=base_count, exists=True)
    bot.already_pending = Mock(return_value=0)
    bot.can_afford = Mock(return_value=True)
    bot.enemy_units = []

    counts = {
        UnitTypeId.ZERGLING: zerglings,
        UnitTypeId.ROACH: roaches,
        UnitTypeId.HYDRALISK: hydras,
        UnitTypeId.MUTALISK: mutas,
    }

    def units(unit_type):
        return SimpleNamespace(amount=counts.get(unit_type, 0))

    bot.units = Mock(side_effect=units)
    bot.structures = Mock(
        side_effect=lambda _u: SimpleNamespace(
            ready=SimpleNamespace(exists=False, first=None), exists=False, amount=0
        )
    )
    return bot


@pytest.fixture
def resilience():
    """ProductionResilience driven against fresh bots per-test."""

    def _make(bot):
        pr = ProductionResilience(bot)
        pr._safe_train = AsyncMock(return_value=True)
        return pr

    return _make


def test_reserve_blocks_when_min_defense_met(resilience):
    # 190s, 2 bases, zerglings=6 -> defense met, reserve active -> hold larva.
    bot = _make_bot(time=190.0, minerals=250, base_count=2, zerglings=6)
    pr = resilience(bot)

    result = asyncio.run(pr._produce_army_unit(Mock()))

    assert result is False
    bot.can_afford.assert_not_called()
    pr._safe_train.assert_not_called()


def test_reserve_releases_when_defense_missing(resilience):
    # 190s, 2 bases, zerglings=0 -> defense NOT met. The reserve should NOT
    # block: instead, produce zerglings to reach the floor.
    bot = _make_bot(time=190.0, minerals=250, base_count=2, zerglings=0)
    pr = resilience(bot)

    asyncio.run(pr._produce_army_unit(Mock()))

    # Either the safe-train was invoked OR can_afford was consulted for the
    # zergling fallback inside the min-defense branch — definitely not the
    # silent "return False" the reserve gate uses.
    assert pr._safe_train.called or bot.can_afford.called


def test_reserve_ignored_when_ignore_caps(resilience):
    # ignore_caps=True bypasses the reserve gate (rich-bank override).
    bot = _make_bot(time=190.0, minerals=250, base_count=2, zerglings=6)
    pr = resilience(bot)

    asyncio.run(pr._produce_army_unit(Mock(), ignore_caps=True))

    # ignore_caps short-circuits BOTH the reserve gate and the defense gate,
    # so production should proceed to the unit-cap logic (can_afford checks).
    assert bot.can_afford.called


def test_no_reserve_when_third_already_pending(resilience):
    # already_pending(HATCHERY) > 0 means a third base is on the way, so the
    # reserve is satisfied — _produce_army_unit should proceed.
    bot = _make_bot(time=190.0, minerals=250, base_count=2, zerglings=6)
    bot.already_pending = Mock(
        side_effect=lambda u: 1 if u == UnitTypeId.HATCHERY else 0
    )
    pr = resilience(bot)

    asyncio.run(pr._produce_army_unit(Mock()))

    assert bot.can_afford.called


def test_no_reserve_before_150s(resilience):
    # Before 150s the third-base reserve doesn't fire, regardless of defense.
    bot = _make_bot(time=140.0, minerals=250, base_count=2, zerglings=6)
    pr = resilience(bot)

    asyncio.run(pr._produce_army_unit(Mock()))

    assert bot.can_afford.called
