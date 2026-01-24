"""
건물 파괴 시스템 (Building Destroyer)

적 건물을 효율적으로 파괴하여 빠르게 게임을 끝냅니다.

핵심 기능:
1. 시야에 보이는 모든 건물을 동시 공격 (병력 분산)
2. 건물 우선순위 (타운홀 > 생산 건물 > 방어 건물 > 기타)
3. 빠른 게임 종료를 위한 공격적 병력 배분
"""

from typing import List, Dict, Set, Optional
from sc2.position import Point2
from sc2.ids.unit_typeid import UnitTypeId
from sc2.unit import Unit
from utils.logger import get_logger
import math


class BuildingDestroyer:
    """건물 파괴 전문 시스템"""

    def __init__(self, bot):
        self.bot = bot
        self.logger = get_logger("BuildingDestroyer")

        # 건물 우선순위 (높을수록 우선)
        self.building_priority = {
            # 타운홀 (최고 우선순위)
            UnitTypeId.NEXUS: 100,
            UnitTypeId.COMMANDCENTER: 100,
            UnitTypeId.ORBITALCOMMAND: 100,
            UnitTypeId.PLANETARYFORTRESS: 100,
            UnitTypeId.HATCHERY: 100,
            UnitTypeId.LAIR: 100,
            UnitTypeId.HIVE: 100,

            # 생산 건물
            UnitTypeId.GATEWAY: 80,
            UnitTypeId.WARPGATE: 80,
            UnitTypeId.BARRACKS: 80,
            UnitTypeId.FACTORY: 80,
            UnitTypeId.STARPORT: 80,
            UnitTypeId.ROBOTICSFACILITY: 80,
            UnitTypeId.STARGATE: 80,
            UnitTypeId.SPAWNINGPOOL: 80,
            UnitTypeId.ROACHWARREN: 80,

            # 테크 건물
            UnitTypeId.TWILIGHTCOUNCIL: 70,
            UnitTypeId.TEMPLARARCHIVE: 70,
            UnitTypeId.DARKSHRINE: 70,
            UnitTypeId.ARMORY: 70,
            UnitTypeId.FUSIONCORE: 70,
            UnitTypeId.SPIRE: 70,
            UnitTypeId.GREATERSPIRE: 70,
            UnitTypeId.INFESTATIONPIT: 70,

            # 방어 건물
            UnitTypeId.PHOTONCANNON: 60,
            UnitTypeId.BUNKER: 60,
            UnitTypeId.MISSILETURRET: 60,
            UnitTypeId.SPINECRAWLER: 60,
            UnitTypeId.SPORECRAWLER: 60,

            # 기타 건물
            "DEFAULT": 40,
        }

        # 공격 배정된 건물 추적
        self.assigned_targets: Dict[int, Set[int]] = {}  # {building_tag: {unit_tags}}

        # 알려진 모든 적 건물 (시야에서 사라져도 기억)
        self.known_enemy_buildings: Dict[int, Point2] = {}  # {tag: last_known_position}

    async def on_step(self, iteration: int):
        """매 프레임 실행"""
        try:
            # 적 건물 업데이트
            self._update_known_buildings()

            # 건물 동시 공격
            await self._distribute_attack_forces()

            # 로그 (10초마다)
            if iteration % 220 == 0:
                self._log_status()

        except Exception as e:
            if iteration % 200 == 0:
                self.logger.error(f"Building destroyer error: {e}")

    def _update_known_buildings(self):
        """알려진 적 건물 업데이트"""
        # 현재 보이는 건물 추가/업데이트
        for structure in self.bot.enemy_structures:
            self.known_enemy_buildings[structure.tag] = structure.position

        # 파괴된 건물 제거
        visible_tags = {s.tag for s in self.bot.enemy_structures}
        destroyed_tags = set(self.known_enemy_buildings.keys()) - visible_tags

        for tag in destroyed_tags:
            # 실제로 파괴되었는지 확인 (시야 밖일 수도 있음)
            # 일단 보존 (정찰로 재확인 필요)
            pass

    async def _distribute_attack_forces(self):
        """
        병력을 여러 건물에 분산 배치

        핵심 아이디어:
        1. 현재 보이는 모든 건물을 우선순위 정렬
        2. 병력을 균등 분배하여 동시 공격
        3. 각 건물당 최소 3유닛 배정
        """
        # 공격 가능한 유닛
        attack_units = self._get_available_attack_units()

        if not attack_units.exists:
            return

        # 공격 대상 건물 (우선순위 정렬)
        target_buildings = self._get_prioritized_buildings()

        if not target_buildings:
            return

        # 병력 분산 계산
        units_per_building = max(3, attack_units.amount // len(target_buildings))

        assigned_count = 0

        for building in target_buildings:
            if assigned_count >= attack_units.amount:
                break

            # 이 건물에 배정할 유닛들
            available = attack_units[assigned_count:assigned_count + units_per_building]

            # 건물 공격 명령
            for unit in available:
                unit.attack(building.position)

            assigned_count += units_per_building

            # 로그
            if self.bot.iteration % 220 == 0:
                building_name = building.type_id.name if hasattr(building.type_id, 'name') else str(building.type_id)
                print(f"[DESTROYER] {len(available)} units attacking {building_name} at {building.position}")

        # 남은 유닛들 (병력이 많으면)
        remaining = attack_units[assigned_count:]

        if remaining.exists:
            # 첫 번째 목표에 추가 병력
            first_target = target_buildings[0]
            for unit in remaining:
                unit.attack(first_target.position)

    def _get_available_attack_units(self):
        """공격 가능한 유닛 가져오기"""
        combat_types = {
            UnitTypeId.ZERGLING,
            UnitTypeId.BANELING,
            UnitTypeId.ROACH,
            UnitTypeId.RAVAGER,
            UnitTypeId.HYDRALISK,
            UnitTypeId.LURKERMP,
            UnitTypeId.MUTALISK,
            UnitTypeId.CORRUPTOR,
            UnitTypeId.ULTRALISK,
        }

        return self.bot.units.filter(
            lambda u: u.type_id in combat_types
        )

    def _get_prioritized_buildings(self) -> List[Unit]:
        """
        우선순위가 높은 순으로 건물 정렬

        정렬 기준:
        1. 건물 우선순위 (타운홀 > 생산 > 방어)
        2. HP (낮은 것 우선)
        3. 거리 (가까운 것 우선)
        """
        buildings = list(self.bot.enemy_structures)

        if not buildings:
            return []

        # 우선순위 계산
        def get_priority(building: Unit) -> float:
            # 기본 우선순위
            base_priority = self.building_priority.get(
                building.type_id,
                self.building_priority["DEFAULT"]
            )

            # HP 보너스 (HP 낮을수록 우선)
            hp_ratio = building.health / building.health_max
            hp_bonus = (1 - hp_ratio) * 20  # 최대 +20

            # 거리 페널티 (가까울수록 우선)
            if self.bot.townhalls.exists:
                distance = building.distance_to(self.bot.townhalls.first)
                distance_penalty = min(distance / 10, 10)  # 최대 -10
            else:
                distance_penalty = 0

            return base_priority + hp_bonus - distance_penalty

        # 우선순위 정렬 (높은 순)
        buildings.sort(key=get_priority, reverse=True)

        return buildings

    def _log_status(self):
        """상태 로그"""
        total_buildings = len(self.bot.enemy_structures)
        known_buildings = len(self.known_enemy_buildings)

        if total_buildings > 0:
            self.logger.info(
                f"[{int(self.bot.time)}s] Enemy buildings: {total_buildings} visible, "
                f"{known_buildings} total known"
            )


# ==================== 빠른 게임 종료 전략 ====================

class RapidVictorySystem:
    """
    빠른 승리 시스템

    게임을 최대한 빨리 끝내기 위한 공격적 전략
    """

    def __init__(self, bot):
        self.bot = bot
        self.logger = get_logger("RapidVictory")

        # 공격적 모드
        self.aggressive_mode = False
        self.rush_threshold = 180  # 3분 이후 공격 시작

    async def on_step(self, iteration: int):
        """매 프레임 실행"""
        try:
            game_time = self.bot.time

            # === 공격적 모드 활성화 ===
            if not self.aggressive_mode and game_time > self.rush_threshold:
                self.aggressive_mode = True
                self.logger.info(f"[{int(game_time)}s] RAPID VICTORY MODE ACTIVATED!")

            # 공격적 모드일 때
            if self.aggressive_mode:
                await self._execute_rapid_victory()

        except Exception as e:
            if iteration % 200 == 0:
                self.logger.error(f"Rapid victory error: {e}")

    async def _execute_rapid_victory(self):
        """빠른 승리 실행"""
        # === 1. 모든 병력 즉시 공격 ===
        await self._send_all_forces()

        # === 2. 드론 생산 제한 (최소한만) ===
        self._limit_worker_production()

        # === 3. 군사 유닛 최대 생산 ===
        # (Production Manager에서 자동 처리)

    async def _send_all_forces(self):
        """모든 병력 공격"""
        combat_types = {
            UnitTypeId.ZERGLING,
            UnitTypeId.BANELING,
            UnitTypeId.ROACH,
            UnitTypeId.RAVAGER,
            UnitTypeId.HYDRALISK,
            UnitTypeId.MUTALISK,
        }

        army = self.bot.units.filter(lambda u: u.type_id in combat_types)

        if not army.exists:
            return

        # 목표: 적 건물
        if self.bot.enemy_structures.exists:
            target = self.bot.enemy_structures.closest_to(army.center)
            for unit in army:
                unit.attack(target.position)
        elif self.bot.enemy_start_locations:
            # 적 시작 위치 공격
            target = self.bot.enemy_start_locations[0]
            for unit in army:
                unit.attack(target)

    def _limit_worker_production(self):
        """드론 생산 제한"""
        # Economy Manager에 신호 전달
        if hasattr(self.bot, 'economy'):
            # 드론 45마리로 제한
            max_workers = 45
            current_workers = self.bot.workers.amount

            if current_workers >= max_workers:
                # 드론 생산 중지 신호
                if hasattr(self.bot.economy, '_emergency_mode'):
                    self.bot.economy._emergency_mode = True
