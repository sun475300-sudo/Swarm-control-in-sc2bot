
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

        # 정찰 설정 - ★ Phase 17: 더 빈번한 정찰 ★
        self.BASE_INTERVAL = 25.0
        self.EMERGENCY_INTERVAL = 15.0
        self.EARLY_GAME_INTERVAL = 30.0  # 초반 (0-5분): 30초마다
        self.MID_GAME_INTERVAL = 60.0     # 중반 (5-10분): 1분마다
        self.LATE_GAME_INTERVAL = 45.0    # 후반 (10분+): 45초마다
        self.last_scout_time = 0.0

        # 정찰 유닛 상태
        # {tag: {"type": str, "target": Point2, "start_time": float}}
        self.active_scouts = {}

        # 정찰 목표 기록 (위치 -> 마지막 정찰 시간)
        self.last_scouted_at: Dict[Point2, float] = {}

        # 유닛별 최대 정찰 수 - ★ Phase 17: 정찰 유닛 수 증가 ★
        self.MAX_SCOUTS = {
            "WORKER": 1,      # 초반용
            "ZERGLING": 4,    # 주력 (3 -> 4)
            "OVERLORD": 3,    # 보조 (2 -> 3, 속업 후 더 적극적)
            "OVERSEER": 3     # 탐지/변신수 (2 -> 3)
        }

        # ★ Phase 17: 정찰 통계 ★
        self.scouts_sent = 0
        self.scouts_returned = 0
        self.scouts_lost = 0
        self.intel_updates = 0  # IntelManager로 전달한 정보 수

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
        """
        ★ Phase 17: 게임 시간대와 적 정보 신선도에 따른 동적 주기 계산 ★

        - 초반 (0-5분): 30초마다 (적 빌드 파악)
        - 중반 (5-10분): 1분마다 (확장 및 군대 조합 확인)
        - 후반 (10분+): 45초마다 (멀티 확장 및 테크 체크)
        - 긴급 상황: 15초마다 (정보가 1분 이상 오래됨)
        """
        game_time = self.bot.time

        # 긴급 모드: 적 정보가 1분 이상 오래됨
        blackboard = getattr(self.bot, "blackboard", None)
        if blackboard:
            last_seen = getattr(blackboard, "last_enemy_seen_time", 0)
            info_age = game_time - last_seen

            if info_age > 60.0:  # 1분 이상 정보 없음
                return self.EMERGENCY_INTERVAL

        # 게임 시간대별 주기
        if game_time < 300:  # 0-5분: 초반
            return self.EARLY_GAME_INTERVAL
        elif game_time < 600:  # 5-10분: 중반
            return self.MID_GAME_INTERVAL
        else:  # 10분+: 후반
            return self.LATE_GAME_INTERVAL

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
                self.scouts_lost += 1  # ★ Phase 17: 정찰 유닛 손실 추적 ★
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
                
            # ★ NEW: Path Safety Check - 경로상 위험 감지 시 우회 ★
            if self._is_path_unsafe(unit, info["target"]):
                safe_pos = self._find_safe_detour(unit, info["target"])
                if safe_pos:
                    unit.move(safe_pos)
                    continue

            # 목표 도달 (시야 범위 내)
            target = info["target"]
            sight = unit.sight_range

            if unit.distance_to(target) < sight * 0.8:
                self.last_scouted_at[target] = self.bot.time
                self.scouts_returned += 1
                to_remove.append(tag)

                # ★ Phase 17: IntelManager에 정찰 정보 전달 ★
                self._report_scouted_intel(unit, target)

                # 권한 해제
                if hasattr(self.bot, "unit_authority"):
                    self.bot.unit_authority.release_unit(tag, "AdvancedScoutingV2")

                # 정찰 완료 후 복귀 또는 순찰 등 추가 로직 가능
                
        for tag in to_remove:
            del self.active_scouts[tag]

    def _send_new_scout(self) -> bool:
        """★ Phase 17: 새로운 정찰 유닛 파견 (통계 추적) ★"""
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
            self.scouts_sent += 1  # ★ 통계 추적 ★

            # 로그
            game_time = self.bot.time
            self.logger.info(
                f"[{int(game_time)}s] Scout {scout_unit.type_id.name} sent to {target} (Total: {self.scouts_sent})"
            )
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
            
        # 3. ★ Race-Specific Strategic Scouting (Phase 17) ★
        # 적 종족에 따라 특정 테크 건물이 있을만한 곳(본진 구석 등) 정찰
        enemy_race = self.bot.enemy_race
        if enemy_race:
             # 적 본진 찾기
             if self.bot.enemy_start_locations:
                 enemy_main = self.bot.enemy_start_locations[0]
                 
                 # 테란/프로토스: 본진 구석구석 (테크 건물 숨기는 곳)
                 if enemy_race in {self.bot.Race.Terran, self.bot.Race.Protoss}:
                     # 본진 주변 4방향 (10~15 거리)
                     corners = [
                         enemy_main.offset((10, 10)),
                         enemy_main.offset((-10, 10)),
                         enemy_main.offset((10, -10)),
                         enemy_main.offset((-10, -10))
                     ]
                     # 아직 안 가본 구석 확인
                     for corner in corners:
                         if corner not in self.last_scouted_at:
                             return corner
         
        # 4. 맵 중앙/감시탑 (Low) - 룰렛 방식이나 상황에 따라 추가
        return self.bot.game_info.map_center

    def _is_path_unsafe(self, unit, target) -> bool:
        """이동 경로상에 known static defense가 있는지 확인"""
        if not hasattr(self.bot, "enemy_structures"):
            return False
            
        # 정적 방어 건물 (반경 7+2=9 내에는 접근 금지)
        static_defense = self.bot.enemy_structures.filter(
            lambda u: u.type_id in {
                UnitTypeId.PHOTONCANNON, UnitTypeId.MISSILETURRET, 
                UnitTypeId.SPORECRAWLER, UnitTypeId.BUNKER, UnitTypeId.PLANETARYFORTRESS
            }
        )
        
        if not static_defense:
            return False
            
        # 현재 위치에서 목표까지의 직선 경로에 방어 건물 반경이 겹치는지 체크 (단순화)
        # 3점 체크: 현재, 중간, 목표
        mid_point = (unit.position + target) / 2
        
        for defense in static_defense:
            # 방어 사거리 (7) + 여유 (2) = 9
            if unit.distance_to(defense) < 9 or \
               mid_point.distance_to(defense) < 9 or \
               target.distance_to(defense) < 9:
                return True
                
        return False

    def _find_safe_detour(self, unit, target) -> Optional[Point2]:
        """안전한 우회 경로 찾기 (단순화된 8방향 체크)"""
        # 현재 위치 기준 8방향으로 5거리 이동 지점 중 안전한 곳 선택
        angles = [45, 90, 135, 180, 225, 270, 315, 0]
        
        best_detour = None
        min_dist_to_target = 999
        
        for angle in angles:
            # 해당 방향으로 조금 이동한 지점
            rad = math.radians(angle)
            check_pos = unit.position.offset((5 * math.cos(rad), 5 * math.sin(rad)))
            
            # 맵 밖이면 패스
            if not self.bot.in_pathing_grid(check_pos):
                continue
                
            # 안전한지 체크 (재귀 호출 방지 위해 로직 복사)
            is_safe = True
            enemy_structures = getattr(self.bot, "enemy_structures", [])
            for structure in enemy_structures:
                if structure.type_id in {UnitTypeId.PHOTONCANNON, UnitTypeId.MISSILETURRET, UnitTypeId.SPORECRAWLER, UnitTypeId.BUNKER, UnitTypeId.PLANETARYFORTRESS}:
                     if check_pos.distance_to(structure) < 9:
                         is_safe = False
                         break
            
            if is_safe:
                dist = check_pos.distance_to(target)
                if dist < min_dist_to_target:
                    min_dist_to_target = dist
                    best_detour = check_pos
                    
        return best_detour

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

    def _report_scouted_intel(self, unit, target: Point2):
        """
        ★ Phase 17: IntelManager에 정찰 정보 전달 ★

        정찰 유닛이 목표 위치에 도착했을 때 발견한 정보를 IntelManager에 전달합니다:
        - 적 건물 발견
        - 적 유닛 구성
        - 확장 타이밍
        """
        intel_manager = getattr(self.bot, "intel", None)
        if not intel_manager:
            return

        try:
            # 정찰 위치 기록
            if hasattr(intel_manager, "record_scouted_location"):
                intel_manager.record_scouted_location(target)
                self.intel_updates += 1

            # 주변 적 건물 확인
            enemy_structures = getattr(self.bot, "enemy_structures", [])
            nearby_structures = [s for s in enemy_structures if s.distance_to(target) < 15]

            if nearby_structures:
                game_time = self.bot.time
                for structure in nearby_structures:
                    structure_type = getattr(structure.type_id, "name", "").upper()

                    # 확장 기지 발견
                    if structure_type in {"COMMANDCENTER", "NEXUS", "HATCHERY", "LAIR", "HIVE"}:
                        self.logger.info(
                            f"[{int(game_time)}s] ★ SCOUT INTEL: Enemy base found at {target} ({structure_type}) ★"
                        )

                    # 테크 건물 발견
                    tech_buildings = {
                        "FACTORY", "STARPORT", "ARMORY", "FUSIONCORE",
                        "ROBOTICSFACILITY", "STARGATE", "DARKSHRINE",
                        "TEMPLARARCHIVE", "FLEETBEACON", "TWILIGHTCOUNCIL",
                        "SPIRE", "GREATERSPIRE", "INFESTATIONPIT",
                        "BANELINGNEST", "ROACHWARREN", "HYDRALISKDEN"
                    }
                    if structure_type in tech_buildings:
                        self.logger.info(
                            f"[{int(game_time)}s] ★ SCOUT INTEL: Enemy tech discovered: {structure_type} ★"
                        )

            # Blackboard에 마지막 적 발견 시간 업데이트
            blackboard = getattr(self.bot, "blackboard", None)
            if blackboard and (nearby_structures or getattr(self.bot, "enemy_units", [])):
                blackboard.set("last_enemy_seen_time", self.bot.time)

        except Exception as e:
            self.logger.warning(f"Failed to report scouted intel: {e}")

    def _print_report(self):
        """★ Phase 17: 정찰 상태 리포트 (통계 추가) ★"""
        types = [info['type'] for info in self.active_scouts.values()]
        counts = {t: types.count(t) for t in set(types)}

        game_time = self.bot.time
        interval = self._get_dynamic_interval()

        # 정찰 성공률 계산
        total_scouts = self.scouts_sent
        success_rate = (self.scouts_returned / total_scouts * 100) if total_scouts > 0 else 0

        self.logger.info(f"=== Advanced Scouting V2 Report [{int(game_time)}s] ===")
        self.logger.info(f"Interval: {interval:.1f}s")
        self.logger.info(f"Active Scouts: {len(self.active_scouts)} {counts}")
        self.logger.info(f"Scouted Locations: {len(self.last_scouted_at)}/{len(self.bot.expansion_locations_list)}")
        self.logger.info(f"Scout Stats: Sent={self.scouts_sent}, Returned={self.scouts_returned}, Lost={self.scouts_lost} (Success: {success_rate:.1f}%)")
        self.logger.info(f"Intel Updates: {self.intel_updates}")
