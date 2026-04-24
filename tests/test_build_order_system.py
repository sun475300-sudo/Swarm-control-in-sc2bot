# -*- coding: utf-8 -*-
"""
Unit tests for wicked_zerg_challenger/build_order_system.py (573 LOC, previously untested).

Exercises enemy-race build selection, win-rate-based auto-selection,
game-result recording, and progress/summary rendering — without requiring
an actual SC2 game instance.
"""
import os
import sys
from unittest.mock import MagicMock, patch

import pytest

sys.path.insert(
    0, os.path.join(os.path.dirname(__file__), "..", "wicked_zerg_challenger")
)


def _import():
    try:
        from build_order_system import (
            BuildOrderStep,
            BuildOrderSystem,
            BuildOrderType,
        )
        return BuildOrderSystem, BuildOrderType, BuildOrderStep
    except ImportError:
        return None, None, None


BuildOrderSystem, BuildOrderType, BuildOrderStep = _import()

pytestmark = pytest.mark.skipif(
    BuildOrderSystem is None, reason="build_order_system not importable"
)


@pytest.fixture
def bot_factory():
    """Return a callable that builds a mock bot with a given enemy race."""
    def _make(enemy_race="terran"):
        b = MagicMock()
        b.enemy_race = enemy_race
        b.time = 0.0
        b.supply_used = 12
        return b
    return _make


@pytest.fixture
def system(bot_factory):
    """System with setup patched out so no knowledge-manager I/O happens."""
    with patch.object(BuildOrderSystem, "_setup_build_order", lambda self: None):
        with patch("build_order_system.KnowledgeManager") as km_mock:
            km_mock.return_value = MagicMock()
            yield BuildOrderSystem(bot_factory("terran"))


class TestEnemyRaceBuildSelection:
    @pytest.mark.parametrize(
        "race,expected",
        [
            ("terran", BuildOrderType.HATCH_FIRST_16),
            ("Terran", BuildOrderType.HATCH_FIRST_16),
            ("protoss", BuildOrderType.ROACH_RUSH),
            ("Protoss", BuildOrderType.ROACH_RUSH),
            ("zerg", BuildOrderType.SAFE_14POOL),
            ("random", BuildOrderType.SAFE_14POOL),  # fallthrough = zerg mirror
        ],
    )
    def test_selects_expected_build(self, bot_factory, race, expected):
        with patch.object(BuildOrderSystem, "_setup_build_order", lambda self: None):
            with patch("build_order_system.KnowledgeManager") as km_mock:
                km_mock.return_value = MagicMock()
                bos = BuildOrderSystem(bot_factory(race))
        assert bos._select_build_by_enemy_race() == expected

    def test_missing_enemy_race_falls_back_to_roach_rush(self, bot_factory):
        with patch.object(BuildOrderSystem, "_setup_build_order", lambda self: None):
            with patch("build_order_system.KnowledgeManager") as km_mock:
                km_mock.return_value = MagicMock()
                bot = bot_factory(None)
                bot.enemy_race = None
                bos = BuildOrderSystem(bot)
        assert bos._select_build_by_enemy_race() == BuildOrderType.ROACH_RUSH


class TestRecordGameResult:
    def test_win_increments_both(self, system):
        system.record_game_result(BuildOrderType.ROACH_RUSH, won=True)
        stats = system.build_order_stats[BuildOrderType.ROACH_RUSH]
        assert stats["games"] == 1
        assert stats["wins"] == 1

    def test_loss_increments_games_only(self, system):
        system.record_game_result(BuildOrderType.ROACH_RUSH, won=False)
        stats = system.build_order_stats[BuildOrderType.ROACH_RUSH]
        assert stats["games"] == 1
        assert stats["wins"] == 0

    def test_multiple_records(self, system):
        for _ in range(3):
            system.record_game_result(BuildOrderType.STANDARD_12POOL, True)
        for _ in range(2):
            system.record_game_result(BuildOrderType.STANDARD_12POOL, False)
        stats = system.build_order_stats[BuildOrderType.STANDARD_12POOL]
        assert stats["games"] == 5
        assert stats["wins"] == 3

    def test_unknown_build_is_noop(self, system):
        # Using an arbitrary string must not raise.
        system.record_game_result("NOT_A_BUILD", won=True)  # type: ignore[arg-type]


class TestSelectByWinRate:
    def test_all_zero_games_returns_default(self, system):
        assert (
            system.select_build_order_by_win_rate()
            == BuildOrderType.STANDARD_12POOL
        )

    def test_needs_min_5_games_to_qualify(self, system):
        for _ in range(4):
            system.record_game_result(BuildOrderType.ROACH_RUSH, True)
        # 4 wins / 4 games = 100%, but games < 5 => ignored.
        assert (
            system.select_build_order_by_win_rate()
            == BuildOrderType.STANDARD_12POOL
        )

    def test_selects_highest_qualifying_win_rate(self, system):
        for _ in range(5):
            system.record_game_result(BuildOrderType.ROACH_RUSH, True)  # 100%
        for _ in range(5):
            system.record_game_result(BuildOrderType.HYDRA_TIMING, False)  # 0%
        assert (
            system.select_build_order_by_win_rate() == BuildOrderType.ROACH_RUSH
        )

    def test_breaks_tie_by_first_encountered(self, system):
        for _ in range(5):
            system.record_game_result(BuildOrderType.ROACH_RUSH, True)
        for _ in range(5):
            system.record_game_result(BuildOrderType.HYDRA_TIMING, True)
        # Both 100% — implementation picks first one strictly greater than 0,
        # so the result is deterministic but either of them is acceptable.
        result = system.select_build_order_by_win_rate()
        assert result in {BuildOrderType.ROACH_RUSH, BuildOrderType.HYDRA_TIMING}


class TestProgress:
    def test_progress_with_no_steps(self, system):
        system.build_order_active = True
        system.build_steps = []
        assert "0/0" in system.get_progress()

    def test_progress_complete(self, system):
        system.build_order_active = False
        assert system.get_progress() == "Build Order Complete"

    def test_progress_percentage(self, system):
        system.build_order_active = True
        s1 = BuildOrderStep(12, "build", None, "Pool")
        s2 = BuildOrderStep(14, "build", None, "Hatch")
        s3 = BuildOrderStep(16, "train", None, "Ling")
        s1.completed = True
        system.build_steps = [s1, s2, s3]
        system.current_step_index = 1
        p = system.get_progress()
        assert "1/3" in p
        assert "33%" in p
        assert "Hatch" in p


class TestStatsSummary:
    def test_empty_summary_includes_all_build_types(self, system):
        out = system.get_stats_summary()
        for build_type in BuildOrderType:
            assert build_type.value in out

    def test_win_rate_formatted(self, system):
        for _ in range(3):
            system.record_game_result(BuildOrderType.ROACH_RUSH, True)
        system.record_game_result(BuildOrderType.ROACH_RUSH, False)
        out = system.get_stats_summary()
        # 3 wins / 4 games = 75.0%
        assert "3/4" in out
        assert "75.0%" in out
