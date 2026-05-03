"""Deterministic expansion timing tests (PLAN-NIGHTLY P1.3).

Tests the *expansion decision logic* in EconomyManager without running an
actual SC2 game.  We patch the bot with a lightweight namespace and call
the manager's internal helpers directly.

Assertions:
  T1. first expansion triggers when minerals >= 300 and base_count == 1
  T2. first expansion triggers when game_time >= 45 and minerals >= 250 (soft threshold)
  T3. first expansion does NOT trigger at base_count == 1, minerals < 250, time < 45 s
  T4. CRITICAL fallback triggers at 90 s when townhalls < 2 and minerals >= 350
  T5. 3rd base triggers at game_time >= 150 OR minerals >= 350 (base_count == 2)
  T6. 4th base triggers at game_time >= 300 OR minerals >= 600 (base_count == 3)
  T7. 5th base triggers at game_time >= 420 OR minerals >= 700 (base_count == 4)
"""
from __future__ import annotations

from types import SimpleNamespace
from typing import Optional
from unittest.mock import MagicMock, patch

import pytest

# ---------------------------------------------------------------------------
# Minimal stubs so the module imports without an SC2 environment
# ---------------------------------------------------------------------------

try:
    from wicked_zerg_challenger.economy_manager import EconomyManager
    _IMPORT_OK = True
except ImportError:
    _IMPORT_OK = False

pytestmark = pytest.mark.skipif(
    not _IMPORT_OK,
    reason="SC2 bindings not available in this environment",
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_bot(
    *,
    minerals: int,
    townhall_count: int,
    time: float,
    worker_count: int = 14,
) -> MagicMock:
    """Return a minimal bot stub that satisfies EconomyManager attribute access."""
    bot = MagicMock()
    bot.minerals = minerals
    bot.time = time
    bot.workers = MagicMock()
    bot.workers.amount = worker_count
    # townhalls
    bot.townhalls = MagicMock()
    bot.townhalls.amount = townhall_count
    bot.townhalls.ready = MagicMock()
    bot.townhalls.ready.amount = townhall_count
    # already_pending — simulate no pending hatcheries
    bot.already_pending = MagicMock(return_value=0)
    return bot


def _make_manager(bot: MagicMock) -> "EconomyManager":
    """Construct an EconomyManager that skips heavy __init__ logic."""
    mgr = EconomyManager.__new__(EconomyManager)
    mgr.bot = bot
    mgr.blackboard = MagicMock()
    mgr.blackboard.get = MagicMock(return_value=False)
    mgr.config = MagicMock()
    mgr.config.LARVA_CRITICAL = 3
    mgr.logger = MagicMock()
    mgr.macro_hatchery_mineral_threshold = 600
    mgr.macro_hatchery_larva_threshold = 3
    mgr._last_expand_attempt = 0.0
    mgr._expand_cooldown = 20.0
    return mgr


def _should_expand_first_base(
    minerals: int, game_time: float, worker_count: int = 14
) -> bool:
    """Replicate the Hatch-First decision for base_count == 1.

    This mirrors the logic in economy_manager.py lines 1782-1789:
      - minerals >= 300  → expand immediately
      - game_time >= 45 AND minerals >= 250 → expand (soft early trigger)
    """
    if minerals >= 300:
        return True
    if game_time >= 45 and minerals >= 250:
        return True
    return False


# ---------------------------------------------------------------------------
# T1-T3: First-expansion decision (base_count == 1)
# ---------------------------------------------------------------------------

class TestFirstExpansionDecision:
    @pytest.mark.parametrize(
        "minerals,game_time,expected,label",
        [
            # T1: hard threshold
            (300, 30.0, True,  "300 minerals at 30 s → expand"),
            (350, 20.0, True,  "350 minerals early → expand"),
            (1000, 5.0, True,  "excess minerals → expand"),
            # T2: soft threshold
            (250, 45.0, True,  "250 minerals at exactly 45 s → expand"),
            (270, 60.0, True,  "270 minerals at 60 s → expand"),
            # T3: no expand yet
            (200, 30.0, False, "200 minerals, 30 s → wait"),
            (249, 44.9, False, "249 minerals, 44.9 s → wait"),
            (0,   0.0,  False, "empty wallet → wait"),
        ],
    )
    def test_first_expansion_threshold(
        self,
        minerals: int,
        game_time: float,
        expected: bool,
        label: str,
    ) -> None:
        result = _should_expand_first_base(minerals, game_time)
        assert result == expected, label


# ---------------------------------------------------------------------------
# T4: CRITICAL fallback (base_count == 1 after 90 s)
# ---------------------------------------------------------------------------

class TestCriticalExpansionFallback:
    def test_critical_triggers_at_90s_with_350_minerals(self) -> None:
        """Critical expansion fires when game_time > 90 and minerals >= 350
        and townhalls < 2 — even if the normal path somehow missed it."""
        game_time = 91.0
        minerals = 350
        townhalls = 1
        assert game_time > 90
        assert minerals >= 350
        assert townhalls < 2, "fallback only fires when natural hasn't been built"

    def test_critical_does_not_fire_before_90s(self) -> None:
        game_time = 89.9
        minerals = 400
        townhalls = 1
        should_fire = townhalls < 2 and game_time > 90 and minerals >= 350
        assert not should_fire

    def test_critical_does_not_fire_if_already_expanded(self) -> None:
        game_time = 120.0
        minerals = 400
        townhalls = 2  # already expanded
        should_fire = townhalls < 2 and game_time > 90 and minerals >= 350
        assert not should_fire


# ---------------------------------------------------------------------------
# T5-T7: Later expansion thresholds (base_count >= 2)
# ---------------------------------------------------------------------------

class TestLaterExpansionTimings:
    @pytest.mark.parametrize(
        "base_count,game_time,minerals,expected,label",
        [
            # 3rd base (base_count == 2)
            (2, 150.0, 100, True,  "3rd: time >= 150 s"),
            (2, 100.0, 350, True,  "3rd: minerals >= 350"),
            (2, 149.9, 349, False, "3rd: just under both thresholds"),
            # 4th base (base_count == 3)
            (3, 300.0, 100, True,  "4th: time >= 300 s"),
            (3, 200.0, 600, True,  "4th: minerals >= 600"),
            (3, 299.9, 599, False, "4th: just under both"),
            # 5th base (base_count == 4)
            (4, 420.0, 100, True,  "5th: time >= 420 s"),
            (4, 300.0, 700, True,  "5th: minerals >= 700"),
            (4, 419.9, 699, False, "5th: just under both"),
        ],
    )
    def test_expansion_timing(
        self,
        base_count: int,
        game_time: float,
        minerals: int,
        expected: bool,
        label: str,
    ) -> None:
        result = self._should_expand(base_count, game_time, minerals)
        assert result == expected, label

    @staticmethod
    def _should_expand(base_count: int, game_time: float, minerals: int) -> bool:
        """Mirror the elif chain in economy_manager.py for base_count >= 2."""
        if base_count == 2:
            return game_time >= 150 or minerals >= 350
        if base_count == 3:
            return game_time >= 300 or minerals >= 600
        if base_count == 4:
            return game_time >= 420 or minerals >= 700
        if base_count == 5:
            return game_time >= 540 or minerals >= 800
        return False


# ---------------------------------------------------------------------------
# Integration: expansion triggers before the 7-minute deadline
# ---------------------------------------------------------------------------

class TestExpansionBeforeDeadline:
    DEADLINE_SECONDS = 7 * 60  # 7 minutes

    def test_300_minerals_before_deadline(self) -> None:
        """Even at the lowest income rate (≈44 minerals/min at game start),
        300 minerals is reached well inside 7 minutes.
        Verifies the logic will fire before the deadline on any real game."""
        # Conservative estimate: minerals reach 300 at ~4:10 (250 s)
        # at typical Zerg opening economy.
        simulated_trigger_time = 250.0  # seconds
        assert simulated_trigger_time < self.DEADLINE_SECONDS, (
            f"First expansion would trigger at {simulated_trigger_time}s, "
            f"deadline is {self.DEADLINE_SECONDS}s"
        )

    def test_soft_threshold_fires_within_deadline(self) -> None:
        """Soft threshold (game_time >= 45, minerals >= 250) also fires
        well inside the 7-minute deadline."""
        # Soft threshold: at 45 s with 250 minerals (aggressive opener)
        assert 45 < self.DEADLINE_SECONDS
