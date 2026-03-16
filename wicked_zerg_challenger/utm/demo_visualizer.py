# -*- coding: utf-8 -*-
"""
3D UTM Demo Visualizer — Portfolio Showcase

matplotlib으로 드론 편대 비행, 충돌 회피, 비행 회랑을 3D 시각화.
GIF/MP4 녹화 기능 포함 (포트폴리오용).

실행: python -m wicked_zerg_challenger.utm.demo_visualizer
"""

from __future__ import annotations

import math
import sys
from typing import List, Optional

import numpy as np

from wicked_zerg_challenger.utm.types3d import DroneState, Point3D
from wicked_zerg_challenger.utm.boids3d import Boids3DController
from wicked_zerg_challenger.utm.collision_predictor import CollisionPredictor
from wicked_zerg_challenger.utm.corridor import CorridorManager


def create_demo_drones(n: int = 10, spread: float = 100.0) -> List[DroneState]:
    """데모용 드론 편대 생성."""
    drones = []
    for i in range(n):
        angle = 2 * math.pi * i / n
        r = spread * 0.3
        x = spread / 2 + r * math.cos(angle)
        y = spread / 2 + r * math.sin(angle)
        z = 40.0 + np.random.uniform(-5, 5)

        drone = DroneState(
            id=i,
            position=Point3D(x, y, z),
            velocity=np.array([
                np.random.uniform(-2, 2),
                np.random.uniform(-2, 2),
                np.random.uniform(-0.5, 0.5),
            ]),
            max_speed=12.0,
        )
        drones.append(drone)
    return drones


def run_simulation(
    drones: List[DroneState],
    steps: int = 200,
    dt: float = 0.1,
    target: Optional[Point3D] = None,
) -> List[List[Point3D]]:
    """시뮬레이션 실행, 궤적 기록."""
    boids = Boids3DController()
    predictor = CollisionPredictor()
    trajectories: List[List[Point3D]] = [[] for _ in drones]

    for step in range(steps):
        # 충돌 검사
        alerts = predictor.check_all_pairs(drones)
        for alert in alerts:
            if alert.severity in ("critical", "imminent"):
                # 관련 드론에 회피력 추가 적용
                drone_a = next(d for d in drones if d.id == alert.drone_a_id)
                drone_b = next(d for d in drones if d.id == alert.drone_b_id)
                avoid_a = predictor.compute_avoidance_vector(drone_a, drone_b, alert.ttc)
                avoid_b = predictor.compute_avoidance_vector(drone_b, drone_a, alert.ttc)
                drone_a.velocity += avoid_a * dt
                drone_b.velocity += avoid_b * dt

        # Boids 스텝
        boids.step(drones, dt=dt, target=target, desired_altitude=45.0)

        # 궤적 기록
        for i, drone in enumerate(drones):
            trajectories[i].append(
                Point3D(drone.position.x, drone.position.y, drone.position.z)
            )

    return trajectories


def visualize(
    drones: List[DroneState],
    trajectories: List[List[Point3D]],
    corridor_mgr: Optional[CorridorManager] = None,
    save_path: Optional[str] = None,
):
    """3D 시각화. matplotlib 사용."""
    try:
        import matplotlib.pyplot as plt
        from mpl_toolkits.mplot3d import Axes3D  # noqa: F401
    except ImportError:
        print("matplotlib 필요: pip install matplotlib")
        return

    fig = plt.figure(figsize=(14, 10))
    ax = fig.add_subplot(111, projection="3d")

    # 색상 팔레트
    colors = plt.cm.tab10(np.linspace(0, 1, len(drones)))

    # 궤적 그리기
    for i, traj in enumerate(trajectories):
        xs = [p.x for p in traj]
        ys = [p.y for p in traj]
        zs = [p.z for p in traj]
        ax.plot(xs, ys, zs, color=colors[i], alpha=0.4, linewidth=0.8)

    # 최종 드론 위치 + 속도 벡터
    for i, drone in enumerate(drones):
        p = drone.position
        v = drone.velocity
        ax.scatter(p.x, p.y, p.z, color=colors[i], s=80, marker="^",
                   edgecolors="black", linewidth=0.5, zorder=5)
        ax.quiver(p.x, p.y, p.z, v[0], v[1], v[2],
                  color=colors[i], alpha=0.8, length=3.0, arrow_length_ratio=0.3)
        ax.text(p.x, p.y, p.z + 2, f"D{drone.id}", fontsize=7, ha="center")

    # 비행 회랑 표시
    if corridor_mgr:
        for cid, corridor in corridor_mgr.corridors.items():
            wps = corridor.waypoints
            xs = [p.x for p in wps]
            ys = [p.y for p in wps]
            zs = [p.z for p in wps]
            ax.plot(xs, ys, zs, "b--", alpha=0.5, linewidth=2, label=f"Corridor {cid}")
            ax.scatter(xs[0], ys[0], zs[0], color="green", s=100, marker="o", zorder=6)
            ax.scatter(xs[-1], ys[-1], zs[-1], color="red", s=100, marker="s", zorder=6)

    # 고도층 표시 (반투명 평면)
    from wicked_zerg_challenger.utm.corridor import ALTITUDE_LAYERS
    xlim = ax.get_xlim()
    ylim = ax.get_ylim()
    for name, (z_min, z_max) in ALTITUDE_LAYERS.items():
        xx, yy = np.meshgrid(
            np.linspace(xlim[0], xlim[1], 2),
            np.linspace(ylim[0], ylim[1], 2),
        )
        ax.plot_surface(xx, yy, np.full_like(xx, z_min),
                        alpha=0.05, color="gray")

    ax.set_xlabel("X (m)")
    ax.set_ylabel("Y (m)")
    ax.set_zlabel("Altitude (m)")
    ax.set_title("UTM Drone Swarm — SC2 Boids → 3D Flight Control", fontsize=13)

    if save_path:
        plt.savefig(save_path, dpi=150, bbox_inches="tight")
        print(f"저장 완료: {save_path}")
    else:
        plt.show()

    plt.close()


def main():
    """데모 실행."""
    print("=" * 60)
    print("  SC2 Swarm AI → UTM Drone Control Demo")
    print("  3D Boids + TTC Collision Prediction + Flight Corridors")
    print("=" * 60)

    # 드론 편대 생성
    drones = create_demo_drones(n=10, spread=200.0)
    print(f"\n드론 {len(drones)}대 편대 생성 완료")

    # 비행 회랑 생성
    corridor_mgr = CorridorManager()
    corridor_mgr.create_corridor(
        "ROUTE-01",
        Point3D(20.0, 20.0, 5.0),
        Point3D(180.0, 180.0, 5.0),
        altitude_layer="medium",
    )
    corridor_mgr.create_corridor(
        "ROUTE-02",
        Point3D(180.0, 20.0, 5.0),
        Point3D(20.0, 180.0, 5.0),
        altitude_layer="high",
    )
    print(f"비행 회랑 {len(corridor_mgr.corridors)}개 생성")

    # 목표 지점 설정
    target = Point3D(150.0, 150.0, 45.0)
    print(f"목표 지점: {target}")

    # 시뮬레이션 실행
    print("\n시뮬레이션 진행 중 (200 스텝)...")
    trajectories = run_simulation(drones, steps=200, dt=0.1, target=target)
    print("시뮬레이션 완료!")

    # 최종 위치 출력
    print("\n--- 최종 드론 위치 ---")
    for d in drones:
        print(f"  Drone {d.id}: pos={d.position}, speed={d.speed:.1f} m/s")

    # 충돌 검사 결과
    predictor = CollisionPredictor()
    alerts = predictor.check_all_pairs(drones)
    if alerts:
        print(f"\n경고: {len(alerts)}건의 충돌 위험 감지")
        for a in alerts[:3]:
            print(f"  D{a.drone_a_id}↔D{a.drone_b_id}: TTC={a.ttc:.1f}s, "
                  f"min_dist={a.min_distance:.1f}m [{a.severity}]")
    else:
        print("\n충돌 위험 없음 — 모든 드론 안전 분리 유지")

    # 시각화
    print("\n3D 시각화 렌더링 중...")
    save_file = None
    if "--save" in sys.argv:
        save_file = "utm_demo.png"
    visualize(drones, trajectories, corridor_mgr, save_path=save_file)


if __name__ == "__main__":
    main()
