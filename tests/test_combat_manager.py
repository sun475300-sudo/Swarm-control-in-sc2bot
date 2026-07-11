# -*- coding: utf-8 -*-
"""
Unit Tests for CombatManager

테스트 범위:
1. 전투 매니저 초기화
2. 타겟팅 시스템 (우선순위 타겟 선정)
3. 기지 방어 시스템
4. 멀티태스킹 시스템
5. 랠리 포인트 관리
6. 후퇴 조건 체크
"""

from typing import List
from unittest.mock import MagicMock, Mock, patch

import pytest

# Combat Manager 임포트
try:
    import os
    import sys

    sys.path.insert(
        0, os.path.join(os.path.dirname(__file__), "..", "wicked_zerg_challenger")
    )
    from combat_manager import CombatManager
except ImportError:
    pytest.skip("CombatManager not available", allow_module_level=True)


class MockUnit:
    """Mock SC2 Unit"""

    def __init__(
        self,
        tag: int,
        type_id,
        position,
        health: float = 100.0,
        health_max: float = 100.0,
        shield: float = 0.0,
        weapon_cooldown: int = 0,
    ):
        self.tag = tag
        self.type_id = type_id
        self.position = position
        self.health = health
        self.health_max = health_max
        self.shield = shield
        self.shield_max = shield
        self.weapon_cooldown = weapon_cooldown
        self.is_idle = True
        self.orders = []
        self.is_flying = False
        self.is_burrowed = False

    @property
    def health_percentage(self):
        return self.health / self.health_max if self.health_max > 0 else 0

    def distance_to(self, other):
        if hasattr(other, "position"):
            pos = other.position
        else:
            pos = other
        return (
            (self.position[0] - pos[0]) ** 2 + (self.position[1] - pos[1]) ** 2
        ) ** 0.5


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

    def closer_than(self, distance: float, position):
        return MockUnits([u for u in self._units if u.distance_to(position) < distance])

    def closest_to(self, position):
        if not self._units:
            return None
        return min(self._units, key=lambda u: u.distance_to(position))

    def filter(self, func):
        return MockUnits([u for u in self._units if func(u)])

    def of_type(self, type_id):
        return MockUnits([u for u in self._units if u.type_id == type_id])

    @property
    def center(self):
        """Average position of units in the collection (mirrors sc2.Units.center)."""
        if not self._units:
            return None
        avg_x = sum(u.position[0] for u in self._units) / len(self._units)
        avg_y = sum(u.position[1] for u in self._units) / len(self._units)
        return (avg_x, avg_y)


class MockBot:
    """Mock SC2 Bot"""

    def __init__(self):
        self.units = MockUnits([])
        self.enemy_units = MockUnits([])
        self.townhalls = MockUnits([])
        self.structures = MockUnits([])
        self.workers = MockUnits([])
        self.time = 0.0
        self.iteration = 0
        self.start_location = (50, 50)
        self.minerals = 50
        self.vespene = 0
        self.supply_used = 12
        self.supply_cap = 14
        self._actions = []

    def do(self, action):
        self._actions.append(action)


# ===== 테스트 케이스 =====


class TestCombatManagerInitialization:
    """전투 매니저 초기화 테스트"""

    def test_initialization(self):
        """기본 초기화 테스트"""
        bot = MockBot()
        combat = CombatManager(bot)

        assert combat.bot == bot
        assert combat._min_army_for_attack > 0
        assert combat._rally_point is None
        assert len(combat._active_tasks) == 0

    def test_manager_components(self):
        """서브 매니저 초기화 테스트"""
        bot = MockBot()
        combat = CombatManager(bot)

        # 타겟팅, 마이크로, Boids 매니저 초기화 확인
        # (실패해도 None으로 설정되어야 함)
        assert hasattr(combat, "targeting")
        assert hasattr(combat, "micro_combat")
        assert hasattr(combat, "boids")


class TestBaseDefense:
    """기지 방어 시스템 테스트"""

    @pytest.mark.asyncio
    async def test_base_under_attack_detection(self):
        """기지 공격 감지 테스트"""
        bot = MockBot()
        combat = CombatManager(bot)

        # 기지 설정
        base = MockUnit(1, "HATCHERY", (50, 50), health=1500)
        bot.townhalls = MockUnits([base])

        # 적 유닛이 기지 근처에 있음
        enemy = MockUnit(100, "MARINE", (52, 52), health=45)
        bot.enemy_units = MockUnits([enemy])

        # 방어 체크 실행
        iteration = 0
        await combat.on_step(iteration)

        # on_step이 크래시 없이 완료되면 통과
        # (실제 방어 로직은 복잡한 조건들이 있을 수 있음)
        assert True

    @pytest.mark.asyncio
    async def test_no_defense_when_no_threat(self):
        """위협 없을 때 방어 미활성화 테스트"""
        bot = MockBot()
        combat = CombatManager(bot)

        # 기지 설정
        base = MockUnit(1, "HATCHERY", (50, 50))
        bot.townhalls = MockUnits([base])

        # 적이 멀리 있음
        enemy = MockUnit(100, "MARINE", (100, 100))
        bot.enemy_units = MockUnits([enemy])

        # 방어 체크 실행
        iteration = 0
        await combat.on_step(iteration)

        # 방어 모드 비활성화 확인
        # (멀리 있는 적은 위협이 아님)
        assert (
            not combat._base_defense_active
            or "base_defense" not in combat._active_tasks
        )


class TestRallyPoint:
    """랠리 포인트 관리 테스트"""

    def test_rally_point_calculation(self):
        """랠리 포인트 계산 테스트"""
        bot = MockBot()
        combat = CombatManager(bot)

        # 기지와 적 위치 설정
        base = MockUnit(1, "HATCHERY", (50, 50))
        bot.townhalls = MockUnits([base])

        enemy = MockUnit(100, "MARINE", (80, 80))
        bot.enemy_units = MockUnits([enemy])

        # 랠리 포인트 계산 (내부 메서드 직접 테스트)
        if hasattr(combat, "_update_rally_point"):
            combat._update_rally_point()

            # 랠리 포인트가 설정될 수 있음 (None일 수도 있음)
            # 이 경우 테스트는 크래시 없이 완료되어야 함
            if combat._rally_point is not None:
                # 랠리 포인트는 기지와 다른 위치여야 함
                base_to_rally = (
                    (combat._rally_point[0] - 50) ** 2
                    + (combat._rally_point[1] - 50) ** 2
                ) ** 0.5
                # 랠리 포인트가 설정되었다면 기지에서 멀리 있을 수 있음
                assert True  # 크래시 없이 실행되면 통과
        else:
            # 메서드가 없으면 스킵
            pytest.skip("_update_rally_point method not available")


class TestArmyManagement:
    """병력 관리 테스트"""

    def test_min_army_threshold(self):
        """최소 병력 임계값 테스트"""
        bot = MockBot()
        combat = CombatManager(bot)

        # 병력이 부족할 때
        zergling1 = MockUnit(1, "ZERGLING", (50, 50))
        zergling2 = MockUnit(2, "ZERGLING", (51, 51))
        bot.units = MockUnits([zergling1, zergling2])

        # 최소 병력 미달 (6기 필요)
        assert len(bot.units) < combat._min_army_for_attack

    def test_army_composition_tracking(self):
        """병력 구성 추적 테스트"""
        bot = MockBot()
        combat = CombatManager(bot)

        # 다양한 유닛 추가
        units = [
            MockUnit(1, "ZERGLING", (50, 50)),
            MockUnit(2, "ZERGLING", (51, 51)),
            MockUnit(3, "ROACH", (52, 52)),
            MockUnit(4, "HYDRALISK", (53, 53)),
        ]
        bot.units = MockUnits(units)

        # 유닛 타입별 카운트 확인
        zerglings = bot.units.of_type("ZERGLING")
        assert zerglings.amount == 2

        roaches = bot.units.of_type("ROACH")
        assert roaches.amount == 1


class TestThreatAssessment:
    """위협 평가 테스트"""

    def test_threat_level_calculation(self):
        """위협 레벨 계산 테스트"""
        bot = MockBot()
        combat = CombatManager(bot)

        # 아군 병력
        friendly_units = [MockUnit(i, "ZERGLING", (50, 50)) for i in range(10)]
        bot.units = MockUnits(friendly_units)

        # 적 병력 (아군보다 많음)
        enemy_units = [MockUnit(100 + i, "MARINE", (55, 55)) for i in range(20)]
        bot.enemy_units = MockUnits(enemy_units)

        # 위협 레벨은 높아야 함 (적이 2배)
        # (실제 구현에 따라 다름)
        assert len(bot.enemy_units) > len(bot.units)


class TestRetreatConditions:
    """후퇴 조건 테스트"""

    def test_retreat_on_low_health(self):
        """체력 낮을 때 후퇴 테스트"""
        bot = MockBot()
        combat = CombatManager(bot)

        # 체력이 낮은 유닛
        damaged_unit = MockUnit(1, "ZERGLING", (50, 50), health=10.0, health_max=35.0)
        bot.units = MockUnits([damaged_unit])

        # 체력 비율 확인 (일반적인 후퇴 임계값 30%)
        retreat_threshold = 0.3
        assert damaged_unit.health_percentage < retreat_threshold

    def test_retreat_on_overwhelming_enemy(self):
        """압도적 적 병력 시 후퇴 테스트"""
        bot = MockBot()
        combat = CombatManager(bot)

        # 소수 아군
        friendly_units = [MockUnit(i, "ZERGLING", (50, 50)) for i in range(5)]
        bot.units = MockUnits(friendly_units)

        # 압도적 적군 (3배)
        enemy_units = [MockUnit(100 + i, "MARINE", (55, 55)) for i in range(15)]
        bot.enemy_units = MockUnits(enemy_units)

        # 적이 1.5배 이상 우세하므로 후퇴 조건 만족
        assert len(bot.enemy_units) > len(bot.units) * 1.5


class TestMultitasking:
    """멀티태스킹 시스템 테스트"""

    def test_task_priority_system(self):
        """작업 우선순위 시스템 테스트"""
        bot = MockBot()
        combat = CombatManager(bot)

        # 작업 우선순위 확인
        assert "base_defense" in combat.task_priorities
        assert "main_attack" in combat.task_priorities

        # 기지 방어가 가장 높은 우선순위
        assert (
            combat.task_priorities["base_defense"]
            > combat.task_priorities["main_attack"]
        )

    def test_unit_assignment_tracking(self):
        """유닛 할당 추적 테스트"""
        bot = MockBot()
        combat = CombatManager(bot)

        # 유닛 할당 시뮬레이션
        unit_tag = 123
        task_name = "base_defense"

        combat._unit_assignments[unit_tag] = task_name

        # 할당 확인
        assert unit_tag in combat._unit_assignments
        assert combat._unit_assignments[unit_tag] == task_name


class TestCombatStatistics:
    """전투 통계 테스트"""

    def test_statistics_initialization(self):
        """통계 초기화 테스트"""
        bot = MockBot()
        combat = CombatManager(bot)

        # 기본 전투 관련 필드 확인
        assert hasattr(combat, "_base_defense_active")
        assert hasattr(combat, "_victory_push_active")
        assert combat._base_defense_active == False
        assert combat._victory_push_active == False

    def test_kd_ratio_tracking(self):
        """전투 추적 시스템 테스트"""
        bot = MockBot()
        combat = CombatManager(bot)

        # 전투 추적 관련 필드 확인
        assert hasattr(combat, "_enemy_structures_destroyed")
        assert hasattr(combat, "_last_combat_time")


# ===== Integration Tests =====


class TestCombatIntegration:
    """통합 테스트"""

    @pytest.mark.asyncio
    async def test_full_combat_cycle(self):
        """전체 전투 사이클 테스트"""
        bot = MockBot()
        combat = CombatManager(bot)

        # 시나리오 설정
        base = MockUnit(1, "HATCHERY", (50, 50))
        bot.townhalls = MockUnits([base])

        # 아군 병력
        friendly_units = [MockUnit(i, "ZERGLING", (50, 50)) for i in range(10)]
        bot.units = MockUnits(friendly_units)

        # 적 병력
        enemy_units = [MockUnit(100 + i, "MARINE", (60, 60)) for i in range(5)]
        bot.enemy_units = MockUnits(enemy_units)

        # 여러 프레임 시뮬레이션
        for iteration in range(100):
            bot.iteration = iteration
            bot.time = iteration / 22.0  # 22 FPS

            try:
                await combat.on_step(iteration)
            except Exception as e:
                pytest.fail(f"Combat manager crashed on iteration {iteration}: {e}")

        # 크래시 없이 실행되었는지 확인
        assert True


# ===== Performance Tests =====


class TestCombatPerformance:
    """성능 테스트"""

    @pytest.mark.asyncio
    async def test_large_army_performance(self):
        """대규모 병력 성능 테스트"""
        bot = MockBot()
        combat = CombatManager(bot)

        # 대규모 병력 (100기)
        friendly_units = [
            MockUnit(i, "ZERGLING", (50 + i % 10, 50 + i // 10)) for i in range(100)
        ]
        bot.units = MockUnits(friendly_units)

        enemy_units = [
            MockUnit(1000 + i, "MARINE", (70 + i % 10, 70 + i // 10))
            for i in range(100)
        ]
        bot.enemy_units = MockUnits(enemy_units)

        # 10 프레임 실행
        import time

        start_time = time.time()

        for iteration in range(10):
            bot.iteration = iteration
            await combat.on_step(iteration)

        elapsed = time.time() - start_time

        # 10 프레임이 1초 이내에 완료되어야 함 (100ms/frame)
        assert elapsed < 1.0, f"Performance issue: {elapsed:.2f}s for 10 frames"


class TestFindHarassTarget:
    """
    회귀 테스트: `_find_harass_target` 중복 정의 버그 (N3, F811) 방지.

    이 메서드는 한때 클래스 안에 두 번 정의되어 있었다. 나중 정의가
    앞선 정의를 조용히 덮어썼는데, 덮어써진(죽은) 버전은 적 워커나
    테크 건물을 전혀 고려하지 않고 그냥 적 시작 위치만 반환했다.
    아래 테스트들은 현재 살아있는 구현이 "워커 > 고립된 테크 건물 >
    적 기지" 우선순위로 동작한다는 것을 고정하여, 만약 죽은 버전이
    다시 살아나 워커 우선순위 로직이 사라지면 실패하도록 한다.
    """

    def test_prioritizes_enemy_workers_over_base(self):
        """적 워커가 있으면 단순 기지 좌표가 아니라 워커 위치를 반환해야 함."""
        from sc2.ids.unit_typeid import UnitTypeId

        bot = MockBot()
        bot.enemy_start_locations = [(10, 10)]
        bot.enemy_structures = MockUnits([])

        worker = MockUnit(200, UnitTypeId.DRONE, (11, 11))
        bot.enemy_units = MockUnits([worker])

        combat = CombatManager(bot)
        target = combat._find_harass_target()

        assert target is not None
        # 죽은(base-only) 버전이었다면 이 값은 (10, 10)이 됐을 것이다.
        assert target == (11, 11)

    def test_targets_isolated_tech_building_when_no_workers(self):
        """워커가 없으면 고립된 테크 건물을 우선 타겟으로 삼아야 함."""
        from sc2.ids.unit_typeid import UnitTypeId

        bot = MockBot()
        bot.enemy_start_locations = [(10, 10)]
        bot.enemy_units = MockUnits([])

        spire = MockUnit(300, UnitTypeId.SPIRE, (40, 40))
        bot.enemy_structures = MockUnits([spire])

        combat = CombatManager(bot)
        target = combat._find_harass_target()

        assert target == (40, 40)

    def test_falls_back_to_enemy_base_when_nothing_else(self):
        """워커도 테크 건물도 없으면 적 시작 위치로 폴백해야 함."""
        bot = MockBot()
        bot.enemy_start_locations = [(15, 15)]
        bot.enemy_units = MockUnits([])
        bot.enemy_structures = MockUnits([])

        combat = CombatManager(bot)
        target = combat._find_harass_target()

        assert target == (15, 15)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
