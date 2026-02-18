# -*- coding: utf-8 -*-
"""
Creep Expansion System - 전 맵 점막 확장

Queen의 Creep Tumor를 활용하여 맵 전체에 점막 확산:
1. 기지 주변 점막 확장
2. 확장 경로 점막 확장
3. 맵 전체 점막 네트워크 구축
"""

from typing import Dict, Set, List
from sc2.ids.unit_typeid import UnitTypeId
from sc2.ids.ability_id import AbilityId
from sc2.position import Point2
from utils.logger import get_logger


class CreepExpansionSystem:
    """전 맵 점막 확장 시스템"""

    def __init__(self, bot):
        self.bot = bot
        self.logger = get_logger("CreepExpansion")

        # 점막 종양 위치 추적
        self.tumor_positions: Set[Point2] = set()
        self.target_creep_positions: List[Point2] = []

        # 통계
        self.tumors_created = 0
        self.map_coverage = 0.0

    async def on_step(self, iteration: int):
        """매 프레임 실행"""
        try:
            # 44프레임(약 2초)마다 실행
            if iteration % 44 != 0:
                return

            game_time = self.bot.time

            # 1. 목표 점막 위치 계산
            if iteration % 220 == 0:  # 10초마다
                self._calculate_creep_targets()

            # 2. Queen으로 점막 종양 생성
            await self._queen_creep_tumors()

            # 3. 점막 종양 확장
            await self._spread_creep_tumors()

            # 4. 통계 업데이트
            if iteration % 1320 == 0:  # 60초마다
                self._update_statistics(game_time)

        except Exception as e:
            if iteration % 50 == 0:
                self.logger.error(f"[CREEP] Error: {e}")

    def _calculate_creep_targets(self):
        """목표 점막 위치 계산"""
        self.target_creep_positions.clear()

        if not self.bot.townhalls.exists:
            return

        import math

        # 1. 모든 기지 주변
        for base in self.bot.townhalls:
            # 기지 중심에서 4방향으로 확장
            for angle in [0, 90, 180, 270]:
                rad = math.radians(angle)
                for distance in [8, 12, 16]:
                    pos = Point2((
                        base.position.x + distance * math.cos(rad),
                        base.position.y + distance * math.sin(rad)
                    ))
                    if self.bot.in_map_bounds(pos):
                        self.target_creep_positions.append(pos)

        # 2. 확장 위치로 가는 경로
        if hasattr(self.bot, "expansion_locations_list"):
            main_base = self.bot.townhalls.first.position
            for exp_loc in list(self.bot.expansion_locations_list)[:5]:
                # 경로상 점막 위치 계산
                direction = exp_loc.direction_to(main_base)
                for i in range(1, 10):
                    pos = main_base.towards(exp_loc, i * 8)
                    if self.bot.in_map_bounds(pos):
                        self.target_creep_positions.append(pos)

        # 3. 맵 중앙
        map_center = self.bot.game_info.map_center
        for angle in [0, 45, 90, 135, 180, 225, 270, 315]:
            rad = math.radians(angle)
            for distance in [10, 15, 20]:
                pos = Point2((
                    map_center.x + distance * math.cos(rad),
                    map_center.y + distance * math.sin(rad)
                ))
                if self.bot.in_map_bounds(pos):
                    self.target_creep_positions.append(pos)

    async def _queen_creep_tumors(self):
        """Queen으로 점막 종양 생성"""
        queens = self.bot.units(UnitTypeId.QUEEN).filter(lambda q: q.energy >= 25)
        if not queens:
            return

        # 점막 종양 개수 제한 (최대 50개)
        current_tumors = self.bot.structures(UnitTypeId.CREEPTUMORBURROWED).amount
        if current_tumors >= 50:
            return

        for queen in queens:
            if not self.target_creep_positions:
                break

            # 가장 가까운 목표 위치
            closest_target = min(
                self.target_creep_positions,
                key=lambda p: queen.distance_to(p)
            )

            # 이미 점막이 있는 위치는 스킵
            if self.bot.has_creep(closest_target):
                self.target_creep_positions.remove(closest_target)
                continue

            # Queen이 목표 근처에 있으면 종양 생성
            if queen.distance_to(closest_target) < 10:
                abilities = await self.bot.get_available_abilities(queen)
                if AbilityId.BUILD_CREEPTUMOR_QUEEN in abilities:
                    self.bot.do(queen(AbilityId.BUILD_CREEPTUMOR_QUEEN, closest_target))
                    self.tumor_positions.add(closest_target)
                    self.tumors_created += 1
                    self.logger.info(f"[CREEP] Queen creep tumor at {closest_target}")
                    break

    async def _spread_creep_tumors(self):
        """점막 종양 확장"""
        tumors = self.bot.structures(UnitTypeId.CREEPTUMORBURROWED).ready
        if not tumors:
            return

        for tumor in tumors:
            if not self.target_creep_positions:
                break

            # 가장 가까운 목표 위치
            closest_target = min(
                self.target_creep_positions,
                key=lambda p: tumor.distance_to(p)
            )

            # 이미 점막이 있는 위치는 스킵
            if self.bot.has_creep(closest_target):
                self.target_creep_positions.remove(closest_target)
                continue

            # 종양이 목표 근처에 있으면 확장
            if tumor.distance_to(closest_target) < 10:
                abilities = await self.bot.get_available_abilities(tumor)
                if AbilityId.BUILD_CREEPTUMOR_TUMOR in abilities:
                    self.bot.do(tumor(AbilityId.BUILD_CREEPTUMOR_TUMOR, closest_target))
                    self.tumor_positions.add(closest_target)
                    self.tumors_created += 1
                    self.logger.info(f"[CREEP] Tumor spread to {closest_target}")
                    break

    def _update_statistics(self, game_time: float):
        """통계 업데이트"""
        # 맵 점막 커버리지 계산
        if hasattr(self.bot, "game_info"):
            map_size = self.bot.game_info.map_size
            total_area = map_size[0] * map_size[1]

            # 간단한 추정: 종양 1개당 약 50 타일 커버
            creep_area = self.tumors_created * 50
            self.map_coverage = min(100.0, (creep_area / total_area) * 100)

            self.logger.info(
                f"[CREEP] [{int(game_time)}s] Tumors: {self.tumors_created}, "
                f"Coverage: {self.map_coverage:.1f}%"
            )
