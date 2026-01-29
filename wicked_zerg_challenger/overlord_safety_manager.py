# -*- coding: utf-8 -*-
"""
Overlord Safety Manager - 대군주 안전 관리 시스템

대군주를 안전하게 배치하고 생존성을 높임:
1. 안전한 고지대(Pillar) 및 시야 포인트 식별
2. 대공 위협 감지 및 자동 후퇴
3. 맵 전역 감시를 위한 분산 배치
"""

from typing import List, Dict, Optional, Set, Tuple
from sc2.position import Point2
from sc2.ids.unit_typeid import UnitTypeId
from utils.logger import get_logger
import random

class OverlordSafetyManager:
    """
    대군주 안전 관리자
    """

    def __init__(self, bot):
        self.bot = bot
        self.logger = get_logger("OverlordSafety")
        
        # 안전한 위치 (Pillars)
        self.safe_spots: List[Point2] = []
        self._pillars_calculated = False
        
        # 대군주 상태 추적
        self.overlord_assignments: Dict[int, Point2] = {}  # tag -> target_pos
        self.fleeing_overlords: Set[int] = set()
        
        # 설정
        self.SAFETY_DISTANCE = 15.0  # 대공 유닛과의 안전 거리
        self.RETREAT_DISTANCE = 10.0 # 후퇴 거리

    async def on_start(self):
        """게임 시작 시 실행"""
        self._calculate_safe_spots()

    async def on_step(self, iteration: int):
        """매 프레임 실행"""
        try:
            # 1. 안전 지대 계산 (아직 안 했으면)
            if not self._pillars_calculated:
                self._calculate_safe_spots()
                
            # 2. 대군주 관리 (2초마다)
            if iteration % 44 == 0:
                await self._manage_overlords()
                
            # 3. 위협 회피 (매 프레임 - 중요)
            if iteration % 4 == 0: # 자주 체크
                await self._check_threats()
                
        except Exception as e:
            if iteration % 200 == 0:
                self.logger.error(f"[OVERLORD_SAFETY] Error: {e}")

    def _calculate_safe_spots(self):
        """맵의 안전한 위치(Pillars) 계산

        Pillar: 공중 유닛만 접근 가능한 고지대 (지상 유닛 불가)
        - terrain_height가 높은 위치
        - pathing_grid가 0 (지상 이동 불가)
        - 주변보다 고립된 지형
        """
        if not hasattr(self.bot, "game_info"):
            return

        game_info = self.bot.game_info

        # 지형 정보 확인
        if not hasattr(game_info, "terrain_height") or not hasattr(game_info, "pathing_grid"):
            self.logger.warning("[OVERLORD_SAFETY] Terrain data not available, using fallback positions")
            self._use_fallback_positions()
            return

        try:
            # 실제 Pillar 위치 계산
            pillars = self._find_pillar_positions()

            if pillars:
                self.safe_spots = pillars
                self.logger.info(f"[OVERLORD_SAFETY] Found {len(pillars)} Pillar positions")
            else:
                # Pillar를 찾지 못한 경우 폴백
                self.logger.warning("[OVERLORD_SAFETY] No Pillars found, using fallback positions")
                self._use_fallback_positions()

            self._pillars_calculated = True

        except Exception as e:
            self.logger.error(f"[OVERLORD_SAFETY] Pillar calculation failed: {e}")
            self._use_fallback_positions()
            self._pillars_calculated = True

    def _find_pillar_positions(self) -> List[Point2]:
        """지형 분석을 통한 실제 Pillar 위치 탐색

        Returns:
            Pillar 위치 리스트 (공중만 접근 가능한 고지대)
        """
        game_info = self.bot.game_info
        terrain_height = game_info.terrain_height
        pathing_grid = game_info.pathing_grid

        pillars = []

        # 맵 크기
        width = terrain_height.width
        height = terrain_height.height

        # 샘플링 간격 (모든 타일을 체크하면 너무 느림)
        sample_step = 5

        # 고지대 임계값 계산 (맵 평균 높이)
        heights = []
        for x in range(0, width, sample_step):
            for y in range(0, height, sample_step):
                heights.append(terrain_height[x, y])

        if not heights:
            return []

        avg_height = sum(heights) / len(heights)
        high_threshold = avg_height + 2  # 평균보다 2 이상 높은 지형

        # Pillar 후보 탐색
        for x in range(sample_step, width - sample_step, sample_step):
            for y in range(sample_step, height - sample_step, sample_step):
                pos = Point2((x, y))

                # 1. 높은 지형인가?
                current_height = terrain_height[x, y]
                if current_height < high_threshold:
                    continue

                # 2. 지상 유닛이 접근 불가능한가? (pathing_grid == 0)
                if pathing_grid[x, y] != 0:
                    continue

                # 3. 주변도 접근 불가능한 고립 지형인가? (더 엄격한 체크)
                # 주변 3x3 영역이 대부분 unpathable이어야 함
                unpathable_count = 0
                for dx in range(-1, 2):
                    for dy in range(-1, 2):
                        nx, ny = x + dx, y + dy
                        if 0 <= nx < width and 0 <= ny < height:
                            if pathing_grid[nx, ny] == 0:
                                unpathable_count += 1

                # 주변 9칸 중 7칸 이상이 unpathable이면 Pillar로 판정
                if unpathable_count >= 7:
                    # 적 시작 위치와 너무 가깝지 않은지 체크 (안전성)
                    if self._is_safe_from_enemy_start(pos):
                        pillars.append(pos)

        # Pillar가 너무 많으면 필터링 (최대 12개)
        if len(pillars) > 12:
            # 맵 전체에 고르게 분포하도록 선택
            pillars = self._select_distributed_pillars(pillars, max_count=12)

        return pillars

    def _is_safe_from_enemy_start(self, pos: Point2) -> bool:
        """적 시작 위치에서 충분히 먼지 확인

        Args:
            pos: 체크할 위치

        Returns:
            안전 여부 (적 시작 위치에서 25 이상 떨어짐)
        """
        if not hasattr(self.bot, "enemy_start_locations"):
            return True

        enemy_starts = self.bot.enemy_start_locations
        if not enemy_starts:
            return True

        min_safe_distance = 25.0

        for enemy_start in enemy_starts:
            if pos.distance_to(enemy_start) < min_safe_distance:
                return False

        return True

    def _select_distributed_pillars(self, pillars: List[Point2], max_count: int) -> List[Point2]:
        """맵 전체에 고르게 분포된 Pillar 선택

        Args:
            pillars: Pillar 후보 리스트
            max_count: 최대 선택 개수

        Returns:
            분산 선택된 Pillar 리스트
        """
        if len(pillars) <= max_count:
            return pillars

        # 간단한 그리드 기반 분산 선택
        selected = []
        game_info = self.bot.game_info
        width = game_info.terrain_height.width
        height = game_info.terrain_height.height

        # 맵을 그리드로 나눔 (4x3 = 12칸)
        grid_cols = 4
        grid_rows = 3
        cell_width = width / grid_cols
        cell_height = height / grid_rows

        # 각 셀에서 하나씩 선택
        for row in range(grid_rows):
            for col in range(grid_cols):
                if len(selected) >= max_count:
                    break

                # 현재 셀 영역
                min_x = col * cell_width
                max_x = (col + 1) * cell_width
                min_y = row * cell_height
                max_y = (row + 1) * cell_height

                # 이 셀에 속하는 Pillar 찾기
                cell_pillars = [
                    p for p in pillars
                    if min_x <= p.x < max_x and min_y <= p.y < max_y
                ]

                if cell_pillars:
                    # 셀 중앙에 가장 가까운 것 선택
                    cell_center = Point2((min_x + max_x) / 2, (min_y + max_y) / 2)
                    best = min(cell_pillars, key=lambda p: p.distance_to(cell_center))
                    selected.append(best)

        # 여전히 부족하면 남은 것 중에서 랜덤 선택
        if len(selected) < max_count:
            remaining = [p for p in pillars if p not in selected]
            import random
            additional = random.sample(remaining, min(max_count - len(selected), len(remaining)))
            selected.extend(additional)

        return selected

    def _use_fallback_positions(self):
        """Pillar 계산 실패 시 폴백 위치 사용 (맵 가장자리)"""
        if not hasattr(self.bot.game_info, "map_size"):
            return

        w = self.bot.game_info.map_size.width
        h = self.bot.game_info.map_size.height

        # 맵 가장자리 포인트 (기존 로직)
        self.safe_spots = [
            Point2((10, 10)), Point2((w/2, 10)), Point2((w-10, 10)),
            Point2((10, h/2)), Point2((w-10, h/2)),
            Point2((10, h-10)), Point2((w/2, h-10)), Point2((w-10, h-10))
        ]

    async def _manage_overlords(self):
        """대군주 분산 배치"""
        overlords = self.bot.units(UnitTypeId.OVERLORD).idle
        if not overlords:
            return

        # 할당되지 않은 대군주 찾기
        unassigned = [ov for ov in overlords if ov.tag not in self.overlord_assignments]
        
        for ov in unassigned:
            # 권한 체크 (UnitAuthority)
            if hasattr(self.bot, "unit_authority"):
                from unit_authority_manager import Authority
                # 대군주는 낮은 우선순위로 제어 (드랍 등에 뺏길 수 있음)
                granted = self.bot.unit_authority.request_authority(
                    {ov.tag}, Authority.IDLE, "OverlordSafety", self.bot.state.game_loop
                )
                if ov.tag not in granted:
                    continue
            
            # 빈 안전 지대 찾기
            target = self._find_best_spot(ov)
            if target:
                self.overlord_assignments[ov.tag] = target
                self.bot.do(ov.move(target))

    def _find_best_spot(self, overlord) -> Optional[Point2]:
        """대군주에게 가장 적합한 안전 지대 찾기"""
        if not self.safe_spots:
            return None
            
        # 이미 점유된 위치 제외
        occupied = set(self.overlord_assignments.values())
        available = [s for s in self.safe_spots if s not in occupied]
        
        if not available:
            # 남는 자리가 없으면 랜덤 (또는 맵 중앙 제외)
            return random.choice(self.safe_spots)
            
        # 가장 가까운 곳
        return min(available, key=lambda s: overlord.distance_to(s))

    async def _check_threats(self):
        """대공 위협 감지 및 회피"""
        overlords = self.bot.units(UnitTypeId.OVERLORD)
        enemy_anti_air = self.bot.enemy_units.filter(lambda u: u.can_attack_air)
        
        # 대공 구조물
        enemy_structures = self.bot.enemy_structures.filter(
            lambda s: s.type_id in {
                UnitTypeId.MISSILETURRET, UnitTypeId.SPORECRAWLER, UnitTypeId.PHOTONCANNON, UnitTypeId.BUNKER
            }
        )
        
        for ov in overlords:
            # 드랍 작전 중인 대군주는 제외 (UnitAuthority로 체크 가능하지만 태그로 간단 체크)
            if hasattr(self.bot, "aggressive_strategies"):
                strat = self.bot.aggressive_strategies
                if hasattr(strat, "_drop_overlords") and ov.tag in strat._drop_overlords:
                    continue

            threats = []
            
            # 유닛 위협
            nearby_units = enemy_anti_air.closer_than(self.SAFETY_DISTANCE, ov)
            if nearby_units:
                threats.extend(nearby_units)
                
            # 구조물 위협
            nearby_structures = enemy_structures.closer_than(self.SAFETY_DISTANCE + 2, ov) # 구조물은 사거리 고려 더 넓게
            if nearby_structures:
                threats.extend(nearby_structures)
                
            if threats:
                # 회피 기동
                self.fleeing_overlords.add(ov.tag)
                
                # 가장 가까운 위협으로부터 반대 방향으로 도망
                closest_threat = min(threats, key=lambda t: t.distance_to(ov))
                flee_dir = ov.position - closest_threat.position
                target_pos = ov.position + flee_dir.normalized * self.RETREAT_DISTANCE
                
                # 맵 밖으로 안 나가게 클램핑 (필요 시)
                self.bot.do(ov.move(target_pos))
            else:
                if ov.tag in self.fleeing_overlords:
                    self.fleeing_overlords.remove(ov.tag)
                    # 다시 원래 자리로 복귀는 _manage_overlords가 처리
