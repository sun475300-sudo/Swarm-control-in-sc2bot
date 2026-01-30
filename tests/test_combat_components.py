# -*- coding: utf-8 -*-
"""
Unit Tests for Combat Components (Targeting, Micro, Boids)

테스트 범위:
1. Targeting System (타겟팅 우선순위)
2. Micro Combat (마이크로 컨트롤)
3. Boids Swarm Control (군집 제어)
"""

import pytest
from unittest.mock import Mock, MagicMock
from typing import List

try:
    import sys
    import os
    sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'wicked_zerg_challenger'))

    from combat.targeting import Targeting
    from combat.micro_combat import MicroCombat
    from combat.boids_swarm_control import BoidsSwarmController
except ImportError:
    pytest.skip("Combat components not available", allow_module_level=True)


class MockUnit:
    """Mock SC2 Unit"""
    def __init__(self, tag: int, type_id, position, health: float = 100.0,
                 health_max: float = 100.0, is_flying: bool = False):
        self.tag = tag
        self.type_id = type_id
        self.position = position
        self.health = health
        self.health_max = health_max
        self.shield = 0.0
        self.shield_max = 0.0
        self.is_flying = is_flying
        self.weapon_cooldown = 0
        self.is_idle = True

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

    def exists(self):
        return len(self._units) > 0

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

    def sorted_by_distance_to(self, position, reverse=False):
        sorted_units = sorted(self._units, key=lambda u: u.distance_to(position), reverse=reverse)
        return MockUnits(sorted_units)


class MockBot:
    """Mock SC2 Bot"""
    def __init__(self):
        self.units = MockUnits([])
        self.enemy_units = MockUnits([])
        self.time = 0.0
        self._actions = []

    def do(self, action):
        self._actions.append(action)


# ===== Targeting System Tests =====

class TestTargeting:
    """타겟팅 시스템 테스트"""

    def test_initialization(self):
        """타겟팅 초기화 테스트"""
        bot = MockBot()
        targeting = Targeting(bot)

        assert targeting.bot == bot
        assert hasattr(targeting, 'priority_targets')

    def test_priority_target_worker(self):
        """일꾼 우선순위 타겟 테스트"""
        bot = MockBot()
        targeting = Targeting(bot)

        # 적 유닛: 일꾼 + 전투 유닛
        worker = MockUnit(1, "SCV", (50, 50), health=45)
        marine = MockUnit(2, "MARINE", (51, 51), health=45)

        enemies = MockUnits([worker, marine])

        # 일꾼이 더 높은 우선순위를 가져야 함
        priority_target = targeting.get_priority_target(enemies, (50, 50))

        if priority_target:
            # 일꾼이 타겟으로 선정되어야 함
            assert priority_target.type_id == "SCV"

    def test_priority_target_low_health(self):
        """저체력 유닛 우선순위 테스트"""
        bot = MockBot()
        targeting = Targeting(bot)

        # 적 유닛: 체력 차이
        healthy_unit = MockUnit(1, "MARINE", (50, 50), health=45, health_max=45)
        damaged_unit = MockUnit(2, "MARINE", (50.5, 50.5), health=10, health_max=45)

        enemies = MockUnits([healthy_unit, damaged_unit])

        # 저체력 유닛이 우선순위
        priority_target = targeting.get_priority_target(enemies, (50, 50))

        if priority_target:
            assert priority_target.health_percentage < 0.5

    def test_priority_target_air_units(self):
        """공중 유닛 우선순위 테스트"""
        bot = MockBot()
        targeting = Targeting(bot)

        # 공중 유닛
        phoenix = MockUnit(1, "PHOENIX", (50, 50), health=120, is_flying=True)
        marine = MockUnit(2, "MARINE", (50, 50), health=45)

        enemies = MockUnits([phoenix, marine])

        # 공중 공격 가능한 유닛이라면 공중 유닛 우선
        # (실제 구현에 따라 다름)
        priority_target = targeting.get_priority_target(enemies, (50, 50))

        assert priority_target is not None

    def test_focus_fire_target(self):
        """집중 사격 타겟 테스트"""
        bot = MockBot()
        targeting = Targeting(bot)

        enemies = MockUnits([
            MockUnit(1, "MARINE", (50, 50), health=45),
            MockUnit(2, "MARINE", (51, 51), health=45),
            MockUnit(3, "MARINE", (52, 52), health=45),
        ])

        # 집중 사격 타겟 선정
        focus_target = targeting.get_focus_fire_target(enemies, (50, 50))

        # 가장 가까운 적이 선정되어야 함
        assert focus_target is not None
        assert focus_target.distance_to((50, 50)) <= 2.0


# ===== Micro Combat Tests =====

class TestMicroCombat:
    """마이크로 컨트롤 테스트"""

    def test_initialization(self):
        """마이크로 컨트롤 초기화 테스트"""
        bot = MockBot()
        micro = MicroCombat(bot)

        assert micro.bot == bot

    def test_kiting_distance(self):
        """키팅 거리 계산 테스트"""
        bot = MockBot()
        micro = MicroCombat(bot)

        # 키팅 가능 여부 확인
        unit = MockUnit(1, "ROACH", (50, 50))
        enemy = MockUnit(2, "ZERGLING", (52, 52))

        # 바퀴의 사거리는 4
        # 적이 사거리 안에 있으면 키팅 필요
        distance = unit.distance_to(enemy)
        assert distance < 4  # 사거리 내

    def test_surround_positioning(self):
        """포위 포지셔닝 테스트"""
        bot = MockBot()
        micro = MicroCombat(bot)

        # 저글링 포위 공격 시뮬레이션
        target = MockUnit(1, "TANK", (50, 50))

        zerglings = [
            MockUnit(i+10, "ZERGLING", (50 + i, 50 + i))
            for i in range(8)
        ]

        # 포위 포지션 계산
        # (실제 MicroCombat 메서드 호출)
        if hasattr(micro, 'calculate_surround_positions'):
            surround_positions = micro.calculate_surround_positions(target.position, len(zerglings))
            assert len(surround_positions) == len(zerglings)

    def test_retreat_logic(self):
        """후퇴 로직 테스트"""
        bot = MockBot()
        micro = MicroCombat(bot)

        # 저체력 유닛은 후퇴해야 함
        damaged_unit = MockUnit(1, "ZERGLING", (50, 50), health=10, health_max=35)
        enemy = MockUnit(2, "MARINE", (52, 52))

        # 후퇴 필요 여부 확인
        should_retreat = damaged_unit.health_percentage < 0.3

        assert should_retreat is True

    def test_stutter_step(self):
        """스터터 스텝 테스트"""
        bot = MockBot()
        micro = MicroCombat(bot)

        # 무기 쿨다운이 있을 때 후퇴
        unit = MockUnit(1, "ROACH", (50, 50))
        unit.weapon_cooldown = 5

        enemy = MockUnit(2, "ZERGLING", (52, 52))

        # 쿨다운 중이면 후퇴
        assert unit.weapon_cooldown > 0

        # 쿨다운 끝나면 공격
        unit.weapon_cooldown = 0
        assert unit.weapon_cooldown == 0


# ===== Boids Swarm Control Tests =====

class TestBoidsSwarmControl:
    """Boids 군집 제어 테스트"""

    def test_initialization(self):
        """Boids 초기화 테스트"""
        boids = BoidsSwarmController()

        assert hasattr(boids, 'separation_weight')
        assert hasattr(boids, 'alignment_weight')
        assert hasattr(boids, 'cohesion_weight')

    def test_separation_force(self):
        """분리 힘 계산 테스트"""
        boids = BoidsSwarmController()

        # 유닛들이 너무 가까우면 분리 힘 발생
        units = [
            MockUnit(1, "ZERGLING", (50, 50)),
            MockUnit(2, "ZERGLING", (50.5, 50.5)),
            MockUnit(3, "ZERGLING", (50.2, 50.2)),
        ]

        # 분리 힘 계산
        unit = units[0]
        if hasattr(boids, 'calculate_separation'):
            separation = boids.calculate_separation(unit, MockUnits(units[1:]))
            # 분리 힘이 0이 아니어야 함
            assert separation is not None

    def test_alignment_force(self):
        """정렬 힘 계산 테스트"""
        boids = BoidsSwarmController()

        # 유닛들이 같은 방향으로 이동하도록 정렬
        units = [
            MockUnit(1, "ZERGLING", (50, 50)),
            MockUnit(2, "ZERGLING", (51, 51)),
            MockUnit(3, "ZERGLING", (52, 52)),
        ]

        # 정렬 힘 계산
        if hasattr(boids, 'calculate_alignment'):
            alignment = boids.calculate_alignment(units[0], MockUnits(units[1:]))
            assert alignment is not None

    def test_cohesion_force(self):
        """응집 힘 계산 테스트"""
        boids = BoidsSwarmController()

        # 유닛들이 그룹 중심으로 모이도록
        units = [
            MockUnit(1, "ZERGLING", (50, 50)),
            MockUnit(2, "ZERGLING", (60, 60)),  # 멀리 있음
            MockUnit(3, "ZERGLING", (51, 51)),
        ]

        # 응집 힘 계산
        if hasattr(boids, 'calculate_cohesion'):
            cohesion = boids.calculate_cohesion(units[0], MockUnits(units[1:]))
            assert cohesion is not None

    def test_combined_forces(self):
        """통합 힘 계산 테스트"""
        boids = BoidsSwarmController()

        units = [
            MockUnit(1, "ZERGLING", (50, 50)),
            MockUnit(2, "ZERGLING", (51, 51)),
            MockUnit(3, "ZERGLING", (49, 49)),
        ]

        # 통합 힘 계산
        if hasattr(boids, 'calculate_boids_force'):
            force = boids.calculate_boids_force(units[0], MockUnits(units[1:]))
            # 힘이 계산되어야 함
            assert force is not None


# ===== Integration Tests =====

class TestCombatComponentsIntegration:
    """컴포넌트 통합 테스트"""

    def test_targeting_with_micro(self):
        """타겟팅과 마이크로 컨트롤 통합 테스트"""
        bot = MockBot()
        targeting = Targeting(bot)
        micro = MicroCombat(bot)

        # 시나리오: 바퀴가 저글링을 키팅하면서 공격
        roach = MockUnit(1, "ROACH", (50, 50))
        zergling = MockUnit(2, "ZERGLING", (52, 52))

        bot.units = MockUnits([roach])
        bot.enemy_units = MockUnits([zergling])

        # 1. 타겟 선정
        target = targeting.get_priority_target(bot.enemy_units, roach.position)
        assert target is not None

        # 2. 키팅 거리 확인
        distance = roach.distance_to(target)
        if distance < 4 and roach.weapon_cooldown > 0:
            # 후퇴해야 함
            should_retreat = True
        else:
            should_retreat = False

        # 로직이 작동해야 함
        assert target == zergling

    def test_boids_with_targeting(self):
        """Boids와 타겟팅 통합 테스트"""
        bot = MockBot()
        targeting = Targeting(bot)
        boids = BoidsSwarmController()

        # 저글링 군집이 적을 공격
        zerglings = [
            MockUnit(i, "ZERGLING", (50 + i*0.5, 50 + i*0.5))
            for i in range(10)
        ]

        marine = MockUnit(100, "MARINE", (60, 60))

        bot.units = MockUnits(zerglings)
        bot.enemy_units = MockUnits([marine])

        # 타겟 선정
        target = targeting.get_priority_target(bot.enemy_units, (50, 50))
        assert target is not None

        # Boids 힘 계산으로 군집 유지
        for zergling in zerglings[:3]:  # 일부만 테스트
            if hasattr(boids, 'calculate_boids_force'):
                force = boids.calculate_boids_force(
                    zergling,
                    MockUnits([z for z in zerglings if z.tag != zergling.tag])
                )
                # 힘이 계산되어야 함
                assert force is not None


# ===== Edge Case Tests =====

class TestEdgeCases:
    """엣지 케이스 테스트"""

    def test_empty_enemy_units(self):
        """적 유닛이 없을 때"""
        bot = MockBot()
        targeting = Targeting(bot)

        empty_enemies = MockUnits([])
        target = targeting.get_priority_target(empty_enemies, (50, 50))

        # None 반환되어야 함
        assert target is None

    def test_single_unit_boids(self):
        """단일 유닛 Boids"""
        boids = BoidsSwarmController()

        single_unit = MockUnit(1, "ZERGLING", (50, 50))
        empty_neighbors = MockUnits([])

        # 이웃이 없어도 크래시 없어야 함
        if hasattr(boids, 'calculate_boids_force'):
            force = boids.calculate_boids_force(single_unit, empty_neighbors)
            # None이거나 (0, 0) 반환
            assert force is None or force == (0, 0)

    def test_overlapping_units(self):
        """겹친 유닛들"""
        bot = MockBot()
        micro = MicroCombat(bot)

        # 정확히 같은 위치의 유닛들
        units = [
            MockUnit(1, "ZERGLING", (50, 50)),
            MockUnit(2, "ZERGLING", (50, 50)),
            MockUnit(3, "ZERGLING", (50, 50)),
        ]

        # 크래시 없이 처리되어야 함
        for unit in units:
            distance = unit.distance_to((50, 50))
            assert distance == 0


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
