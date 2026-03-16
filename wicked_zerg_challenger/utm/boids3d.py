# -*- coding: utf-8 -*-
"""
3D Boids Swarm Controller for Drone Formation Flight

SC2 BoidsSwarmController의 6개 힘을 3D로 확장 + 고도 관련 힘 2개 추가.
총 8개 힘: separation, alignment, cohesion, target_seeking,
          obstacle_avoidance, altitude_hold, terrain_clearance, corridor_follow

Origin: wicked_zerg_challenger/combat/boids_swarm_control.py
"""

from __future__ import annotations

import math
from typing import List, Optional, Tuple

import numpy as np

from wicked_zerg_challenger.utm.types3d import DroneState, Point3D, _get_pos3d


class Boids3DController:
    """
    3D Boids-based swarm controller for drone fleet management.

    SC2 BoidsSwarmController와의 차이:
    - 모든 벡터: 2D [vx,vy] → 3D [vx,vy,vz]
    - 신규 힘: altitude_hold (고도 유지), terrain_clearance (지면 이격)
    - 드론 운동학 반영: max_speed, max_acceleration 제한
    """

    def __init__(
        self,
        separation_weight: float = 2.0,
        alignment_weight: float = 1.0,
        cohesion_weight: float = 1.0,
        target_weight: float = 1.5,
        avoidance_weight: float = 2.5,
        altitude_hold_weight: float = 1.0,
        terrain_clearance_weight: float = 3.0,
        separation_radius: float = 5.0,    # 미터 (SC2: 2.0 game units)
        neighbor_radius: float = 30.0,     # 미터 (SC2: 5.0 game units)
        max_force: float = 5.0,            # m/s² (SC2: 0.5)
    ):
        self.separation_weight = separation_weight
        self.alignment_weight = alignment_weight
        self.cohesion_weight = cohesion_weight
        self.target_weight = target_weight
        self.avoidance_weight = avoidance_weight
        self.altitude_hold_weight = altitude_hold_weight
        self.terrain_clearance_weight = terrain_clearance_weight
        self.separation_radius = separation_radius
        self.neighbor_radius = neighbor_radius
        self.max_force = max_force

    def calculate_force(
        self,
        drone: DroneState,
        neighbors: List[DroneState],
        target: Optional[Point3D] = None,
        obstacles: Optional[List[Point3D]] = None,
        desired_altitude: Optional[float] = None,
        terrain_height: float = 0.0,
    ) -> np.ndarray:
        """
        8개 힘을 합산하여 최종 가속도 벡터 반환.

        기존 calculate_swarm_velocity()의 3D 확장.
        """
        force = np.zeros(3)

        # 1. Separation (분리) — 기존 _calculate_separation 확장
        sep = self._separation(drone, neighbors)
        force += sep * self.separation_weight

        # 2. Alignment (정렬) — 기존 _calculate_alignment 확장
        ali = self._alignment(drone, neighbors)
        force += ali * self.alignment_weight

        # 3. Cohesion (응집) — 기존 _calculate_cohesion 확장
        coh = self._cohesion(drone, neighbors)
        force += coh * self.cohesion_weight

        # 4. Target Seeking (목표 추적) — 기존 _calculate_target_seeking 확장
        if target is not None:
            tgt = self._target_seeking(drone, target)
            force += tgt * self.target_weight

        # 5. Obstacle Avoidance (장애물 회피) — 기존 enemy_avoidance 변형
        if obstacles:
            avoid = self._obstacle_avoidance(drone, obstacles)
            force += avoid * self.avoidance_weight

        # 6. Altitude Hold (고도 유지) — 신규
        if desired_altitude is not None:
            alt = self._altitude_hold(drone, desired_altitude)
            force += alt * self.altitude_hold_weight

        # 7. Terrain Clearance (지면 이격) — 신규
        terrain = self._terrain_clearance(drone, terrain_height)
        force += terrain * self.terrain_clearance_weight

        # 최대 힘 제한 (기존 max_force 클램핑 동일)
        mag = float(np.linalg.norm(force))
        if mag > self.max_force:
            force = force / mag * self.max_force

        return force

    def _separation(self, drone: DroneState, neighbors: List[DroneState]) -> np.ndarray:
        """
        분리력: 가까운 이웃으로부터 반발.
        기존: diff / distance² (역제곱 법칙) — 동일하게 3D 적용.
        """
        force = np.zeros(3)
        pos = drone.position.to_array()
        count = 0

        for neighbor in neighbors:
            if neighbor.id == drone.id:
                continue
            n_pos = neighbor.position.to_array()
            diff = pos - n_pos
            dist = float(np.linalg.norm(diff))

            if 0.01 < dist < self.separation_radius:
                # 역제곱 반발력 (기존 Boids 패턴)
                force += diff / (dist * dist)
                count += 1

        if count > 0:
            force /= count
            mag = float(np.linalg.norm(force))
            if mag > 0:
                force = force / mag * self.max_force

        return force

    def _alignment(self, drone: DroneState, neighbors: List[DroneState]) -> np.ndarray:
        """
        정렬력: 이웃들의 평균 속도 방향으로 정렬.
        기존: 이웃 평균 위치 방향 — 여기서는 속도 정렬 (더 정확한 Boids 구현).
        """
        avg_vel = np.zeros(3)
        count = 0

        for neighbor in neighbors:
            if neighbor.id == drone.id:
                continue
            dist = drone.position.distance_to(neighbor.position)
            if dist < self.neighbor_radius:
                avg_vel += neighbor.velocity
                count += 1

        if count > 0:
            avg_vel /= count
            desired = avg_vel - drone.velocity
            mag = float(np.linalg.norm(desired))
            if mag > 0:
                desired = desired / mag * self.max_force
            return desired

        return np.zeros(3)

    def _cohesion(self, drone: DroneState, neighbors: List[DroneState]) -> np.ndarray:
        """
        응집력: 이웃 그룹의 중심으로 이동.
        기존: centroid(neighbors) - unit_pos — 동일 패턴 3D.
        """
        center = np.zeros(3)
        count = 0

        for neighbor in neighbors:
            if neighbor.id == drone.id:
                continue
            dist = drone.position.distance_to(neighbor.position)
            if dist < self.neighbor_radius:
                center += neighbor.position.to_array()
                count += 1

        if count > 0:
            center /= count
            desired = center - drone.position.to_array()
            mag = float(np.linalg.norm(desired))
            if mag > 0:
                desired = desired / mag * self.max_force
            return desired

        return np.zeros(3)

    def _target_seeking(self, drone: DroneState, target: Point3D) -> np.ndarray:
        """
        목표 추적력: 목표 지점으로 이동.
        기존: force = min(distance/10, 1.0) * max_force — 동일 감쇠.
        """
        desired = target.to_array() - drone.position.to_array()
        dist = float(np.linalg.norm(desired))

        if dist < 0.01:
            return np.zeros(3)

        # 거리 비례 감쇠 (기존 패턴)
        scale = min(dist / 50.0, 1.0) * self.max_force
        return desired / dist * scale

    def _obstacle_avoidance(
        self, drone: DroneState, obstacles: List[Point3D]
    ) -> np.ndarray:
        """
        장애물 회피력: 기존 enemy_avoidance의 3D 변형.
        기존: strength = (danger_radius - distance) / danger_radius
        """
        force = np.zeros(3)
        pos = drone.position.to_array()
        danger_radius = 20.0  # 미터

        for obs in obstacles:
            obs_arr = obs.to_array()
            diff = pos - obs_arr
            dist = float(np.linalg.norm(diff))

            if 0.01 < dist < danger_radius:
                strength = (danger_radius - dist) / danger_radius
                force += (diff / (dist + 0.1)) * strength

        return force

    def _altitude_hold(self, drone: DroneState, desired_alt: float) -> np.ndarray:
        """
        고도 유지력: 지정 고도에서 벗어나면 복원력 적용. (UTM 신규)
        PID 제어 기반: P항만 사용 (간단 구현).
        """
        error = desired_alt - drone.position.z
        # 수직 방향만 힘 적용
        fz = error * 0.5  # Kp = 0.5
        fz = max(-self.max_force, min(fz, self.max_force))
        return np.array([0.0, 0.0, fz])

    def _terrain_clearance(self, drone: DroneState, terrain_height: float) -> np.ndarray:
        """
        지면 이격력: 최소 안전 고도 미만 시 강한 상승력. (UTM 신규)
        기존 potential_fields.py의 반발력 패턴 적용.
        """
        clearance = drone.position.z - terrain_height
        min_clearance = drone.min_altitude

        if clearance >= min_clearance:
            return np.zeros(3)

        # 지면에 가까울수록 강한 상승력
        strength = (min_clearance - clearance) / min_clearance
        return np.array([0.0, 0.0, self.max_force * strength * 2.0])

    def step(
        self,
        drones: List[DroneState],
        dt: float = 0.1,
        target: Optional[Point3D] = None,
        obstacles: Optional[List[Point3D]] = None,
        desired_altitude: Optional[float] = None,
    ) -> None:
        """
        전체 드론 편대 1 스텝 업데이트.
        기존 apply_boids_to_units()의 3D 확장.
        """
        forces = []
        for drone in drones:
            f = self.calculate_force(
                drone, drones, target, obstacles, desired_altitude
            )
            forces.append(f)

        for drone, f in zip(drones, forces):
            drone.update(f, dt)
