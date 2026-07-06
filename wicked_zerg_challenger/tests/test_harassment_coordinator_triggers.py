# -*- coding: utf-8 -*-
"""Regression tests for HarassmentCoordinator multi-angle attack triggers.

Covers a bug where _trigger_zergling_runby/_trigger_mutalisk_harassment were
empty placeholders: coordinate_multi_angle_attack called them, but they never
actually ran the existing run-by / mutalisk harassment logic.
"""

import asyncio
import os
import sys
from unittest.mock import AsyncMock, Mock

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from combat.harassment_coordinator import HarassmentCoordinator


def _make_coordinator():
    bot = Mock()
    bot.time = 300.0
    return HarassmentCoordinator(bot)


def test_trigger_zergling_runby_delegates_to_manager():
    coordinator = _make_coordinator()
    coordinator._manage_zergling_runby = AsyncMock()

    asyncio.run(coordinator._trigger_zergling_runby())

    coordinator._manage_zergling_runby.assert_awaited_once()


def test_trigger_mutalisk_harassment_delegates_to_manager():
    coordinator = _make_coordinator()
    coordinator._manage_mutalisk_harassment = AsyncMock()

    asyncio.run(coordinator._trigger_mutalisk_harassment())

    coordinator._manage_mutalisk_harassment.assert_awaited_once()


def test_multi_angle_attack_actually_runs_harassment_logic():
    coordinator = _make_coordinator()
    coordinator._can_execute_zergling_runby = Mock(return_value=True)
    coordinator._can_execute_mutalisk_harass = Mock(return_value=True)
    coordinator._can_execute_baneling_drop = Mock(return_value=False)
    coordinator._manage_zergling_runby = AsyncMock()
    coordinator._manage_mutalisk_harassment = AsyncMock()

    asyncio.run(coordinator.coordinate_multi_angle_attack(iteration=1))

    coordinator._manage_zergling_runby.assert_awaited_once()
    coordinator._manage_mutalisk_harassment.assert_awaited_once()
