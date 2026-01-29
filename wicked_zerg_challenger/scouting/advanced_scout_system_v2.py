
"""
Advanced Scouting System V2 - 고급 정찰 시스템 V2

Phase 10 구현 사항:
1. 정찰 유닛 다양화 (일꾼, 저글링, 대군주, 감시군주+변신수)
2. 동적 정찰 주기 (기본 25초, 긴급 15초)
3. 지능형 목표 설정 (우선순위 기반)
4. Unit Authority Manager 연동
"""

import math
from typing import List, Optional, Tuple, Dict, Set
from utils.logger import get_logger

try:
    from sc2.bot_ai import BotAI
    from sc2.ids.unit_typeid import UnitTypeId
    from sc2.ids.ability_id import AbilityId
    from sc2.ids.upgrade_id import UpgradeId
    from sc2.position import Point2
    from sc2.unit import Unit
except ImportError:
    pass

from unit_authority_manager import UnitAuthorityManager, AuthorityLevel

class AdvancedScoutingSystemV2:
    def __init__(self, bot: BotAI):
        self.bot = bot
        self.logger = get_logger("AdvScoutV2")
        
        # 정찰 설정
        self.BASE_INTERVAL = 25.0
        self.EMERGENCY_INTERVAL = 15.0
        self.last_scout_time = 0.0
        
        # 정찰 유닛 상태
        # {tag: {"type": str, "target": Point2, "start_time": float}}
        self.active_scouts = {}
        
        # 정찰 목표 기록 (위치 -> 마지막 정찰 시간)
        self.last_scouted_at: Dict[Point2, float] = {}
        
        # 유닛별 최대 정찰 수
        self.MAX_SCOUTS = {
            "WORKER": 1,      # 초반용
            "ZERGLING": 3,    # 주력
            "OVERLORD": 2,    # 보조 (속업 후)
            "OVERSEER": 2     # 탐지/변신수
        }

    async def on_step(self, iteration: int):
        # 1. 활성 정찰 유닛 관리 (사망/임무완료 체크)
        self._manage_active_scouts()

        # 2. 정찰 주기 체크
        current_time = self.bot.time
        interval = self._get_dynamic_interval()

        if current_time - self.last_scout_time >= interval:
            if self._send_new_scout():
                self.last_scout_time = current_time

        # 3. 감시군주 변신수 활용
        await self._manage_changelings()

        # 4. 메모리 누수 방지: 오래된 정찰 데이터 정리 (50초마다)
        if iteration % 1100 == 0:
            self._cleanup_old_scout_data()

        # 5. 리포트 (30초마다)
        if iteration % 660 == 0:
            self._print_report()

    def _get_dynamic_interval(self) -> float:
        """적 정보 신선도에 따른 동적 주기 계산"""
        blackboard = getattr(self.bot, "blackboard", None)
        if not blackboard:
            return self.BASE_INTERVAL
            
        # 마지막 적 정보 갱신 시간 확인 (Blackboard 연동 가정)
        last_seen = getattr(blackboard, "last_enemy_seen_time", 0)
        info_age = self.bot.time - last_seen
        
        if info_age > 60.0:  # 1분 이상 정보 없음
            return self.EMERGENCY_INTERVAL
        return self.BASE_INTERVAL

    def _manage_active_scouts(self):
        """
        활성 정찰 유닛 모니터링 및 임무 완료 처리

        ★ NEW: Active Scout Safety - 정찰 유닛 생존 본능 ★
        - 공격받거나 체력 감소 시 즉시 후퇴
        - 적 대공 유닛 근처에서 회피
        """
        to_remove = []

        for tag, info in self.active_scouts.items():
            unit = self.bot.units.find_by_tag(tag)

            # 유닛 사망
            if not unit:
                to_remove.append(tag)
                continue

            # ★ NEW: Scout Safety Check - 위협 감지 및 회피 ★
            if self._scout_is_threatened(unit):
                # Retreat to main base immediately
                if hasattr(self.bot, "start_location"):
                    retreat_pos = self.bot.start_location
                    unit.move(retreat_pos)
                    self.logger.info(f"[SCOUT_RETREAT] {unit.type_id.name} retreating from threat (HP: {unit.health_percentage*100:.0f}%)")
                    # Remove from active scouts to allow reassignment
                    to_remove.append(tag)
                    continue
                
            # 목표 도달 (시야 범위 내)
            target = info["target"]
            sight = unit.sight_range
            
            if unit.distance_to(target) < sight * 0.8:
                self.last_scouted_at[target] = self.bot.time
                to_remove.append(tag)
                
                # 권한 해제
                if hasattr(self.bot, "unit_authority"):
                    self.bot.unit_authority.release_unit(tag, "AdvancedScoutingV2")
                
                # 정찰 완료 후 복귀 또는 순찰 등 추가 로직 가능
                
        for tag in to_remove:
            del self.active_scouts[tag]

    def _send_new_scout(self) -> bool:
        """새로운 정찰 유닛 파견"""
        target = self._select_scout_target()
        if not target:
            return False
            
        # 적절한 유닛 선택
        scout_unit = self._select_scout_unit(target)
        if not scout_unit:
            return False
            
        # 정찰 명령
        if self._request_authority(scout_unit):
            self.bot.do(scout_unit.move(target))
            self.active_scouts[scout_unit.tag] = {
                "type": scout_unit.type_id.name,
                "target": target,
                "start_time": self.bot.time
            }
            return True
            
        return False

    def _select_scout_target(self) -> Optional[Point2]:
        """우선순위 기반 정찰 목표 선택"""
        if not self.bot.expansion_locations_list:
            return None
            
        # 1. 미발견 확장 지역 (High)
        unscouted = [
            loc for loc in self.bot.expansion_locations_list
            if loc not in self.last_scouted_at
        ]
        if unscouted:
            # 적 시작 위치와 가까운 순서로
            if self.bot.enemy_start_locations:
                enemy_start = self.bot.enemy_start_locations[0]
            else:
                enemy_start = self.bot.game_info.map_center if hasattr(self.bot, "game_info") else None

            if not enemy_start:
                return unscouted[0]  # 기본적으로 첫 번째 위치 반환

            return min(unscouted, key=lambda p: p.distance_to(enemy_start))
            
        # 2. 정보가 오래된 지역 (Medium)
        sorted_locations = sorted(
            self.bot.expansion_locations_list,
            key=lambda p: self.last_scouted_at.get(p, 0)
        )
        
        # 가장 오래된 곳 선택 (최소 60초 이상 경과)
        target = sorted_locations[0]
        if self.bot.time - self.last_scouted_at.get(target, 0) > 60:
            return target
            
        # 3. 맵 중앙/감시탑 (Low) - 룰렛 방식이나 상황에 따라 추가
        return self.bot.game_info.map_center

    def _select_scout_unit(self, target: Point2) -> Optional[Unit]:
        """목표와 상황에 맞는 정찰 유닛 선택"""
        
        # 1. 감시군주 (은폐 감지 필요 시 or 안전한 공중 정찰)
        active_overseers = len([s for s in self.active_scouts.values() if s["type"] == "OVERSEER"])
        if active_overseers < self.MAX_SCOUTS["OVERSEER"]:
            overseers = self.bot.units(UnitTypeId.OVERSEER).filter(
                lambda u: u.tag not in self.active_scouts
            )
            if overseers:
                return overseers.closest_to(target)
                
        # 2. 저글링 (빠른 기동성)
        active_lings = len([s for s in self.active_scouts.values() if s["type"] == "ZERGLING"])
        if active_lings < self.MAX_SCOUTS["ZERGLING"]:
            zerglings = self.bot.units(UnitTypeId.ZERGLING).filter(
                lambda u: u.tag not in self.active_scouts and not u.is_burrowed
            )
            if zerglings:
                return zerglings.closest_to(target)
                
        # 3. 대군주 (속업 완료 시, 공중 시야)
        movement_speed = self.bot.state.upgrades
        has_speed = UpgradeId.OVERLORDSPEED in movement_speed
        
        active_overlords = len([s for s in self.active_scouts.values() if s["type"] == "OVERLORD"])
        # 속업 되어있고, 인구수가 넉넉할 때만 (안전)
        if has_speed and active_overlords < self.MAX_SCOUTS["OVERLORD"]:
            overlords = self.bot.units(UnitTypeId.OVERLORD).filter(
                lambda u: u.tag not in self.active_scouts
            )
            if overlords:
                return overlords.closest_to(target)
                
        # 4. 일꾼 (극초반)
        if self.bot.time < 180 and len(self.active_scouts) == 0:
            workers = self.bot.workers.filter(lambda u: not u.is_carrying_resource)
            if workers:
                return workers.closest_to(target)
                
        return None

    def _request_authority(self, unit: Unit) -> bool:
        """Unit Authority Manager에 권한 요청"""
        if not hasattr(self.bot, "unit_authority"):
            return True
        
        return self.bot.unit_authority.request_unit(
            unit_tag=unit.tag,
            requester="AdvancedScoutingV2",
            level=AuthorityLevel.SCOUTING
        )

    async def _manage_changelings(self):
        """감시군주 변신수 생성 및 활용"""
        overseers = self.bot.units(UnitTypeId.OVERSEER)
        for overseer in overseers:
            if overseer.energy >= 50:
                 # TODO: 적 기지 근처일 때만 사용하도록 최적화 가능
                 self.bot.do(overseer(AbilityId.SPAWNCHANGELING_SPAWNCHANGELING))

        # 변신수 정찰 (기본적으로 적 본진으로)
        changelings = self.bot.units(UnitTypeId.CHANGELING) | \
                      self.bot.units(UnitTypeId.CHANGELINGZEALOT) | \
                      self.bot.units(UnitTypeId.CHANGELINGMARINESHIELD) | \
                      self.bot.units(UnitTypeId.CHANGELINGMARINE) | \
                      self.bot.units(UnitTypeId.CHANGELINGZERGLING) | \
                      self.bot.units(UnitTypeId.CHANGELINGZERGLINGWINGS)

        if not changelings:
            return

        # 정찰 타겟 선택: 적 본진 또는 맵 중앙
        if self.bot.enemy_start_locations:
            target = self.bot.enemy_start_locations[0]
        elif hasattr(self.bot, "game_info") and self.bot.game_info.map_center:
            target = self.bot.game_info.map_center
        else:
            return  # 타겟이 없으면 정찰 중단

        for changeling in changelings:
            self.bot.do(changeling.move(target))

    def _scout_is_threatened(self, unit) -> bool:
        """
        Check if scout unit is threatened and should retreat.

        Threat conditions:
        1. HP below 50% (taking damage)
        2. Enemy anti-air units within 10 range (for air scouts)
        3. Enemy combat units within 5 range (for ground scouts)
        """
        # 1. Low HP check
        if unit.health_percentage < 0.5:
            return True

        # 2. Enemy threats nearby
        enemy_units = getattr(self.bot, "enemy_units", [])
        if not enemy_units:
            return False

        # Check for nearby threats
        is_flying = getattr(unit, "is_flying", False)
        threat_range = 10 if is_flying else 5

        for enemy in enemy_units:
            distance = unit.distance_to(enemy)
            if distance > threat_range:
                continue

            # Air scouts: check for anti-air capability
            if is_flying and getattr(enemy, "can_attack_air", False):
                return True

            # Ground scouts: any combat unit is a threat
            if not is_flying and not enemy.is_worker:
                return True

        return False

    def _cleanup_old_scout_data(self):
        """
        메모리 누수 방지: 오래된 정찰 데이터 정리

        - 60초 이상 전에 정찰한 위치 데이터는 유지 (재정찰 필요 판단용)
        - 하지만 메모리 제한을 위해 100개 이상이면 오래된 것부터 제거
        """
        if len(self.last_scouted_at) > 100:
            # 가장 오래된 50개 제거
            sorted_locations = sorted(
                self.last_scouted_at.items(),
                key=lambda x: x[1]  # 시간 기준 정렬
            )

            # 오래된 50개 제거
            for loc, _ in sorted_locations[:50]:
                del self.last_scouted_at[loc]

            self.logger.debug(f"Cleaned up old scout data: {len(self.last_scouted_at)} locations remaining")

    def _print_report(self):
        """정찰 상태 리포트"""
        types = [info['type'] for info in self.active_scouts.values()]
        counts = {t: types.count(t) for t in set(types)}

        self.logger.info(f"=== Advanced Scouting V2 Report ===")
        self.logger.info(f"Interval: {self._get_dynamic_interval()}s")
        self.logger.info(f"Active Scouts: {len(self.active_scouts)} {counts}")
        self.logger.info(f"Scouted Locations: {len(self.last_scouted_at)}/{len(self.bot.expansion_locations_list)}")
