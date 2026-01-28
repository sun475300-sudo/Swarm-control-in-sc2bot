# -*- coding: utf-8 -*-
"""
Complete Destruction Trainer - 완전 파괴 학습 시스템

모든 적 건물을 파괴하는 방법을 학습:
1. 타운홀뿐만 아니라 모든 생산 건물 추적
2. 건물 파괴 우선순위 학습
3. 완전 승리 보장 (모든 건물 파괴)
4. Combat Manager와 통합
"""

from typing import List, Dict, Optional, Set
from sc2.position import Point2
from sc2.ids.unit_typeid import UnitTypeId
from utils.logger import get_logger


class TargetBuilding:
    """파괴 목표 건물"""

    def __init__(self, position: Point2, unit_type: UnitTypeId, tag: int):
        self.position = position
        self.unit_type = unit_type
        self.tag = tag
        self.priority = 0  # 파괴 우선순위
        self.assigned_units = 0  # 할당된 공격 유닛 수
        self.last_seen_time = 0.0


class CompleteDestructionTrainer:
    """
    완전 파괴 학습 시스템

    모든 적 건물을 체계적으로 파괴하는 방법을 학습합니다.
    """

    def __init__(self, bot):
        self.bot = bot
        self.logger = get_logger("CompleteDestruction")

        # 파괴 목표 추적
        self.target_buildings: Dict[int, TargetBuilding] = {}  # tag -> TargetBuilding
        self.destroyed_buildings: Set[int] = set()

        # 건물 타입별 우선순위 (높을수록 먼저 파괴)
        self.DESTRUCTION_PRIORITY = {
            # 타운홀 (최우선)
            UnitTypeId.COMMANDCENTER: 100,
            UnitTypeId.ORBITALCOMMAND: 100,
            UnitTypeId.PLANETARYFORTRESS: 100,
            UnitTypeId.NEXUS: 100,
            UnitTypeId.HATCHERY: 100,
            UnitTypeId.LAIR: 100,
            UnitTypeId.HIVE: 100,

            # 생산 건물 (두 번째 우선순위)
            UnitTypeId.BARRACKS: 80,
            UnitTypeId.FACTORY: 80,
            UnitTypeId.STARPORT: 80,
            UnitTypeId.GATEWAY: 80,
            UnitTypeId.ROBOTICSFACILITY: 80,
            UnitTypeId.STARGATE: 80,
            UnitTypeId.SPAWNINGPOOL: 80,
            UnitTypeId.ROACHWARREN: 80,
            UnitTypeId.HYDRALISKDEN: 80,
            UnitTypeId.SPIRE: 80,

            # 테크 건물 (세 번째 우선순위)
            UnitTypeId.ENGINEERINGBAY: 60,
            UnitTypeId.ARMORY: 60,
            UnitTypeId.FORGE: 60,
            UnitTypeId.CYBERNETICSCORE: 60,
            UnitTypeId.TWILIGHTCOUNCIL: 60,
            UnitTypeId.EVOLUTIONCHAMBER: 60,

            # 방어 건물 (네 번째 우선순위)
            UnitTypeId.BUNKER: 70,
            UnitTypeId.PHOTONCANNON: 70,
            UnitTypeId.SPINECRAWLER: 70,
            UnitTypeId.SPORECRAWLER: 70,
            UnitTypeId.MISSILETURRET: 50,

            # 기타 건물 (낮은 우선순위)
            UnitTypeId.SUPPLYDEPOT: 30,
            UnitTypeId.PYLON: 30,
        }

        # 통계
        self.total_buildings_found = 0
        self.total_buildings_destroyed = 0
        self.buildings_destroyed_per_type: Dict[str, int] = {}

        # 설정
        self.MIN_ARMY_FOR_DESTRUCTION = 8  # 건물 파괴에 필요한 최소 군대
        self.MAX_UNITS_PER_BUILDING = 5  # 건물당 최대 할당 유닛

    async def on_step(self, iteration: int):
        """매 프레임 실행"""
        try:
            game_time = self.bot.time

            # 1. 적 건물 발견 및 추적 (매 프레임)
            self._discover_enemy_buildings(game_time)

            # 2. 파괴된 건물 확인 (2초마다)
            if iteration % 44 == 0:
                self._check_destroyed_buildings()

            # 3. 파괴 우선순위 계산 (2초마다)
            if iteration % 44 == 0:
                self._calculate_priorities(game_time)

            # 4. 공격 유닛 할당 (1초마다)
            if iteration % 22 == 0:
                await self._assign_attack_units()

            # 5. 디버그 출력 (20초마다)
            if iteration % 440 == 0 and self.target_buildings:
                self._print_status(game_time)

        except Exception as e:
            if iteration % 200 == 0:
                self.logger.error(f"[COMPLETE_DESTRUCTION] Error: {e}")

    def _discover_enemy_buildings(self, game_time: float):
        """모든 적 건물 발견"""
        if not hasattr(self.bot, "enemy_structures"):
            return

        for structure in self.bot.enemy_structures:
            tag = structure.tag

            if tag not in self.target_buildings and tag not in self.destroyed_buildings:
                # 새 건물 발견
                self.target_buildings[tag] = TargetBuilding(
                    position=structure.position,
                    unit_type=structure.type_id,
                    tag=tag
                )
                self.total_buildings_found += 1

                # 우선순위 설정
                priority = self.DESTRUCTION_PRIORITY.get(structure.type_id, 40)
                self.target_buildings[tag].priority = priority

                self.logger.info(
                    f"[NEW TARGET] {structure.type_id.name} at {structure.position} "
                    f"(Priority: {priority})"
                )
            elif tag in self.target_buildings:
                # 기존 건물 업데이트
                self.target_buildings[tag].last_seen_time = game_time

    def _check_destroyed_buildings(self):
        """파괴된 건물 확인"""
        current_enemy_tags = {s.tag for s in self.bot.enemy_structures}

        destroyed_tags = []
        for tag in self.target_buildings.keys():
            if tag not in current_enemy_tags:
                destroyed_tags.append(tag)

        for tag in destroyed_tags:
            building = self.target_buildings[tag]
            self.destroyed_buildings.add(tag)
            del self.target_buildings[tag]

            self.total_buildings_destroyed += 1

            # 타입별 통계
            type_name = building.unit_type.name
            self.buildings_destroyed_per_type[type_name] = \
                self.buildings_destroyed_per_type.get(type_name, 0) + 1

            self.logger.info(
                f"[DESTROYED] {type_name} at {building.position} "
                f"({self.total_buildings_destroyed}/{self.total_buildings_found})"
            )

    def _calculate_priorities(self, game_time: float):
        """파괴 우선순위 재계산"""
        our_main_base = self.bot.start_location

        for building in self.target_buildings.values():
            base_priority = self.DESTRUCTION_PRIORITY.get(building.unit_type, 40)

            # 거리 가중치 (가까울수록 높은 우선순위)
            distance_to_us = building.position.distance_to(our_main_base)
            distance_weight = max(0, 100 - distance_to_us) / 100

            # Map Memory에서 확인된 적 기지 근처인지 확인
            near_enemy_base = False
            if hasattr(self.bot, "map_memory") and self.bot.map_memory:
                enemy_bases = self.bot.map_memory.get_enemy_bases()
                for base_pos in enemy_bases:
                    if building.position.distance_to(base_pos) < 15:
                        near_enemy_base = True
                        break

            # 적 기지 근처 건물은 우선순위 증가
            base_weight = 1.5 if near_enemy_base else 1.0

            # 최종 우선순위
            building.priority = int(base_priority * base_weight * (0.7 + 0.3 * distance_weight))

    async def _assign_attack_units(self):
        """공격 유닛 할당"""
        if not self.target_buildings:
            return

        # 충분한 군대가 있는지 확인
        army_units = self.bot.units.filter(
            lambda u: u.type_id in {
                UnitTypeId.ZERGLING, UnitTypeId.ROACH, UnitTypeId.HYDRALISK,
                UnitTypeId.MUTALISK, UnitTypeId.RAVAGER, UnitTypeId.ULTRALISK
            }
        )

        if army_units.amount < self.MIN_ARMY_FOR_DESTRUCTION:
            return

        # 우선순위 순으로 정렬
        sorted_buildings = sorted(
            self.target_buildings.values(),
            key=lambda b: b.priority,
            reverse=True
        )

        if not sorted_buildings:
            return

        # 최고 우선순위 건물 선택
        target = sorted_buildings[0]

        # 근처 유닛 찾기
        nearby_units = army_units.closer_than(50, target.position)

        if nearby_units:
            # 최대 5유닛 할당
            units_to_assign = nearby_units.take(self.MAX_UNITS_PER_BUILDING)

            for unit in units_to_assign:
                # Unit Authority Manager 통합
                if hasattr(self.bot, "unit_authority") and self.bot.unit_authority:
                    from unit_authority_manager import Authority
                    granted = self.bot.unit_authority.request_authority(
                        {unit.tag},
                        Authority.COMBAT,
                        "CompleteDestruction",
                        self.bot.state.game_loop
                    )

                    if unit.tag in granted:
                        self.bot.do(unit.attack(target.position))
                else:
                    # 폴백: 직접 명령
                    self.bot.do(unit.attack(target.position))

            target.assigned_units = units_to_assign.amount

    def get_primary_target(self) -> Optional[Point2]:
        """
        주요 공격 목표 반환 (Combat Manager 통합용)

        Returns:
            최고 우선순위 건물 위치
        """
        if not self.target_buildings:
            return None

        # 우선순위 순으로 정렬
        sorted_buildings = sorted(
            self.target_buildings.values(),
            key=lambda b: b.priority,
            reverse=True
        )

        if sorted_buildings:
            return sorted_buildings[0].position

        return None

    def get_all_targets(self) -> List[Point2]:
        """모든 파괴 목표 위치 반환"""
        return [building.position for building in self.target_buildings.values()]

    def is_complete_victory(self) -> bool:
        """완전 승리 여부 (모든 건물 파괴)"""
        return len(self.target_buildings) == 0 and self.total_buildings_found > 0

    def _print_status(self, game_time: float):
        """상태 출력"""
        remaining = len(self.target_buildings)
        destroyed_percent = (self.total_buildings_destroyed / max(self.total_buildings_found, 1) * 100)

        self.logger.info(
            f"[STATUS] [{int(game_time)}s] "
            f"Remaining: {remaining}, Destroyed: {self.total_buildings_destroyed}/{self.total_buildings_found} "
            f"({destroyed_percent:.1f}%)"
        )

        # 타입별 파괴 통계
        if self.buildings_destroyed_per_type:
            self.logger.info("[DESTROYED BY TYPE]")
            for type_name, count in sorted(self.buildings_destroyed_per_type.items(), key=lambda x: x[1], reverse=True):
                self.logger.info(f"  {type_name}: {count}")

    def get_statistics(self) -> Dict:
        """통계 반환"""
        destroyed_percent = (self.total_buildings_destroyed / max(self.total_buildings_found, 1) * 100)

        return {
            "total_found": self.total_buildings_found,
            "total_destroyed": self.total_buildings_destroyed,
            "remaining": len(self.target_buildings),
            "destroyed_percent": f"{destroyed_percent:.1f}%",
            "is_complete_victory": self.is_complete_victory(),
            "destroyed_by_type": dict(self.buildings_destroyed_per_type)
        }
