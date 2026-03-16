# -*- coding: utf-8 -*-
"""
Virtual Flight Corridor System

SC2 creep_highway.py의 A* 경로 + 웨이포인트 시스템을 3D 비행 회랑으로 진화.
고도층 분리, 방향 기반 회랑 할당으로 항공 교통 규칙 모사.

Origin: wicked_zerg_challenger/combat/creep_highway.py
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple

from wicked_zerg_challenger.utm.types3d import Point3D

# 고도층 정의 (UTM 규정 모사)
ALTITUDE_LAYERS = {
    "low": (5.0, 30.0),       # 저고도: 5~30m (촬영, 농업)
    "medium": (30.0, 60.0),   # 중고도: 30~60m (배송, 순찰)
    "high": (60.0, 120.0),    # 고고도: 60~120m (장거리 이동)
}

# 방향별 고도 분리 (항공 규칙: 동행 → 홀수, 서행 → 짝수)
DIRECTION_ALTITUDE_OFFSETS = {
    "eastbound": 0.0,    # 0~180° heading
    "westbound": 15.0,   # 180~360° heading → +15m 오프셋
}


@dataclass
class FlightCorridor:
    """
    가상 비행 회랑. SC2 creep_highway의 웨이포인트 시퀀스를 3D로 확장.

    Attributes:
        corridor_id: 고유 ID
        waypoints: 3D 웨이포인트 시퀀스
        width: 회랑 폭 (미터)
        altitude_layer: 할당된 고도층
    """
    corridor_id: str
    waypoints: List[Point3D]
    width: float = 20.0  # 기본 회랑 폭 (SC2: waypoint_spacing = 9.0)
    altitude_layer: str = "medium"
    bidirectional: bool = False

    @property
    def length(self) -> float:
        """총 회랑 길이."""
        total = 0.0
        for i in range(len(self.waypoints) - 1):
            total += self.waypoints[i].distance_to(self.waypoints[i + 1])
        return total

    @property
    def start(self) -> Point3D:
        return self.waypoints[0]

    @property
    def end(self) -> Point3D:
        return self.waypoints[-1]

    def get_nearest_waypoint_index(self, position: Point3D) -> int:
        """현재 위치에서 가장 가까운 웨이포인트 인덱스."""
        best_idx = 0
        best_dist = float("inf")
        for i, wp in enumerate(self.waypoints):
            d = position.distance_to(wp)
            if d < best_dist:
                best_dist = d
                best_idx = i
        return best_idx

    def get_next_waypoint(self, position: Point3D) -> Optional[Point3D]:
        """현재 위치 기준 다음 웨이포인트 반환."""
        idx = self.get_nearest_waypoint_index(position)
        if idx + 1 < len(self.waypoints):
            return self.waypoints[idx + 1]
        return None

    def is_inside(self, position: Point3D) -> bool:
        """해당 위치가 회랑 내부인지 확인."""
        # 가장 가까운 웨이포인트까지의 수평 거리로 판단
        idx = self.get_nearest_waypoint_index(position)
        wp = self.waypoints[idx]
        h_dist = position.horizontal_distance_to(wp)
        alt_min, alt_max = ALTITUDE_LAYERS.get(self.altitude_layer, (0, 120))
        return h_dist <= self.width and alt_min <= position.z <= alt_max


@dataclass
class CorridorManager:
    """
    비행 회랑 관리자. 회랑 생성, 할당, 충돌 검사.
    SC2 CreepHighway의 경로 관리 기능을 UTM으로 진화.
    """
    corridors: Dict[str, FlightCorridor] = field(default_factory=dict)
    waypoint_spacing: float = 50.0  # 미터 (SC2: 9.0 game units)

    def create_corridor(
        self,
        corridor_id: str,
        start: Point3D,
        end: Point3D,
        altitude_layer: str = "medium",
        width: float = 20.0,
    ) -> FlightCorridor:
        """
        출발-도착 사이 직선 회랑 생성.
        기존 creep_highway.py의 직선 경로 보간 패턴 재사용.
        """
        alt_min, alt_max = ALTITUDE_LAYERS.get(altitude_layer, (30.0, 60.0))
        cruise_alt = (alt_min + alt_max) / 2.0

        # 수평 거리 기반 웨이포인트 보간 (기존 패턴)
        h_dist = start.horizontal_distance_to(end)
        steps = max(1, int(h_dist / self.waypoint_spacing))

        waypoints = []
        for i in range(steps + 1):
            t = i / steps
            x = start.x + (end.x - start.x) * t
            y = start.y + (end.y - start.y) * t
            # 이/착륙 고도 프로파일: 상승 → 순항 → 하강
            if t < 0.15:
                z = start.z + (cruise_alt - start.z) * (t / 0.15)
            elif t > 0.85:
                z = cruise_alt + (end.z - cruise_alt) * ((t - 0.85) / 0.15)
            else:
                z = cruise_alt
            waypoints.append(Point3D(x, y, z))

        corridor = FlightCorridor(
            corridor_id=corridor_id,
            waypoints=waypoints,
            width=width,
            altitude_layer=altitude_layer,
        )
        self.corridors[corridor_id] = corridor
        return corridor

    def get_assigned_altitude(self, heading: float, layer: str = "medium") -> float:
        """
        헤딩 기반 고도 할당 (항공 교통 규칙).
        0~180° → 동행 고도, 180~360° → 서행 고도 (15m 오프셋).
        """
        alt_min, alt_max = ALTITUDE_LAYERS.get(layer, (30.0, 60.0))
        base_alt = (alt_min + alt_max) / 2.0

        heading_deg = math.degrees(heading) % 360
        if heading_deg < 180:
            return base_alt
        else:
            return base_alt + DIRECTION_ALTITUDE_OFFSETS["westbound"]

    def find_corridor(self, position: Point3D) -> Optional[FlightCorridor]:
        """현재 위치가 속한 회랑 검색."""
        for corridor in self.corridors.values():
            if corridor.is_inside(position):
                return corridor
        return None

    def check_corridor_conflict(
        self, corridor_a: str, corridor_b: str
    ) -> List[Point3D]:
        """두 회랑의 교차점 검출 (UTM 충돌 위험 지점)."""
        a = self.corridors.get(corridor_a)
        b = self.corridors.get(corridor_b)
        if not a or not b:
            return []

        conflicts = []
        for wp_a in a.waypoints:
            for wp_b in b.waypoints:
                dist = wp_a.distance_to(wp_b)
                if dist < (a.width + b.width) / 2:
                    # 중간점을 충돌 위험 지점으로 등록
                    mid = Point3D(
                        (wp_a.x + wp_b.x) / 2,
                        (wp_a.y + wp_b.y) / 2,
                        (wp_a.z + wp_b.z) / 2,
                    )
                    conflicts.append(mid)
        return conflicts
