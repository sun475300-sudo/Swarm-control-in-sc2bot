# -*- coding: utf-8 -*-
import asyncio
import os
import sys
import unittest
from unittest.mock import AsyncMock, Mock

os.environ["PROTOCOL_BUFFERS_PYTHON_IMPLEMENTATION"] = "python"
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
sys.modules.pop("utils", None)

from sc2.ids.unit_typeid import UnitTypeId
from upgrade_manager import EvolutionUpgradeManager


class TestUpgradeManagerExpansionReserve(unittest.TestCase):
    def setUp(self):
        self.bot = Mock()
        self.bot.time = 170
        self.bot.structures = Mock()
        self.bot.townhalls = Mock()
        self.bot.townhalls.amount = 2
        self.bot.already_pending = Mock(return_value=0)
        self.manager = EvolutionUpgradeManager(self.bot)

    def test_reserves_for_third_base_before_noncritical_tech(self):
        """Two-base play pauses non-critical upgrade spending until third starts."""
        self.assertTrue(self.manager._should_reserve_for_third_base())

    def test_pending_third_base_unlocks_noncritical_tech(self):
        """A pending third Hatchery releases the upgrade manager reserve."""
        self.bot.townhalls.amount = 3

        self.assertFalse(self.manager._should_reserve_for_third_base())

    def test_reserves_for_fourth_base_after_three_bases(self):
        """Three-base play pauses non-critical upgrades until fourth starts."""
        self.bot.time = 370
        self.bot.townhalls.amount = 3
        self.bot.already_pending.return_value = 0

        self.assertTrue(self.manager._should_reserve_for_third_base())

    def test_pending_fourth_base_unlocks_noncritical_tech(self):
        """A pending fourth Hatchery releases the upgrade manager reserve."""
        self.bot.time = 370
        self.bot.townhalls.amount = 3
        self.bot.already_pending.side_effect = (
            lambda unit_type: 1 if unit_type == UnitTypeId.HATCHERY else 0
        )

        self.assertFalse(self.manager._should_reserve_for_third_base())

    def test_on_step_runs_critical_only_during_third_base_reserve(self):
        """The reserve keeps critical upgrades but skips tech, morphs, and evo."""
        self.manager._process_gas_reservations = AsyncMock()
        self.manager._research_critical_upgrades = AsyncMock()
        self.manager._upgrade_tech_buildings = AsyncMock()
        self.manager._ensure_morph_tech_buildings = AsyncMock()
        self.manager._build_evolution_chamber = AsyncMock()

        asyncio.run(self.manager.on_step(10))

        self.manager._research_critical_upgrades.assert_awaited_once()
        self.manager._upgrade_tech_buildings.assert_not_awaited()
        self.manager._ensure_morph_tech_buildings.assert_not_awaited()
        self.manager._build_evolution_chamber.assert_not_awaited()

    def test_overlord_speed_waits_for_third_base(self):
        """Critical upgrade handling keeps overlord speed from delaying the third."""
        self.bot.time = 210
        self.manager._zergling_speed_started = True
        self.manager._research_overlord_speed = AsyncMock()

        asyncio.run(self.manager._research_critical_upgrades(20))

        self.manager._research_overlord_speed.assert_not_awaited()

    def test_overlord_speed_allowed_after_third_base(self):
        """Once the third exists, overlord speed can use the normal critical path."""
        self.bot.time = 210
        self.bot.townhalls.amount = 3
        self.bot.units = Mock(return_value=Mock(amount=0))
        self.manager._zergling_speed_started = True
        self.manager._research_overlord_speed = AsyncMock()
        self.manager._has_lair = Mock(return_value=False)
        self.manager._has_hive = Mock(return_value=False)

        asyncio.run(self.manager._research_critical_upgrades(20))

        self.manager._research_overlord_speed.assert_awaited_once()


if __name__ == "__main__":
    unittest.main()
