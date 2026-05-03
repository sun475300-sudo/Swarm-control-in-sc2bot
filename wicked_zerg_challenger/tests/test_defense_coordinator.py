# -*- coding: utf-8 -*-
"""
Unit tests for DefenseCoordinator.

Note: many threat-evaluation branches inside DefenseCoordinator early-return
when GameStateBlackboard / ThreatLevel are unavailable (the module imports
them via try/except). Those modules are not present in this repository, so
we focus on what's safely testable:
- __init__ defaults
- reset() clears state
- detect_and_evaluate_threats clears tags when no enemies and propagates to
  blackboard if attached
- get_status structure (with and without blackboard)
"""

import asyncio
import os
import sys
import unittest
from unittest.mock import Mock

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from defense_coordinator import DefenseCoordinator
from sc2.position import Point2


def _bot(time=60.0):
    bot = Mock()
    bot.time = time
    bot.enemy_units = []
    bot.enemy_structures = []
    bot.townhalls = []
    bot.do = Mock()
    bot.game_info = Mock()
    bot.game_info.map_center = Point2((50, 50))
    return bot


class TestInit(unittest.TestCase):
    def test_default_state(self):
        bot = _bot()
        dc = DefenseCoordinator(bot)
        self.assertEqual(dc.detected_threats, set())
        self.assertEqual(dc.defending_units, set())
        self.assertFalse(dc.pool_requested)
        self.assertFalse(dc.first_queen_requested)
        self.assertEqual(dc.spine_crawler_positions, [])
        self.assertEqual(dc.spore_crawler_positions, [])
        self.assertFalse(dc.proactive_spore_requested)

    def test_blackboard_default_none(self):
        bot = _bot()
        dc = DefenseCoordinator(bot)
        self.assertIsNone(dc.blackboard)

    def test_blackboard_can_be_attached(self):
        bot = _bot()
        bb = Mock()
        dc = DefenseCoordinator(bot, blackboard=bb)
        self.assertIs(dc.blackboard, bb)

    def test_intervals_present(self):
        bot = _bot()
        dc = DefenseCoordinator(bot)
        # threat_check_interval comes from config or fallback
        self.assertIsInstance(dc.threat_check_interval, float)
        self.assertGreater(dc.threat_check_interval, 0)
        # early_game_threshold sane
        self.assertGreater(dc.early_game_threshold, 0)


class TestReset(unittest.TestCase):
    def test_reset_clears_all_mutable_state(self):
        bot = _bot()
        dc = DefenseCoordinator(bot)
        dc.detected_threats.add(1)
        dc.defending_units.add(2)
        dc.pool_requested = True
        dc.first_queen_requested = True
        dc.spine_crawler_positions.append(Point2((1, 1)))
        dc.spore_crawler_positions.append(Point2((2, 2)))

        dc.reset()

        self.assertEqual(dc.detected_threats, set())
        self.assertEqual(dc.defending_units, set())
        self.assertFalse(dc.pool_requested)
        self.assertFalse(dc.first_queen_requested)
        self.assertEqual(dc.spine_crawler_positions, [])
        self.assertEqual(dc.spore_crawler_positions, [])


class TestDetectAndEvaluateThreats(unittest.IsolatedAsyncioTestCase):
    async def test_no_enemies_clears_threats(self):
        bot = _bot()
        bot.enemy_units = []
        dc = DefenseCoordinator(bot)
        dc.detected_threats.add(99)
        dc.defending_units.add(42)
        await dc._detect_and_evaluate_threats()
        self.assertEqual(dc.detected_threats, set())
        self.assertEqual(dc.defending_units, set())

    async def test_no_enemies_propagates_empty_to_blackboard(self):
        bot = _bot()
        bot.enemy_units = []
        bb = Mock()
        bb.set = Mock()
        dc = DefenseCoordinator(bot, blackboard=bb)
        dc.defending_units.add(42)
        await dc._detect_and_evaluate_threats()
        # Should have written defense_unit_tags=set() to blackboard
        called_keys = [c.args[0] for c in bb.set.call_args_list]
        self.assertIn("defense_unit_tags", called_keys)

    async def test_no_townhalls_returns_quietly_when_enemies_present(self):
        bot = _bot()
        e = Mock()
        e.tag = 1
        bot.enemy_units = [e]
        bot.townhalls = []  # no bases
        dc = DefenseCoordinator(bot)
        # Just must not raise
        await dc._detect_and_evaluate_threats()


class TestGetStatus(unittest.TestCase):
    def test_status_no_blackboard(self):
        bot = _bot()
        dc = DefenseCoordinator(bot)
        status = dc.get_status()
        self.assertEqual(status["threat_level"], "UNKNOWN")
        self.assertEqual(status["detected_threats"], 0)
        self.assertEqual(status["defending_units"], 0)
        self.assertFalse(status["pool_requested"])
        self.assertFalse(status["first_queen_requested"])

    def test_status_reports_counts(self):
        bot = _bot()
        dc = DefenseCoordinator(bot)
        dc.detected_threats.update({1, 2, 3})
        dc.defending_units.update({10, 20})
        dc.pool_requested = True
        status = dc.get_status()
        self.assertEqual(status["detected_threats"], 3)
        self.assertEqual(status["defending_units"], 2)
        self.assertTrue(status["pool_requested"])

    def test_status_with_blackboard_threat(self):
        bot = _bot()
        bb = Mock()
        threat = Mock()
        threat.level = Mock()
        threat.level.name = "HIGH"
        bb.threat = threat
        dc = DefenseCoordinator(bot, blackboard=bb)
        status = dc.get_status()
        self.assertEqual(status["threat_level"], "HIGH")

    def test_status_with_blackboard_no_threat(self):
        bot = _bot()
        bb = Mock()
        bb.threat = None
        dc = DefenseCoordinator(bot, blackboard=bb)
        status = dc.get_status()
        self.assertEqual(status["threat_level"], "UNKNOWN")


if __name__ == "__main__":
    unittest.main()
