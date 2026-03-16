# -*- coding: utf-8 -*-
"""
SC2-Swarm 캡스톤 디자인: 이해하기 쉬운 3D 시각화
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
- 큰 글씨, 명확한 색상, 최소한의 요소
- 심사위원/교수님이 한 눈에 파악 가능
- 한국어 라벨 + 영어 기술 용어 병기

python generate_clear_visuals.py
"""

import os
import math
import numpy as np
import plotly.graph_objects as go

OUTPUT_DIR = os.path.dirname(os.path.abspath(__file__))


def save(fig, name):
    path = os.path.join(OUTPUT_DIR, f"{name}.html")
    fig.write_html(path, include_plotlyjs="cdn")
    print(f"  -> {path}")


# ═══════════════════════════════════════════════════════
# 1. 시스템 전체 구조도 (가장 중요한 한 장)
# ═══════════════════════════════════════════════════════

def clear_system_overview():
    """
    캡스톤 핵심 1장: SC2 → 시뮬레이션 → 실제 드론
    3단계 파이프라인을 3D 계단식으로 보여줌
    """
    print("[1] 시스템 전체 구조도 (3-Stage Pipeline)")

    fig = go.Figure()

    # ── 3개 스테이지 플랫폼 ──
    stages = [
        {"name": "Stage 1\nSC2 게임 시뮬레이션", "x": 0, "z": 0,
         "color": "#1976D2", "items": [
             "Boids 군집 알고리즘", "FSM 상태 머신", "RL 강화학습",
         ]},
        {"name": "Stage 2\nGazebo 3D 시뮬레이션", "x": 5, "z": 2,
         "color": "#7B1FA2", "items": [
             "ROS 2 미들웨어", "물리 엔진 (중력/바람)", "센서 노이즈 반영",
         ]},
        {"name": "Stage 3\n실제 드론 비행", "x": 10, "z": 4,
         "color": "#2E7D32", "items": [
             "Pixhawk + RPi", "WiFi Mesh 통신", "3대 편대 비행",
         ]},
    ]

    for s in stages:
        x, z, col = s["x"], s["z"], s["color"]

        # 플랫폼 (큰 투명 박스)
        # 바닥면
        bx = [x - 1.8, x + 1.8, x + 1.8, x - 1.8]
        by = [-1.5, -1.5, 1.5, 1.5]
        fig.add_trace(go.Mesh3d(
            x=bx, y=by, z=[z] * 4,
            i=[0, 0], j=[1, 2], k=[2, 3],
            color=col, opacity=0.15,
            hoverinfo="skip", showlegend=False,
        ))

        # 스테이지 제목 (크게)
        fig.add_trace(go.Scatter3d(
            x=[x], y=[0], z=[z + 1.8],
            mode="text",
            text=[s["name"]],
            textfont=dict(size=16, color=col, family="Arial Black"),
            showlegend=False, hoverinfo="skip",
        ))

        # 세부 항목 (아래 정렬)
        for i, item in enumerate(s["items"]):
            fig.add_trace(go.Scatter3d(
                x=[x], y=[-1.0 + i * 1.0], z=[z + 0.5],
                mode="markers+text",
                marker=dict(size=8, color=col, opacity=0.7,
                            symbol="circle", line=dict(width=1, color="white")),
                text=[item],
                textposition="middle right",
                textfont=dict(size=12, color="#333"),
                showlegend=False,
            ))

    # ── 스테이지 간 화살표 (큰 화살표) ──
    arrows = [
        {"from": 0, "to": 5, "z1": 0, "z2": 2, "label": "알고리즘 추출\n(2D → 3D 변환)"},
        {"from": 5, "to": 10, "z1": 2, "z2": 4, "label": "Sim-to-Real\n(시뮬 → 실제)"},
    ]

    for a in arrows:
        # 곡선 경로
        t = np.linspace(0, 1, 30)
        ax = a["from"] + (a["to"] - a["from"]) * t
        az = a["z1"] + (a["z2"] - a["z1"]) * t
        ay = np.sin(t * math.pi) * 1.2  # 위로 볼록

        fig.add_trace(go.Scatter3d(
            x=ax, y=ay, z=az,
            mode="lines",
            line=dict(color="#FF6F00", width=8),
            showlegend=False, hoverinfo="skip",
        ))

        # 화살표 라벨
        mid_x = (a["from"] + a["to"]) / 2
        mid_z = (a["z1"] + a["z2"]) / 2
        fig.add_trace(go.Scatter3d(
            x=[mid_x], y=[1.8], z=[mid_z + 0.5],
            mode="text",
            text=[a["label"]],
            textfont=dict(size=13, color="#FF6F00", family="Arial Black"),
            showlegend=False, hoverinfo="skip",
        ))

    # 큰 제목
    fig.add_trace(go.Scatter3d(
        x=[5], y=[0], z=[7],
        mode="text",
        text=["SC2-Swarm: Sim-to-Real 3단계 파이프라인"],
        textfont=dict(size=20, color="#333", family="Arial Black"),
        showlegend=False, hoverinfo="skip",
    ))

    fig.update_layout(
        scene=dict(
            xaxis=dict(visible=False, range=[-3, 13]),
            yaxis=dict(visible=False, range=[-3, 4]),
            zaxis=dict(visible=False, range=[-1, 8]),
            camera=dict(
                eye=dict(x=1.0, y=2.0, z=0.8),
                up=dict(x=0, y=0, z=1),
            ),
            bgcolor="white",
        ),
        paper_bgcolor="white",
        margin=dict(l=0, r=0, t=20, b=0),
        width=1200, height=700,
    )
    save(fig, "clear_1_system_overview")


# ═══════════════════════════════════════════════════════
# 2. Boids 알고리즘 설명도 (핵심 기술)
# ═══════════════════════════════════════════════════════

def clear_boids_explained():
    """
    Boids 3대 규칙을 큰 화살표와 라벨로 직관적 표현
    중심에 '나', 주변에 이웃, 3가지 힘 벡터
    """
    print("[2] Boids 알고리즘 설명도")

    fig = go.Figure()

    # 중심 드론 (ME)
    fig.add_trace(go.Scatter3d(
        x=[0], y=[0], z=[0],
        mode="markers+text",
        marker=dict(size=20, color="#FF6F00", opacity=1,
                    line=dict(width=3, color="white"),
                    symbol="diamond"),
        text=["  나 (ME)"],
        textposition="middle right",
        textfont=dict(size=18, color="#FF6F00", family="Arial Black"),
        name="현재 드론",
    ))

    # 이웃 드론들 (반원 배치)
    neighbor_angles = [30, 80, 130, 210, 280, 340]
    for i, ang in enumerate(neighbor_angles):
        rad = math.radians(ang)
        nx = 2.5 * math.cos(rad)
        ny = 2.5 * math.sin(rad)
        fig.add_trace(go.Scatter3d(
            x=[nx], y=[ny], z=[0],
            mode="markers",
            marker=dict(size=10, color="#78909C", opacity=0.6,
                        line=dict(width=1, color="white")),
            showlegend=False, hovertext=f"이웃 드론 {i + 1}",
        ))
        # 연결 점선
        fig.add_trace(go.Scatter3d(
            x=[0, nx], y=[0, ny], z=[0, 0],
            mode="lines",
            line=dict(color="#B0BEC5", width=1, dash="dot"),
            showlegend=False, hoverinfo="skip",
        ))

    # ── 3대 힘 벡터 (크고 명확하게) ──
    forces = [
        {
            "name": "① 분리 (Separation)",
            "desc": "너무 가까우면 밀어냄\n→ 충돌 방지",
            "dir": (-2.5, -1.5, 1.5),
            "color": "#F44336",
        },
        {
            "name": "② 정렬 (Alignment)",
            "desc": "이웃과 같은 방향\n→ 대형 유지",
            "dir": (2.0, 2.5, 0.5),
            "color": "#2196F3",
        },
        {
            "name": "③ 응집 (Cohesion)",
            "desc": "그룹 중심으로 모임\n→ 흩어짐 방지",
            "dir": (0.5, -2.0, -1.0),
            "color": "#4CAF50",
        },
    ]

    for f in forces:
        dx, dy, dz = f["dir"]
        col = f["color"]

        # 큰 화살표 (Cone)
        fig.add_trace(go.Cone(
            x=[0], y=[0], z=[0],
            u=[dx], v=[dy], w=[dz],
            sizemode="absolute", sizeref=0.6,
            colorscale=[[0, col], [1, col]],
            showscale=False,
            name=f["name"],
            hovertext=f["name"],
        ))

        # 라벨 (화살표 끝에)
        fig.add_trace(go.Scatter3d(
            x=[dx * 1.3], y=[dy * 1.3], z=[dz * 1.3],
            mode="text",
            text=[f["name"]],
            textfont=dict(size=14, color=col, family="Arial Black"),
            showlegend=False,
        ))

        # 설명 (라벨 아래)
        fig.add_trace(go.Scatter3d(
            x=[dx * 1.5], y=[dy * 1.5], z=[dz * 1.5 - 0.5],
            mode="text",
            text=[f["desc"]],
            textfont=dict(size=11, color="#666"),
            showlegend=False,
        ))

    # 최종 합벡터
    total = np.array([0.0, 0.0, 0.0])
    for f in forces:
        total += np.array(f["dir"])
    total = total / np.linalg.norm(total) * 3.0

    fig.add_trace(go.Cone(
        x=[0], y=[0], z=[0],
        u=[total[0]], v=[total[1]], w=[total[2]],
        sizemode="absolute", sizeref=0.8,
        colorscale=[[0, "#FF6F00"], [1, "#FFD600"]],
        showscale=False,
        name="최종 이동 방향",
    ))

    fig.add_trace(go.Scatter3d(
        x=[total[0] * 1.2], y=[total[1] * 1.2], z=[total[2] * 1.2],
        mode="text",
        text=["최종 이동 방향 ▶"],
        textfont=dict(size=16, color="#FF6F00", family="Arial Black"),
        showlegend=False,
    ))

    # 공식
    fig.add_trace(go.Scatter3d(
        x=[0], y=[0], z=[3.5],
        mode="text",
        text=["V = Separation × 1.5  +  Alignment × 1.0  +  Cohesion × 1.0"],
        textfont=dict(size=14, color="#333", family="Courier New"),
        showlegend=False,
    ))

    fig.update_layout(
        title=dict(text="Boids 알고리즘: 군집 비행의 3대 규칙",
                   font=dict(size=22, family="Arial Black"),
                   x=0.5),
        scene=dict(
            xaxis=dict(visible=False, range=[-5, 5]),
            yaxis=dict(visible=False, range=[-5, 5]),
            zaxis=dict(visible=False, range=[-3, 5]),
            camera=dict(eye=dict(x=1.5, y=1.2, z=0.8)),
            bgcolor="white",
        ),
        paper_bgcolor="white",
        margin=dict(l=0, r=0, t=60, b=0),
        width=1100, height=750,
    )
    save(fig, "clear_2_boids_explained")


# ═══════════════════════════════════════════════════════
# 3. SC2 ↔ 드론 매핑 (기술 전이)
# ═══════════════════════════════════════════════════════

def clear_tech_transfer():
    """
    SC2 모듈 → 드론 ATC 대응 모듈
    양쪽에 박스, 가운데 연결선 (색상으로 전이 신뢰도)
    """
    print("[3] SC2 ↔ 드론 기술 전이 매핑")

    fig = go.Figure()

    mappings = [
        ("Blackboard\n(상태 관리)", "Flight Data Hub\n(비행 데이터)", 5, "#4CAF50"),
        ("Boids Algorithm\n(군집 이동)", "Formation Flight\n(편대 비행)", 5, "#4CAF50"),
        ("Authority Mode\n(우선순위)", "ATC Priority\n(관제 우선순위)", 5, "#4CAF50"),
        ("IntelManager\n(정찰/탐지)", "Sensor Fusion\n(센서 융합)", 4, "#FFC107"),
        ("StrategyManager\n(전략 FSM)", "Route Planner\n(경로 계획)", 4, "#FFC107"),
        ("RL Agent\n(강화학습)", "Adaptive AI\n(적응형 AI)", 4, "#FFC107"),
        ("CreepManager\n(영역 확장)", "Airspace Control\n(공역 관리)", 3, "#FF9800"),
    ]

    LEFT_X = -4
    RIGHT_X = 4
    START_Z = 7

    # 헤더
    fig.add_trace(go.Scatter3d(
        x=[LEFT_X], y=[0], z=[START_Z + 1.5],
        mode="text",
        text=["SC2 게임 모듈"],
        textfont=dict(size=18, color="#1565C0", family="Arial Black"),
        showlegend=False,
    ))
    fig.add_trace(go.Scatter3d(
        x=[RIGHT_X], y=[0], z=[START_Z + 1.5],
        mode="text",
        text=["드론 ATC 모듈"],
        textfont=dict(size=18, color="#C62828", family="Arial Black"),
        showlegend=False,
    ))

    for i, (sc2, atc, conf, col) in enumerate(mappings):
        z = START_Z - i * 1.2

        # SC2 모듈 (좌측 박스)
        fig.add_trace(go.Scatter3d(
            x=[LEFT_X], y=[0], z=[z],
            mode="markers+text",
            marker=dict(size=14, color="#1565C0", opacity=0.8,
                        symbol="square",
                        line=dict(width=2, color="white")),
            text=[sc2],
            textposition="middle left",
            textfont=dict(size=12, color="#1565C0"),
            showlegend=False,
        ))

        # 드론 모듈 (우측 박스)
        fig.add_trace(go.Scatter3d(
            x=[RIGHT_X], y=[0], z=[z],
            mode="markers+text",
            marker=dict(size=14, color="#C62828", opacity=0.8,
                        symbol="square",
                        line=dict(width=2, color="white")),
            text=[atc],
            textposition="middle right",
            textfont=dict(size=12, color="#C62828"),
            showlegend=False,
        ))

        # 연결선 (두께 = 신뢰도)
        width = conf * 2
        t_arr = np.linspace(0, 1, 20)
        lx = LEFT_X + (RIGHT_X - LEFT_X) * t_arr
        ly = np.sin(t_arr * math.pi) * 0.8
        lz = np.full_like(t_arr, z)

        fig.add_trace(go.Scatter3d(
            x=lx, y=ly, z=lz,
            mode="lines",
            line=dict(color=col, width=width),
            showlegend=False,
            hovertext=f"전이 신뢰도: {'★' * conf}",
        ))

        # 신뢰도 표시 (가운데)
        fig.add_trace(go.Scatter3d(
            x=[0], y=[1.2], z=[z],
            mode="text",
            text=["★" * conf],
            textfont=dict(size=12, color=col),
            showlegend=False,
        ))

    # 범례
    for conf_val, col, label in [(5, "#4CAF50", "★★★★★ Direct (직접 전이)"),
                                  (4, "#FFC107", "★★★★☆ Adapt (적응 필요)"),
                                  (3, "#FF9800", "★★★☆☆ Concept (개념 전이)")]:
        fig.add_trace(go.Scatter3d(
            x=[0], y=[0], z=[-2],  # 화면 밖
            mode="markers",
            marker=dict(size=8, color=col),
            name=label,
        ))

    fig.update_layout(
        title=dict(text="SC2 → 드론 ATC: 기술 전이 매핑",
                   font=dict(size=22, family="Arial Black"),
                   x=0.5),
        scene=dict(
            xaxis=dict(visible=False, range=[-8, 8]),
            yaxis=dict(visible=False, range=[-2, 3]),
            zaxis=dict(visible=False, range=[-2, 10]),
            camera=dict(eye=dict(x=0, y=2.5, z=0.3)),
            bgcolor="white",
        ),
        paper_bgcolor="white",
        margin=dict(l=0, r=0, t=60, b=0),
        width=1200, height=800,
        legend=dict(font=dict(size=12), x=0.02, y=0.02,
                    bgcolor="rgba(255,255,255,0.8)"),
    )
    save(fig, "clear_3_tech_transfer")


# ═══════════════════════════════════════════════════════
# 4. Boids 군집 비행 시뮬레이션 (깔끔 버전)
# ═══════════════════════════════════════════════════════

def clear_swarm_simulation():
    """
    드론 20대가 V자 편대로 목표지점까지 이동하는 시뮬레이션
    어두운 배경 + 네온 드론 = 미래적 느낌
    """
    print("[4] 드론 편대 비행 3D 시뮬레이션")

    np.random.seed(42)
    N = 20
    FRAMES = 50

    # V자 편대 초기 위치
    pos = np.zeros((N, 3))
    for i in range(N):
        row = i // 2
        side = 1 if i % 2 == 0 else -1
        if i == 0:
            pos[i] = [0, 0, 50]
        else:
            pos[i] = [side * row * 2.0, row * -1.5, 50 + np.random.randn() * 2]

    target = np.array([0, 30, 50])
    vel = np.zeros((N, 3))

    all_pos = [pos.copy()]
    for _ in range(FRAMES):
        new_pos = pos.copy()
        for i in range(N):
            # 리더 추종
            leader_pos = all_pos[-1][0]
            if i == 0:
                # 리더: 목표로 직진
                seek = (target - pos[0]) * 0.02
                new_pos[0] = pos[0] + seek
            else:
                # 팔로워: Boids
                # Separation
                sep = np.zeros(3)
                for j in range(N):
                    if i != j:
                        d = pos[i] - pos[j]
                        dist = np.linalg.norm(d)
                        if 0 < dist < 3.0:
                            sep += d / (dist ** 2)

                # 리더 방향 정렬
                to_leader = leader_pos - pos[i]
                ali = to_leader / (np.linalg.norm(to_leader) + 1e-6) * 0.3

                # V자 대형 위치 유지
                row = i // 2
                side = 1 if i % 2 == 0 else -1
                formation_target = leader_pos + np.array([side * row * 2.0, row * -1.5, 0])
                coh = (formation_target - pos[i]) * 0.1

                v = sep * 1.0 + ali + coh
                speed = np.linalg.norm(v)
                if speed > 0.5:
                    v = v / speed * 0.5
                # 약간의 고도 흔들림
                v[2] += np.random.randn() * 0.05
                new_pos[i] = pos[i] + v

        pos = new_pos
        all_pos.append(pos.copy())

    # 기본 프레임 + 애니메이션
    fig = go.Figure()

    # 지면 그리드
    grid_x = np.linspace(-15, 15, 10)
    grid_y = np.linspace(-5, 35, 15)
    fig.add_trace(go.Scatter3d(
        x=np.repeat(grid_x, len(grid_y)),
        y=np.tile(grid_y, len(grid_x)),
        z=np.zeros(len(grid_x) * len(grid_y)),
        mode="markers",
        marker=dict(size=1, color="#2a2a4a", opacity=0.3),
        showlegend=False, hoverinfo="skip",
    ))

    # 목표점
    fig.add_trace(go.Scatter3d(
        x=[target[0]], y=[target[1]], z=[0],
        mode="markers+text",
        marker=dict(size=12, color="#FF6F00", symbol="x", opacity=0.6),
        text=["목표 지점"],
        textposition="top center",
        textfont=dict(size=13, color="#FF6F00"),
        showlegend=False,
    ))

    # 드론 (리더 + 팔로워)
    init = all_pos[0]
    fig.add_trace(go.Scatter3d(
        x=[init[0, 0]], y=[init[0, 1]], z=[init[0, 2]],
        mode="markers+text",
        marker=dict(size=12, color="#FFD600", symbol="diamond",
                    line=dict(width=2, color="white")),
        text=["LEADER"],
        textposition="top center",
        textfont=dict(size=11, color="#FFD600"),
        name="리더 드론",
    ))

    fig.add_trace(go.Scatter3d(
        x=init[1:, 0], y=init[1:, 1], z=init[1:, 2],
        mode="markers",
        marker=dict(size=7, color="#00E5FF", opacity=0.85,
                    symbol="circle",
                    line=dict(width=1, color="white")),
        name=f"팔로워 드론 ×{N - 1}",
    ))

    # 드론 간 연결선 (편대 형태 시각화)
    for i in range(1, N):
        fig.add_trace(go.Scatter3d(
            x=[init[0, 0], init[i, 0]],
            y=[init[0, 1], init[i, 1]],
            z=[init[0, 2], init[i, 2]],
            mode="lines",
            line=dict(color="#00E5FF", width=1),
            opacity=0.2,
            showlegend=False, hoverinfo="skip",
        ))

    # 애니메이션 프레임
    anim_frames = []
    for fi, fpos in enumerate(all_pos):
        frame_data = [
            go.Scatter3d(x=np.repeat(grid_x, len(grid_y)),
                         y=np.tile(grid_y, len(grid_x)),
                         z=np.zeros(len(grid_x) * len(grid_y))),
            go.Scatter3d(x=[target[0]], y=[target[1]], z=[0]),
            go.Scatter3d(x=[fpos[0, 0]], y=[fpos[0, 1]], z=[fpos[0, 2]]),
            go.Scatter3d(x=fpos[1:, 0], y=fpos[1:, 1], z=fpos[1:, 2]),
        ]
        # 연결선
        for i in range(1, N):
            frame_data.append(go.Scatter3d(
                x=[fpos[0, 0], fpos[i, 0]],
                y=[fpos[0, 1], fpos[i, 1]],
                z=[fpos[0, 2], fpos[i, 2]],
            ))

        anim_frames.append(go.Frame(data=frame_data, name=f"f{fi}"))

    fig.frames = anim_frames

    fig.update_layout(
        title=dict(text="V자 편대 비행 시뮬레이션 (20대 드론, Boids 알고리즘)",
                   font=dict(size=18, family="Arial Black"),
                   x=0.5),
        scene=dict(
            xaxis=dict(title="East-West (m)", range=[-15, 15]),
            yaxis=dict(title="Forward (m)", range=[-5, 35]),
            zaxis=dict(title="Altitude (m)", range=[0, 80]),
            camera=dict(eye=dict(x=1.5, y=-1.5, z=0.8)),
            bgcolor="#0a0a1a",
        ),
        paper_bgcolor="#0a0a1a",
        font=dict(color="white"),
        updatemenus=[dict(
            type="buttons", showactive=False, y=0, x=0.5, xanchor="center",
            buttons=[
                dict(label="▶ 비행 시작",
                     method="animate",
                     args=[None, dict(frame=dict(duration=100, redraw=True),
                                      fromcurrent=True)]),
                dict(label="⏸ 정지",
                     method="animate",
                     args=[[None], dict(frame=dict(duration=0, redraw=False),
                                        mode="immediate")]),
            ],
        )],
        sliders=[dict(
            active=0,
            steps=[dict(args=[[f"f{i}"],
                               dict(mode="immediate",
                                    frame=dict(duration=80, redraw=True))],
                         method="animate", label=f"{i}")
                   for i in range(len(all_pos))],
            x=0.1, len=0.8, y=0,
            currentvalue=dict(prefix="Frame: ", visible=True, font=dict(color="white")),
            font=dict(color="white"),
        )],
        margin=dict(l=0, r=0, t=60, b=60),
        width=1200, height=800,
    )
    save(fig, "clear_4_swarm_simulation")


# ═══════════════════════════════════════════════════════
# 5. ATC 우선순위 시스템 (피라미드)
# ═══════════════════════════════════════════════════════

def clear_atc_priority():
    """
    ATC 우선순위를 3D 피라미드로 — 위쪽일수록 높은 우선순위
    """
    print("[5] ATC 우선순위 피라미드")

    fig = go.Figure()

    levels = [
        {"name": "Level 0: 충돌 회피\n(COLLISION AVOIDANCE)", "z": 3,
         "color": "#F44336", "width": 1.5,
         "desc": "모든 드론 즉각 회피\n= SC2 EMERGENCY 모드"},
        {"name": "Level 1: 의료/긴급\n(MEDICAL/EMERGENCY)", "z": 2,
         "color": "#FF9800", "width": 2.5,
         "desc": "긴급 드론 우선 통과\n일반 드론 대기"},
        {"name": "Level 2: 계획 배송\n(SCHEDULED DELIVERY)", "z": 1,
         "color": "#4CAF50", "width": 3.5,
         "desc": "스케줄 기반 경로 할당\n정상 운용"},
        {"name": "Level 3: 순찰/측량\n(SURVEY/PATROL)", "z": 0,
         "color": "#2196F3", "width": 4.5,
         "desc": "여유 공역 자유 비행\n= SC2 ECONOMY 모드"},
    ]

    for lv in levels:
        z = lv["z"]
        w = lv["width"]
        col = lv["color"]

        # 피라미드 단 (사각형)
        corners_x = [-w, w, w, -w, -w]
        corners_y = [-w, -w, w, w, -w]
        corners_z = [z] * 5

        fig.add_trace(go.Scatter3d(
            x=corners_x, y=corners_y, z=corners_z,
            mode="lines",
            line=dict(color=col, width=5),
            showlegend=False, hoverinfo="skip",
        ))

        # 채움 (반투명)
        fig.add_trace(go.Mesh3d(
            x=[-w, w, w, -w],
            y=[-w, -w, w, w],
            z=[z] * 4,
            i=[0, 0], j=[1, 2], k=[2, 3],
            color=col, opacity=0.25,
            showlegend=False, hoverinfo="skip",
        ))

        # 라벨 (위)
        fig.add_trace(go.Scatter3d(
            x=[0], y=[0], z=[z + 0.3],
            mode="text",
            text=[lv["name"]],
            textfont=dict(size=14, color=col, family="Arial Black"),
            showlegend=False,
        ))

        # 설명 (옆)
        fig.add_trace(go.Scatter3d(
            x=[w + 1.5], y=[0], z=[z],
            mode="text",
            text=[lv["desc"]],
            textfont=dict(size=11, color="#555"),
            showlegend=False,
        ))

    # 위쪽 화살표
    fig.add_trace(go.Scatter3d(
        x=[-6], y=[0], z=[0, 1, 2, 3],
        mode="lines+text",
        line=dict(color="#333", width=3),
        text=["낮음", "", "", "높음"],
        textposition="middle left",
        textfont=dict(size=12, color="#333"),
        showlegend=False,
    ))

    fig.add_trace(go.Scatter3d(
        x=[-6.5], y=[0], z=[1.5],
        mode="text",
        text=["우\n선\n순\n위"],
        textfont=dict(size=14, color="#333", family="Arial Black"),
        showlegend=False,
    ))

    fig.update_layout(
        title=dict(text="드론 ATC 우선순위 시스템 (= SC2 Authority Mode)",
                   font=dict(size=20, family="Arial Black"),
                   x=0.5),
        scene=dict(
            xaxis=dict(visible=False, range=[-8, 8]),
            yaxis=dict(visible=False, range=[-6, 6]),
            zaxis=dict(visible=False, range=[-0.5, 5]),
            camera=dict(eye=dict(x=1.3, y=1.5, z=1.0)),
            bgcolor="white",
        ),
        paper_bgcolor="white",
        margin=dict(l=0, r=0, t=60, b=0),
        width=1100, height=750,
    )
    save(fig, "clear_5_atc_priority")


# ═══════════════════════════════════════════════════════
# Main
# ═══════════════════════════════════════════════════════

if __name__ == "__main__":
    print("=" * 60)
    print("이해하기 쉬운 3D 시각화 생성")
    print("=" * 60)

    clear_system_overview()
    clear_boids_explained()
    clear_tech_transfer()
    clear_swarm_simulation()
    clear_atc_priority()

    print("\n" + "=" * 60)
    files = sorted(f for f in os.listdir(OUTPUT_DIR) if f.startswith("clear_"))
    print(f"완료! {len(files)}개 파일 생성:")
    for f in files:
        print(f"  {f}")
    print("=" * 60)
