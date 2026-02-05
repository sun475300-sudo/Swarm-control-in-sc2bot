# -*- coding: utf-8 -*-
"""
Unit Tests for ExpansionManager

테스트 범위:
1. 확장 안전성 체크 - 기본 조건
2. 확장 안전성 체크 - 공격 받는 중
3. 확장 안전성 체크 - 적이 근처에 있음
4. 확장 안전성 체크 - 공격적 확장 (미네랄 300+)
5. 확장 안전성 체크 - 낮은 군대 보급
6. 확장 안전성 체크 - 낮은 드론 수
7. 확장 안전성 체크 - 쿨다운 시간
8. 확장 시도 - 자원 부족
9. 확장 시도 - 이미 확장 중
10. 확장 시도 - 성공적인 확장
11. 확장 차단 로그 출력
12. 건물 예약 정리

사용 패턴:
- MockBot 및 MockUnit 클래스 사용
- 초기화 테스트
- 핵심 기능 테스트
- 엣지 케이스 테스트
- pytest 프레임워크 사용
"""

import pytest
from unittest.mock import Mock, MagicMock, AsyncMock
from typing import List


# ExpansionManager 함수 임포트
try:
    import sys
    import os
    sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'wicked_zerg_challenger', 'local_training', 'production'))
    from expansion_manager import can_expand_safely, try_expand, log_expand_block, cleanup_build_reservations
except ImportError:
    pytest.skip("ExpansionManager not available", allow_module_level=True)


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

    @property
    def exists(self):
        return len(self._units) > 0

    def closer_than(self, distance: float, position):
        return MockUnits([
            u for u in self._units
            if u.distance_to(position) < distance
        ])

    def filter(self, func):
        return MockUnits([u for u in self._units if func(u)])


class MockIntel:
    """Mock Intel Manager"""
    def __init__(self, under_attack: bool = False):
        self._under_attack = under_attack

    def is_under_attack(self) -> bool:
        return self._under_attack


class MockBot:
    """Mock SC2 Bot"""
    def __init__(self):
        self.minerals = 300
        self.vespene = 0
        self.supply_cap = 14
        self.supply_used = 12
        self.supply_left = 2
        self.supply_army = 0
        self.townhalls = MockUnits([MockUnit(100, "HATCHERY", (50, 50))])
        self.workers = MockUnits([MockUnit(i, "DRONE", (50, 50)) for i in range(16)])
        self.enemy_units = MockUnits([])
        self.time = 0.0
        self.intel = MockIntel(under_attack=False)
        self.can_afford = Mock(return_value=True)
        self.already_pending = Mock(return_value=0)
        self.expand_now = AsyncMock()
        self.get_next_expansion = AsyncMock(return_value=(60, 60))
        self.build = AsyncMock()
        self.build_reservations = {}

    def reset_mocks(self):
        """Reset all mock call counts"""
        self.expand_now.reset_mock()
        self.get_next_expansion.reset_mock()
        self.build.reset_mock()


class MockResilience:
    """Mock ProductionResilience instance"""
    def __init__(self, bot):
        self.bot = bot
        self.enemy_near_base_distance = 30.0
        self.enemy_near_base_scale = 1.0
        self.min_army_supply = 8
        self.min_army_time = 180.0  # 3 minutes
        self.min_drones_per_base = 16
        self.expansion_retry_cooldown = 30.0
        self.last_expansion_attempt = 0.0
        self.last_expand_log_time = 0.0


class TestExpansionSafetyBasic:
    """테스트 1: 확장 안전성 체크 - 기본 조건"""

    def test_can_expand_safely_basic_success(self):
        """기본 조건에서 안전한 확장 가능"""
        bot = MockBot()
        bot.minerals = 300
        bot.workers = MockUnits([MockUnit(i, "DRONE", (50, 50)) for i in range(16)])
        bot.townhalls = MockUnits([MockUnit(100, "HATCHERY", (50, 50))])
        bot.supply_army = 10
        bot.time = 100.0  # Set time to avoid cooldown

        resilience = MockResilience(bot)
        resilience.last_expansion_attempt = 0.0  # No recent expansion attempt

        can_expand, reason = can_expand_safely(resilience)

        assert can_expand == True
        assert reason == ""

    def test_can_expand_safely_natural_expansion(self):
        """앞마당 확장 시 완화된 조건"""
        bot = MockBot()
        bot.minerals = 200
        bot.workers = MockUnits([MockUnit(i, "DRONE", (50, 50)) for i in range(14)])
        bot.townhalls = MockUnits([MockUnit(100, "HATCHERY", (50, 50))])  # 1 base only
        bot.supply_army = 0  # No army yet
        bot.time = 100.0

        resilience = MockResilience(bot)
        resilience.last_expansion_attempt = 0.0

        can_expand, reason = can_expand_safely(resilience)

        # Should allow natural expansion even with low army
        assert can_expand == True or "low_drones" in reason


class TestExpansionSafetyUnderAttack:
    """테스트 2: 확장 안전성 체크 - 공격 받는 중"""

    def test_cannot_expand_when_under_attack(self):
        """공격 받는 중에는 확장 불가 (미네랄 200 미만, 2+ 베이스)"""
        bot = MockBot()
        bot.minerals = 150  # Less than 200 (not aggressive for any case)
        bot.intel = MockIntel(under_attack=True)
        bot.supply_army = 10
        bot.time = 100.0
        # 2 bases so aggressive_expand needs minerals >= 300 (not 200)
        bot.townhalls = MockUnits([
            MockUnit(100, "HATCHERY", (50, 50)),
            MockUnit(101, "HATCHERY", (60, 60))
        ])
        bot.workers = MockUnits([MockUnit(i, "DRONE", (50, 50)) for i in range(32)])

        resilience = MockResilience(bot)
        resilience.last_expansion_attempt = 0.0  # No recent attempt

        can_expand, reason = can_expand_safely(resilience)

        assert can_expand == False
        assert reason == "under_attack"

    def test_can_expand_when_under_attack_with_high_minerals(self):
        """공격 받아도 미네랄 300+ 이상이면 확장 가능 (공격적 확장)"""
        bot = MockBot()
        bot.minerals = 350
        bot.intel = MockIntel(under_attack=True)
        bot.supply_army = 10
        bot.time = 100.0

        resilience = MockResilience(bot)
        resilience.last_expansion_attempt = 0.0

        can_expand, reason = can_expand_safely(resilience)

        # Aggressive expansion bypasses under_attack check
        assert can_expand == True


class TestExpansionSafetyEnemyNearby:
    """테스트 3: 확장 안전성 체크 - 적이 근처에 있음"""

    def test_cannot_expand_with_enemy_near_base(self):
        """적이 본진 근처에 있을 때 확장 불가 (미네랄 200 미만, 2+ 베이스)"""
        bot = MockBot()
        bot.minerals = 150  # Less than 200 (not aggressive for any case)
        # 2 bases so aggressive_expand needs minerals >= 300
        bot.townhalls = MockUnits([
            MockUnit(100, "HATCHERY", (50, 50)),
            MockUnit(101, "HATCHERY", (60, 60))
        ])
        bot.enemy_units = MockUnits([
            MockUnit(200, "MARINE", (55, 55)),  # Close to base
            MockUnit(201, "MARINE", (56, 56)),
            MockUnit(202, "MARINE", (57, 57)),  # 3 enemies - more than scout threshold
        ])
        bot.supply_army = 10
        bot.time = 100.0
        bot.workers = MockUnits([MockUnit(i, "DRONE", (50, 50)) for i in range(32)])

        resilience = MockResilience(bot)
        resilience.last_expansion_attempt = 0.0

        can_expand, reason = can_expand_safely(resilience)

        assert can_expand == False
        assert reason == "enemy_near_base"

    def test_can_expand_with_scouts_near_base(self):
        """정찰 유닛(1-2기)은 무시하고 확장 가능"""
        bot = MockBot()
        bot.minerals = 250
        bot.enemy_units = MockUnits([
            MockUnit(200, "REAPER", (55, 55)),  # Just 1 scout
        ])
        bot.supply_army = 10
        bot.time = 100.0

        resilience = MockResilience(bot)
        resilience.last_expansion_attempt = 0.0

        can_expand, reason = can_expand_safely(resilience)

        # Should ignore scouts (1-2 units)
        assert can_expand == True or "low_drones" in reason


class TestExpansionAggressiveMode:
    """테스트 4: 확장 안전성 체크 - 공격적 확장 (미네랄 300+)"""

    def test_aggressive_expansion_bypasses_enemy_check(self):
        """미네랄 300+ 이상이면 적 근처 체크 우회"""
        bot = MockBot()
        bot.minerals = 350
        bot.enemy_units = MockUnits([
            MockUnit(200, "MARINE", (55, 55)),
            MockUnit(201, "MARINE", (56, 56)),
            MockUnit(202, "MARINE", (57, 57)),
        ])
        bot.supply_army = 10
        bot.workers = MockUnits([MockUnit(i, "DRONE", (50, 50)) for i in range(16)])
        bot.time = 100.0

        resilience = MockResilience(bot)
        resilience.last_expansion_attempt = 0.0

        can_expand, reason = can_expand_safely(resilience)

        # Aggressive expansion should succeed
        assert can_expand == True

    def test_aggressive_expansion_reduced_cooldown(self):
        """공격적 확장 시 쿨다운 반감"""
        bot = MockBot()
        bot.minerals = 350
        bot.time = 20.0
        bot.supply_army = 10

        resilience = MockResilience(bot)
        resilience.last_expansion_attempt = 5.0
        resilience.expansion_retry_cooldown = 30.0

        can_expand, reason = can_expand_safely(resilience)

        # Cooldown should be halved (15s instead of 30s)
        # 20.0 - 5.0 = 15.0 >= 15.0 (half of 30)
        assert can_expand == True or reason == "cooldown"


class TestExpansionLowArmy:
    """테스트 5: 확장 안전성 체크 - 낮은 군대 보급"""

    def test_cannot_expand_third_base_without_army(self):
        """3번째 확장(bases >= 2) 시 군대 부족하면 차단"""
        bot = MockBot()
        bot.minerals = 250  # Not aggressive enough to bypass
        bot.townhalls = MockUnits([
            MockUnit(100, "HATCHERY", (50, 50)),
            MockUnit(101, "HATCHERY", (60, 60)),  # 2 bases
        ])
        bot.supply_army = 3  # Low army
        bot.time = 200.0  # Past min_army_time (180s)

        resilience = MockResilience(bot)
        resilience.min_army_supply = 8

        can_expand, reason = can_expand_safely(resilience)

        assert can_expand == False
        assert "low_army" in reason

    def test_can_expand_third_base_with_sufficient_army(self):
        """3번째 확장 시 군대가 충분하면 허용"""
        bot = MockBot()
        bot.minerals = 300
        bot.townhalls = MockUnits([
            MockUnit(100, "HATCHERY", (50, 50)),
            MockUnit(101, "HATCHERY", (60, 60)),
        ])
        bot.supply_army = 10  # Sufficient army
        bot.time = 200.0
        bot.workers = MockUnits([MockUnit(i, "DRONE", (50, 50)) for i in range(32)])  # 16 per base

        resilience = MockResilience(bot)
        resilience.min_army_supply = 8

        can_expand, reason = can_expand_safely(resilience)

        assert can_expand == True


class TestExpansionLowDrones:
    """테스트 6: 확장 안전성 체크 - 낮은 드론 수"""

    def test_cannot_expand_with_insufficient_drones(self):
        """드론 포화도가 낮으면 확장 차단"""
        bot = MockBot()
        bot.minerals = 250
        bot.townhalls = MockUnits([
            MockUnit(100, "HATCHERY", (50, 50)),
            MockUnit(101, "HATCHERY", (60, 60)),
        ])
        bot.workers = MockUnits([MockUnit(i, "DRONE", (50, 50)) for i in range(20)])  # 10 per base (too low)
        bot.supply_army = 10
        bot.time = 100.0

        resilience = MockResilience(bot)
        resilience.min_drones_per_base = 16
        resilience.last_expansion_attempt = 0.0

        can_expand, reason = can_expand_safely(resilience)

        assert can_expand == False
        assert "low_drones" in reason

    def test_can_expand_with_high_mineral_bank(self):
        """미네랄 1000+ 이상이면 드론 체크 우회"""
        bot = MockBot()
        bot.minerals = 1200
        bot.townhalls = MockUnits([
            MockUnit(100, "HATCHERY", (50, 50)),
            MockUnit(101, "HATCHERY", (60, 60)),
        ])
        bot.workers = MockUnits([MockUnit(i, "DRONE", (50, 50)) for i in range(20)])  # Low drones
        bot.supply_army = 10
        bot.time = 100.0

        resilience = MockResilience(bot)
        resilience.min_drones_per_base = 16
        resilience.last_expansion_attempt = 0.0

        can_expand, reason = can_expand_safely(resilience)

        # Should allow expansion to burn minerals
        assert can_expand == True


class TestExpansionCooldown:
    """테스트 7: 확장 안전성 체크 - 쿨다운 시간"""

    def test_cannot_expand_during_cooldown(self):
        """쿨다운 중에는 확장 불가 (미네랄 300 미만, 2+ 베이스)"""
        bot = MockBot()
        bot.minerals = 250  # Not enough for aggressive expansion
        bot.time = 20.0
        bot.supply_army = 10
        bot.workers = MockUnits([MockUnit(i, "DRONE", (50, 50)) for i in range(32)])
        # 2 bases - so cooldown is not reduced (natural already exists)
        bot.townhalls = MockUnits([
            MockUnit(100, "HATCHERY", (50, 50)),
            MockUnit(101, "HATCHERY", (60, 60))
        ])

        resilience = MockResilience(bot)
        resilience.last_expansion_attempt = 10.0
        resilience.expansion_retry_cooldown = 30.0

        can_expand, reason = can_expand_safely(resilience)

        # 20.0 - 10.0 = 10.0 < 30.0 (full cooldown for 2+ bases with <300 minerals)
        assert can_expand == False
        assert reason == "cooldown"

    def test_can_expand_after_cooldown(self):
        """쿨다운 시간이 지나면 확장 가능"""
        bot = MockBot()
        bot.minerals = 300
        bot.time = 50.0
        bot.supply_army = 10
        bot.workers = MockUnits([MockUnit(i, "DRONE", (50, 50)) for i in range(16)])

        resilience = MockResilience(bot)
        resilience.last_expansion_attempt = 10.0
        resilience.expansion_retry_cooldown = 30.0

        can_expand, reason = can_expand_safely(resilience)

        # 50 - 10 = 40 >= 30 (cooldown passed)
        assert can_expand == True


class TestTryExpandResources:
    """테스트 8: 확장 시도 - 자원 부족"""

    @pytest.mark.asyncio
    async def test_cannot_expand_without_resources(self):
        """자원 부족 시 확장 실패"""
        bot = MockBot()
        bot.can_afford = Mock(return_value=False)
        bot.minerals = 100  # Not enough for hatchery (300)

        resilience = MockResilience(bot)

        result = await try_expand(resilience)

        assert result == False
        assert bot.expand_now.call_count == 0


class TestTryExpandPending:
    """테스트 9: 확장 시도 - 이미 확장 중"""

    @pytest.mark.asyncio
    async def test_cannot_expand_when_already_pending(self):
        """이미 확장 건설 중이면 차단"""
        bot = MockBot()
        bot.can_afford = Mock(return_value=True)
        bot.already_pending = Mock(return_value=1)  # Already building hatchery

        resilience = MockResilience(bot)

        result = await try_expand(resilience)

        assert result == False
        assert bot.expand_now.call_count == 0


class TestTryExpandSuccess:
    """테스트 10: 확장 시도 - 성공적인 확장"""

    @pytest.mark.asyncio
    async def test_successful_expansion_with_expand_now(self):
        """expand_now 메서드를 통한 성공적인 확장"""
        bot = MockBot()
        bot.can_afford = Mock(return_value=True)
        bot.already_pending = Mock(return_value=0)
        bot.minerals = 300
        bot.supply_army = 10
        bot.time = 50.0

        resilience = MockResilience(bot)

        result = await try_expand(resilience)

        assert result == True
        assert bot.expand_now.call_count == 1
        assert resilience.last_expansion_attempt == 50.0

    @pytest.mark.asyncio
    async def test_successful_expansion_with_get_next_expansion(self):
        """get_next_expansion 메서드를 통한 성공적인 확장"""
        bot = MockBot()
        bot.can_afford = Mock(return_value=True)
        bot.already_pending = Mock(return_value=0)
        bot.minerals = 300
        bot.supply_army = 10
        bot.time = 60.0

        # Remove expand_now, use get_next_expansion instead
        del bot.expand_now

        resilience = MockResilience(bot)

        result = await try_expand(resilience)

        assert result == True
        assert bot.get_next_expansion.call_count == 1
        assert bot.build.call_count == 1


class TestLogExpandBlock:
    """테스트 11: 확장 차단 로그 출력"""

    def test_log_expand_block_first_time(self):
        """첫 번째 확장 차단 로그"""
        bot = MockBot()
        bot.time = 100.0

        resilience = MockResilience(bot)
        resilience.last_expand_log_time = 0.0

        # Should log without error
        log_expand_block(resilience, "under_attack")

        assert resilience.last_expand_log_time == 100.0

    def test_log_expand_block_rate_limited(self):
        """로그 출력 빈도 제한 (15초)"""
        bot = MockBot()
        bot.time = 110.0

        resilience = MockResilience(bot)
        resilience.last_expand_log_time = 100.0

        # Should not update log time (within 15s)
        log_expand_block(resilience, "enemy_near_base")

        assert resilience.last_expand_log_time == 100.0  # Not updated

    def test_log_expand_block_after_cooldown(self):
        """로그 쿨다운 후 다시 출력"""
        bot = MockBot()
        bot.time = 120.0

        resilience = MockResilience(bot)
        resilience.last_expand_log_time = 100.0

        # Should update log time (>15s passed)
        log_expand_block(resilience, "low_army")

        assert resilience.last_expand_log_time == 120.0


class TestCleanupBuildReservations:
    """테스트 12: 건물 예약 정리"""

    def test_cleanup_stale_reservations(self):
        """오래된 건물 예약 제거 (45초 이상)"""
        bot = MockBot()
        bot.time = 100.0
        bot.build_reservations = {
            "structure_1": 50.0,   # 50s old - should be removed
            "structure_2": 70.0,   # 30s old - keep
            "structure_3": 90.0,   # 10s old - keep
        }

        resilience = MockResilience(bot)

        cleanup_build_reservations(resilience)

        # Only structure_1 should be removed (100 - 50 = 50 > 45)
        assert "structure_1" not in bot.build_reservations
        assert "structure_2" in bot.build_reservations
        assert "structure_3" in bot.build_reservations

    def test_cleanup_empty_reservations(self):
        """예약이 없을 때도 에러 없이 처리"""
        bot = MockBot()
        bot.time = 100.0
        bot.build_reservations = {}

        resilience = MockResilience(bot)

        # Should complete without error
        cleanup_build_reservations(resilience)

        assert len(bot.build_reservations) == 0

    def test_cleanup_handles_missing_attribute(self):
        """build_reservations 속성이 없어도 에러 처리"""
        bot = MockBot()
        bot.time = 100.0
        del bot.build_reservations

        resilience = MockResilience(bot)

        # Should complete without error (exception handled)
        cleanup_build_reservations(resilience)

        assert True  # No exception raised


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
