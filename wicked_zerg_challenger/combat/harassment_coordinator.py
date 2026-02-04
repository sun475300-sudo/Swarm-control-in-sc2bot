"""
Harassment Coordinator - 견제 시스템 통합 관리

다방향 견제를 조율하여 적의 멀티태스킹을 강요합니다:
1. Zergling Run-by - 전투 중 일꾼 타겟 (Unit Authority 사용)
2. Mutalisk Worker Harassment - 미네랄 라인 타격, HP 30% 이하 퇴각
3. Roach/Ravager Poking - 담즙으로 주요 건물 공격, 본진 오기 전 퇴각
4. Drop Play - Overlord + 유닛으로 확장 타격

Features:
- Unit Authority Manager 연동으로 안전한 유닛 제어
- 본진 교전 중 자동 멀티프롱 어택
- HP 기반 자동 후퇴 시스템
- 위협 레벨 분석 및 안전 견제
- 우선순위 타겟팅 (일꾼 > 테크 건물 > 생산 건물)
"""

from typing import List, Dict, Optional, Set
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


class HarassmentCoordinator:
    """
    견제 시스템 통합 관리
    """

    def __init__(self, bot: BotAI):
        self.bot = bot
        self.logger = get_logger("Harassment")

        # ★ Zergling Run-by ★
        self.zergling_runby_active = False
        self.zergling_runby_tags: Set[int] = set()
        self.zergling_runby_cooldown = 0  # 쿨다운 (초)
        self.zergling_runby_interval = 120  # 2분마다

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

        # ★ Harassment Targets ★
        self.priority_targets: List[Point2] = []  # 우선순위 타겟 위치

        # ★ Performance Optimization: 캐싱 변수 ★
        self._has_closer_than = None  # hasattr 체크 캐시
        self._cached_army_fighting = False  # 전투 상태 캐시
        self._last_army_check_time = 0  # 마지막 전투 체크 시간

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

            # 6. Drop Play
            if iteration % 44 == 0:  # ~2초마다
                await self._manage_drop_play()

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
            
            # HP 너무 낮으면 권한 해제 (CombatManager가 가져가도록)
            if unit.health_percentage < 0.2:
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

        # ★ 전투 중인지 확인 ★
        is_combat = self._is_main_army_fighting()
        if not is_combat:
            return

        # ★ 저글링 확인 ★
        zerglings = self.bot.units(UnitTypeId.ZERGLING).filter(
            lambda u: u.tag not in self.zergling_runby_tags
        )
        if len(zerglings) < 12:  # 최소 12마리 (본대 유지 위해)
            return

        # ★ 6마리를 Run-by로 파견 ★
        runby_count = 6
        candidates = zerglings.sorted(lambda u: u.distance_to(self.bot.start_location))[:runby_count]

        # ★ 타겟: 적 미네랄 라인 ★
        target = self._find_enemy_mineral_line()
        if not target:
            return

        # ★ 권한 요청 및 실행 ★
        for ling in candidates:
            if self.bot.unit_authority.request_unit(
                ling.tag, 
                "Harassment_Runby", 
                AuthorityLevel.TACTICAL
            ):
                self.bot.do(ling.attack(target))
                self.zergling_runby_tags.add(ling.tag)

        if self.zergling_runby_tags:
            self.zergling_runby_active = True
            self.zergling_runby_cooldown = game_time + self.zergling_runby_interval

            self.logger.info(
                f"[{int(game_time)}s] ★ ZERGLING RUN-BY activated! ({len(self.zergling_runby_tags)} units) → {target} ★"
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
        """적 미네랄 라인 찾기"""
        if not hasattr(self.bot, "enemy_structures"):
            return None

        # 적 본진 또는 확장 기지
        enemy_bases = self.bot.enemy_structures.filter(
            lambda s: getattr(s.type_id, "name", "").upper() in {
                "COMMANDCENTER", "NEXUS", "HATCHERY", "LAIR", "HIVE",
                "PLANETARYFORTRESS", "ORBITALCOMMAND"
            }
        )

        if not enemy_bases:
            return None

        # 가장 먼 기지 선택 (빈집 털이 효과 증대)
        if not hasattr(self.bot, "start_location") or not self.bot.start_location:
            target_base = enemy_bases[0]
        else:
            # 적 본진에서 가장 먼 적 기지 (확장)
            if self.bot.enemy_start_locations:
                enemy_main = self.bot.enemy_start_locations[0]
                target_base = max(
                    enemy_bases,
                    key=lambda b: b.position.distance_to(enemy_main)
                )
            else:
                target_base = enemy_bases[0]

        # 미네랄 패치 근처 위치 반환
        if hasattr(self.bot, "mineral_field") and self.bot.mineral_field:
            minerals_near_base = self.bot.mineral_field.closer_than(10, target_base)
            if minerals_near_base:
                return minerals_near_base.center

        return target_base.position

    # ========================================
    # Mutalisk Harassment
    # ========================================

    async def _manage_mutalisk_harassment(self):
        """
        Mutalisk 견제 관리 (Unit Authority 적용)
        """
        if not hasattr(self.bot, "units") or not hasattr(self.bot, "unit_authority"):
            return

        mutalisks = self.bot.units(UnitTypeId.MUTALISK)
        if not mutalisks:
            return

        # 1. 기존 견제 유닛 관리
        active_mutas = []
        for tag in list(self.mutalisk_harass_tags):
            muta = self.bot.units.find_by_tag(tag)
            
            # 유닛 없음 or HP 낮음 -> 해제
            if not muta or muta.health_percentage <= self.mutalisk_retreat_hp_threshold:
                if muta:
                    # 안전한 곳으로 후퇴 명령 후 해제
                    safe_spot = self.bot.start_location
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

        # 2. 새로운 드랍 시작 조건
        if not self._is_main_army_fighting():
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

    def _find_drop_target(self) -> Optional[Point2]:
        """Drop 타겟 선택 (적 확장)"""
        if not hasattr(self.bot, "enemy_structures"):
            return None
        
        # 가장 먼 기지
        if hasattr(self.bot, "enemy_start_locations") and self.bot.enemy_start_locations:
            enemy_main = self.bot.enemy_start_locations[0]
            bases = self.bot.enemy_structures.filter(lambda s: s.type_id == UnitTypeId.HATCHERY or s.type_id == UnitTypeId.NEXUS or s.type_id == UnitTypeId.COMMANDCENTER)
            if bases:
                 # 본진에서 가장 먼 기지
                 return max(bases, key=lambda b: b.distance_to(enemy_main)).position
        
        return None

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
        }
