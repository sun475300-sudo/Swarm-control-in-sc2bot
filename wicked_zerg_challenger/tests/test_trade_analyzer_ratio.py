# -*- coding: utf-8 -*-
"""Regression: trade ratio when enemy losses are zero but we have losses."""

import os
import sys
import unittest
from unittest.mock import Mock

os.environ["PROTOCOL_BUFFERS_PYTHON_IMPLEMENTATION"] = "python"
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from combat.trade_analyzer import TradeAnalyzer


class TestTradeRatioEdgeCases(unittest.TestCase):
    def _make(self):
        bot = Mock()
        bot.time = 100.0
        return TradeAnalyzer(bot)

    def test_no_losses_anywhere_is_neutral(self):
        ta = self._make()
        ta._calculate_trade_efficiency()
        self.assertEqual(ta.current_trade_ratio, 1.0)

    def test_we_lose_units_but_kill_nothing_is_disastrous(self):
        ta = self._make()
        ta.friendly_losses["ZERGLING"] = 10
        ta._calculate_trade_efficiency()
        # 적이 0원이고 우리가 손실 → 무한대 (= 즉시 retreat-warning 임계 초과)
        self.assertGreater(ta.current_trade_ratio, 2.0)

    def test_kills_with_no_losses_is_great(self):
        ta = self._make()
        ta.enemy_losses["MARINE"] = 5
        ta._calculate_trade_efficiency()
        self.assertEqual(ta.current_trade_ratio, 0.0)


if __name__ == "__main__":
    unittest.main()
