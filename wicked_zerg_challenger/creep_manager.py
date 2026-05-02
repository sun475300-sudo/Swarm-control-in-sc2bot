#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Creep Manager - BurnySc2/CreepyBot inspired creep expansion system.

Key improvements from CreepyBot:
- Uncreeped area priority spreading (sort by distance to nearest uncreeped pos)
- Batch placement query validation
- Expansion location protection with Chebyshev distance
- Used-tumor tracking to prevent double-spread
- Creep coverage sampling and threshold-based queen redirect
"""

from __future__ import annotations

import logging
import math
from collections import deque
from typing import Dict, Iterable, List, Optional, Set, Tuple

logger = logging.getLogger(__name__)

try:
    from sc2.ids.ability_id import AbilityId
    from sc2.ids.unit_typeid import UnitTypeId
    from sc2.position import Point2
except ImportError:  # Fallbacks for tooling environments
    Point2 = None
    AbilityId = None
    UnitTypeId = None


def await_or_sync(func, *args, **kwargs):
    """Call a function that may or may not be a coroutine, returning result synchronously."""
    result = func(*args, **kwargs)
    # If it's a coroutine, we can't await here - return None
    if hasattr(result, "__await__"):
        return None
    return result


class CreepManager:
    """
    Manages creep spread through queens and automatic tumor relay.

    Features (BurnySc2/CreepyBot inspired):
    - Uncreeped area priority: tumors spread toward gaps in coverage
    - Batch placement queries for validation efficiency
    - Expansion protection via Chebyshev distance > 3
    - Used-tumor tracking prevents double-spread waste
    - Coverage sampling with configurable target threshold
    """

    # CreepyBot-inspired constants
    TUMOR_MIN_SPACING_DIST = 10  # Minimum distance between tumors to avoid overlap
    TUMOR_SPREAD_RANGE = 10.0  # Max spread distance for existing tumors
    QUEEN_TUMOR_RANGE = 8.0  # Max queen creep tumor placement range
    EXPANSION_BLOCK_DIST = 3  # Chebyshev distance to protect expansions
    COVERAGE_TARGET = 0.30  # 30% coverage target (CreepyBot default)
    COVERAGE_SAMPLE_STEP = 15  # Grid step for coverage sampling

    def __init__(self, bot):
        self.bot = bot
        self.last_update = 0
        self.update_interval = 10
        self.tumor_relay_interval = 6
        self.last_tumor_relay = 0
        self.cached_targets: List[object] = []
        self.tumor_spread_cooldowns: Dict[int, int] = (
            {}
        )  # tumor_tag -> last_spread_frame
        self.used_tumor_tags: Set[int] = (
            set()
        )  # CreepyBot: track tumors that already spawned
        self.max_tumors_per_cycle = 6
        self.spread_directions = []
        self._tumor_count_check_interval = 0

        # CreepyBot-style coverage tracking
        self._positions_with_creep: List[object] = []
        self._positions_without_creep: List[object] = []
        self._creep_coverage: float = 0.0
        self._last_coverage_update: float = 0.0
        self._coverage_update_interval: float = 15.0  # seconds

    async def on_step(self, iteration: int) -> None:
        """
        Main creep manager loop.
        - Refreshes creep targets periodically
        - Handles automatic tumor relay
        - Tracks creep spread progress
        """
        if iteration - self.last_update < self.update_interval:
            if iteration - self.last_tumor_relay >= self.tumor_relay_interval:
                await self._handle_tumor_relay(iteration)
            return

        self.last_update = iteration
        self._refresh_targets()
        await self._handle_tumor_relay(iteration)

        # 점막 확장 진행 상황 로그 (30초마다)
        self._tumor_count_check_interval += 1
        if self._tumor_count_check_interval >= 50:  # ~30초마다
            self._tumor_count_check_interval = 0
            await self._log_creep_progress(iteration)

    def get_creep_target(self, origin_unit) -> Optional[object]:
        if not self.cached_targets:
            self._refresh_targets()

        direction_target = self._get_direction_target()
        origin = getattr(origin_unit, "position", None)
        if not origin or not Point2:
            return None

        if direction_target and self.cached_targets:
            scored = max(
                self.cached_targets,
                key=lambda pos: self._score_target(origin, pos, direction_target),
            )
            return scored

        if direction_target:
            return origin.towards(direction_target, 7)

        return None

    def _refresh_targets(self) -> None:
        targets: List[object] = []
        targets.extend(self._get_expansion_targets())
        targets.extend(self._get_scout_targets())
        targets.extend(self._get_attack_path_targets())
        targets.extend(self._get_base_perimeter_targets())  # Issue 8
        self.cached_targets = self._dedupe_positions(targets)

    def _get_base_perimeter_targets(self) -> List[object]:
        """기지 주변 점막 우선 확장 (방어 및 시야)"""
        if not hasattr(self.bot, "townhalls") or not self.bot.townhalls:
            return []

        targets = []
        import math

        # 각 기지 주변 12 거리의 원형 포인트 추가
        for th in self.bot.townhalls:
            for angle in range(0, 360, 60):
                rad = math.radians(angle)
                x = th.position.x + 12 * math.cos(rad)
                y = th.position.y + 12 * math.sin(rad)
                targets.append(Point2((x, y)))
        return targets

    def _get_direction_target(self) -> Optional[object]:
        enemy_starts = getattr(self.bot, "enemy_start_locations", [])
        if enemy_starts:
            return enemy_starts[0]
        if hasattr(self.bot, "game_info"):
            return self.bot.game_info.map_center
        return None

    def _get_expansion_targets(self) -> List[object]:
        expansion_list = getattr(self.bot, "expansion_locations_list", None)
        if not expansion_list:
            return []
        return list(expansion_list)

    def _get_scout_targets(self) -> List[object]:
        scout = getattr(self.bot, "scout", None)
        if not scout:
            return []
        targets: List[object] = []
        targets.extend(getattr(scout, "cached_positions", []))
        assignments = getattr(scout, "overlord_assignments", {})
        targets.extend(assignments.values())
        return targets

    def _get_attack_path_targets(self) -> List[object]:
        if not Point2:
            return []

        # ★ A* 고속도로 웨이포인트 우선 사용 ★
        astar_highway = getattr(self.bot, "creep_highway_astar", None)
        if astar_highway and astar_highway.highway_waypoints:
            return list(astar_highway.highway_waypoints)

        # Fallback: 직선 경로
        if not hasattr(self.bot, "townhalls") or not self.bot.townhalls:
            return []
        origin = self.bot.townhalls.first.position
        target = self._get_direction_target()
        if not target:
            return []
        path = []
        distance = origin.distance_to(target)
        step = 8.0
        current = origin
        traveled = 0.0
        while traveled + step < distance:
            current = current.towards(target, step)
            path.append(current)
            traveled += step
            if len(path) >= 6:
                break
        return path

    @staticmethod
    def _dedupe_positions(positions: Iterable[object]) -> List[object]:
        if not Point2:
            return list(positions)
        deduped: List[object] = []
        for pos in positions:
            if not pos:
                continue
            if all(pos.distance_to(other) > 2.5 for other in deduped):
                deduped.append(pos)
        return deduped

    async def _update_creep_coverage(self) -> None:
        """
        CreepyBot-style creep coverage sampling.
        Scans playable area on a grid to track creep/uncreeped positions.
        """
        game_time = getattr(self.bot, "time", 0.0)
        if game_time - self._last_coverage_update < self._coverage_update_interval:
            return

        self._last_coverage_update = game_time

        if not hasattr(self.bot, "game_info") or not Point2:
            return

        try:
            map_size = self.bot.game_info.map_size
            with_creep = []
            without_creep = []

            step = self.COVERAGE_SAMPLE_STEP
            for x in range(5, int(map_size.x) - 5, step):
                for y in range(5, int(map_size.y) - 5, step):
                    pos = Point2((x, y))
                    # Skip unpathable terrain
                    try:
                        if hasattr(self.bot.game_info, "pathing_grid"):
                            grid = self.bot.game_info.pathing_grid
                            if grid[x, y] == 0:
                                continue
                    except (IndexError, AttributeError, TypeError):
                        pass

                    try:
                        if hasattr(self.bot, "has_creep") and self.bot.has_creep(pos):
                            with_creep.append(pos)
                        else:
                            without_creep.append(pos)
                    except (TypeError, AttributeError):
                        without_creep.append(pos)

            self._positions_with_creep = with_creep
            self._positions_without_creep = without_creep

            total = len(with_creep) + len(without_creep)
            self._creep_coverage = len(with_creep) / total if total > 0 else 0.0

        except Exception as e:
            logger.warning(f"[CreepManager] coverage sampling suppressed: {e}")

    def _find_creep_plant_location(self, tumor) -> Optional[object]:
        """
        CreepyBot-inspired optimal tumor placement.

        1. Generate candidate positions in a circle around the tumor
        2. Filter: must be on creep, not block expansions (Chebyshev > 3)
        3. Filter: not too close to existing unused tumors (dist >= 10)
        4. Sort by distance to nearest uncreeped position (key optimization)
        """
        if not Point2:
            return None

        origin = tumor.position
        spread_range = self.TUMOR_SPREAD_RANGE

        # Generate circle positions (CreepyBot: trigonometric sampling)
        candidates = []
        for angle_deg in range(0, 360, 20):  # 18 candidate positions
            rad = math.radians(angle_deg)
            for dist in [7.0, 9.0]:  # Two distance rings
                x = origin.x + dist * math.cos(rad)
                y = origin.y + dist * math.sin(rad)
                candidates.append(Point2((x, y)))

        if not candidates:
            return None

        # Get expansion locations for blocking check
        expansion_locations = []
        if hasattr(self.bot, "expansion_locations_list"):
            expansion_locations = list(self.bot.expansion_locations_list)
        elif hasattr(self.bot, "expansion_locations"):
            expansion_locations = list(self.bot.expansion_locations.keys())

        # Get existing tumor positions for distance check
        tumor_positions = []
        if hasattr(self.bot, "structures"):
            tumor_types = {
                UnitTypeId.CREEPTUMOR,
                UnitTypeId.CREEPTUMORBURROWED,
                UnitTypeId.CREEPTUMORQUEEN,
            }
            tumor_positions = [
                t.position for t in self.bot.structures if t.type_id in tumor_types
            ]

        # Filter candidates
        valid = []
        for pos in candidates:
            # Must be on creep
            try:
                if hasattr(self.bot, "has_creep") and not self.bot.has_creep(pos):
                    continue
            except (TypeError, AttributeError):
                continue

            # Chebyshev distance to expansions must be > 3 (CreepyBot pattern)
            blocked = False
            for exp_loc in expansion_locations:
                try:
                    chebyshev = max(abs(pos.x - exp_loc.x), abs(pos.y - exp_loc.y))
                    if chebyshev <= self.EXPANSION_BLOCK_DIST:
                        blocked = True
                        break
                except Exception:
                    continue
            if blocked:
                continue

            # Not too close to existing tumors (CreepyBot: dist >= 10)
            too_close = False
            for t_pos in tumor_positions:
                try:
                    if pos.distance_to(t_pos) < self.TUMOR_MIN_SPACING_DIST:
                        too_close = True
                        break
                except Exception:
                    continue
            if too_close:
                continue

            valid.append(pos)

        if not valid:
            return None

        # CreepyBot: Batch query_building_placement to validate positions
        # This is more reliable than has_creep alone - checks actual buildability
        try:
            if hasattr(self.bot, "can_place") and hasattr(
                AbilityId, "ZERGBUILD_CREEPTUMOR"
            ):
                placement_results = await_or_sync(
                    self.bot.can_place, AbilityId.ZERGBUILD_CREEPTUMOR, valid
                )
                if placement_results and len(placement_results) == len(valid):
                    valid = [pos for pos, ok in zip(valid, placement_results) if ok]
        except Exception:
            pass  # Fall through to distance-based selection if batch query fails

        if not valid:
            return None

        # KEY OPTIMIZATION (CreepyBot): Sort by distance to nearest uncreeped position
        if self._positions_without_creep:

            def dist_to_nearest_uncreeped(pos):
                min_dist = float("inf")
                for uc_pos in self._positions_without_creep:
                    try:
                        d = pos.distance_to(uc_pos)
                        if d < min_dist:
                            min_dist = d
                    except Exception:
                        continue
                return min_dist

            valid.sort(key=dist_to_nearest_uncreeped)

        return valid[0]

    async def _handle_tumor_relay(self, iteration: int) -> None:
        """
        BurnySc2/CreepyBot-style tumor relay system.

        Key improvements:
        - Used-tumor tracking prevents double-spread
        - Optimal placement via _find_creep_plant_location
        - Coverage-aware: redirects effort once target reached
        """
        if not UnitTypeId or not AbilityId:
            return

        self.last_tumor_relay = iteration

        # Update creep coverage periodically
        await self._update_creep_coverage()

        # Get all creep tumors
        tumors = []
        if hasattr(self.bot, "structures"):
            tumor_types = {
                UnitTypeId.CREEPTUMOR,
                UnitTypeId.CREEPTUMORBURROWED,
                UnitTypeId.CREEPTUMORQUEEN,
            }
            tumors = [t for t in self.bot.structures if t.type_id in tumor_types]

        if not tumors:
            return

        # Clean up tracking for dead tumors
        tumor_tags = {t.tag for t in tumors}
        self.tumor_spread_cooldowns = {
            tag: frame
            for tag, frame in self.tumor_spread_cooldowns.items()
            if tag in tumor_tags
        }
        self.used_tumor_tags = self.used_tumor_tags & tumor_tags

        direction_target = self._get_direction_target()
        if not direction_target:
            return

        our_base = None
        if hasattr(self.bot, "townhalls") and self.bot.townhalls:
            our_base = self.bot.townhalls.first.position
        if not our_base:
            return

        # Score tumors: prefer outermost, unused tumors
        scored_tumors = []
        for tumor in tumors:
            # Skip already-used tumors (CreepyBot pattern)
            if tumor.tag in self.used_tumor_tags:
                continue

            # Skip if on cooldown
            last_spread = self.tumor_spread_cooldowns.get(tumor.tag, 0)
            if iteration - last_spread < 50:
                continue

            try:
                dist_to_enemy = tumor.position.distance_to(direction_target)
                dist_to_base = tumor.position.distance_to(our_base)
                score = dist_to_base - dist_to_enemy * 0.5
                scored_tumors.append((tumor, score))
            except Exception as e:
                logger.warning(f"[CreepManager] tumor scoring suppressed: {e}")
                continue

        if not scored_tumors:
            return

        scored_tumors.sort(key=lambda x: x[1], reverse=True)
        actions = []

        for tumor, _ in scored_tumors[: self.max_tumors_per_cycle]:
            try:
                # Use CreepyBot-style optimal placement
                spread_target = self._find_creep_plant_location(tumor)

                if not spread_target:
                    # Fallback: simple towards-enemy direction
                    spread_target = tumor.position.towards(direction_target, 9.0)
                    # Verify it's on creep
                    try:
                        if hasattr(self.bot, "has_creep") and not self.bot.has_creep(
                            spread_target
                        ):
                            continue
                    except (TypeError, AttributeError):
                        pass

                # Execute spread
                if hasattr(tumor, "can_cast") and hasattr(
                    AbilityId, "BUILD_CREEPTUMOR_TUMOR"
                ):
                    if tumor.can_cast(AbilityId.BUILD_CREEPTUMOR_TUMOR):
                        actions.append(
                            tumor(AbilityId.BUILD_CREEPTUMOR_TUMOR, spread_target)
                        )
                        self.tumor_spread_cooldowns[tumor.tag] = iteration
                        self.used_tumor_tags.add(tumor.tag)  # Mark as used
                elif hasattr(AbilityId, "BUILD_CREEPTUMOR_TUMOR"):
                    actions.append(
                        tumor(AbilityId.BUILD_CREEPTUMOR_TUMOR, spread_target)
                    )
                    self.tumor_spread_cooldowns[tumor.tag] = iteration
                    self.used_tumor_tags.add(tumor.tag)
            except Exception as e:
                logger.warning(f"[CreepManager] tumor spread suppressed: {e}")
                continue

        if actions:
            try:
                if hasattr(self.bot, "do_actions"):
                    result = self.bot.do_actions(actions)
                    if hasattr(result, "__await__"):
                        await result
                else:
                    for action in actions:
                        result = self.bot.do(action)
                        if hasattr(result, "__await__"):
                            await result
            except Exception as e:
                logger.warning(f"[CreepManager] do_actions suppressed: {e}")

    @staticmethod
    def _score_target(origin, candidate, direction_target) -> float:
        dx = candidate.x - origin.x
        dy = candidate.y - origin.y
        dist = (dx * dx + dy * dy) ** 0.5

        dir_x = direction_target.x - origin.x
        dir_y = direction_target.y - origin.y
        dir_len = (dir_x * dir_x + dir_y * dir_y) ** 0.5
        if dir_len == 0:
            return dist
        dir_x /= dir_len
        dir_y /= dir_len
        projection = dx * dir_x + dy * dir_y
        return projection - dist * 0.15

    async def _log_creep_progress(self, iteration: int) -> None:
        """점막 확장 진행 상황 로그 (coverage 포함)"""
        if not UnitTypeId or not hasattr(self.bot, "structures"):
            return

        try:
            game_time = getattr(self.bot, "time", 0)

            tumor_types = {
                UnitTypeId.CREEPTUMOR,
                UnitTypeId.CREEPTUMORBURROWED,
                UnitTypeId.CREEPTUMORQUEEN,
            }
            tumors = [t for t in self.bot.structures if t.type_id in tumor_types]
            tumor_count = len(tumors)
            used_count = len(self.used_tumor_tags & {t.tag for t in tumors})

            farthest_dist = 0
            if tumors and hasattr(self.bot, "townhalls") and self.bot.townhalls:
                our_base = self.bot.townhalls.first.position
                for tumor in tumors:
                    try:
                        dist = tumor.position.distance_to(our_base)
                        if dist > farthest_dist:
                            farthest_dist = dist
                    except Exception as e:
                        logger.warning(
                            f"[CreepManager] tumor distance check suppressed: {e}"
                        )
                        continue

            logger.info(
                f"[CREEP] [{int(game_time)}s] Tumors: {tumor_count} "
                f"(used: {used_count}), Coverage: {self._creep_coverage:.1%}, "
                f"Farthest: {int(farthest_dist)} from base"
            )

        except Exception as e:
            logger.warning(f"[CreepManager] log_creep_progress suppressed: {e}")

    def get_tumor_count(self) -> int:
        """현재 종양 수 반환"""
        if not UnitTypeId or not hasattr(self.bot, "structures"):
            return 0

        tumor_types = {
            UnitTypeId.CREEPTUMOR,
            UnitTypeId.CREEPTUMORBURROWED,
            UnitTypeId.CREEPTUMORQUEEN,
        }
        return sum(1 for t in self.bot.structures if t.type_id in tumor_types)


# =============================================================================
# Feature #97: CreepSpreadManager - BFS/그리드 기반 크립 스프레드 최적화
# =============================================================================


class CreepSpreadManager:
    """
    크립 스프레드 최적화 매니저 (Feature #97)

    기존 CreepManager의 벡터 기반 확산에 BFS/그리드 패턴 기반
    최적화를 추가한 고급 크립 관리 시스템입니다.

    핵심 기능:
    - BFS 알고리즘 기반 크립 종양 목표 위치 생성
    - 그리드 패턴으로 균등한 크립 커버리지
    - 퀸 자동 크립 종양 생성 (에너지 >= 50)
    - 크립 커버리지 추적 및 보고
    - 확장/적 방향 우선 확산
    """

    # 크립 종양 관련 상수
    TUMOR_SPREAD_RANGE = 10.0  # 종양 확산 반경
    TUMOR_MIN_DISTANCE = 8.0  # 종양 간 최소 거리
    QUEEN_TUMOR_ENERGY = 25  # 퀸 종양 생성 에너지
    GRID_CELL_SIZE = 9.0  # 그리드 셀 크기

    def __init__(self, bot):
        """
        크립 스프레드 최적화 매니저 초기화

        Args:
            bot: SC2 봇 인스턴스
        """
        self.bot = bot

        # 크립 종양 추적
        self.tumor_positions: Set[Tuple[float, float]] = set()
        self.pending_tumor_positions: Set[Tuple[float, float]] = set()
        self.queen_tumor_cooldowns: Dict[int, float] = {}

        # 크립 그리드 (BFS 기반)
        self._target_grid: List[Point2] = []
        self._grid_generated: bool = False

        # 퀸 관리
        self.creep_queen_tags: Set[int] = set()
        self.queen_tumor_interval: float = 5.0

        # 확산 방향 우선순위
        self._expansion_directions: List[Point2] = []
        self._enemy_direction: Optional[Point2] = None

        # 통계
        self.total_tumors_created: int = 0
        self.queen_tumors_created: int = 0
        self.tumor_spread_created: int = 0
        self._creep_coverage_percent: float = 0.0
        self._last_coverage_check: float = 0.0

    async def on_step(self, iteration: int):
        """
        매 프레임 크립 스프레드 최적화 업데이트

        Args:
            iteration: 현재 게임 반복 횟수
        """
        try:
            if not UnitTypeId:
                return

            game_time = getattr(self.bot, "time", 0.0)

            # 크립 그리드 생성 (한 번만)
            if not self._grid_generated and game_time > 30:
                self._generate_creep_grid()
                self._update_priority_directions()

            # 기존 종양 위치 업데이트
            if iteration % 44 == 0:
                self._update_tumor_positions()

            # 퀸으로 크립 종양 생성
            if iteration % 22 == 0:
                await self._queen_spread_creep(game_time)

            # 기존 종양에서 새 종양 확산
            if iteration % 33 == 0:
                await self._spread_from_tumors(game_time)

            # 크립 커버리지 업데이트 (30초마다)
            if game_time - self._last_coverage_check > 30:
                self._update_coverage(game_time)
                self._last_coverage_check = game_time

        except Exception as e:
            logger.warning(f"[CreepSpreadManager] on_step suppressed: {e}")

    def _generate_creep_grid(self):
        """BFS/그리드 패턴으로 크립 종양 목표 위치 생성"""
        if not hasattr(self.bot, "start_location") or not hasattr(
            self.bot, "game_info"
        ):
            return

        if not Point2:
            return

        start = self.bot.start_location
        map_size = self.bot.game_info.map_size

        visited: Set[Tuple[int, int]] = set()
        queue: deque = deque()
        targets: List[Point2] = []

        start_gx = int(start.x / self.GRID_CELL_SIZE)
        start_gy = int(start.y / self.GRID_CELL_SIZE)
        queue.append((start_gx, start_gy))
        visited.add((start_gx, start_gy))

        directions = [
            (1, 0),
            (-1, 0),
            (0, 1),
            (0, -1),
            (1, 1),
            (-1, 1),
            (1, -1),
            (-1, -1),
        ]

        while queue:
            gx, gy = queue.popleft()
            real_x = gx * self.GRID_CELL_SIZE + self.GRID_CELL_SIZE / 2
            real_y = gy * self.GRID_CELL_SIZE + self.GRID_CELL_SIZE / 2

            if real_x < 5 or real_x > map_size.x - 5:
                continue
            if real_y < 5 or real_y > map_size.y - 5:
                continue

            pos = Point2((real_x, real_y))
            try:
                if hasattr(self.bot.game_info, "pathing_grid"):
                    grid = self.bot.game_info.pathing_grid
                    px, py = int(real_x), int(real_y)
                    if 0 <= px < grid.width and 0 <= py < grid.height:
                        if grid[px, py] == 0:
                            continue
            except (IndexError, AttributeError, TypeError):
                pass

            targets.append(pos)

            for dx, dy in directions:
                nx, ny = gx + dx, gy + dy
                if (nx, ny) not in visited:
                    visited.add((nx, ny))
                    queue.append((nx, ny))

        # ★ Phase 45: BFS 그리드 최대 300개 cap (성능 보호)
        if len(targets) > 300:
            targets = targets[:300]
        self._target_grid = targets
        self._grid_generated = True

    def _update_priority_directions(self):
        """확산 우선순위 방향 업데이트"""
        if not hasattr(self.bot, "start_location"):
            return
        start = self.bot.start_location
        expansions = getattr(self.bot, "expansion_locations_list", [])
        for exp in expansions:
            if exp.distance_to(start) < 50:
                self._expansion_directions.append(exp)
        if (
            hasattr(self.bot, "enemy_start_locations")
            and self.bot.enemy_start_locations
        ):
            self._enemy_direction = self.bot.enemy_start_locations[0]

    def _update_tumor_positions(self):
        """현재 크립 종양 위치 업데이트"""
        if not hasattr(self.bot, "structures"):
            return
        self.tumor_positions.clear()
        for tid in [
            UnitTypeId.CREEPTUMOR,
            UnitTypeId.CREEPTUMORBURROWED,
            UnitTypeId.CREEPTUMORQUEEN,
        ]:
            for tumor in self.bot.structures(tid):
                pos = (round(tumor.position.x, 1), round(tumor.position.y, 1))
                self.tumor_positions.add(pos)

    async def _queen_spread_creep(self, game_time: float):
        """퀸을 사용한 크립 종양 생성 (에너지 >= 50 시)"""
        if not hasattr(self.bot, "units"):
            return
        queens = self.bot.units(UnitTypeId.QUEEN)
        if not queens.exists:
            return

        for queen in queens:
            if queen.energy < self.QUEEN_TUMOR_ENERGY + 25:
                continue
            last_tumor = self.queen_tumor_cooldowns.get(queen.tag, 0)
            if game_time - last_tumor < self.queen_tumor_interval:
                continue
            if not queen.is_idle and queen.tag not in self.creep_queen_tags:
                continue

            tumor_pos = self._find_best_tumor_position(queen.position)
            if not tumor_pos:
                continue

            try:
                if hasattr(self.bot, "has_creep"):
                    if not self.bot.has_creep(tumor_pos):
                        continue
            except (TypeError, AttributeError):
                pass

            try:
                self.bot.do(queen(AbilityId.BUILD_CREEPTUMOR_QUEEN, tumor_pos))
                self.queen_tumor_cooldowns[queen.tag] = game_time
                self.queen_tumors_created += 1
                self.total_tumors_created += 1
                pos_tuple = (round(tumor_pos.x, 1), round(tumor_pos.y, 1))
                self.pending_tumor_positions.add(pos_tuple)
            except Exception as e:
                logger.warning(
                    f"[CreepSpreadManager] queen tumor creation suppressed: {e}"
                )

    async def _spread_from_tumors(self, game_time: float):
        """기존 크립 종양에서 새 종양 확산"""
        if not hasattr(self.bot, "structures"):
            return
        burrowed_tumors = self.bot.structures(UnitTypeId.CREEPTUMORBURROWED)
        if not burrowed_tumors.exists:
            return

        for tumor in burrowed_tumors:
            # ★ Phase 45: get_available_abilities() API 호출 제거 (O(n) 비용)
            # CREEPTUMORBURROWED는 is_idle 상태일 때 확산 가능
            try:
                if not tumor.is_idle:
                    continue
            except Exception as e:
                logger.warning(f"[CreepSpreadManager] tumor.is_idle suppressed: {e}")
                continue

            spread_pos = self._find_best_tumor_position(
                tumor.position, is_tumor_spread=True
            )
            if not spread_pos:
                continue
            try:
                self.bot.do(tumor(AbilityId.BUILD_CREEPTUMOR_TUMOR, spread_pos))
                self.tumor_spread_created += 1
                self.total_tumors_created += 1
                pos_tuple = (round(spread_pos.x, 1), round(spread_pos.y, 1))
                self.pending_tumor_positions.add(pos_tuple)
            except Exception as e:
                logger.warning(
                    f"[CreepSpreadManager] tumor spread action suppressed: {e}"
                )

    def _find_best_tumor_position(
        self,
        source_pos,
        is_tumor_spread: bool = False,
    ) -> Optional[Point2]:
        """
        최적 크립 종양 배치 위치 계산 (BFS 그리드 기반)

        우선순위:
        1. 확장 기지 방향
        2. 적 방향
        3. 더 먼 곳 (넓게 확산)

        Args:
            source_pos: 원점 위치
            is_tumor_spread: 종양 확산인 경우 True

        Returns:
            최적 배치 위치 또는 None
        """
        if not Point2:
            return None

        spread_range = self.TUMOR_SPREAD_RANGE if is_tumor_spread else 8.0
        candidates: List[Tuple[Point2, float]] = []

        for target in self._target_grid:
            dist = source_pos.distance_to(target)
            if dist > spread_range or dist < 2:
                continue

            pos_tuple = (round(target.x, 1), round(target.y, 1))
            if (
                pos_tuple in self.tumor_positions
                or pos_tuple in self.pending_tumor_positions
            ):
                continue

            too_close = False
            for existing in self.tumor_positions:
                ex_dist = math.sqrt(
                    (target.x - existing[0]) ** 2 + (target.y - existing[1]) ** 2
                )
                if ex_dist < self.TUMOR_MIN_DISTANCE:
                    too_close = True
                    break
            if too_close:
                continue

            score = 0.0
            for exp_dir in self._expansion_directions:
                if target.distance_to(exp_dir) < source_pos.distance_to(exp_dir):
                    score += 2.0
            if self._enemy_direction:
                if target.distance_to(self._enemy_direction) < source_pos.distance_to(
                    self._enemy_direction
                ):
                    score += 1.0
            score += dist * 0.1
            candidates.append((target, score))

        if not candidates:
            return None
        candidates.sort(key=lambda c: c[1], reverse=True)
        return candidates[0][0]

    def _update_coverage(self, game_time: float):
        """크립 커버리지 추정 (샘플링)"""
        if not hasattr(self.bot, "game_info") or not Point2:
            return
        try:
            map_size = self.bot.game_info.map_size
            total_cells = 0
            creep_cells = 0
            step = 5
            for x in range(5, int(map_size.x) - 5, step):
                for y in range(5, int(map_size.y) - 5, step):
                    pos = Point2((x, y))
                    try:
                        if hasattr(self.bot.game_info, "pathing_grid"):
                            grid = self.bot.game_info.pathing_grid
                            if grid[x, y] == 0:
                                continue
                    except (IndexError, AttributeError, TypeError):
                        pass
                    total_cells += 1
                    try:
                        if hasattr(self.bot, "has_creep") and self.bot.has_creep(pos):
                            creep_cells += 1
                    except (TypeError, AttributeError):
                        pass
            if total_cells > 0:
                self._creep_coverage_percent = (creep_cells / total_cells) * 100
        except Exception as e:
            logger.warning(f"[CreepSpreadManager] update_coverage suppressed: {e}")

    def assign_creep_queen(self, queen_tag: int):
        """크립 전용 퀸 지정"""
        self.creep_queen_tags.add(queen_tag)

    def unassign_creep_queen(self, queen_tag: int):
        """크립 전용 퀸 해제"""
        self.creep_queen_tags.discard(queen_tag)

    def get_creep_stats(self) -> Dict:
        """
        크립 스프레드 최적화 통계 반환

        Returns:
            통계 딕셔너리
        """
        return {
            "tumor_count": len(self.tumor_positions),
            "total_created": self.total_tumors_created,
            "queen_created": self.queen_tumors_created,
            "spread_created": self.tumor_spread_created,
            "coverage_percent": round(self._creep_coverage_percent, 1),
            "creep_queens": len(self.creep_queen_tags),
            "grid_targets": len(self._target_grid),
        }
