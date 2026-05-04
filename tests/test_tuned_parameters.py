# -*- coding: utf-8 -*-
"""봇 매니저별 점진 튜닝 파라미터 회귀 방지.

EconomyManager 외 매니저들(QueenManager, IntelManager 등)이 사이클을 거치며
조정해 온 핵심 상수들을 단언으로 고정한다. 안전 범위와 정확값을 함께 검사해
무의도 회귀와 의도된 변경 누락 모두를 즉시 드러낸다.

스킵 정책: 임포트 실패 시 모듈 단위 skip (sc2 미설치 환경 대응).
"""

from unittest.mock import Mock

import pytest


# ────────────────────────────────────────────────────────────
# QueenManager
# ────────────────────────────────────────────────────────────


class TestQueenManagerTunedParameters:
    """QueenManager의 인젝트/점막/퀸 생산 튜닝 파라미터 회귀 방지."""

    def setup_method(self):
        try:
            from wicked_zerg_challenger.queen_manager import QueenManager
        except ImportError as e:
            pytest.skip(f"QueenManager not importable: {e}")

        self.manager = QueenManager(Mock())

    def test_inject_cooldown_matches_sc2_spawn_larva(self):
        """SC2 Spawn Larva 쿨다운 28.57초 + 여유 0.43초 = 29.0초."""
        assert self.manager.inject_cooldown == 29.0

    def test_inject_energy_threshold(self):
        """인젝트 에너지 임계 = 25 (SC2 능력 비용)."""
        assert self.manager.inject_energy_threshold == 25

    def test_max_inject_distance(self):
        """인젝트 사거리 — 8.0 (4→8로 확장; SC2 기본 + 이동 보정)."""
        assert self.manager.max_inject_distance == 8.0

    def test_creep_energy_threshold_aggressive(self):
        """점막 종양 에너지 임계 — 20 (25→20로 공격적 조정)."""
        assert self.manager.creep_energy_threshold <= 25
        assert self.manager.creep_energy_threshold == 20

    def test_creep_spread_cooldown_fast(self):
        """점막 확산 쿨다운 — 4.0초 (6→4로 단축)."""
        assert self.manager.creep_spread_cooldown <= 6.0
        assert self.manager.creep_spread_cooldown == 4.0

    def test_inject_queen_creep_threshold(self):
        """인젝트 퀸 점막 보조 임계 에너지 — 35 (40→35)."""
        assert self.manager.inject_queen_creep_threshold == 35

    def test_max_queens_per_base(self):
        """기지당 퀸 — 2마리."""
        assert self.manager.max_queens_per_base == 2

    def test_creep_queen_bonus(self):
        """점막 전용 퀸 추가 — 4마리 (3→4로 강화)."""
        assert self.manager.creep_queen_bonus >= 3
        assert self.manager.creep_queen_bonus == 4

    def test_transfuse_thresholds(self):
        """수혈(Transfuse) 발동 조건 — 에너지 50 / 체력 50%."""
        assert self.manager.transfuse_energy_threshold == 50
        assert self.manager.transfuse_cooldown == 1.0
        assert self.manager.transfuse_health_threshold == 0.5


# ────────────────────────────────────────────────────────────
# IntelManager
# ────────────────────────────────────────────────────────────


class TestIntelManagerTunedParameters:
    """IntelManager 정찰 갱신 주기/숨은 테크 알림 매핑 회귀 방지."""

    def setup_method(self):
        try:
            from wicked_zerg_challenger.intel_manager import IntelManager
        except ImportError as e:
            pytest.skip(f"IntelManager not importable: {e}")

        self.manager = IntelManager(Mock())

    def test_update_interval(self):
        """정보 갱신 주기 — 8 iter (~0.5초)."""
        assert self.manager.update_interval == 8

    def test_hidden_tech_alerts_required_keys(self):
        """필수 hidden-tech 키와 매핑된 알림 코드가 모두 존재."""
        required = {
            "DARKSHRINE": "DT_INCOMING",
            "STARGATE": "AIR_INCOMING",
            "FUSIONCORE": "BC_INCOMING",
            "TEMPLARARCHIVE": "HT_INCOMING",
            "NYDUSNETWORK": "NYDUS_INCOMING",
            "FLEETBEACON": "CARRIER_INCOMING",
        }
        for k, v in required.items():
            assert k in self.manager._hidden_tech_alerts
            assert self.manager._hidden_tech_alerts[k] == v

    def test_high_threat_types_complete(self):
        """고위협 유닛 집합이 비어있지 않고 핵심 유닛을 포함."""
        critical = {
            "SIEGETANK",
            "BROODLORD",
            "ULTRALISK",
            "COLOSSUS",
            "BATTLECRUISER",
        }
        assert critical.issubset(self.manager._high_threat_types)

    def test_threat_level_initial(self):
        """초기 위협 단계 = 'none'."""
        assert self.manager._threat_level == "none"

    def test_initial_under_attack_false(self):
        """초기 _under_attack 플래그 = False."""
        assert self.manager._under_attack is False
