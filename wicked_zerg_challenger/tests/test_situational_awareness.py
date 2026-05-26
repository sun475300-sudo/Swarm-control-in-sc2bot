import os
import sys
import unittest
from unittest.mock import MagicMock

# Add project root to path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from core.situational_awareness import (
    OpportunityIndex,
    SituationalAwareness,
    ThreatLevel,
)


class MockStrategyManagerV2:
    pass


class TestSituationalAwareness(unittest.TestCase):
    def setUp(self):
        self.bot = MagicMock()
        self.bot.logger = MagicMock()
        self.bot.time = 100.0
        self.bot.iteration = 2200
        self.bot.minerals = 500
        self.bot.vespene = 200
        self.bot.supply_used = 100
        self.bot.supply_cap = 200

        # Mock StrategyManager as instance of dummy class
        self.bot.strategy_manager = MockStrategyManagerV2()
        self.bot.strategy_manager.current_win_condition = MagicMock()
        self.bot.strategy_manager.current_win_condition.name = "WINNING_ECONOMY"
        self.bot.strategy_manager.strategy_scores = {"ZergRush": 0.8, "Macro": 0.2}
        self.bot.strategy_manager.current_build_phase = MagicMock()
        self.bot.strategy_manager.current_build_phase.name = "MIDGAME"

        # Mock Blackboard
        self.bot.blackboard = MagicMock()

        self.sa = SituationalAwareness(self.bot)

    def test_sitrep_structure(self):
        """Test if SITREP JSON has correct structure"""
        # Patch the class in the module with our dummy class
        with unittest.mock.patch(
            "core.situational_awareness.StrategyManagerV2", MockStrategyManagerV2
        ):
            self.sa.update_sitrep()
            sitrep = self.sa.get_latest_sitrep()

        self.assertIn("timestamp", sitrep)
        self.assertIn("status", sitrep)
        self.assertIn("economy", sitrep)
        self.assertIn("military", sitrep)

        self.assertEqual(sitrep["status"]["win_condition"], "WINNING_ECONOMY")
        self.assertEqual(sitrep["economy"]["minerals"], 500)
        self.assertEqual(sitrep["military"]["strategy_scores"]["ZergRush"], 0.8)

    def test_throttling(self):
        """Test if updates are throttled"""
        self.sa.update_sitrep = MagicMock()

        # First call
        self.sa.on_step(100)
        self.sa.update_sitrep.assert_called_once()

        # Immediate second call (should be skipped)
        self.sa.on_step(100)
        self.sa.update_sitrep.assert_called_once()

        # Call after interval
        self.bot.time += 3.0
        self.sa.on_step(100)
        self.assertEqual(self.sa.update_sitrep.call_count, 2)

    def test_opportunity_assessment(self):
        """Test opportunity calculation"""
        self.bot.strategy_manager.current_win_condition.name = "WINNING_ARMY"

        # Patch and execute
        with unittest.mock.patch(
            "core.situational_awareness.StrategyManagerV2", MockStrategyManagerV2
        ):
            self.sa.update_sitrep()

        self.assertEqual(self.sa.opportunity_index, OpportunityIndex.HIGH)


class TestAssessThreatLevel(unittest.TestCase):
    """
    Regression coverage for _assess_threat_level — the blackboard threat
    used to be silently ignored (the branch contained a bare `pass`).
    """

    def setUp(self):
        from blackboard import GameStateBlackboard
        from blackboard import ThreatLevel as BBThreatLevel

        self.BBThreatLevel = BBThreatLevel
        self.bot = MagicMock()
        self.bot.time = 100.0
        self.bot.iteration = 0
        self.bot.minerals = 0
        self.bot.vespene = 0
        self.bot.supply_used = 0
        self.bot.supply_cap = 0
        self.bot.strategy_manager = None
        self.bot.blackboard = GameStateBlackboard()
        # No townhalls / enemy_units so the base-health branch can't fire
        self.bot.townhalls = MagicMock()
        self.bot.townhalls.__iter__ = lambda self_: iter([])
        self.bot.enemy_units = None
        self.sa = SituationalAwareness(self.bot)

    def test_blackboard_none_threat_stays_none(self):
        self.bot.blackboard.update_threat(self.BBThreatLevel.NONE)
        self.assertEqual(self.sa._assess_threat_level(), ThreatLevel.NONE)

    def test_blackboard_medium_threat_maps_to_local_medium(self):
        self.bot.blackboard.update_threat(self.BBThreatLevel.MEDIUM)
        self.assertEqual(self.sa._assess_threat_level(), ThreatLevel.MEDIUM)

    def test_blackboard_high_threat_maps_to_local_high(self):
        self.bot.blackboard.update_threat(self.BBThreatLevel.HIGH)
        self.assertEqual(self.sa._assess_threat_level(), ThreatLevel.HIGH)

    def test_blackboard_critical_threat_maps_to_local_critical(self):
        self.bot.blackboard.update_threat(self.BBThreatLevel.CRITICAL)
        self.assertEqual(self.sa._assess_threat_level(), ThreatLevel.CRITICAL)

    def test_no_blackboard_returns_none(self):
        self.bot.blackboard = None
        self.assertEqual(self.sa._assess_threat_level(), ThreatLevel.NONE)


if __name__ == "__main__":
    unittest.main()
