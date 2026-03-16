# -*- coding: utf-8 -*-
"""
SC2-Swarm → Drone ATC: Animated GIF Generator
DRONAI(osamhack2021) 스타일의 움직이는 시각 자료 생성

생성되는 GIF:
  1. boids_swarm_attack.gif     — 저그 유닛 Boids 군집 공격 시뮬레이션
  2. formation_flight.gif       — 드론 편대 비행 (V자/원형/라인)
  3. collision_avoidance.gif    — 자동 충돌 회피 시뮬레이션
  4. sim_to_real_pipeline.gif   — Sim-to-Real 파이프라인 애니메이션
  5. authority_mode_switch.gif  — Authority Mode 전환 시각화

사용법:
    python generate_animated_gifs.py
"""

import os
import math
import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
from matplotlib.animation import FuncAnimation, PillowWriter
from matplotlib.patches import FancyArrowPatch, Circle

OUTPUT_DIR = os.path.dirname(os.path.abspath(__file__))
DPI = 100
FPS = 15


def save_gif(anim, name, fps=FPS):
    path = os.path.join(OUTPUT_DIR, f"{name}.gif")
    anim.save(path, writer=PillowWriter(fps=fps), dpi=DPI)
    print(f"  [GIF] {path}")
    plt.close("all")


# ═══════════════════════════════════════════════════════
# 1. Boids Swarm Attack Simulation
# ═══════════════════════════════════════════════════════

def gif_boids_swarm():
    """DRONAI 64기 편대처럼 저그 유닛 60기의 Boids 군집 공격"""
    print("[GIF 1] Boids Swarm Attack Simulation")

    np.random.seed(42)
    N = 60
    FRAMES = 80

    # 초기 위치 (하단 집결)
    pos = np.random.randn(N, 2) * 2.0 + np.array([0, -8])
    vel = np.zeros((N, 2))

    # 유닛 타입: 0=저글링(녹), 1=바퀴(짙은녹), 2=히드라(파), 3=뮤탈(보라)
    types = np.array([0]*20 + [1]*15 + [2]*15 + [3]*10)
    colors = ["#8BC34A", "#2E7D32", "#1976D2", "#7B1FA2"]
    sizes = [15, 25, 20, 18]
    markers = ["o", "s", "^", "D"]

    target = np.array([0, 10])  # 적 기지
    enemy_pos = np.random.randn(15, 2) * 1.5 + target

    # 프레임별 위치 시뮬레이션
    all_pos = [pos.copy()]
    for _ in range(FRAMES):
        new_pos = pos.copy()
        new_vel = vel.copy()
        for i in range(N):
            # Separation
            sep = np.zeros(2)
            neighbors = 0
            for j in range(N):
                if i != j:
                    diff = pos[i] - pos[j]
                    dist = np.linalg.norm(diff)
                    if dist < 1.8 and dist > 0:
                        sep += diff / (dist ** 2)
                        neighbors += 1

            # Alignment (이웃 속도 평균)
            ali = np.zeros(2)
            if neighbors > 0:
                for j in range(N):
                    if i != j and np.linalg.norm(pos[i] - pos[j]) < 3.0:
                        ali += vel[j]
                ali /= max(neighbors, 1)

            # Cohesion (그룹 중심)
            center = pos.mean(axis=0)
            coh = (center - pos[i]) * 0.05

            # Target seeking
            to_target = target - pos[i]
            dist_to_target = np.linalg.norm(to_target)
            seek = to_target / (dist_to_target + 1e-6) * 0.3

            # 뮤탈은 측면 우회
            if types[i] == 3:
                offset = np.array([3.0 * (1 if i % 2 == 0 else -1), 0])
                flank_target = target + offset
                seek = (flank_target - pos[i])
                seek = seek / (np.linalg.norm(seek) + 1e-6) * 0.35

            # 합성
            accel = sep * 1.5 + ali * 0.3 + coh * 0.5 + seek
            new_vel[i] = vel[i] * 0.85 + accel
            speed = np.linalg.norm(new_vel[i])
            max_speed = 0.4 if types[i] != 3 else 0.5
            if speed > max_speed:
                new_vel[i] = new_vel[i] / speed * max_speed
            new_pos[i] = pos[i] + new_vel[i]

        pos = new_pos
        vel = new_vel
        all_pos.append(pos.copy())

    # 애니메이션
    fig, ax = plt.subplots(figsize=(8, 10), facecolor="#0d1117")
    ax.set_facecolor("#0d1117")
    ax.set_xlim(-10, 10)
    ax.set_ylim(-12, 14)
    ax.set_aspect("equal")
    ax.axis("off")

    # 적 기지 (고정)
    ax.scatter(enemy_pos[:, 0], enemy_pos[:, 1], c="#F44336", s=80,
               marker="X", alpha=0.7, zorder=2)
    ax.text(0, 12.5, "ENEMY BASE", color="#F44336", ha="center",
            fontsize=14, fontweight="bold", family="monospace")

    # 점막 (Creep) 표시
    creep = plt.Rectangle((-6, -12), 12, 8, color="#4A148C", alpha=0.15)
    ax.add_patch(creep)
    ax.text(0, -11.5, "CREEP TERRITORY", color="#7B1FA2", ha="center",
            fontsize=9, alpha=0.5, family="monospace")

    # 유닛 scatter (타입별)
    scatters = []
    for t in range(4):
        mask = types == t
        sc = ax.scatter([], [], c=colors[t], s=sizes[t] * 3,
                        marker=markers[t], alpha=0.85, edgecolors="white",
                        linewidths=0.5, zorder=3)
        scatters.append((sc, mask))

    title = ax.text(0, 13.5, "", color="white", ha="center",
                    fontsize=16, fontweight="bold", family="monospace")
    frame_text = ax.text(-9.5, -11.5, "", color="#666", fontsize=9,
                         family="monospace")

    # 레전드
    legend_elements = [
        mpatches.Patch(color="#8BC34A", label=f"Zergling ×20"),
        mpatches.Patch(color="#2E7D32", label=f"Roach ×15"),
        mpatches.Patch(color="#1976D2", label=f"Hydralisk ×15"),
        mpatches.Patch(color="#7B1FA2", label=f"Mutalisk ×10"),
    ]
    ax.legend(handles=legend_elements, loc="upper left", fontsize=8,
              facecolor="#1a1a2e", edgecolor="#333", labelcolor="white")

    def update(frame):
        p = all_pos[frame]
        for sc, mask in scatters:
            sc.set_offsets(p[mask])
        title.set_text(f"BOIDS SWARM ATTACK — Frame {frame}/{FRAMES}")
        frame_text.set_text(f"Units: {N} | Boids: Sep×1.5 + Ali×0.3 + Coh×0.5")
        return [sc for sc, _ in scatters] + [title, frame_text]

    anim = FuncAnimation(fig, update, frames=len(all_pos), interval=66, blit=True)
    save_gif(anim, "boids_swarm_attack")


# ═══════════════════════════════════════════════════════
# 2. Drone Formation Flight
# ═══════════════════════════════════════════════════════

def gif_formation_flight():
    """DRONAI 원형 편대처럼 드론 편대 비행 (V → Circle → Line 전환)"""
    print("[GIF 2] Drone Formation Flight")

    N = 16
    FRAMES_PER_FORMATION = 40
    TRANSITION_FRAMES = 20

    def v_formation(n):
        """V자 편대"""
        pos = []
        for i in range(n):
            row = i // 2
            side = 1 if i % 2 == 0 else -1
            if i == 0:
                pos.append([0, 2])
            else:
                pos.append([side * row * 1.2, 2 - row * 0.8])
        return np.array(pos, dtype=float)

    def circle_formation(n, radius=4):
        """원형 편대"""
        angles = np.linspace(0, 2 * np.pi, n, endpoint=False)
        return np.stack([radius * np.cos(angles), radius * np.sin(angles)], axis=1)

    def line_formation(n):
        """라인 편대"""
        x = np.linspace(-6, 6, n)
        return np.stack([x, np.zeros(n)], axis=1)

    formations = [
        ("V-FORMATION", v_formation(N)),
        ("CIRCLE FORMATION", circle_formation(N)),
        ("LINE FORMATION", line_formation(N)),
    ]

    # 전체 프레임 계산
    all_frames = []
    all_labels = []

    for fi, (name, target_pos) in enumerate(formations):
        if fi == 0:
            current_pos = target_pos.copy()
        # 현재 위치 유지
        for _ in range(FRAMES_PER_FORMATION):
            # 약간의 흔들림 (바람 효과)
            noise = np.random.randn(N, 2) * 0.05
            frame_pos = current_pos + noise
            all_frames.append(frame_pos.copy())
            all_labels.append(name)

        # 다음 편대로 전이
        if fi < len(formations) - 1:
            next_pos = formations[fi + 1][1]
            for t in range(TRANSITION_FRAMES):
                alpha = t / TRANSITION_FRAMES
                # Smooth easing
                alpha = 0.5 - 0.5 * math.cos(alpha * math.pi)
                interp = current_pos * (1 - alpha) + next_pos * alpha
                noise = np.random.randn(N, 2) * 0.08
                all_frames.append(interp + noise)
                all_labels.append(f"TRANSITIONING...")
            current_pos = next_pos.copy()

    fig, ax = plt.subplots(figsize=(10, 8), facecolor="#0a1628")
    ax.set_facecolor("#0a1628")
    ax.set_xlim(-8, 8)
    ax.set_ylim(-6, 6)
    ax.set_aspect("equal")
    ax.axis("off")

    # 그리드 (비행 공역)
    for x in range(-8, 9, 2):
        ax.axvline(x, color="#1a2a4a", linewidth=0.3, alpha=0.5)
    for y in range(-6, 7, 2):
        ax.axhline(y, color="#1a2a4a", linewidth=0.3, alpha=0.5)

    sc = ax.scatter([], [], c="#00E5FF", s=80, marker="^",
                    edgecolors="#00BCD4", linewidths=1.5, zorder=3, alpha=0.9)

    # 드론 간 연결선 (통신 메쉬)
    lines = []
    for i in range(N):
        for j in range(i + 1, N):
            line, = ax.plot([], [], color="#00E5FF", alpha=0.1, linewidth=0.5)
            lines.append((line, i, j))

    title = ax.text(0, 5.3, "", color="#00E5FF", ha="center",
                    fontsize=16, fontweight="bold", family="monospace")
    info = ax.text(-7.5, -5.5, "", color="#4FC3F7", fontsize=9,
                   family="monospace")
    drone_count = ax.text(7.5, 5.3, f"DRONES: {N}", color="#4FC3F7",
                          fontsize=10, ha="right", family="monospace")

    def update(frame):
        p = all_frames[frame]
        sc.set_offsets(p)
        title.set_text(f"▲ {all_labels[frame]}")
        info.set_text(f"Frame {frame}/{len(all_frames)} | Spacing: 1.2m | Alt: 50m")

        # 연결선 업데이트 (가까운 드론 간만)
        for line, i, j in lines:
            dist = np.linalg.norm(p[i] - p[j])
            if dist < 4.0:
                line.set_data([p[i][0], p[j][0]], [p[i][1], p[j][1]])
                line.set_alpha(max(0, 0.15 - dist * 0.03))
            else:
                line.set_data([], [])

        return [sc, title, info] + [l for l, _, _ in lines]

    anim = FuncAnimation(fig, update, frames=len(all_frames), interval=66, blit=True)
    save_gif(anim, "formation_flight")


# ═══════════════════════════════════════════════════════
# 3. Collision Avoidance Simulation
# ═══════════════════════════════════════════════════════

def gif_collision_avoidance():
    """DRONAI 자동회피처럼 드론 간 충돌 회피 시뮬레이션"""
    print("[GIF 3] Collision Avoidance Simulation")

    N = 8
    FRAMES = 100
    SAFE_DIST = 1.5

    # 드론들이 서로 교차하는 경로 설정
    np.random.seed(7)
    start_angles = np.linspace(0, 2 * np.pi, N, endpoint=False)
    radius = 5.0

    start_pos = np.stack([radius * np.cos(start_angles),
                          radius * np.sin(start_angles)], axis=1)
    # 목표: 반대편
    end_pos = -start_pos

    # 시뮬레이션
    pos = start_pos.copy()
    vel = np.zeros((N, 2))
    all_pos = [pos.copy()]
    avoidance_events = []

    for f in range(FRAMES):
        new_pos = pos.copy()
        new_vel = vel.copy()
        frame_avoid = []

        for i in range(N):
            # 목표 방향
            to_goal = end_pos[i] - pos[i]
            dist_goal = np.linalg.norm(to_goal)
            if dist_goal < 0.3:
                new_vel[i] *= 0
                continue
            seek = to_goal / (dist_goal + 1e-6) * 0.15

            # 충돌 회피
            avoid = np.zeros(2)
            avoiding = False
            for j in range(N):
                if i == j:
                    continue
                diff = pos[i] - pos[j]
                dist = np.linalg.norm(diff)
                if dist < SAFE_DIST * 2 and dist > 0:
                    force = diff / (dist ** 2) * 2.0
                    avoid += force
                    if dist < SAFE_DIST * 1.2:
                        avoiding = True
                        frame_avoid.append((i, j))

            new_vel[i] = vel[i] * 0.7 + seek + avoid
            speed = np.linalg.norm(new_vel[i])
            if speed > 0.2:
                new_vel[i] = new_vel[i] / speed * 0.2
            new_pos[i] = pos[i] + new_vel[i]

        pos = new_pos
        vel = new_vel
        all_pos.append(pos.copy())
        avoidance_events.append(frame_avoid)

    # 애니메이션
    fig, ax = plt.subplots(figsize=(8, 8), facecolor="#0d1117")
    ax.set_facecolor("#0d1117")
    ax.set_xlim(-7, 7)
    ax.set_ylim(-7, 7)
    ax.set_aspect("equal")
    ax.axis("off")

    drone_colors = plt.cm.Set2(np.linspace(0, 1, N))

    # 목표점 (반투명)
    for i in range(N):
        ax.plot(end_pos[i][0], end_pos[i][1], "x",
                color=drone_colors[i], markersize=12, alpha=0.3)

    # 드론
    init_pos = all_pos[0]
    sc = ax.scatter(init_pos[:, 0], init_pos[:, 1], s=120, c=drone_colors,
                    marker="^", edgecolors="white", linewidths=1, zorder=3)

    # 안전 거리 원
    circles = []
    for i in range(N):
        c = plt.Circle((0, 0), SAFE_DIST, fill=False, color=drone_colors[i],
                        linestyle="--", linewidth=0.5, alpha=0)
        ax.add_patch(c)
        circles.append(c)

    # 경고 라인
    warn_lines = []
    for _ in range(N * N):
        line, = ax.plot([], [], color="#FF5252", linewidth=2, alpha=0)
        warn_lines.append(line)

    title = ax.text(0, 6.3, "", color="white", ha="center",
                    fontsize=14, fontweight="bold", family="monospace")
    status = ax.text(-6.5, -6.5, "", color="#4FC3F7", fontsize=9,
                     family="monospace")

    def update(frame):
        p = all_pos[frame]
        sc.set_offsets(p)

        # 안전 원 업데이트
        for i, c in enumerate(circles):
            c.center = (p[i][0], p[i][1])

        # 경고 초기화
        for wl in warn_lines:
            wl.set_data([], [])
            wl.set_alpha(0)

        # 근접 경고
        warn_count = 0
        wi = 0
        avoids = avoidance_events[min(frame, len(avoidance_events) - 1)]
        for i_a, j_a in avoids:
            if wi < len(warn_lines):
                warn_lines[wi].set_data(
                    [p[i_a][0], p[j_a][0]], [p[i_a][1], p[j_a][1]])
                warn_lines[wi].set_alpha(0.6)
                wi += 1
                warn_count += 1
                circles[i_a].set_alpha(0.4)
                circles[j_a].set_alpha(0.4)

        for i in range(N):
            if not any(i == a[0] or i == a[1] for a in avoids):
                circles[i].set_alpha(0)

        title.set_text(f"COLLISION AVOIDANCE — Frame {frame}")
        warn_text = f"⚠ AVOIDING: {warn_count}" if warn_count > 0 else "✓ CLEAR"
        status.set_text(f"Drones: {N} | Safe dist: {SAFE_DIST}m | {warn_text}")

        return [sc, title, status] + circles + warn_lines

    anim = FuncAnimation(fig, update, frames=len(all_pos), interval=66, blit=True)
    save_gif(anim, "collision_avoidance")


# ═══════════════════════════════════════════════════════
# 4. Sim-to-Real Pipeline Animation
# ═══════════════════════════════════════════════════════

def gif_sim_to_real():
    """Sim-to-Real 파이프라인 단계별 진행 애니메이션"""
    print("[GIF 4] Sim-to-Real Pipeline")

    FRAMES = 120

    fig, ax = plt.subplots(figsize=(12, 5), facecolor="#0d1117")
    ax.set_facecolor("#0d1117")
    ax.set_xlim(-1, 13)
    ax.set_ylim(-1.5, 3)
    ax.set_aspect("auto")
    ax.axis("off")

    stages = [
        (1.5, "SC2\nSimulation", "#1565C0", "🎮 Boids + FSM\n10,000+ games"),
        (4.5, "3D Sim\n(Gazebo)", "#6A1B9A", "🖥️ ROS2 + Gazebo\n2D→3D transfer"),
        (7.5, "Real Drone\n(PX4)", "#2E7D32", "🚁 Pixhawk + RPi\n3-drone flight"),
        (10.5, "ATC\nScale-up", "#E65100", "✈️ 100+ drones\nCity airspace"),
    ]

    # 화살표
    for i in range(3):
        ax.annotate("", xy=(stages[i + 1][0] - 0.8, 1.5),
                     xytext=(stages[i][0] + 0.8, 1.5),
                     arrowprops=dict(arrowstyle="->", color="#555",
                                     lw=2, connectionstyle="arc3,rad=0"))

    # 단계 박스 (정적)
    boxes = []
    for x, label, col, desc in stages:
        rect = mpatches.FancyBboxPatch(
            (x - 0.8, 0.8), 1.6, 1.4,
            boxstyle="round,pad=0.1", facecolor=col, alpha=0.15,
            edgecolor=col, linewidth=2)
        ax.add_patch(rect)
        boxes.append(rect)
        ax.text(x, 1.5, label, color="white", ha="center", va="center",
                fontsize=11, fontweight="bold", family="monospace")
        ax.text(x, 0.2, desc, color="#888", ha="center", va="center",
                fontsize=7, family="monospace")

    # 프로그레스 바
    progress_bg = mpatches.FancyBboxPatch(
        (0.5, -0.8), 11, 0.3, boxstyle="round,pad=0.05",
        facecolor="#1a1a2e", edgecolor="#333")
    ax.add_patch(progress_bg)

    progress_bar = mpatches.FancyBboxPatch(
        (0.5, -0.8), 0.1, 0.3, boxstyle="round,pad=0.05",
        facecolor="#00E5FF", edgecolor="none")
    ax.add_patch(progress_bar)

    # 이동 포인트
    dot, = ax.plot([], [], "o", color="#00E5FF", markersize=12, zorder=5)
    stage_label = ax.text(6, 2.7, "", color="#00E5FF", ha="center",
                          fontsize=13, fontweight="bold", family="monospace")
    pct_text = ax.text(6, -1.2, "", color="#4FC3F7", ha="center",
                       fontsize=10, family="monospace")

    def update(frame):
        progress = frame / FRAMES
        stage_idx = min(int(progress * 4), 3)

        # 프로그레스 바 업데이트
        bar_width = max(0.1, progress * 11)
        progress_bar.set_width(bar_width)

        # 이동 점
        x = 1.5 + progress * 9
        dot.set_data([x], [1.5])

        # 현재 단계 하이라이트
        for i, box in enumerate(boxes):
            if i == stage_idx:
                box.set_alpha(0.4)
                box.set_linewidth(3)
            else:
                box.set_alpha(0.15)
                box.set_linewidth(2)

        stage_names = ["SC2 Simulation", "3D Simulation", "Real Drone", "ATC Scale-up"]
        stage_label.set_text(f"▶ {stage_names[stage_idx]}")
        pct_text.set_text(f"Progress: {progress * 100:.0f}%")

        return [dot, progress_bar, stage_label, pct_text] + boxes

    anim = FuncAnimation(fig, update, frames=FRAMES, interval=66, blit=True)
    save_gif(anim, "sim_to_real_pipeline")


# ═══════════════════════════════════════════════════════
# 5. Authority Mode Switch Visualization
# ═══════════════════════════════════════════════════════

def gif_authority_mode():
    """Authority Mode 실시간 전환 시뮬레이션"""
    print("[GIF 5] Authority Mode Switch")

    FRAMES = 120

    # 시나리오: BALANCED → EMERGENCY → COMBAT → BALANCED → ECONOMY
    scenario = [
        (0, 30, "BALANCED", "#2196F3"),
        (30, 50, "EMERGENCY", "#F44336"),
        (50, 75, "COMBAT", "#FF9800"),
        (75, 95, "BALANCED", "#2196F3"),
        (95, 120, "ECONOMY", "#4CAF50"),
    ]

    # 리소스 시뮬레이션
    np.random.seed(10)
    minerals = np.zeros(FRAMES)
    army_supply = np.zeros(FRAMES)
    threat_level = np.zeros(FRAMES)

    for start, end, mode, _ in scenario:
        for f in range(start, min(end, FRAMES)):
            if mode == "BALANCED":
                minerals[f] = 300 + np.random.randn() * 30
                army_supply[f] = 80 + np.random.randn() * 10
                threat_level[f] = 30 + np.random.randn() * 5
            elif mode == "EMERGENCY":
                minerals[f] = 150 - (f - start) * 3 + np.random.randn() * 20
                army_supply[f] = 50 + (f - start) * 2 + np.random.randn() * 5
                threat_level[f] = 90 + np.random.randn() * 5
            elif mode == "COMBAT":
                minerals[f] = 100 + np.random.randn() * 20
                army_supply[f] = 100 + np.random.randn() * 8
                threat_level[f] = 60 - (f - start) * 1 + np.random.randn() * 5
            elif mode == "ECONOMY":
                minerals[f] = 400 + (f - start) * 5 + np.random.randn() * 20
                army_supply[f] = 60 + np.random.randn() * 5
                threat_level[f] = 10 + np.random.randn() * 3

    fig, axes = plt.subplots(3, 1, figsize=(10, 7), facecolor="#0d1117",
                              gridspec_kw={"height_ratios": [2, 1, 1]})
    for ax_ in axes:
        ax_.set_facecolor("#0d1117")
        ax_.tick_params(colors="#666")
        for spine in ax_.spines.values():
            spine.set_color("#333")

    # 상단: 모드 표시
    ax_mode = axes[0]
    ax_mode.set_xlim(0, FRAMES)
    ax_mode.set_ylim(0, 1)
    ax_mode.axis("off")

    mode_text = ax_mode.text(0.5, 0.5, "", transform=ax_mode.transAxes,
                              ha="center", va="center", fontsize=28,
                              fontweight="bold", family="monospace")
    event_text = ax_mode.text(0.5, 0.15, "", transform=ax_mode.transAxes,
                               ha="center", va="center", fontsize=11,
                               color="#888", family="monospace")

    # 중간: 리소스
    ax_res = axes[1]
    ax_res.set_xlim(0, FRAMES)
    ax_res.set_ylim(0, 600)
    ax_res.set_ylabel("Resources", color="#888", fontsize=9)
    line_min, = ax_res.plot([], [], color="#FFD700", linewidth=1.5, label="Minerals")
    line_army, = ax_res.plot([], [], color="#4FC3F7", linewidth=1.5, label="Army Supply")
    ax_res.legend(fontsize=7, facecolor="#1a1a2e", edgecolor="#333",
                  labelcolor="white", loc="upper right")

    # 하단: 위협
    ax_threat = axes[2]
    ax_threat.set_xlim(0, FRAMES)
    ax_threat.set_ylim(0, 100)
    ax_threat.set_ylabel("Threat %", color="#888", fontsize=9)
    ax_threat.set_xlabel("Game Time (frames)", color="#888", fontsize=9)
    line_threat, = ax_threat.plot([], [], color="#F44336", linewidth=1.5)
    threat_fill = None

    events = {
        30: "🚨 RUSH DETECTED!",
        50: "⚔️ Rush Defended → Combat",
        75: "✅ Threat Cleared",
        95: "💰 Coast Clear → Economy",
    }

    def update(frame):
        nonlocal threat_fill
        # 현재 모드 찾기
        current_mode = "BALANCED"
        current_color = "#2196F3"
        for start, end, mode, col in scenario:
            if start <= frame < end:
                current_mode = mode
                current_color = col
                break

        mode_text.set_text(current_mode)
        mode_text.set_color(current_color)

        # 이벤트 표시
        if frame in events:
            event_text.set_text(events[frame])
        elif frame % 3 == 0:
            event_text.set_text("")

        # 리소스 라인
        x = list(range(frame + 1))
        line_min.set_data(x, minerals[:frame + 1])
        line_army.set_data(x, army_supply[:frame + 1])
        line_threat.set_data(x, threat_level[:frame + 1])

        # 위협 배경색
        if threat_fill:
            threat_fill.remove()
        threat_fill = ax_threat.fill_between(
            x, threat_level[:frame + 1], alpha=0.2, color="#F44336")

        return [mode_text, event_text, line_min, line_army, line_threat]

    plt.tight_layout()
    anim = FuncAnimation(fig, update, frames=FRAMES, interval=83, blit=False)
    save_gif(anim, "authority_mode_switch")


# ═══════════════════════════════════════════════════════
# Main
# ═══════════════════════════════════════════════════════

if __name__ == "__main__":
    print("=" * 60)
    print("SC2-Swarm: Animated GIF Generator (DRONAI Style)")
    print("=" * 60)

    gif_boids_swarm()
    gif_formation_flight()
    gif_collision_avoidance()
    gif_sim_to_real()
    gif_authority_mode()

    print("\n" + "=" * 60)
    gifs = [f for f in os.listdir(OUTPUT_DIR) if f.endswith(".gif")]
    print(f"Complete! {len(gifs)} GIF files generated:")
    for g in sorted(gifs):
        size = os.path.getsize(os.path.join(OUTPUT_DIR, g)) / 1024
        print(f"  {g} ({size:.0f} KB)")
    print(f"\nOutput: {OUTPUT_DIR}")
    print("=" * 60)
