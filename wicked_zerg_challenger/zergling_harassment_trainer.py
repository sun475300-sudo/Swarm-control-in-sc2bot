# -*- coding: utf-8 -*-
"""
Zergling Harassment Trainer - 저글링 괴롭힘 전술 학습 시스템

저글링의 기동성을 활용한 고급 괴롭힘 전술:
1. 빠른 이동 속도 (3.15, 대사 업그레이드 시 4.725)
2. 적 일꾼 지속 괴롭힘
3. 확장 견제 및 방해
4. 히트 앤 런 전술
5. 멀티태스킹 공격 (여러 지점 동시 공격)
"""

from typing import Dict, Set, List, Optional
from sc2.position import Point2
from sc2.ids.unit_typeid import UnitTypeId
from sc2.ids.upgrade_id import UpgradeId
from utils.logger import get_logger


class ZerglingSquad:
    """저글링 분대"""

    def __init__(self, squad_id: int, lings: List):
        self.squad_id = squad_id
        self.ling_tags = {u.tag for u in lings}
        self.target_position: Optional[Point2] = None
        self.last_attack_time = 0.0
        self.kills = 0
        self.created_time = 0.0


class ZerglingHarassmentTrainer:
    """
    저글링 괴롭힘 전술 학습 시스템

    저글링의 기동성을 활용하여 적을 지속적으로 괴롭힘
    """

    def __init__(self, bot):
        self.bot = bot
        self.logger = get_logger("ZerglingHarass")

        # 분대 관리
        self.squads: Dict[int, ZerglingSquad] = {}  # squad_id -> ZerglingSquad
        self.next_squad_id = 1

        # 괴롭힘 설정 (게임 초반 최적화)
        self.SQUAD_SIZE = 4  # 분대당 저글링 수 (6 → 4, 더 빠른 괴롭힘)
        self.MIN_LINGS_FOR_HARASS = 4  # 괴롭힘에 필요한 최소 저글링
        self.MAX_SQUADS = 6  # 최대 분대 수 (4 → 6, 더 많은 동시 괴롭힘)

        # 타겟 우선순위
        self.WORKER_PRIORITY = 100
        self.GAS_BUILDING_PRIORITY = 90
        self.TECH_BUILDING_PRIORITY = 80
        self.EXPANSION_PRIORITY = 70

        # 히트 앤 런 설정
        self.RETREAT_HP_THRESHOLD = 0.3  # 체력 30% 이하면 후퇴
        self.RETREAT_DISTANCE = 10.0
        self.REENGAGE_HP_THRESHOLD = 0.8  # 체력 80% 이상이면 재공격

        # 멀티태스킹 설정 (게임 초반 집중 괴롭힘)
        self.MULTITASK_ENABLED = True
        self.HARASSMENT_INTERVAL = 3.0  # 괴롭힘 간격 (5초 → 3초, 더 빠른 괴롭힘)

        # 통계
        self.total_worker_kills = 0
        self.total_building_kills = 0
        self.total_squads_created = 0
        self.total_harass_missions = 0

        # 업그레이드 확인
        self.has_metabolic_boost = False  # 대사 촉진 (이동 속도 증가)
        self.has_adrenal_glands = False  # 부신 분비선 (공격 속도 증가)

    async def on_step(self, iteration: int):
        """매 프레임 실행"""
        try:
            game_time = self.bot.time

            # 업그레이드 확인
            self._check_upgrades()

            # 저글링 확인
            zerglings = self.bot.units(UnitTypeId.ZERGLING)
            if zerglings.amount < self.MIN_LINGS_FOR_HARASS:
                return

            # 1. 분대 생성 및 업데이트 (5초마다)
            if iteration % 110 == 0:
                self._update_squads(zerglings, game_time)

            # 2. 괴롭힘 타겟 선정 (1초마다)
            if iteration % 22 == 0:
                self._assign_harassment_targets(game_time)

            # 3. 히트 앤 런 실행 (매 프레임)
            await self._execute_hit_and_run(zerglings, game_time)

            # 4. 일꾼 사냥 (0.5초마다)
            if iteration % 11 == 0:
                await self._hunt_workers(zerglings)

            # 5. 통계 출력 (30초마다)
            if iteration % 660 == 0 and self.total_squads_created > 0:
                self._print_statistics(game_time)

        except Exception as e:
            if iteration % 200 == 0:
                self.logger.error(f"[ZERGLING_HARASS] Error: {e}")

    def _check_upgrades(self):
        """업그레이드 확인"""
        try:
            self.has_metabolic_boost = UpgradeId.ZERGLINGMOVEMENTSPEED in self.bot.state.upgrades
            self.has_adrenal_glands = UpgradeId.ZERGLINGATTACKSPEED in self.bot.state.upgrades
        except Exception:
            pass

    def _update_squads(self, zerglings, game_time: float):
        """
        분대 생성 및 업데이트

        유휴 저글링을 모아서 괴롭힘 분대 생성
        """
        # 기존 분대의 저글링 태그 수집
        assigned_tags = set()
        for squad in self.squads.values():
            assigned_tags.update(squad.ling_tags)

        # 유휴 저글링 (분대에 속하지 않은 저글링)
        idle_lings = [z for z in zerglings if z.tag not in assigned_tags]

        # 분대 생성 가능한지 확인
        if len(idle_lings) >= self.SQUAD_SIZE and len(self.squads) < self.MAX_SQUADS:
            # 새 분대 생성
            squad_lings = idle_lings[:self.SQUAD_SIZE]
            
            # ★ Unit Authority Check ★
            if hasattr(self.bot, "unit_authority") and self.bot.unit_authority:
                from unit_authority_manager import Authority
                ling_tags = {l.tag for l in squad_lings}
                # COMBAT 권한 요청 (괴롭힘 임무)
                granted = self.bot.unit_authority.request_authority(
                    ling_tags, Authority.COMBAT, "ZerglingHarass", self.bot.state.game_loop
                )
                # 권한 못 받은 유닛 제외
                squad_lings = [l for l in squad_lings if l.tag in granted]
                
            if len(squad_lings) >= 4: # 최소 4마리
                squad = ZerglingSquad(self.next_squad_id, squad_lings)
                squad.created_time = game_time

                self.squads[self.next_squad_id] = squad
                self.next_squad_id += 1
                self.total_squads_created += 1

                self.logger.info(
                    f"[NEW_SQUAD] Squad #{squad.squad_id} created with {len(squad_lings)} zerglings"
                )

        # 죽은 저글링 제거
        current_ling_tags = {z.tag for z in zerglings}
        for squad in list(self.squads.values()):
            squad.ling_tags = squad.ling_tags & current_ling_tags

            # 분대원이 2마리 이하면 해산
            if len(squad.ling_tags) < 2:
                del self.squads[squad.squad_id]

    def _assign_harassment_targets(self, game_time: float):
        """
        괴롭힘 타겟 선정

        우선순위:
        1. 적 일꾼 (가장 높음)
        2. 가스 건물
        3. 테크 건물
        4. 확장 기지
        """
        if not self.squads:
            return

        for squad in self.squads.values():
            # 쿨다운 확인
            time_since_last = game_time - squad.last_attack_time
            if time_since_last < self.HARASSMENT_INTERVAL:
                continue

            # 타겟 선정
            target = self._find_best_harassment_target(squad)
            if target:
                squad.target_position = target
                squad.last_attack_time = game_time
                self.total_harass_missions += 1

    def _find_best_harassment_target(self, squad: ZerglingSquad) -> Optional[Point2]:
        """최적의 괴롭힘 타겟 찾기"""
        targets = []

        # 1. 적 일꾼
        if self.bot.enemy_units:
            workers = self.bot.enemy_units.filter(
                lambda u: u.type_id in {
                    UnitTypeId.SCV, UnitTypeId.PROBE, UnitTypeId.DRONE
                }
            )
            if workers:
                for worker in workers:
                    targets.append((worker.position, self.WORKER_PRIORITY))

        # 2. 가스 건물
        if self.bot.enemy_structures:
            gas_buildings = self.bot.enemy_structures.filter(
                lambda s: s.type_id in {
                    UnitTypeId.REFINERY, UnitTypeId.ASSIMILATOR, UnitTypeId.EXTRACTOR,
                    UnitTypeId.REFINERYRICH, UnitTypeId.ASSIMILATORRICH, UnitTypeId.EXTRACTORRICH
                }
            )
            if gas_buildings:
                for building in gas_buildings:
                    targets.append((building.position, self.GAS_BUILDING_PRIORITY))

        # 3. 테크 건물
        if self.bot.enemy_structures:
            tech_buildings = self.bot.enemy_structures.filter(
                lambda s: s.type_id in {
                    UnitTypeId.ENGINEERINGBAY, UnitTypeId.ARMORY,
                    UnitTypeId.FORGE, UnitTypeId.CYBERNETICSCORE,
                    UnitTypeId.EVOLUTIONCHAMBER
                }
            )
            if tech_buildings:
                for building in tech_buildings:
                    targets.append((building.position, self.TECH_BUILDING_PRIORITY))

        # 4. 확장 기지
        if hasattr(self.bot, "map_memory") and self.bot.map_memory:
            enemy_bases = self.bot.map_memory.get_enemy_bases()
            if enemy_bases:
                # 가장 가까운 확장 기지
                if self.bot.start_location:
                    closest_base = min(
                        enemy_bases,
                        key=lambda b: b.distance_to(self.bot.start_location)
                    )
                    targets.append((closest_base, self.EXPANSION_PRIORITY))

        if not targets:
            return None

        # 우선순위 순으로 정렬
        targets.sort(key=lambda x: x[1], reverse=True)

        return targets[0][0]

    async def _execute_hit_and_run(self, zerglings, game_time: float):
        """
        히트 앤 런 실행

        체력이 낮으면 후퇴, 회복되면 재공격
        """
        for squad in self.squads.values():
            squad_lings = [z for z in zerglings if z.tag in squad.ling_tags]
            if not squad_lings:
                continue

            # 평균 체력 계산
            avg_hp_ratio = sum(z.health / z.health_max for z in squad_lings) / len(squad_lings)

            # 체력이 낮으면 후퇴
            if avg_hp_ratio < self.RETREAT_HP_THRESHOLD:
                await self._retreat_squad(squad, squad_lings)

            # 체력이 회복되면 재공격
            elif avg_hp_ratio > self.REENGAGE_HP_THRESHOLD and squad.target_position:
                await self._attack_target(squad, squad_lings)

    async def _retreat_squad(self, squad: ZerglingSquad, squad_lings: List):
        """분대 후퇴"""
        if not self.bot.townhalls.exists:
            return

        # 가장 가까운 아군 기지로 후퇴
        closest_base = self.bot.townhalls.closest_to(squad_lings[0].position)
        retreat_pos = closest_base.position

        for ling in squad_lings:
            # 후퇴 거리만큼 이동
            direction = (retreat_pos - ling.position).normalized
            retreat_target = ling.position + direction * self.RETREAT_DISTANCE

            self.bot.do(ling.move(retreat_target))

    async def _attack_target(self, squad: ZerglingSquad, squad_lings: List):
        """타겟 공격"""
        if not squad.target_position:
            return

        for ling in squad_lings:
            self.bot.do(ling.attack(squad.target_position))

    async def _hunt_workers(self, zerglings):
        """
        일꾼 사냥

        적 일꾼을 발견하면 집중 공격
        """
        if not self.bot.enemy_units:
            return

        # 적 일꾼 찾기
        workers = self.bot.enemy_units.filter(
            lambda u: u.type_id in {
                UnitTypeId.SCV, UnitTypeId.PROBE, UnitTypeId.DRONE
            }
        )

        if not workers:
            return

        # 분대별로 가장 가까운 일꾼 공격
        for squad in self.squads.values():
            squad_lings = [z for z in zerglings if z.tag in squad.ling_tags]
            if not squad_lings:
                continue

            # 가장 가까운 일꾼
            closest_worker = workers.closest_to(squad_lings[0].position)

            # 공격 거리 내에 있으면 집중 공격
            if squad_lings[0].distance_to(closest_worker) < 15:
                for ling in squad_lings:
                    # 체력이 30% 이상이면 공격
                    if ling.health / ling.health_max > 0.3:
                        self.bot.do(ling.attack(closest_worker))

    def get_harassment_statistics(self) -> Dict:
        """괴롭힘 통계 반환"""
        active_squads = len(self.squads)
        total_lings_in_squads = sum(len(s.ling_tags) for s in self.squads.values())

        return {
            "active_squads": active_squads,
            "total_lings_in_squads": total_lings_in_squads,
            "total_squads_created": self.total_squads_created,
            "total_harass_missions": self.total_harass_missions,
            "worker_kills": self.total_worker_kills,
            "building_kills": self.total_building_kills,
            "has_metabolic_boost": self.has_metabolic_boost,
            "has_adrenal_glands": self.has_adrenal_glands
        }

    def _print_statistics(self, game_time: float):
        """통계 출력"""
        stats = self.get_harassment_statistics()

        self.logger.info(
            f"[HARASS_STATS] [{int(game_time)}s] "
            f"Active Squads: {stats['active_squads']}, "
            f"Lings: {stats['total_lings_in_squads']}, "
            f"Missions: {stats['total_harass_missions']}"
        )

        if stats['has_metabolic_boost']:
            self.logger.info("[HARASS_STATS] Metabolic Boost: ACTIVE (+50% speed)")
