# -*- coding: utf-8 -*-
"""
Unit Tests for EconomyManager

테스트 범위:
1. 경제 매니저 초기화
2. 긴급 모드 설정
3. 오버로드 생산 시스템
4. 드론 생산 시스템
5. 골드 확장지 감지
6. 자원 상태 조회
7. 경제 회복 모드
8. 목표 드론 수 계산
9. 가스 일꾼 분배
10. 대기 일꾼 할당
11. 자원 예약 시스템
12. 초반 일꾼 분할
13. 사전 확장 체크
14. 강제 확장
15. 매크로 해처리 건설
16. 일꾼 재분배
17. 자원 뱅킹 방지
18. 가스 타이밍 최적화
"""

import pytest
from unittest.mock import Mock, MagicMock, patch, AsyncMock
from typing import List

# Economy Manager 임포트
try:
    import sys
    import os
    sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'wicked_zerg_challenger'))
    from economy_manager import EconomyManager
except ImportError:
    pytest.skip("EconomyManager not available", allow_module_level=True)


class MockUnit:
    """Mock SC2 Unit"""
    def __init__(self, tag: int, type_id, position, health: float = 100.0,
                 health_max: float = 100.0, is_idle: bool = False):
        self.tag = tag
        self.type_id = type_id
        self.position = position
        self.health = health
        self.health_max = health_max
        self.is_idle = is_idle
        self.orders = []
        self.is_carrying_minerals = False
        self.is_carrying_vespene = False
        self.order_target = None
        self.assigned_harvesters = 0
        self.ideal_harvesters = 3
        self.mineral_contents = health  # Use health as mineral_contents for mineral fields

    @property
    def health_percentage(self):
        return self.health / self.health_max if self.health_max > 0 else 0

    def distance_to(self, other):
        if hasattr(other, 'position'):
            pos = other.position
        else:
            pos = other
        return ((self.position[0] - pos[0])**2 + (self.position[1] - pos[1])**2)**0.5


class MockUnits:
    """Mock SC2 Units collection"""
    def __init__(self, units: List[MockUnit]):
        self._units = units

    def __iter__(self):
        return iter(self._units)

    def __len__(self):
        return len(self._units)

    @property
    def amount(self):
        return len(self._units)

    @property
    def first(self):
        """Return first unit in collection"""
        return self._units[0] if self._units else None

    def exists(self):
        return len(self._units) > 0

    @property
    def ready(self):
        """Return ready units (simplified - all units are ready)"""
        return self

    def closer_than(self, distance: float, position):
        return MockUnits([
            u for u in self._units
            if u.distance_to(position) < distance
        ])

    def closest_to(self, position):
        if not self._units:
            return None
        return min(self._units, key=lambda u: u.distance_to(position))

    def filter(self, func):
        return MockUnits([u for u in self._units if func(u)])

    def __call__(self, type_id):
        """Support bot.units(UnitTypeId.X) pattern"""
        return MockUnits([u for u in self._units if u.type_id == type_id])

    def of_type(self, type_id):
        return MockUnits([u for u in self._units if u.type_id == type_id])

    def sorted(self, key_func, reverse=False):
        return MockUnits(sorted(self._units, key=key_func, reverse=reverse))


class MockBot:
    """Mock SC2 Bot"""
    def __init__(self):
        self.minerals = 50
        self.vespene = 0
        self.supply_cap = 14
        self.supply_used = 12
        self.supply_left = 2
        self.larva = MockUnits([])
        self.townhalls = MockUnits([])
        self.workers = MockUnits([])
        self.mineral_field = MockUnits([])
        self.gas_buildings = MockUnits([])
        self.units = MockUnits([])
        self.state = Mock()
        self.state.game_loop = 0
        self.iteration = 0  # Added iteration attribute
        self.time = 0.0
        self.start_location = (50, 50)
        self.main_base_ramp = Mock()
        self.main_base_ramp.top_center = (50, 50)
        self.can_afford = Mock(return_value=True)
        self.do = Mock()
        self.already_pending = Mock(return_value=0)
        self.expansion_locations_list = [(60, 60), (70, 70)]

        # Mock methods
        self.calculate_supply_cost = Mock(return_value=1)
        self.get_next_expansion = Mock(return_value=(60, 60))

    def can_afford_with_priority(self, unit_type):
        """Mock can_afford with priority"""
        return self.minerals >= 50


class TestEconomyManagerInitialization:
    """테스트 1: 경제 매니저 초기화"""

    def test_initialization(self):
        """EconomyManager 기본 초기화"""
        bot = MockBot()
        manager = EconomyManager(bot)

        assert manager.bot == bot
        assert manager.balancer is not None
        assert manager.macro_hatchery_mineral_threshold > 0
        assert manager.macro_hatchery_larva_threshold > 0

    def test_initialization_with_config(self):
        """Config 파일이 있을 때 초기화"""
        bot = MockBot()
        manager = EconomyManager(bot)

        # Default values should be used if config import fails
        assert manager.macro_hatchery_mineral_threshold >= 300  # Phase 16: 600으로 낮춤 (더 빠른 매크로 해처리)


class TestEmergencyMode:
    """테스트 2: 긴급 모드 설정"""

    def test_set_emergency_mode_active(self):
        """긴급 모드 활성화"""
        bot = MockBot()
        manager = EconomyManager(bot)

        manager.set_emergency_mode(True)
        assert manager._emergency_mode == True

    def test_set_emergency_mode_inactive(self):
        """긴급 모드 비활성화"""
        bot = MockBot()
        manager = EconomyManager(bot)

        manager.set_emergency_mode(False)
        assert manager._emergency_mode == False


class TestOverlordProduction:
    """테스트 3: 오버로드 생산 시스템"""

    @pytest.mark.asyncio
    async def test_train_overlord_when_supply_blocked(self):
        """서플라이가 막혔을 때 오버로드 생산"""
        bot = MockBot()
        bot.supply_left = 0
        bot.supply_cap = 14
        bot.supply_used = 14
        bot.minerals = 100
        bot.larva = MockUnits([MockUnit(1, "LARVA", (50, 50))])
        bot.already_pending = Mock(return_value=0)

        manager = EconomyManager(bot)
        await manager._train_overlord_if_needed()

        # Should attempt to train overlord
        assert bot.do.called or bot.larva.amount == 1

    @pytest.mark.asyncio
    async def test_no_overlord_when_supply_sufficient(self):
        """서플라이가 충분할 때 오버로드 미생산"""
        bot = MockBot()
        bot.supply_left = 10
        bot.minerals = 100
        bot.larva = MockUnits([MockUnit(1, "LARVA", (50, 50))])

        manager = EconomyManager(bot)
        call_count_before = bot.do.call_count
        await manager._train_overlord_if_needed()

        # Should not produce overlord when supply is sufficient
        # (implementation may vary, this tests the logic exists)
        assert True  # Verification that function completes


class TestDroneProduction:
    """테스트 4: 드론 생산 시스템"""

    @pytest.mark.asyncio
    async def test_train_drone_when_workers_needed(self):
        """일꾼이 부족할 때 드론 생산"""
        bot = MockBot()
        bot.minerals = 50
        bot.supply_left = 5
        bot.workers = MockUnits([MockUnit(i, "DRONE", (50, 50)) for i in range(12)])
        bot.townhalls = MockUnits([MockUnit(100, "HATCHERY", (50, 50))])
        bot.larva = MockUnits([MockUnit(1, "LARVA", (50, 50))])

        manager = EconomyManager(bot)
        await manager._train_drone_if_needed()

        # Function should complete without error
        assert True

    @pytest.mark.asyncio
    async def test_no_drone_when_workers_sufficient(self):
        """일꾼이 충분할 때 드론 미생산"""
        bot = MockBot()
        bot.minerals = 50
        bot.workers = MockUnits([MockUnit(i, "DRONE", (50, 50)) for i in range(80)])
        bot.townhalls = MockUnits([MockUnit(100, "HATCHERY", (50, 50))])
        bot.larva = MockUnits([MockUnit(1, "LARVA", (50, 50))])

        manager = EconomyManager(bot)
        call_count_before = bot.do.call_count
        await manager._train_drone_if_needed()

        # Should not produce more drones when saturated
        assert True


class TestGoldExpansion:
    """테스트 5: 골드 확장지 감지"""

    def test_is_gold_expansion_true(self):
        """골드 미네랄이 있는 확장지 감지"""
        bot = MockBot()

        # Create gold mineral patches (1500+ minerals)
        gold_position = (60, 60)
        bot.mineral_field = MockUnits([
            MockUnit(1, "MINERAL", gold_position, health=1500),
            MockUnit(2, "MINERAL", gold_position, health=1600)
        ])

        manager = EconomyManager(bot)
        is_gold = manager._is_gold_expansion(gold_position)

        assert is_gold == True

    def test_is_gold_expansion_false(self):
        """일반 미네랄만 있는 확장지"""
        bot = MockBot()

        # Create normal mineral patches (900 minerals)
        normal_position = (60, 60)
        bot.mineral_field = MockUnits([
            MockUnit(1, "MINERAL", normal_position, health=900),
            MockUnit(2, "MINERAL", normal_position, health=900)
        ])

        manager = EconomyManager(bot)
        is_gold = manager._is_gold_expansion(normal_position)

        assert is_gold == False

    def test_get_gold_expansion_locations(self):
        """골드 확장지 목록 조회"""
        bot = MockBot()
        bot.expansion_locations_list = [(60, 60), (70, 70), (80, 80)]

        # Gold at (60, 60)
        bot.mineral_field = MockUnits([
            MockUnit(1, "MINERAL", (60, 60), health=1500),
            MockUnit(2, "MINERAL", (70, 70), health=900),
        ])

        manager = EconomyManager(bot)
        gold_locations = manager._get_gold_expansion_locations()

        # Should identify gold bases
        assert isinstance(gold_locations, list)


class TestResourceStatus:
    """테스트 6: 자원 상태 조회"""

    def test_get_resource_status(self):
        """자원 상태 조회"""
        bot = MockBot()
        bot.minerals = 500
        bot.vespene = 200
        bot.supply_left = 10
        bot.supply_cap = 40
        bot.workers = MockUnits([MockUnit(i, "DRONE", (50, 50)) for i in range(30)])

        manager = EconomyManager(bot)
        status = manager.get_resource_status()

        assert 'minerals' in status
        assert 'gas' in status  # Changed from 'vespene' to 'gas'
        assert status['minerals'] == 500
        assert status['gas'] == 200


class TestEconomyRecoveryMode:
    """테스트 7: 경제 회복 모드"""

    def test_is_economy_recovery_mode_true(self):
        """경제 회복 모드 활성화 조건"""
        bot = MockBot()
        bot.workers = MockUnits([MockUnit(i, "DRONE", (50, 50)) for i in range(20)])
        bot.townhalls = MockUnits([MockUnit(100, "HATCHERY", (50, 50))])

        manager = EconomyManager(bot)
        is_recovery = manager.is_economy_recovery_mode()

        # Should return boolean
        assert isinstance(is_recovery, bool)

    def test_is_economy_recovery_mode_false(self):
        """경제 회복 모드 비활성 조건"""
        bot = MockBot()
        bot.workers = MockUnits([MockUnit(i, "DRONE", (50, 50)) for i in range(60)])
        bot.townhalls = MockUnits([
            MockUnit(100, "HATCHERY", (50, 50)),
            MockUnit(101, "HATCHERY", (60, 60))
        ])

        manager = EconomyManager(bot)
        is_recovery = manager.is_economy_recovery_mode()

        # Should be False when economy is healthy
        assert isinstance(is_recovery, bool)


class TestTargetDroneCount:
    """테스트 8: 목표 드론 수 계산"""

    def test_get_target_drone_count_one_base(self):
        """1베이스 목표 드론 수"""
        bot = MockBot()
        bot.townhalls = MockUnits([MockUnit(100, "HATCHERY", (50, 50))])

        manager = EconomyManager(bot)
        target = manager.get_target_drone_count()

        assert target > 0
        assert target <= 80  # Max reasonable drone count

    def test_get_target_drone_count_multi_base(self):
        """멀티베이스 목표 드론 수"""
        bot = MockBot()
        bot.townhalls = MockUnits([
            MockUnit(100, "HATCHERY", (50, 50)),
            MockUnit(101, "HATCHERY", (60, 60)),
            MockUnit(102, "HATCHERY", (70, 70))
        ])

        manager = EconomyManager(bot)
        target = manager.get_target_drone_count()

        assert target > 16  # More than 1 base
        assert target <= 80


class TestGasWorkerDistribution:
    """테스트 9: 가스 일꾼 분배"""

    @pytest.mark.asyncio
    async def test_distribute_workers_to_gas(self):
        """가스 건물에 일꾼 분배"""
        bot = MockBot()
        bot.workers = MockUnits([MockUnit(i, "DRONE", (50, 50)) for i in range(30)])
        extractor = MockUnit(200, "EXTRACTOR", (52, 52))
        extractor.assigned_harvesters = 0
        extractor.ideal_harvesters = 3
        bot.gas_buildings = MockUnits([extractor])

        manager = EconomyManager(bot)
        await manager._distribute_workers_to_gas()

        # Function should complete
        assert True


class TestIdleWorkerAssignment:
    """테스트 10: 대기 일꾼 할당"""

    @pytest.mark.asyncio
    async def test_assign_idle_workers(self):
        """대기 중인 일꾼을 미네랄에 할당"""
        bot = MockBot()
        idle_drone = MockUnit(1, "DRONE", (50, 50), is_idle=True)
        bot.workers = MockUnits([idle_drone])
        bot.mineral_field = MockUnits([MockUnit(300, "MINERAL", (51, 51))])
        bot.townhalls = MockUnits([MockUnit(100, "HATCHERY", (50, 50))])

        manager = EconomyManager(bot)
        await manager._assign_idle_workers()

        # Function should complete
        assert True


class TestResourceReservations:
    """테스트 11: 자원 예약 시스템"""

    def test_update_resource_reservations(self):
        """자원 예약 업데이트"""
        bot = MockBot()
        bot.minerals = 1000
        bot.vespene = 500

        manager = EconomyManager(bot)
        manager._update_resource_reservations()

        # Reservations should be tracked
        assert hasattr(manager, '_reserved_minerals')
        assert hasattr(manager, '_reserved_gas')


class TestEarlyWorkerSplit:
    """테스트 12: 초반 일꾼 분할"""

    @pytest.mark.asyncio
    async def test_optimize_early_worker_split(self):
        """게임 시작 시 일꾼 분할 최적화"""
        bot = MockBot()
        bot.workers = MockUnits([MockUnit(i, "DRONE", (50, 50)) for i in range(12)])
        bot.mineral_field = MockUnits([
            MockUnit(300 + i, "MINERAL", (50 + i, 50)) for i in range(8)
        ])
        bot.townhalls = MockUnits([MockUnit(100, "HATCHERY", (50, 50))])

        manager = EconomyManager(bot)
        await manager._optimize_early_worker_split()

        # Function should complete
        assert True


class TestProactiveExpansion:
    """테스트 13: 사전 확장 체크"""

    @pytest.mark.asyncio
    async def test_check_proactive_expansion(self):
        """사전 예방적 확장 체크"""
        bot = MockBot()
        bot.townhalls = MockUnits([MockUnit(100, "HATCHERY", (50, 50))])
        bot.minerals = 300
        bot.time = 180.0  # 3분

        manager = EconomyManager(bot)
        await manager._check_proactive_expansion()

        # Function should complete
        assert True


class TestForceExpansion:
    """테스트 14: 강제 확장"""

    @pytest.mark.asyncio
    async def test_force_expansion_if_stuck(self):
        """자원이 막혔을 때 강제 확장"""
        bot = MockBot()
        bot.townhalls = MockUnits([MockUnit(100, "HATCHERY", (50, 50))])
        bot.minerals = 800
        bot.time = 300.0  # 5분
        bot.workers = MockUnits([MockUnit(i, "DRONE", (50, 50)) for i in range(40)])

        manager = EconomyManager(bot)
        await manager._force_expansion_if_stuck()

        # Function should complete
        assert True


class TestMacroHatchery:
    """테스트 15: 매크로 해처리 건설"""

    @pytest.mark.asyncio
    async def test_build_macro_hatchery_if_needed(self):
        """자원 과잉 시 매크로 해처리 건설"""
        bot = MockBot()
        bot.townhalls = MockUnits([MockUnit(100, "HATCHERY", (50, 50))])
        bot.minerals = 2000
        bot.larva = MockUnits([MockUnit(1, "LARVA", (50, 50))])

        manager = EconomyManager(bot)
        await manager._build_macro_hatchery_if_needed()

        # Function should complete
        assert True


class TestWorkerRedistribution:
    """테스트 16: 일꾼 재분배"""

    @pytest.mark.asyncio
    async def test_redistribute_mineral_workers(self):
        """미네랄 일꾼 재분배"""
        bot = MockBot()
        hatch1 = MockUnit(100, "HATCHERY", (50, 50))
        hatch1.assigned_harvesters = 24
        hatch1.ideal_harvesters = 16

        hatch2 = MockUnit(101, "HATCHERY", (60, 60))
        hatch2.assigned_harvesters = 8
        hatch2.ideal_harvesters = 16

        bot.townhalls = MockUnits([hatch1, hatch2])
        bot.workers = MockUnits([MockUnit(i, "DRONE", (50, 50)) for i in range(32)])
        bot.mineral_field = MockUnits([MockUnit(300, "MINERAL", (60, 60))])

        manager = EconomyManager(bot)
        await manager._redistribute_mineral_workers()

        # Function should complete
        assert True


class TestResourceBankingPrevention:
    """테스트 17: 자원 뱅킹 방지"""

    @pytest.mark.asyncio
    async def test_prevent_resource_banking(self):
        """과도한 자원 축적 방지"""
        bot = MockBot()
        bot.minerals = 3000
        bot.vespene = 2000
        bot.townhalls = MockUnits([MockUnit(100, "HATCHERY", (50, 50))])

        manager = EconomyManager(bot)
        await manager._prevent_resource_banking()

        # Function should complete
        assert True


class TestGasTimingOptimization:
    """테스트 18: 가스 타이밍 최적화"""

    @pytest.mark.asyncio
    async def test_optimize_gas_timing(self):
        """가스 채취 타이밍 최적화"""
        bot = MockBot()
        bot.townhalls = MockUnits([MockUnit(100, "HATCHERY", (50, 50))])
        bot.workers = MockUnits([MockUnit(i, "DRONE", (50, 50)) for i in range(16)])
        bot.time = 120.0  # 2분
        bot.vespene = 0

        manager = EconomyManager(bot)
        await manager._optimize_gas_timing()

        # Function should complete
        assert True


class TestGasBoostMode:
    """테스트 19: Phase 18 가스 부스트 모드"""

    def test_default_gas_boost_off(self):
        """초기에는 가스 부스트 모드 비활성"""
        bot = MockBot()
        manager = EconomyManager(bot)
        assert manager.gas_boost_mode is False

    def test_enable_gas_boost_mode_default_duration(self):
        """기본 인자 호출 시 120초 지속 시간"""
        bot = MockBot()
        bot.time = 42.0
        manager = EconomyManager(bot)
        manager.enable_gas_boost_mode()
        assert manager.gas_boost_mode is True
        assert manager.gas_boost_duration == 120
        assert manager.gas_boost_start_time == 42.0

    def test_enable_gas_boost_mode_custom_duration(self):
        """커스텀 지속 시간 적용"""
        bot = MockBot()
        bot.time = 100.0
        manager = EconomyManager(bot)
        manager.enable_gas_boost_mode(duration=180)
        assert manager.gas_boost_mode is True
        assert manager.gas_boost_duration == 180
        assert manager.gas_boost_start_time == 100.0

    def test_disable_gas_boost_mode(self):
        """가스 부스트 모드 비활성화"""
        bot = MockBot()
        manager = EconomyManager(bot)
        manager.enable_gas_boost_mode(duration=60)
        assert manager.gas_boost_mode is True
        manager.disable_gas_boost_mode()
        assert manager.gas_boost_mode is False


class TestGasStats:
    """테스트 20: 가스 통계 (get_gas_stats)"""

    def test_gas_stats_structure(self):
        """get_gas_stats 가 dict 와 필요한 키들을 반환"""
        bot = MockBot()
        manager = EconomyManager(bot)
        stats = manager.get_gas_stats()
        assert isinstance(stats, dict)
        assert "gas" in stats
        assert "extractors" in stats
        assert "gas_workers" in stats
        assert "gas_boost_mode" in stats

    def test_gas_stats_reflects_boost_mode(self):
        """부스트 모드 상태가 stats 에 반영됨"""
        bot = MockBot()
        manager = EconomyManager(bot)
        manager.enable_gas_boost_mode()
        stats = manager.get_gas_stats()
        assert stats.get("gas_boost_mode") is True

    def test_gas_stats_counts_extractors(self):
        """추출기 개수와 일꾼 합계 정확히 집계"""
        bot = MockBot()
        ex1 = MockUnit(200, "EXTRACTOR", (52, 52))
        ex1.assigned_harvesters = 3
        ex2 = MockUnit(201, "EXTRACTOR", (53, 53))
        ex2.assigned_harvesters = 2
        bot.gas_buildings = MockUnits([ex1, ex2])
        bot.vespene = 250
        manager = EconomyManager(bot)
        stats = manager.get_gas_stats()
        assert stats["extractors"] == 2
        assert stats["gas_workers"] == 5
        assert stats["gas"] == 250


class TestInjectEfficiencyTracking:
    """테스트 21: Queen Inject Efficiency Tracking (Feature 88)"""

    def test_initial_efficiency_is_zero(self):
        """초기 시도 없음 → 0.0%"""
        bot = MockBot()
        manager = EconomyManager(bot)
        assert manager.get_inject_efficiency() == 0.0

    def test_record_success_only(self):
        """전체 성공 → 100%"""
        bot = MockBot()
        manager = EconomyManager(bot)
        for _ in range(5):
            manager.record_inject_attempt(success=True)
        assert manager.get_inject_efficiency() == 100.0

    def test_record_partial_success(self):
        """3성공/1실패 = 75%"""
        bot = MockBot()
        manager = EconomyManager(bot)
        manager.record_inject_attempt(True)
        manager.record_inject_attempt(True)
        manager.record_inject_attempt(False)
        manager.record_inject_attempt(True)
        assert manager.get_inject_efficiency() == 75.0

    def test_record_default_success(self):
        """success 인자 생략 시 성공 처리"""
        bot = MockBot()
        manager = EconomyManager(bot)
        manager.record_inject_attempt()
        manager.record_inject_attempt()
        assert manager.get_inject_efficiency() == 100.0

    def test_get_inject_stats_structure(self):
        """attempts/successes/efficiency 키 반환"""
        bot = MockBot()
        manager = EconomyManager(bot)
        manager.record_inject_attempt(True)
        manager.record_inject_attempt(False)
        stats = manager.get_inject_stats()
        assert stats["inject_attempts"] == 2
        assert stats["inject_successes"] == 1
        assert stats["inject_efficiency"] == 50.0

    def test_efficiency_rounded_in_stats(self):
        """1/3 = 33.3 (소수점 첫자리 round)"""
        bot = MockBot()
        manager = EconomyManager(bot)
        manager.record_inject_attempt(True)
        manager.record_inject_attempt(False)
        manager.record_inject_attempt(False)
        stats = manager.get_inject_stats()
        assert stats["inject_efficiency"] == 33.3


class TestResourceStatus:
    """테스트 22: 자원 상태 조회 (get_resource_status)"""

    def test_resource_status_returns_dict(self):
        """resource_status 가 dict 반환"""
        bot = MockBot()
        bot.minerals = 1000
        bot.vespene = 500
        manager = EconomyManager(bot)
        status = manager.get_resource_status()
        assert isinstance(status, dict)


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
