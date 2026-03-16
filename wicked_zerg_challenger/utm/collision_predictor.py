# -*- coding: utf-8 -*-
"""
Time-to-Collision (TTC) Predictor for Drone Deconfliction

기존 Boids의 distance-based 회피를 시간 기반 궤적 예측으로 업그레이드.
두 드론의 미래 궤적을 계산하여 충돌 시간과 최소 이격 거리를 예측.

Origin: potential_fields.py의 반발력 + pid_controller.py의 제어
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import List, Optional, Tuple

import numpy as np

from wicked_zerg_challenger.utm.types3d import DroneState, Point3D


@dataclass
class CollisionAlert:
    """충돌 경고 데이터."""
    drone_a_id: int
    drone_b_id: int
    ttc: float              # 충돌까지 남은 시간 (초)
    min_distance: float     # 최소 접근 거리 (미터)
    conflict_point: Point3D  # 예상 충돌 지점
    severity: str           # "warning" | "critical" | "imminent"


class CollisionPredictor:
    """
    TTC 기반 충돌 예측 시스템.

    기존 Boids의 distance-based 회피와의 차이:
    - 기존: 현재 거리 < threshold → 반발력
    - TTC: 미래 궤적 교차 예측 → 선제적 회피
    """

    def __init__(
        self,
        time_horizon: float = 5.0,    # 예측 시간 범위 (초)
        safety_distance: float = 5.0,  # 최소 안전 거리 (미터)
        warning_ttc: float = 5.0,     # 경고 시간 임계값
        critical_ttc: float = 3.0,    # 위험 시간 임계값
        imminent_ttc: float = 1.0,    # 긴급 시간 임계값
    ):
        self.time_horizon = time_horizon
        self.safety_distance = safety_distance
        self.warning_ttc = warning_ttc
        self.critical_ttc = critical_ttc
        self.imminent_ttc = imminent_ttc

    def predict_ttc(
        self, drone_a: DroneState, drone_b: DroneState
    ) -> Optional[float]:
        """
        두 드론의 충돌 시간(TTC) 계산.

        등속 직선 운동 가정:
        relative_pos + relative_vel * t = 0 (최소 거리 시점)
        TTC = -dot(rel_pos, rel_vel) / dot(rel_vel, rel_vel)
        """
        rel_pos = drone_b.position.to_array() - drone_a.position.to_array()
        rel_vel = drone_b.velocity - drone_a.velocity

        vel_sq = float(np.dot(rel_vel, rel_vel))
        if vel_sq < 1e-8:
            # 상대 속도 거의 없음 → 충돌 없음 (병렬 이동)
            return None

        ttc = -float(np.dot(rel_pos, rel_vel)) / vel_sq

        # 과거 또는 너무 먼 미래는 무시
        if ttc < 0 or ttc > self.time_horizon:
            return None

        # 해당 시점의 최소 거리 확인
        min_dist = self._distance_at_time(drone_a, drone_b, ttc)
        if min_dist > self.safety_distance:
            return None

        return ttc

    def _distance_at_time(
        self, drone_a: DroneState, drone_b: DroneState, t: float
    ) -> float:
        """t초 후 두 드론 사이 예상 거리."""
        pos_a = drone_a.position.to_array() + drone_a.velocity * t
        pos_b = drone_b.position.to_array() + drone_b.velocity * t
        return float(np.linalg.norm(pos_a - pos_b))

    def check_all_pairs(
        self, drones: List[DroneState]
    ) -> List[CollisionAlert]:
        """
        모든 드론 쌍의 충돌 검사. O(N²) — VoxelGrid로 사전 필터링 가능.
        """
        alerts = []
        n = len(drones)
        for i in range(n):
            for j in range(i + 1, n):
                ttc = self.predict_ttc(drones[i], drones[j])
                if ttc is not None:
                    min_dist = self._distance_at_time(drones[i], drones[j], ttc)
                    conflict_pos = self._midpoint_at_time(drones[i], drones[j], ttc)

                    if ttc <= self.imminent_ttc:
                        severity = "imminent"
                    elif ttc <= self.critical_ttc:
                        severity = "critical"
                    else:
                        severity = "warning"

                    alerts.append(CollisionAlert(
                        drone_a_id=drones[i].id,
                        drone_b_id=drones[j].id,
                        ttc=ttc,
                        min_distance=min_dist,
                        conflict_point=conflict_pos,
                        severity=severity,
                    ))

        # 긴급도 순 정렬
        alerts.sort(key=lambda a: a.ttc)
        return alerts

    def compute_avoidance_vector(
        self, drone: DroneState, threat: DroneState, ttc: float
    ) -> np.ndarray:
        """
        충돌 회피 벡터 계산.
        기존 potential_fields.py 반발력 패턴의 시간 기반 확장:
        strength = (safety_time - ttc) / safety_time
        """
        # 충돌 시점의 상대 위치 예측
        future_self = drone.position.to_array() + drone.velocity * ttc
        future_threat = threat.position.to_array() + threat.velocity * ttc

        # 반발 방향 (충돌 지점에서 멀어지는 방향)
        diff = future_self - future_threat
        dist = float(np.linalg.norm(diff))
        if dist < 0.01:
            # 정확히 같은 지점 → 수직 회피
            diff = np.array([0.0, 0.0, 1.0])
            dist = 1.0

        # 시간 기반 강도 (기존 거리 기반 패턴의 시간 변형)
        strength = max(0.0, (self.warning_ttc - ttc) / self.warning_ttc)
        return (diff / dist) * strength * 5.0

    def _midpoint_at_time(
        self, drone_a: DroneState, drone_b: DroneState, t: float
    ) -> Point3D:
        """t초 후 두 드론의 중간 지점."""
        pos_a = drone_a.position.to_array() + drone_a.velocity * t
        pos_b = drone_b.position.to_array() + drone_b.velocity * t
        mid = (pos_a + pos_b) / 2
        return Point3D.from_array(mid)
