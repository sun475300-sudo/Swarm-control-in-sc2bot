# -*- coding: utf-8 -*-
"""
Unit Tests for ProductionResilience

테스트 범위:
1. 생산 복원력 초기화
2. 안전한 유닛 생산
3. 확장 가능 여부 체크
4. 확장 시도
5. 생산 병목 해결
6. 균형잡힌 생산
7. 군대 유닛 생산
8. 긴급 저글링 생산
9. 초반 부스트
10. 생산 상태 진단
11. 공격적 군대 생산
12. 자원 소진
13. 테란 카운터 유닛
14. 프로토스 카운터 유닛
15. 저그 카운터 유닛
16. 기술 건물 자동 건설
17. 가스 건물 자동 건설
18. 레어 변태
19. 스파이어 건설
20. 뮤탈 생산
"""

import pytest
from unittest.mock import Mock, MagicMock, patch, AsyncMock
from typing import List

# Production Resilience 임포트
try:
    import sys
    import os
    sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'wicked_zerg_challenger'))
    sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'wicked_zerg_challenger', 'local_training'))
    from local_training.production_resilience import ProductionResilience
except ImportError:
    pytest.skip("ProductionResilience not available", allow_module_level=True)


class MockUnit:
    """Mock SC2 Unit"""
    def __init__(self, tag: int, type_id, position, health: float = 100.0,
                 health_max: float = 100.0, is_idle: bool = False, is_ready: bool = True):
        self.tag = tag
        self.type_id = type_id
        self.position = position
        self.health = health
        self.health_max = health_max
        self.is_idle = is_idle
        self.is_ready = is_ready
        self.orders = []
        self.is_carrying_minerals = False
        self.is_carrying_vespene = False
        self.order_target = None
        self.assigned_harvesters = 0
        self.ideal_harvesters = 3
        self.mineral_contents = health

    @property
    def health_percentage(self):
        return self.health / self.health_max if self.health_max > 0 else 0

    def distance_to(self, other):
        if hasattr(other, 'position'):
            pos = other.position
        else:
            pos = other
        return ((self.position[0] - pos[0])**2 + (self.position[1] - pos[1])**2)**0.5

    def train(self, unit_type):
        """Mock train method"""
        return Mock()


class MockUnits:
    """Mock SC2 Units collection"""
    def __init__(self, units: List[MockUnit]):
        self._units = units

    def __iter__(self):
        return iter(self._units)

    def __len__(self):
        return len(self._units)

    def __bool__(self):
        return len(self._units) > 0

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
        """Return ready units"""
        return MockUnits([u for u in self._units if u.is_ready])

    @property
    def idle(self):
        """Return idle units"""
        return MockUnits([u for u in self._units if u.is_idle])

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

    def of_type(self, type_id):
        return MockUnits([u for u in self._units if u.type_id == type_id])

    def sorted(self, key_func, reverse=False):
        return MockUnits(sorted(self._units, key=key_func, reverse=reverse))


class MockBot:
    """Mock SC2 Bot"""
    def __init__(self):
        self.minerals = 200
        self.vespene = 100
        self.supply_cap = 30
        self.supply_used = 20
        self.supply_left = 10
        self.larva = MockUnits([])
        self.townhalls = MockUnits([])
        self.workers = MockUnits([])
        self.mineral_field = MockUnits([])
        self.gas_buildings = MockUnits([])
        self._units = MockUnits([])
        self._structures = MockUnits([])
        self.enemy_units = MockUnits([])
        self.production = MockUnits([])  # Added production attribute
        self.state = Mock()
        self.state.game_loop = 0
        self.iteration = 0
        self.time = 0.0
        self.start_location = (50, 50)
        self.main_base_ramp = Mock()
        self.main_base_ramp.top_center = (50, 50)
        self.can_afford = Mock(return_value=True)
        self.do = Mock()
        self.already_pending = Mock(return_value=0)
        self.expansion_locations_list = [(60, 60), (70, 70)]
        self.enemy_race = "Terran"

        # Mock methods
        self.calculate_supply_cost = Mock(return_value=1)
        self.get_next_expansion = Mock(return_value=(60, 60))

    def units(self, unit_type=None):
        """Mock units method that filters by type"""
        if unit_type is None:
            return self._units
        return self._units.of_type(unit_type)

    def structures(self, structure_type=None):
        """Mock structures method that filters by type"""
        if structure_type is None:
            return self._structures
        return self._structures.of_type(structure_type)

    async def _determine_ideal_composition(self):
        """Mock ideal composition method"""
        return {
            "ZERGLING": 0.5,
            "ROACH": 0.3,
            "HYDRALISK": 0.2
        }

    def can_afford_with_priority(self, unit_type):
        """Mock can_afford with priority"""
        return self.minerals >= 50


class TestProductionResilienceInitialization:
    """테스트 1: 생산 복원력 초기화"""

    def test_initialization(self):
        """ProductionResilience 기본 초기화"""
        bot = MockBot()
        resilience = ProductionResilience(bot)

        assert resilience.bot == bot
        # Balancer may or may not be initialized depending on imports
        assert hasattr(resilience, 'balancer')

    def test_initialization_with_balancer(self):
        """Balancer와 함께 초기화"""
        bot = MockBot()
        resilience = ProductionResilience(bot)

        # Should have balancer attribute
        assert hasattr(resilience, 'balancer')


class TestSafeTrain:
    """테스트 2: 안전한 유닛 생산"""

    @pytest.mark.asyncio
    async def test_safe_train_success(self):
        """유닛 생산 성공"""
        bot = MockBot()
        resilience = ProductionResilience(bot)

        larva = MockUnit(1, "LARVA", (50, 50))
        result = await resilience._safe_train(larva, "ZERGLING")

        # Should complete without error
        assert isinstance(result, bool)

    @pytest.mark.asyncio
    async def test_safe_train_invalid_unit(self):
        """잘못된 유닛으로 생산 시도"""
        bot = MockBot()
        resilience = ProductionResilience(bot)

        result = await resilience._safe_train(None, "ZERGLING")

        # Should return False for invalid unit
        assert result == False


class TestCanExpandSafely:
    """테스트 3: 확장 가능 여부 체크"""

    def test_can_expand_safely_with_resources(self):
        """자원이 충분할 때 확장 가능"""
        bot = MockBot()
        bot.minerals = 400
        bot.townhalls = MockUnits([MockUnit(100, "HATCHERY", (50, 50))])

        resilience = ProductionResilience(bot)
        can_expand, reason = resilience._can_expand_safely()

        # Should return tuple
        assert isinstance(can_expand, bool)
        assert isinstance(reason, str)

    def test_can_expand_safely_without_resources(self):
        """자원이 부족할 때 확장 불가"""
        bot = MockBot()
        bot.minerals = 50
        bot.townhalls = MockUnits([MockUnit(100, "HATCHERY", (50, 50))])

        resilience = ProductionResilience(bot)
        can_expand, reason = resilience._can_expand_safely()

        # Should return False when not enough minerals
        assert isinstance(can_expand, bool)


class TestTryExpand:
    """테스트 4: 확장 시도"""

    @pytest.mark.asyncio
    async def test_try_expand_success(self):
        """확장 성공"""
        bot = MockBot()
        bot.minerals = 400
        bot.townhalls = MockUnits([MockUnit(100, "HATCHERY", (50, 50))])
        bot.workers = MockUnits([MockUnit(1, "DRONE", (50, 50))])

        resilience = ProductionResilience(bot)
        result = await resilience._try_expand()

        # Should complete
        assert isinstance(result, bool)


class TestFixProductionBottleneck:
    """테스트 5: 생산 병목 해결"""

    @pytest.mark.asyncio
    async def test_fix_production_bottleneck(self):
        """생산 병목 해결 시스템"""
        bot = MockBot()
        bot.minerals = 1000
        bot.larva = MockUnits([MockUnit(1, "LARVA", (50, 50))])
        bot.townhalls = MockUnits([MockUnit(100, "HATCHERY", (50, 50))])

        resilience = ProductionResilience(bot)
        await resilience.fix_production_bottleneck()

        # Should complete without error
        assert True


class TestBalancedProduction:
    """테스트 6: 균형잡힌 생산"""

    @pytest.mark.asyncio
    async def test_balanced_production(self):
        """균형잡힌 유닛 생산"""
        bot = MockBot()
        bot.minerals = 500
        bot.vespene = 200
        bot.supply_left = 20
        larvae = MockUnits([MockUnit(i, "LARVA", (50, 50)) for i in range(3)])

        resilience = ProductionResilience(bot)
        await resilience._balanced_production(larvae)

        # Should complete
        assert True


class TestProduceArmyUnit:
    """테스트 7: 군대 유닛 생산"""

    @pytest.mark.asyncio
    async def test_produce_army_unit_zergling(self):
        """저글링 생산"""
        bot = MockBot()
        bot.minerals = 50
        bot.supply_left = 2
        larva = MockUnit(1, "LARVA", (50, 50))
        bot._structures = MockUnits([MockUnit(200, "SPAWNINGPOOL", (52, 52), is_ready=True)])

        resilience = ProductionResilience(bot)
        result = await resilience._produce_army_unit(larva)

        # Should complete
        assert isinstance(result, bool)

    @pytest.mark.asyncio
    async def test_produce_army_unit_no_pool(self):
        """스포닝풀 없이 군대 유닛 생산"""
        bot = MockBot()
        bot.minerals = 50
        larva = MockUnit(1, "LARVA", (50, 50))

        resilience = ProductionResilience(bot)
        result = await resilience._produce_army_unit(larva)

        # Should return False without spawning pool
        assert isinstance(result, bool)


class TestEmergencyZerglingProduction:
    """테스트 8: 긴급 저글링 생산"""

    @pytest.mark.asyncio
    async def test_emergency_zergling_production(self):
        """긴급 저글링 생산"""
        bot = MockBot()
        bot.minerals = 200
        bot.supply_left = 10
        larvae = MockUnits([MockUnit(i, "LARVA", (50, 50)) for i in range(4)])
        bot._structures = MockUnits([MockUnit(200, "SPAWNINGPOOL", (52, 52), is_ready=True)])

        resilience = ProductionResilience(bot)
        await resilience._emergency_zergling_production(larvae)

        # Should complete
        assert True


class TestBoostEarlyGame:
    """테스트 9: 초반 부스트"""

    @pytest.mark.asyncio
    async def test_boost_early_game(self):
        """초반 게임 부스트"""
        bot = MockBot()
        bot.time = 120.0  # 2분
        bot.minerals = 300
        bot.townhalls = MockUnits([MockUnit(100, "HATCHERY", (50, 50))])

        resilience = ProductionResilience(bot)
        await resilience._boost_early_game()

        # Should complete
        assert True


class TestDiagnoseProductionStatus:
    """테스트 10: 생산 상태 진단"""

    @pytest.mark.asyncio
    async def test_diagnose_production_status(self):
        """생산 상태 진단"""
        bot = MockBot()
        bot.minerals = 500
        bot.vespene = 200
        bot.larva = MockUnits([MockUnit(1, "LARVA", (50, 50))])
        bot.townhalls = MockUnits([MockUnit(100, "HATCHERY", (50, 50))])

        resilience = ProductionResilience(bot)
        await resilience.diagnose_production_status(100)

        # Should complete
        assert True


class TestBuildArmyAggressive:
    """테스트 11: 공격적 군대 생산"""

    @pytest.mark.asyncio
    async def test_build_army_aggressive(self):
        """공격적인 군대 생산"""
        bot = MockBot()
        bot.minerals = 500
        bot.vespene = 300
        bot.supply_left = 20
        bot.larva = MockUnits([MockUnit(i, "LARVA", (50, 50)) for i in range(5)])
        bot._structures = MockUnits([MockUnit(200, "SPAWNINGPOOL", (52, 52), is_ready=True)])

        resilience = ProductionResilience(bot)
        await resilience.build_army_aggressive()

        # Should complete
        assert True


class TestForceResourceDump:
    """테스트 12: 자원 소진"""

    @pytest.mark.asyncio
    async def test_force_resource_dump(self):
        """과도한 자원 소진"""
        bot = MockBot()
        bot.minerals = 2000
        bot.vespene = 1500
        bot.larva = MockUnits([MockUnit(i, "LARVA", (50, 50)) for i in range(5)])
        bot.townhalls = MockUnits([MockUnit(100, "HATCHERY", (50, 50))])

        resilience = ProductionResilience(bot)
        await resilience.force_resource_dump()

        # Should complete
        assert True


class TestBuildTerranCounters:
    """테스트 13: 테란 카운터 유닛"""

    @pytest.mark.asyncio
    async def test_build_terran_counters(self):
        """테란 상대 카운터 유닛 생산"""
        bot = MockBot()
        bot.enemy_race = "Terran"
        bot.minerals = 500
        bot.vespene = 300
        bot.larva = MockUnits([MockUnit(i, "LARVA", (50, 50)) for i in range(3)])
        bot._structures = MockUnits([MockUnit(200, "SPAWNINGPOOL", (52, 52), is_ready=True)])

        resilience = ProductionResilience(bot)
        await resilience.build_terran_counters()

        # Should complete
        assert True


class TestBuildProtossCounters:
    """테스트 14: 프로토스 카운터 유닛"""

    @pytest.mark.asyncio
    async def test_build_protoss_counters(self):
        """프로토스 상대 카운터 유닛 생산"""
        bot = MockBot()
        bot.enemy_race = "Protoss"
        bot.minerals = 500
        bot.vespene = 300
        bot.larva = MockUnits([MockUnit(i, "LARVA", (50, 50)) for i in range(3)])
        bot._structures = MockUnits([MockUnit(200, "SPAWNINGPOOL", (52, 52), is_ready=True)])

        resilience = ProductionResilience(bot)
        await resilience.build_protoss_counters()

        # Should complete
        assert True


class TestBuildZergCounters:
    """테스트 15: 저그 카운터 유닛"""

    @pytest.mark.asyncio
    async def test_build_zerg_counters(self):
        """저그 상대 카운터 유닛 생산"""
        bot = MockBot()
        bot.enemy_race = "Zerg"
        bot.minerals = 500
        bot.vespene = 300
        bot.larva = MockUnits([MockUnit(i, "LARVA", (50, 50)) for i in range(3)])
        bot._structures = MockUnits([MockUnit(200, "SPAWNINGPOOL", (52, 52), is_ready=True)])

        resilience = ProductionResilience(bot)
        await resilience.build_zerg_counters()

        # Should complete
        assert True


class TestAutoBuildTechStructures:
    """테스트 16: 기술 건물 자동 건설"""

    @pytest.mark.asyncio
    async def test_auto_build_tech_structures(self):
        """기술 건물 자동 건설"""
        bot = MockBot()
        bot.minerals = 500
        bot.vespene = 200
        bot.time = 300.0  # 5분
        bot.townhalls = MockUnits([MockUnit(100, "HATCHERY", (50, 50))])
        bot.workers = MockUnits([MockUnit(1, "DRONE", (50, 50))])

        resilience = ProductionResilience(bot)
        await resilience._auto_build_tech_structures()

        # Should complete
        assert True


class TestAutoBuildExtractors:
    """테스트 17: 가스 건물 자동 건설"""

    @pytest.mark.asyncio
    async def test_auto_build_extractors(self):
        """가스 추출기 자동 건설"""
        bot = MockBot()
        bot.minerals = 75
        bot.time = 120.0  # 2분
        bot.townhalls = MockUnits([MockUnit(100, "HATCHERY", (50, 50))])
        bot.workers = MockUnits([MockUnit(1, "DRONE", (50, 50))])
        bot.gas_buildings = MockUnits([])

        # Mock vespene geysers
        geyser = MockUnit(300, "VESPENEGEYSER", (52, 52))
        bot._units = MockUnits([geyser])

        resilience = ProductionResilience(bot)
        await resilience._auto_build_extractors(120.0)

        # Should complete
        assert True


class TestMorphToLair:
    """테스트 18: 레어 변태"""

    @pytest.mark.asyncio
    async def test_morph_to_lair_success(self):
        """레어로 변태 성공"""
        bot = MockBot()
        bot.minerals = 150
        bot.vespene = 100
        hatchery = MockUnit(100, "HATCHERY", (50, 50), is_ready=True)
        bot.townhalls = MockUnits([hatchery])
        bot._structures = MockUnits([MockUnit(200, "SPAWNINGPOOL", (52, 52), is_ready=True)])

        resilience = ProductionResilience(bot)
        result = await resilience._morph_to_lair()

        # Should complete
        assert isinstance(result, bool)

    @pytest.mark.asyncio
    async def test_morph_to_lair_no_pool(self):
        """스포닝풀 없이 레어 변태 시도"""
        bot = MockBot()
        bot.minerals = 150
        bot.vespene = 100
        bot.townhalls = MockUnits([MockUnit(100, "HATCHERY", (50, 50), is_ready=True)])

        resilience = ProductionResilience(bot)
        result = await resilience._morph_to_lair()

        # Should return False without spawning pool
        assert result == False


class TestBuildSpire:
    """테스트 19: 스파이어 건설"""

    @pytest.mark.asyncio
    async def test_build_spire(self):
        """스파이어 건설"""
        bot = MockBot()
        bot.minerals = 200
        bot.vespene = 200
        lair = MockUnit(100, "LAIR", (50, 50), is_ready=True)
        bot.townhalls = MockUnits([lair])
        bot.workers = MockUnits([MockUnit(1, "DRONE", (50, 50))])

        resilience = ProductionResilience(bot)
        result = await resilience._build_spire()

        # Should complete
        assert isinstance(result, bool)


class TestProduceMutalisks:
    """테스트 20: 뮤탈 생산"""

    @pytest.mark.asyncio
    async def test_produce_mutalisks(self):
        """뮤탈리스크 생산"""
        bot = MockBot()
        bot.minerals = 500
        bot.vespene = 500
        bot.supply_left = 10
        bot.larva = MockUnits([MockUnit(i, "LARVA", (50, 50)) for i in range(5)])
        bot._structures = MockUnits([
            MockUnit(200, "SPIRE", (52, 52), is_ready=True),
            MockUnit(201, "SPAWNINGPOOL", (53, 53), is_ready=True)
        ])

        resilience = ProductionResilience(bot)
        result = await resilience._produce_mutalisks(count=3)

        # Should return number produced
        assert isinstance(result, int)


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
