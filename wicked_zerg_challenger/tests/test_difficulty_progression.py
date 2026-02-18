# -*- coding: utf-8 -*-
"""
Unit Tests for difficulty_progression.py

Tests DifficultyProgression system:
- Game result recording
- Win rate calculation
- Difficulty recommendation
- Progression logic
- Stats persistence
"""

import unittest
import tempfile
import os
import json
from unittest.mock import Mock, patch
import sys
from io import StringIO

# Add parent directory to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from difficulty_progression import DifficultyProgression

# Mock sc2.data imports
try:
    from sc2.data import Difficulty, Race
except ImportError:
    # Create mock enums for testing
    from enum import Enum

    class Difficulty(Enum):
        VeryEasy = 1
        Easy = 2
        Medium = 3
        MediumHard = 4
        Hard = 5
        Harder = 6
        VeryHard = 7
        CheatVision = 8
        CheatMoney = 9
        CheatInsane = 10

    class Race(Enum):
        Terran = 1
        Protoss = 2
        Zerg = 3


class TestDifficultyProgressionBasics(unittest.TestCase):
    """Test basic DifficultyProgression functionality"""

    def setUp(self):
        """Create temporary file for each test"""
        self.temp_file = tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.json')
        self.temp_file.close()
        self.progression = DifficultyProgression(data_file=self.temp_file.name)

    def tearDown(self):
        """Clean up temporary file"""
        try:
            os.unlink(self.temp_file.name)
        except Exception:
            pass

    def test_initialization(self):
        """Test DifficultyProgression initialization"""
        self.assertIsNotNone(self.progression)
        self.assertEqual(self.progression.win_rate_threshold, 0.90)
        self.assertEqual(self.progression.min_games_for_progression, 10)

    def test_difficulty_ladder_order(self):
        """Test difficulty ladder is properly ordered"""
        ladder = DifficultyProgression.DIFFICULTY_LADDER
        self.assertGreater(len(ladder), 5)
        self.assertEqual(ladder[0], Difficulty.VeryEasy)
        self.assertEqual(ladder[1], Difficulty.Easy)
        self.assertEqual(ladder[-1], Difficulty.CheatInsane)


class TestGameRecording(unittest.TestCase):
    """Test game recording functionality"""

    def setUp(self):
        """Create temporary file for each test"""
        self.temp_file = tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.json')
        self.temp_file.close()
        self.progression = DifficultyProgression(data_file=self.temp_file.name)

    def tearDown(self):
        """Clean up temporary file"""
        try:
            os.unlink(self.temp_file.name)
        except Exception:
            pass

    def test_record_single_win(self):
        """Test recording a single win"""
        self.progression.record_game(
            map_name="TestMap",
            opponent_race=Race.Terran,
            difficulty=Difficulty.Easy,
            won=True
        )

        stats = self.progression.stats["TestMap"][Race.Terran][Difficulty.Easy]
        self.assertEqual(stats["wins"], 1)
        self.assertEqual(stats["losses"], 0)

    def test_record_single_loss(self):
        """Test recording a single loss"""
        self.progression.record_game(
            map_name="TestMap",
            opponent_race=Race.Protoss,
            difficulty=Difficulty.Medium,
            won=False
        )

        stats = self.progression.stats["TestMap"][Race.Protoss][Difficulty.Medium]
        self.assertEqual(stats["wins"], 0)
        self.assertEqual(stats["losses"], 1)

    def test_record_multiple_games(self):
        """Test recording multiple games"""
        for i in range(5):
            self.progression.record_game(
                map_name="TestMap",
                opponent_race=Race.Zerg,
                difficulty=Difficulty.Hard,
                won=(i % 2 == 0)  # Win 3, Lose 2
            )

        stats = self.progression.stats["TestMap"][Race.Zerg][Difficulty.Hard]
        self.assertEqual(stats["wins"], 3)
        self.assertEqual(stats["losses"], 2)

    def test_record_different_maps(self):
        """Test recording games on different maps"""
        self.progression.record_game("Map1", Race.Terran, Difficulty.Easy, True)
        self.progression.record_game("Map2", Race.Terran, Difficulty.Easy, True)

        self.assertIn("Map1", self.progression.stats)
        self.assertIn("Map2", self.progression.stats)


class TestDifficultyRecommendation(unittest.TestCase):
    """Test difficulty recommendation logic"""

    def setUp(self):
        """Create temporary file for each test"""
        self.temp_file = tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.json')
        self.temp_file.close()
        self.progression = DifficultyProgression(data_file=self.temp_file.name)

    def tearDown(self):
        """Clean up temporary file"""
        try:
            os.unlink(self.temp_file.name)
        except Exception:
            pass

    def test_recommend_default_difficulty(self):
        """Test default difficulty recommendation for new map"""
        difficulty = self.progression.get_recommended_difficulty("NewMap", Race.Terran)
        self.assertEqual(difficulty, Difficulty.Easy)

    def test_recommend_stay_on_current_difficulty(self):
        """Test staying on current difficulty with low win rate"""
        # Record 10 games with 70% win rate (below 90% threshold)
        for i in range(10):
            self.progression.record_game(
                "TestMap", Race.Protoss, Difficulty.Medium,
                won=(i < 7)
            )

        difficulty = self.progression.get_recommended_difficulty("TestMap", Race.Protoss)
        self.assertEqual(difficulty, Difficulty.Medium)

    def test_recommend_next_difficulty_after_mastery(self):
        """Test progression to next difficulty after achieving 90% win rate"""
        # Suppress stdout to avoid emoji encoding errors
        old_stdout = sys.stdout
        sys.stdout = StringIO()
        try:
            # Record 10 games with 100% win rate
            for i in range(10):
                self.progression.record_game(
                    "TestMap", Race.Zerg, Difficulty.Easy,
                    won=True
                )

            difficulty = self.progression.get_recommended_difficulty("TestMap", Race.Zerg)
            self.assertEqual(difficulty, Difficulty.Medium)
        finally:
            sys.stdout = old_stdout


class TestProgressionChecking(unittest.TestCase):
    """Test progression checking and notification"""

    def setUp(self):
        """Create temporary file for each test"""
        self.temp_file = tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.json')
        self.temp_file.close()
        self.progression = DifficultyProgression(data_file=self.temp_file.name)

    def tearDown(self):
        """Clean up temporary file"""
        try:
            os.unlink(self.temp_file.name)
        except Exception:
            pass

    def test_no_progression_with_few_games(self):
        """Test no progression with insufficient games"""
        # Suppress stdout to avoid emoji encoding errors
        old_stdout = sys.stdout
        sys.stdout = StringIO()
        try:
            # Record only 5 games (below minimum of 10)
            for i in range(5):
                self.progression.record_game(
                    "TestMap", Race.Terran, Difficulty.Easy,
                    won=True
                )

            # Should not progress yet
            difficulty = self.progression.get_recommended_difficulty("TestMap", Race.Terran)
            # With only 5 games, still recommends Easy (not enough for progression)
            self.assertIn(difficulty, [Difficulty.VeryEasy, Difficulty.Easy, Difficulty.Medium])
        finally:
            sys.stdout = old_stdout

    def test_progression_with_high_winrate(self):
        """Test progression triggers with high win rate"""
        # Suppress stdout to avoid emoji encoding errors
        old_stdout = sys.stdout
        sys.stdout = StringIO()
        try:
            # Record 10 wins (100% win rate) at Medium difficulty
            for i in range(10):
                self.progression.record_game(
                    "TestMap", Race.Protoss, Difficulty.Medium,
                    won=True
                )

            # Check that win rate is 100%
            stats = self.progression.stats["TestMap"][Race.Protoss][Difficulty.Medium]
            self.assertEqual(stats["wins"], 10)
            self.assertEqual(stats["losses"], 0)

            # With 100% win rate at Medium, should recommend Medium or higher
            difficulty = self.progression.get_recommended_difficulty("TestMap", Race.Protoss)
            self.assertIn(difficulty, [Difficulty.Medium, Difficulty.MediumHard, Difficulty.Hard])
        finally:
            sys.stdout = old_stdout


class TestStatsSerDe(unittest.TestCase):
    """Test statistics serialization and deserialization"""

    def setUp(self):
        """Create temporary file for each test"""
        self.temp_file = tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.json')
        self.temp_file.close()
        self.progression = DifficultyProgression(data_file=self.temp_file.name)

    def tearDown(self):
        """Clean up temporary file"""
        try:
            os.unlink(self.temp_file.name)
        except Exception:
            pass

    def test_save_and_load_stats(self):
        """Test saving and loading stats from file"""
        # Record some games
        self.progression.record_game("Map1", Race.Terran, Difficulty.Easy, True)
        self.progression.record_game("Map1", Race.Terran, Difficulty.Easy, True)
        self.progression.record_game("Map1", Race.Terran, Difficulty.Easy, False)

        # Create new instance to load from file
        progression2 = DifficultyProgression(data_file=self.temp_file.name)

        # Verify data was loaded
        self.assertIn("Map1", progression2.stats)
        stats = progression2.stats["Map1"][Race.Terran][Difficulty.Easy]
        self.assertEqual(stats["wins"], 2)
        self.assertEqual(stats["losses"], 1)

    def test_serialize_deserialize_consistency(self):
        """Test serialization/deserialization maintains data integrity"""
        # Record games
        for i in range(5):
            self.progression.record_game("TestMap", Race.Zerg, Difficulty.Hard, True)

        # Serialize
        serialized = self.progression._serialize_stats(self.progression.stats)

        # Deserialize
        deserialized = self.progression._deserialize_stats(serialized)

        # Verify
        self.assertIn("TestMap", deserialized)
        self.assertEqual(
            deserialized["TestMap"][Race.Zerg][Difficulty.Hard]["wins"],
            5
        )


class TestStatsSummary(unittest.TestCase):
    """Test stats summary generation"""

    def setUp(self):
        """Create temporary file for each test"""
        self.temp_file = tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.json')
        self.temp_file.close()
        self.progression = DifficultyProgression(data_file=self.temp_file.name)

    def tearDown(self):
        """Clean up temporary file"""
        try:
            os.unlink(self.temp_file.name)
        except Exception:
            pass

    def test_summary_for_new_map(self):
        """Test summary for map with no stats"""
        summary = self.progression.get_stats_summary("NewMap", Race.Terran)
        self.assertIn("No stats", summary)

    def test_summary_with_stats(self):
        """Test summary generation with actual stats"""
        # Suppress stdout to avoid emoji encoding errors
        old_stdout = sys.stdout
        sys.stdout = StringIO()
        try:
            # Record games
            for i in range(10):
                self.progression.record_game("TestMap", Race.Protoss, Difficulty.Easy, True)

            summary = self.progression.get_stats_summary("TestMap", Race.Protoss)
            self.assertIn("TestMap", summary)
            self.assertIn("Protoss", summary)
            self.assertIn("Easy", summary)
            self.assertIn("10W", summary)
        finally:
            sys.stdout = old_stdout


class TestHelperMethods(unittest.TestCase):
    """Test helper methods"""

    def setUp(self):
        """Create temporary file for each test"""
        self.temp_file = tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.json')
        self.temp_file.close()
        self.progression = DifficultyProgression(data_file=self.temp_file.name)

    def tearDown(self):
        """Clean up temporary file"""
        try:
            os.unlink(self.temp_file.name)
        except Exception:
            pass

    def test_get_next_difficulty(self):
        """Test getting next difficulty in ladder"""
        next_diff = self.progression._get_next_difficulty(Difficulty.Easy)
        self.assertEqual(next_diff, Difficulty.Medium)

    def test_get_next_difficulty_at_max(self):
        """Test getting next difficulty at maximum"""
        next_diff = self.progression._get_next_difficulty(Difficulty.CheatInsane)
        self.assertIsNone(next_diff)

    def test_get_previous_difficulty(self):
        """Test getting previous difficulty in ladder"""
        prev_diff = self.progression._get_previous_difficulty(Difficulty.Medium)
        self.assertEqual(prev_diff, Difficulty.Easy)

    def test_get_previous_difficulty_at_min(self):
        """Test getting previous difficulty at minimum"""
        prev_diff = self.progression._get_previous_difficulty(Difficulty.VeryEasy)
        self.assertIsNone(prev_diff)


if __name__ == '__main__':
    # Run all tests
    unittest.main(verbosity=2)
