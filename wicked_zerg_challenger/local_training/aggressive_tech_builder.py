# -*- coding: utf-8 -*-
"""
Aggressive Tech Builder - 자원이 넘칠 때 테크를 더 공격적으로 올리는 모듈

현재 건설 로직은 중복 건설을 잘 방지하지만, 자원이 넘칠 때 테크를 더 빠르게 올리거나
유연하게 대처하는 '과감함'이 필요합니다.

이 모듈은 자원이 넘칠 때:
1. 테크 건설 우선순위를 높임
2. Supply 조건을 완화하여 더 빠르게 테크를 올림
3. 여러 테크를 동시에 올릴 수 있도록 함
"""

from typing import Optional, Dict, List, Tuple
try:
    from sc2.ids.unit_typeid import UnitTypeId
except ImportError:
    class UnitTypeId:
        SPAWNINGPOOL = "SPAWNINGPOOL"
        EXTRACTOR = "EXTRACTOR"
        ROACHWARREN = "ROACHWARREN"
        HYDRALISKDEN = "HYDRALISKDEN"
        LAIR = "LAIR"
        HATCHERY = "HATCHERY"
        BANELINGNEST = "BANELINGNEST"
        EVOLUTIONCHAMBER = "EVOLUTIONCHAMBER"
        SPAIRE = "SPAIRE"


class AggressiveTechBuilder:
    """
    자원이 넘칠 때 테크를 더 공격적으로 올리는 빌더
    
    자원이 넘칠 때 (미네랄 800+, 가스 200+):
    - Supply 조건을 완화하여 더 빠르게 테크를 올림
    - 여러 테크를 동시에 올릴 수 있도록 함
    - 테크 건설 우선순위를 높임
    """
    
    def __init__(self, bot):
        self.bot = bot
        # 자원이 넘치는 기준값
        self.excess_mineral_threshold = 800  # 미네랄 800 이상
        self.excess_gas_threshold = 200      # 가스 200 이상
        # Supply 완화 비율 (자원이 넘칠 때 supply 조건을 이만큼 완화)
        self.supply_reduction_factor = 0.7   # 30% 완화 (예: 17 -> 12)
        
    def has_excess_resources(self) -> Tuple[bool, float, float]:
        """
        자원이 넘치는지 확인
        
        Returns:
            (has_excess, mineral_excess, gas_excess): 
            - has_excess: 자원이 넘치는지 여부
            - mineral_excess: 미네랄 초과량
            - gas_excess: 가스 초과량
        """
        minerals = getattr(self.bot, "minerals", 0)
        gas = getattr(self.bot, "vespene", 0)
        
        mineral_excess = max(0, minerals - self.excess_mineral_threshold)
        gas_excess = max(0, gas - self.excess_gas_threshold)
        
        has_excess = minerals >= self.excess_mineral_threshold or gas >= self.excess_gas_threshold
        
        return has_excess, mineral_excess, gas_excess
    
    def get_adjusted_supply_threshold(self, base_supply: float) -> float:
        """
        자원이 넘칠 때 supply 조건을 완화
        
        Args:
            base_supply: 기본 supply 조건
            
        Returns:
            완화된 supply 조건
        """
        has_excess, _, _ = self.has_excess_resources()
        if has_excess:
            return base_supply * self.supply_reduction_factor
        return base_supply
    
    async def should_build_tech_aggressively(
        self, 
        tech_type: UnitTypeId, 
        base_supply: float,
        check_existing: bool = True
    ) -> bool:
        """
        자원이 넘칠 때 테크를 더 공격적으로 올릴지 결정
        
        Args:
            tech_type: 건설할 테크 타입
            base_supply: 기본 supply 조건
            check_existing: 기존 건물 존재 여부 확인
            
        Returns:
            건설해야 하는지 여부
        """
        has_excess, mineral_excess, gas_excess = self.has_excess_resources()
        supply_used = getattr(self.bot, "supply_used", 0)
        
        # 기존 건물 확인
        if check_existing:
            if hasattr(self.bot, "structures"):
                existing = self.bot.structures(tech_type)
                if existing.exists or self.bot.already_pending(tech_type) > 0:
                    return False
        
        # 자원이 넘칠 때: supply 조건 완화
        if has_excess:
            adjusted_supply = self.get_adjusted_supply_threshold(base_supply)
            if supply_used >= adjusted_supply:
                return True
        else:
            # 자원이 넘치지 않을 때: 기본 조건
            if supply_used >= base_supply:
                return True
        
        return False
    
    async def build_tech_aggressively(
        self, 
        tech_type: UnitTypeId,
        build_func,
        base_supply: float = 17.0,
        priority: int = 1
    ) -> bool:
        """
        자원이 넘칠 때 테크를 더 공격적으로 올림
        
        Args:
            tech_type: 건설할 테크 타입
            build_func: 건설 함수 (async function)
            base_supply: 기본 supply 조건
            priority: 우선순위 (1=최우선, 2=차순위)
            
        Returns:
            건설 성공 여부
        """
        has_excess, mineral_excess, gas_excess = self.has_excess_resources()
        
        # 자원이 넘치지 않으면 기본 로직 사용
        if not has_excess:
            return False
        
        # 건설 가능 여부 확인
        if not self.bot.can_afford(tech_type):
            return False
        
        # Supply 조건 확인 (완화된 조건)
        should_build = await self.should_build_tech_aggressively(
            tech_type, 
            base_supply,
            check_existing=True
        )
        
        if not should_build:
            return False
        
        # 건설 실행
        try:
            result = await build_func()
            if result:
                excess_info = f"M:{int(mineral_excess)}+ G:{int(gas_excess)}+" if has_excess else ""
                print(f"[AGGRESSIVE TECH] [{int(self.bot.time)}s] Building {tech_type} "
                      f"at supply {self.bot.supply_used:.1f} (excess resources: {excess_info})")
                return True
        except Exception as e:
            if self.bot.iteration % 100 == 0:
                print(f"[AGGRESSIVE TECH] Failed to build {tech_type}: {e}")
        
        return False
    
    async def build_multiple_techs_aggressively(
        self,
        tech_priorities: List[Tuple[UnitTypeId, callable, float]]
    ) -> Dict[UnitTypeId, bool]:
        """
        자원이 넘칠 때 여러 테크를 동시에 올림
        
        Args:
            tech_priorities: [(tech_type, build_func, base_supply), ...] 리스트
        
        Returns:
            {tech_type: success} 딕셔너리
        """
        has_excess, _, _ = self.has_excess_resources()
        if not has_excess:
            return {}
        
        results = {}
        
        # 우선순위 순으로 건설
        sorted_techs = sorted(tech_priorities, key=lambda x: x[3] if len(x) > 3 else 1)
        
        for tech_info in sorted_techs:
            tech_type = tech_info[0]
            build_func = tech_info[1]
            base_supply = tech_info[2] if len(tech_info) > 2 else 17.0
            
            # 자원이 충분한지 확인
            if not self.bot.can_afford(tech_type):
                results[tech_type] = False
                continue
            
            # 건설 실행
            success = await self.build_tech_aggressively(
                tech_type,
                build_func,
                base_supply
            )
            results[tech_type] = success
            
            # 한 번에 하나씩만 건설 (중복 방지)
            if success:
                break
        
        return results
    
    def get_tech_build_priority(self, tech_type: UnitTypeId) -> int:
        """
        테크 건설 우선순위 반환
        
        Args:
            tech_type: 테크 타입
            
        Returns:
            우선순위 (1=최우선, 숫자가 클수록 낮은 우선순위)
        """
        priority_map = {
            UnitTypeId.SPAWNINGPOOL: 1,      # 최우선
            UnitTypeId.EXTRACTOR: 2,         # 차순위
            UnitTypeId.ROACHWARREN: 3,       # 3순위
            UnitTypeId.HYDRALISKDEN: 4,      # 4순위
            UnitTypeId.BANELINGNEST: 5,      # 5순위
            UnitTypeId.EVOLUTIONCHAMBER: 6,  # 6순위
            UnitTypeId.LAIR: 7,              # 7순위
            UnitTypeId.SPAIRE: 8,            # 8순위
        }
        return priority_map.get(tech_type, 10)
    
    async def recommend_tech_builds(self) -> List[Tuple[UnitTypeId, float, int]]:
        """
        자원이 넘칠 때 건설할 테크 추천
        
        Returns:
            [(tech_type, base_supply, priority), ...] 리스트
        """
        has_excess, mineral_excess, gas_excess = self.has_excess_resources()
        if not has_excess:
            return []
        
        recommendations = []
        supply_used = getattr(self.bot, "supply_used", 0)
        
        # Spawning Pool (기본 테크)
        if not self.bot.structures(UnitTypeId.SPAWNINGPOOL).exists:
            recommendations.append((UnitTypeId.SPAWNINGPOOL, 12.0, 1))
        
        # Extractor (가스가 부족할 때)
        if gas_excess < 100 and not self.bot.structures(UnitTypeId.EXTRACTOR).exists:
            recommendations.append((UnitTypeId.EXTRACTOR, 14.0, 2))
        
        # Roach Warren (미네랄이 많이 넘칠 때)
        if mineral_excess > 300 and not self.bot.structures(UnitTypeId.ROACHWARREN).exists:
            recommendations.append((UnitTypeId.ROACHWARREN, 20.0, 3))
        
        # Hydralisk Den (가스가 많이 넘칠 때)
        if gas_excess > 100 and not self.bot.structures(UnitTypeId.HYDRALISKDEN).exists:
            recommendations.append((UnitTypeId.HYDRALISKDEN, 25.0, 4))
        
        # Lair (미네랄과 가스가 모두 많이 넘칠 때) - 강화된 로직
        if (mineral_excess > 500 and gas_excess > 150 and 
            self.bot.structures(UnitTypeId.LAIR).amount == 0 and
            self.bot.structures(UnitTypeId.HATCHERY).ready.exists):
            # Spawning Pool 확인 (필수 요구사항)
            if self.bot.structures(UnitTypeId.SPAWNINGPOOL).ready.exists:
                # Extractor 확인 (가스 수입 확인)
                if self.bot.structures(UnitTypeId.EXTRACTOR).ready.exists:
                    recommendations.append((UnitTypeId.LAIR, 30.0, 5))
        
        return recommendations
