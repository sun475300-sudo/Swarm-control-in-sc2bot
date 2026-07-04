# -*- coding: utf-8 -*-
"""
Tests that BotStepIntegrator actually wires up MemoryMonitor.

utils/memory_monitor.py had unit tests for the class itself but was never
imported/used anywhere at runtime - no leak detection was actually active.
"""

import os
import sys
import unittest
from unittest.mock import Mock

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

import bot_step_integration
from utils.memory_monitor import MemoryMonitor


class TestBotStepIntegratorMemoryMonitor(unittest.TestCase):
    def test_integrator_creates_memory_monitor(self):
        bot = Mock()
        bot.logger = None

        integrator = bot_step_integration.BotStepIntegrator(bot)

        self.assertIsInstance(integrator.memory_monitor, MemoryMonitor)

    def test_integrator_tolerates_missing_memory_monitor_class(self):
        original = bot_step_integration.MemoryMonitor
        bot_step_integration.MemoryMonitor = None
        try:
            bot = Mock()
            bot.logger = None
            integrator = bot_step_integration.BotStepIntegrator(bot)
            self.assertIsNone(integrator.memory_monitor)
        finally:
            bot_step_integration.MemoryMonitor = original


if __name__ == "__main__":
    unittest.main()
