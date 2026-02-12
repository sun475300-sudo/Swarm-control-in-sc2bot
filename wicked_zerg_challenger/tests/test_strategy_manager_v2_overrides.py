import unittest
from unittest.mock import MagicMock
import sys
import os

# Add project root to path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

# Mock StrategyConfig before importing StrategyManagerV2
sys.modules['config.unit_configs'] = MagicMock()

from strategy_manager_v2 import StrategyManagerV2
from strategy_manager import StrategyMode

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
            "status": {
                "threat_level": "CRITICAL",
                "opportunity": "NONE"
            }
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
            "status": {
                "threat_level": "NONE",
                "opportunity": "HIGH"
            }
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
            "status": {
                "threat_level": "NONE",
                "opportunity": "GAME_ENDING"
            }
        }
        
        # Execute logic
        self.sm._apply_situational_overrides()
        
        # Verify
        self.assertEqual(self.sm.current_mode, StrategyMode.ALL_IN)

if __name__ == '__main__':
    unittest.main()
