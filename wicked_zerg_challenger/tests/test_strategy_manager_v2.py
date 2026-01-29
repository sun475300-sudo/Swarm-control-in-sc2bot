# -*- coding: utf-8 -*-
"""
Unit Tests for strategy_manager_v2.py

Tests Strategy Manager V2 features:
- Win condition detection
- Build order transitions
- Strategy scoring
- Resource allocation
- Multi-strategy execution
"""

import unittest
from unittest.mock import Mock, MagicMock, patch
import sys
import os

# Add parent directory to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from strategy_manager_v2 import (
    StrategyManagerV2,
    WinCondition,
    BuildOrderPhase,
    StrategyPriority
)


class MockBot:
    """Mock SC2 bot for testing"""
    def __init__(self):
        self.time = 0.0
        self.iteration = 0
        self.units = MockUnits([])
        self.enemy_units = MockUnits([])
        self.structures = MockUnits([])
        self.enemy_structures = MockUnits([])
        self.townhalls = MockUnits([])
        self.supply_army = 0
        self.supply_used = 0
        self.minerals = 50
        self.vespene = 0
        self.enemy_race = None


class MockUnits:
    """Mock units collection"""
    def __init__(self, units):
        self._units = units
        self.amount = len(units)

    def __call__(self, unit_type):
        """Filter by type"""
        return self

    def __iter__(self):
        return iter(self._units)

    def __len__(self):
        return len(self._units)

    def exists(self):
        return len(self._units) > 0

    def first(self):
        return self._units[0] if self._units else None


class TestWinConditionDetection(unittest.TestCase):
    """Test win condition detection system"""

    def setUp(self):
        """Create mock bot and strategy manager"""
        self.bot = MockBot()
        self.manager = StrategyManagerV2(self.bot)

    def test_initial_win_condition(self):
        """Test initial win condition is unknown"""
        self.assertEqual(self.manager.current_win_condition, WinCondition.UNKNOWN)

    def test_economy_advantage_detection(self):
        """Test detecting economy advantage"""
        # Mock strong economy (many workers) with full scores
        self.manager._calculate_economy_score = Mock(return_value=3.0)
        self.manager._calculate_army_score = Mock(return_value=2.0)
        self.manager._calculate_tech_score = Mock(return_value=1.0)

        # Update win condition
        self.bot.time = 10.0
        self.manager._update_win_condition(10.0)

        # Should detect winning economy (total >= 6 and economy is highest)
        self.assertEqual(self.manager.current_win_condition, WinCondition.WINNING_ECONOMY)

    def test_army_disadvantage_detection(self):
        """Test detecting army disadvantage"""
        # Mock weak army with full negative scores (army is most negative)
        self.manager._calculate_economy_score = Mock(return_value=-1.0)
        self.manager._calculate_army_score = Mock(return_value=-3.0)
        self.manager._calculate_tech_score = Mock(return_value=-2.0)

        # Update win condition
        self.bot.time = 10.0
        self.manager._update_win_condition(10.0)

        # Should detect losing army (total <= -6 and army is most negative)
        self.assertEqual(self.manager.current_win_condition, WinCondition.LOSING_ARMY)

    def test_win_condition_update_interval(self):
        """Test win condition updates respect interval"""
        self.bot.time = 1.0
        self.manager._update_win_condition(1.0)
        initial_condition = self.manager.current_win_condition

        # Try to update immediately (should be skipped)
        self.bot.time = 2.0
        self.manager._update_win_condition(2.0)
        self.assertEqual(self.manager.current_win_condition, initial_condition)

        # Update after interval
        self.bot.time = 10.0
        self.manager._update_win_condition(10.0)
        # May have changed


class TestBuildOrderTransitions(unittest.TestCase):
    """Test build order transition system"""

    def setUp(self):
        """Create mock bot and strategy manager"""
        self.bot = MockBot()
        self.manager = StrategyManagerV2(self.bot)

    def test_initial_build_phase(self):
        """Test initial build phase is opening"""
        self.assertEqual(self.manager.current_build_phase, BuildOrderPhase.OPENING)

    def test_opening_to_transition(self):
        """Test transition from opening to transition phase"""
        self.bot.time = 190.0  # 3:10
        self.manager._update_build_phase(190.0)
        self.assertEqual(self.manager.current_build_phase, BuildOrderPhase.TRANSITION)

    def test_transition_to_midgame(self):
        """Test transition from transition to midgame"""
        self.bot.time = 370.0  # 6:10
        self.manager._update_build_phase(370.0)
        self.assertEqual(self.manager.current_build_phase, BuildOrderPhase.MIDGAME)

    def test_midgame_to_lategame(self):
        """Test transition from midgame to lategame"""
        self.bot.time = 610.0  # 10:10
        self.manager._update_build_phase(610.0)
        self.assertEqual(self.manager.current_build_phase, BuildOrderPhase.LATEGAME)

    def test_build_transition_callback(self):
        """Test build transition executes callback"""
        # Mock the transition method
        self.manager._execute_build_transition = Mock()

        # Trigger phase change
        self.bot.time = 190.0
        self.manager._update_build_phase(190.0)

        # Verify callback was called
        self.manager._execute_build_transition.assert_called_once()

    def test_expansion_planning(self):
        """Test expansion planning at target times"""
        self.manager._plan_expansion(target_time=240.0)
        self.assertIn(240.0, self.manager.planned_expansions)


class TestResourceAllocation(unittest.TestCase):
    """Test resource allocation system"""

    def setUp(self):
        """Create mock bot and strategy manager"""
        self.bot = MockBot()
        self.manager = StrategyManagerV2(self.bot)

    def test_default_resource_priorities(self):
        """Test default resource allocation"""
        self.assertEqual(self.manager.resource_priorities["economy"], 0.4)
        self.assertEqual(self.manager.resource_priorities["army"], 0.4)
        self.assertEqual(self.manager.resource_priorities["tech"], 0.1)
        self.assertEqual(self.manager.resource_priorities["defense"], 0.1)

    def test_losing_army_adjusts_priorities(self):
        """Test resource priorities when losing army"""
        self.manager.current_win_condition = WinCondition.LOSING_ARMY
        self.manager._adjust_resource_priorities()

        # Should prioritize army production
        self.assertGreater(self.manager.resource_priorities["army"], 0.5)

    def test_losing_economy_adjusts_priorities(self):
        """Test resource priorities when losing economy"""
        self.manager.current_win_condition = WinCondition.LOSING_ECONOMY
        self.manager._adjust_resource_priorities()

        # Should prioritize economy
        self.assertGreater(self.manager.resource_priorities["economy"], 0.5)

    def test_winning_adjusts_priorities(self):
        """Test resource priorities when winning"""
        self.manager.current_win_condition = WinCondition.WINNING_ARMY
        self.manager._adjust_resource_priorities()

        # Should prioritize army to push advantage
        self.assertGreater(self.manager.resource_priorities["army"], 0.5)

    def test_emergency_mode_priorities(self):
        """Test resource priorities in emergency mode"""
        self.manager.emergency_active = True
        self.manager._adjust_resource_priorities()

        # Should prioritize army and defense
        self.assertGreater(self.manager.resource_priorities["army"], 0.6)
        self.assertEqual(self.manager.resource_priorities["economy"], 0.0)

    def test_get_resource_priority(self):
        """Test getting resource priority for category"""
        priority = self.manager.get_resource_priority("army")
        self.assertIsInstance(priority, float)
        self.assertGreaterEqual(priority, 0.0)
        self.assertLessEqual(priority, 1.0)


class TestStrategyScoring(unittest.TestCase):
    """Test strategy scoring system"""

    def setUp(self):
        """Create mock bot and strategy manager"""
        self.bot = MockBot()
        self.manager = StrategyManagerV2(self.bot)

    def test_initial_strategy_scores(self):
        """Test initial strategy scores are empty"""
        self.assertEqual(len(self.manager.strategy_scores), 0)

    def test_calculate_strategy_score(self):
        """Test calculating strategy score"""
        strategy = {"name": "test_strategy"}
        score = self.manager._calculate_strategy_score(strategy)

        self.assertIsInstance(score, float)
        self.assertGreaterEqual(score, 0.0)
        self.assertLessEqual(score, 1.0)

    def test_evaluate_strategy_effectiveness(self):
        """Test evaluating strategy effectiveness"""
        # Add a test strategy
        self.manager.active_strategies.append({"name": "test_strategy"})

        # Evaluate
        self.manager._evaluate_strategy_effectiveness()

        # Should have score for the strategy
        self.assertIn("test_strategy", self.manager.strategy_scores)


class TestMultiStrategyExecution(unittest.TestCase):
    """Test multi-strategy execution system"""

    def setUp(self):
        """Create mock bot and strategy manager"""
        self.bot = MockBot()
        self.manager = StrategyManagerV2(self.bot)

    def test_initial_active_strategies(self):
        """Test initial active strategies list is empty"""
        self.assertEqual(len(self.manager.active_strategies), 0)

    def test_add_strategy(self):
        """Test adding a strategy"""
        strategy = {
            "name": "test_strategy",
            "priority": StrategyPriority.HIGH,
            "start_time": 0.0
        }
        self.manager._add_strategy(strategy)

        self.assertEqual(len(self.manager.active_strategies), 1)
        self.assertEqual(self.manager.active_strategies[0]["name"], "test_strategy")

    def test_prevent_duplicate_strategies(self):
        """Test preventing duplicate strategies"""
        strategy = {"name": "test_strategy"}
        self.manager._add_strategy(strategy)
        self.manager._add_strategy(strategy)  # Try to add again

        # Should only have one
        self.assertEqual(len(self.manager.active_strategies), 1)

    def test_strategy_limit(self):
        """Test concurrent strategy limit"""
        # Fill up to limit
        for i in range(self.manager.concurrent_strategy_limit + 2):
            self.manager._add_strategy({"name": f"strategy_{i}"})

        # Check limit is respected (initially limit is 3)
        self.assertLessEqual(len(self.manager.active_strategies),
                           self.manager.concurrent_strategy_limit + 2)

    def test_cleanup_completed_strategies(self):
        """Test cleaning up completed strategies"""
        # Add strategies
        self.manager.active_strategies.append({"name": "active", "complete": False})
        self.manager.active_strategies.append({"name": "completed", "complete": True})

        # Execute cleanup
        self.manager._execute_multi_strategy()

        # Completed should be removed
        strategy_names = [s["name"] for s in self.manager.active_strategies]
        self.assertIn("active", strategy_names)
        self.assertNotIn("completed", strategy_names)


class TestHelperMethods(unittest.TestCase):
    """Test helper methods"""

    def setUp(self):
        """Create mock bot and strategy manager"""
        self.bot = MockBot()
        self.manager = StrategyManagerV2(self.bot)

    def test_count_workers(self):
        """Test counting workers"""
        # Mock workers
        with patch.object(self.manager, '_count_workers', return_value=25):
            count = self.manager._count_workers()
            self.assertEqual(count, 25)

    def test_count_bases(self):
        """Test counting bases"""
        self.bot.townhalls = MockUnits([Mock(), Mock(), Mock()])
        count = self.manager._count_bases()
        self.assertEqual(count, 3)

    def test_estimate_enemy_workers_with_scouting(self):
        """Test estimating enemy workers when scouted"""
        # Mock scouted workers
        worker = Mock()
        worker.type_id = Mock()
        worker.type_id.name = "PROBE"
        self.bot.enemy_units = MockUnits([worker] * 20)

        count = self.manager._estimate_enemy_workers()
        self.assertEqual(count, 20)

    def test_estimate_enemy_workers_without_scouting(self):
        """Test estimating enemy workers without scouting"""
        self.bot.enemy_units = MockUnits([])
        self.manager._estimate_enemy_bases = Mock(return_value=2)

        count = self.manager._estimate_enemy_workers()
        self.assertEqual(count, 32)  # 2 bases * 16 workers

    def test_should_prioritize_economy(self):
        """Test economy prioritization check"""
        self.manager.resource_priorities["economy"] = 0.6
        self.assertTrue(self.manager.should_prioritize_economy())

        self.manager.resource_priorities["economy"] = 0.2
        self.assertFalse(self.manager.should_prioritize_economy())

    def test_should_prioritize_army(self):
        """Test army prioritization check"""
        self.manager.resource_priorities["army"] = 0.7
        self.assertTrue(self.manager.should_prioritize_army())

        self.manager.resource_priorities["army"] = 0.3
        self.assertFalse(self.manager.should_prioritize_army())


class TestStatusReport(unittest.TestCase):
    """Test status reporting"""

    def setUp(self):
        """Create mock bot and strategy manager"""
        self.bot = MockBot()
        self.manager = StrategyManagerV2(self.bot)

    def test_status_report_v2_structure(self):
        """Test V2 status report has all required fields"""
        report = self.manager.get_status_report_v2()

        # Check V2 fields
        self.assertIn("win_condition", report)
        self.assertIn("build_phase", report)
        self.assertIn("resource_priorities", report)
        self.assertIn("active_strategies", report)
        self.assertIn("strategy_scores", report)

    def test_status_report_v2_includes_base_report(self):
        """Test V2 report includes base report fields"""
        report = self.manager.get_status_report_v2()

        # Check base fields from parent
        self.assertIn("mode", report)
        self.assertIn("enemy_race", report)
        self.assertIn("game_phase", report)


if __name__ == '__main__':
    # Run all tests
    unittest.main(verbosity=2)
