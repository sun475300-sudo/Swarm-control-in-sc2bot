
"""
Advanced Scouting System V2 - 고급 정찰 시스템 V2

Phase 10 기반, Phase 22 고도화:
1. 정찰 유닛 다양화 (일꾼, 저글링, 대군주, 감시군주+변신수)
2. 동적 정찰 주기 (기본 25초, 긴급 15초)
3. 지능형 목표 설정 (우선순위 기반)
4. Unit Authority Manager 연동
5. ★ Phase 22: 순찰 경로 시스템 (다중 웨이포인트) ★
6. ★ Phase 22: 젤나가 감시탑 확보 ★
7. ★ Phase 22: 드롭 경로 감시 ★
8. ★ Phase 22: 백과사전 연동 (상성 기반 정찰 우선순위) ★
9. ★ Phase 22: 변신수 분산 배치 ★
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

# 백과사전 임포트 (상성 데이터 활용)
try:
    from sc2_encyclopedia import get_counter, COUNTER_MATRIX
except ImportError:
    get_counter = None
    COUNTER_MATRIX = {}


class AdvancedScoutingSystemV2:
    def __init__(self, bot: BotAI):
        self.bot = bot
        self.logger = get_logger("AdvScoutV2")

        # Scouting timers
        self.last_scout_times = {
            "OVERLORD": 0.0,
            "ZERGLING": 0.0,
            "GENERAL": 0.0,
            "PATROL": 0.0,        # ★ Phase 22: 순찰 타이머
            "WATCHTOWER": 0.0,    # ★ Phase 22: 감시탑 타이머
            "DROP_WATCH": 0.0,    # ★ Phase 22: 드롭 감시 타이머
        }

        # 정찰 유닛 상태
        # {tag: {"type": str, "target": Point2, "start_time": float, "mode": str}}
        self.active_scouts = {}

        # 정찰 목표 기록 (위치 -> 마지막 정찰 시간)
        self.last_scouted_at: Dict[Point2, float] = {}

        # 유닛별 최대 정찰 수
        self.MAX_SCOUTS = {
            "WORKER": 1,
            "ZERGLING": 4,
            "OVERLORD": 3,
            "OVERSEER": 3
        }

        # ★ Phase 22: 순찰 경로 시스템 ★
        self._patrol_routes: Dict[str, List[Point2]] = {}  # route_name -> waypoints
        self._patrol_index: Dict[int, int] = {}  # unit_tag -> current waypoint index
        self._patrol_units: Set[int] = set()  # 순찰 임무 중인 유닛 태그

        # ★ Phase 22: 젤나가 감시탑 ★
        self._watchtower_positions: List[Point2] = []
        self._watchtower_claimers: Dict[Point2, int] = {}  # pos -> zergling tag

        # ★ Phase 22: 드롭 감시 포인트 ★
        self._drop_watch_positions: List[Point2] = []

        # ★ Phase 22: 우선 정찰 대상 (백과사전 기반) ★
        self._priority_scout_targets: List[str] = []  # 현재 찾아야 할 적 테크

        # 정찰 통계
        self.scouts_sent = 0
        self.scouts_returned = 0
        self.scouts_lost = 0
        self.intel_updates = 0

    async def on_step(self, iteration: int):
        # 0. 초기화 (한 번만)
        if not self._patrol_routes:
            self._initialize_routes()

        # 1. 활성 정찰 유닛 관리 (사망/임무완료 체크)
        self._manage_active_scouts()

        # 2. 정찰 주기 체크 (개별 타이머 통합 관리)
        current_time = self.bot.time

        # A. Overlord Scouting (Every 30s)
        if current_time - self.last_scout_times["OVERLORD"] >= 30.0:
            if self._send_specific_scout(UnitTypeId.OVERLORD):
                self.last_scout_times["OVERLORD"] = current_time

        # B. Zergling Scouting (Every 60s)
        if current_time - self.last_scout_times["ZERGLING"] >= 60.0:
            if self._send_specific_scout(UnitTypeId.ZERGLING):
                self.last_scout_times["ZERGLING"] = current_time

        # C. General Dynamic Scouting (Based on interval)
        interval = self._get_dynamic_interval()
        if current_time - self.last_scout_times["GENERAL"] >= interval:
            if self._send_new_scout():
                self.last_scout_times["GENERAL"] = current_time

        # 3. 감시군주 변신수 활용
        await self._manage_changelings()

        # ★ Phase 22: 순찰 경로 업데이트 (매 5초) ★
        if current_time - self.last_scout_times["PATROL"] >= 5.0:
            self._update_patrol_units()
            self.last_scout_times["PATROL"] = current_time

        # ★ Phase 22: 젤나가 감시탑 확보 (매 20초) ★
        if current_time - self.last_scout_times["WATCHTOWER"] >= 20.0:
            self._claim_watchtowers()
            self.last_scout_times["WATCHTOWER"] = current_time

        # ★ Phase 22: 드롭 경로 감시 (중반 이후, 매 30초) ★
        if current_time > 300 and current_time - self.last_scout_times["DROP_WATCH"] >= 30.0:
            self._monitor_drop_paths()
            self.last_scout_times["DROP_WATCH"] = current_time

        # ★ Phase 22: 백과사전 기반 우선 정찰 대상 갱신 (매 60초) ★
        if iteration % 1320 == 0:
            self._update_priority_targets()

        # 4. 메모리 누수 방지: 오래된 정찰 데이터 정리 (50초마다)
        if iteration % 1100 == 0:
            self._cleanup_old_scout_data()

        # 5. 리포트 (30초마다)
        if iteration % 660 == 0:
            self._print_report()

    def _get_dynamic_interval(self) -> float:
        """
        ★ Phase 21: 향상된 동적 정찰 간격 (더 빈번한 정찰) ★

        - 초반 (0-5분): 25초마다 (30초 → 25초) - 적 빌드 빠른 파악
        - 중반 (5-10분): 40초마다 (60초 → 40초) - 대폭 개선, 확장/군대 조합 확인
        - 후반 (10분+): 35초마다 (45초 → 35초) - 멀티 확장 및 테크 빠른 체크
        - 테크 타이밍 (4-7분): 20초마다 (NEW) - 중요 테크 전환 윈도우
        - 긴급 상황: 15초마다 (정보가 60초 이상 오래됨)

        Performance impact: Minimal (scouts run on separate frame budget)
        """
        game_time = self.bot.time

        # 긴급 모드: 적 정보가 60초 이상 오래됨
        if self._is_emergency_mode():
            return 15.0

        # 테크 타이밍 윈도우 (4-7분): 가장 중요한 테크 전환 시기
        if 240 < game_time < 420:  # 4분 ~ 7분
            return 20.0

        # 게임 시간대별 간격 (Phase 21 개선)
        if game_time < 300:  # 0-5분 (초반)
            return 25.0      # 30초 → 25초 (17% 향상)
        elif game_time < 600:  # 5-10분 (중반)
            return 40.0      # 60초 → 40초 (33% 향상)
        else:  # 10분+ (후반)
            return 35.0      # 45초 → 35초 (22% 향상)

    def _is_emergency_mode(self) -> bool:
        """
        긴급 모드 감지: 적 정보가 오래됨

        Returns:
            True if intel is stale (>60s old)
        """
        game_time = self.bot.time
        blackboard = getattr(self.bot, "blackboard", None)
        if blackboard:
            last_seen = getattr(blackboard, "last_enemy_seen_time", 0)
            info_age = game_time - last_seen
            if info_age > 60:  # 60초 이상 오래된 정보
                return True

        return False

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

            # 순찰/감시탑/드롭감시 모드 유닛은 별도 관리
            mode = info.get("mode", "scout")
            if mode in ("patrol", "watchtower", "drop_watch"):
                # 위협 시만 철수, 그 외에는 _update_patrol_units가 관리
                if self._scout_is_threatened(unit) and mode != "watchtower":
                    if hasattr(self.bot, "start_location"):
                        unit.move(self.bot.start_location)
                        to_remove.append(tag)
                continue

            # Scout Safety Check - 위협 감지 및 회피
            if self._scout_is_threatened(unit):
                if hasattr(self.bot, "start_location"):
                    retreat_pos = self.bot.start_location
                    unit.move(retreat_pos)
                    self.logger.info(f"[SCOUT_RETREAT] {unit.type_id.name} retreating from threat (HP: {unit.health_percentage*100:.0f}%)")
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
        """새로운 정찰 유닛 파견 + 중반 이후 순찰 트리거"""
        # ★ Phase 22: 중반 이후 순찰 경로 자동 활성화
        if self.bot.time > 300:
            self._trigger_midgame_patrols()
        return self._send_specific_scout()

    def _send_specific_scout(self, force_unit_type: Optional[UnitTypeId] = None) -> bool:
        """
        특정 유닛 타입을 강제하거나 일반적인 로직으로 정찰 유닛 파견
        """
        target = self._select_scout_target()
        if not target:
            return False

        # 유닛 선택 (강제 타입이 있으면 해당 타입만, 없으면 일반 로직)
        scout_unit = None
        if force_unit_type:
            available_units = self.bot.units(force_unit_type).filter(
                lambda u: u.tag not in self.active_scouts
            )
            if force_unit_type == UnitTypeId.OVERLORD:
                # 대군주 속업 체크 (속업 안 되어있으면 정찰 지양하지만 강제라면 수행)
                if available_units:
                    scout_unit = available_units.closest_to(target)
            elif force_unit_type == UnitTypeId.ZERGLING:
                if available_units:
                    scout_unit = available_units.closest_to(target)
        else:
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
            self.scouts_sent += 1

            # 로그
            game_time = self.bot.time
            self.logger.info(
                f"[{int(game_time)}s] Scout {scout_unit.type_id.name} sent to {target} (Total: {self.scouts_sent}, Forced: {force_unit_type is not None})"
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
            
        # 3. ★ Phase 22: 백과사전 기반 우선 정찰 (테크 건물 숨김 탐지) ★
        if self._priority_scout_targets and self.bot.enemy_start_locations:
            enemy_main = self.bot.enemy_start_locations[0]
            corners = [
                enemy_main.offset((10, 10)),
                enemy_main.offset((-10, 10)),
                enemy_main.offset((10, -10)),
                enemy_main.offset((-10, -10))
            ]
            for corner in corners:
                last_time = self.last_scouted_at.get(corner, 0)
                if self.bot.time - last_time > 45:
                    return corner

        # 4. Race-Specific Strategic Scouting
        enemy_race = self.bot.enemy_race
        if enemy_race:
             if self.bot.enemy_start_locations:
                 enemy_main = self.bot.enemy_start_locations[0]
                 if enemy_race in {self.bot.Race.Terran, self.bot.Race.Protoss}:
                     corners = [
                         enemy_main.offset((10, 10)),
                         enemy_main.offset((-10, 10)),
                         enemy_main.offset((10, -10)),
                         enemy_main.offset((-10, -10))
                     ]
                     for corner in corners:
                         if corner not in self.last_scouted_at:
                             return corner

        # 5. 맵 중앙/감시탑
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
        """
        ★ Phase 22: 변신수 분산 배치 ★
        모든 변신수를 적 본진으로 보내지 않고, 각각 다른 정찰 목표로 분산.
        """
        overseers = self.bot.units(UnitTypeId.OVERSEER)
        for overseer in overseers:
            if overseer.energy >= 50:
                self.bot.do(overseer(AbilityId.SPAWNCHANGELING_SPAWNCHANGELING))

        changelings = self.bot.units(UnitTypeId.CHANGELING) | \
                      self.bot.units(UnitTypeId.CHANGELINGZEALOT) | \
                      self.bot.units(UnitTypeId.CHANGELINGMARINESHIELD) | \
                      self.bot.units(UnitTypeId.CHANGELINGMARINE) | \
                      self.bot.units(UnitTypeId.CHANGELINGZERGLING) | \
                      self.bot.units(UnitTypeId.CHANGELINGZERGLINGWINGS)

        if not changelings:
            return

        # ★ Phase 22: 분산 정찰 대상 목록 구성 ★
        targets = []

        # 1순위: 적 확장 지역 (미정찰 우선)
        if self.bot.enemy_start_locations:
            enemy_base = self.bot.enemy_start_locations[0]
            enemy_exps = sorted(
                self.bot.expansion_locations_list,
                key=lambda p: p.distance_to(enemy_base)
            )
            for exp in enemy_exps[:5]:
                targets.append(exp)

        # 2순위: 맵 중앙
        if hasattr(self.bot, "game_info"):
            targets.append(self.bot.game_info.map_center)

        # 3순위: 우선 정찰 대상 위치 (백과사전 기반으로 테크 건물 있을 법한 곳)
        if self._priority_scout_targets and self.bot.enemy_start_locations:
            corners = [
                enemy_base.offset((12, 12)),
                enemy_base.offset((-12, 12)),
                enemy_base.offset((12, -12)),
                enemy_base.offset((-12, -12)),
            ]
            targets.extend(corners)

        if not targets:
            return

        # 각 변신수를 다른 목표로 분산 배치
        for i, changeling in enumerate(changelings):
            target = targets[i % len(targets)]
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
        """정찰 상태 리포트"""
        types = [info['type'] for info in self.active_scouts.values()]
        counts = {t: types.count(t) for t in set(types)}

        game_time = self.bot.time
        interval = self._get_dynamic_interval()

        total_scouts = self.scouts_sent
        success_rate = (self.scouts_returned / total_scouts * 100) if total_scouts > 0 else 0

        self.logger.info(f"=== Advanced Scouting V2 Report [{int(game_time)}s] ===")
        self.logger.info(f"Interval: {interval:.1f}s")
        self.logger.info(f"Active Scouts: {len(self.active_scouts)} {counts}")
        self.logger.info(f"Patrol Units: {len(self._patrol_units)}, Watchtowers: {len(self._watchtower_claimers)}")
        self.logger.info(f"Scouted Locations: {len(self.last_scouted_at)}/{len(self.bot.expansion_locations_list)}")
        self.logger.info(f"Stats: Sent={self.scouts_sent}, Ret={self.scouts_returned}, Lost={self.scouts_lost} ({success_rate:.1f}%)")
        if self._priority_scout_targets:
            self.logger.info(f"Priority Targets: {self._priority_scout_targets[:3]}")

    # ================================================================
    # ★ Phase 22: 순찰 경로 시스템 ★
    # ================================================================

    def _initialize_routes(self):
        """게임 시작 시 순찰 경로 및 감시 포인트 초기화"""
        if not self.bot.enemy_start_locations:
            return

        our_base = self.bot.start_location
        enemy_base = self.bot.enemy_start_locations[0]
        map_center = self.bot.game_info.map_center

        # 1. 적진 순환 순찰 경로 (적 확장 지역 순회)
        enemy_expansions = sorted(
            self.bot.expansion_locations_list,
            key=lambda p: p.distance_to(enemy_base)
        )
        # 적 본진 + 가까운 확장 3개를 순환
        enemy_patrol = [loc for loc in enemy_expansions[:4]]
        if enemy_patrol:
            self._patrol_routes["enemy_bases"] = enemy_patrol

        # 2. 맵 중앙 순찰 경로 (중앙 + 양쪽 길목)
        mid_route = [map_center]
        # 맵 중앙에서 양쪽으로 오프셋한 감시 지점
        dx = (enemy_base.x - our_base.x)
        dy = (enemy_base.y - our_base.y)
        length = max(math.sqrt(dx*dx + dy*dy), 1)
        perp_x, perp_y = -dy/length * 15, dx/length * 15
        mid_route.append(Point2((map_center.x + perp_x, map_center.y + perp_y)))
        mid_route.append(Point2((map_center.x - perp_x, map_center.y - perp_y)))
        self._patrol_routes["mid_map"] = mid_route

        # 3. 아군 방어 순찰 (우리 확장 외곽)
        our_expansions = sorted(
            self.bot.expansion_locations_list,
            key=lambda p: p.distance_to(our_base)
        )
        defense_patrol = []
        for exp in our_expansions[1:4]:  # 2~4번째 확장
            # 확장에서 맵 외곽 방향으로 약간 벗어난 감시 지점
            watch = exp.towards(map_center, -8)
            defense_patrol.append(watch)
        if defense_patrol:
            self._patrol_routes["defense"] = defense_patrol

        # 4. 젤나가 감시탑 위치 수집
        if hasattr(self.bot, "watchtowers"):
            self._watchtower_positions = [t.position for t in self.bot.watchtowers]
        # 감시탑이 없는 맵이면 주요 교차로를 감시탑 대용으로
        if not self._watchtower_positions:
            quarter_1 = Point2(((our_base.x + map_center.x) / 2, (our_base.y + map_center.y) / 2))
            quarter_3 = Point2(((enemy_base.x + map_center.x) / 2, (enemy_base.y + map_center.y) / 2))
            self._watchtower_positions = [quarter_1, quarter_3]

        # 5. 드롭 감시 포인트 (우리 본진 뒤편, 자원라인 접근로)
        # 본진에서 적 반대 방향 가장자리
        behind_x = our_base.x + (our_base.x - enemy_base.x) * 0.3
        behind_y = our_base.y + (our_base.y - enemy_base.y) * 0.3
        # 맵 경계 내로 클램프
        map_w = self.bot.game_info.map_size[0]
        map_h = self.bot.game_info.map_size[1]
        behind_x = max(5, min(map_w - 5, behind_x))
        behind_y = max(5, min(map_h - 5, behind_y))
        self._drop_watch_positions = [
            Point2((behind_x, behind_y)),
            Point2(((our_base.x + behind_x) / 2, (our_base.y + behind_y) / 2)),
        ]
        # 양쪽 측면도 추가
        self._drop_watch_positions.append(
            Point2((our_base.x + perp_x * 0.8, our_base.y + perp_y * 0.8))
        )
        self._drop_watch_positions.append(
            Point2((our_base.x - perp_x * 0.8, our_base.y - perp_y * 0.8))
        )

        self.logger.info(f"[INIT] Routes: enemy_bases={len(self._patrol_routes.get('enemy_bases', []))}, "
                         f"mid_map={len(self._patrol_routes.get('mid_map', []))}, "
                         f"defense={len(self._patrol_routes.get('defense', []))}")
        self.logger.info(f"[INIT] Watchtowers: {len(self._watchtower_positions)}, "
                         f"Drop watch: {len(self._drop_watch_positions)}")

    def _update_patrol_units(self):
        """
        순찰 중인 유닛의 다음 웨이포인트로 이동 명령.
        단일 목표 도착 시 다음 웨이포인트로 자동 전환.
        """
        to_remove = []
        for tag in list(self._patrol_units):
            unit = self.bot.units.find_by_tag(tag)
            if not unit:
                to_remove.append(tag)
                continue

            # 현재 웨이포인트 인덱스
            idx = self._patrol_index.get(tag, 0)

            # 이 유닛의 순찰 경로 찾기
            route = self._get_unit_patrol_route(tag)
            if not route:
                to_remove.append(tag)
                continue

            target = route[idx % len(route)]

            # 목표 근처 도달 시 다음 웨이포인트로
            if unit.distance_to(target) < 5:
                self.last_scouted_at[target] = self.bot.time
                idx = (idx + 1) % len(route)
                self._patrol_index[tag] = idx
                next_target = route[idx]
                unit.move(next_target)

            # 위협 감지 시 후퇴
            if self._scout_is_threatened(unit):
                if hasattr(self.bot, "start_location"):
                    unit.move(self.bot.start_location)
                    to_remove.append(tag)

        for tag in to_remove:
            self._patrol_units.discard(tag)
            self._patrol_index.pop(tag, None)
            # active_scouts에서도 제거
            self.active_scouts.pop(tag, None)
            if hasattr(self.bot, "unit_authority"):
                self.bot.unit_authority.release_unit(tag, "AdvancedScoutingV2")

    def _get_unit_patrol_route(self, tag: int) -> Optional[List[Point2]]:
        """유닛 태그에서 순찰 경로 찾기"""
        info = self.active_scouts.get(tag)
        if not info:
            return None
        route_name = info.get("patrol_route")
        if route_name:
            return self._patrol_routes.get(route_name)
        return None

    def _assign_patrol(self, route_name: str, unit_type: UnitTypeId = UnitTypeId.OVERLORD) -> bool:
        """
        특정 순찰 경로에 유닛 배정.
        중반 이후 오버로드/감시군주를 적진 순환 순찰에 투입.
        """
        route = self._patrol_routes.get(route_name)
        if not route:
            return False

        # 이미 이 경로에 배정된 유닛이 있으면 스킵
        for tag in self._patrol_units:
            info = self.active_scouts.get(tag)
            if info and info.get("patrol_route") == route_name:
                return False

        # 유닛 선택
        available = self.bot.units(unit_type).filter(
            lambda u: u.tag not in self.active_scouts and u.tag not in self._patrol_units
        )
        # 오버로드는 다른 시스템이 관리하지 않는 것만
        if unit_type == UnitTypeId.OVERLORD:
            available = available.idle

        if not available:
            return False

        scout = available.closest_to(route[0])
        if not self._request_authority(scout):
            return False

        scout.move(route[0])
        self.active_scouts[scout.tag] = {
            "type": scout.type_id.name,
            "target": route[0],
            "start_time": self.bot.time,
            "mode": "patrol",
            "patrol_route": route_name,
        }
        self._patrol_units.add(scout.tag)
        self._patrol_index[scout.tag] = 0
        self.scouts_sent += 1

        self.logger.info(f"[{int(self.bot.time)}s] ★ PATROL assigned: {scout.type_id.name} -> route '{route_name}' ({len(route)} waypoints)")
        return True

    # ================================================================
    # ★ Phase 22: 젤나가 감시탑 확보 ★
    # ================================================================

    def _claim_watchtowers(self):
        """저글링으로 젤나가 감시탑 점령 시도"""
        game_time = self.bot.time
        if game_time < 120:  # 2분 이전에는 스킵
            return

        # 사망한 감시탑 수비병 정리
        for pos in list(self._watchtower_claimers.keys()):
            tag = self._watchtower_claimers[pos]
            unit = self.bot.units.find_by_tag(tag)
            if not unit:
                del self._watchtower_claimers[pos]

        # 미점령 감시탑에 저글링 파견
        for tower_pos in self._watchtower_positions:
            if tower_pos in self._watchtower_claimers:
                continue

            # 이미 아군 유닛이 근처에 있으면 스킵
            nearby_units = self.bot.units.closer_than(3, tower_pos)
            if nearby_units:
                # 가장 가까운 유닛을 수비병으로 등록
                self._watchtower_claimers[tower_pos] = nearby_units.first.tag
                continue

            # 저글링 파견
            zerglings = self.bot.units(UnitTypeId.ZERGLING).filter(
                lambda u: u.tag not in self.active_scouts
                and u.tag not in self._patrol_units
                and not u.is_burrowed
            )
            if not zerglings:
                continue

            ling = zerglings.closest_to(tower_pos)
            # 너무 멀면 스킵 (전선에 있는 저글링 뺏지 않기)
            if ling.distance_to(tower_pos) > 50:
                continue

            if self._request_authority(ling):
                ling.move(tower_pos)
                self._watchtower_claimers[tower_pos] = ling.tag
                self.active_scouts[ling.tag] = {
                    "type": "ZERGLING",
                    "target": tower_pos,
                    "start_time": game_time,
                    "mode": "watchtower",
                }
                self.logger.info(f"[{int(game_time)}s] ★ WATCHTOWER claim: Zergling -> {tower_pos}")

    # ================================================================
    # ★ Phase 22: 드롭 경로 감시 ★
    # ================================================================

    def _monitor_drop_paths(self):
        """
        오버로드를 드롭 접근 경로에 배치하여 조기 경보.
        중반 이후(5분+) 테란/프로토스 상대로 활성화.
        """
        enemy_race = getattr(self.bot, "enemy_race", None)
        if not enemy_race:
            return

        # 테란(메디백 드롭), 프로토스(프리즘 드롭)일 때만
        is_drop_race = False
        try:
            if enemy_race in {self.bot.Race.Terran, self.bot.Race.Protoss}:
                is_drop_race = True
        except (AttributeError, TypeError):
            pass

        if not is_drop_race:
            return

        # 드롭 감시에 오버로드 최대 2기 배정
        assigned_count = sum(
            1 for info in self.active_scouts.values()
            if info.get("mode") == "drop_watch"
        )
        if assigned_count >= 2:
            return

        for watch_pos in self._drop_watch_positions:
            # 이미 감시 중이면 스킵
            already_watched = any(
                info.get("mode") == "drop_watch" and info["target"].distance_to(watch_pos) < 10
                for info in self.active_scouts.values()
            )
            if already_watched:
                continue

            overlords = self.bot.units(UnitTypeId.OVERLORD).idle.filter(
                lambda u: u.tag not in self.active_scouts and u.tag not in self._patrol_units
            )
            if not overlords:
                break

            ol = overlords.closest_to(watch_pos)
            if self._request_authority(ol):
                ol.move(watch_pos)
                self.active_scouts[ol.tag] = {
                    "type": "OVERLORD",
                    "target": watch_pos,
                    "start_time": self.bot.time,
                    "mode": "drop_watch",
                }
                self.logger.info(f"[{int(self.bot.time)}s] ★ DROP WATCH: Overlord -> {watch_pos}")
                assigned_count += 1
                if assigned_count >= 2:
                    break

    # ================================================================
    # ★ Phase 22: 백과사전 연동 - 상성 기반 정찰 우선순위 ★
    # ================================================================

    def _update_priority_targets(self):
        """
        IntelManager의 적 조합 정보 + 백과사전 데이터를 조합하여
        현재 가장 찾아야 할 적 테크/유닛을 결정.
        """
        if not get_counter:
            return

        intel = getattr(self.bot, "intel", None)
        if not intel:
            return

        enemy_comp = getattr(intel, "enemy_unit_counts", {})
        enemy_tech = getattr(intel, "enemy_tech_buildings", set())

        self._priority_scout_targets = []

        # 현재 발견된 적 유닛 기반으로 "아직 안 보인 위험 유닛" 추론
        # 예: FACTORY 보였지만 SIEGETANK 안 보임 → 탱크 숨기고 있을 수 있음
        tech_unit_map = {
            "FACTORY": ["SIEGETANK", "HELLION", "CYCLONE", "THOR"],
            "STARPORT": ["MEDIVAC", "LIBERATOR", "BATTLECRUISER", "BANSHEE", "VIKINGFIGHTER"],
            "ROBOTICSFACILITY": ["IMMORTAL", "COLOSSUS", "DISRUPTOR", "OBSERVER"],
            "STARGATE": ["ORACLE", "VOIDRAY", "CARRIER", "TEMPEST", "PHOENIX"],
            "DARKSHRINE": ["DARKTEMPLAR"],
            "TEMPLARARCHIVE": ["HIGHTEMPLAR", "ARCHON"],
            "SPIRE": ["MUTALISK", "CORRUPTOR"],
            "GREATERSPIRE": ["BROODLORD"],
        }

        for tech_building in enemy_tech:
            possible_units = tech_unit_map.get(tech_building, [])
            for unit_name in possible_units:
                if unit_name not in enemy_comp or enemy_comp.get(unit_name, 0) == 0:
                    # 테크는 있지만 유닛이 안 보임 → 우선 정찰 대상
                    counter_info = get_counter(unit_name)
                    if counter_info and counter_info.get("priority", "") == "high":
                        self._priority_scout_targets.append(unit_name)

        if self._priority_scout_targets:
            self.logger.info(f"[{int(self.bot.time)}s] Priority scout targets: {self._priority_scout_targets[:5]}")

    # ================================================================
    # ★ Phase 22: 중후반 자동 순찰 트리거 ★
    # ================================================================

    def _trigger_midgame_patrols(self):
        """
        중반(5분+) 이후 자동으로 순찰 경로 활성화.
        on_step에서 호출하지 않고 _send_specific_scout 등에서 조건부 호출.
        """
        game_time = self.bot.time

        # 5분 이후: 적진 순환 순찰 (오버로드 속업 시)
        if game_time > 300:
            has_speed = UpgradeId.OVERLORDSPEED in self.bot.state.upgrades
            if has_speed:
                self._assign_patrol("enemy_bases", UnitTypeId.OVERLORD)

        # 8분 이후: 맵 중앙 순찰 (감시군주)
        if game_time > 480:
            overseers = self.bot.units(UnitTypeId.OVERSEER)
            if overseers.amount >= 2:
                self._assign_patrol("mid_map", UnitTypeId.OVERSEER)

        # 10분 이후: 아군 방어 순찰 (저글링)
        if game_time > 600:
            self._assign_patrol("defense", UnitTypeId.ZERGLING)

    def get_scout_report(self) -> dict:
        """외부 시스템용 정찰 상태 리포트"""
        ling_count = sum(1 for i in self.active_scouts.values() if i["type"] == "ZERGLING")
        ol_count = sum(1 for i in self.active_scouts.values() if i["type"] == "OVERLORD")
        os_count = sum(1 for i in self.active_scouts.values() if i["type"] == "OVERSEER")
        patrol_count = len(self._patrol_units)
        watchtower_count = len(self._watchtower_claimers)

        return {
            "zergling_patrol_count": ling_count,
            "overlord_scout_count": ol_count,
            "overseer_scout_count": os_count,
            "patrol_units": patrol_count,
            "watchtowers_held": watchtower_count,
            "total_active": len(self.active_scouts),
            "scouts_sent": self.scouts_sent,
            "scouts_lost": self.scouts_lost,
            "priority_targets": self._priority_scout_targets[:3],
        }
