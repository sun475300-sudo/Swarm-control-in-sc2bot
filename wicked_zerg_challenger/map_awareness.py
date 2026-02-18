# -*- coding: utf-8 -*-
"""
Map Awareness Manager - 맵 인식 시스템 (#106)

맵 지형을 분석하고 안개 속 적 위치를 추정하는 시스템입니다.

주요 기능:
1. 맵 지형 분석 (초크포인트, 고지대, 평지)
2. 시야 범위 외 적 추정 위치 트래킹
3. 적 확장 기지 예측
4. 안전/위험 지역 분류
5. 이동 경로 최적화를 위한 경유지 계산
"""

import math
from typing import Any, Dict, List, Optional, Set, Tuple

try:
    from sc2.position import Point2
except ImportError:
    Point2 = None

try:
    from sc2.ids.unit_typeid import UnitTypeId
except ImportError:
    UnitTypeId = None


class TerrainZone:
    """맵 지형 구역"""

    def __init__(self, center: Tuple[float, float], zone_type: str,
                 radius: float = 5.0):
        """
        Args:
            center: 구역 중심 좌표
            zone_type: 구역 타입 ("chokepoint", "high_ground", "open", "ramp", "base_location")
            radius: 구역 반경
        """
        self.center = center
        self.zone_type = zone_type
        self.radius = radius
        self.danger_level: float = 0.0  # 0.0 (안전) ~ 1.0 (위험)
        self.last_scouted: float = 0.0  # 마지막 정찰 시간

    def distance_to(self, point: Tuple[float, float]) -> float:
        """특정 지점과의 거리"""
        dx = self.center[0] - point[0]
        dy = self.center[1] - point[1]
        return math.sqrt(dx * dx + dy * dy)

    def contains(self, point: Tuple[float, float]) -> bool:
        """해당 지점이 구역 내에 있는지"""
        return self.distance_to(point) <= self.radius


class EnemyGhost:
    """
    안개 속 적 추정 위치

    마지막으로 관찰된 적 유닛의 추정 현재 위치를 트래킹합니다.
    시간이 지나면 정보의 신뢰도가 감소합니다.
    """

    def __init__(self, unit_tag: int, unit_type: str,
                 last_position: Tuple[float, float], last_seen: float):
        """
        Args:
            unit_tag: 유닛 태그
            unit_type: 유닛 타입 이름
            last_position: 마지막 관찰 위치
            last_seen: 마지막 관찰 시간
        """
        self.unit_tag = unit_tag
        self.unit_type = unit_type
        self.last_position = last_position
        self.last_seen = last_seen
        self.estimated_position = last_position
        self.confidence: float = 1.0  # 신뢰도 (시간 경과에 따라 감소)
        self.is_dead: bool = False

    def update_confidence(self, current_time: float, decay_rate: float = 0.01) -> None:
        """
        시간 경과에 따른 신뢰도 업데이트

        Args:
            current_time: 현재 게임 시간
            decay_rate: 초당 신뢰도 감소율
        """
        elapsed = current_time - self.last_seen
        self.confidence = max(0.0, 1.0 - elapsed * decay_rate)

    def update_sighting(self, position: Tuple[float, float],
                        time: float) -> None:
        """유닛 재관찰 시 업데이트"""
        self.last_position = position
        self.estimated_position = position
        self.last_seen = time
        self.confidence = 1.0


class MapAwarenessManager:
    """
    맵 인식 관리자

    맵 지형 분석과 안개 속 적 위치 추정을 통합 관리합니다.
    전략적 의사결정에 필요한 공간 정보를 제공합니다.

    사용 예:
        awareness = MapAwarenessManager(bot)
        awareness.initialize()  # 게임 시작 시 1회 호출
        awareness.update()      # 매 스텝 호출

        chokes = awareness.get_chokepoints()
        danger = awareness.get_danger_zone(position)
        ghosts = awareness.get_enemy_ghosts()
    """

    def __init__(self, bot):
        """
        Args:
            bot: SC2 봇 인스턴스
        """
        self.bot = bot

        # 지형 구역
        self.terrain_zones: List[TerrainZone] = []
        self.chokepoints: List[TerrainZone] = []
        self.high_grounds: List[TerrainZone] = []
        self.base_locations: List[TerrainZone] = []
        self.ramps: List[TerrainZone] = []

        # 적 추정 위치
        self.enemy_ghosts: Dict[int, EnemyGhost] = {}

        # 적 확장 기지 예측
        self.predicted_enemy_bases: List[Tuple[float, float]] = []

        # 시야 정보
        self.scouted_areas: Set[Tuple[int, int]] = set()
        self.last_scout_time: Dict[Tuple[int, int], float] = {}

        # 맵 크기
        self.map_width: float = 0.0
        self.map_height: float = 0.0

        # 초기화 여부
        self._initialized: bool = False

        print("[MAP_AWARENESS] 맵 인식 관리자 초기화")

    def initialize(self) -> None:
        """
        게임 시작 시 맵 분석 수행 (1회)

        초크포인트, 고지대, 기지 위치 등을 분석합니다.
        """
        if self._initialized:
            return

        try:
            # 맵 크기
            if hasattr(self.bot, "game_info"):
                gi = self.bot.game_info
                if hasattr(gi, "map_size"):
                    self.map_width = gi.map_size.x
                    self.map_height = gi.map_size.y

            # 초크포인트 분석
            self._analyze_chokepoints()

            # 확장 기지 위치 분석
            self._analyze_base_locations()

            # 고지대/경사로 분석
            self._analyze_ramps()

            self._initialized = True

            print(f"[MAP_AWARENESS] 맵 분석 완료: "
                  f"chokepoints={len(self.chokepoints)}, "
                  f"bases={len(self.base_locations)}, "
                  f"ramps={len(self.ramps)}")

        except Exception as e:
            print(f"[MAP_AWARENESS] 맵 분석 실패: {e}")

    def update(self) -> None:
        """매 스텝 업데이트"""
        if not self._initialized:
            self.initialize()

        game_time = getattr(self.bot, "time", 0.0)

        # 적 유닛 위치 트래킹
        self._track_enemy_units(game_time)

        # 적 고스트(안개 속 추정) 업데이트
        self._update_ghosts(game_time)

        # 적 확장 기지 예측
        self._predict_enemy_bases(game_time)

        # 위험도 업데이트
        self._update_danger_levels(game_time)

    def get_chokepoints(self) -> List[TerrainZone]:
        """초크포인트 목록 반환"""
        return self.chokepoints

    def get_nearest_chokepoint(self, position: Tuple[float, float]) -> Optional[TerrainZone]:
        """가장 가까운 초크포인트 반환"""
        if not self.chokepoints:
            return None
        return min(self.chokepoints, key=lambda c: c.distance_to(position))

    def get_danger_level(self, position: Tuple[float, float]) -> float:
        """
        특정 위치의 위험도 반환

        Args:
            position: 좌표 (x, y)

        Returns:
            위험도 (0.0 = 안전, 1.0 = 매우 위험)
        """
        max_danger = 0.0

        # 적 유닛 근접도 기반 위험도
        for ghost in self.enemy_ghosts.values():
            if ghost.is_dead or ghost.confidence < 0.1:
                continue
            dist = math.sqrt(
                (position[0] - ghost.estimated_position[0]) ** 2 +
                (position[1] - ghost.estimated_position[1]) ** 2
            )
            if dist < 15:
                danger = ghost.confidence * max(0, (15 - dist) / 15)
                max_danger = max(max_danger, danger)

        # 지형 구역 위험도
        for zone in self.terrain_zones:
            if zone.contains(position):
                max_danger = max(max_danger, zone.danger_level)

        return min(1.0, max_danger)

    def get_safe_path_waypoints(self, start: Tuple[float, float],
                                  end: Tuple[float, float]) -> List[Tuple[float, float]]:
        """
        안전한 이동 경로의 경유지 계산

        Args:
            start: 시작 위치
            end: 목표 위치

        Returns:
            경유지 리스트
        """
        waypoints = [start]

        # 직선 경로의 위험도 체크
        mid_x = (start[0] + end[0]) / 2
        mid_y = (start[1] + end[1]) / 2
        mid_danger = self.get_danger_level((mid_x, mid_y))

        if mid_danger > 0.5:
            # 위험 구간 회피 - 아군 기지 쪽으로 우회
            if hasattr(self.bot, "start_location"):
                base_pos = self.bot.start_location
                safe_x = (mid_x + base_pos.x) / 2
                safe_y = (mid_y + base_pos.y) / 2
                waypoints.append((safe_x, safe_y))

        waypoints.append(end)
        return waypoints

    def get_enemy_ghosts(self, min_confidence: float = 0.3) -> List[EnemyGhost]:
        """
        일정 신뢰도 이상의 적 추정 위치 반환

        Args:
            min_confidence: 최소 신뢰도

        Returns:
            적 고스트 리스트
        """
        return [
            ghost for ghost in self.enemy_ghosts.values()
            if ghost.confidence >= min_confidence and not ghost.is_dead
        ]

    def get_unscouted_base_locations(self, time_threshold: float = 120.0) -> List[Tuple[float, float]]:
        """
        최근에 정찰하지 않은 기지 위치 반환

        Args:
            time_threshold: 정찰 기준 시간 (초)

        Returns:
            미정찰 기지 위치 리스트
        """
        game_time = getattr(self.bot, "time", 0.0)
        unscouted = []

        for base_zone in self.base_locations:
            grid = (int(base_zone.center[0]), int(base_zone.center[1]))
            last_time = self.last_scout_time.get(grid, 0.0)
            if game_time - last_time > time_threshold:
                unscouted.append(base_zone.center)

        return unscouted

    def _analyze_chokepoints(self) -> None:
        """초크포인트 분석"""
        try:
            if hasattr(self.bot, "game_info") and hasattr(self.bot.game_info, "map_ramps"):
                for ramp in self.bot.game_info.map_ramps:
                    if hasattr(ramp, "top_center"):
                        center = (ramp.top_center.x, ramp.top_center.y)
                        zone = TerrainZone(center, "chokepoint", radius=4.0)
                        self.chokepoints.append(zone)
                        self.terrain_zones.append(zone)
        except Exception as e:
            print(f"[MAP_AWARENESS] 초크포인트 분석 실패: {e}")

    def _analyze_base_locations(self) -> None:
        """기지 위치 분석"""
        try:
            if hasattr(self.bot, "expansion_locations_list"):
                for loc in self.bot.expansion_locations_list:
                    if Point2 and isinstance(loc, Point2):
                        center = (loc.x, loc.y)
                    else:
                        center = (float(loc[0]), float(loc[1]))
                    zone = TerrainZone(center, "base_location", radius=8.0)
                    self.base_locations.append(zone)
                    self.terrain_zones.append(zone)
        except Exception as e:
            print(f"[MAP_AWARENESS] 기지 위치 분석 실패: {e}")

    def _analyze_ramps(self) -> None:
        """경사로 분석"""
        try:
            if hasattr(self.bot, "game_info") and hasattr(self.bot.game_info, "map_ramps"):
                for ramp in self.bot.game_info.map_ramps:
                    if hasattr(ramp, "bottom_center"):
                        center = (ramp.bottom_center.x, ramp.bottom_center.y)
                        zone = TerrainZone(center, "ramp", radius=3.0)
                        self.ramps.append(zone)
                        self.terrain_zones.append(zone)
        except Exception as e:
            print(f"[MAP_AWARENESS] 경사로 분석 실패: {e}")

    def _track_enemy_units(self, game_time: float) -> None:
        """적 유닛 위치 트래킹"""
        if not hasattr(self.bot, "enemy_units"):
            return

        for unit in self.bot.enemy_units:
            try:
                tag = unit.tag
                unit_type = getattr(unit.type_id, "name", "UNKNOWN")
                pos = (unit.position.x, unit.position.y)

                if tag in self.enemy_ghosts:
                    self.enemy_ghosts[tag].update_sighting(pos, game_time)
                else:
                    self.enemy_ghosts[tag] = EnemyGhost(tag, unit_type, pos, game_time)

                # 시야 업데이트
                grid = (int(pos[0]), int(pos[1]))
                self.scouted_areas.add(grid)
                self.last_scout_time[grid] = game_time

            except Exception:
                continue

    def _update_ghosts(self, game_time: float) -> None:
        """적 고스트 신뢰도 업데이트"""
        dead_tags = []
        for tag, ghost in self.enemy_ghosts.items():
            ghost.update_confidence(game_time)
            if ghost.confidence <= 0.0:
                dead_tags.append(tag)

        # 신뢰도 0 된 고스트 제거
        for tag in dead_tags:
            del self.enemy_ghosts[tag]

    def _predict_enemy_bases(self, game_time: float) -> None:
        """적 확장 기지 위치 예측"""
        # 5초마다만 업데이트
        if int(game_time) % 5 != 0:
            return

        self.predicted_enemy_bases.clear()

        # 알려진 적 기지 위치
        known_enemy_bases = set()
        if hasattr(self.bot, "enemy_structures"):
            for struct in self.bot.enemy_structures:
                try:
                    name = getattr(struct.type_id, "name", "").upper()
                    if name in ("HATCHERY", "LAIR", "HIVE", "NEXUS",
                               "COMMANDCENTER", "ORBITALCOMMAND", "PLANETARYFORTRESS"):
                        known_enemy_bases.add((int(struct.position.x), int(struct.position.y)))
                except Exception:
                    continue

        # 적 시작 위치 기반 가까운 확장 위치 예측
        if hasattr(self.bot, "enemy_start_locations") and self.bot.enemy_start_locations:
            enemy_start = self.bot.enemy_start_locations[0]
            for base_zone in self.base_locations:
                pos = base_zone.center
                grid = (int(pos[0]), int(pos[1]))

                # 이미 알려진 기지는 스킵
                if grid in known_enemy_bases:
                    continue

                # 적 시작 위치에 가까운 확장 위치를 예측
                dist = math.sqrt(
                    (pos[0] - enemy_start.x) ** 2 +
                    (pos[1] - enemy_start.y) ** 2
                )

                # 게임 시간에 따라 예측 범위 확대
                max_expansion_dist = 30 + game_time * 0.05
                if dist < max_expansion_dist:
                    self.predicted_enemy_bases.append(pos)

    def _update_danger_levels(self, game_time: float) -> None:
        """지형 구역 위험도 업데이트"""
        for zone in self.terrain_zones:
            danger = 0.0

            # 적 고스트 기반 위험도
            for ghost in self.enemy_ghosts.values():
                if ghost.is_dead or ghost.confidence < 0.2:
                    continue
                dist = zone.distance_to(ghost.estimated_position)
                if dist < 15:
                    danger += ghost.confidence * (15 - dist) / 15

            zone.danger_level = min(1.0, danger)

    def get_status(self) -> Dict[str, Any]:
        """맵 인식 상태 반환"""
        return {
            "initialized": self._initialized,
            "chokepoints": len(self.chokepoints),
            "base_locations": len(self.base_locations),
            "tracked_enemies": len(self.enemy_ghosts),
            "predicted_enemy_bases": len(self.predicted_enemy_bases),
            "scouted_areas": len(self.scouted_areas),
        }
