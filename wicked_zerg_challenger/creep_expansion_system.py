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

        # ★ Phase 45: 점막 목표 우선순위/안전 제약 ★
        self.target_batch_size = 80
        self.enemy_avoid_radius = 14.0

        # ★ Phase 46: 경로 점수 기반 목표 선택 ★
        self.path_step_distance = 7.0
        self.expansion_lane_weight = 0.55
        self.center_lane_weight = 0.30
        self.safety_weight = 0.15

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

        # ★ Phase 45: 중복 제거 + 우선순위 정렬(안전/확장 효율 기반) ★
        self.target_creep_positions = self._prioritize_targets(self.target_creep_positions)

    def _prioritize_targets(self, positions: List[Point2]) -> List[Point2]:
        """Deduplicate and prioritize creep targets for safer/faster spread."""
        if not positions:
            return []

        # 격자 단위로 중복 제거
        unique: Dict[tuple, Point2] = {}
        for p in positions:
            key = (int(p.x), int(p.y))
            if key not in unique:
                unique[key] = p

        candidates = list(unique.values())

        # 적 시작 위치를 기준으로 너무 위험한 지점 제외
        enemy_start = None
        if hasattr(self.bot, "enemy_start_locations") and self.bot.enemy_start_locations:
            enemy_start = self.bot.enemy_start_locations[0]

        safe_candidates: List[Point2] = []
        for p in candidates:
            if enemy_start and p.distance_to(enemy_start) < self.enemy_avoid_radius and self.bot.time < 420:
                continue
            safe_candidates.append(p)

        if not safe_candidates:
            safe_candidates = candidates

        anchor = self.bot.townhalls.first.position if self.bot.townhalls.exists else self.bot.start_location
        map_center = self.bot.game_info.map_center
        expansion_points = list(getattr(self.bot, "expansion_locations_list", []))

        # ★ Phase 46: 확장 경로/중앙 진출/안전도 기반 점수로 정렬 ★
        safe_candidates.sort(
            key=lambda p: self._score_target(
                anchor=anchor,
                target=p,
                expansion_points=expansion_points,
                map_center=map_center,
                enemy_start=enemy_start,
            ),
            reverse=True,
        )

        return safe_candidates[: self.target_batch_size]

    def _score_target(
        self,
        anchor: Point2,
        target: Point2,
        expansion_points: List[Point2],
        map_center: Point2,
        enemy_start: Point2 | None,
    ) -> float:
        """크립 목표의 확장 경로 적합도/중앙 압박/안전도를 합산 점수화한다."""
        # 확장 멀티 라인 근접도 (가까울수록 높음)
        exp_dist = 50.0
        if expansion_points:
            exp_dist = min(target.distance_to(exp) for exp in expansion_points)
        expansion_lane_score = 1.0 / (1.0 + exp_dist / 18.0)

        # 맵 중앙 진출도 (본진에서 중앙 방향으로 진행될수록 가점)
        anchor_to_center = max(1.0, anchor.distance_to(map_center))
        center_progress = min(1.0, anchor.distance_to(target) / anchor_to_center)
        center_lane_score = center_progress

        # 안전도 (초중반엔 적 시작점과 거리 확보)
        safety_score = 1.0
        if enemy_start is not None and self.bot.time < 480:
            enemy_dist = target.distance_to(enemy_start)
            safety_score = min(1.0, enemy_dist / max(1.0, self.enemy_avoid_radius * 2.0))

        return (
            expansion_lane_score * self.expansion_lane_weight
            + center_lane_score * self.center_lane_weight
            + safety_score * self.safety_weight
        )

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
