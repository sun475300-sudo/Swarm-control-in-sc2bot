# -*- coding: utf-8 -*-
"""
Unit Tests for SituationalAwareness

테스트 범위:
- SITREP 생성 (update_sitrep) — 모든 필드 채워지는지
- on_step throttling (update_interval=2.0초)
- _assess_threat_level — 기지 HP 90% 이하 + 적 근접 시 CRITICAL
- _get_game_phase — 시간 기반 OPENING/MIDGAME/LATEGAME 폴백
- _get_intel_summary — CLOAK_TECH, AIR_THREAT, SPLASH_DAMAGE, 오버로드 제외 로직
- 히스토리 보관 (150개 cap)
"""

import pytest
from unittest.mock import MagicMock

try:
    from wicked_zerg_challenger.core.situational_awareness import (
        SituationalAwareness,
        ThreatLevel,
        OpportunityIndex,
    )
except ImportError:
    pytest.skip("situational_awareness not available", allow_module_level=True)


# ============================================================================
# 테스트용 Mock
# ============================================================================

def _mock_unit(name, **kwargs):
    """type_id.name 을 가진 unit mock"""
    u = MagicMock()
    u.type_id.name = name
    u.is_structure = kwargs.get("is_structure", False)
    u.is_flying = kwargs.get("is_flying", False)
    u.health_percentage = kwargs.get("health_percentage", 1.0)
    u.position = kwargs.get("position", (0, 0))
    return u


class _MockUnits:
    def __init__(self, units):
        self._units = list(units)

    def __iter__(self):
        return iter(self._units)

    def __len__(self):
        return len(self._units)

    @property
    def amount(self):
        return len(self._units)

    @property
    def exists(self):
        return len(self._units) > 0

    def closer_than(self, dist, position_or_unit):
        # 단순화: 모든 유닛이 가깝다고 가정 (position 비교 생략)
        return _MockUnits(self._units)


class _MockBot:
    def __init__(self, **kwargs):
        self.time = kwargs.get("time", 0.0)
        self.iteration = kwargs.get("iteration", 0)
        self.minerals = kwargs.get("minerals", 100)
        self.vespene = kwargs.get("vespene", 50)
        self.supply_used = kwargs.get("supply_used", 12)
        self.supply_cap = kwargs.get("supply_cap", 14)
        self.workers = _MockUnits(kwargs.get("workers", []))
        self.townhalls = _MockUnits(kwargs.get("townhalls", []))
        self.units = _MockUnits(kwargs.get("units", []))
        self.enemy_units = _MockUnits(kwargs.get("enemy_units", []))
        self.enemy_structures = _MockUnits(kwargs.get("enemy_structures", []))
        self.enemy_race = kwargs.get("enemy_race", "Terran")


# ============================================================================
# 초기화
# ============================================================================
class TestInitialization:
    def test_default_state(self):
        sa = SituationalAwareness(_MockBot())
        assert sa.last_sitrep == {}
        assert sa.last_update_time == 0.0
        assert sa.update_interval == 2.0
        assert sa.threat_level == ThreatLevel.NONE
        assert sa.opportunity_index == OpportunityIndex.NONE
        assert sa.threat_history == []
        assert sa.sitrep_history == []


# ============================================================================
# update_sitrep
# ============================================================================
class TestUpdateSitrep:
    def test_sitrep_basic_structure(self):
        bot = _MockBot(minerals=300, vespene=150, supply_used=20, supply_cap=30)
        sa = SituationalAwareness(bot)
        sa.update_sitrep()

        sitrep = sa.get_latest_sitrep()
        assert "timestamp" in sitrep
        assert "frame" in sitrep
        assert "game_phase" in sitrep
        assert "status" in sitrep
        assert "economy" in sitrep
        assert "military" in sitrep
        assert "intelligence" in sitrep

    def test_sitrep_economy_filled(self):
        bot = _MockBot(minerals=500, vespene=200, supply_used=15, supply_cap=20,
                       workers=[_mock_unit("DRONE") for _ in range(15)],
                       townhalls=[_mock_unit("HATCHERY"), _mock_unit("HATCHERY")])
        sa = SituationalAwareness(bot)
        sa.update_sitrep()
        eco = sa.get_latest_sitrep()["economy"]
        assert eco["minerals"] == 500
        assert eco["vespene"] == 200
        assert eco["supply"] == "15/20"
        assert eco["workers"] == 15
        assert eco["bases"] == 2

    def test_sitrep_includes_intel(self):
        bot = _MockBot(enemy_race="Zerg")
        sa = SituationalAwareness(bot)
        sa.update_sitrep()
        intel = sa.get_latest_sitrep()["intelligence"]
        assert "race" in intel
        assert "threats" in intel
        assert "detected_bases_count" in intel

    def test_sitrep_history_capped_at_150(self):
        bot = _MockBot()
        sa = SituationalAwareness(bot)
        # 200번 SITREP 생성 → 150개로 cap
        for i in range(200):
            sa.bot.iteration = i
            sa.update_sitrep()
        assert len(sa.sitrep_history) == 150


# ============================================================================
# on_step throttling
# ============================================================================
class TestThrottling:
    def test_first_call_triggers_update(self):
        bot = _MockBot(time=0.0)
        sa = SituationalAwareness(bot)
        # last_update_time=0.0, time=0.0 → diff=0 < 2.0 → skip 첫 호출
        # → 첫 호출은 throttle 됨
        sa.on_step(0)
        assert sa.last_sitrep == {}

    def test_after_interval_triggers_update(self):
        bot = _MockBot(time=0.0)
        sa = SituationalAwareness(bot)
        bot.time = 2.5
        sa.on_step(1)
        assert sa.last_sitrep != {}

    def test_within_interval_skipped(self):
        bot = _MockBot(time=10.0)
        sa = SituationalAwareness(bot)
        sa.on_step(1)  # time=10, last=0 → 10>2 → 업데이트, last_update_time=10
        first_sitrep = sa.last_sitrep.copy()

        bot.time = 11.0
        bot.iteration = 999  # 변경 사항 있어도 throttle 으로 무시되어야 함
        sa.on_step(2)
        # 1초만 지났으므로 throttle (업데이트 안 됨)
        assert sa.last_sitrep == first_sitrep


# ============================================================================
# Threat Level Assessment
# ============================================================================
class TestThreatLevel:
    def test_no_threat_when_healthy_base(self):
        bot = _MockBot(townhalls=[_mock_unit("HATCHERY", health_percentage=1.0)])
        sa = SituationalAwareness(bot)
        assert sa._assess_threat_level() == ThreatLevel.NONE

    def test_critical_when_base_damaged_and_enemy_close(self):
        damaged_base = _mock_unit("HATCHERY", health_percentage=0.7)
        enemy = _mock_unit("MARINE")
        bot = _MockBot(townhalls=[damaged_base], enemy_units=[enemy])
        sa = SituationalAwareness(bot)
        assert sa._assess_threat_level() == ThreatLevel.CRITICAL

    def test_no_critical_when_base_damaged_no_enemy_near(self):
        # 적이 없으면 critical 아님
        damaged_base = _mock_unit("HATCHERY", health_percentage=0.7)
        bot = _MockBot(townhalls=[damaged_base], enemy_units=[])
        sa = SituationalAwareness(bot)
        assert sa._assess_threat_level() == ThreatLevel.NONE


# ============================================================================
# Game Phase
# ============================================================================
class TestGamePhase:
    def test_opening_under_300s(self):
        bot = _MockBot(time=120.0)
        sa = SituationalAwareness(bot)
        assert sa._get_game_phase() == "OPENING"

    def test_midgame_300_to_600(self):
        bot = _MockBot(time=400.0)
        sa = SituationalAwareness(bot)
        assert sa._get_game_phase() == "MIDGAME"

    def test_lategame_above_600(self):
        bot = _MockBot(time=900.0)
        sa = SituationalAwareness(bot)
        assert sa._get_game_phase() == "LATEGAME"


# ============================================================================
# Intel Summary
# ============================================================================
class TestIntelSummary:
    def test_clean_intel_no_threats(self):
        bot = _MockBot()
        sa = SituationalAwareness(bot)
        intel = sa._get_intel_summary()
        assert intel["threats"] == []
        assert intel["detected_bases_count"] == 0

    def test_cloak_tech_detected_from_dark_shrine(self):
        ds = _mock_unit("DARKSHRINE", is_structure=True)
        bot = _MockBot(enemy_structures=[ds])
        sa = SituationalAwareness(bot)
        intel = sa._get_intel_summary()
        assert "CLOAK_TECH" in intel["threats"]

    def test_air_threat_detected_from_starport(self):
        sp = _mock_unit("STARPORT", is_structure=True)
        bot = _MockBot(enemy_structures=[sp])
        sa = SituationalAwareness(bot)
        intel = sa._get_intel_summary()
        assert "AIR_THREAT" in intel["threats"]

    def test_overlord_does_not_trigger_air_threat(self):
        """오버로드 같은 비전투 비행유닛은 AIR_THREAT 트리거 안 함"""
        ovr = _mock_unit("OVERLORD", is_structure=False, is_flying=True)
        bot = _MockBot(enemy_units=[ovr])
        sa = SituationalAwareness(bot)
        intel = sa._get_intel_summary()
        assert "AIR_THREAT" not in intel["threats"]

    def test_mutalisk_triggers_air_threat(self):
        """뮤탈리스크 같은 전투 비행유닛은 AIR_THREAT 트리거"""
        mut = _mock_unit("MUTALISK", is_structure=False, is_flying=True)
        bot = _MockBot(enemy_units=[mut])
        sa = SituationalAwareness(bot)
        intel = sa._get_intel_summary()
        assert "AIR_THREAT" in intel["threats"]

    def test_splash_detected_from_baneling_nest(self):
        bn = _mock_unit("BANELINGNEST", is_structure=True)
        bot = _MockBot(enemy_structures=[bn])
        sa = SituationalAwareness(bot)
        intel = sa._get_intel_summary()
        assert "SPLASH_DAMAGE" in intel["threats"]

    def test_known_bases_counted(self):
        h1 = _mock_unit("HATCHERY", is_structure=True)
        h2 = _mock_unit("LAIR", is_structure=True)
        random_struct = _mock_unit("EXTRACTOR", is_structure=True)
        bot = _MockBot(enemy_structures=[h1, h2, random_struct])
        sa = SituationalAwareness(bot)
        intel = sa._get_intel_summary()
        assert intel["detected_bases_count"] == 2  # extractor 제외


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
