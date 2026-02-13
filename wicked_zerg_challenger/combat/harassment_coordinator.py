"""
Harassment Coordinator - 견제 시스템 통합 관리

★ Phase 21: Aggressive Mode System & Baneling Drops ★

다방향 견제를 조율하여 적의 멀티태스킹을 강요합니다:
1. Zergling Run-by - 전투 중 일꾼 타겟 (Unit Authority 사용)
2. Mutalisk Worker Harassment - 미네랄 라인 타격, HP 30% 이하 퇴각
3. Roach/Ravager Poking - 담즙으로 주요 건물 공격, 본진 오기 전 퇴각
4. Drop Play - Overlord + 유닛으로 확장 타격
5. ★ NEW: Baneling Drops - 맹독충 드랍으로 일꾼 라인 타격 ★
6. ★ NEW: Multi-angle Coordination - 2+ 방향 동시 공격 ★

Features:
- ★ Aggressive Mode System: 게임 상황에 따른 견제 강도 조절
- Unit Authority Manager 연동으로 안전한 유닛 제어
- 본진 교전 중 자동 멀티프롱 어택
- HP 기반 자동 후퇴 시스템
- 위협 레벨 분석 및 안전 견제
- 우선순위 타겟팅 (일꾼 > 테크 건물 > 생산 건물)
"""

from typing import List, Dict, Optional, Set
from enum import Enum
from utils.logger import get_logger

try:
    from sc2.bot_ai import BotAI
    from sc2.ids.unit_typeid import UnitTypeId
    from sc2.ids.ability_id import AbilityId
    from sc2.ids.upgrade_id import UpgradeId
    from sc2.position import Point2
    from sc2.unit import Unit
    from sc2.units import Units
except ImportError:
    # Fallback for tooling
    BotAI = object
    UnitTypeId = object
    AbilityId = object
    UpgradeId = object
    Point2 = tuple
    Unit = object
    Units = list

try:
    from unit_authority_manager import UnitAuthorityManager, AuthorityLevel
except ImportError:
    UnitAuthorityManager = None
    AuthorityLevel = None


class AggressiveMode(Enum):
    """
    ★ Phase 21: Harassment Aggressive Mode System ★

    견제 강도 레벨:
    - PASSIVE: 5% 병력 할당, 방어적 견제
    - OPPORTUNISTIC: 10% 병력 할당, 기회주의적 견제 (기본)
    - AGGRESSIVE: 15% 병력 할당, 공격적 견제 (우세 시)
    - ULTRA_AGGRESSIVE: 25% 병력 할당, 초공격적 견제 (초반 1-4분)
    """
    PASSIVE = "passive"
    OPPORTUNISTIC = "opportunistic"
    AGGRESSIVE = "aggressive"
    ULTRA_AGGRESSIVE = "ultra_aggressive"


class HarassmentCoordinator:
    """
    견제 시스템 통합 관리
    """

    def __init__(self, bot: BotAI):
        self.bot = bot
        self.logger = get_logger("Harassment")

        # ★ Zergling Run-by - Phase 17: 더 공격적인 견제 ★
        self.zergling_runby_active = False
        self.zergling_runby_tags: Set[int] = set()
        self.zergling_runby_cooldown = 0  # 쿨다운 (초)
        self.zergling_runby_interval = 60  # ★ Phase 17: 2분 → 1분으로 단축 (더 빈번한 견제) ★

        # ★ Mutalisk Harassment ★
        self.mutalisk_harass_active = False
        self.mutalisk_harass_tags: Set[int] = set()
        self.mutalisk_harass_target: Optional[Point2] = None
        self.mutalisk_retreat_hp_threshold = 0.35  # 30% -> 35% 상향 (생존력 강화)

        # ★ Roach/Ravager Poking ★
        self.roach_poke_active = False
        self.roach_poke_tags: Set[int] = set()
        self.ravager_bile_ready = True

        # ★ Drop Play ★
        self.drop_play_active = False
        self.drop_overlord_tag: Optional[int] = None
        self.drop_unit_tags: Set[int] = set()
        self.drop_target: Optional[Point2] = None

        # ★ Phase 21: Aggressive Mode System ★
        self.aggressive_mode = AggressiveMode.OPPORTUNISTIC
        self.harassment_allocation_percent = 0.10  # 기본: 10% 병력 할당

        # ★ Phase 21: Baneling Drop System ★
        self.baneling_drop_active = False
        self.baneling_drop_overlord_tag: Optional[int] = None
        self.baneling_drop_baneling_tags: Set[int] = set()
        self.baneling_drop_target: Optional[Point2] = None
        self.baneling_drop_cooldown = 0  # 쿨다운 (초)
        self.baneling_drop_interval = 120  # 2분 쿨다운

        # ★ Phase 21.3: Unit Persistence System (Squad Lock) ★
        self.locked_units: Set[int] = set()  # 견제에 할당된 유닛 태그
        self.squad_assignments: Dict[int, str] = {}  # {unit_tag: squad_name}
        self.squad_members: Dict[str, Set[int]] = {
            "zergling_runby": set(),
            "mutalisk_harass": set(),
            "baneling_drop": set(),
            "roach_poke": set()
        }
        self.squad_lock_duration: Dict[str, float] = {}  # {squad_name: lock_until_time}
        self.default_lock_duration = 30.0  # 30초 동안 유닛 고정

        # ★ Harassment Targets ★
        self.priority_targets: List[Point2] = []  # 우선순위 타겟 위치

        # ★ Performance Optimization: 캐싱 변수 ★
        self._has_closer_than = None  # hasattr 체크 캐시
        self._cached_army_fighting = False  # 전투 상태 캐시
        self._last_army_check_time = 0  # 마지막 전투 체크 시간

        # ★ Synchronized Strikes - Phase 17 ★
        self.sync_strike_active = False
        self.sync_strike_cooldown = 0
        self.sync_strike_interval = 120  # 2분마다 합동 타격 시도
        self.sync_strike_setup_time = 0

        # ★ Nydus Harassment - Phase 17 ★
        self.nydus_active = False
        self.nydus_network_tag: Optional[int] = None
        self.nydus_worm_tag: Optional[int] = None
        self.nydus_target: Optional[Point2] = None
        self.nydus_squad_tags: Set[int] = set()
        self.nydus_cooldown = 0

        # ★ Phase 22: 일꾼 처치 추적 & 스마트 견제 ★
        self.workers_killed = 0
        self.raids_executed = 0
        self.last_worker_kill_count = 0  # 시작 시점 적 일꾼 수 스냅샷
        self._aggro_mode_last_update = 0  # 마지막 공격모드 자동 갱신 시간
        self._mineral_line_defense_cache: Dict[Point2, int] = {}  # 미네랄라인별 방어력 캐시
        self._defense_cache_time = 0

    async def on_step(self, iteration: int):
        """매 프레임 실행"""
        try:
            current_time = self.bot.time

            # 1. Update harassment targets
            if iteration % 110 == 0:  # ~5초마다
                self._update_harassment_targets()

            # 2. Zergling Run-by (전투 중 자동 발동)
            if iteration % 44 == 0:  # ~2초마다
                await self._manage_zergling_runby()

            # 3. Mutalisk Harassment
            if iteration % 22 == 0:  # ~1초마다
                await self._manage_mutalisk_harassment()

            # 4. Roach/Ravager Poking
            if iteration % 33 == 0:  # ~1.5초마다
                await self._manage_roach_poking()

            # 5. 메모리 누수 방지 & 권한 체크 정리 (50초마다)
            if iteration % 1100 == 0:
                self._cleanup_dead_unit_tags()

            # 5.1. ★ Phase 21.3: Unit Persistence Cleanup ★
            if iteration % 22 == 0:  # 매 1초마다
                self.cleanup_dead_units()
                self.cleanup_expired_locks()

            # 6. Drop Play
            if iteration % 44 == 0:  # ~2초마다
                await self._manage_drop_play()

            # 7. ★ Synchronized Strikes (Phase 17) ★
            if iteration % 22 == 0:
                await self._manage_synchronized_strikes()

            # 8. ★ Nydus Harassment (Phase 17) ★
            if iteration % 33 == 0:
                await self._manage_nydus_harassment()

            # 9. ★ Phase 22: 자동 공격모드 조정 (30초마다) ★
            if iteration % 660 == 0:
                self._auto_adjust_aggressive_mode()

            # 10. ★ Phase 22: 일꾼 처치 추적 (5초마다) ★
            if iteration % 110 == 0:
                self._track_worker_kills()

        except Exception as e:
            if iteration % 200 == 0:
                self.logger.error(f"[HARASSMENT] Error: {e}")

    # ========================================
    # Harassment Target Selection
    # ========================================

    def _update_harassment_targets(self):
        """견제 타겟 업데이트"""
        if not hasattr(self.bot, "enemy_structures"):
            return

        self.priority_targets = []

        # ★ 1. Enemy Expansions (highest priority) ★
        enemy_bases = self.bot.enemy_structures.filter(
            lambda s: getattr(s.type_id, "name", "").upper() in {
                "COMMANDCENTER", "NEXUS", "HATCHERY", "LAIR", "HIVE",
                "PLANETARYFORTRESS", "ORBITALCOMMAND"
            }
        )

        for base in enemy_bases:
            self.priority_targets.append(base.position)

        # ★ 2. Tech Buildings ★
        tech_buildings = self.bot.enemy_structures.filter(
            lambda s: getattr(s.type_id, "name", "").upper() in {
                "FACTORY", "STARPORT", "ROBOTICSFACILITY", "STARGATE",
                "TWILIGHTCOUNCIL", "SPIRE", "HYDRALISKDEN", "TEMPLARARCHIVE", 
                "DARKSHRINE", "FLEETBEACON", "GHOSTACADEMY", "FUSIONCORE"
            }
        )

        for building in tech_buildings:
            self.priority_targets.append(building.position)

    def _find_harassment_target(self) -> Optional[Point2]:
        """견제 타겟 찾기"""
        if self.priority_targets:
            # 적 본진과 가장 먼 곳(확장) 우선? 아니면 가장 가까운 곳?
            # 견제는 보통 '빈집'이므로 적 주력과 먼 곳이 좋음.
            # 하지만 단순화를 위해 시작 위치와 가까운 곳(가장 가까운 적 기지) 선택
            if hasattr(self.bot, "start_location"):
                return min(
                    self.priority_targets,
                    key=lambda pos: pos.distance_to(self.bot.start_location)
                )

        # Fallback: 적 본진
        if hasattr(self.bot, "enemy_start_locations") and self.bot.enemy_start_locations:
            return self.bot.enemy_start_locations[0]

        return None

    # ========================================
    # Zergling Run-by
    # ========================================

    async def _manage_zergling_runby(self):
        """
        Zergling Run-by 관리 (Unit Authority 적용)
        """
        if not hasattr(self.bot, "unit_authority"):
            return # Authority Manager 필수

        game_time = getattr(self.bot, "time", 0)

        # 1. 활성 런바이 유닛 관리
        active_lings = []
        for tag in list(self.zergling_runby_tags):
            unit = self.bot.units.find_by_tag(tag)
            if not unit:
                self.zergling_runby_tags.discard(tag)
                continue
            
            # HP 너무 낮으면 안전 후퇴 후 권한 해제
            if unit.health_percentage < 0.2:
                retreat = self._find_safe_retreat_point(unit.position)
                self.bot.do(unit.move(retreat))
                self.bot.unit_authority.release_unit(tag, "Harassment_Runby")
                self.zergling_runby_tags.discard(tag)
                continue
                
            active_lings.append(unit)

        # 런바이 진행 중이면 유지
        if active_lings:
            target = self._find_enemy_mineral_line()
            if target:
                for ling in active_lings:
                    self.bot.do(ling.attack(target))
            return

        # 2. 새로운 런바이 시작 조건 체크
        if game_time < self.zergling_runby_cooldown:
            return

        # ★ Phase 17: 전투 중이 아니어도 주기적으로 견제 (4분 이후) ★
        is_combat = self._is_main_army_fighting()
        is_mid_game = game_time > 240  # 4분 이후

        # 전투 중이거나, 중반 이후에는 전투 없이도 견제
        if not is_combat and not is_mid_game:
            return

        # ★ 저글링 확인 ★
        zerglings = self.bot.units(UnitTypeId.ZERGLING).filter(
            lambda u: u.tag not in self.zergling_runby_tags
        )
        if len(zerglings) < 12:  # 최소 12마리 (본대 유지 위해)
            return

        # ★ Phase 22: 멀티 베이스 동시 타격 ★
        targets = self._find_multi_mineral_lines(count=2)
        if not targets:
            target = self._find_enemy_mineral_line()
            if target:
                targets = [target]
            else:
                return

        # 분대 크기 결정 (공격모드에 따라)
        total_runby = min(
            int(len(zerglings) * self.harassment_allocation_percent * 2),
            12  # 최대 12마리
        )
        total_runby = max(total_runby, 6)  # 최소 6마리
        per_squad = total_runby // len(targets)

        candidates = zerglings.sorted(lambda u: u.distance_to(self.bot.start_location))

        # ★ Phase 22: 각 타겟에 분대 배정 ★
        assigned_count = 0
        for i, target in enumerate(targets):
            squad_candidates = candidates[i * per_squad:(i + 1) * per_squad]
            for ling in squad_candidates:
                if self.bot.unit_authority.request_unit(
                    ling.tag,
                    "Harassment_Runby",
                    AuthorityLevel.TACTICAL
                ):
                    self.bot.do(ling.attack(target))
                    self.zergling_runby_tags.add(ling.tag)
                    assigned_count += 1

        if self.zergling_runby_tags:
            self.zergling_runby_active = True
            self.zergling_runby_cooldown = game_time + self.zergling_runby_interval
            self.raids_executed += 1

            self.logger.info(
                f"[{int(game_time)}s] ★ ZERGLING RUN-BY activated! ({assigned_count} units) → {len(targets)} targets ★"
            )

    def _is_main_army_fighting(self) -> bool:
        """
        본진 군대가 전투 중인지 확인
        """
        if not hasattr(self.bot, "units") or not hasattr(self.bot, "enemy_units"):
            return False

        # ★ 캐싱: 2초 이내면 이전 결과 재사용 ★
        current_time = self.bot.time
        if current_time - self._last_army_check_time < 2.0:
            return self._cached_army_fighting

        # ★ hasattr 캐싱 (한 번만 체크) ★
        if self._has_closer_than is None:
            self._has_closer_than = hasattr(self.bot.enemy_units, "closer_than")

        # 아군 전투 유닛이 적 근처에 있는지 확인
        army_units = self.bot.units.filter(
            lambda u: u.type_id in {UnitTypeId.ZERGLING, UnitTypeId.ROACH, UnitTypeId.HYDRALISK}
        )

        if not army_units:
            self._cached_army_fighting = False
            self._last_army_check_time = current_time
            return False

        # 적 유닛과 15거리 이내에 전투 유닛이 있으면 전투 중
        for unit in army_units[:10]:  # 샘플링
            if self._has_closer_than:
                nearby_enemies = self.bot.enemy_units.closer_than(15, unit)
            else:
                nearby_enemies = [e for e in self.bot.enemy_units if e.distance_to(unit) < 15]

            if nearby_enemies:
                self._cached_army_fighting = True
                self._last_army_check_time = current_time
                return True

        self._cached_army_fighting = False
        self._last_army_check_time = current_time
        return False

    def _find_enemy_mineral_line(self) -> Optional[Point2]:
        """
        ★ Phase 22: 스마트 미네랄라인 타겟팅 ★
        가장 방어가 약한(전투 유닛이 적은) 적 미네랄라인을 선택.
        """
        if not hasattr(self.bot, "enemy_structures"):
            return None

        enemy_bases = self.bot.enemy_structures.filter(
            lambda s: getattr(s.type_id, "name", "").upper() in {
                "COMMANDCENTER", "NEXUS", "HATCHERY", "LAIR", "HIVE",
                "PLANETARYFORTRESS", "ORBITALCOMMAND"
            }
        )

        if not enemy_bases:
            return None

        # ★ Phase 22: 방어력 평가 캐시 업데이트 (2초마다) ★
        current_time = self.bot.time
        if current_time - self._defense_cache_time > 2.0:
            self._mineral_line_defense_cache = {}
            for base in enemy_bases:
                defense = self._assess_threat_at_position(base.position)
                self._mineral_line_defense_cache[base.position] = defense
            self._defense_cache_time = current_time

        # 방어가 가장 약한 기지 선택 (동점이면 아군 본진에서 가까운 쪽)
        best_base = None
        min_defense = 999
        for base in enemy_bases:
            defense = self._mineral_line_defense_cache.get(base.position, 0)
            # 행성요새는 직접 공격 불가 → 페널티
            if getattr(base.type_id, "name", "").upper() == "PLANETARYFORTRESS":
                defense += 20
            if defense < min_defense:
                min_defense = defense
                best_base = base
            elif defense == min_defense and best_base:
                # 동점: 아군 본진에 가까운 쪽 (이동시간 단축)
                if hasattr(self.bot, "start_location"):
                    if base.distance_to(self.bot.start_location) < best_base.distance_to(self.bot.start_location):
                        best_base = base

        if not best_base:
            best_base = enemy_bases[0]

        # 미네랄 패치 근처 위치 반환
        if hasattr(self.bot, "mineral_field") and self.bot.mineral_field:
            minerals_near_base = self.bot.mineral_field.closer_than(10, best_base)
            if minerals_near_base:
                return minerals_near_base.center

        return best_base.position

    def _find_multi_mineral_lines(self, count: int = 2) -> List[Point2]:
        """
        ★ Phase 22: 멀티 베이스 동시 타격용 - 여러 미네랄라인 반환 ★
        방어가 가장 약한 순서대로 최대 count개 반환.
        """
        if not hasattr(self.bot, "enemy_structures"):
            return []

        enemy_bases = self.bot.enemy_structures.filter(
            lambda s: getattr(s.type_id, "name", "").upper() in {
                "COMMANDCENTER", "NEXUS", "HATCHERY", "LAIR", "HIVE",
                "PLANETARYFORTRESS", "ORBITALCOMMAND"
            }
        )

        if not enemy_bases:
            return []

        # 방어력 기준 정렬
        scored = []
        for base in enemy_bases:
            defense = self._mineral_line_defense_cache.get(base.position, 0)
            if getattr(base.type_id, "name", "").upper() == "PLANETARYFORTRESS":
                defense += 20
            scored.append((base, defense))

        scored.sort(key=lambda x: x[1])

        targets = []
        for base, _ in scored[:count]:
            if hasattr(self.bot, "mineral_field") and self.bot.mineral_field:
                minerals = self.bot.mineral_field.closer_than(10, base)
                if minerals:
                    targets.append(minerals.center)
                    continue
            targets.append(base.position)

        return targets

    # ========================================
    # Mutalisk Harassment
    # ========================================

    async def _manage_mutalisk_harassment(self):
        """
        ★ Phase 17: Mutalisk 견제 관리 (더 공격적) ★

        - 뮤탈리스크가 3마리 이상이면 즉시 견제 시작
        - HP 회복된 유닛은 즉시 재투입
        - 일꾼 집중 타격
        """
        if not hasattr(self.bot, "units") or not hasattr(self.bot, "unit_authority"):
            return

        mutalisks = self.bot.units(UnitTypeId.MUTALISK)
        if not mutalisks or len(mutalisks) < 3:  # ★ Phase 17: 최소 3마리면 견제 시작 ★
            return

        # 1. 기존 견제 유닛 관리
        active_mutas = []
        for tag in list(self.mutalisk_harass_tags):
            muta = self.bot.units.find_by_tag(tag)
            
            # 유닛 없음 or HP 낮음 -> 해제
            if not muta or muta.health_percentage <= self.mutalisk_retreat_hp_threshold:
                if muta:
                    # ★ Phase 22: 가장 가까운 안전 지점으로 후퇴 ★
                    safe_spot = self._find_safe_retreat_point(muta.position)
                    self.bot.do(muta.move(safe_spot))
                    self.bot.unit_authority.release_unit(tag, "Harassment_Muta")
                self.mutalisk_harass_tags.discard(tag)
                continue
            
            active_mutas.append(muta)

        # 2. 신규 견제 유닛 모집
        candidates = mutalisks.filter(
            lambda m: m.tag not in self.mutalisk_harass_tags and 
                      m.health_percentage > 0.8  # 건강한 뮤탈만
        )

        for muta in candidates:
            # 권한 요청
            if self.bot.unit_authority.request_unit(
                muta.tag,
                "Harassment_Muta",
                AuthorityLevel.TACTICAL
            ):
                self.mutalisk_harass_tags.add(muta.tag)
                active_mutas.append(muta)

        if not active_mutas:
            return

        # ★ 타겟 설정 ★
        if not self.mutalisk_harass_target:
            self.mutalisk_harass_target = self._find_enemy_mineral_line()

        if not self.mutalisk_harass_target:
            return

        # ★ 견제 실행 ★
        for muta in active_mutas:
            # 위협 체크
            if self._assess_threat_at_position(muta.position) > 5: # 너무 위험하면
                 self.bot.do(muta.move(self.bot.start_location)) # 일시 후퇴
                 continue

            # 일꾼 우선 타겟
            workers = self._find_enemy_workers_near(self.mutalisk_harass_target)
            if workers:
                target_worker = min(workers, key=lambda w: w.distance_to(muta))
                self.bot.do(muta.attack(target_worker))
            else:
                self.bot.do(muta.move(self.mutalisk_harass_target))

    def _find_enemy_workers_near(self, position: Point2) -> List:
        """특정 위치 근처의 적 일꾼 찾기"""
        if not hasattr(self.bot, "enemy_units"):
            return []

        workers = self.bot.enemy_units.filter(
            lambda u: getattr(u.type_id, "name", "") in ["SCV", "PROBE", "DRONE"]
        )

        if hasattr(workers, "closer_than"):
            return workers.closer_than(15, position)
        else:
            return [w for w in workers if w.position.distance_to(position) < 15]

    # ========================================
    # Roach/Ravager Poking
    # ========================================

    async def _manage_roach_poking(self):
        """
        Roach/Ravager 포킹 (Unit Authority 적용)
        """
        if not hasattr(self.bot, "unit_authority"):
            return

        roaches = self.bot.units(UnitTypeId.ROACH)
        ravagers = self.bot.units(UnitTypeId.RAVAGER)
        poke_units = roaches | ravagers
        
        # 1. 기존 유닛 관리
        active_pokes = []
        for tag in list(self.roach_poke_tags):
            unit = self.bot.units.find_by_tag(tag)
            if not unit:
                self.roach_poke_tags.discard(tag)
                continue
            
            # HP 낮으면 해제
            if unit.health_percentage < 0.4:
                self.bot.unit_authority.release_unit(tag, "Harassment_Poke")
                self.roach_poke_tags.discard(tag)
                continue
                
            active_pokes.append(unit)
            
        # 2. 신규 모집 (쿨다운 혹은 조건 필요)
        if len(active_pokes) < 5 and len(poke_units) > 10:
             # 임의 모집 (개선 필요: 전술적 판단)
             candidates = poke_units.filter(lambda u: u.tag not in self.roach_poke_tags)
             for unit in candidates[:5]:
                 if self.bot.unit_authority.request_unit(
                     unit.tag, "Harassment_Poke", AuthorityLevel.TACTICAL
                 ):
                     self.roach_poke_tags.add(unit.tag)
                     active_pokes.append(unit)

        if not active_pokes:
            return

        # ★ 포킹 타겟 찾기 ★
        target = self._find_harassment_target()
        if not target:
            return

        # ★ 위협 레벨 체크 ★
        threat_level = self._assess_threat_at_position(target)

        # ★ 포킹 실행 ★
        for unit in active_pokes:
            # 안전 거리 유지하며 건물 공격
            distance = unit.distance_to(target)
            
            if threat_level > 10: # 위협이 너무 크면 후퇴
                self.bot.do(unit.move(self.bot.start_location))
                continue
                
            buildings = self._find_buildings_near(target)
            if buildings:
                self.bot.do(unit.attack(buildings[0]))
            else:
                self.bot.do(unit.attack(target))

            # ★ Ravager 담즙 ★
            if unit.type_id == UnitTypeId.RAVAGER and unit.energy >= 25:
                # 건물이나 밀집지역에 담즙
                if buildings:
                     self.bot.do(unit(AbilityId.EFFECT_CORROSIVEBILE, buildings[0].position))

    def _assess_threat_at_position(self, position: Point2) -> int:
        """특정 위치의 위협 레벨 평가"""
        if not hasattr(self.bot, "enemy_units"):
            return 0

        # 근처 적 전투 유닛 수
        if hasattr(self.bot.enemy_units, "closer_than"):
            nearby_enemies = self.bot.enemy_units.closer_than(20, position)
        else:
            nearby_enemies = [e for e in self.bot.enemy_units if e.position.distance_to(position) < 20]

        # 전투 유닛만 카운트
        combat_units = [
            e for e in nearby_enemies
            if hasattr(e, "can_attack") and e.can_attack
        ]

        return len(combat_units)

    def _cleanup_dead_unit_tags(self):
        """메모리 누수 방지"""
        # (기존 로직과 유사하지만 authority release 추가 필요)
        all_tags = self.zergling_runby_tags | self.mutalisk_harass_tags | self.roach_poke_tags | self.drop_unit_tags
        
        dead_tags = []
        if hasattr(self.bot, "units"):
             for tag in all_tags:
                 if not self.bot.units.find_by_tag(tag):
                     dead_tags.append(tag)
        
        for tag in dead_tags:
            self.zergling_runby_tags.discard(tag)
            self.mutalisk_harass_tags.discard(tag)
            self.roach_poke_tags.discard(tag)
            self.drop_unit_tags.discard(tag)
            # 죽었으므로 authority release는 불필요하지만 manager 내부 정리됨

    def _find_buildings_near(self, position: Point2) -> List:
        """특정 위치 근처의 적 건물 찾기"""
        if not hasattr(self.bot, "enemy_structures"):
            return []

        if hasattr(self.bot.enemy_structures, "closer_than"):
            return list(self.bot.enemy_structures.closer_than(15, position))
        else:
            return [b for b in self.bot.enemy_structures if b.position.distance_to(position) < 15]

    # ========================================
    # Drop Play
    # ========================================

    async def _manage_drop_play(self):
        """
        Drop Play 관리 (Unit Authority 적용)
        """
        if not hasattr(self.bot, "unit_authority"):
            return

        # 1. 진행 중인 드랍 관리
        if self.drop_play_active:
             # 오버로드 확인
             overlord = self.bot.units.find_by_tag(self.drop_overlord_tag)
             if not overlord:
                 self.drop_play_active = False # 오버로드 사망
                 return
             
             # 목적지 도달 시 하차
             if self.drop_target and overlord.distance_to(self.drop_target) < 4:
                 self.bot.do(overlord(AbilityId.UNLOADALLAT, self.drop_target))
                 self.drop_play_active = False
                 # 권한 해제 (유닛들은 이제 자유롭게 싸움)
                 self.bot.unit_authority.release_unit(self.drop_overlord_tag, "Harassment_Drop")
                 for tag in self.drop_unit_tags:
                     self.bot.unit_authority.release_unit(tag, "Harassment_Drop")
                 self.drop_unit_tags.clear()
                 self.drop_overlord_tag = None
             else:
                 # 이동 계속
                 if self.drop_target:
                    self.bot.do(overlord.move(self.drop_target))
             return

        # 2. ★ Phase 17: 새로운 드랍 시작 조건 (더 공격적) ★
        # 전투 중이 아니어도 드랍 가능 (중반 이후)
        game_time = getattr(self.bot, "time", 0)
        is_combat = self._is_main_army_fighting()
        is_mid_game = game_time > 300  # 5분 이후

        if not is_combat and not is_mid_game:
            return

        if UpgradeId.OVERLORDTRANSPORT not in self.bot.state.upgrades:
            return

        # 오버로드 확보
        overlords = self.bot.units(UnitTypeId.OVERLORD).filter(
            lambda o: o.is_idle and not o.has_cargo
        )
        if not overlords:
            return
            
        drop_overlord = overlords.first

        # 유닛 확보 (저글링)
        candidates = self.bot.units(UnitTypeId.ZERGLING).filter(
            lambda u: u.tag not in self.zergling_runby_tags
        )
        if len(candidates) < 8:
            return
            
        drop_units = candidates[:8]
        
        # 권한 요청
        if not self.bot.unit_authority.request_unit(drop_overlord.tag, "Harassment_Drop", AuthorityLevel.TACTICAL):
            return
            
        approved_units = []
        for unit in drop_units:
            if self.bot.unit_authority.request_unit(unit.tag, "Harassment_Drop", AuthorityLevel.TACTICAL):
                approved_units.append(unit)
                
        if len(approved_units) < 4:
            # 실패 시 모두 반환
            self.bot.unit_authority.release_unit(drop_overlord.tag, "Harassment_Drop")
            for u in approved_units:
                self.bot.unit_authority.release_unit(u.tag, "Harassment_Drop")
            return

        # 드랍 시작
        self.drop_overlord_tag = drop_overlord.tag
        self.drop_unit_tags = {u.tag for u in approved_units}
        self.drop_target = self._find_drop_target()
        
        # 로딩 명령
        for unit in approved_units:
            self.bot.do(drop_overlord(AbilityId.LOAD, unit))
            
        self.drop_play_active = True
        self.logger.info(f"[Harassment] Drop Play Started Target: {self.drop_target}")

        return None

    # ========================================
    # Synchronized Strikes (Phase 17)
    # ========================================

    async def _manage_synchronized_strikes(self):
        """
        합동 견제 코디네이터
        
        서로 다른 견제 수단(Run-by, Drop, Nydus)을 동시에 트리거하여
        적의 멀티태스킹 붕괴를 유도합니다.
        """
        current_time = self.bot.time

        # 1. 쿨다운 체크
        if current_time < self.sync_strike_cooldown:
            return

        # 2. 발동 조건 (인구수 충족 시)
        if self.bot.supply_used < 100:
            return

        # 3. 준비 단계 (모든 견제 수단 준비 확인)
        # 이미 개별적으로 로직들이 돌고 있지만, 여기서 강제로 여러 개를 동시에 활성화시킴
        
        # Run-by 가능?
        runby_ready = not self.zergling_runby_active and len(self.bot.units(UnitTypeId.ZERGLING)) >= 12
        
        # Drop 가능?
        drop_ready = not self.drop_play_active and \
                     UpgradeId.OVERLORDTRANSPORT in self.bot.state.upgrades and \
                     self.bot.units(UnitTypeId.OVERLORD).exists

        # 동시 실행 가능한 조합이 있을 때만 발동
        if runby_ready and drop_ready:
            self.logger.info(f"[{int(current_time)}s] ★ SYNCHRONIZED STRIKE ACTIVATED! (Run-by + Drop) ★")
            
            # 강제로 쿨다운 무시하고 실행 요청
            self.zergling_runby_cooldown = 0
            await self._manage_zergling_runby()
            await self._manage_drop_play()
            
            self.sync_strike_active = True
            self.sync_strike_cooldown = current_time + self.sync_strike_interval

    # ========================================
    # Nydus Harassment (Phase 17)
    # ========================================

    async def _manage_nydus_harassment(self):
        """
        땅굴망 견제 시스템
        """
        current_time = self.bot.time
        
        # 1. 쿨다운 및 조건 체크
        if current_time < self.nydus_cooldown:
            return

        # 땅굴망 건물 확인
        nydus_network = self.bot.structures(UnitTypeId.NYDUSNETWORK).ready
        if not nydus_network:
            return
        network = nydus_network.first
        self.nydus_network_tag = network.tag

        # 2. 진행 중인 땅굴망 관리
        if self.nydus_active:
            # 웜 확인
            worm = self.bot.structures(UnitTypeId.NYDUSCANAL).ready
            if not worm:
                # 웜이 파괴되었거나 아직 건설 중
                return
            self.nydus_worm_tag = worm.first.tag
            
            # 병력 내리기
            if network.cargo_used > 0:
                self.bot.do(network(AbilityId.UNLOADALL_NYDUSNETWORK))
            elif worm.first.cargo_used > 0:
                self.bot.do(worm.first(AbilityId.UNLOADALL_NYDUSWORM))
                
            return

        # 3. 새로운 땅굴망 공격 시작
        if self.bot.supply_used < 120: # 충분한 병력 있을 때
            return

        # 타겟 설정
        target = self._find_drop_target() # 드랍 타겟 로직 재사용
        if not target:
            return

        # 시야가 밝혀져 있어야 땅굴 소환 가능
        # 해당 위치에 감시군주나 오버로드가 있거나, 크립이 있어야 함 (NydusCanal 요구사항은 시야)
        # 하지만 봇 API에서는 AbilityId.BUILD_NYDUSWORM 사용
        
        # 권한 요청 및 병력 로딩 로직은 복잡하므로
        # 여기서는 단순하게 "가능하면 적 기지 근처에 뚫는다"로 구현
        
        # 땅굴 뚫기 (사거리 제한 없음, 시야 必)
        # 시야 확인을 위해 정찰 유닛이나 오버로드 주변 체크
        # 시야가 있는 적 기지 근처 위치 찾기
        valid_target = None
        for unit in self.bot.units:
            if unit.distance_to(target) < 15:
                valid_target = unit.position
                break
                
        if valid_target:
             if self.bot.can_afford(UnitTypeId.NYDUSCANAL):
                 # 건설 명령
                 try:
                     self.bot.do(network(AbilityId.BUILD_NYDUSWORM, valid_target))
                     self.logger.info(f"[{int(current_time)}s] ★ NYDUS WORM SUMMONED at {valid_target} ★")
                     self.nydus_active = True
                     self.nydus_cooldown = current_time + 60
                 except AttributeError as e:
                     self.logger.error(f"[HarassmentCoordinator] Nydus worm build failed (AttributeError): {e}")
                 except Exception as e:
                     self.logger.error(f"[HarassmentCoordinator] Unexpected error in nydus worm placement: {e}")

    def _find_drop_target(self) -> Optional[Point2]:
        """Drop 타겟 선택 (적 확장)"""
        if not hasattr(self.bot, "enemy_structures"):
            return None

        # 가장 먼 기지
        if hasattr(self.bot, "enemy_start_locations") and self.bot.enemy_start_locations:
            enemy_main = self.bot.enemy_start_locations[0]
            bases = self.bot.enemy_structures.filter(
                lambda s: s.type_id == UnitTypeId.HATCHERY or
                          s.type_id == UnitTypeId.NEXUS or
                          s.type_id == UnitTypeId.COMMANDCENTER
            )
            if bases:
                # 본진에서 가장 먼 기지
                return max(bases, key=lambda b: b.distance_to(enemy_main)).position

        # Fallback: 적 본진
        if hasattr(self.bot, "enemy_start_locations") and self.bot.enemy_start_locations:
            return self.bot.enemy_start_locations[0]

        return None

    # ============================================================================
    # Phase 21: Aggressive Mode System & Baneling Drops
    # ============================================================================

    def set_aggressive_mode(self, mode: AggressiveMode) -> None:
        """
        ★ Phase 21: 견제 강도 설정 ★

        Args:
            mode: AggressiveMode enum value
        """
        self.aggressive_mode = mode

        # 할당 비율 조정
        if mode == AggressiveMode.PASSIVE:
            self.harassment_allocation_percent = 0.05
        elif mode == AggressiveMode.OPPORTUNISTIC:
            self.harassment_allocation_percent = 0.10
        elif mode == AggressiveMode.AGGRESSIVE:
            self.harassment_allocation_percent = 0.15
        elif mode == AggressiveMode.ULTRA_AGGRESSIVE:
            self.harassment_allocation_percent = 0.25

        self.logger.info(
            f"[HARASSMENT MODE] {mode.value.upper()} "
            f"({self.harassment_allocation_percent:.0%} allocation)"
        )

    async def execute_baneling_drop(self, iteration: int) -> bool:
        """
        ★ Phase 21: Baneling Drop 실행 ★

        맹독충 4기를 대군주에 태워 적 미네랄 라인에 드랍

        Args:
            iteration: Current game iteration

        Returns:
            True if drop was initiated
        """
        current_time = self.bot.time

        # 쿨다운 체크
        if current_time < self.baneling_drop_cooldown:
            return False

        # 이미 활성 드랍 있으면 스킵
        if self.baneling_drop_active:
            return False

        # 1. Transport Overlord 확보
        overlord = self._get_transport_overlord()
        if not overlord:
            return False

        # 2. Banelings 확보 (최소 4기)
        banelings = self._get_drop_banelings(min_count=4)
        if len(banelings) < 4:
            return False

        # 3. 타겟 선택 (적 미네랄 라인)
        target = self._select_drop_target()
        if not target:
            return False

        # 4. Load banelings
        for baneling in banelings:
            self.bot.do(overlord(AbilityId.LOAD, baneling))
            self.baneling_drop_baneling_tags.add(baneling.tag)

        # 5. Fly to target
        overlord.move(target)

        # 6. Track drop
        self.baneling_drop_active = True
        self.baneling_drop_overlord_tag = overlord.tag
        self.baneling_drop_target = target
        self.baneling_drop_cooldown = current_time + self.baneling_drop_interval

        self.logger.info(
            f"[{int(current_time)}s] ★★ BANELING DROP LAUNCHED ★★ "
            f"{len(banelings)} banelings → {target}"
        )

        return True

    async def manage_active_baneling_drop(self) -> None:
        """
        활성 맹독 드랍 관리 (언로드 및 후퇴)
        """
        if not self.baneling_drop_active:
            return

        # Overlord 확인
        overlord = self.bot.units.find_by_tag(self.baneling_drop_overlord_tag)
        if not overlord:
            self._cancel_baneling_drop()
            return

        # 타겟 근처 도착 시 언로드
        if overlord.distance_to(self.baneling_drop_target) < 3:
            self.bot.do(overlord(AbilityId.UNLOADALLAT, self.baneling_drop_target))

            # Overlord 후퇴
            safe_pos = self.bot.start_location
            overlord.move(safe_pos)

            self.logger.info(
                f"[{int(self.bot.time)}s] Baneling drop: UNLOADING at target"
            )

            # 드랍 종료
            self._cancel_baneling_drop()

    def _get_transport_overlord(self) -> Optional[Unit]:
        """
        운송용 대군주 확보 (Ventral Sacs 업그레이드 필요)

        Returns:
            Available transport overlord, or None
        """
        # Ventral Sacs 업그레이드 체크
        if UpgradeId.OVERLORDSPEED not in self.bot.state.upgrades:
            return None

        # 사용 가능한 대군주 찾기
        overlords = self.bot.units(UnitTypeId.OVERLORD).filter(
            lambda o: o.is_idle and o.cargo_used == 0
        )

        if overlords:
            return overlords.first

        return None

    def _get_drop_banelings(self, min_count: int = 4) -> List[Unit]:
        """
        드랍용 맹독충 확보

        Args:
            min_count: 최소 맹독충 수

        Returns:
            List of available banelings
        """
        banelings = self.bot.units(UnitTypeId.BANELING).filter(
            lambda b: b.is_idle
        )

        if len(banelings) >= min_count:
            return banelings[:min_count]

        return []

    def _select_drop_target(self) -> Optional[Point2]:
        """
        드랍 타겟 선택 (적 미네랄 라인 우선)

        Returns:
            Target position, or None
        """
        # 적 확장 찾기
        if not hasattr(self.bot, "enemy_structures"):
            return None

        # 적 기지 (TownHall 타입)
        townhalls = self.bot.enemy_structures.filter(
            lambda s: s.type_id in {
                UnitTypeId.COMMANDCENTER, UnitTypeId.NEXUS, UnitTypeId.HATCHERY,
                UnitTypeId.ORBITALCOMMAND, UnitTypeId.PLANETARYFORTRESS,
                UnitTypeId.LAIR, UnitTypeId.HIVE
            }
        )

        if not townhalls:
            return None

        # 본진에서 가장 먼 기지 (확장) 우선
        if hasattr(self.bot, "enemy_start_locations") and self.bot.enemy_start_locations:
            enemy_main = self.bot.enemy_start_locations[0]
            furthest_base = max(townhalls, key=lambda b: b.distance_to(enemy_main))
            return furthest_base.position

        return townhalls.first.position

    def _cancel_baneling_drop(self) -> None:
        """맹독 드랍 취소 및 정리"""
        self.baneling_drop_active = False
        self.baneling_drop_overlord_tag = None
        self.baneling_drop_baneling_tags.clear()
        self.baneling_drop_target = None

    async def coordinate_multi_angle_attack(self, iteration: int) -> None:
        """
        ★ Phase 21: 다각도 동시 공격 조율 ★

        2개 이상의 견제를 동시에 실행하여 상대 멀티태스킹 강요

        Args:
            iteration: Current game iteration
        """
        attack_vectors = []

        # Vector 1: Zergling run-by
        if self._can_execute_zergling_runby():
            attack_vectors.append("zergling_runby")
            await self._trigger_zergling_runby()

        # Vector 2: Mutalisk harassment
        if self._can_execute_mutalisk_harass():
            attack_vectors.append("mutalisk_harass")
            await self._trigger_mutalisk_harassment()

        # Vector 3: Baneling drop
        if self._can_execute_baneling_drop():
            success = await self.execute_baneling_drop(iteration)
            if success:
                attack_vectors.append("baneling_drop")

        # Log multi-angle attack
        if len(attack_vectors) >= 2:
            self.logger.info(
                f"[{int(self.bot.time)}s] ★★ MULTI-ANGLE ATTACK ★★ "
                f"{' + '.join(attack_vectors)}"
            )

    def _can_execute_zergling_runby(self) -> bool:
        """Check if zergling run-by can be executed"""
        zerglings = self.bot.units(UnitTypeId.ZERGLING)
        return len(zerglings) >= 8 and self.zergling_runby_cooldown <= 0

    def _can_execute_mutalisk_harass(self) -> bool:
        """Check if mutalisk harassment can be executed"""
        mutalisks = self.bot.units(UnitTypeId.MUTALISK)
        return len(mutalisks) >= 5 and not self.mutalisk_harass_active

    def _can_execute_baneling_drop(self) -> bool:
        """Check if baneling drop can be executed"""
        banelings = self.bot.units(UnitTypeId.BANELING)
        overlords = self.bot.units(UnitTypeId.OVERLORD)
        has_upgrade = UpgradeId.OVERLORDSPEED in self.bot.state.upgrades

        return (
            len(banelings) >= 4 and
            len(overlords) >= 1 and
            has_upgrade and
            not self.baneling_drop_active and
            self.bot.time >= self.baneling_drop_cooldown
        )

    async def _trigger_zergling_runby(self) -> None:
        """Trigger zergling run-by (placeholder for existing logic)"""
        # This would call existing zergling run-by logic
        pass

    async def _trigger_mutalisk_harassment(self) -> None:
        """Trigger mutalisk harassment (placeholder for existing logic)"""
        # This would call existing mutalisk harassment logic
        pass

    # ============================================================================
    # Phase 21.3: Unit Persistence System (Squad Lock)
    # ============================================================================

    def lock_unit_to_squad(self, unit_tag: int, squad_name: str, duration: Optional[float] = None) -> None:
        """
        ★ Phase 21.3: 유닛을 스쿼드에 고정 ★

        유닛이 다른 시스템(메인 어택 등)에 의해 재할당되지 않도록 락 걸기

        Args:
            unit_tag: Unit tag to lock
            squad_name: Squad identifier (e.g., "zergling_runby")
            duration: Lock duration in seconds (None = default 30s)
        """
        self.locked_units.add(unit_tag)
        self.squad_assignments[unit_tag] = squad_name

        if squad_name not in self.squad_members:
            self.squad_members[squad_name] = set()

        self.squad_members[squad_name].add(unit_tag)

        # Set squad lock expiration
        lock_time = duration if duration else self.default_lock_duration
        self.squad_lock_duration[squad_name] = self.bot.time + lock_time

    def unlock_unit(self, unit_tag: int) -> None:
        """
        유닛 락 해제

        Args:
            unit_tag: Unit tag to unlock
        """
        if unit_tag in self.locked_units:
            self.locked_units.discard(unit_tag)

        if unit_tag in self.squad_assignments:
            squad_name = self.squad_assignments[unit_tag]

            # Remove from squad
            if squad_name in self.squad_members:
                self.squad_members[squad_name].discard(unit_tag)

            del self.squad_assignments[unit_tag]

    def is_unit_locked(self, unit_tag: int) -> bool:
        """
        유닛이 락되어 있는지 확인

        Args:
            unit_tag: Unit tag to check

        Returns:
            True if unit is locked to harassment
        """
        return unit_tag in self.locked_units

    def get_locked_units_by_squad(self, squad_name: str) -> Set[int]:
        """
        특정 스쿼드에 락된 유닛 태그 반환

        Args:
            squad_name: Squad identifier

        Returns:
            Set of unit tags in the squad
        """
        return set(self.squad_members.get(squad_name, set()))

    def _auto_unlock_expired_squads(self) -> None:
        """만료된 스쿼드 자동 언락 (cleanup_expired_locks 호출)"""
        self.cleanup_expired_locks()

    def get_unit_squad(self, unit_tag: int) -> Optional[str]:
        """
        유닛이 속한 스쿼드 반환

        Args:
            unit_tag: Unit tag

        Returns:
            Squad name or None
        """
        return self.squad_assignments.get(unit_tag)

    def cleanup_dead_units(self) -> None:
        """
        죽은 유닛 정리 (매 프레임 호출)
        """
        alive_tags = {unit.tag for unit in self.bot.units}

        # Remove dead units from locks
        dead_units = self.locked_units - alive_tags

        for unit_tag in dead_units:
            self.unlock_unit(unit_tag)

    def cleanup_expired_locks(self) -> None:
        """
        만료된 락 정리
        """
        current_time = self.bot.time

        expired_squads = []
        for squad_name, expire_time in self.squad_lock_duration.items():
            if current_time >= expire_time:
                expired_squads.append(squad_name)

        for squad_name in expired_squads:
            # Unlock all units in squad
            if squad_name in self.squad_members:
                for unit_tag in list(self.squad_members[squad_name]):
                    self.unlock_unit(unit_tag)

            # Remove expiration
            del self.squad_lock_duration[squad_name]

            self.logger.info(
                f"[HARASSMENT] Squad '{squad_name}' lock expired and released"
            )

    def get_available_units_for_harassment(self, unit_type: "UnitTypeId") -> "Units":
        """
        견제에 사용 가능한 유닛 반환 (락되지 않은 유닛만)

        Args:
            unit_type: Unit type to get

        Returns:
            Available units (not locked by other systems)
        """
        all_units = self.bot.units(unit_type)

        # Filter out locked units
        available = all_units.filter(
            lambda u: u.tag not in self.locked_units
        )

        return available

    def renew_squad_lock(self, squad_name: str, additional_duration: Optional[float] = None) -> None:
        """
        스쿼드 락 갱신 (임무 연장)

        Args:
            squad_name: Squad to renew
            additional_duration: Additional time (None = default 30s)
        """
        duration = additional_duration if additional_duration else self.default_lock_duration

        if squad_name in self.squad_lock_duration:
            # Extend existing lock
            self.squad_lock_duration[squad_name] = max(
                self.squad_lock_duration[squad_name],
                self.bot.time + duration
            )
        else:
            # Create new lock
            self.squad_lock_duration[squad_name] = self.bot.time + duration

    def get_squad_status(self) -> Dict[str, Dict]:
        """
        모든 스쿼드 상태 반환

        Returns:
            Dictionary of squad info
        """
        status = {}

        for squad_name, members in self.squad_members.items():
            if members:
                expire_time = self.squad_lock_duration.get(squad_name, 0)
                time_left = max(0, expire_time - self.bot.time)

                status[squad_name] = {
                    "members": len(members),
                    "time_left": time_left,
                    "active": time_left > 0
                }

        return status

    def get_harassment_status(self) -> Dict:
        """견제 상태 반환"""
        return {
            "zergling_runby_active": self.zergling_runby_active,
            "zergling_runby_count": len(self.zergling_runby_tags),
            "mutalisk_harass_active": self.mutalisk_harass_active,
            "mutalisk_harass_count": len(self.mutalisk_harass_tags),
            "roach_poke_active": self.roach_poke_active,
            "drop_play_active": self.drop_play_active,
            "priority_targets": len(self.priority_targets),
            "workers_killed": self.workers_killed,
            "raids_executed": self.raids_executed,
            "aggressive_mode": self.aggressive_mode.value,
        }

    # ================================================================
    # ★ Phase 22: 자동 공격모드 조정 ★
    # ================================================================

    def _auto_adjust_aggressive_mode(self):
        """
        게임 상황에 따라 견제 강도 자동 조정:
        - 경제 우세 → AGGRESSIVE (적극적 견제로 격차 벌리기)
        - 군대 우세 → AGGRESSIVE (여유 병력으로 견제)
        - 초반 러시 → ULTRA_AGGRESSIVE
        - 방어 필요 → PASSIVE
        """
        game_time = self.bot.time
        intel = getattr(self.bot, "intel", None)

        # 초반 (1-4분): 초공격적
        if 60 < game_time < 240:
            self.set_aggressive_mode(AggressiveMode.ULTRA_AGGRESSIVE)
            return

        if not intel:
            return

        # 위협 체크: 공격받고 있으면 수비 우선
        if intel.is_under_attack() and intel.get_threat_level() in ("heavy", "critical"):
            self.set_aggressive_mode(AggressiveMode.PASSIVE)
            return

        # 경제/군사 우위 판단
        our_workers = self.bot.workers.amount if hasattr(self.bot, "workers") else 0
        enemy_workers = getattr(intel, "enemy_worker_count", 0)
        our_supply = getattr(self.bot, "supply_army", 0)
        enemy_supply = getattr(intel, "enemy_army_supply", 0)

        economic_advantage = our_workers > enemy_workers + 10
        military_advantage = our_supply > enemy_supply * 1.3

        if economic_advantage and military_advantage:
            self.set_aggressive_mode(AggressiveMode.AGGRESSIVE)
        elif economic_advantage or military_advantage:
            self.set_aggressive_mode(AggressiveMode.OPPORTUNISTIC)
        else:
            self.set_aggressive_mode(AggressiveMode.OPPORTUNISTIC)

    # ================================================================
    # ★ Phase 22: 일꾼 처치 추적 ★
    # ================================================================

    def _track_worker_kills(self):
        """
        적 일꾼 수 변화를 추적하여 견제 효과 측정.
        (정확한 킬 카운트는 불가능하므로, 적 일꾼 수 감소량으로 추정)
        """
        intel = getattr(self.bot, "intel", None)
        if not intel:
            return

        current_enemy_workers = getattr(intel, "enemy_worker_count", 0)

        # 첫 측정
        if self.last_worker_kill_count == 0 and current_enemy_workers > 0:
            self.last_worker_kill_count = current_enemy_workers
            return

        # 적 일꾼이 감소했으면 (우리 견제 or 자연 감소)
        if current_enemy_workers < self.last_worker_kill_count:
            killed = self.last_worker_kill_count - current_enemy_workers
            # 견제가 활성화된 상태에서만 카운트 (자연 감소 제외)
            if self.zergling_runby_active or self.mutalisk_harass_active or self.drop_play_active:
                self.workers_killed += killed
                if killed >= 3:
                    self.logger.info(
                        f"[{int(self.bot.time)}s] ★ HARASSMENT EFFECTIVE: ~{killed} workers eliminated! (Total: {self.workers_killed}) ★"
                    )

        self.last_worker_kill_count = current_enemy_workers

    # ================================================================
    # ★ Phase 22: 안전 후퇴 지점 ★
    # ================================================================

    def _find_safe_retreat_point(self, unit_position: Point2) -> Point2:
        """
        본진 대신 가장 가까운 아군 확장 기지로 후퇴.
        확장이 없으면 본진으로.
        """
        if not hasattr(self.bot, "townhalls") or not self.bot.townhalls:
            return self.bot.start_location

        # 가장 가까운 아군 기지
        closest_base = self.bot.townhalls.closest_to(unit_position)
        return closest_base.position
