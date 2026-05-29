# -*- coding: utf-8 -*-
"""
Unit tests for GameStateBlackboard — the shared-state bus used to coordinate
production, authority, building reservations and cached state across managers.

The module is sc2-free (sc2 imports are TYPE_CHECKING only), so these run
everywhere.
"""

import os
import sys

import pytest

sys.path.insert(
    0, os.path.join(os.path.dirname(__file__), "..", "wicked_zerg_challenger")
)

try:
    import blackboard as bb_mod
except ImportError:  # pragma: no cover
    pytest.skip("blackboard not importable", allow_module_level=True)

Blackboard = bb_mod.GameStateBlackboard
ThreatLevel = bb_mod.ThreatLevel
GamePhase = bb_mod.GamePhase
AuthorityMode = bb_mod.AuthorityMode


@pytest.fixture
def bb():
    return Blackboard()


# ---------------------------------------------------------------------------
# Production request queue
# ---------------------------------------------------------------------------


class TestProductionQueue:
    def test_get_next_respects_priority_order(self, bb):
        bb.request_production("drone", 1, "EconomyManager", priority=3)
        bb.request_production("zergling", 1, "DefenseCoordinator", priority=0)
        bb.request_production("roach", 1, "UnitFactory", priority=1)
        # Lowest priority number first.
        assert bb.get_next_production() == ("zergling", 1, "DefenseCoordinator")
        assert bb.get_next_production() == ("roach", 1, "UnitFactory")
        assert bb.get_next_production() == ("drone", 1, "EconomyManager")
        assert bb.get_next_production() is None

    def test_duplicate_request_updates_count(self, bb):
        bb.request_production("roach", 2, "UnitFactory", priority=1)
        bb.request_production("roach", 5, "UnitFactory", priority=1)
        # Same unit + requester at same priority -> updated, not duplicated.
        assert bb.get_next_production() == ("roach", 5, "UnitFactory")
        assert bb.get_next_production() is None

    def test_priority_defaults_to_authority(self, bb):
        # BALANCED: DefenseCoordinator -> priority 0.
        bb.set_authority_mode(AuthorityMode.BALANCED)
        bb.request_production("zergling", 1, "DefenseCoordinator")
        assert bb.production_queue[0] == [("zergling", 1, "DefenseCoordinator")]

    def test_clear_by_requester(self, bb):
        bb.request_production("drone", 1, "EconomyManager", priority=3)
        bb.request_production("roach", 1, "UnitFactory", priority=1)
        bb.clear_production_requests("EconomyManager")
        remaining = [bb.get_next_production(), bb.get_next_production()]
        assert remaining == [("roach", 1, "UnitFactory"), None]

    def test_clear_all(self, bb):
        bb.request_production("drone", 1, "EconomyManager", priority=3)
        bb.request_production("roach", 1, "UnitFactory", priority=1)
        bb.clear_requests()  # alias for clear_production_requests()
        assert bb.get_next_production() is None


# ---------------------------------------------------------------------------
# Dynamic authority priorities
# ---------------------------------------------------------------------------


class TestAuthorityPriority:
    def test_emergency_only_defense_is_top(self, bb):
        bb.set_authority_mode(AuthorityMode.EMERGENCY)
        assert bb.get_authority_priority("DefenseCoordinator") == 0
        assert bb.get_authority_priority("UnitFactory") == 3
        assert bb.get_authority_priority("Whatever") == 3

    def test_combat_prefers_unit_factory(self, bb):
        bb.set_authority_mode(AuthorityMode.COMBAT)
        assert bb.get_authority_priority("UnitFactory") == 0
        assert bb.get_authority_priority("EconomyManager") == 3

    def test_economy_prefers_economy(self, bb):
        bb.set_authority_mode(AuthorityMode.ECONOMY)
        assert bb.get_authority_priority("EconomyManager") == 0
        assert bb.get_authority_priority("AggressiveStrategies") == 3

    def test_unknown_requester_defaults_to_2(self, bb):
        bb.set_authority_mode(AuthorityMode.BALANCED)
        assert bb.get_authority_priority("Mystery") == 2


# ---------------------------------------------------------------------------
# Building reservations (time-based)
# ---------------------------------------------------------------------------


class TestBuildingReservation:
    def test_reserve_then_blocked_until_expiry(self, bb):
        bb.game_time = 100.0
        assert bb.reserve_building("hatchery", "EconomyManager", duration=10.0) is True
        # Still within the window -> second reservation fails.
        bb.game_time = 105.0
        assert bb.reserve_building("hatchery", "UnitFactory", duration=10.0) is False
        assert bb.is_building_reserved("hatchery", duration=10.0) is True

    def test_reservation_expires(self, bb):
        bb.game_time = 100.0
        bb.reserve_building("spire", "UnitFactory", duration=10.0)
        bb.game_time = 111.0  # past the 10s window
        assert bb.is_building_reserved("spire", duration=10.0) is False
        # Now a fresh reservation succeeds.
        assert bb.reserve_building("spire", "EconomyManager", duration=10.0) is True

    def test_unreserved_building(self, bb):
        assert bb.is_building_reserved("nydus") is False


# ---------------------------------------------------------------------------
# Cache with per-key TTL
# ---------------------------------------------------------------------------


class TestCache:
    def test_set_get_roundtrip(self, bb):
        bb.cache_set("k", 42, ttl=5.0)
        assert bb.cache_get("k") == 42

    def test_per_key_ttl_expiry(self, bb):
        bb.game_time = 0.0
        bb.cache_set("short", "v", ttl=1.0)
        bb.cache_set("long", "v", ttl=100.0)
        bb.game_time = 2.0
        # short expired, long still valid (per-key TTL, not a global one)
        assert bb.cache_get("short", default="gone") == "gone"
        assert bb.cache_get("long") == "v"

    def test_missing_key_returns_default(self, bb):
        assert bb.cache_get("nope", default="d") == "d"

    def test_clear(self, bb):
        bb.cache_set("k", 1)
        bb.cache_clear()
        assert bb.cache_get("k", default=None) is None


# ---------------------------------------------------------------------------
# State helpers
# ---------------------------------------------------------------------------


class TestStateHelpers:
    def test_should_defend_on_medium_threat(self, bb):
        bb.update_threat(ThreatLevel.MEDIUM)
        assert bb.should_defend() is True

    def test_should_defend_false_when_calm(self, bb):
        bb.update_threat(ThreatLevel.NONE)
        bb.is_under_attack = False
        assert bb.should_defend() is False

    def test_can_attack_blocked_in_opening(self, bb):
        bb.update_threat(ThreatLevel.LOW)
        bb.game_phase = GamePhase.OPENING
        assert bb.can_attack() is False

    def test_can_attack_when_safe_past_opening(self, bb):
        bb.update_threat(ThreatLevel.LOW)
        bb.is_under_attack = False
        bb.game_phase = GamePhase.MID_GAME
        assert bb.can_attack() is True

    def test_should_expand_requires_no_threat_and_supply(self, bb):
        bb.update_threat(ThreatLevel.NONE)
        bb.is_under_attack = False
        bb.update_resources(minerals=500, vespene=0, supply_used=20, supply_cap=40)
        assert bb.should_expand() is True
        # Supply-blocked -> no expand.
        bb.update_resources(minerals=500, vespene=0, supply_used=40, supply_cap=40)
        assert bb.should_expand() is False


# ---------------------------------------------------------------------------
# Backward-compatible set/get sync
# ---------------------------------------------------------------------------


class TestBackwardCompatState:
    def test_set_enemy_race_syncs_attribute(self, bb):
        bb.set("enemy_race", "Protoss")
        assert bb.enemy_race == "Protoss"
        assert bb.get("enemy_race") == "Protoss"

    def test_set_rush_detected_syncs_threat(self, bb):
        bb.set("is_rush_detected", True)
        assert bb.threat.is_rushing is True

    def test_update_threat_syncs_state_dict(self, bb):
        bb.update_threat(ThreatLevel.HIGH, is_rushing=True)
        assert bb.get("threat_level") == int(ThreatLevel.HIGH)
        assert bb.get("is_rush_detected") is True
