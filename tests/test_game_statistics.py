# -*- coding: utf-8 -*-
"""
GameStatistics 테스트 - 맵/난이도/종족별 승률 통계
"""

import sys
from pathlib import Path

import pytest

PROJECT_ROOT = Path(__file__).parent.parent
BOT_ROOT = PROJECT_ROOT / "wicked_zerg_challenger"
if str(BOT_ROOT) not in sys.path:
    sys.path.insert(0, str(BOT_ROOT))


@pytest.fixture
def stats(tmp_path):
    from game_statistics import GameStatistics
    return GameStatistics(stats_file=str(tmp_path / "test_stats.json"))


class TestInit:
    def test_empty_stats(self, stats):
        assert stats.stats["total_games"] == 0
        assert stats.stats["total_wins"] == 0
        assert stats.stats["total_losses"] == 0

    def test_empty_categories(self, stats):
        assert stats.stats["by_map"] == {}
        assert stats.stats["by_difficulty"] == {}
        assert stats.stats["by_race"] == {}


class TestRecordGame:
    def test_record_win(self, stats):
        stats.record_game("MapA", "Hard", "Terran", victory=True)
        assert stats.stats["total_games"] == 1
        assert stats.stats["total_wins"] == 1
        assert stats.stats["total_losses"] == 0

    def test_record_loss(self, stats):
        stats.record_game("MapA", "Hard", "Terran", victory=False)
        assert stats.stats["total_losses"] == 1

    def test_by_map(self, stats):
        stats.record_game("Acropolis", "VeryHard", "Zerg", victory=True)
        assert stats.stats["by_map"]["Acropolis"]["wins"] == 1

    def test_by_difficulty(self, stats):
        stats.record_game("M", "Hard", "Terran", victory=True)
        assert stats.stats["by_difficulty"]["Hard"]["wins"] == 1

    def test_by_race(self, stats):
        stats.record_game("M", "Hard", "Protoss", victory=False)
        assert stats.stats["by_race"]["Protoss"]["losses"] == 1

    def test_accumulate(self, stats):
        stats.record_game("M", "Hard", "Terran", victory=True)
        stats.record_game("M", "Hard", "Terran", victory=False)
        stats.record_game("M", "Hard", "Terran", victory=True)
        assert stats.stats["total_games"] == 3
        assert stats.stats["total_wins"] == 2
        assert stats.stats["total_losses"] == 1

    def test_combined_keys(self, stats):
        stats.record_game("MapA", "Hard", "Terran", victory=True)
        assert "MapA_Hard" in stats.stats["by_map_difficulty"]
        assert "MapA_Terran" in stats.stats["by_map_race"]


class TestPersistence:
    def test_save_and_reload(self, tmp_path):
        from game_statistics import GameStatistics
        path = tmp_path / "stats.json"
        s1 = GameStatistics(stats_file=str(path))
        s1.record_game("MapA", "Hard", "Terran", victory=True)
        s1.save_stats()
        s2 = GameStatistics(stats_file=str(path))
        assert s2.stats["total_games"] == 1
        assert s2.stats["total_wins"] == 1


class TestReports:
    def test_print_no_crash(self, stats):
        stats.print_statistics()

    def test_print_with_data(self, stats):
        stats.record_game("M", "Hard", "Terran", victory=True)
        stats.record_game("M", "Hard", "Zerg", victory=False)
        stats.print_statistics()

    def test_get_streak(self, stats):
        stats.record_game("M", "Hard", "Terran", victory=True)
        result = stats.get_streak()
        assert isinstance(result, dict)
