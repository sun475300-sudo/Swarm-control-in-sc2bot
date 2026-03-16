# -*- coding: utf-8 -*-
"""
SC2 Swarm Control → Drone ATC: 3D Presentation Visuals Generator
Plotly 기반 인터랙티브 3D 시각화 4파트 생성

사용법:
    python generate_3d_visuals.py          # HTML 인터랙티브 생성
    python generate_3d_visuals.py --png    # PNG 이미지도 함께 생성
"""

import os
import sys
import math
import numpy as np

import plotly.graph_objects as go
from plotly.subplots import make_subplots

OUTPUT_DIR = os.path.dirname(os.path.abspath(__file__))
EXPORT_PNG = "--png" in sys.argv


def save(fig, name, width=1200, height=800):
    """HTML 저장 + 선택적 PNG 내보내기"""
    html_path = os.path.join(OUTPUT_DIR, f"{name}.html")
    fig.write_html(html_path, include_plotlyjs="cdn")
    print(f"  [HTML] {html_path}")
    if EXPORT_PNG:
        png_path = os.path.join(OUTPUT_DIR, f"{name}.png")
        fig.write_image(png_path, width=width, height=height, scale=2)
        print(f"  [PNG]  {png_path}")


# ═══════════════════════════════════════════════════════
# Part 1: SC2 Bot Architecture (FSM + RL Hybrid) — 3D
# ═══════════════════════════════════════════════════════

def part1_fsm_3d():
    """1-1. Game Phase FSM을 3D 타임라인으로 표현"""
    print("[Part 1-1] FSM Game Phase 3D Timeline")

    phases = ["OPENING", "EARLY GAME", "MID GAME", "LATE GAME"]
    times = [0, 3, 6, 12]  # 분
    colors = ["#4CAF50", "#2196F3", "#FF9800", "#F44336"]

    # 각 단계별 서브 액션
    sub_actions = {
        "OPENING": ["Build Pool", "Queen ×2", "Lings ×8", "Natural Exp"],
        "EARLY GAME": ["Scout Enemy", "Identify Race", "Select Comp", "Drone Up"],
        "MID GAME": ["3rd Base", "Upgrades +1/+1", "Army Build", "Engage"],
        "LATE GAME": ["Max Supply", "Tech Switch", "Multi-Prong", "Final Push"],
    }

    fig = go.Figure()

    # 메인 타임라인 (3D 파이프)
    for i, (phase, t, col) in enumerate(zip(phases, times, colors)):
        # 메인 노드 (큰 구)
        fig.add_trace(go.Scatter3d(
            x=[t], y=[0], z=[2],
            mode="markers+text",
            marker=dict(size=20, color=col, opacity=0.9,
                        line=dict(width=2, color="white")),
            text=[phase],
            textposition="top center",
            textfont=dict(size=14, color=col, family="Arial Black"),
            name=phase,
            hovertext=f"{phase}<br>Time: {t}:00<br>Actions: {', '.join(sub_actions[phase])}",
        ))

        # 서브 액션 (작은 구, 아래로 배치)
        actions = sub_actions[phase]
        for j, act in enumerate(actions):
            angle = (j / len(actions)) * math.pi - math.pi / 2
            ay = math.sin(angle) * 1.5
            az = math.cos(angle) * 1.0
            fig.add_trace(go.Scatter3d(
                x=[t], y=[ay], z=[az],
                mode="markers+text",
                marker=dict(size=8, color=col, opacity=0.6),
                text=[act],
                textposition="bottom center",
                textfont=dict(size=9),
                showlegend=False,
                hovertext=f"{phase} → {act}",
            ))
            # 연결선
            fig.add_trace(go.Scatter3d(
                x=[t, t], y=[0, ay], z=[2, az],
                mode="lines",
                line=dict(color=col, width=2, dash="dot"),
                showlegend=False,
                hoverinfo="skip",
            ))

    # 타임라인 연결선
    fig.add_trace(go.Scatter3d(
        x=times, y=[0] * 4, z=[2] * 4,
        mode="lines",
        line=dict(color="#333", width=5),
        showlegend=False,
        hoverinfo="skip",
    ))

    fig.update_layout(
        title=dict(text="SC2 Bot: Game Phase FSM (3D Timeline)",
                   font=dict(size=20)),
        scene=dict(
            xaxis=dict(title="Game Time (min)", range=[-1, 14]),
            yaxis=dict(title="Action Space", range=[-2, 2]),
            zaxis=dict(title="Phase Level", range=[-1, 4]),
            camera=dict(eye=dict(x=1.5, y=1.5, z=1.0)),
            bgcolor="#f8f9fa",
        ),
        margin=dict(l=0, r=0, t=60, b=0),
        template="plotly_white",
    )
    save(fig, "part1_1_fsm_timeline")


def part1_authority_3d():
    """1-2. Authority Mode를 3D 상태 전이 그래프로 표현"""
    print("[Part 1-2] Authority Mode 3D State Graph")

    modes = ["EMERGENCY", "COMBAT", "ECONOMY", "BALANCED"]
    positions = {
        "EMERGENCY": (0, 0, 3),
        "COMBAT":    (2, 1, 2),
        "ECONOMY":   (-2, 1, 1),
        "BALANCED":  (0, -1, 0),
    }
    colors_map = {
        "EMERGENCY": "#F44336",
        "COMBAT":    "#FF9800",
        "ECONOMY":   "#4CAF50",
        "BALANCED":  "#2196F3",
    }
    sizes = {"EMERGENCY": 25, "COMBAT": 20, "ECONOMY": 20, "BALANCED": 22}

    transitions = [
        ("BALANCED", "EMERGENCY", "Rush Detected"),
        ("BALANCED", "COMBAT", "Medium Threat"),
        ("BALANCED", "ECONOMY", "Coast Clear"),
        ("EMERGENCY", "COMBAT", "Rush Defended"),
        ("COMBAT", "BALANCED", "Threat Cleared"),
        ("ECONOMY", "BALANCED", "Drones Saturated"),
        ("ECONOMY", "EMERGENCY", "Sudden Attack"),
    ]

    fig = go.Figure()

    # 노드
    for mode in modes:
        x, y, z = positions[mode]
        fig.add_trace(go.Scatter3d(
            x=[x], y=[y], z=[z],
            mode="markers+text",
            marker=dict(size=sizes[mode], color=colors_map[mode], opacity=0.9,
                        line=dict(width=2, color="white")),
            text=[mode],
            textposition="top center",
            textfont=dict(size=13, color=colors_map[mode], family="Arial Black"),
            name=mode,
            hovertext=f"Mode: {mode}",
        ))

    # 전이 화살표 (선)
    for src, dst, label in transitions:
        sx, sy, sz = positions[src]
        dx, dy, dz = positions[dst]
        # 중간점 살짝 올려서 곡선 효과
        mx, my, mz = (sx + dx) / 2, (sy + dy) / 2, (sz + dz) / 2 + 0.5
        fig.add_trace(go.Scatter3d(
            x=[sx, mx, dx], y=[sy, my, dy], z=[sz, mz, dz],
            mode="lines+text",
            line=dict(color="#666", width=3),
            text=["", label, ""],
            textposition="top center",
            textfont=dict(size=9, color="#666"),
            showlegend=False,
        ))
        # 화살표 끝 (작은 콘)
        fig.add_trace(go.Cone(
            x=[dx], y=[dy], z=[dz],
            u=[dx - mx], v=[dy - my], w=[dz - mz],
            sizemode="absolute", sizeref=0.15,
            colorscale=[[0, "#666"], [1, "#666"]],
            showscale=False, showlegend=False,
        ))

    fig.update_layout(
        title=dict(text="Authority Mode: Dynamic Priority Switching (3D)",
                   font=dict(size=20)),
        scene=dict(
            xaxis=dict(title="", showticklabels=False, showgrid=False),
            yaxis=dict(title="", showticklabels=False, showgrid=False),
            zaxis=dict(title="Priority Level", range=[-1, 4.5]),
            camera=dict(eye=dict(x=1.8, y=1.2, z=1.0)),
            bgcolor="#f8f9fa",
        ),
        margin=dict(l=0, r=0, t=60, b=0),
        template="plotly_white",
    )
    save(fig, "part1_2_authority_mode")


def part1_hybrid_3d():
    """1-3. Rule-Based + RL Hybrid Architecture를 3D 레이어로 표현"""
    print("[Part 1-3] Rule + RL Hybrid Architecture 3D")

    fig = go.Figure()

    # 레이어 정의 (z축 = 레이어 높이)
    layers = [
        {"name": "Input Layer", "z": 0, "color": "#E3F2FD",
         "nodes": ["Units", "Resources", "Map", "Time"]},
        {"name": "Rule Engine", "z": 1.5, "color": "#C8E6C9",
         "nodes": ["FSM", "Authority", "Triggers"]},
        {"name": "RL Engine", "z": 1.5, "color": "#BBDEFB",
         "nodes": ["DQN", "Hierarchical RL", "Reward"]},
        {"name": "Decision Fusion", "z": 3, "color": "#FFF9C4",
         "nodes": ["Rule 70% + RL 30%"]},
        {"name": "Output", "z": 4.5, "color": "#FFCDD2",
         "nodes": ["Build", "Move", "Ability", "Expand"]},
    ]

    for layer in layers:
        z = layer["z"]
        nodes = layer["nodes"]
        n = len(nodes)

        # 레이어 플레인 (반투명 사각형)
        plane_size = max(n * 1.2, 3)
        xx = np.array([-plane_size, plane_size, plane_size, -plane_size]) / 2
        yy = np.array([-0.8, -0.8, 0.8, 0.8])
        zz = np.array([z, z, z, z])

        fig.add_trace(go.Mesh3d(
            x=list(xx), y=list(yy), z=list(zz),
            i=[0, 0], j=[1, 2], k=[2, 3],
            color=layer["color"], opacity=0.3,
            name=layer["name"],
            hoverinfo="name",
        ))

        # 노드들
        for i, node in enumerate(nodes):
            x_pos = (i - (n - 1) / 2) * 1.5
            # Rule Engine은 y=-0.3, RL Engine은 y=+0.3
            y_off = 0
            if layer["name"] == "Rule Engine":
                y_off = -0.4
            elif layer["name"] == "RL Engine":
                y_off = 0.4

            fig.add_trace(go.Scatter3d(
                x=[x_pos], y=[y_off], z=[z],
                mode="markers+text",
                marker=dict(size=10, color=layer["color"],
                            line=dict(width=2, color="#333"), opacity=0.9),
                text=[node],
                textposition="top center",
                textfont=dict(size=10),
                showlegend=False,
                hovertext=f"{layer['name']}: {node}",
            ))

    # 레이어 간 연결선 (대표)
    connections = [
        (0, 0, 0, 0, -0.4, 1.5),    # Input → Rule
        (0, 0, 0, 0, 0.4, 1.5),     # Input → RL
        (0, -0.4, 1.5, 0, 0, 3),    # Rule → Fusion
        (0, 0.4, 1.5, 0, 0, 3),     # RL → Fusion
        (0, 0, 3, 0, 0, 4.5),       # Fusion → Output
    ]
    line_colors = ["#666", "#666", "#2E7D32", "#1565C0", "#E65100"]

    for (x1, y1, z1, x2, y2, z2), col in zip(connections, line_colors):
        fig.add_trace(go.Scatter3d(
            x=[x1, x2], y=[y1, y2], z=[z1, z2],
            mode="lines",
            line=dict(color=col, width=4),
            showlegend=False,
            hoverinfo="skip",
        ))

    # RL 피드백 루프 (점선)
    fig.add_trace(go.Scatter3d(
        x=[0, 2.5, 2.5, 0.75], y=[0, 0, 0.4, 0.4], z=[4.5, 4.5, 1.5, 1.5],
        mode="lines",
        line=dict(color="#1565C0", width=2, dash="dash"),
        showlegend=False,
        hovertext="RL Feedback Loop",
    ))

    fig.update_layout(
        title=dict(text="Rule-Based + RL Hybrid Architecture (3D Layers)",
                   font=dict(size=20)),
        scene=dict(
            xaxis=dict(title="", showticklabels=False, showgrid=False),
            yaxis=dict(title="", showticklabels=False, showgrid=False),
            zaxis=dict(title="Processing Layer", range=[-0.5, 5.5]),
            camera=dict(eye=dict(x=1.6, y=1.6, z=1.2)),
            bgcolor="#f8f9fa",
        ),
        margin=dict(l=0, r=0, t=60, b=0),
        template="plotly_white",
    )
    save(fig, "part1_3_hybrid_architecture")


# ═══════════════════════════════════════════════════════
# Part 2: Operation Flow (Tactical Decision) — 3D
# ═══════════════════════════════════════════════════════

def part2_tactical_3d():
    """2-1. 전술 의사결정 5단계를 3D 나선형으로 표현"""
    print("[Part 2-1] Tactical Decision Chain 3D Spiral")

    phases = [
        ("SCOUT", "#2196F3", ["Overlord Scout", "Identify Race", "Threat Assess"]),
        ("DECIDE", "#9C27B0", ["Strategy Select", "Comp Choose", "Timing"]),
        ("RALLY", "#FF9800", ["Rally Point", "Group Form", "Formation"]),
        ("ENGAGE", "#F44336", ["Boids Attack", "Micro Control", "Spell Cast"]),
        ("EVALUATE", "#4CAF50", ["Result Check", "RL Learn", "Adapt Strategy"]),
    ]

    fig = go.Figure()

    # 나선형 배치 (위에서 아래로, 회전)
    for i, (name, col, subs) in enumerate(phases):
        angle = i * (2 * math.pi / 5)
        radius = 2.5
        x = radius * math.cos(angle)
        y = radius * math.sin(angle)
        z = 4 - i * 0.8  # 위에서 아래로

        # 메인 노드
        fig.add_trace(go.Scatter3d(
            x=[x], y=[y], z=[z],
            mode="markers+text",
            marker=dict(size=18, color=col, opacity=0.9,
                        line=dict(width=2, color="white"),
                        symbol="diamond"),
            text=[f"Phase {i + 1}\n{name}"],
            textposition="top center",
            textfont=dict(size=12, color=col, family="Arial Black"),
            name=name,
        ))

        # 서브 노드
        for j, sub in enumerate(subs):
            sub_angle = angle + (j - 1) * 0.3
            sub_r = 1.0
            sx = x + sub_r * math.cos(sub_angle)
            sy = y + sub_r * math.sin(sub_angle)
            sz = z - 0.3

            fig.add_trace(go.Scatter3d(
                x=[sx], y=[sy], z=[sz],
                mode="markers+text",
                marker=dict(size=7, color=col, opacity=0.5),
                text=[sub],
                textposition="bottom center",
                textfont=dict(size=8),
                showlegend=False,
            ))
            fig.add_trace(go.Scatter3d(
                x=[x, sx], y=[y, sy], z=[z, sz],
                mode="lines",
                line=dict(color=col, width=1, dash="dot"),
                showlegend=False, hoverinfo="skip",
            ))

        # 다음 단계 연결
        if i < len(phases) - 1:
            na = (i + 1) * (2 * math.pi / 5)
            nx = radius * math.cos(na)
            ny = radius * math.sin(na)
            nz = 4 - (i + 1) * 0.8
            fig.add_trace(go.Scatter3d(
                x=[x, nx], y=[y, ny], z=[z, nz],
                mode="lines",
                line=dict(color="#333", width=4),
                showlegend=False, hoverinfo="skip",
            ))

    # 순환 화살표 (마지막 → 처음)
    angle0 = 0
    anglelast = 4 * (2 * math.pi / 5)
    fig.add_trace(go.Scatter3d(
        x=[2.5 * math.cos(anglelast), 0, 2.5 * math.cos(angle0)],
        y=[2.5 * math.sin(anglelast), 0, 2.5 * math.sin(angle0)],
        z=[4 - 3.2, 2, 4],
        mode="lines",
        line=dict(color="#333", width=3, dash="dash"),
        showlegend=False,
        hovertext="Cycle: Evaluate → Scout",
    ))

    fig.update_layout(
        title=dict(text="Tactical Decision Chain (3D Spiral)",
                   font=dict(size=20)),
        scene=dict(
            xaxis=dict(title="", showticklabels=False, showgrid=False),
            yaxis=dict(title="", showticklabels=False, showgrid=False),
            zaxis=dict(title="Decision Flow", range=[-0.5, 5.5]),
            camera=dict(eye=dict(x=1.5, y=1.5, z=1.2)),
            bgcolor="#f8f9fa",
        ),
        margin=dict(l=0, r=0, t=60, b=0),
        template="plotly_white",
    )
    save(fig, "part2_1_tactical_spiral")


def part2_engagement_3d():
    """2-2. 교전 의사결정 플로우차트를 3D 트리로 표현"""
    print("[Part 2-2] Engagement Decision Tree 3D")

    fig = go.Figure()

    # 노드 정의: (id, label, x, y, z, color, size)
    nodes = [
        ("start",       "Army Ready",         0,    0,   5,   "#2196F3", 14),
        ("ratio",       "Power Ratio\n> 0.7?", 0,    0,   4,   "#FF9800", 12),
        ("weakness",    "Enemy\nWeakness?",    -1.5, 0,   3,   "#FF9800", 12),
        ("creep",       "On Creep?",           -1.5, -1,  2,   "#FF9800", 12),
        ("spell",       "Spell\nEnergy?",      -1.5, 1,   1,   "#FF9800", 12),
        ("wait",        "Wait &\nReinforce",    2,   0,   3.5, "#607D8B", 11),
        ("harass",      "Harass\nSquad",        0.5, 0,   2.5, "#9C27B0", 11),
        ("creep_push",  "Creep\nExpand",       -3,   -1,  1.5, "#795548", 11),
        ("full_engage", "FULL\nENGAGE",        -2.5, 1.5, 0,   "#4CAF50", 16),
        ("partial",     "Partial\nEngage",     -0.5, 1.5, 0,   "#FFC107", 13),
        ("victory",     "PUSH",               -2,    0,  -1,   "#4CAF50", 12),
        ("defeat",      "RETREAT",             0,    0,  -1,   "#F44336", 12),
    ]

    for nid, label, x, y, z, col, sz in nodes:
        fig.add_trace(go.Scatter3d(
            x=[x], y=[y], z=[z],
            mode="markers+text",
            marker=dict(size=sz, color=col, opacity=0.85,
                        line=dict(width=1.5, color="white")),
            text=[label],
            textposition="top center",
            textfont=dict(size=9),
            showlegend=False,
            hovertext=label.replace("\n", " "),
        ))

    # 연결선 (parent → child)
    edges = [
        ("start", "ratio"),
        ("ratio", "weakness", "Yes"),
        ("ratio", "wait", "No"),
        ("weakness", "creep", "Yes"),
        ("weakness", "harass", "No"),
        ("creep", "spell", "Yes"),
        ("creep", "creep_push", "No"),
        ("spell", "full_engage", "Yes"),
        ("spell", "partial", "No"),
        ("full_engage", "victory"),
        ("partial", "defeat"),
    ]

    node_map = {n[0]: (n[2], n[3], n[4]) for n in nodes}
    for edge in edges:
        src, dst = edge[0], edge[1]
        sx, sy, sz = node_map[src]
        dx, dy, dz = node_map[dst]
        label = edge[2] if len(edge) > 2 else ""
        fig.add_trace(go.Scatter3d(
            x=[sx, dx], y=[sy, dy], z=[sz, dz],
            mode="lines+text",
            line=dict(color="#888", width=3),
            text=["", label],
            textposition="middle right",
            textfont=dict(size=8, color="#333"),
            showlegend=False,
        ))

    fig.update_layout(
        title=dict(text="Engagement Decision Tree (3D)",
                   font=dict(size=20)),
        scene=dict(
            xaxis=dict(title="", showticklabels=False, showgrid=False),
            yaxis=dict(title="", showticklabels=False, showgrid=False),
            zaxis=dict(title="Decision Depth"),
            camera=dict(eye=dict(x=1.8, y=1.5, z=0.9)),
            bgcolor="#f8f9fa",
        ),
        margin=dict(l=0, r=0, t=60, b=0),
        template="plotly_white",
    )
    save(fig, "part2_2_engagement_tree")


# ═══════════════════════════════════════════════════════
# Part 3: Boids Swarm Simulation — 3D
# ═══════════════════════════════════════════════════════

def part3_boids_3d():
    """3-1. Boids 알고리즘 3D 시뮬레이션 (실제 입자 시스템)"""
    print("[Part 3-1] Boids Swarm 3D Simulation")

    np.random.seed(42)
    N = 60  # 유닛 수

    # 초기 위치: 아군 (아래쪽), 적군 (위쪽)
    ally_pos = np.random.randn(N, 3) * 1.5 + np.array([0, 0, 2])
    enemy_pos = np.random.randn(20, 3) * 1.0 + np.array([0, 0, 8])

    # 유닛 타입별 색상
    unit_types = []
    unit_colors = []
    for i in range(N):
        if i < 20:
            unit_types.append("Zergling")
            unit_colors.append("#8BC34A")
        elif i < 35:
            unit_types.append("Roach")
            unit_colors.append("#4CAF50")
        elif i < 45:
            unit_types.append("Hydralisk")
            unit_colors.append("#2196F3")
        else:
            unit_types.append("Mutalisk")
            unit_colors.append("#9C27B0")
            ally_pos[i][2] += 2  # 뮤탈은 더 높이

    # Boids 힘 시뮬레이션 (3프레임)
    frames = []
    positions = ally_pos.copy()

    target = np.array([0, 0, 8])  # 적 기지 방향

    for frame_idx in range(8):
        new_pos = positions.copy()
        for i in range(N):
            # Separation
            sep = np.zeros(3)
            for j in range(N):
                if i != j:
                    diff = positions[i] - positions[j]
                    dist = np.linalg.norm(diff)
                    if dist < 1.5 and dist > 0:
                        sep += diff / (dist * dist)

            # Alignment (average velocity toward target)
            ali = (target - positions[i])
            ali = ali / (np.linalg.norm(ali) + 1e-6)

            # Cohesion (move toward center of group)
            center = positions.mean(axis=0)
            coh = (center - positions[i]) * 0.1

            # Combined
            velocity = sep * 1.5 + ali * 0.8 + coh * 0.5
            speed = np.linalg.norm(velocity)
            if speed > 0.5:
                velocity = velocity / speed * 0.5

            new_pos[i] = positions[i] + velocity

        positions = new_pos
        frames.append(positions.copy())

    # 애니메이션 프레임 생성
    fig = go.Figure()

    # 초기 프레임 — 아군
    fig.add_trace(go.Scatter3d(
        x=frames[0][:, 0], y=frames[0][:, 1], z=frames[0][:, 2],
        mode="markers",
        marker=dict(
            size=[6 if t == "Zergling" else 8 if t == "Roach" else 7 for t in unit_types],
            color=unit_colors,
            opacity=0.85,
            line=dict(width=1, color="white"),
        ),
        text=unit_types,
        name="Zerg Army",
    ))

    # 적군 (고정)
    fig.add_trace(go.Scatter3d(
        x=enemy_pos[:, 0], y=enemy_pos[:, 1], z=enemy_pos[:, 2],
        mode="markers",
        marker=dict(size=8, color="#F44336", opacity=0.7, symbol="x",
                    line=dict(width=1, color="white")),
        name="Enemy",
    ))

    # 적 기지 표시
    fig.add_trace(go.Scatter3d(
        x=[0], y=[0], z=[9],
        mode="markers+text",
        marker=dict(size=15, color="#F44336", opacity=0.3, symbol="diamond"),
        text=["Enemy Base"],
        textposition="top center",
        showlegend=False,
    ))

    # 애니메이션 프레임
    anim_frames = []
    for fi, fpos in enumerate(frames):
        anim_frames.append(go.Frame(
            data=[
                go.Scatter3d(
                    x=fpos[:, 0], y=fpos[:, 1], z=fpos[:, 2],
                    mode="markers",
                    marker=dict(
                        size=[6 if t == "Zergling" else 8 if t == "Roach" else 7 for t in unit_types],
                        color=unit_colors,
                        opacity=0.85,
                        line=dict(width=1, color="white"),
                    ),
                ),
                go.Scatter3d(
                    x=enemy_pos[:, 0], y=enemy_pos[:, 1], z=enemy_pos[:, 2],
                ),
            ],
            name=f"frame_{fi}",
        ))

    fig.frames = anim_frames

    # 플레이/슬라이더
    fig.update_layout(
        title=dict(text="Boids Swarm Attack Simulation (3D)",
                   font=dict(size=20)),
        scene=dict(
            xaxis=dict(title="X", range=[-5, 5]),
            yaxis=dict(title="Y", range=[-5, 5]),
            zaxis=dict(title="Z (Height / Advance)", range=[-1, 11]),
            camera=dict(eye=dict(x=1.5, y=1.5, z=0.8)),
            bgcolor="#1a1a2e",
        ),
        paper_bgcolor="#1a1a2e",
        font=dict(color="white"),
        updatemenus=[dict(
            type="buttons",
            showactive=False,
            y=0,
            x=0.5,
            xanchor="center",
            buttons=[
                dict(label="▶ Play",
                     method="animate",
                     args=[None, dict(frame=dict(duration=400, redraw=True),
                                      fromcurrent=True)]),
                dict(label="⏸ Pause",
                     method="animate",
                     args=[[None], dict(frame=dict(duration=0, redraw=False),
                                        mode="immediate")]),
            ],
        )],
        sliders=[dict(
            active=0,
            steps=[dict(args=[[f"frame_{i}"],
                               dict(mode="immediate",
                                    frame=dict(duration=300, redraw=True))],
                         method="animate", label=f"T{i}")
                   for i in range(len(frames))],
            x=0.1, len=0.8,
            y=0, xanchor="left",
            currentvalue=dict(prefix="Frame: ", visible=True),
        )],
        margin=dict(l=0, r=0, t=60, b=60),
    )
    save(fig, "part3_1_boids_simulation")


def part3_forces_3d():
    """3-2. Boids 3대 힘 벡터 시각화"""
    print("[Part 3-2] Boids Force Vectors 3D")

    fig = go.Figure()

    # 중심 유닛
    fig.add_trace(go.Scatter3d(
        x=[0], y=[0], z=[0],
        mode="markers+text",
        marker=dict(size=15, color="#4CAF50", opacity=1,
                    line=dict(width=2, color="white")),
        text=["ME"],
        textposition="top center",
        textfont=dict(size=14, color="white", family="Arial Black"),
        name="Current Unit",
    ))

    # 이웃 유닛들
    neighbors = [
        (1.2, 0.5, 0.3), (-0.8, 1.0, -0.2), (0.3, -0.9, 0.5),
        (-1.0, -0.5, 0.1), (0.7, 0.8, -0.4),
    ]
    fig.add_trace(go.Scatter3d(
        x=[n[0] for n in neighbors],
        y=[n[1] for n in neighbors],
        z=[n[2] for n in neighbors],
        mode="markers",
        marker=dict(size=8, color="#81C784", opacity=0.6),
        name="Neighbors",
    ))

    # 힘 벡터들
    forces = [
        ("Separation (×1.5)", [-0.8, -0.3, 0.1], "#F44336"),
        ("Alignment (×1.0)", [0.5, 0.7, 0.2], "#2196F3"),
        ("Cohesion (×1.0)", [0.2, -0.1, 0.3], "#FF9800"),
        ("Threat Avoid", [-0.3, 0.4, 0.5], "#9C27B0"),
        ("Target Seek", [0.6, 0.1, -0.2], "#4CAF50"),
    ]

    for fname, fvec, fcol in forces:
        # 힘 벡터를 Cone으로 표시
        fig.add_trace(go.Cone(
            x=[0], y=[0], z=[0],
            u=[fvec[0]], v=[fvec[1]], w=[fvec[2]],
            sizemode="absolute", sizeref=0.3,
            colorscale=[[0, fcol], [1, fcol]],
            showscale=False,
            name=fname,
            hovertext=fname,
        ))
        # 벡터 라벨
        fig.add_trace(go.Scatter3d(
            x=[fvec[0] * 1.3], y=[fvec[1] * 1.3], z=[fvec[2] * 1.3],
            mode="text",
            text=[fname],
            textfont=dict(size=10, color=fcol),
            showlegend=False,
        ))

    # 최종 합벡터
    total = np.array([0.0, 0.0, 0.0])
    weights = [1.5, 1.0, 1.0, 1.0, 1.0]
    for (_, fvec, _), w in zip(forces, weights):
        total += np.array(fvec) * w

    total_norm = total / (np.linalg.norm(total) + 1e-6) * 1.5

    fig.add_trace(go.Cone(
        x=[0], y=[0], z=[0],
        u=[total_norm[0]], v=[total_norm[1]], w=[total_norm[2]],
        sizemode="absolute", sizeref=0.4,
        colorscale=[[0, "#FFD700"], [1, "#FFD700"]],
        showscale=False,
        name="FINAL VECTOR",
    ))

    fig.update_layout(
        title=dict(text="Boids Force Vectors (3D Visualization)",
                   font=dict(size=20)),
        scene=dict(
            xaxis=dict(title="X", range=[-2, 2]),
            yaxis=dict(title="Y", range=[-2, 2]),
            zaxis=dict(title="Z", range=[-1.5, 1.5]),
            camera=dict(eye=dict(x=1.5, y=1.5, z=1.0)),
            bgcolor="#f8f9fa",
        ),
        margin=dict(l=0, r=0, t=60, b=0),
        template="plotly_white",
    )
    save(fig, "part3_2_boids_forces")


# ═══════════════════════════════════════════════════════
# Part 4: SC2 → Drone ATC System — 3D
# ═══════════════════════════════════════════════════════

def part4_concept_mapping_3d():
    """4-1. SC2 → Drone ATC 개념 매핑을 3D 브릿지로 표현"""
    print("[Part 4-1] SC2 → Drone ATC Concept Mapping 3D Bridge")

    sc2_modules = [
        ("Blackboard", "#42A5F5"),
        ("IntelManager", "#66BB6A"),
        ("StrategyManager", "#FFA726"),
        ("Boids Algorithm", "#EF5350"),
        ("Authority Mode", "#AB47BC"),
        ("SpellCaster", "#26C6DA"),
        ("CreepManager", "#8D6E63"),
        ("RL Agent", "#78909C"),
    ]

    atc_modules = [
        ("Flight Data Hub", "#EF5350"),
        ("Sensor Fusion", "#FFA726"),
        ("Route Planner", "#66BB6A"),
        ("Formation Flight", "#42A5F5"),
        ("Priority Manager", "#AB47BC"),
        ("Auto Maneuver", "#26C6DA"),
        ("Airspace Control", "#8D6E63"),
        ("Adaptive AI", "#78909C"),
    ]

    confidence = [5, 4, 4, 5, 5, 4, 3, 4]  # Transfer confidence (1-5)

    fig = go.Figure()

    # SC2 컬럼 (좌측, x=-3)
    for i, (name, col) in enumerate(sc2_modules):
        z = 7 - i * 1.0
        fig.add_trace(go.Scatter3d(
            x=[-3], y=[0], z=[z],
            mode="markers+text",
            marker=dict(size=12, color=col, opacity=0.9,
                        line=dict(width=1, color="white")),
            text=[name],
            textposition="middle left",
            textfont=dict(size=10),
            showlegend=False,
            hovertext=f"SC2: {name}",
        ))

    # ATC 컬럼 (우측, x=+3)
    for i, (name, col) in enumerate(atc_modules):
        z = 7 - i * 1.0
        fig.add_trace(go.Scatter3d(
            x=[3], y=[0], z=[z],
            mode="markers+text",
            marker=dict(size=12, color=col, opacity=0.9,
                        line=dict(width=1, color="white")),
            text=[name],
            textposition="middle right",
            textfont=dict(size=10),
            showlegend=False,
            hovertext=f"ATC: {name}",
        ))

    # 매핑 브릿지 (곡선)
    for i in range(len(sc2_modules)):
        z = 7 - i * 1.0
        c = confidence[i]
        width = c * 1.5
        opacity = 0.3 + c * 0.12

        # 곡선 (Y축으로 볼록)
        t_arr = np.linspace(0, 1, 20)
        bx = -3 + 6 * t_arr
        by = np.sin(t_arr * math.pi) * (0.5 + c * 0.15)
        bz = np.full_like(t_arr, z)

        color_map = {5: "#4CAF50", 4: "#FFC107", 3: "#FF9800"}
        bridge_col = color_map.get(c, "#999")

        fig.add_trace(go.Scatter3d(
            x=bx, y=by, z=bz,
            mode="lines",
            line=dict(color=bridge_col, width=width),
            opacity=opacity,
            showlegend=False,
            hovertext=f"Transfer: {'★' * c} ({sc2_modules[i][0]} → {atc_modules[i][0]})",
        ))

    # 타이틀 라벨
    fig.add_trace(go.Scatter3d(
        x=[-3], y=[0], z=[8.2],
        mode="text",
        text=["🎮 SC2 Swarm Control"],
        textfont=dict(size=16, color="#1565C0", family="Arial Black"),
        showlegend=False,
    ))
    fig.add_trace(go.Scatter3d(
        x=[3], y=[0], z=[8.2],
        mode="text",
        text=["✈️ Drone ATC System"],
        textfont=dict(size=16, color="#C62828", family="Arial Black"),
        showlegend=False,
    ))

    fig.update_layout(
        title=dict(text="SC2 → Drone ATC: Technology Transfer Bridge (3D)",
                   font=dict(size=20)),
        scene=dict(
            xaxis=dict(title="", range=[-5, 5], showticklabels=False, showgrid=False),
            yaxis=dict(title="", range=[-1.5, 2], showticklabels=False, showgrid=False),
            zaxis=dict(title="Module Layer", range=[-1, 9]),
            camera=dict(eye=dict(x=0, y=2.5, z=0.5)),
            bgcolor="#f8f9fa",
        ),
        margin=dict(l=0, r=0, t=60, b=0),
        template="plotly_white",
    )
    save(fig, "part4_1_concept_bridge")


def part4_drone_atc_3d():
    """4-2. Drone ATC 시스템 3D 공역 시각화"""
    print("[Part 4-2] Drone ATC 3D Airspace")

    np.random.seed(123)
    fig = go.Figure()

    # 공역 레이어 (고도별)
    altitudes = [
        (50, "Emergency Layer", "#F4433644", 8),
        (100, "Medical Priority", "#FF980044", 6),
        (150, "Scheduled Delivery", "#4CAF5044", 12),
        (200, "Survey / Patrol", "#2196F344", 5),
    ]

    for alt, name, col, n_drones in altitudes:
        # 고도 평면 (반투명 디스크)
        theta = np.linspace(0, 2 * np.pi, 30)
        r = 4
        x_plane = r * np.cos(theta)
        y_plane = r * np.sin(theta)
        z_plane = np.full_like(theta, alt)

        fig.add_trace(go.Scatter3d(
            x=x_plane, y=y_plane, z=z_plane,
            mode="lines",
            line=dict(color=col[:7], width=2, dash="dash"),
            name=f"{name} ({alt}m)",
            hoverinfo="name",
        ))

        # 드론들
        drone_x = np.random.randn(n_drones) * 2
        drone_y = np.random.randn(n_drones) * 2
        drone_z = np.full(n_drones, alt) + np.random.randn(n_drones) * 5

        fig.add_trace(go.Scatter3d(
            x=drone_x, y=drone_y, z=drone_z,
            mode="markers",
            marker=dict(size=5, color=col[:7], opacity=0.8,
                        symbol="diamond"),
            showlegend=False,
            hovertext=[f"Drone @ {alt}m ({name})" for _ in range(n_drones)],
        ))

    # 비행 회랑 (Corridor)
    corridor_t = np.linspace(0, 2 * np.pi, 50)
    corridor_x = 3 * np.cos(corridor_t)
    corridor_y = 3 * np.sin(corridor_t)
    corridor_z = np.linspace(30, 220, 50)

    fig.add_trace(go.Scatter3d(
        x=corridor_x, y=corridor_y, z=corridor_z,
        mode="lines",
        line=dict(color="#FFD700", width=4),
        name="Flight Corridor",
    ))

    # 지상 기지 (0m)
    fig.add_trace(go.Scatter3d(
        x=[0], y=[0], z=[0],
        mode="markers+text",
        marker=dict(size=20, color="#795548", opacity=0.8, symbol="square"),
        text=["Ground Station"],
        textposition="top center",
        showlegend=False,
    ))

    fig.update_layout(
        title=dict(text="Drone ATC: 3D Airspace Management",
                   font=dict(size=20)),
        scene=dict(
            xaxis=dict(title="East-West (km)"),
            yaxis=dict(title="North-South (km)"),
            zaxis=dict(title="Altitude (m)", range=[0, 250]),
            camera=dict(eye=dict(x=1.5, y=1.5, z=1.0)),
            bgcolor="#0d1117",
        ),
        paper_bgcolor="#0d1117",
        font=dict(color="white"),
        margin=dict(l=0, r=0, t=60, b=0),
    )
    save(fig, "part4_2_drone_airspace")


def part4_roadmap_3d():
    """4-3. End-to-End Vision 로드맵 3D"""
    print("[Part 4-3] Vision Roadmap 3D")

    fig = go.Figure()

    stages = [
        ("Stage 1\nSC2 Simulation", 0, "#1565C0",
         ["SC2 게임 환경", "Boids + FSM + RL", "10,000+ 게임 학습"]),
        ("Stage 2\nSim Transfer", 3, "#6A1B9A",
         ["3D 시뮬레이터", "2D→3D 파라미터", "충돌률 < 0.01%"]),
        ("Stage 3\nReal Drone", 6, "#2E7D32",
         ["ROS2 + PX4", "Edge Computing", "5대 편대 비행"]),
        ("Stage 4\nATC Scale", 9, "#E65100",
         ["100+ 드론 관제", "도시 공역 관리", "AI 실시간 최적화"]),
    ]

    for name, x, col, details in stages:
        # 메인 스테이지 (큰 구)
        fig.add_trace(go.Scatter3d(
            x=[x], y=[0], z=[2],
            mode="markers+text",
            marker=dict(size=22, color=col, opacity=0.9,
                        line=dict(width=2, color="white")),
            text=[name],
            textposition="top center",
            textfont=dict(size=12, color=col, family="Arial Black"),
            name=name.split("\n")[1],
            hovertext="<br>".join(details),
        ))

        # 서브 디테일
        for j, detail in enumerate(details):
            dz = 0.5 - j * 0.8
            dy = 1.2
            fig.add_trace(go.Scatter3d(
                x=[x], y=[dy], z=[dz],
                mode="markers+text",
                marker=dict(size=5, color=col, opacity=0.5),
                text=[detail],
                textposition="middle right",
                textfont=dict(size=8),
                showlegend=False,
            ))
            fig.add_trace(go.Scatter3d(
                x=[x, x], y=[0, dy], z=[2, dz],
                mode="lines",
                line=dict(color=col, width=1, dash="dot"),
                showlegend=False, hoverinfo="skip",
            ))

    # 스테이지 연결
    xs = [s[1] for s in stages]
    fig.add_trace(go.Scatter3d(
        x=xs, y=[0] * 4, z=[2] * 4,
        mode="lines",
        line=dict(color="#333", width=6),
        showlegend=False, hoverinfo="skip",
    ))

    # 화살표 라벨
    arrows = ["알고리즘 이전", "시뮬 검증", "스케일업"]
    for i, arr in enumerate(arrows):
        mx = (xs[i] + xs[i + 1]) / 2
        fig.add_trace(go.Scatter3d(
            x=[mx], y=[0], z=[2.8],
            mode="text",
            text=[f"→ {arr}"],
            textfont=dict(size=10, color="#666"),
            showlegend=False,
        ))

    fig.update_layout(
        title=dict(text="End-to-End Vision: Game → Reality (3D Roadmap)",
                   font=dict(size=20)),
        scene=dict(
            xaxis=dict(title="Development Phase", range=[-1.5, 11]),
            yaxis=dict(title="", range=[-1, 2.5], showticklabels=False, showgrid=False),
            zaxis=dict(title="", range=[-1.5, 4], showticklabels=False, showgrid=False),
            camera=dict(eye=dict(x=1.3, y=1.8, z=0.8)),
            bgcolor="#f8f9fa",
        ),
        margin=dict(l=0, r=0, t=60, b=0),
        template="plotly_white",
    )
    save(fig, "part4_3_vision_roadmap")


# ═══════════════════════════════════════════════════════
# Main
# ═══════════════════════════════════════════════════════

if __name__ == "__main__":
    print("=" * 60)
    print("SC2 → Drone ATC: 3D Presentation Visuals Generator")
    print("=" * 60)

    print("\n[Part 1] SC2 Bot Architecture")
    part1_fsm_3d()
    part1_authority_3d()
    part1_hybrid_3d()

    print("\n[Part 2] Operation Flow")
    part2_tactical_3d()
    part2_engagement_3d()

    print("\n[Part 3] Boids Swarm")
    part3_boids_3d()
    part3_forces_3d()

    print("\n[Part 4] SC2 → Drone ATC")
    part4_concept_mapping_3d()
    part4_drone_atc_3d()
    part4_roadmap_3d()

    print("\n" + "=" * 60)
    total = len([f for f in os.listdir(OUTPUT_DIR) if f.endswith(".html")])
    print(f"Complete! {total} HTML files generated in:")
    print(f"  {OUTPUT_DIR}")
    print("\nOpen any .html file in a browser to interact (rotate/zoom/pan)")
    print("=" * 60)
