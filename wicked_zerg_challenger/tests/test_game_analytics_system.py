# -*- coding: utf-8 -*-
"""
Unit tests for game_analytics_system.

Tests cover:
- DefeatReason enum values
- GameAnalytics.__init__ defaults
- record_game: win counting, race stats, map stats, defeat reason tally,
  timing updates
- _analyze_defeat_reason: covers each branch
- _update_timing_stats: shortest/longest/avg + EMA for pool/expand
- get_summary structure
- get_race_specific_advice: data-poor branch + thresholds
- save/load roundtrip via tmp paths
"""

import json
import os
import shutil
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from game_analytics_system import DefeatReason, GameAnalytics


def _make_analytics(tmpdir):
    """Build a fresh GameAnalytics with save paths inside `tmpdir`."""
    a = GameAnalytics()
    a.save_path = Path(tmpdir) / "stats.json"
    a.detailed_log_path = Path(tmpdir) / "detailed.jsonl"
    return a


class TestDefeatReasonEnum(unittest.TestCase):
    def test_all_values_unique_strings(self):
        values = [r.value for r in DefeatReason]
        self.assertEqual(len(values), len(set(values)))

    def test_unknown_present(self):
        self.assertIn(DefeatReason.UNKNOWN, list(DefeatReason))


class TestInit(unittest.TestCase):
    def setUp(self):
        self.tmpdir = tempfile.mkdtemp()

    def tearDown(self):
        shutil.rmtree(self.tmpdir, ignore_errors=True)

    def test_defaults(self):
        a = _make_analytics(self.tmpdir)
        self.assertEqual(a.total_games, 0)
        self.assertEqual(a.total_wins, 0)
        # All three races present
        for r in ("Terran", "Protoss", "Zerg"):
            self.assertIn(r, a.race_stats)
        # All defeat reasons initialized to 0
        for r in DefeatReason:
            self.assertEqual(a.defeat_reasons[r.value], 0)
        self.assertEqual(a.timing_stats["avg_game_time"], 0.0)
        self.assertEqual(a.timing_stats["longest_game"], 0.0)


class TestAnalyzeDefeatReason(unittest.TestCase):
    def setUp(self):
        self.tmpdir = tempfile.mkdtemp()
        self.a = _make_analytics(self.tmpdir)

    def tearDown(self):
        shutil.rmtree(self.tmpdir, ignore_errors=True)

    def test_early_rush(self):
        self.assertEqual(
            self.a._analyze_defeat_reason(120, {}),
            DefeatReason.EARLY_RUSH,
        )

    def test_economy_collapse(self):
        # Game time 200, worker_count below 16
        self.assertEqual(
            self.a._analyze_defeat_reason(200, {"worker_count": 10}),
            DefeatReason.ECONOMY_COLLAPSE,
        )

    def test_army_wipeout(self):
        self.assertEqual(
            self.a._analyze_defeat_reason(
                500, {"worker_count": 50, "army_count": 2, "base_count": 3}
            ),
            DefeatReason.ARMY_WIPEOUT,
        )

    def test_expansion_failure(self):
        self.assertEqual(
            self.a._analyze_defeat_reason(
                500, {"worker_count": 50, "army_count": 30, "base_count": 1}
            ),
            DefeatReason.EXPANSION_FAILURE,
        )

    def test_timeout(self):
        self.assertEqual(
            self.a._analyze_defeat_reason(
                1500, {"worker_count": 50, "army_count": 30, "base_count": 5}
            ),
            DefeatReason.TIMEOUT,
        )

    def test_unknown(self):
        # Mid-game, decent stats — falls through
        self.assertEqual(
            self.a._analyze_defeat_reason(
                500, {"worker_count": 50, "army_count": 30, "base_count": 3}
            ),
            DefeatReason.UNKNOWN,
        )


class TestRecordGame(unittest.TestCase):
    def setUp(self):
        self.tmpdir = tempfile.mkdtemp()
        self.a = _make_analytics(self.tmpdir)

    def tearDown(self):
        shutil.rmtree(self.tmpdir, ignore_errors=True)

    def test_records_a_win(self):
        self.a.record_game(
            game_id=1,
            map_name="MapA",
            opponent_race="Terran",
            difficulty="Hard",
            result="VICTORY",
            game_time=600.0,
        )
        self.assertEqual(self.a.total_games, 1)
        self.assertEqual(self.a.total_wins, 1)
        self.assertEqual(self.a.race_stats["Terran"]["wins"], 1)
        self.assertEqual(self.a.map_stats["MapA"]["wins"], 1)
        # No defeat reason logged on a win
        for v in self.a.defeat_reasons.values():
            self.assertEqual(v, 0)

    def test_records_a_loss_with_auto_defeat_reason(self):
        # 100s game time -> EARLY_RUSH branch
        self.a.record_game(
            game_id=2,
            map_name="MapB",
            opponent_race="Protoss",
            difficulty="Hard",
            result="DEFEAT",
            game_time=100.0,
        )
        self.assertEqual(self.a.total_games, 1)
        self.assertEqual(self.a.total_wins, 0)
        self.assertEqual(self.a.defeat_reasons[DefeatReason.EARLY_RUSH.value], 1)

    def test_records_a_loss_with_explicit_defeat_reason(self):
        self.a.record_game(
            game_id=3,
            map_name="MapC",
            opponent_race="Zerg",
            difficulty="Medium",
            result="LOSS",
            game_time=900.0,
            defeat_reason=DefeatReason.HARASSMENT,
        )
        self.assertEqual(self.a.defeat_reasons[DefeatReason.HARASSMENT.value], 1)

    def test_average_time_updated(self):
        self.a.record_game(1, "M", "Zerg", "Hard", "VICTORY", 600.0)
        self.a.record_game(2, "M", "Zerg", "Hard", "VICTORY", 800.0)
        # Average should be 700.0
        self.assertAlmostEqual(self.a.race_stats["Zerg"]["avg_time"], 700.0)

    def test_unknown_race_skips_race_stats_update(self):
        # Race not in {Terran, Protoss, Zerg}
        self.a.record_game(1, "M", "Random", "Hard", "VICTORY", 600.0)
        # total_games still increments
        self.assertEqual(self.a.total_games, 1)


class TestUpdateTimingStats(unittest.TestCase):
    def setUp(self):
        self.tmpdir = tempfile.mkdtemp()
        self.a = _make_analytics(self.tmpdir)

    def tearDown(self):
        shutil.rmtree(self.tmpdir, ignore_errors=True)

    def test_updates_shortest_and_longest(self):
        # need total_games > 0 for the avg calculation to be meaningful;
        # _update_timing_stats divides by self.total_games
        self.a.total_games = 1
        self.a._update_timing_stats(500.0, {})
        self.assertEqual(self.a.timing_stats["shortest_game"], 500.0)
        self.assertEqual(self.a.timing_stats["longest_game"], 500.0)

        self.a.total_games = 2
        self.a._update_timing_stats(800.0, {})
        self.assertEqual(self.a.timing_stats["shortest_game"], 500.0)
        self.assertEqual(self.a.timing_stats["longest_game"], 800.0)

    def test_pool_timing_seeds_then_emas(self):
        self.a.total_games = 1
        self.a._update_timing_stats(500.0, {"pool_timing": 60.0})
        self.assertEqual(self.a.timing_stats["avg_pool_timing"], 60.0)
        # second update applies EMA
        self.a.total_games = 2
        self.a._update_timing_stats(500.0, {"pool_timing": 80.0})
        # 60*0.9 + 80*0.1 = 62.0
        self.assertAlmostEqual(self.a.timing_stats["avg_pool_timing"], 62.0)


class TestImprovementSuggestions(unittest.TestCase):
    def setUp(self):
        self.tmpdir = tempfile.mkdtemp()
        self.a = _make_analytics(self.tmpdir)

    def tearDown(self):
        shutil.rmtree(self.tmpdir, ignore_errors=True)

    def test_early_rush_suggestions(self):
        record = {
            "defeat_reason": DefeatReason.EARLY_RUSH.value,
            "game_time": 100,
        }
        suggestions = self.a._get_improvement_suggestions(record)
        self.assertTrue(any("스파인" in s for s in suggestions))

    def test_economy_collapse_suggestions(self):
        record = {
            "defeat_reason": DefeatReason.ECONOMY_COLLAPSE.value,
            "game_time": 200,
        }
        self.assertTrue(self.a._get_improvement_suggestions(record))

    def test_no_match_returns_empty(self):
        record = {"defeat_reason": None, "game_time": 600}
        self.assertEqual(self.a._get_improvement_suggestions(record), [])


class TestRaceSpecificAdvice(unittest.TestCase):
    def setUp(self):
        self.tmpdir = tempfile.mkdtemp()
        self.a = _make_analytics(self.tmpdir)

    def tearDown(self):
        shutil.rmtree(self.tmpdir, ignore_errors=True)

    def test_unknown_race_returns_empty(self):
        self.assertEqual(self.a.get_race_specific_advice("Random"), "")

    def test_data_poor_branch(self):
        # 0 games -> data poor message
        msg = self.a.get_race_specific_advice("Terran")
        self.assertIn("데이터 부족", msg)

    def test_high_winrate_branch(self):
        # 10 games, 8 wins -> 80% winrate
        self.a.race_stats["Terran"]["games"] = 10
        self.a.race_stats["Terran"]["wins"] = 8
        msg = self.a.get_race_specific_advice("Terran")
        self.assertIn("승률 양호", msg)

    def test_low_winrate_branch(self):
        self.a.race_stats["Terran"]["games"] = 10
        self.a.race_stats["Terran"]["wins"] = 1  # 10%
        msg = self.a.get_race_specific_advice("Terran")
        self.assertIn("매우 낮음", msg)


class TestGetSummary(unittest.TestCase):
    def setUp(self):
        self.tmpdir = tempfile.mkdtemp()
        self.a = _make_analytics(self.tmpdir)

    def tearDown(self):
        shutil.rmtree(self.tmpdir, ignore_errors=True)

    def test_summary_with_no_games(self):
        out = self.a.get_summary()
        self.assertIn("0/0승", out)
        self.assertIn("0.0%", out)

    def test_summary_after_a_game(self):
        self.a.record_game(1, "MapA", "Terran", "Hard", "VICTORY", 600.0)
        out = self.a.get_summary()
        self.assertIn("MapA", out)
        self.assertIn("Terran", out)


class TestSaveLoadRoundtrip(unittest.TestCase):
    def setUp(self):
        self.tmpdir = tempfile.mkdtemp()

    def tearDown(self):
        shutil.rmtree(self.tmpdir, ignore_errors=True)

    def test_save_then_load(self):
        a1 = _make_analytics(self.tmpdir)
        a1.total_games = 5
        a1.total_wins = 3
        a1.race_stats["Terran"]["games"] = 2
        a1.race_stats["Terran"]["wins"] = 1
        a1._save_stats()
        self.assertTrue(a1.save_path.exists())

        a2 = GameAnalytics()
        a2.save_path = a1.save_path
        a2.detailed_log_path = a1.detailed_log_path
        a2._load_stats()
        self.assertEqual(a2.total_games, 5)
        self.assertEqual(a2.total_wins, 3)
        self.assertEqual(a2.race_stats["Terran"]["games"], 2)

    def test_load_handles_missing_file(self):
        a = _make_analytics(self.tmpdir)
        # File definitely doesn't exist
        a.save_path = Path(self.tmpdir) / "nonexistent.json"
        a._load_stats()
        # Should not raise, defaults preserved
        self.assertEqual(a.total_games, 0)

    def test_detailed_log_appends_jsonl(self):
        a = _make_analytics(self.tmpdir)
        a.record_game(1, "MapA", "Terran", "Hard", "VICTORY", 600.0)
        a.record_game(2, "MapA", "Terran", "Hard", "DEFEAT", 200.0)
        with open(a.detailed_log_path, encoding="utf-8") as f:
            lines = f.readlines()
        self.assertEqual(len(lines), 2)
        for line in lines:
            json.loads(line)  # must parse


if __name__ == "__main__":
    unittest.main()
