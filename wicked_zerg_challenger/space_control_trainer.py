# -*- coding: utf-8 -*-
"""
Space Control Trainer - 공간 확보 학습 시스템

파괴 가능한 구조물을 활용한 전략:
1. 확장 경로 개척 (바위/장애물 파괴)
2. 전략적 위치 확보
3. 적 우회로 차단
4. 크립 확장 경로 개척
"""

from typing import Dict, Set, List, Optional, Tuple
from sc2.position import Point2
from sc2.ids.unit_typeid import UnitTypeId
from utils.logger import get_logger


class DestructibleTarget:
    """파괴 목표 구조물"""

    def __init__(self, tag: int, position: Point2, priority: int):
        self.tag = tag
        self.position = position
        self.priority = priority  # 파괴 우선순위
        self.assigned_units = 0
        self.destruction_started = 0.0


class SpaceControlTrainer:
    """
    공간 확보 학습 시스템

    파괴 가능한 구조물을 전략적으로 파괴하여 공간 확보
    """

    def __init__(self, bot):
        self.bot = bot
        self.logger = get_logger("SpaceControl")

        # 파괴 목표 추적
        self.destructible_targets: Dict[int, DestructibleTarget] = {}
        self.destroyed_tags: Set[int] = set()

        # 우선순위 기준
        self.EXPANSION_PATH_PRIORITY = 100  # 확장 경로 최우선
        self.STRATEGIC_POSITION_PRIORITY = 80  # 전략적 위치
        self.CREEP_HIGHWAY_PRIORITY = 60  # 크립 확장
        self.GENERAL_PRIORITY = 40  # 일반

        # 설정
        self.MIN_WORKERS_FOR_DESTRUCTION = 3  # 파괴에 필요한 최소 일꾼
        self.MAX_WORKERS_PER_TARGET = 5  # 목표당 최대 일꾼
        self.DESTRUCTION_RANGE = 15.0  # 파괴 명령 거리

        # 통계
        self.total_destructibles_found = 0
        self.total_destructibles_destroyed = 0
        self.expansion_paths_cleared = 0

    async def on_step(self, iteration: int):
        """매 프레임 실행"""
        try:
            game_time = self.bot.time

            # 1. 파괴 가능 구조물 발견 (5초마다)
            if iteration % 110 == 0:
                self._discover_destructibles()

            # 2. 우선순위 계산 (10초마다)
            if iteration % 220 == 0:
                self._calculate_priorities()

            # 3. 일꾼 할당 및 파괴 (2초마다)
            if iteration % 44 == 0:
                await self._assign_workers_to_destroy()

            # 4. 파괴 완료 확인 (2초마다)
            if iteration % 44 == 0:
                self._check_destroyed()

            # 5. 통계 출력 (60초마다)
            if iteration % 1320 == 0 and self.total_destructibles_found > 0:
                self._print_statistics(game_time)

        except Exception as e:
            if iteration % 200 == 0:
                self.logger.error(f"[SPACE_CONTROL] Error: {e}")

    def _discover_destructibles(self):
        """파괴 가능한 구조물 발견"""
        if not hasattr(self.bot, "destructables"):
            return

        for destructible in self.bot.destructables:
            tag = destructible.tag

            # 이미 처리된 것은 스킵
            if tag in self.destructible_targets or tag in self.destroyed_tags:
                continue

            # 새로운 파괴 가능 구조물 발견
            position = destructible.position
            priority = self._calculate_initial_priority(position)

            self.destructible_targets[tag] = DestructibleTarget(
                tag=tag,
                position=position,
                priority=priority
            )

            self.total_destructibles_found += 1

            self.logger.info(
                f"[DISCOVERED] Destructible at {position} (Priority: {priority})"
            )

    def _calculate_initial_priority(self, position: Point2) -> int:
        """초기 우선순위 계산"""
        try:
            # 1. 확장 경로에 있는지 확인 (최우선)
            if self._is_on_expansion_path(position):
                return self.EXPANSION_PATH_PRIORITY

            # 2. 전략적 위치 확인
            if self._is_strategic_position(position):
                return self.STRATEGIC_POSITION_PRIORITY

            # 3. 크립 확장 경로 확인
            if self._is_on_creep_highway(position):
                return self.CREEP_HIGHWAY_PRIORITY

            # 4. 일반 우선순위
            return self.GENERAL_PRIORITY

        except Exception:
            return self.GENERAL_PRIORITY

    def _is_on_expansion_path(self, position: Point2) -> bool:
        """확장 경로에 있는지 확인"""
        try:
            if not hasattr(self.bot, "expansion_locations_list"):
                return False

            # 아군 본진 확인
            if not self.bot.townhalls.exists:
                return False

            main_base = self.bot.townhalls.first.position

            # 가장 가까운 3개 확장 위치 확인
            expansion_locs = list(self.bot.expansion_locations_list)[:3]

            for exp_loc in expansion_locs:
                # 확장 위치 근처 15 거리 이내
                if position.distance_to(exp_loc) < 15:
                    return True

                # 본진 → 확장 경로상에 있는지 확인
                distance_to_main = position.distance_to(main_base)
                distance_to_exp = position.distance_to(exp_loc)
                direct_distance = main_base.distance_to(exp_loc)

                # 경로상에 있으면 (삼각형 부등식)
                if distance_to_main + distance_to_exp < direct_distance + 5:
                    return True

            return False

        except Exception:
            return False

    def _is_strategic_position(self, position: Point2) -> bool:
        """전략적 위치인지 확인"""
        try:
            # 맵 중앙 근처
            if hasattr(self.bot, "game_info"):
                map_center = self.bot.game_info.map_center
                if position.distance_to(map_center) < 20:
                    return True

            # 적 본진 근처
            if hasattr(self.bot, "enemy_start_locations"):
                enemy_start = self.bot.enemy_start_locations[0]
                if position.distance_to(enemy_start) < 30:
                    return True

            return False

        except Exception:
            return False

    def _is_on_creep_highway(self, position: Point2) -> bool:
        """크립 확장 경로에 있는지 확인"""
        try:
            # 아군 기지들 확인
            if not self.bot.townhalls.exists:
                return False

            # 기지 간 연결 경로
            bases = list(self.bot.townhalls)
            if len(bases) >= 2:
                for i in range(len(bases) - 1):
                    base1 = bases[i].position
                    base2 = bases[i + 1].position

                    # 두 기지 사이 경로상에 있는지
                    dist1 = position.distance_to(base1)
                    dist2 = position.distance_to(base2)
                    direct = base1.distance_to(base2)

                    if dist1 + dist2 < direct + 5:
                        return True

            return False

        except Exception:
            return False

    def _calculate_priorities(self):
        """우선순위 재계산"""
        for target in self.destructible_targets.values():
            # 거리 가중치
            distance_weight = 1.0

            if self.bot.townhalls.exists:
                main_base = self.bot.townhalls.first.position
                distance = target.position.distance_to(main_base)

                # 가까울수록 높은 우선순위
                distance_weight = max(0.5, 1.5 - (distance / 100))

            # 최종 우선순위
            target.priority = int(target.priority * distance_weight)

    async def _assign_workers_to_destroy(self):
        """일꾼을 할당하여 파괴"""
        if not self.destructible_targets:
            return

        # 유휴 일꾼 확인
        idle_workers = self.bot.workers.idle

        if idle_workers.amount < self.MIN_WORKERS_FOR_DESTRUCTION:
            return

        # 우선순위 순으로 정렬
        sorted_targets = sorted(
            self.destructible_targets.values(),
            key=lambda t: t.priority,
            reverse=True
        )

        if not sorted_targets:
            return

        # 최고 우선순위 목표
        target = sorted_targets[0]

        # 근처 일꾼 찾기
        nearby_workers = idle_workers.closer_than(
            self.DESTRUCTION_RANGE,
            target.position
        )

        if nearby_workers:
            # 일꾼 할당 (최대 5명)
            workers_to_assign = nearby_workers.take(self.MAX_WORKERS_PER_TARGET)

            for worker in workers_to_assign:
                # Unit Authority 확인
                if hasattr(self.bot, "unit_authority") and self.bot.unit_authority:
                    from unit_authority_manager import AuthorityLevel
                    granted = self.bot.unit_authority.request_authority(
                        {worker.tag},
                        AuthorityLevel.ECONOMY,
                        "SpaceControl",
                        self.bot.state.game_loop
                    )

                    if worker.tag in granted:
                        self.bot.do(worker.attack(target.position))
                else:
                    self.bot.do(worker.attack(target.position))

            target.assigned_units = workers_to_assign.amount

            if target.destruction_started == 0:
                target.destruction_started = self.bot.time
                self.logger.info(
                    f"[DESTROYING] {workers_to_assign.amount} workers assigned to "
                    f"destructible at {target.position} (Priority: {target.priority})"
                )

    def _check_destroyed(self):
        """파괴 완료 확인"""
        if not hasattr(self.bot, "destructables"):
            return

        current_tags = {d.tag for d in self.bot.destructables}

        # 파괴된 구조물 찾기
        destroyed = []
        for tag in self.destructible_targets.keys():
            if tag not in current_tags:
                destroyed.append(tag)

        # 파괴 처리
        for tag in destroyed:
            target = self.destructible_targets[tag]
            self.destroyed_tags.add(tag)
            del self.destructible_targets[tag]

            self.total_destructibles_destroyed += 1

            # 확장 경로였으면 카운트
            if target.priority >= self.EXPANSION_PATH_PRIORITY:
                self.expansion_paths_cleared += 1

            self.logger.info(
                f"[DESTROYED] Destructible at {target.position} "
                f"({self.total_destructibles_destroyed}/{self.total_destructibles_found})"
            )

    def get_statistics(self) -> Dict:
        """통계 반환"""
        cleared_percent = 0
        if self.total_destructibles_found > 0:
            cleared_percent = (self.total_destructibles_destroyed /
                             self.total_destructibles_found * 100)

        return {
            "total_found": self.total_destructibles_found,
            "total_destroyed": self.total_destructibles_destroyed,
            "remaining": len(self.destructible_targets),
            "cleared_percent": f"{cleared_percent:.1f}%",
            "expansion_paths": self.expansion_paths_cleared
        }

    def _print_statistics(self, game_time: float):
        """통계 출력"""
        stats = self.get_statistics()

        self.logger.info(
            f"[SPACE_CONTROL] [{int(game_time)}s] "
            f"Cleared: {stats['total_destroyed']}/{stats['total_found']} "
            f"({stats['cleared_percent']}), "
            f"Expansion Paths: {stats['expansion_paths']}"
        )
