# -*- coding: utf-8 -*-
"""
Creep Denial System - 적 점막 제거 시스템

적의 시야와 기동성을 제한하기 위해 점막 종양(Creep Tumor)을 적극적으로 제거합니다.
ZvZ 매치업에서 특히 중요합니다.

기능:
1. 적 점막 종양 탐지 (보이는 것 + 숨겨진 것 추정)
2. 근처 아군 유닛(여왕, 히드라, 바퀴) 할당 (Unit Authority 권한 요청)
3. 안전 확인 후 제거 및 위협 시 후퇴
"""

from typing import List, Set, Optional, Dict
from sc2.position import Point2
from sc2.unit import Unit
from sc2.ids.unit_typeid import UnitTypeId
from sc2.ids.ability_id import AbilityId
from utils.logger import get_logger

try:
    from unit_authority_manager import UnitAuthorityManager, AuthorityLevel
except ImportError:
    UnitAuthorityManager = None
    AuthorityLevel = None

try:
    from config.unit_configs import CreepDenialConfig
except ImportError:
    CreepDenialConfig = None

class CreepDenialSystem:
    """
    적 점막 제거 시스템
    """
    def __init__(self, bot):
        self.bot = bot
        self.logger = get_logger("CreepDenial")

        # Load configuration
        self.config = CreepDenialConfig() if CreepDenialConfig else None

        # 제거 대상 태그 추적 (중복 명령 방지)
        # {tumor_tag: killer_tag}
        self.assignments: Dict[int, int] = {}

        # 제거에 사용할 유닛 타입 (설정값 사용)
        if self.config:
            self.killer_types = set()
            for unit_name in self.config.KILLER_UNIT_TYPES:
                try:
                    self.killer_types.add(getattr(UnitTypeId, unit_name))
                except AttributeError:
                    pass
        else:
            self.killer_types = {
                UnitTypeId.QUEEN,
                UnitTypeId.HYDRALISK,
                UnitTypeId.ROACH,
                UnitTypeId.RAVAGER,
            }

        # 점막 종양 타입 (설정값 사용)
        if self.config:
            self.tumor_types = set()
            for unit_name in self.config.TUMOR_TYPES:
                try:
                    self.tumor_types.add(getattr(UnitTypeId, unit_name))
                except AttributeError:
                    pass
        else:
            self.tumor_types = {
                UnitTypeId.CREEPTUMOR,
                UnitTypeId.CREEPTUMORQUEEN,
                UnitTypeId.CREEPTUMORBURROWED,
            }

    async def on_step(self, iteration: int):
        """매 프레임 실행 (최적화: 설정값 사용)"""
        # 1. 할당된 유닛 관리 (매 프레임)
        self._manage_assignments()

        update_interval = self.config.UPDATE_INTERVAL if self.config else 11
        if iteration % update_interval != 0:
            return

        # 2. 적 점막 종양 찾기
        enemy_tumors = self._find_enemy_tumors()
        if not enemy_tumors:
            return

        # 3. 제거 명령 실행 (새로운 할당)
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

    def _manage_assignments(self):
        """할당된 유닛 관리 (생존 확인 및 임무 완료 체크)"""
        if not self.assignments:
            return

        completed_tumors = []
        
        for tumor_tag, killer_tag in self.assignments.items():
            killer = self.bot.units.find_by_tag(killer_tag)
            
            # 1. 킬러가 죽거나 없어진 경우
            if not killer:
                completed_tumors.append(tumor_tag)
                continue
                
            # 2. 위협 체크 (즉시 후퇴)
            if self._is_dangerous_position(killer.position):
                # 권한 해제하여 CombatManager가 처리하도록 함
                if hasattr(self.bot, "unit_authority"):
                    self.bot.unit_authority.release_unit(killer.tag, "CreepDenial")
                completed_tumors.append(tumor_tag)
                continue

            # 3. 종양 제거 확인
            # 종양 태그로 찾을 수 없으면 제거된 것으로 간주 (시야 내에 있는데 없으면)
            # 주의: 시야 밖으로 나간 경우일 수도 있음.
            # 여기서는 간단히 킬러의 명령이 없거나 다른 것으로 바뀌었으면 해제
            if not killer.orders or killer.order_target != tumor_tag:
                 # 다시 공격 명령 (아직 종양이 있다면)
                 tumor = self.bot.enemy_structures.find_by_tag(tumor_tag)
                 if tumor:
                     killer.attack(tumor)
                 else:
                     # 종양 사라짐 -> 임무 완료
                     if hasattr(self.bot, "unit_authority"):
                        self.bot.unit_authority.release_unit(killer.tag, "CreepDenial")
                     completed_tumors.append(tumor_tag)

        for tag in completed_tumors:
            if tag in self.assignments:
                del self.assignments[tag]

    async def _assign_killers(self, tumors: List[Unit]):
        """
        종양 제거를 위해 유닛 할당
        """
        if not hasattr(self.bot, "unit_authority"):
            return

        # 이미 할당된 종양 제외
        tumors = [t for t in tumors if t.tag not in self.assignments]
        if not tumors:
            return

        # 가용한 아군 유닛 검색 (권한 없는 유닛들)
        # UnitAuthorityManager를 통해 나중에 요청하므로 여기서는 모든 후보군 검색
        my_units = self.bot.units.filter(
            lambda u: u.type_id in self.killer_types and not u.is_structure
        )
        
        if not my_units:
            return

        for tumor in tumors:
            # 1. 주변 아군 유닛 찾기 (설정값 사용)
            assignment_range = self.config.ASSIGNMENT_RANGE if self.config else 20
            nearby_units = my_units.closer_than(assignment_range, tumor.position)
            
            if not nearby_units:
                continue

            # 2. 위협 체크
            if self._is_dangerous_position(tumor.position):
                continue
                
            # 3. 공격 유닛 선택 
            # 가장 가까운 유닛 1기
            killer = nearby_units.closest_to(tumor)
            
            # 4. 권한 요청
            if self.bot.unit_authority.request_unit(
                unit_tag=killer.tag,
                requester="CreepDenial",
                level=AuthorityLevel.TACTICAL  # 정찰보다 높고 전투보다 낮음
            ):
                # 권한 획득 성공 -> 공격 명령
                killer.attack(tumor)
                self.assignments[tumor.tag] = killer.tag
                break # 한 프레임에 하나씩만 할당 (부하 방지)

    def _is_dangerous_position(self, position: Point2) -> bool:
        """
        해당 위치가 위험한지 판단 (설정값 사용)
        """
        if not hasattr(self.bot, "enemy_units"):
            return False

        # 설정값 로드
        danger_range = self.config.DANGER_DETECTION_RANGE if self.config else 12
        danger_count = self.config.DANGER_ENEMY_COUNT if self.config else 2

        # 무시할 유닛 타입 (설정값 사용)
        if self.config:
            ignore_types = set()
            for unit_name in self.config.IGNORE_UNIT_TYPES:
                try:
                    ignore_types.add(getattr(UnitTypeId, unit_name))
                except AttributeError:
                    pass
            ignore_types.update(self.tumor_types)
        else:
            ignore_types = self.tumor_types | {UnitTypeId.DRONE, UnitTypeId.PROBE, UnitTypeId.SCV}

        nearby_enemies = self.bot.enemy_units.closer_than(danger_range, position)

        combat_enemies = nearby_enemies.filter(
            lambda u: u.type_id not in ignore_types and not u.is_structure
        )

        if combat_enemies.amount >= danger_count:
            return True

        # 방어 타워 확인 (설정값 사용)
        if self.config:
            defense_types = set()
            for unit_name in self.config.STATIC_DEFENSE_TYPES:
                try:
                    defense_types.add(getattr(UnitTypeId, unit_name))
                except AttributeError:
                    pass
        else:
            defense_types = {UnitTypeId.SIEGETANK, UnitTypeId.SIEGETANKSIEGED,
                           UnitTypeId.SPINECRAWLER, UnitTypeId.PHOTONCANNON,
                           UnitTypeId.BUNKER, UnitTypeId.PLANETARYFORTRESS}

        static_defense = nearby_enemies.filter(lambda u: u.type_id in defense_types)
        if static_defense.exists:
            return True

        return False

