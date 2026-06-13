# -*- coding: utf-8 -*-
"""
GameStateBlackboard 테스트 - 게임 상태 중앙 관리
"""

import sys
from pathlib import Path

import pytest

PROJECT_ROOT = Path(__file__).parent.parent
BOT_ROOT = PROJECT_ROOT / "wicked_zerg_challenger"
if str(BOT_ROOT) not in sys.path:
    sys.path.insert(0, str(BOT_ROOT))


@pytest.fixture
def blackboard():
    from blackboard import GameStateBlackboard
    return GameStateBlackboard()


class TestEnums:
    def test_threat_level_ordering(self):
        from blackboard import ThreatLevel
        assert ThreatLevel.NONE < ThreatLevel.LOW < ThreatLevel.MEDIUM
        assert ThreatLevel.HIGH < ThreatLevel.CRITICAL

    def test_game_phase_values(self):
        from blackboard import GamePhase
        assert GamePhase.OPENING.value == "opening"
        assert GamePhase.LATE_GAME.value == "late_game"

    def test_authority_modes(self):
        from blackboard import AuthorityMode
        assert AuthorityMode.EMERGENCY.value == "emergency"
        assert AuthorityMode.BALANCED.value == "balanced"


class TestUnitCounts:
    def test_total(self):
        from blackboard import UnitCounts
        assert UnitCounts(current=5, pending=3).total == 8

    def test_defaults(self):
        from blackboard import UnitCounts
        u = UnitCounts()
        assert u.current == 0 and u.pending == 0 and u.total == 0


class TestResourceState:
    def test_supply_blocked_true(self):
        from blackboard import ResourceState
        assert ResourceState(supply_used=20, supply_left=0).is_supply_blocked is True

    def test_supply_blocked_false_when_room(self):
        from blackboard import ResourceState
        assert ResourceState(supply_used=20, supply_left=4).is_supply_blocked is False

    def test_supply_not_blocked_at_max(self):
        from blackboard import ResourceState
        assert ResourceState(supply_used=200, supply_left=0).is_supply_blocked is False


class TestInit:
    def test_initial_state(self, blackboard):
        from blackboard import GamePhase, AuthorityMode
        assert blackboard.game_time == 0.0
        assert blackboard.iteration == 0
        assert blackboard.game_phase == GamePhase.OPENING
        assert blackboard.authority_mode == AuthorityMode.BALANCED

    def test_production_queue_priorities(self, blackboard):
        assert len(blackboard.production_queue) == 4
        for p in range(4):
            assert blackboard.production_queue[p] == []


class TestGetSet:
    def test_set_get(self, blackboard):
        blackboard.set("k", "v")
        assert blackboard.get("k") == "v"

    def test_get_default(self, blackboard):
        assert blackboard.get("missing", "default") == "default"

    def test_set_strategy_mode_syncs(self, blackboard):
        blackboard.set("strategy_mode", "AGGRESSIVE")
        assert blackboard.strategy_mode == "AGGRESSIVE"

    def test_set_enemy_race_syncs(self, blackboard):
        blackboard.set("enemy_race", "Terran")
        assert blackboard.enemy_race == "Terran"


class TestGamePhaseTransitions:
    def test_opening(self, blackboard):
        from blackboard import GamePhase
        blackboard.update_game_info(60.0, iteration=100)
        assert blackboard.game_phase == GamePhase.OPENING

    def test_early(self, blackboard):
        from blackboard import GamePhase
        blackboard.update_game_info(240.0)
        assert blackboard.game_phase == GamePhase.EARLY_GAME

    def test_mid(self, blackboard):
        from blackboard import GamePhase
        blackboard.update_game_info(500.0)
        assert blackboard.game_phase == GamePhase.MID_GAME

    def test_late(self, blackboard):
        from blackboard import GamePhase
        blackboard.update_game_info(800.0)
        assert blackboard.game_phase == GamePhase.LATE_GAME


class TestProductionQueue:
    def test_request_and_get(self, blackboard):
        blackboard.request_production("ZERGLING", 5, priority=1, requester="test")
        result = blackboard.get_next_production()
        assert result is not None

    def test_clear_requests(self, blackboard):
        blackboard.request_production("ROACH", 3, priority=1, requester="test")
        blackboard.clear_production_requests()
        # After clearing, queue should be empty
        result = blackboard.get_next_production()
        assert result is None


class TestThreatInfo:
    def test_initial_threat(self, blackboard):
        from blackboard import ThreatLevel
        assert blackboard.threat.level == ThreatLevel.NONE
        assert blackboard.threat.is_rushing is False
