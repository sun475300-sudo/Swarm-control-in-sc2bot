# -*- coding: utf-8 -*-
"""
Unit tests for RealtimeAwarenessEngine emergency-production helpers.

Targets the simplification done by removing the dead `asyncio.ensure_future`
fire-and-forget branch (burnysc2 7.x BotAI.do is synchronous and returns bool).
"""

import os
import sys
import unittest
from unittest.mock import Mock

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from realtime_awareness_engine import RealtimeAwarenessEngine
from sc2.ids.unit_typeid import UnitTypeId


class TestEmergencyProductionHelpers(unittest.TestCase):
    """Verify the consolidated _train_from_larva helper and its callers."""

    def setUp(self):
        self.bot = Mock()
        self.bot.do = Mock(return_value=True)

        # Default: nothing affordable / no buildings
        self.bot.can_afford = Mock(return_value=False)

        def has_struct(_unit_type):
            res = Mock()
            res.ready = Mock()
            res.ready.exists = False
            return res

        self.bot.structures = Mock(side_effect=has_struct)

        self.bot.larva = Mock()
        self.bot.larva.exists = False
        self.bot.larva.amount = 0
        self.bot.vespene = 0

        self.engine = RealtimeAwarenessEngine(self.bot)

    def _make_larva(self, amount):
        larva = Mock()
        larva.exists = amount > 0
        larva.amount = amount
        larva.first = Mock()
        larva.first.train = Mock(return_value="TRAIN_CMD")
        larva.random = larva.first
        return larva

    def test_train_from_larva_calls_bot_do(self):
        larva_unit = Mock()
        larva_unit.train = Mock(return_value="TRAIN_CMD")
        ok = self.engine._train_from_larva(larva_unit, UnitTypeId.ZERGLING)
        self.assertTrue(ok)
        larva_unit.train.assert_called_once_with(UnitTypeId.ZERGLING)
        self.bot.do.assert_called_once_with("TRAIN_CMD")

    def test_force_overlord_production_no_larva_is_noop(self):
        self.bot.larva = self._make_larva(0)
        self.engine._force_overlord_production()
        self.bot.do.assert_not_called()

    def test_force_overlord_production_trains_when_affordable(self):
        self.bot.larva = self._make_larva(1)
        self.bot.can_afford = Mock(return_value=True)
        self.engine._force_overlord_production()
        self.bot.do.assert_called_once_with("TRAIN_CMD")

    def test_force_overlord_production_swallows_exceptions(self):
        # If anything in the chain raises, the helper must not propagate.
        self.bot.larva = self._make_larva(1)
        self.bot.can_afford = Mock(return_value=True)
        self.bot.do = Mock(side_effect=RuntimeError("boom"))
        # Must not raise
        self.engine._force_overlord_production()

    def test_flush_minerals_caps_at_eight_orders(self):
        self.bot.larva = self._make_larva(20)
        self.bot.can_afford = Mock(return_value=True)
        # Pretend SPAWNINGPOOL is ready
        pool = Mock()
        pool.ready = Mock()
        pool.ready.exists = True
        self.bot.structures = Mock(return_value=pool)
        self.engine._flush_minerals()
        self.assertEqual(self.bot.do.call_count, 8)

    def test_force_army_production_zergling_path(self):
        self.bot.larva = self._make_larva(3)
        self.bot.vespene = 0  # No gas → skip ROACH branch
        self.bot.can_afford = Mock(return_value=True)
        pool = Mock()
        pool.ready = Mock()
        pool.ready.exists = True
        self.bot.structures = Mock(return_value=pool)
        self.engine._force_army_production()
        # Should issue at most min(amount, 5) train orders
        self.assertGreaterEqual(self.bot.do.call_count, 1)
        self.assertLessEqual(self.bot.do.call_count, 5)


if __name__ == "__main__":
    unittest.main()
