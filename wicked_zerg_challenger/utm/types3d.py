# -*- coding: utf-8 -*-
"""
3D Coordinate Types for UTM Drone System

SC2의 Point2(x, y)를 Point3D(x, y, z)로 확장.
고도(z)를 포함한 드론 상태 표현.

Origin: SC2 boids_swarm_control.py의 _get_pos() 패턴 확장
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field
from typing import Any, Tuple

import numpy as np


@dataclass(frozen=True)
class Point3D:
    """3D 좌표 (미터 단위). SC2 Point2의 3D 확장."""

    x: float
    y: float
    z: float  # 고도 (meters above ground)

    def distance_to(self, other: Point3D) -> float:
        """3D 유클리드 거리. 기존 sqrt(dx²+dy²) → sqrt(dx²+dy²+dz²)"""
        dx = self.x - other.x
        dy = self.y - other.y
        dz = self.z - other.z
        return math.sqrt(dx * dx + dy * dy + dz * dz)

    def horizontal_distance_to(self, other: Point3D) -> float:
        """수평 거리만 (고도 무시). 기존 2D 거리 계산과 동일."""
        dx = self.x - other.x
        dy = self.y - other.y
        return math.sqrt(dx * dx + dy * dy)

    def to_array(self) -> np.ndarray:
        """numpy 배열 변환. Boids 벡터 연산용."""
        return np.array([self.x, self.y, self.z], dtype=np.float64)

    def to_tuple(self) -> Tuple[float, float, float]:
        return (self.x, self.y, self.z)

    def offset(self, dx: float = 0.0, dy: float = 0.0, dz: float = 0.0) -> Point3D:
        return Point3D(self.x + dx, self.y + dy, self.z + dz)

    def towards(self, other: Point3D, distance: float) -> Point3D:
        """다른 점을 향해 지정 거리만큼 이동한 점 반환."""
        d = self.distance_to(other)
        if d < 1e-8:
            return Point3D(self.x, self.y, self.z)
        ratio = distance / d
        return Point3D(
            self.x + (other.x - self.x) * ratio,
            self.y + (other.y - self.y) * ratio,
            self.z + (other.z - self.z) * ratio,
        )

    @staticmethod
    def from_array(arr: np.ndarray) -> Point3D:
        return Point3D(float(arr[0]), float(arr[1]), float(arr[2]))

    def __repr__(self) -> str:
        return f"Point3D({self.x:.1f}, {self.y:.1f}, {self.z:.1f})"


@dataclass
class DroneState:
    """드론 상태. SC2의 Unit을 실세계 드론으로 매핑."""

    id: int
    position: Point3D
    velocity: np.ndarray = field(default_factory=lambda: np.zeros(3))  # [vx, vy, vz] m/s
    heading: float = 0.0  # radians (0 = North/+y)
    drone_type: str = "quadrotor"  # "quadrotor" | "fixed_wing"
    max_speed: float = 15.0  # m/s
    max_acceleration: float = 5.0  # m/s²
    min_altitude: float = 5.0  # 최소 안전 고도 (m)
    max_altitude: float = 120.0  # 법적 최대 고도 (m)

    @property
    def speed(self) -> float:
        return float(np.linalg.norm(self.velocity))

    def predict_position(self, dt: float) -> Point3D:
        """dt초 후 예상 위치 (등속 직선 운동 가정)."""
        future = self.position.to_array() + self.velocity * dt
        return Point3D.from_array(future)

    def update(self, force: np.ndarray, dt: float) -> None:
        """힘(가속도)을 적용하여 위치/속도 갱신."""
        # 가속도 제한
        accel_mag = float(np.linalg.norm(force))
        if accel_mag > self.max_acceleration:
            force = force / accel_mag * self.max_acceleration

        # 속도 갱신
        self.velocity = self.velocity + force * dt

        # 속도 제한
        speed = float(np.linalg.norm(self.velocity))
        if speed > self.max_speed:
            self.velocity = self.velocity / speed * self.max_speed

        # 위치 갱신
        new_pos = self.position.to_array() + self.velocity * dt
        # 고도 클램핑
        new_pos[2] = max(self.min_altitude, min(new_pos[2], self.max_altitude))
        self.position = Point3D.from_array(new_pos)

        # 헤딩 갱신 (수평 속도 기반)
        if abs(self.velocity[0]) > 0.01 or abs(self.velocity[1]) > 0.01:
            self.heading = float(math.atan2(self.velocity[0], self.velocity[1]))


def _get_pos3d(obj: Any) -> Tuple[float, float, float]:
    """객체에서 (x, y, z) 좌표를 안전하게 추출. 기존 _get_pos() 확장."""
    if isinstance(obj, DroneState):
        return obj.position.to_tuple()
    if isinstance(obj, Point3D):
        return obj.to_tuple()
    pos = getattr(obj, "position", obj)
    x = float(getattr(pos, "x", 0.0))
    y = float(getattr(pos, "y", 0.0))
    z = float(getattr(pos, "z", 0.0))
    return (x, y, z)
