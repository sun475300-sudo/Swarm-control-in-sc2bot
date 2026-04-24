# -*- coding: utf-8 -*-
"""
Unit tests for wicked_zerg_challenger/defense_coordinator.py (785 LOC, previously untested).

Focuses on lightweight, non-IO behaviour: construction, reset state,
status reporting, short-circuits in execute() when prerequisites missing.
"""
import os
import sys
from unittest.mock import MagicMock

import pytest

sys.path.insert(
    0, os.path.join(os.path.dirname(__file__), "..", "wicked_zerg_challenger")
)


def _import():
    try:
        from defense_coordinator import DefenseCoordinator
        return DefenseCoordinator
    except ImportError:
        return None


DefenseCoordinator = _import()

pytestmark = pytest.mark.skipif(
    DefenseCoordinator is None, reason="defense_coordinator not importable"
)


@pytest.fixture
def bot():
    b = MagicMock()
    b.time = 0.0
    b.minerals = 500
    b.vespene = 200
    b.units = []
    b.structures = []
    b.enemy_units = []
    b.enemy_structures = []
    return b


@pytest.fixture
def blackboard():
    bb = MagicMock()
    bb.threat = MagicMock()
    bb.threat.level = MagicMock()
    bb.threat.level.name = "NONE"
    return bb


@pytest.fixture
def coordinator(bot, blackboard):
    return DefenseCoordinator(bot, blackboard)


class TestInitialization:
    def test_default_state_empty(self, coordinator):
        assert coordinator.detected_threats == set()
        assert coordinator.defending_units == set()
        assert coordinator.pool_requested is False
        assert coordinator.first_queen_requested is False
        assert coordinator.spine_crawler_positions == []
        assert coordinator.spore_crawler_positions == []
        assert coordinator.proactive_spore_requested is False

    def test_thresholds_loaded(self, coordinator):
        assert coordinator.early_game_threshold > 0
        assert coordinator.proactive_spore_timing > 0
        assert coordinator.threat_check_interval >= 0


class TestReset:
    def test_reset_clears_all_state(self, coordinator):
        coordinator.detected_threats.add(42)
        coordinator.defending_units.add(17)
        coordinator.pool_requested = True
        coordinator.first_queen_requested = True
        coordinator.spine_crawler_positions.append(MagicMock())
        coordinator.spore_crawler_positions.append(MagicMock())
        coordinator.proactive_spore_requested = True
        coordinator.last_threat_check = 123.5

        coordinator.reset()

        assert coordinator.detected_threats == set()
        assert coordinator.defending_units == set()
        assert coordinator.pool_requested is False
        assert coordinator.first_queen_requested is False
        assert coordinator.spine_crawler_positions == []
        assert coordinator.spore_crawler_positions == []
        assert coordinator.proactive_spore_requested is False
        assert coordinator.last_threat_check == 0.0

    def test_reset_after_reset_is_idempotent(self, coordinator):
        coordinator.reset()
        coordinator.reset()
        assert coordinator.detected_threats == set()


class TestExecuteGuards:
    async def test_no_bot_is_noop(self, bot, blackboard):
        dc = DefenseCoordinator(bot, blackboard)
        dc.bot = None
        # Should short-circuit without raising.
        await dc.execute(0)

    async def test_no_blackboard_is_noop(self, bot, blackboard):
        dc = DefenseCoordinator(bot, blackboard)
        dc.blackboard = None
        await dc.execute(0)


class TestGetStatus:
    def test_status_shape(self, coordinator):
        status = coordinator.get_status()
        assert set(status.keys()) == {
            "threat_level",
            "detected_threats",
            "defending_units",
            "pool_requested",
            "first_queen_requested",
        }

    def test_threat_level_from_blackboard(self, bot, blackboard):
        blackboard.threat.level.name = "HIGH"
        dc = DefenseCoordinator(bot, blackboard)
        assert dc.get_status()["threat_level"] == "HIGH"

    def test_unknown_when_blackboard_missing_threat(self, bot):
        bb = MagicMock()
        bb.threat = None
        dc = DefenseCoordinator(bot, bb)
        assert dc.get_status()["threat_level"] == "UNKNOWN"

    def test_counts_reflect_state(self, coordinator):
        coordinator.detected_threats.update({1, 2, 3})
        coordinator.defending_units.update({10, 20})
        coordinator.pool_requested = True
        coordinator.first_queen_requested = False
        status = coordinator.get_status()
        assert status["detected_threats"] == 3
        assert status["defending_units"] == 2
        assert status["pool_requested"] is True
        assert status["first_queen_requested"] is False
