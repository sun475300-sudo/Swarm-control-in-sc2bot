# -*- coding: utf-8 -*-
"""
UTM (Unmanned Traffic Management) Module

SC2 Zerg 군집 제어 로직을 3D 드론 교통 관제 시스템으로 확장한 모듈.
기존 2D 공간 분할, KD-트리, Boids 알고리즘을 3D(고도 포함)로 진화.

Portfolio: SC2 Swarm AI → Real-World Drone UTM
"""

from wicked_zerg_challenger.utm.types3d import Point3D, DroneState
from wicked_zerg_challenger.utm.voxel_grid import VoxelGrid
from wicked_zerg_challenger.utm.kdtree3d import KDTree3D
from wicked_zerg_challenger.utm.boids3d import Boids3DController
from wicked_zerg_challenger.utm.corridor import FlightCorridor, CorridorManager
from wicked_zerg_challenger.utm.collision_predictor import CollisionPredictor

__all__ = [
    "Point3D", "DroneState",
    "VoxelGrid", "KDTree3D",
    "Boids3DController",
    "FlightCorridor", "CorridorManager",
    "CollisionPredictor",
]
