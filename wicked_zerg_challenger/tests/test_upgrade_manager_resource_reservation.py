# -*- coding: utf-8 -*-
"""
Regression tests for UpgradeManager <-> ResourceManager integration.

Before this fix, upgrade_manager.py only checked bot.can_afford(upgrade_id)
before issuing research, independent of what other managers (BuildingManager,
EconomyManager) were about to spend the same frame -- a race that could let
two managers both believe they could afford overlapping mineral/gas costs.
These tests confirm UpgradeManager now reserves through the shared
ResourceManager when one is present, and stays backward compatible when
one is not (e.g. in lightweight test bots).
"""

import asyncio
import os
import sys
import unittest
from unittest.mock import AsyncMock, Mock

os.environ["PROTOCOL_BUFFERS_PYTHON_IMPLEMENTATION"] = "python"
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
sys.modules.pop("utils", None)

from upgrade_manager import EvolutionUpgradeManager


class TestUpgradeManagerResourceReservation(unittest.TestCase):
    def setUp(self):
        self.bot = Mock()
        self.bot.time = 170
        self.bot.minerals = 500
        self.bot.vespene = 500
        self.manager = EvolutionUpgradeManager(self.bot)
        self.manager._get_upgrade_cost = Mock(return_value=(100, 100))

    def test_no_resource_manager_proceeds_unchanged(self):
        """Without a shared ResourceManager, reservation is a no-op that allows research."""
        del self.bot.resource_manager  # Mock() auto-vivifies attrs; force it absent.
        self.assertFalse(hasattr(self.bot, "resource_manager"))

        allowed = asyncio.run(self.manager._try_reserve_upgrade_cost("SOME_UPGRADE"))

        self.assertTrue(allowed)

    def test_reserves_cost_through_resource_manager(self):
        """When present, reservation goes through resource_manager.try_reserve with the upgrade cost."""
        self.bot.resource_manager = Mock()
        self.bot.resource_manager.try_reserve = AsyncMock(return_value=True)

        allowed = asyncio.run(self.manager._try_reserve_upgrade_cost("SOME_UPGRADE"))

        self.assertTrue(allowed)
        self.bot.resource_manager.try_reserve.assert_awaited_once_with(
            100, 100, "UpgradeManager"
        )

    def test_reservation_denied_when_another_manager_holds_resources(self):
        """A denied reservation propagates as False so the caller skips this upgrade."""
        self.bot.resource_manager = Mock()
        self.bot.resource_manager.try_reserve = AsyncMock(return_value=False)

        allowed = asyncio.run(self.manager._try_reserve_upgrade_cost("SOME_UPGRADE"))

        self.assertFalse(allowed)

    def test_release_calls_resource_manager_when_present(self):
        self.bot.resource_manager = Mock()
        self.bot.resource_manager.release = AsyncMock()

        asyncio.run(self.manager._release_upgrade_reservation())

        self.bot.resource_manager.release.assert_awaited_once_with("UpgradeManager")

    def test_release_is_noop_without_resource_manager(self):
        del self.bot.resource_manager
        self.assertFalse(hasattr(self.bot, "resource_manager"))

        # Should not raise even though there is nothing to release against.
        asyncio.run(self.manager._release_upgrade_reservation())

    def test_release_suppresses_resource_manager_errors(self):
        """A failing release must not propagate and break the calling research loop."""
        self.bot.resource_manager = Mock()
        self.bot.resource_manager.release = AsyncMock(side_effect=RuntimeError("boom"))

        # Should not raise.
        asyncio.run(self.manager._release_upgrade_reservation())


if __name__ == "__main__":
    unittest.main()
