"""
Harassment Coordinator - 견제 시스템 통합 관리

다방향 견제를 조율하여 적의 멀티태스킹을 강요합니다:
1. Zergling Run-by - 전투 중 일꾼 타겟
2. Mutalisk Worker Harassment - 미네랄 라인 타격, HP 30% 이하 퇴각
3. Roach/Ravager Poking - 담즙으로 주요 건물 공격, 본진 오기 전 퇴각
4. Drop Play - Overlord + 유닛으로 확장 타격

Features:
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
    from sc2.position import Point2
    from sc2.unit import Unit
    from sc2.units import Units
except ImportError:
    class BotAI:
        pass
    class UnitTypeId:
        ZERGLING = "ZERGLING"
        MUTALISK = "MUTALISK"
        ROACH = "ROACH"
        RAVAGER = "RAVAGER"
        OVERLORD = "OVERLORD"
        DRONE = "DRONE"
        SCV = "SCV"
        PROBE = "PROBE"
    class AbilityId:
        EFFECT_CORROSIVEBILE = "EFFECT_CORROSIVEBILE"
        LOAD = "LOAD"
    Point2 = tuple
    Unit = None
    Units = list


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
        self.mutalisk_retreat_hp_threshold = 0.3  # 30% HP 이하 퇴각

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

            # 5. 메모리 누수 방지: 죽은 유닛 tag 정리 (50초마다)
            if iteration % 1100 == 0:
                self._cleanup_dead_unit_tags()

            # 5. Drop Play
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
                "COMMANDCENTER", "NEXUS", "HATCHERY", "LAIR", "HIVE"
            }
        )

        for base in enemy_bases:
            self.priority_targets.append(base.position)

        # ★ 2. Tech Buildings ★
        tech_buildings = self.bot.enemy_structures.filter(
            lambda s: getattr(s.type_id, "name", "").upper() in {
                "FACTORY", "STARPORT", "ROBOTICSFACILITY", "STARGATE",
                "TWILIGHTCOUNCIL", "SPIRE", "HYDRALISKDEN"
            }
        )

        for building in tech_buildings:
            self.priority_targets.append(building.position)

    def _find_harassment_target(self) -> Optional[Point2]:
        """견제 타겟 찾기"""
        if self.priority_targets:
            # 가장 가까운 타겟 선택
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
        Zergling Run-by 관리

        전투가 발생 중이면 일부 저글링을 적 미네랄 라인으로 파견
        """
        game_time = getattr(self.bot, "time", 0)

        # Cooldown check
        if game_time < self.zergling_runby_cooldown:
            return

        # ★ 전투 중인지 확인 ★
        is_combat = self._is_main_army_fighting()
        if not is_combat:
            return

        # ★ 저글링 확인 ★
        if not hasattr(self.bot, "units"):
            return

        zerglings = self.bot.units(UnitTypeId.ZERGLING)
        if len(zerglings) < 8:  # 최소 8마리 필요
            return

        # ★ 4마리를 Run-by로 파견 ★
        runby_count = min(4, len(zerglings) // 2)  # 최대 절반
        runby_units = zerglings[:runby_count]

        # ★ 타겟: 적 미네랄 라인 ★
        target = self._find_enemy_mineral_line()
        if not target:
            return

        # ★ Run-by 실행 ★
        for ling in runby_units:
            self.bot.do(ling.attack(target))
            self.zergling_runby_tags.add(ling.tag)

        self.zergling_runby_active = True
        self.zergling_runby_cooldown = game_time + self.zergling_runby_interval

        self.logger.info(
            f"[{int(game_time)}s] ★ ZERGLING RUN-BY activated! ({runby_count} units) → {target} ★"
        )

    def _is_main_army_fighting(self) -> bool:
        """
        본진 군대가 전투 중인지 확인

        성능 최적화:
        - hasattr() 체크를 한 번만 수행 (캐싱)
        - 2초마다만 재계산 (캐시 활용)
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
        for unit in army_units[:10]:  # 샘플링 (성능 최적화)
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
                "COMMANDCENTER", "NEXUS", "HATCHERY", "LAIR", "HIVE"
            }
        )

        if not enemy_bases:
            return None

        # 가장 가까운 기지 선택
        if not hasattr(self.bot, "start_location") or not self.bot.start_location:
            # start_location이 없으면 첫 번째 기지 선택
            closest_base = enemy_bases[0]
        else:
            closest_base = min(
                enemy_bases,
                key=lambda b: b.position.distance_to(self.bot.start_location)
            )

        # 미네랄 패치 근처 위치 반환
        if hasattr(self.bot, "mineral_field") and self.bot.mineral_field:
            minerals_near_base = self.bot.mineral_field.closer_than(10, closest_base)
            if minerals_near_base:
                first_mineral = minerals_near_base.first
                if first_mineral:
                    return first_mineral.position

        return closest_base.position

    # ========================================
    # Mutalisk Harassment
    # ========================================

    async def _manage_mutalisk_harassment(self):
        """
        Mutalisk 견제 관리

        - 미네랄 라인 타격
        - HP 30% 이하 자동 퇴각
        """
        if not hasattr(self.bot, "units"):
            return

        mutalisks = self.bot.units(UnitTypeId.MUTALISK)
        if not mutalisks:
            return

        # ★ HP 체크 및 퇴각 ★
        for muta in mutalisks:
            hp_percent = muta.health / muta.health_max if muta.health_max > 0 else 0

            if hp_percent <= self.mutalisk_retreat_hp_threshold:
                # ★ 퇴각: 본진으로 복귀 ★
                if hasattr(self.bot, "start_location") and self.bot.start_location:
                    self.bot.do(muta.move(self.bot.start_location))
                    if muta.tag in self.mutalisk_harass_tags:
                        self.mutalisk_harass_tags.remove(muta.tag)
                elif hasattr(self.bot, "townhalls") and self.bot.townhalls:
                    # start_location이 없으면 가장 가까운 타운홀로
                    closest_townhall = self.bot.townhalls.closest_to(muta)
                    if closest_townhall:
                        self.bot.do(muta.move(closest_townhall.position))
                        if muta.tag in self.mutalisk_harass_tags:
                            self.mutalisk_harass_tags.remove(muta.tag)
                continue

        # ★ 건강한 뮤탈만 견제 ★
        healthy_mutas = mutalisks.filter(
            lambda m: m.health / m.health_max > self.mutalisk_retreat_hp_threshold
        )

        if not healthy_mutas or len(healthy_mutas) < 4:
            return

        # ★ 타겟 설정 ★
        if not self.mutalisk_harass_target:
            self.mutalisk_harass_target = self._find_enemy_mineral_line()

        if not self.mutalisk_harass_target:
            return

        # ★ 견제 실행 ★
        for muta in healthy_mutas:
            # 일꾼 우선 타겟
            workers = self._find_enemy_workers_near(self.mutalisk_harass_target)

            if workers:
                # 가장 가까운 일꾼 공격
                target_worker = min(workers, key=lambda w: w.distance_to(muta))
                self.bot.do(muta.attack(target_worker))
            else:
                # 일꾼 없으면 타겟 위치로 이동
                self.bot.do(muta.move(self.mutalisk_harass_target))

            self.mutalisk_harass_tags.add(muta.tag)

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
        Roach/Ravager 포킹

        - 담즙으로 주요 건물 공격
        - 적 본진 오기 전 퇴각
        """
        if not hasattr(self.bot, "units"):
            return

        roaches = self.bot.units(UnitTypeId.ROACH)
        ravagers = self.bot.units(UnitTypeId.RAVAGER)

        if not roaches and not ravagers:
            return

        poke_units = roaches | ravagers

        if len(poke_units) < 5:  # 최소 5기 필요
            return

        # ★ 포킹 타겟 찾기 ★
        target = self._find_harassment_target()
        if not target:
            return

        # ★ 위협 레벨 체크 ★
        threat_level = self._assess_threat_at_position(target)

        if threat_level > 15:  # 적 병력이 너무 많으면 퇴각
            # ★ 퇴각 ★
            for unit in poke_units:
                if hasattr(self.bot, "start_location"):
                    self.bot.do(unit.move(self.bot.start_location))
            return

        # ★ 포킹 실행 ★
        for roach in roaches:
            # 타겟 근처 건물 공격
            buildings = self._find_buildings_near(target)
            if buildings:
                self.bot.do(roach.attack(buildings[0]))
            else:
                self.bot.do(roach.attack(target))

        # ★ Ravager 담즙 ★
        for ravager in ravagers:
            if ravager.energy >= 25:  # Bile 에너지 필요
                buildings = self._find_buildings_near(target)
                if buildings:
                    self.bot.do(ravager(AbilityId.EFFECT_CORROSIVEBILE, buildings[0].position))

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
        """
        메모리 누수 방지: 죽은 유닛 tag 정리

        - zergling_runby_tags, mutalisk_harass_tags, roach_poke_tags 등에서
          실제로 존재하지 않는 유닛들을 제거
        """
        if not hasattr(self.bot, "units"):
            return

        # Zergling Run-by tags 정리
        dead_ling_tags = []
        for tag in self.zergling_runby_tags:
            unit = self.bot.units.find_by_tag(tag)
            if not unit:
                dead_ling_tags.append(tag)

        for tag in dead_ling_tags:
            self.zergling_runby_tags.discard(tag)

        # Mutalisk Harassment tags 정리
        dead_muta_tags = []
        for tag in self.mutalisk_harass_tags:
            unit = self.bot.units.find_by_tag(tag)
            if not unit:
                dead_muta_tags.append(tag)

        for tag in dead_muta_tags:
            self.mutalisk_harass_tags.discard(tag)

        # Roach Poking tags 정리
        dead_roach_tags = []
        for tag in self.roach_poke_tags:
            unit = self.bot.units.find_by_tag(tag)
            if not unit:
                dead_roach_tags.append(tag)

        for tag in dead_roach_tags:
            self.roach_poke_tags.discard(tag)

        # Drop unit tags 정리
        dead_drop_tags = []
        for tag in self.drop_unit_tags:
            unit = self.bot.units.find_by_tag(tag)
            if not unit:
                dead_drop_tags.append(tag)

        for tag in dead_drop_tags:
            self.drop_unit_tags.discard(tag)

        # Drop overlord tag 정리
        if self.drop_overlord_tag:
            overlord = self.bot.units.find_by_tag(self.drop_overlord_tag)
            if not overlord:
                self.drop_overlord_tag = None

        # 정리된 tag 수 로그
        total_cleaned = len(dead_ling_tags) + len(dead_muta_tags) + len(dead_roach_tags) + len(dead_drop_tags)
        if total_cleaned > 0:
            self.logger.debug(f"Cleaned up {total_cleaned} dead unit tags from harassment tracker")

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
        Drop Play 관리

        - Overlord + 유닛으로 확장 타격
        - 본진 교전 중 멀티프롱 어택
        """
        if not hasattr(self.bot, "units"):
            return

        # ★ 1. 본진 교전 중인지 확인 (Drop Play 타이밍) ★
        if not self._is_main_army_fighting():
            return  # 본진이 교전 중일 때만 Drop Play 실행

        # ★ 2. Overlord 운송 능력 확인 ★
        overlords = self.bot.units(UnitTypeId.OVERLORD).filter(
            lambda o: o.is_idle and not o.has_cargo
        )

        if not overlords:
            return

        # ★ 3. 운송 가능한 유닛 선택 (Zergling 또는 Roach) ★
        dropable_units = self.bot.units.filter(
            lambda u: u.type_id in {UnitTypeId.ZERGLING, UnitTypeId.ROACH} and u.is_idle
        )

        if len(dropable_units) < 4:  # 최소 4기 필요
            return

        # ★ 4. Drop 목표 선택: 적 확장 기지 ★
        target = self._find_drop_target()
        if not target:
            return

        # ★ 5. Overlord에 유닛 로딩 ★
        overlord = overlords.first
        units_to_load = dropable_units[:8]  # Overlord는 최대 8 supply 운송 가능

        for unit in units_to_load:
            self.bot.do(overlord(AbilityId.LOAD, unit))

        # ★ 6. Drop 위치로 이동 ★
        self.bot.do(overlord.move(target))

        # 로그
        game_time = int(self.bot.time)
        self.logger.info(
            f"[{game_time}s] ★ DROP PLAY INITIATED! {len(units_to_load)} units → {target} ★"
        )

    def _find_drop_target(self) -> Optional[Point2]:
        """Drop 타겟 선택: 적 확장 기지"""
        if not hasattr(self.bot, "enemy_structures"):
            return None

        # 적 확장 기지 찾기
        enemy_bases = self.bot.enemy_structures.filter(
            lambda s: s.type_id in {
                UnitTypeId.COMMANDCENTER,
                UnitTypeId.ORBITALCOMMAND,
                UnitTypeId.PLANETARYFORTRESS,
                UnitTypeId.NEXUS,
                UnitTypeId.HATCHERY,
                UnitTypeId.LAIR,
                UnitTypeId.HIVE,
            }
        )

        if not enemy_bases:
            return None

        # 본진이 아닌 확장 기지 선택 (거리가 먼 것)
        if hasattr(self.bot, "enemy_start_locations") and self.bot.enemy_start_locations:
            enemy_main = self.bot.enemy_start_locations[0]
            expansions = [b for b in enemy_bases if b.position.distance_to(enemy_main) > 20]

            if expansions:
                # 가장 가까운 확장 선택
                if hasattr(self.bot, "start_location") and self.bot.start_location:
                    closest_expansion = min(
                        expansions,
                        key=lambda b: b.position.distance_to(self.bot.start_location)
                    )
                    return closest_expansion.position
                else:
                    return expansions[0].position

        # 확장이 없으면 본진 뒤쪽 미네랄 라인
        if enemy_bases:
            return enemy_bases.first.position

        return None

    # ========================================
    # Utility
    # ========================================

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
