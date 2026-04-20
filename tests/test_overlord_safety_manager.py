# -*- coding: utf-8 -*-
"""Tests for OverlordSafetyManager."""

import sys
import pytest

sys.path.insert(0, "wicked_zerg_challenger")

from overlord_safety_manager import OverlordSafetyManager


class _FakeBot:
    def __init__(self):
        self.time = 0.0


class TestInitialization:
    def test_instantiate(self):
        mgr = OverlordSafetyManager(_FakeBot())
        assert mgr.safe_spots == []
        assert mgr._pillars_calculated is False

    def test_default_constants(self):
        mgr = OverlordSafetyManager(_FakeBot())
        assert mgr.SAFETY_DISTANCE > 0
        assert mgr.RETREAT_DISTANCE > 0

    def test_safety_distance_greater_than_retreat(self):
        mgr = OverlordSafetyManager(_FakeBot())
        # Safety distance should exceed retreat distance
        assert mgr.SAFETY_DISTANCE > mgr.RETREAT_DISTANCE


class TestReset:
    def test_reset_clears_state(self):
        mgr = OverlordSafetyManager(_FakeBot())
        # Seed state
        mgr.safe_spots.append("fake_spot")
        mgr._pillars_calculated = True
        mgr.overlord_assignments[123] = "pos"
        mgr.fleeing_overlords.add(456)

        mgr.reset()

        assert mgr.safe_spots == []
        assert mgr._pillars_calculated is False
        assert len(mgr.overlord_assignments) == 0
        assert len(mgr.fleeing_overlords) == 0


class TestOverlordAssignments:
    def test_assignments_start_empty(self):
        mgr = OverlordSafetyManager(_FakeBot())
        assert len(mgr.overlord_assignments) == 0

    def test_fleeing_overlords_start_empty(self):
        mgr = OverlordSafetyManager(_FakeBot())
        assert len(mgr.fleeing_overlords) == 0

    def test_assignment_tracking(self):
        mgr = OverlordSafetyManager(_FakeBot())
        mgr.overlord_assignments[100] = (0.0, 0.0)
        mgr.overlord_assignments[200] = (5.0, 5.0)
        assert len(mgr.overlord_assignments) == 2


class TestCalculateSafeSpots:
    def test_no_game_info_returns_gracefully(self):
        mgr = OverlordSafetyManager(_FakeBot())
        # Bot has no game_info attribute - should not crash
        mgr._calculate_safe_spots()
        assert mgr.safe_spots == []


class TestStateBetweenGames:
    def test_multiple_resets_are_idempotent(self):
        mgr = OverlordSafetyManager(_FakeBot())
        mgr.reset()
        mgr.reset()
        mgr.reset()
        assert mgr.safe_spots == []
        assert not mgr._pillars_calculated
