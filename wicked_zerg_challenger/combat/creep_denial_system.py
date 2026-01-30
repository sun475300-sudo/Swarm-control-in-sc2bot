# -*- coding: utf-8 -*-
"""
Creep Denial System - 적 점막 제거 시스템

적의 시야와 기동성을 제한하기 위해 점막 종양(Creep Tumor)을 적극적으로 제거합니다.
ZvZ 매치업에서 특히 중요합니다.

기능:
1. 적 점막 종양 탐지 (보이는 것 + 숨겨진 것 추정)
2. 근처 아군 유닛(여왕, 히드라, 바퀴) 할당
3. 안전 확인 후 제거
"""

from typing import List, Set, Optional, Dict
from sc2.position import Point2
from sc2.unit import Unit
from sc2.ids.unit_typeid import UnitTypeId
from sc2.ids.ability_id import AbilityId
from utils.logger import get_logger

class CreepDenialSystem:
    """
    적 점막 제거 시스템
    """
    def __init__(self, bot):
        self.bot = bot
        self.logger = get_logger("CreepDenial")
        
        # 제거 대상 태그 추적 (중복 명령 방지)
        self.target_tumors: Set[int] = set()
        
        # 제거에 사용할 유닛 타입
        self.killer_types = {
            UnitTypeId.QUEEN,
            UnitTypeId.HYDRALISK,
            UnitTypeId.ROACH,
            UnitTypeId.RAVAGER,
            UnitTypeId.ZERGLING, # 저글링은 위험할 수 있으므로 주의 필요
        }
        
        # 점막 종양 타입
        self.tumor_types = {
            UnitTypeId.CREEPTUMOR,
            UnitTypeId.CREEPTUMORQUEEN,
            UnitTypeId.CREEPTUMORBURROWED,
        }

    async def on_step(self, iteration: int):
        """매 프레임 실행 (최적화: 11프레임마다)"""
        if iteration % 11 != 0:
            return

        # 1. 적 점막 종양 찾기
        enemy_tumors = self._find_enemy_tumors()
        if not enemy_tumors:
            return

        # 2. 제거 명령 실행
        await self._assign_killers(enemy_tumors)

    def _find_enemy_tumors(self) -> List[Unit]:
        """적 점막 종양 탐색"""
        if not hasattr(self.bot, "enemy_structures"):
            return []
            
        # 적 구조물 중 Tumor 타입 필터링
        tumors = self.bot.enemy_structures.filter(
            lambda s: s.type_id in self.tumor_types
        )
        return list(tumors)

    async def _assign_killers(self, tumors: List[Unit]):
        """
        종양 제거를 위해 유닛 할당
        """
        # 가용한 아군 유닛 (전투 중이거나 중요 임무 중인 유닛 제외 고려 필요)
        # 여기서는 간단히 전체 유닛 중 필터링
        # TODO: Unit Authority Manager 연동 권장
        available_units = self.bot.units.filter(
            lambda u: u.type_id in self.killer_types and not u.is_structure
        )
        
        if not available_units:
            return

        actions = []
        assigned_killers = set()

        for tumor in tumors:
            # 1. 주변(15 거리) 아군 유닛 찾기
            nearby_units = available_units.closer_than(15, tumor.position)
            
            if not nearby_units:
                continue

            # 2. 위협 체크 (종양 근처에 적 주력 병력이 있으면 포기)
            if self._is_dangerous_position(tumor.position):
                continue
                
            # 3. 공격 유닛 선택 (가장 가까운 1~3기)
            # 히드라/여왕 우선 (사거리 우위)
            killers = nearby_units.sorted(
                lambda u: (
                    0 if u.type_id in {UnitTypeId.HYDRALISK, UnitTypeId.QUEEN} else 1,
                    u.distance_to(tumor)
                )
            )
            
            # 최대 2기만 할당해도 충분 (종양 체력 낮음)
            for killer in killers[:2]:
                if killer.tag in assigned_killers:
                    continue
                    
                # 이미 공격 중이면 스킵
                if killer.order_target == tumor.tag:
                    assigned_killers.add(killer.tag)
                    continue

                # 공격 명령
                actions.append(killer.attack(tumor))
                assigned_killers.add(killer.tag)
                
                # 로그 (가끔만)
                if self.bot.iteration % 200 == 0:
                    # self.logger.info(f"[CreepDenial] Killing tumor at {tumor.position} with {killer.type_id.name}")
                    pass

        if actions:
            await self.bot.do_actions(actions)

    def _is_dangerous_position(self, position: Point2) -> bool:
        """
        해당 위치가 위험한지 판단
        """
        # 적 유닛이 근처에 3기 이상이면 위험
        if hasattr(self.bot, "enemy_units"):
            nearby_enemies = self.bot.enemy_units.closer_than(10, position)
            # 일꾼이나 종양은 위협 아님
            combat_enemies = nearby_enemies.filter(
                lambda u: u.type_id not in self.tumor_types and 
                          u.type_id not in {UnitTypeId.DRONE, UnitTypeId.PROBE, UnitTypeId.SCV}
            )
            
            if combat_enemies.amount >= 3:
                return True
                
            # 탱크나 가시촉수 등 방어 타워 있으면 위험
            static_defense = nearby_enemies.filter(
                lambda u: u.type_id in {UnitTypeId.SIEGETANK, UnitTypeId.SIEGETANKSIEGED, 
                                      UnitTypeId.SPINECRAWLER, UnitTypeId.PHOTONCANNON, UnitTypeId.BUNKER}
            )
            if static_defense.exists:
                return True

        return False
