import os
import sys
import unittest
from unittest.mock import MagicMock

# Add project root to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
sys.modules.pop("utils", None)

# Mock StrategyConfig before importing StrategyManagerV2
sys.modules["config.unit_configs"] = MagicMock()

from strategy_manager import StrategyMode
from strategy_manager_v2 import StrategyManagerV2


class TestStrategyManagerV2Overrides(unittest.TestCase):
    def setUp(self):
        self.bot = MagicMock()
        self.bot.logger = MagicMock()
        self.bot.time = 100.0

        # Mock SituationalAwareness
        self.bot.situational_awareness = MagicMock()

        # Initialize StrategyManagerV2
        self.sm = StrategyManagerV2(self.bot)
        self.sm.current_mode = StrategyMode.NORMAL

    def test_critical_threat_override(self):
        """Test if CRITICAL threat forces EMERGENCY mode"""
        # Setup SITREP
        self.bot.situational_awareness.get_latest_sitrep.return_value = {
            "status": {"threat_level": "CRITICAL", "opportunity": "NONE"}
        }

        # Execute logic
        self.sm._apply_situational_overrides()

        # Verify
        self.assertEqual(self.sm.current_mode, StrategyMode.EMERGENCY)
        self.assertTrue(self.sm.emergency_active)

    def test_high_opportunity_override(self):
        """Test if HIGH opportunity triggers AGGRESSIVE mode"""
        self.sm.current_mode = StrategyMode.NORMAL

        # Setup SITREP
        self.bot.situational_awareness.get_latest_sitrep.return_value = {
            "status": {"threat_level": "NONE", "opportunity": "HIGH"}
        }

        # Execute logic
        self.sm._apply_situational_overrides()

        # Verify
        self.assertEqual(self.sm.current_mode, StrategyMode.AGGRESSIVE)

    def test_finish_opportunity_override(self):
        """Test if GAME_ENDING opportunity triggers ALL_IN mode"""
        self.sm.current_mode = StrategyMode.AGGRESSIVE

        # Setup SITREP
        self.bot.situational_awareness.get_latest_sitrep.return_value = {
            "status": {"threat_level": "NONE", "opportunity": "GAME_ENDING"}
        }

        # Execute logic
        self.sm._apply_situational_overrides()

        # Verify
        self.assertEqual(self.sm.current_mode, StrategyMode.ALL_IN)

    def test_defense_mode_does_not_exit_while_base_threat_exists(self):
        """Visible enemies near a base keep defense mode active."""
        base = MagicMock()
        enemy = MagicMock()
        enemy.distance_to.return_value = 10
        self.bot.townhalls = [base]
        self.bot.enemy_units = [enemy]
        self.bot.time = 250.0

        self.sm.current_mode = StrategyMode.DEFENSIVE
        self.sm.last_major_attack_time = 0.0
        self.sm._detect_major_attack = MagicMock(return_value=False)

        self.sm._check_defense_mode_timeout()

        self.assertEqual(self.sm.current_mode, StrategyMode.DEFENSIVE)
        self.assertEqual(self.sm.last_major_attack_time, 250.0)


if __name__ == "__main__":
    unittest.main()
