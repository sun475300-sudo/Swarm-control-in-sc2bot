# -*- coding: utf-8 -*-
"""
Unit Tests for GameStateBlackboard

테스트 범위:
- 기본 set/get 호환성 API
- 게임 단계 자동 결정 (update_game_info)
- 자원 / 유닛 카운트 / 위협 / 권한 모드 업데이트
- 생산 요청 우선순위 큐 (request_production / get_next_production)
- 건물 예약 (reserve_building / is_building_reserved)
- 캐시 시스템 (per-key TTL, Bug fix #6)
"""

import os
import sys

import pytest

# blackboard.py 는 wicked_zerg_challenger 패키지 내부에서 `from utils.logger import ...`
# 와 같이 패키지 상대가 아닌 sibling import 를 사용한다. 따라서 패키지 디렉토리를
# sys.path 에 추가해 sibling 모듈을 직접 import 가능하게 한다.
_PKG_DIR = os.path.join(os.path.dirname(__file__), "..", "wicked_zerg_challenger")
if _PKG_DIR not in sys.path:
    sys.path.insert(0, _PKG_DIR)

try:
    from blackboard import (  # type: ignore
        GameStateBlackboard,
        GamePhase,
        ThreatLevel,
        AuthorityMode,
    )
except ImportError:
    pytest.skip("blackboard not available", allow_module_level=True)


@pytest.fixture
def bb():
    return GameStateBlackboard()


# ============================================================================
# 호환 API: set/get
# ============================================================================
class TestCompatibilitySetGet:
    def test_set_get_roundtrip(self, bb):
        bb.set("custom_key", 42)
        assert bb.get("custom_key") == 42

    def test_get_default_when_missing(self, bb):
        assert bb.get("missing_key", default="X") == "X"

    def test_set_strategy_mode_syncs_attribute(self, bb):
        bb.set("strategy_mode", "AGGRESSIVE")
        assert bb.strategy_mode == "AGGRESSIVE"

    def test_set_enemy_race_syncs_attribute(self, bb):
        bb.set("enemy_race", "Zerg")
        assert bb.enemy_race == "Zerg"

    def test_set_is_rush_detected_syncs_threat(self, bb):
        bb.set("is_rush_detected", True)
        assert bb.threat.is_rushing is True


# ============================================================================
# update_game_info: 게임 단계 자동 분류
# ============================================================================
class TestGamePhaseTransitions:
    def test_opening_phase_under_180s(self, bb):
        bb.update_game_info(60.0, 100)
        assert bb.game_phase == GamePhase.OPENING
        assert bb.iteration == 100

    def test_early_game_phase_180_to_360(self, bb):
        bb.update_game_info(200.0)
        assert bb.game_phase == GamePhase.EARLY_GAME

    def test_mid_game_phase_360_to_720(self, bb):
        bb.update_game_info(400.0)
        assert bb.game_phase == GamePhase.MID_GAME

    def test_late_game_phase_above_720(self, bb):
        bb.update_game_info(1000.0)
        assert bb.game_phase == GamePhase.LATE_GAME


# ============================================================================
# update_resources
# ============================================================================
class TestResourceUpdate:
    def test_update_resources_syncs_flat_attributes(self, bb):
        bb.update_resources(minerals=500, vespene=200, supply_used=20, supply_cap=30)
        assert bb.minerals == 500
        assert bb.vespene == 200
        assert bb.supply_used == 20
        assert bb.supply_cap == 30
        assert bb.resources.supply_left == 10

    def test_resources_supply_blocked(self, bb):
        bb.update_resources(0, 0, 30, 30)
        # is_supply_blocked 는 property
        assert bb.resources.is_supply_blocked is True

    def test_resources_supply_not_blocked(self, bb):
        bb.update_resources(0, 0, 20, 30)
        assert bb.resources.is_supply_blocked is False


# ============================================================================
# update_unit_count / get_unit_count
# ============================================================================
class TestUnitCounts:
    def test_default_count_is_empty(self, bb):
        counts = bb.get_unit_count("ZERGLING")
        assert counts.current == 0
        assert counts.pending == 0
        # total 은 property
        assert counts.total == 0

    def test_update_unit_count_overwrites(self, bb):
        bb.update_unit_count("ZERGLING", current=10, pending=4)
        counts = bb.get_unit_count("ZERGLING")
        assert counts.current == 10
        assert counts.pending == 4
        assert counts.total == 14

    def test_unit_count_isolated_by_type(self, bb):
        bb.update_unit_count("ZERGLING", 5, 1)
        bb.update_unit_count("ROACH", 3, 0)
        assert bb.get_unit_count("ZERGLING").current == 5
        assert bb.get_unit_count("ROACH").current == 3


# ============================================================================
# update_threat
# ============================================================================
class TestThreatUpdate:
    def test_threat_basic_update(self, bb):
        bb.update_threat(
            level=ThreatLevel.HIGH,
            enemy_army_supply=20.0,
            enemy_units_near_base=5,
        )
        assert bb.threat.level == ThreatLevel.HIGH
        assert bb.threat.enemy_army_supply == 20.0

    def test_threat_records_detection_time_when_medium_or_higher(self, bb):
        bb.game_time = 90.0
        bb.update_threat(level=ThreatLevel.MEDIUM)
        assert bb.threat.detected_at == 90.0

    def test_threat_does_not_overwrite_detection_time(self, bb):
        bb.game_time = 90.0
        bb.update_threat(level=ThreatLevel.MEDIUM)
        bb.game_time = 200.0
        bb.update_threat(level=ThreatLevel.HIGH)
        # detected_at은 최초 감지 시간을 보존
        assert bb.threat.detected_at == 90.0

    def test_threat_low_level_does_not_record_detection(self, bb):
        bb.game_time = 50.0
        bb.update_threat(level=ThreatLevel.LOW)
        assert bb.threat.detected_at == 0.0


# ============================================================================
# Authority Priority
# ============================================================================
class TestAuthorityPriority:
    def test_emergency_priorities_defense_first(self, bb):
        bb.set_authority_mode(AuthorityMode.EMERGENCY)
        assert bb.get_authority_priority("DefenseCoordinator") == 0
        assert bb.get_authority_priority("EconomyManager") == 3

    def test_combat_priorities(self, bb):
        bb.set_authority_mode(AuthorityMode.COMBAT)
        assert bb.get_authority_priority("UnitFactory") == 0
        assert bb.get_authority_priority("DefenseCoordinator") == 1

    def test_economy_mode_priorities(self, bb):
        bb.set_authority_mode(AuthorityMode.ECONOMY)
        assert bb.get_authority_priority("EconomyManager") == 0

    def test_unknown_requester_default_priority(self, bb):
        bb.set_authority_mode(AuthorityMode.BALANCED)
        assert bb.get_authority_priority("UnknownManager") == 2


# ============================================================================
# Auto Adjust Authority
# ============================================================================
class TestAutoAdjustAuthority:
    def test_rushing_triggers_emergency(self, bb):
        bb.threat.is_rushing = True
        bb.auto_adjust_authority()
        assert bb.authority_mode == AuthorityMode.EMERGENCY

    def test_critical_threat_triggers_emergency(self, bb):
        bb.threat.level = ThreatLevel.CRITICAL
        bb.auto_adjust_authority()
        assert bb.authority_mode == AuthorityMode.EMERGENCY

    def test_high_threat_triggers_combat(self, bb):
        bb.threat.level = ThreatLevel.HIGH
        bb.auto_adjust_authority()
        assert bb.authority_mode == AuthorityMode.COMBAT


# ============================================================================
# Production Queue
# ============================================================================
class TestProductionQueue:
    def test_request_production_default_priority(self, bb):
        bb.set_authority_mode(AuthorityMode.BALANCED)
        bb.request_production("ZERGLING", 5, "UnitFactory")
        # priority 1 (BALANCED → UnitFactory = 1)
        assert len(bb.production_queue[1]) == 1

    def test_explicit_priority_overrides_authority(self, bb):
        bb.request_production("ZERGLING", 3, "EconomyManager", priority=0)
        assert len(bb.production_queue[0]) == 1

    def test_duplicate_request_updates_count(self, bb):
        bb.request_production("ZERGLING", 5, "UnitFactory", priority=1)
        bb.request_production("ZERGLING", 12, "UnitFactory", priority=1)
        # 같은 (unit_type, requester) 는 새 count 로 갱신
        assert len(bb.production_queue[1]) == 1
        utype, count, req = bb.production_queue[1][0]
        assert count == 12

    def test_get_next_production_priority_order(self, bb):
        bb.request_production("ROACH", 1, "Combat", priority=2)
        bb.request_production("ZERGLING", 2, "Defense", priority=0)
        # priority 0 이 먼저
        first = bb.get_next_production()
        assert first[0] == "ZERGLING"

    def test_get_next_production_empty_returns_none(self, bb):
        assert bb.get_next_production() is None

    def test_clear_production_requests_all(self, bb):
        bb.request_production("X", 1, "A", priority=0)
        bb.request_production("Y", 1, "B", priority=2)
        bb.clear_production_requests()
        assert sum(len(q) for q in bb.production_queue.values()) == 0

    def test_clear_production_requests_by_requester(self, bb):
        bb.request_production("X", 1, "Keep", priority=1)
        bb.request_production("Y", 1, "Drop", priority=1)
        bb.clear_production_requests("Drop")
        remaining = bb.production_queue[1]
        assert len(remaining) == 1
        assert remaining[0][2] == "Keep"


# ============================================================================
# Building Reservations
# ============================================================================
class TestBuildingReservations:
    def test_reserve_building_first_time_succeeds(self, bb):
        ok = bb.reserve_building("SPAWNINGPOOL", "ProductionResilience")
        assert ok is True

    def test_reserve_building_within_duration_blocks(self, bb):
        bb.game_time = 0.0
        bb.reserve_building("SPAWNINGPOOL", "A", duration=10.0)
        bb.game_time = 5.0
        ok = bb.reserve_building("SPAWNINGPOOL", "B", duration=10.0)
        assert ok is False

    def test_reserve_building_after_duration_succeeds(self, bb):
        bb.game_time = 0.0
        bb.reserve_building("SPAWNINGPOOL", "A", duration=10.0)
        bb.game_time = 11.0
        ok = bb.reserve_building("SPAWNINGPOOL", "B", duration=10.0)
        assert ok is True

    def test_is_building_reserved(self, bb):
        bb.game_time = 0.0
        bb.reserve_building("EXTRACTOR", "A", duration=10.0)
        assert bb.is_building_reserved("EXTRACTOR", duration=10.0) is True
        bb.game_time = 20.0
        assert bb.is_building_reserved("EXTRACTOR", duration=10.0) is False

    def test_is_building_reserved_unknown_returns_false(self, bb):
        assert bb.is_building_reserved("NEVER_RESERVED") is False


# ============================================================================
# Cache (Bug fix #6: per-key TTL)
# ============================================================================
class TestCachePerKeyTTL:
    def test_cache_set_get(self, bb):
        bb.cache_set("k1", "v1")
        assert bb.cache_get("k1") == "v1"

    def test_cache_get_default_when_missing(self, bb):
        assert bb.cache_get("nope", default=99) == 99

    def test_cache_per_key_ttl_independent(self, bb):
        """key1 은 TTL 1.0 (기본), key2 는 TTL 100.0 — 시간 경과 시 분리되어 만료"""
        bb.game_time = 0.0
        bb.cache_set("short", "S")
        bb.cache_set("long", "L", ttl=100.0)

        bb.game_time = 5.0  # short 는 만료, long 은 살아있어야 함
        assert bb.cache_get("short") is None
        assert bb.cache_get("long") == "L"

    def test_cache_clear_removes_all(self, bb):
        bb.cache_set("a", 1)
        bb.cache_set("b", 2, ttl=10.0)
        bb.cache_clear()
        assert bb.cache_get("a") is None
        assert bb.cache_get("b") is None
        assert bb._cache_ttls == {}


# ============================================================================
# Helper: should_defend
# ============================================================================
class TestShouldDefend:
    def test_should_defend_when_medium_threat(self, bb):
        bb.threat.level = ThreatLevel.MEDIUM
        assert bb.should_defend() is True

    def test_should_defend_when_under_attack(self, bb):
        bb.threat.level = ThreatLevel.NONE
        bb.is_under_attack = True
        assert bb.should_defend() is True

    def test_should_defend_when_rushing(self, bb):
        bb.threat.level = ThreatLevel.NONE
        bb.threat.is_rushing = True
        assert bb.should_defend() is True

    def test_should_not_defend_when_safe(self, bb):
        bb.threat.level = ThreatLevel.NONE
        bb.is_under_attack = False
        bb.threat.is_rushing = False
        assert bb.should_defend() is False


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
