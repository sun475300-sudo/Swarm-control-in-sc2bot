# -*- coding: utf-8 -*-
"""
Unit tests for Opponent Modeling System

Tests cover:
- OpponentModel learning and prediction
- Strategy signal detection
- Game history tracking
- Pattern recognition
- Model serialization/deserialization
- Integration with IntelManager
"""

import unittest
from unittest.mock import Mock, MagicMock, patch
import sys
import os
import tempfile
import json

# Add parent directory to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from opponent_modeling import (
    OpponentModeling, OpponentModel, GameHistory,
    OpponentStyle, StrategySignal
)
from sc2.position import Point2


class TestOpponentModel(unittest.TestCase):
    """Test suite for OpponentModel"""

    def setUp(self):
        """Set up test fixtures"""
        self.model = OpponentModel("test_opponent")

    # ==================== Model Initialization Tests ====================

    def test_model_initialization(self):
        """Test opponent model initialization"""
        self.assertEqual(self.model.opponent_id, "test_opponent")
        self.assertEqual(self.model.games_played, 0)
        self.assertEqual(self.model.games_won, 0)
        self.assertEqual(self.model.games_lost, 0)
        self.assertEqual(self.model.dominant_style, OpponentStyle.UNKNOWN)

    def test_model_empty_predictions(self):
        """Test predictions with no historical data"""
        strategy, confidence = self.model.predict_strategy(["early_pool"])
        self.assertEqual(strategy, "unknown")
        self.assertEqual(confidence, 0.0)

    # ==================== Game History Update Tests ====================

    def test_update_from_game_loss(self):
        """Test model update when we lose (opponent wins)"""
        game_history = GameHistory(
            game_id="game_1",
            opponent_race="Zerg",
            opponent_style="aggressive",
            detected_strategy="zerg_12pool",
            build_order_observed=["spawningpool", "hatchery"],
            timing_attacks=[120.0],
            final_composition={"zergling": 30},
            game_result="loss",  # We lost -> opponent won
            game_duration=300.0,
            early_signals=["early_pool", "early_army"],
            tech_progression=[(90.0, "spawningpool")]
        )

        self.model.update_from_game(game_history)

        self.assertEqual(self.model.games_played, 1)
        self.assertEqual(self.model.games_won, 1)  # Opponent won
        self.assertEqual(self.model.games_lost, 0)
        self.assertEqual(self.model.style_counts["aggressive"], 1)
        self.assertEqual(self.model.strategy_frequency["zerg_12pool"], 1)

    def test_update_from_game_win(self):
        """Test model update when we win (opponent loses)"""
        game_history = GameHistory(
            game_id="game_2",
            opponent_race="Terran",
            opponent_style="macro",
            detected_strategy="terran_bio",
            build_order_observed=["barracks", "commandcenter"],
            timing_attacks=[],
            final_composition={"marine": 40, "marauder": 15},
            game_result="win",  # We won -> opponent lost
            game_duration=600.0,
            early_signals=["fast_expand"],
            tech_progression=[(120.0, "barracks"), (180.0, "factory")]
        )

        self.model.update_from_game(game_history)

        self.assertEqual(self.model.games_played, 1)
        self.assertEqual(self.model.games_won, 0)  # Opponent lost
        self.assertEqual(self.model.games_lost, 1)

    def test_dominant_style_calculation(self):
        """Test dominant style after multiple games"""
        # Add 3 aggressive games
        for i in range(3):
            game_history = GameHistory(
                game_id=f"game_{i}",
                opponent_race="Zerg",
                opponent_style="aggressive",
                detected_strategy="zerg_rush",
                build_order_observed=[],
                timing_attacks=[120.0],
                final_composition={},
                game_result="win",
                game_duration=300.0,
                early_signals=[],
                tech_progression=[]
            )
            self.model.update_from_game(game_history)

        # Add 1 macro game
        game_history = GameHistory(
            game_id="game_4",
            opponent_race="Zerg",
            opponent_style="macro",
            detected_strategy="zerg_macro",
            build_order_observed=[],
            timing_attacks=[],
            final_composition={},
            game_result="win",
            game_duration=900.0,
            early_signals=[],
            tech_progression=[]
        )
        self.model.update_from_game(game_history)

        self.assertEqual(self.model.dominant_style, OpponentStyle.AGGRESSIVE)
        self.assertEqual(self.model.games_played, 4)

    # ==================== Strategy Prediction Tests ====================

    def test_strategy_prediction_with_signals(self):
        """Test strategy prediction based on early signals"""
        # Train model with 2 games
        for i in range(2):
            game_history = GameHistory(
                game_id=f"game_{i}",
                opponent_race="Zerg",
                opponent_style="aggressive",
                detected_strategy="zerg_12pool",
                build_order_observed=["spawningpool"],
                timing_attacks=[120.0],
                final_composition={"zergling": 30},
                game_result="win",
                game_duration=300.0,
                early_signals=["early_pool", "early_army"],
                tech_progression=[]
            )
            self.model.update_from_game(game_history)

        # Make prediction
        strategy, confidence = self.model.predict_strategy(["early_pool", "early_army"])

        self.assertEqual(strategy, "zerg_12pool")
        self.assertGreater(confidence, 0.0)

    def test_strategy_prediction_fallback(self):
        """Test fallback to most frequent strategy when no signals match"""
        # Train model with multiple strategies
        for strat in ["terran_bio", "terran_bio", "terran_mech"]:
            game_history = GameHistory(
                game_id=f"game_{strat}",
                opponent_race="Terran",
                opponent_style="mixed",
                detected_strategy=strat,
                build_order_observed=[],
                timing_attacks=[],
                final_composition={},
                game_result="win",
                game_duration=500.0,
                early_signals=["some_signal"],
                tech_progression=[]
            )
            self.model.update_from_game(game_history)

        # Predict with unknown signal
        strategy, confidence = self.model.predict_strategy(["unknown_signal"])

        # Should fall back to most frequent (terran_bio)
        self.assertEqual(strategy, "terran_bio")
        self.assertGreater(confidence, 0.0)

    # ==================== Timing Attack Prediction Tests ====================

    def test_expected_timing_attacks(self):
        """Test expected timing attack prediction"""
        # Add games with consistent timing attacks at 180s
        for i in range(5):
            game_history = GameHistory(
                game_id=f"game_{i}",
                opponent_race="Protoss",
                opponent_style="timing",
                detected_strategy="protoss_timing",
                build_order_observed=[],
                timing_attacks=[180.0],
                final_composition={},
                game_result="win",
                game_duration=400.0,
                early_signals=[],
                tech_progression=[]
            )
            self.model.update_from_game(game_history)

        expected_timings = self.model.get_expected_timing_attacks()

        # Should predict 180s timing
        self.assertIn(180.0, expected_timings)

    def test_no_timing_attacks_expected(self):
        """Test when no consistent timing attacks"""
        # Add games with no timing attacks
        for i in range(3):
            game_history = GameHistory(
                game_id=f"game_{i}",
                opponent_race="Zerg",
                opponent_style="macro",
                detected_strategy="zerg_macro",
                build_order_observed=[],
                timing_attacks=[],
                final_composition={},
                game_result="win",
                game_duration=900.0,
                early_signals=[],
                tech_progression=[]
            )
            self.model.update_from_game(game_history)

        expected_timings = self.model.get_expected_timing_attacks()
        self.assertEqual(len(expected_timings), 0)

    # ==================== Serialization Tests ====================

    def test_model_serialization(self):
        """Test model to_dict serialization"""
        # Add some game history
        game_history = GameHistory(
            game_id="game_1",
            opponent_race="Terran",
            opponent_style="aggressive",
            detected_strategy="terran_rush",
            build_order_observed=["barracks"],
            timing_attacks=[120.0],
            final_composition={"marine": 20},
            game_result="win",
            game_duration=300.0,
            early_signals=["early_army"],
            tech_progression=[]
        )
        self.model.update_from_game(game_history)

        # Serialize
        data = self.model.to_dict()

        # Check structure
        self.assertEqual(data["opponent_id"], "test_opponent")
        self.assertEqual(data["games_played"], 1)
        self.assertIn("style_counts", data)
        self.assertIn("strategy_frequency", data)

    def test_model_deserialization(self):
        """Test model from_dict deserialization"""
        # Create serialized data
        data = {
            "opponent_id": "test_opponent_2",
            "games_played": 3,
            "games_won": 2,
            "games_lost": 1,
            "style_counts": {"aggressive": 2, "macro": 1},
            "dominant_style": "aggressive",
            "strategy_frequency": {"zerg_rush": 2, "zerg_macro": 1},
            "build_order_patterns": [["spawningpool"], ["hatchery", "spawningpool"]],
            "timing_attack_history": [120.0, 150.0],
            "early_signal_correlations": {
                "early_pool": {"zerg_rush": 2}
            },
            "unit_preferences": {"zergling": 60, "roach": 20}
        }

        # Deserialize
        model = OpponentModel.from_dict(data)

        # Verify
        self.assertEqual(model.opponent_id, "test_opponent_2")
        self.assertEqual(model.games_played, 3)
        self.assertEqual(model.games_won, 2)
        self.assertEqual(model.dominant_style, OpponentStyle.AGGRESSIVE)


class TestOpponentModeling(unittest.TestCase):
    """Test suite for OpponentModeling system"""

    def setUp(self):
        """Set up test fixtures"""
        self.bot = Mock()
        self.bot.time = 0.0
        self.bot.iteration = 0
        self.bot.enemy_race = Mock()
        self.bot.enemy_race.name = "Zerg"
        self.bot.start_location = Point2((50, 50))

        # Mock intel manager
        self.intel = Mock()
        self.intel.enemy_tech_buildings = set()
        self.intel.get_enemy_composition = Mock(return_value={})
        self.intel.is_under_attack = Mock(return_value=False)

        # Mock units/structures
        self.bot.enemy_structures = []
        self.bot.enemy_units = []

        # Use temporary file for testing
        self.temp_file = tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.json')
        self.temp_file.close()

        self.modeling = OpponentModeling(
            self.bot,
            intel_manager=self.intel,
            data_file=self.temp_file.name
        )

    def tearDown(self):
        """Clean up test files"""
        if os.path.exists(self.temp_file.name):
            os.unlink(self.temp_file.name)

    # ==================== Initialization Tests ====================

    def test_initialization(self):
        """Test opponent modeling system initialization"""
        self.assertIsNotNone(self.modeling)
        self.assertEqual(len(self.modeling.opponent_models), 0)
        self.assertIsNone(self.modeling.current_opponent_id)

    async def test_on_start_new_opponent(self):
        """Test game start with new opponent"""
        await self.modeling.on_start()

        self.assertIsNotNone(self.modeling.current_opponent_id)
        self.assertEqual(self.modeling.current_opponent_id, "opponent_Zerg")
        self.assertIn("opponent_Zerg", self.modeling.opponent_models)

    async def test_on_start_known_opponent(self):
        """Test game start with known opponent"""
        # Pre-populate model
        model = OpponentModel("opponent_Zerg")
        model.games_played = 5
        model.games_won = 3
        model.games_lost = 2
        self.modeling.opponent_models["opponent_Zerg"] = model

        await self.modeling.on_start()

        self.assertEqual(self.modeling.current_opponent_id, "opponent_Zerg")

    # ==================== Signal Detection Tests ====================

    async def test_detect_fast_expand_signal(self):
        """Test fast expand signal detection"""
        self.bot.time = 100.0

        # Create 2 hatcheries
        mock_hatch1 = Mock()
        mock_hatch1.type_id = Mock()
        mock_hatch1.type_id.name = "HATCHERY"

        mock_hatch2 = Mock()
        mock_hatch2.type_id = Mock()
        mock_hatch2.type_id.name = "HATCHERY"

        self.bot.enemy_structures = [mock_hatch1, mock_hatch2]

        await self.modeling._detect_early_signals(self.bot.time)

        self.assertIn("fast_expand", self.modeling.observed_signals)

    async def test_detect_early_pool_signal(self):
        """Test early pool signal detection"""
        self.bot.time = 90.0

        # Create spawning pool
        mock_pool = Mock()
        mock_pool.type_id = Mock()
        mock_pool.type_id.name = "SPAWNINGPOOL"

        self.bot.enemy_structures = [mock_pool]

        await self.modeling._detect_early_signals(self.bot.time)

        self.assertIn("early_pool", self.modeling.observed_signals)

    async def test_detect_no_natural_signal(self):
        """Test no natural expansion signal"""
        self.bot.time = 150.0

        # Only 1 base
        mock_hatch = Mock()
        mock_hatch.type_id = Mock()
        mock_hatch.type_id.name = "HATCHERY"

        self.bot.enemy_structures = [mock_hatch]

        await self.modeling._detect_early_signals(self.bot.time)

        self.assertIn("no_natural", self.modeling.observed_signals)

    async def test_detect_early_army_signal(self):
        """Test early army signal detection"""
        self.bot.time = 140.0

        # Create army units (15+ supply)
        mock_units = []
        for i in range(15):
            unit = Mock()
            unit.is_worker = False
            unit.supply_cost = 1
            mock_units.append(unit)

        self.bot.enemy_units = mock_units

        await self.modeling._detect_early_signals(self.bot.time)

        self.assertIn("early_army", self.modeling.observed_signals)

    # ==================== Timing Attack Detection Tests ====================

    async def test_timing_attack_detection(self):
        """Test timing attack detection"""
        self.bot.time = 180.0
        self.intel.is_under_attack = Mock(return_value=True)

        await self.modeling._detect_timing_attacks(self.bot.time)

        self.assertEqual(len(self.modeling.timing_attacks_detected), 1)
        self.assertEqual(self.modeling.timing_attacks_detected[0], 180.0)

    async def test_timing_attack_cooldown(self):
        """Test timing attack detection cooldown (30s)"""
        self.bot.time = 180.0
        self.intel.is_under_attack = Mock(return_value=True)

        # First attack
        await self.modeling._detect_timing_attacks(self.bot.time)
        self.assertEqual(len(self.modeling.timing_attacks_detected), 1)

        # Second attack too soon (within 30s)
        self.bot.time = 200.0
        await self.modeling._detect_timing_attacks(self.bot.time)
        self.assertEqual(len(self.modeling.timing_attacks_detected), 1)

        # Third attack after cooldown
        self.bot.time = 220.0
        await self.modeling._detect_timing_attacks(self.bot.time)
        self.assertEqual(len(self.modeling.timing_attacks_detected), 2)

    # ==================== Style Classification Tests ====================

    def test_classify_cheese_style_proxy(self):
        """Test cheese style classification with proxy"""
        self.bot.time = 150.0
        self.modeling.observed_signals.add("proxy_detected")

        style = self.modeling._classify_opponent_style()

        self.assertEqual(style, OpponentStyle.CHEESE.value)

    def test_classify_aggressive_style(self):
        """Test aggressive style classification"""
        self.bot.time = 400.0
        self.modeling.timing_attacks_detected = [120.0, 240.0]

        style = self.modeling._classify_opponent_style()

        self.assertEqual(style, OpponentStyle.AGGRESSIVE.value)

    def test_classify_macro_style(self):
        """Test macro style classification"""
        self.bot.time = 600.0
        self.modeling.observed_signals.add("fast_expand")
        self.modeling.timing_attacks_detected = []

        style = self.modeling._classify_opponent_style()

        self.assertEqual(style, OpponentStyle.MACRO.value)

    def test_classify_timing_style(self):
        """Test timing attack style classification"""
        self.bot.time = 300.0
        self.modeling.timing_attacks_detected = [240.0]

        style = self.modeling._classify_opponent_style()

        self.assertEqual(style, OpponentStyle.TIMING.value)

    # ==================== Counter Strategy Tests ====================

    def test_counter_strategy_terran_bio(self):
        """Test counter strategy for terran bio"""
        counters = self.modeling._get_counter_strategy("terran_bio")

        self.assertIn("baneling", counters)
        self.assertIn("zergling", counters)

    def test_counter_strategy_protoss_stargate(self):
        """Test counter strategy for protoss stargate"""
        counters = self.modeling._get_counter_strategy("protoss_stargate")

        self.assertIn("hydralisk", counters)
        self.assertIn("corruptor", counters)

    def test_counter_strategy_unknown(self):
        """Test counter strategy for unknown strategy"""
        counters = self.modeling._get_counter_strategy("unknown_strategy")

        # Should return default
        self.assertIn("roach", counters)

    # ==================== Save/Load Tests ====================

    def test_save_models(self):
        """Test saving models to file"""
        # Create a model
        model = OpponentModel("test_opponent")
        self.modeling.opponent_models["test_opponent"] = model

        # Save
        result = self.modeling.save_models()

        self.assertTrue(result)
        self.assertTrue(os.path.exists(self.temp_file.name))

    def test_load_models(self):
        """Test loading models from file"""
        # Create and save a model
        model = OpponentModel("test_opponent")
        model.games_played = 5
        self.modeling.opponent_models["test_opponent"] = model
        self.modeling.save_models()

        # Create new instance and load
        new_modeling = OpponentModeling(
            self.bot,
            intel_manager=self.intel,
            data_file=self.temp_file.name
        )

        self.assertIn("test_opponent", new_modeling.opponent_models)
        self.assertEqual(new_modeling.opponent_models["test_opponent"].games_played, 5)

    def test_load_nonexistent_file(self):
        """Test loading when file doesn't exist"""
        new_modeling = OpponentModeling(
            self.bot,
            intel_manager=self.intel,
            data_file="/nonexistent/path/models.json"
        )

        # Should not crash
        self.assertEqual(len(new_modeling.opponent_models), 0)

    # ==================== Integration Tests ====================

    async def test_full_game_flow(self):
        """Test complete game flow from start to end"""
        # Start game
        await self.modeling.on_start()

        # Early game - detect signals
        self.bot.time = 100.0
        mock_pool = Mock()
        mock_pool.type_id = Mock()
        mock_pool.type_id.name = "SPAWNINGPOOL"
        self.bot.enemy_structures = [mock_pool]

        await self.modeling.on_step(100)

        # Mid game - detect timing attack
        self.bot.time = 180.0
        self.intel.is_under_attack = Mock(return_value=True)

        await self.modeling.on_step(180)

        # End game
        self.bot.time = 400.0
        self.intel.get_enemy_composition = Mock(return_value={"zergling": 30})

        await self.modeling.on_end("Defeat")

        # Verify model was updated
        model = self.modeling.opponent_models["opponent_Zerg"]
        self.assertEqual(model.games_played, 1)

    def test_get_opponent_stats(self):
        """Test retrieving opponent statistics"""
        # Create model with history
        model = OpponentModel("test_opponent")
        model.games_played = 10
        model.games_won = 6
        model.games_lost = 4
        model.dominant_style = OpponentStyle.AGGRESSIVE
        model.strategy_frequency["zerg_rush"] = 7
        model.unit_preferences["zergling"] = 200

        self.modeling.opponent_models["test_opponent"] = model

        # Get stats
        stats = self.modeling.get_opponent_stats("test_opponent")

        self.assertIsNotNone(stats)
        self.assertEqual(stats["games_played"], 10)
        self.assertEqual(stats["win_rate"], 0.6)
        self.assertEqual(stats["dominant_style"], "aggressive")
        self.assertEqual(stats["most_common_strategy"], "zerg_rush")


# Run tests
if __name__ == '__main__':
    unittest.main(verbosity=2)
