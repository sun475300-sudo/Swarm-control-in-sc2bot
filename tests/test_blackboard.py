# -*- coding: utf-8 -*-
"""Tests for blackboard.py - central game state management."""

import sys
import pytest

sys.path.insert(0, "wicked_zerg_challenger")

from blackboard import (
    GameStateBlackboard,
    ThreatLevel,
    GamePhase,
    AuthorityMode,
    UnitCounts,
    ThreatInfo,
    ResourceState,
)


class TestEnumsAndOrderings:
    def test_threat_level_ordering(self):
        assert ThreatLevel.NONE < ThreatLevel.LOW
        assert ThreatLevel.LOW < ThreatLevel.MEDIUM
        assert ThreatLevel.MEDIUM < ThreatLevel.HIGH
        assert ThreatLevel.HIGH < ThreatLevel.CRITICAL

    def test_threat_level_values(self):
        assert ThreatLevel.NONE == 0
        assert ThreatLevel.CRITICAL == 4

    def test_game_phases_exist(self):
        assert GamePhase.OPENING
        assert GamePhase.EARLY_GAME
        assert GamePhase.MID_GAME
        assert GamePhase.LATE_GAME

    def test_authority_modes_exist(self):
        assert AuthorityMode.EMERGENCY
        assert AuthorityMode.COMBAT
        assert AuthorityMode.STRATEGY
        assert AuthorityMode.ECONOMY
        assert AuthorityMode.BALANCED


class TestUnitCounts:
    def test_default_is_zero(self):
        uc = UnitCounts()
        assert uc.current == 0
        assert uc.pending == 0
        assert uc.total == 0

    def test_total_sums_current_and_pending(self):
        uc = UnitCounts(current=5, pending=3)
        assert uc.total == 8


class TestBlackboardInit:
    def test_initial_state(self):
        bb = GameStateBlackboard()
        assert bb.game_time == 0.0
        assert bb.iteration == 0
        assert bb.game_phase == GamePhase.OPENING
        assert bb.authority_mode == AuthorityMode.BALANCED

    def test_initial_threat_is_none(self):
        bb = GameStateBlackboard()
        assert bb.threat.level == ThreatLevel.NONE

    def test_initial_resources_zero(self):
        bb = GameStateBlackboard()
        assert bb.minerals == 0
        assert bb.vespene == 0
        assert bb.supply_used == 0

    def test_enemy_race_unknown_initially(self):
        bb = GameStateBlackboard()
        assert bb.enemy_race == "Unknown"


class TestUpdateGameInfo:
    def test_opening_phase(self):
        bb = GameStateBlackboard()
        bb.update_game_info(game_time=100.0, iteration=2200)
        assert bb.game_phase == GamePhase.OPENING
        assert bb.game_time == 100.0
        assert bb.iteration == 2200

    def test_early_game_phase(self):
        bb = GameStateBlackboard()
        bb.update_game_info(game_time=200.0)
        assert bb.game_phase == GamePhase.EARLY_GAME

    def test_mid_game_phase(self):
        bb = GameStateBlackboard()
        bb.update_game_info(game_time=500.0)
        assert bb.game_phase == GamePhase.MID_GAME

    def test_late_game_phase(self):
        bb = GameStateBlackboard()
        bb.update_game_info(game_time=800.0)
        assert bb.game_phase == GamePhase.LATE_GAME


class TestResources:
    def test_update_resources(self):
        bb = GameStateBlackboard()
        bb.update_resources(minerals=500, vespene=200, supply_used=50, supply_cap=100)
        assert bb.minerals == 500
        assert bb.vespene == 200
        assert bb.supply_used == 50
        assert bb.supply_cap == 100
        assert bb.resources.supply_left == 50


class TestUnitCounting:
    def test_get_unit_count_default_zero(self):
        bb = GameStateBlackboard()
        uc = bb.get_unit_count("ZERGLING")
        assert uc.current == 0
        assert uc.pending == 0

    def test_update_and_get_unit_count(self):
        bb = GameStateBlackboard()
        bb.update_unit_count("ZERGLING", current=12, pending=4)
        uc = bb.get_unit_count("ZERGLING")
        assert uc.current == 12
        assert uc.pending == 4
        assert uc.total == 16

    def test_update_overwrites_existing(self):
        bb = GameStateBlackboard()
        bb.update_unit_count("ROACH", 5, 0)
        bb.update_unit_count("ROACH", 10, 2)
        uc = bb.get_unit_count("ROACH")
        assert uc.current == 10
        assert uc.pending == 2


class TestThreatUpdates:
    def test_update_threat_sets_level(self):
        bb = GameStateBlackboard()
        bb.update_threat(ThreatLevel.HIGH, enemy_army_supply=25.0)
        assert bb.threat.level == ThreatLevel.HIGH
        assert bb.threat.enemy_army_supply == 25.0

    def test_rush_flag_propagated(self):
        bb = GameStateBlackboard()
        bb.update_threat(ThreatLevel.CRITICAL, is_rushing=True)
        assert bb.threat.is_rushing
        assert bb.state.get("is_rush_detected") is True

    def test_detected_at_recorded_on_medium(self):
        bb = GameStateBlackboard()
        bb.game_time = 100.0
        bb.update_threat(ThreatLevel.MEDIUM)
        assert bb.threat.detected_at == 100.0


class TestSetGet:
    def test_set_then_get(self):
        bb = GameStateBlackboard()
        bb.set("my_key", "my_value")
        assert bb.get("my_key") == "my_value"

    def test_get_missing_returns_default(self):
        bb = GameStateBlackboard()
        assert bb.get("nonexistent", default=42) == 42

    def test_get_missing_returns_none_by_default(self):
        bb = GameStateBlackboard()
        assert bb.get("nonexistent") is None


class TestAuthorityMode:
    def test_set_authority_mode(self):
        bb = GameStateBlackboard()
        bb.set_authority_mode(AuthorityMode.EMERGENCY, reason="Rush detected")
        assert bb.authority_mode == AuthorityMode.EMERGENCY


class TestCache:
    def test_cache_set_and_get(self):
        bb = GameStateBlackboard()
        bb.cache_set("cached_value", 100)
        assert bb.cache_get("cached_value") == 100

    def test_cache_miss_returns_default(self):
        bb = GameStateBlackboard()
        assert bb.cache_get("missing", default="fallback") == "fallback"

    def test_cache_clear_removes_all(self):
        bb = GameStateBlackboard()
        bb.cache_set("a", 1)
        bb.cache_set("b", 2)
        bb.cache_clear()
        assert bb.cache_get("a") is None
        assert bb.cache_get("b") is None
