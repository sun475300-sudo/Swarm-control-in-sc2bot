"""Unit tests for QueenInjectOptimizer.

Covers the pure-logic helpers that don't require an SC2 game loop:
- _can_inject (cooldown gate)
- _is_hatchery_already_injected (buff inspection)
- _calculate_inject_efficiency (theoretical-max ratio)
- _update_queen_assignments dead-tag cleanup
- _assign_queen_roles dead-tag cleanup
- get_inject_stats shape
"""

from __future__ import annotations

from unittest.mock import MagicMock

import pytest

try:
    from wicked_zerg_challenger.economy.queen_inject_optimizer import (
        QueenInjectOptimizer,
        QueenRole,
    )
except ImportError as exc:  # pragma: no cover
    pytest.skip(f"queen_inject_optimizer import failed: {exc}", allow_module_level=True)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_unit(tag: int, position=(0.0, 0.0)):
    u = MagicMock()
    u.tag = tag
    u.position = MagicMock()
    u.position.x = position[0]
    u.position.y = position[1]
    u.position.distance_to = MagicMock(return_value=0.0)
    return u


def _make_bot(time: float = 30.0):
    bot = MagicMock()
    bot.time = time
    bot.units = MagicMock()
    bot.townhalls = MagicMock()
    bot.start_location = MagicMock()
    bot.start_location.distance_to = MagicMock(return_value=0.0)
    return bot


# ---------------------------------------------------------------------------
# _can_inject
# ---------------------------------------------------------------------------


class TestCanInject:
    def test_can_inject_when_no_history(self):
        opt = QueenInjectOptimizer(_make_bot())
        hatch = _make_unit(tag=10)

        assert opt._can_inject(hatch, game_time=30.0) is True

    def test_blocked_within_cooldown(self):
        opt = QueenInjectOptimizer(_make_bot())
        hatch = _make_unit(tag=10)
        opt.inject_cooldowns[10] = 50.0  # 마지막 인젝트 t=50

        assert (
            opt._can_inject(hatch, game_time=60.0) is False
        ), "10s after last cast (cooldown=29s) must block"

    def test_allowed_after_cooldown(self):
        opt = QueenInjectOptimizer(_make_bot())
        hatch = _make_unit(tag=10)
        opt.inject_cooldowns[10] = 50.0

        assert opt._can_inject(hatch, game_time=80.0) is True


# ---------------------------------------------------------------------------
# _is_hatchery_already_injected
# ---------------------------------------------------------------------------


class TestHatcheryAlreadyInjected:
    def test_no_buffs_attribute_returns_false(self):
        opt = QueenInjectOptimizer(_make_bot())
        hatch = MagicMock(spec=[])  # no buffs attribute

        assert opt._is_hatchery_already_injected(hatch) is False

    def test_inject_buff_present_returns_true(self):
        opt = QueenInjectOptimizer(_make_bot())
        hatch = MagicMock()
        hatch.buffs = ["INJECTLARVA"]

        assert opt._is_hatchery_already_injected(hatch) is True

    def test_larva_buff_also_matches(self):
        opt = QueenInjectOptimizer(_make_bot())
        hatch = MagicMock()
        hatch.buffs = ["QUEENSPAWNLARVATIMER"]

        assert opt._is_hatchery_already_injected(hatch) is True

    def test_unrelated_buff_returns_false(self):
        opt = QueenInjectOptimizer(_make_bot())
        hatch = MagicMock()
        hatch.buffs = ["RAVENSCRAMBLERMISSILE"]

        assert opt._is_hatchery_already_injected(hatch) is False


# ---------------------------------------------------------------------------
# _calculate_inject_efficiency
# ---------------------------------------------------------------------------


class TestInjectEfficiency:
    def test_early_game_skipped(self):
        bot = _make_bot(time=30.0)  # < 60s
        opt = QueenInjectOptimizer(bot)
        opt.total_injects = 5
        opt.inject_efficiency = 0.7  # sentinel

        opt._calculate_inject_efficiency()

        assert (
            opt.inject_efficiency == 0.7
        ), "Early game (<60s) must not update efficiency"

    def test_efficiency_capped_at_one(self):
        bot = _make_bot(time=120.0)
        bot.townhalls.ready = MagicMock()
        bot.townhalls.ready.amount = 2
        bot.townhalls.ready.__bool__ = MagicMock(return_value=True)
        opt = QueenInjectOptimizer(bot)
        opt.total_injects = 999  # impossibly large

        opt._calculate_inject_efficiency()

        assert opt.inject_efficiency == 1.0, "Efficiency must be clamped at 1.0"

    def test_efficiency_proportional_to_injects(self):
        bot = _make_bot(time=120.0)
        bot.townhalls.ready = MagicMock()
        bot.townhalls.ready.amount = 1
        bot.townhalls.ready.__bool__ = MagicMock(return_value=True)
        opt = QueenInjectOptimizer(bot)

        # Theoretical max at t=120 with 1 hatch = 120/29 ≈ 4.14
        opt.total_injects = 2  # ~48% of max

        opt._calculate_inject_efficiency()

        assert 0.4 < opt.inject_efficiency < 0.6


# ---------------------------------------------------------------------------
# get_inject_stats
# ---------------------------------------------------------------------------


class TestGetInjectStats:
    def test_default_shape(self):
        opt = QueenInjectOptimizer(_make_bot())

        stats = opt.get_inject_stats()

        assert set(stats.keys()) == {
            "total_injects",
            "missed_injects",
            "inject_efficiency",
            "queens_assigned",
            "hatcheries_covered",
        }
        assert stats["total_injects"] == 0
        assert stats["queens_assigned"] == 0
        assert stats["hatcheries_covered"] == 0


# ---------------------------------------------------------------------------
# Dead-tag cleanup in _update_queen_assignments
# ---------------------------------------------------------------------------


def _set_units_and_townhalls(bot, queens, hatches):
    """Wire the MagicMock bot so `bot.units(QUEEN)` returns the queens
    list and `bot.townhalls.ready` returns the hatches list. Lists are
    fine here — the production code only iterates them, and a list
    can be iterated more than once whereas an iterator can't."""
    bot.units.side_effect = lambda *_a, **_kw: queens
    bot.townhalls.ready = hatches


class TestUpdateQueenAssignments:
    def test_dead_queen_tag_purged(self):
        bot = _make_bot()
        opt = QueenInjectOptimizer(bot)

        # Pre-seed a stale assignment for a queen no longer alive
        opt.queen_assignments[999] = 10

        q = _make_unit(1)
        h = _make_unit(10)
        _set_units_and_townhalls(bot, [q], [h])

        opt._update_queen_assignments()

        assert 999 not in opt.queen_assignments
        assert opt.queen_assignments[1] == 10

    def test_dead_hatch_tag_purged(self):
        bot = _make_bot()
        opt = QueenInjectOptimizer(bot)

        # Queen 1 was previously assigned to the now-dead hatch 99
        opt.queen_assignments[1] = 99

        q = _make_unit(1)
        new_hatch = _make_unit(10)
        _set_units_and_townhalls(bot, [q], [new_hatch])

        opt._update_queen_assignments()

        assert opt.queen_assignments[1] == 10, "Queen must be re-assigned to live hatch"


# ---------------------------------------------------------------------------
# Dead-tag cleanup in _assign_queen_roles
# ---------------------------------------------------------------------------


class TestAssignQueenRoles:
    def test_dead_queen_role_purged(self):
        bot = _make_bot()
        opt = QueenInjectOptimizer(bot)

        # Stale role for a dead queen
        opt.queen_roles[999] = QueenRole.INJECT
        opt.queens_reserved_for_inject.add(999)

        q = _make_unit(1)
        h = _make_unit(10)
        _set_units_and_townhalls(bot, [q], [h])

        opt._assign_queen_roles()

        assert 999 not in opt.queen_roles
        assert 999 not in opt.queens_reserved_for_inject

    def test_dead_hatch_state_purged(self):
        bot = _make_bot()
        opt = QueenInjectOptimizer(bot)

        # Pre-seed dead-hatch entries across all four hatch-keyed dicts
        opt.inject_cooldowns[99] = 10.0
        opt.hatchery_priorities[99] = 5
        opt.expected_inject_times[99] = 50.0
        opt.inject_retry_attempts[99] = 2

        q = _make_unit(1)
        h = _make_unit(10)
        _set_units_and_townhalls(bot, [q], [h])

        opt._assign_queen_roles()

        assert 99 not in opt.inject_cooldowns
        assert 99 not in opt.hatchery_priorities
        assert 99 not in opt.expected_inject_times
        assert 99 not in opt.inject_retry_attempts
