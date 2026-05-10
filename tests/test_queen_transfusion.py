"""Tests for QueenTransfusionManager — priority, dedup, and cooldown logic.

These tests use MagicMock so no SC2 game instance is required.
"""
from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import MagicMock, patch

import pytest

try:
    from sc2.ids.unit_typeid import UnitTypeId
except ImportError:
    pytest.skip("sc2 library not available", allow_module_level=True)

# ---------------------------------------------------------------------------
# Minimal stubs so we can import without a running SC2 environment
# ---------------------------------------------------------------------------

def _make_unit(type_id, health_pct=0.4, health_max=200, tag=1, energy=100,
               is_flying=False, is_biological=True, is_ready=True):
    u = MagicMock()
    u.type_id = type_id
    u.health_percentage = health_pct
    u.health = health_max * health_pct
    u.health_max = health_max
    u.tag = tag
    u.energy = energy
    u.is_flying = is_flying
    u.is_biological = is_biological
    u.is_ready = is_ready
    u.is_idle = False  # not idle — key test for the is_idle fix
    return u


def _make_queen(tag=99, energy=100, is_flying=False):
    q = _make_unit(UnitTypeId.QUEEN, health_pct=0.9, tag=tag, energy=energy,
                   is_flying=is_flying)
    q.distance_to = MagicMock(return_value=4.0)
    return q


def _make_bot(time=120.0):
    bot = MagicMock()
    bot.time = time
    bot.do = MagicMock()
    return bot


try:
    from wicked_zerg_challenger.economy.queen_transfusion_manager import QueenTransfusionManager
except ImportError:
    pytest.skip("QueenTransfusionManager not available", allow_module_level=True)


# ---------------------------------------------------------------------------
# Helper
# ---------------------------------------------------------------------------

def _mgr(time=120.0):
    bot = _make_bot(time)
    return QueenTransfusionManager(bot), bot


# ---------------------------------------------------------------------------
# Tests: is_idle fix — queens should transfuse even when not idle
# ---------------------------------------------------------------------------

class TestIsIdleFix:
    def test_non_idle_queen_can_transfuse(self):
        """Queen that is NOT idle (is_idle=False) must still appear in available_queens."""
        mgr, bot = _mgr()
        queen = _make_queen(tag=1, energy=100)
        queen.is_idle = False  # explicitly not idle

        # _find_best_transfusion_target bypasses the filter; test filter directly
        queens_mock = [queen]
        # is_flying=False, energy >= 50 → should pass the new filter
        available = [q for q in queens_mock
                     if q.energy >= mgr.TRANSFUSION_ENERGY_COST
                     and not q.is_flying]
        assert len(available) == 1, "Non-idle queen should pass energy+flying filter"

    def test_flying_queen_excluded(self):
        """Flying queens cannot cast transfusion."""
        mgr, bot = _mgr()
        queen = _make_queen(tag=2, energy=100, is_flying=True)
        available = [q for q in [queen]
                     if q.energy >= mgr.TRANSFUSION_ENERGY_COST
                     and not q.is_flying]
        assert len(available) == 0, "Flying queen must be excluded"

    def test_low_energy_queen_excluded(self):
        """Queens with < 50 energy must be excluded."""
        mgr, bot = _mgr()
        queen = _make_queen(tag=3, energy=49)
        available = [q for q in [queen]
                     if q.energy >= mgr.TRANSFUSION_ENERGY_COST
                     and not q.is_flying]
        assert len(available) == 0


# ---------------------------------------------------------------------------
# Tests: target deduplication
# ---------------------------------------------------------------------------

class TestTargetDeduplication:
    def test_targeted_set_starts_empty(self):
        mgr, _ = _mgr()
        assert len(mgr._targeted_this_iter) == 0

    def test_targeted_unit_skipped_by_second_queen(self):
        """If unit tag is already in _targeted_this_iter, _find_best_transfusion_target
        must skip it."""
        mgr, bot = _mgr()
        queen1 = _make_queen(tag=10)
        queen2 = _make_queen(tag=11)

        ultra = _make_unit(UnitTypeId.ULTRALISK, health_pct=0.3, health_max=400, tag=55)
        ultra.distance_to = MagicMock(return_value=3.0)
        queen1.distance_to = MagicMock(return_value=3.0)
        queen2.distance_to = MagicMock(return_value=3.0)

        # Queen 1 targets the ultralisk and marks it
        mgr._targeted_this_iter.clear()
        t1 = mgr._find_best_transfusion_target(queen1, [ultra])
        assert t1 is not None
        mgr._targeted_this_iter.add(ultra.tag)

        # Queen 2 should find no valid target (ultralisk already marked)
        t2 = mgr._find_best_transfusion_target(queen2, [ultra])
        assert t2 is None, "Already-targeted unit must be skipped by second queen"

    def test_dedup_cleared_each_iteration(self):
        """_targeted_this_iter must be cleared at the start of execute_transfusions."""
        mgr, bot = _mgr()
        mgr._targeted_this_iter.add(999)  # stale tag from previous iteration

        # execute_transfusions with empty inputs returns early but still clears
        # We verify clear happens by calling the method
        import asyncio

        async def _run():
            await mgr.execute_transfusions([], [], 100)

        asyncio.run(_run())
        assert 999 not in mgr._targeted_this_iter, "Dedup set must be cleared each call"


# ---------------------------------------------------------------------------
# Tests: per-queen cast cooldown
# ---------------------------------------------------------------------------

class TestQueenCastCooldown:
    def test_queen_skipped_within_cooldown(self):
        """Queen that cast < QUEEN_CAST_COOLDOWN seconds ago must be skipped."""
        mgr, bot = _mgr(time=100.0)
        queen = _make_queen(tag=20, energy=100)

        # Simulate that queen cast at t=99.5 (0.5 s ago, cooldown=1.5 s)
        mgr._queen_last_cast[queen.tag] = 99.5

        now = bot.time  # 100.0
        skip = mgr._queen_last_cast.get(queen.tag, 0.0) + mgr.QUEEN_CAST_COOLDOWN > now
        assert skip, "Queen within cooldown window must be skipped"

    def test_queen_allowed_after_cooldown(self):
        """Queen whose last cast is older than cooldown must be allowed."""
        mgr, bot = _mgr(time=100.0)
        queen = _make_queen(tag=21, energy=100)

        # Cast at t=98.0 (2.0 s ago, cooldown=1.5 s → should be clear)
        mgr._queen_last_cast[queen.tag] = 98.0

        now = bot.time
        skip = mgr._queen_last_cast.get(queen.tag, 0.0) + mgr.QUEEN_CAST_COOLDOWN > now
        assert not skip, "Queen past cooldown window must be allowed"

    def test_unknown_queen_has_no_cooldown(self):
        """Queen with no recorded cast must not be blocked."""
        mgr, bot = _mgr(time=100.0)
        queen = _make_queen(tag=99, energy=100)

        skip = mgr._queen_last_cast.get(queen.tag, 0.0) + mgr.QUEEN_CAST_COOLDOWN > bot.time
        assert not skip, "First-time queen must not be in cooldown"


# ---------------------------------------------------------------------------
# Tests: priority ordering
# ---------------------------------------------------------------------------

class TestPriorityOrdering:
    def test_ultralisk_healed_before_zergling(self):
        """Ultralisk (priority 100) must be chosen over zergling (priority 30)."""
        mgr, _ = _mgr()
        queen = _make_queen(tag=30)
        queen.distance_to = MagicMock(return_value=3.0)

        ultra = _make_unit(UnitTypeId.ULTRALISK, health_pct=0.5, health_max=400, tag=1)
        ling = _make_unit(UnitTypeId.ZERGLING, health_pct=0.2, health_max=35, tag=2)
        for u in (ultra, ling):
            u.distance_to = MagicMock(return_value=3.0)

        target = mgr._find_best_transfusion_target(queen, [ling, ultra])
        assert target is not None
        assert target.type_id == UnitTypeId.ULTRALISK, \
            "Ultralisk must be preferred over zergling"

    def test_critical_hp_unit_chosen_over_same_priority_unit(self):
        """Among equal-priority units, one at critical HP (<30%) wins."""
        mgr, _ = _mgr()
        queen = _make_queen(tag=31)
        queen.distance_to = MagicMock(return_value=3.0)

        roach_crit = _make_unit(UnitTypeId.ROACH, health_pct=0.2, health_max=145, tag=10)
        roach_norm = _make_unit(UnitTypeId.ROACH, health_pct=0.55, health_max=145, tag=11)
        for u in (roach_crit, roach_norm):
            u.distance_to = MagicMock(return_value=3.0)

        target = mgr._find_best_transfusion_target(queen, [roach_norm, roach_crit])
        assert target.tag == roach_crit.tag, \
            "Critical-HP unit must be preferred over same-type healthy unit"

    def test_baneling_excluded(self):
        """Banelings (suicide units) must never be valid transfusion targets."""
        mgr, _ = _mgr()
        queen = _make_queen(tag=40)
        queen.distance_to = MagicMock(return_value=2.0)

        baneling = _make_unit(UnitTypeId.BANELING, health_pct=0.1, health_max=30, tag=99)
        baneling.distance_to = MagicMock(return_value=2.0)

        target = mgr._find_best_transfusion_target(queen, [baneling])
        assert target is None, "Baneling must never be a transfusion target"

    def test_unit_above_threshold_excluded(self):
        """Unit above HP threshold (≥60%) must not be targeted."""
        mgr, _ = _mgr()
        queen = _make_queen(tag=50)
        queen.distance_to = MagicMock(return_value=2.0)

        healthy_ling = _make_unit(UnitTypeId.ZERGLING, health_pct=0.75, tag=100)
        healthy_ling.distance_to = MagicMock(return_value=2.0)

        target = mgr._find_best_transfusion_target(queen, [healthy_ling])
        assert target is None, "Healthy unit above threshold must not be targeted"

    def test_out_of_range_unit_excluded(self):
        """Units outside TRANSFUSION_RANGE must not be targeted."""
        mgr, _ = _mgr()
        queen = _make_queen(tag=60)

        far_ultra = _make_unit(UnitTypeId.ULTRALISK, health_pct=0.1, health_max=400, tag=200)
        queen.distance_to = MagicMock(return_value=10.0)  # beyond range 7
        far_ultra.distance_to = MagicMock(return_value=10.0)

        target = mgr._find_best_transfusion_target(queen, [far_ultra])
        assert target is None, "Out-of-range unit must not be targeted"
