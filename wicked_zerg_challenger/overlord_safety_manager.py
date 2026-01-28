# -*- coding: utf-8 -*-
"""
Overlord Safety Manager - 대군주 안전 관리 시스템

대군주를 안전하게 배치하고 생존성을 높임:
1. 안전한 고지대(Pillar) 및 시야 포인트 식별
2. 대공 위협 감지 및 자동 후퇴
3. 맵 전역 감시를 위한 분산 배치
"""

from typing import List, Dict, Optional, Set, Tuple
from sc2.position import Point2
from sc2.ids.unit_typeid import UnitTypeId
from utils.logger import get_logger
import random

class OverlordSafetyManager:
    """
    대군주 안전 관리자
    """

    def __init__(self, bot):
        self.bot = bot
        self.logger = get_logger("OverlordSafety")
        
        # 안전한 위치 (Pillars)
        self.safe_spots: List[Point2] = []
        self._pillars_calculated = False
        
        # 대군주 상태 추적
        self.overlord_assignments: Dict[int, Point2] = {}  # tag -> target_pos
        self.fleeing_overlords: Set[int] = set()
        
        # 설정
        self.SAFETY_DISTANCE = 15.0  # 대공 유닛과의 안전 거리
        self.RETREAT_DISTANCE = 10.0 # 후퇴 거리

    async def on_start(self):
        """게임 시작 시 실행"""
        self._calculate_safe_spots()

    async def on_step(self, iteration: int):
        """매 프레임 실행"""
        try:
            # 1. 안전 지대 계산 (아직 안 했으면)
            if not self._pillars_calculated:
                self._calculate_safe_spots()
                
            # 2. 대군주 관리 (2초마다)
            if iteration % 44 == 0:
                await self._manage_overlords()
                
            # 3. 위협 회피 (매 프레임 - 중요)
            if iteration % 4 == 0: # 자주 체크
                await self._check_threats()
                
        except Exception as e:
            if iteration % 200 == 0:
                self.logger.error(f"[OVERLORD_SAFETY] Error: {e}")

    def _calculate_safe_spots(self):
        """맵의 안전한 위치(Pillars) 계산"""
        if not hasattr(self.bot, "game_info"):
            return

        # 1. 맵의 전술적 고지대 (Pillars) 가져오기
        # sc2.game_info.GameInfo.overlord_spots or similar logic
        # 기본 라이브러리에서 제공하지 않을 경우 지형 분석 필요
        
        # 임시: 맵 경계 근처를 안전지대로 간주 (초간단 로직)
        # 실제로는 지형 높이(pathing grid vs height grid) 비교가 필요함
        
        if hasattr(self.bot.game_info, "map_size"):
            w = self.bot.game_info.map_size.width
            h = self.bot.game_info.map_size.height
            
            # 맵 가장자리 포인트
            self.safe_spots = [
                Point2((10, 10)), Point2((w/2, 10)), Point2((w-10, 10)),
                Point2((10, h/2)), Point2((w-10, h/2)),
                Point2((10, h-10)), Point2((w/2, h-10)), Point2((w-10, h-10))
            ]
            self._pillars_calculated = True
            
            # TODO: 실제 Pillar(공중 유닛만 갈 수 있는 지형) 계산 로직 추가 필요
            # TerrainAnalysis 모듈이 있다면 활용 가능

    async def _manage_overlords(self):
        """대군주 분산 배치"""
        overlords = self.bot.units(UnitTypeId.OVERLORD).idle
        if not overlords:
            return

        # 할당되지 않은 대군주 찾기
        unassigned = [ov for ov in overlords if ov.tag not in self.overlord_assignments]
        
        for ov in unassigned:
            # 권한 체크 (UnitAuthority)
            if hasattr(self.bot, "unit_authority"):
                from unit_authority_manager import Authority
                # 대군주는 낮은 우선순위로 제어 (드랍 등에 뺏길 수 있음)
                granted = self.bot.unit_authority.request_authority(
                    {ov.tag}, Authority.IDLE, "OverlordSafety", self.bot.state.game_loop
                )
                if ov.tag not in granted:
                    continue
            
            # 빈 안전 지대 찾기
            target = self._find_best_spot(ov)
            if target:
                self.overlord_assignments[ov.tag] = target
                self.bot.do(ov.move(target))

    def _find_best_spot(self, overlord) -> Optional[Point2]:
        """대군주에게 가장 적합한 안전 지대 찾기"""
        if not self.safe_spots:
            return None
            
        # 이미 점유된 위치 제외
        occupied = set(self.overlord_assignments.values())
        available = [s for s in self.safe_spots if s not in occupied]
        
        if not available:
            # 남는 자리가 없으면 랜덤 (또는 맵 중앙 제외)
            return random.choice(self.safe_spots)
            
        # 가장 가까운 곳
        return min(available, key=lambda s: overlord.distance_to(s))

    async def _check_threats(self):
        """대공 위협 감지 및 회피"""
        overlords = self.bot.units(UnitTypeId.OVERLORD)
        enemy_anti_air = self.bot.enemy_units.filter(lambda u: u.can_attack_air)
        
        # 대공 구조물
        enemy_structures = self.bot.enemy_structures.filter(
            lambda s: s.type_id in {
                UnitTypeId.MISSILETURRET, UnitTypeId.SPORECRAWLER, UnitTypeId.PHOTONCANNON, UnitTypeId.BUNKER
            }
        )
        
        for ov in overlords:
            # 드랍 작전 중인 대군주는 제외 (UnitAuthority로 체크 가능하지만 태그로 간단 체크)
            if hasattr(self.bot, "aggressive_strategies"):
                strat = self.bot.aggressive_strategies
                if hasattr(strat, "_drop_overlords") and ov.tag in strat._drop_overlords:
                    continue

            threats = []
            
            # 유닛 위협
            nearby_units = enemy_anti_air.closer_than(self.SAFETY_DISTANCE, ov)
            if nearby_units:
                threats.extend(nearby_units)
                
            # 구조물 위협
            nearby_structures = enemy_structures.closer_than(self.SAFETY_DISTANCE + 2, ov) # 구조물은 사거리 고려 더 넓게
            if nearby_structures:
                threats.extend(nearby_structures)
                
            if threats:
                # 회피 기동
                self.fleeing_overlords.add(ov.tag)
                
                # 가장 가까운 위협으로부터 반대 방향으로 도망
                closest_threat = min(threats, key=lambda t: t.distance_to(ov))
                flee_dir = ov.position - closest_threat.position
                target_pos = ov.position + flee_dir.normalized * self.RETREAT_DISTANCE
                
                # 맵 밖으로 안 나가게 클램핑 (필요 시)
                self.bot.do(ov.move(target_pos))
            else:
                if ov.tag in self.fleeing_overlords:
                    self.fleeing_overlords.remove(ov.tag)
                    # 다시 원래 자리로 복귀는 _manage_overlords가 처리
