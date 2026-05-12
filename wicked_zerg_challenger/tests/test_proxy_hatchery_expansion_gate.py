# -*- coding: utf-8 -*-
import asyncio
import os
import sys
import unittest
from types import SimpleNamespace
from unittest.mock import Mock

os.environ["PROTOCOL_BUFFERS_PYTHON_IMPLEMENTATION"] = "python"
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

import pytest

try:
    from sc2.ids.unit_typeid import UnitTypeId
except ImportError:  # pragma: no cover
    pytest.skip("sc2 library not available", allow_module_level=True)
from strategy.proxy_hatchery import ProxyHatchery


class FakePoint:
    def __init__(self, x=50.0, y=50.0):
        self.x = x
        self.y = y

    def towards(self, other, distance):
        return FakePoint(self.x - distance, self.y - distance)


class FakeDrone:
    def build(self, unit_type, location):
        return ("build", unit_type, location)


class FakeUnits(list):
    @property
    def amount(self):
        return len(self)

    @property
    def first(self):
        return self[0]


class TestProxyHatcheryExpansionGate(unittest.TestCase):
    def _make_bot(self, ready_bases=4, pending_hatcheries=0):
        bot = Mock()
        bot.time = 400.0
        bot.minerals = 500
        bot.enemy_start_locations = [FakePoint(100.0, 100.0)]
        bot.game_info = SimpleNamespace(map_center=FakePoint(50.0, 50.0))
        bot.do = Mock()
        bot.units = Mock(return_value=FakeUnits([FakeDrone()]))

        bot.townhalls = Mock()
        bot.townhalls.ready.amount = ready_bases
        bot.townhalls.amount = ready_bases
        bot.already_pending.side_effect = lambda unit_type: (
            pending_hatcheries if unit_type == UnitTypeId.HATCHERY else 0
        )
        return bot

    def test_proxy_hatch_waits_until_four_ready_bases(self):
        bot = self._make_bot(ready_bases=3, pending_hatcheries=0)
        proxy = ProxyHatchery(bot)

        asyncio.run(proxy._attempt_proxy_hatchery())

        bot.do.assert_not_called()
        self.assertFalse(proxy.proxy_attempted)

    def test_proxy_hatch_waits_while_macro_hatchery_pending(self):
        bot = self._make_bot(ready_bases=4, pending_hatcheries=1)
        proxy = ProxyHatchery(bot)

        asyncio.run(proxy._attempt_proxy_hatchery())

        bot.do.assert_not_called()
        self.assertFalse(proxy.proxy_attempted)

    def test_proxy_hatch_allowed_after_four_ready_bases(self):
        bot = self._make_bot(ready_bases=4, pending_hatcheries=0)
        proxy = ProxyHatchery(bot)

        asyncio.run(proxy._attempt_proxy_hatchery())

        bot.do.assert_called_once()
        self.assertTrue(proxy.proxy_attempted)
        self.assertIsNotNone(proxy.proxy_location)


if __name__ == "__main__":
    unittest.main()
