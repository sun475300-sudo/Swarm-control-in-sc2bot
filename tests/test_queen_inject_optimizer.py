"""Tests for QueenInjectOptimizer queen-selection improvements.

Covers the two regressions fixed in Batch 2b:

1. Non-idle (but ground, energy-sufficient) queens are still considered
   eligible for inject — the previous ``queens.idle`` filter discarded
   queens with passive orders (e.g. rallying or returning from creep duty)
   and caused missed injects.
2. When multiple eligible queens are assigned to a hatchery, the optimizer
   picks the closest one instead of the first-encountered one.
"""

from __future__ import annotations

import asyncio
import os
import sys
from unittest.mock import MagicMock

import pytest

# Make the in-tree ``utils`` package visible — queen_inject_optimizer.py uses
# ``from utils.logger import get_logger`` which expects wicked_zerg_challenger
# to be on sys.path.
_WZC = os.path.join(os.path.dirname(__file__), "..", "wicked_zerg_challenger")
if os.path.isdir(_WZC) and _WZC not in sys.path:
    sys.path.insert(0, _WZC)

try:
    from sc2.ids.unit_typeid import UnitTypeId  # noqa: F401

    from wicked_zerg_challenger.economy.queen_inject_optimizer import (
        QueenInjectOptimizer,
    )
except ImportError:
    pytest.skip(
        "sc2 library or QueenInjectOptimizer not available",
        allow_module_level=True,
    )


class _Point:
    def __init__(self, x: float, y: float) -> None:
        self.x = float(x)
        self.y = float(y)

    def distance_to(self, other) -> float:
        ox, oy = other.x, other.y
        return ((self.x - ox) ** 2 + (self.y - oy) ** 2) ** 0.5


def _make_queen(tag, energy=100, position=(0.0, 0.0), is_flying=False):
    q = MagicMock()
    q.tag = tag
    q.energy = energy
    q.position = _Point(*position)
    q.is_flying = is_flying
    return q


def _make_hatchery(tag, position=(0.0, 0.0)):
    h = MagicMock()
    h.tag = tag
    h.position = _Point(*position)
    return h


class _UnitsList(list):
    """Tiny list-like that supports ``find_by_tag`` and ``__call__`` filters."""

    def find_by_tag(self, tag):
        for u in self:
            if getattr(u, "tag", None) == tag:
                return u
        return None

    def __call__(self, _unit_type):
        return self  # only queens are used in this test


def _make_bot(queens, hatcheries):
    bot = MagicMock()
    bot.time = 120.0
    bot.units = _UnitsList(queens)
    bot.townhalls = MagicMock()
    bot.townhalls.ready = hatcheries
    bot.do = MagicMock()
    return bot


def _make_optimizer(bot):
    opt = QueenInjectOptimizer(bot)

    # Force the can_inject / role / dedup checks to pass so the test exercises
    # only the queen-selection path.
    opt._can_inject = MagicMock(return_value=True)
    opt.can_queen_do_inject = MagicMock(return_value=True)
    opt._is_hatchery_already_injected = MagicMock(return_value=False)
    return opt


def test_non_idle_queen_with_energy_is_eligible_for_inject():
    """A queen with an active order but sufficient energy must still inject."""
    hatchery = _make_hatchery(tag=1, position=(0, 0))
    queen = _make_queen(tag=10, energy=80, position=(2, 0))
    queen.is_idle = False  # explicitly not idle

    bot = _make_bot(queens=[queen], hatcheries=[hatchery])
    opt = _make_optimizer(bot)

    asyncio.run(opt._execute_injects())

    assert bot.do.called, "Non-idle queen with energy should issue an inject"
    assert opt.total_injects == 1


def test_flying_queen_excluded_from_inject():
    """Defensive: flying queens (impossible in normal play) must be filtered."""
    hatchery = _make_hatchery(tag=2, position=(0, 0))
    queen = _make_queen(tag=11, energy=100, position=(1, 0), is_flying=True)

    bot = _make_bot(queens=[queen], hatcheries=[hatchery])
    opt = _make_optimizer(bot)

    asyncio.run(opt._execute_injects())

    assert not bot.do.called, "Flying queen must not inject"
    assert opt.total_injects == 0


def test_low_energy_queen_excluded():
    hatchery = _make_hatchery(tag=3, position=(0, 0))
    queen = _make_queen(tag=12, energy=20, position=(1, 0))

    bot = _make_bot(queens=[queen], hatcheries=[hatchery])
    opt = _make_optimizer(bot)

    asyncio.run(opt._execute_injects())

    assert not bot.do.called
    assert opt.total_injects == 0


def test_closest_assigned_queen_is_picked():
    """Given two assigned queens with enough energy, the closest one injects."""
    hatchery = _make_hatchery(tag=4, position=(0, 0))
    near = _make_queen(tag=20, energy=80, position=(1, 0))
    far = _make_queen(tag=21, energy=200, position=(20, 0))

    bot = _make_bot(queens=[near, far], hatcheries=[hatchery])
    opt = _make_optimizer(bot)
    opt.hatchery_queens[hatchery.tag] = {near.tag, far.tag}

    asyncio.run(opt._execute_injects())

    assert bot.do.called, "An inject should have been issued"
    # Inspect the argument: bot.do(queen(AbilityId.EFFECT_INJECTLARVA, hatchery))
    call_arg = bot.do.call_args.args[0]
    # The queen call returns a MagicMock whose first call args[0] is the ability
    # but MagicMock makes that opaque — easier check: the .tag of the queen that
    # had its __call__ invoked.
    invoked_queens = [q for q in (near, far) if q.call_args is not None]
    assert invoked_queens == [near], "Closest queen should have been chosen"
    del call_arg
