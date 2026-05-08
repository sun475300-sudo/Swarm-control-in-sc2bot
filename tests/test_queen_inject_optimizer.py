"""Unit tests for QueenInjectOptimizer.

Focused on the dead-tag cleanup helper added to bound long-match memory.
"""

from __future__ import annotations

from collections import defaultdict
from unittest.mock import MagicMock

import pytest

try:
    from sc2.ids.unit_typeid import UnitTypeId
except ImportError:
    pytest.skip("sc2 library not available", allow_module_level=True)


from wicked_zerg_challenger.economy.queen_inject_optimizer import (
    QueenInjectOptimizer,
    QueenRole,
)


def _make_unit(tag: int):
    u = MagicMock()
    u.tag = tag
    return u


def _make_bot(queen_tags=(), hatch_tags=()):
    bot = MagicMock()
    bot.time = 100.0

    queens = [_make_unit(t) for t in queen_tags]
    hatcheries = [_make_unit(t) for t in hatch_tags]

    def units_call(type_id):
        if type_id is UnitTypeId.QUEEN:
            return queens
        return []

    bot.units = MagicMock(side_effect=units_call)
    bot.townhalls = hatcheries
    return bot


class TestCleanupDeadTags:
    def test_removes_dead_queen_entries(self):
        bot = _make_bot(queen_tags=[1, 2], hatch_tags=[10])
        opt = QueenInjectOptimizer(bot)

        opt.queen_assignments = {1: 10, 2: 10, 99: 10}  # 99 dead
        opt.queen_roles = {1: QueenRole.INJECT, 99: QueenRole.DEFENSE}
        opt.queens_reserved_for_inject = {1, 99}

        opt._cleanup_dead_tags()

        assert 99 not in opt.queen_assignments
        assert 99 not in opt.queen_roles
        assert 99 not in opt.queens_reserved_for_inject
        # Live queens preserved
        assert opt.queen_assignments[1] == 10

    def test_removes_dead_hatchery_entries(self):
        bot = _make_bot(queen_tags=[1], hatch_tags=[10])
        opt = QueenInjectOptimizer(bot)

        opt.inject_cooldowns = {10: 50.0, 999: 30.0}
        opt.expected_inject_times = {10: 80.0, 999: 60.0}
        opt.inject_retry_attempts = defaultdict(int)
        opt.inject_retry_attempts[10] = 1
        opt.inject_retry_attempts[999] = 2
        opt.hatchery_priorities = {10: 0, 999: 1}
        opt.hatchery_queens = defaultdict(set)
        opt.hatchery_queens[10].add(1)
        opt.hatchery_queens[999].add(1)

        opt._cleanup_dead_tags()

        for d in (
            opt.inject_cooldowns,
            opt.expected_inject_times,
            opt.inject_retry_attempts,
            opt.hatchery_priorities,
            opt.hatchery_queens,
        ):
            assert 999 not in d, f"dead hatchery 999 still present in {d}"
            assert 10 in d, "live hatchery 10 must be preserved"

    def test_no_op_when_bot_has_no_units(self):
        bot = MagicMock(spec=[])  # no units / townhalls attrs
        opt = QueenInjectOptimizer(MagicMock())  # init with full mock first
        opt.bot = bot
        opt.queen_assignments = {1: 10}
        opt._cleanup_dead_tags()
        # Untouched because bot lacks attrs
        assert opt.queen_assignments == {1: 10}
