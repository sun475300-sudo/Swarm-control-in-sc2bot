# -*- coding: utf-8 -*-
"""
Overlord Hunter - 적 대군주 사냥 모듈

적의 시야를 끊어내기 위해 초반 대군주를 사냥합니다.
"""

from typing import Optional, Set, List
from sc2.ids.unit_typeid import UnitTypeId
from sc2.position import Point2
from sc2.units import Units

class OverlordHunter:
    """
    Overlord Hunter
    
    기능:
    1. 맵 주변의 적 대군주 탐지
    2. 사냥 유닛(퀸, 뮤탈 등) 할당 및 공격 유도
    3. 안전한 추적 (적 본진 깊숙이는 쫓지 않음)
    """
    
    def __init__(self, bot):
        self.bot = bot
        self.assigned_hunters: Set[int] = set() # tags of hunting units
        self.target_overlords: Set[int] = set() # tags of target overlords
        
    async def on_step(self, iteration: int):
        """매 프레임 실행"""
        # 1초에 한 번 정도만 로직 실행
        if iteration % 22 != 0:
            return
            
        # 1. 적 대군주 스캔
        overlords = self.bot.enemy_units.of_type(UnitTypeId.OVERLORD)
        if not overlords:
            self._release_hunters()
            return
            
        # 2. 사냥 가능한 대군주 필터링 (너무 멀거나 위험한 곳 제외)
        huntable_targets = self._filter_huntable_targets(overlords)
        
        if not huntable_targets:
            self._release_hunters()
            return

        # 3. 사냥꾼 할당 및 공격
        await self._assign_and_attack(huntable_targets)

    def _filter_huntable_targets(self, overlords: Units) -> Units:
        """사냥하기 좋은 위치의 대군주만 필터링"""
        # 우리 기지 근처거나, 맵 중앙 등에 떠있는 대군주

        # 수정: Units([], self.bot) 직접 생성자 호출 대신 일반 list 사용
        collected: List = []

        # 적 본진 위치 (추정)
        enemy_start = self.bot.enemy_start_locations[0] if self.bot.enemy_start_locations else None
        
        for ov in overlords:
            # 1. 적 본진에서 너무 가까우면 제외 (방어 타워 위험)
            if enemy_start and ov.distance_to(enemy_start) < 25:
                continue
                
            # 2. 우리 기지 근처에 있으면 최우선 타겟 (정찰 차단)
            near_base = any(
                ov.distance_to(th) < 30
                for th in self.bot.townhalls
            )
            
            if near_base:
                collected.append(ov)
                continue
                
            # 3. 그 외 안전한 구역 (필러 등)
            # 일단은 단순하게 우리 유닛이나 건물 주변
            # opponents risk calculation needed ideally
            collected.append(ov)

        # 수정: 필터링된 list를 Units 로 한 번만 감싸서 반환
        return overlords.filter(lambda ov: ov.tag in {u.tag for u in collected})

    async def _assign_and_attack(self, targets: Units):
        """유닛 할당 및 공격 명령"""
        # 퀸이나 대공 유닛 활용
        # 지금은 간단히: 여왕(Queen)이 근처에 있으면 공격
        
        for target in targets:
            # 타겟 근처의 여왕 찾기 (사거리 + 추적 거리)
            # 여왕 지상 이동 속도가 느리므로 너무 멀리 쫓지는 않음
            queens = self.bot.units(UnitTypeId.QUEEN).filter(
                lambda u: u.distance_to(target) < 15 and u.energy >= 0 # 조건
            )
            
            for queen in queens:
                # 이미 다른 중요한 일(펌핑, 수비) 중인지 체크?
                # 여기서는 간단히 공격 명령
                # ★ Stutter Step 모듈이 있다면 거기서 처리하겠지만, 
                # 여기서는 타겟 지정만 해줌
                
                # 공격 명령 (이미 공격 중이면 패스)
                if queen.order_target != target.tag:
                    self.bot.do(queen.attack(target))
                    self.assigned_hunters.add(queen.tag)
                    
        # 뮤탈/타락귀 등 공중 유닛이 있다면 추가 (나중 구현)

    def _release_hunters(self):
        """사냥 종료 시 상태 초기화"""
        self.assigned_hunters.clear()
        self.target_overlords.clear()
