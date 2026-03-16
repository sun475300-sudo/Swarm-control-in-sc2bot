# -*- coding: utf-8 -*-
"""
Creep Highway - A* 기반 점막 고속도로

아군 본진에서 적 본진까지 A* 최단 경로를 계산하고,
해당 경로를 따라 종양 배치 웨이포인트를 생성합니다.

점막 퀸은 이 웨이포인트를 순서대로 따라가며
고속도로를 건설합니다.
"""

from __future__ import annotations

import heapq
import math
from typing import Dict, List, Optional, Set, Tuple

try:
    from sc2.position import Point2
except ImportError:
    Point2 = None


class CreepHighway:
    """
    A* 기반 점막 고속도로 경로 계획기

    1. 아군 → 적 A* 최단 경로 계산
    2. 경로를 종양 확산 간격(9.0)으로 웨이포인트 변환
    3. 점막 퀸이 순서대로 웨이포인트 따라 종양 설치
    """

    GRID_RESOLUTION = 4      # A* 그리드 셀 크기 (게임 단위)
    WAYPOINT_SPACING = 9.0   # 종양 확산 범위 (게임 단위)

    def __init__(self, bot):
        self.bot = bot
        self.highway_waypoints: List = []  # Point2 list
        self.completed_waypoints: Set[int] = set()  # 완성된 웨이포인트 인덱스
        self._computed = False
        self._last_progress_check = 0

    def compute_highway(self) -> List:
        """
        A* 경로 계산 후 웨이포인트 생성.
        게임 시작 시 1회 호출. 이후 필요 시 재계산.
        """
        if not hasattr(self.bot, "townhalls") or not self.bot.townhalls:
            return []
        if not self.bot.enemy_start_locations:
            return []

        start = self.bot.townhalls.first.position
        goal = self.bot.enemy_start_locations[0]

        # A* 경로 탐색
        path = self._astar(start, goal)

        if not path:
            path = self._straight_line_path(start, goal)

        # 경로 → 웨이포인트 변환
        self.highway_waypoints = self._path_to_waypoints(path)
        self._computed = True
        return self.highway_waypoints

    def _astar(self, start, goal) -> List[Tuple[float, float]]:
        """
        A* 경로 탐색 (pathing_grid 기반)

        Args:
            start: 시작 위치 (아군 본진)
            goal: 목표 위치 (적 본진)

        Returns:
            (x, y) 좌표 리스트
        """
        gi = self.bot.game_info
        pathing = getattr(gi, "pathing_grid", None)

        if pathing is None:
            return self._straight_line_path(start, goal)

        res = self.GRID_RESOLUTION
        sx, sy = int(start.x / res), int(start.y / res)
        gx, gy = int(goal.x / res), int(goal.y / res)

        w = pathing.width // res + 1
        h = pathing.height // res + 1

        # 경계 안전 보정
        sx = max(0, min(sx, w - 1))
        sy = max(0, min(sy, h - 1))
        gx = max(0, min(gx, w - 1))
        gy = max(0, min(gy, h - 1))

        open_set = [(0.0, sx, sy)]
        came_from: Dict[Tuple[int, int], Tuple[int, int]] = {}
        g_score: Dict[Tuple[int, int], float] = {(sx, sy): 0.0}

        def heuristic(ax, ay, bx, by):
            return math.sqrt((ax - bx) ** 2 + (ay - by) ** 2)

        iterations = 0
        max_iterations = w * h * 2  # 안전 제한

        while open_set and iterations < max_iterations:
            iterations += 1
            _, cx, cy = heapq.heappop(open_set)

            if (cx, cy) == (gx, gy):
                # 경로 복원
                path = []
                node = (gx, gy)
                while node in came_from:
                    path.append((node[0] * res, node[1] * res))
                    node = came_from[node]
                path.append((sx * res, sy * res))
                path.reverse()
                return path

            # 8방향 이웃 탐색
            for dx, dy in [(-1, 0), (1, 0), (0, -1), (0, 1),
                           (-1, -1), (1, 1), (-1, 1), (1, -1)]:
                nx, ny = cx + dx, cy + dy

                if not (0 <= nx < w and 0 <= ny < h):
                    continue

                # 지상 이동 가능 확인
                real_x = min(nx * res, pathing.width - 1)
                real_y = min(ny * res, pathing.height - 1)
                try:
                    if not pathing[real_x, real_y]:
                        continue
                except (IndexError, Exception):
                    continue

                cost = 1.414 if abs(dx) + abs(dy) == 2 else 1.0
                tentative = g_score[(cx, cy)] + cost

                if tentative < g_score.get((nx, ny), float("inf")):
                    came_from[(nx, ny)] = (cx, cy)
                    g_score[(nx, ny)] = tentative
                    f = tentative + heuristic(nx, ny, gx, gy)
                    heapq.heappush(open_set, (f, nx, ny))

        # A* 실패 시 직선 경로 fallback
        return self._straight_line_path(start, goal)

    def _straight_line_path(self, start, goal) -> List[Tuple[float, float]]:
        """직선 경로 fallback"""
        path = []
        try:
            dist = start.distance_to(goal)
        except Exception:
            return [(start.x, start.y), (goal.x, goal.y)]

        steps = max(1, int(dist / self.WAYPOINT_SPACING))
        for i in range(steps + 1):
            t = i / steps
            x = start.x + (goal.x - start.x) * t
            y = start.y + (goal.y - start.y) * t
            path.append((x, y))
        return path

    def _path_to_waypoints(self, path: List[Tuple[float, float]]) -> List:
        """
        A* 경로를 종양 배치 간격(9.0)으로 웨이포인트 변환.
        """
        if not Point2:
            return []

        waypoints = []
        last_wp = None

        for x, y in path:
            pos = Point2((x, y))
            if last_wp is None or pos.distance_to(last_wp) >= self.WAYPOINT_SPACING:
                waypoints.append(pos)
                last_wp = pos

        return waypoints

    def get_next_uncreeped_waypoint(self) -> Optional[object]:
        """고속도로에서 다음 점막 미완성 웨이포인트 반환"""
        for i, wp in enumerate(self.highway_waypoints):
            if i in self.completed_waypoints:
                continue
            try:
                if self.bot.has_creep(wp):
                    self.completed_waypoints.add(i)
                    continue
            except Exception:
                continue
            return wp
        return None

    def update_progress(self) -> None:
        """완성된 웨이포인트 업데이트 (on_step에서 주기적 호출)"""
        for i, wp in enumerate(self.highway_waypoints):
            if i in self.completed_waypoints:
                continue
            try:
                if self.bot.has_creep(wp):
                    self.completed_waypoints.add(i)
            except Exception:
                continue

    def get_highway_progress(self) -> float:
        """고속도로 완성률 (0.0 ~ 1.0)"""
        if not self.highway_waypoints:
            return 0.0
        return len(self.completed_waypoints) / len(self.highway_waypoints)

    def get_stats(self) -> Dict:
        """통계 반환"""
        return {
            "total_waypoints": len(self.highway_waypoints),
            "completed": len(self.completed_waypoints),
            "progress": f"{self.get_highway_progress():.1%}",
            "computed": self._computed,
        }