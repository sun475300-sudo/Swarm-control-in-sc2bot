# -*- coding: utf-8 -*-
"""
군집 드론 레이더 망 + 유저 드론 ATC 시스템 시각화
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

개념:
  1. 군집 드론(Sentinel)이 공역에 배치되어 레이더 망을 형성
  2. 레이더 망 내부로 진입하는 유저 드론을 감지
  3. 유저 드론에게 비행 시간(Time Slot)을 할당
  4. 시간 만료 시 알림 전송 → 착륙 유도

python generate_radar_mesh_atc.py
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
# 1. 전체 시스템 개요 (가장 중요한 한 장)
# ═══════════════════════════════════════════════════════

def radar_system_overview():
    """
    군집 드론이 레이더 망을 형성하고,
    내부의 유저 드론을 감지/관리하는 전체 그림
    """
    print("[1] 전체 시스템 개요: 레이더 망 + 유저 드론 관제")

    fig = go.Figure()

    # ── 군집 드론 (Sentinel) 배치: 정육각형 격자 ──
    sentinel_positions = []
    RADIUS = 8  # 전체 공역 반경
    SPACING = 4  # 드론 간 간격
    for q in range(-3, 4):
        for r in range(-3, 4):
            x = SPACING * (q + r * 0.5)
            y = SPACING * (r * math.sqrt(3) / 2)
            if math.sqrt(x**2 + y**2) <= RADIUS * 1.2:
                sentinel_positions.append((x, y))

    sentinel_alt = 120  # 군집 드론 고도 (m)
    sx = [p[0] for p in sentinel_positions]
    sy = [p[1] for p in sentinel_positions]
    sz = [sentinel_alt] * len(sentinel_positions)

    # 군집 드론 마커 (라벨 없이 hover로 표시 — 겹침 방지)
    fig.add_trace(go.Scatter3d(
        x=sx, y=sy, z=sz,
        mode="markers",
        marker=dict(size=8, color="#F44336", opacity=0.95,
                    symbol="diamond",
                    line=dict(width=1.5, color="white")),
        hovertext=[f"Sentinel {i+1}" for i in range(len(sx))],
        hoverinfo="text",
        name="군집 드론 (Sentinel)",
    ))

    # ── 레이더 망 (드론 간 연결선) ──
    for i in range(len(sentinel_positions)):
        for j in range(i + 1, len(sentinel_positions)):
            dx = sentinel_positions[i][0] - sentinel_positions[j][0]
            dy = sentinel_positions[i][1] - sentinel_positions[j][1]
            dist = math.sqrt(dx**2 + dy**2)
            if dist <= SPACING * 1.3:  # 인접 드론만 연결
                fig.add_trace(go.Scatter3d(
                    x=[sentinel_positions[i][0], sentinel_positions[j][0]],
                    y=[sentinel_positions[i][1], sentinel_positions[j][1]],
                    z=[sentinel_alt, sentinel_alt],
                    mode="lines",
                    line=dict(color="#F44336", width=2),
                    opacity=0.3,
                    showlegend=False, hoverinfo="skip",
                ))

    # ── 레이더 감지 범위 (아래로 원뿔형) ──
    cone_angles = np.linspace(0, 2 * math.pi, 40)
    for sp in sentinel_positions[::3]:  # 일부만 표시 (시인성)
        cone_r = 3.0
        cx = sp[0] + cone_r * np.cos(cone_angles)
        cy = sp[1] + cone_r * np.sin(cone_angles)
        cz = np.full_like(cone_angles, sentinel_alt - 40)

        # 꼭대기 → 바닥 원
        fig.add_trace(go.Scatter3d(
            x=np.append(cx, sp[0]),
            y=np.append(cy, sp[1]),
            z=np.append(cz, sentinel_alt),
            mode="lines",
            line=dict(color="#FF8A80", width=1),
            opacity=0.1,
            showlegend=False, hoverinfo="skip",
        ))

    # ── 레이더 망 커버리지 (바닥 원) ──
    cover_r = RADIUS + 2
    cover_theta = np.linspace(0, 2 * math.pi, 60)
    fig.add_trace(go.Scatter3d(
        x=(cover_r * np.cos(cover_theta)).tolist(),
        y=(cover_r * np.sin(cover_theta)).tolist(),
        z=[0] * 60,
        mode="lines",
        line=dict(color="#FF6F00", width=3, dash="dash"),
        name="레이더 커버리지 경계",
    ))
    fig.add_trace(go.Scatter3d(
        x=[cover_r + 2.5], y=[0], z=[0],
        mode="text",
        text=["관제 공역 경계"],
        textfont=dict(size=11, color="#FF6F00", family="Arial Black"),
        showlegend=False,
    ))

    # ── 유저 드론 (내부 비행 중) — 간격 확보 + hover로 상세정보 ──
    n_users = 6
    # 겹치지 않도록 수동 배치
    user_x = np.array([-5.5, 4.0, -2.0, 5.5, -4.5, 1.0])
    user_y = np.array([4.0, -5.0, -3.0, 3.0, -1.0, 5.5])
    user_z = np.array([45, 65, 80, 35, 55, 70])
    user_labels = ["U1", "U2", "U3", "U4", "U5", "U6"]
    user_status = ["U1: 비행중 (12:30 남음)", "U2: 비행중 (08:45 남음)",
                   "U3: 비행중 (23:10 남음)", "U4: 시간 임박! (01:20)",
                   "U5: 비행중 (15:00 남음)", "U6: 신규 진입 감지!"]
    user_colors = ["#2196F3", "#2196F3", "#2196F3",
                   "#FF9800", "#2196F3", "#4CAF50"]

    fig.add_trace(go.Scatter3d(
        x=user_x, y=user_y, z=user_z,
        mode="markers+text",
        marker=dict(size=10, color=user_colors, opacity=0.9,
                    symbol="circle",
                    line=dict(width=2, color="white")),
        text=user_labels,
        textposition="top center",
        textfont=dict(size=9, color="#1565C0"),
        name="유저 드론",
        hovertext=user_status,
        hoverinfo="text",
    ))

    # 유저 드론 → 지면 투영선 (위치 파악용)
    for i in range(n_users):
        fig.add_trace(go.Scatter3d(
            x=[user_x[i], user_x[i]],
            y=[user_y[i], user_y[i]],
            z=[user_z[i], 0],
            mode="lines",
            line=dict(color=user_colors[i], width=1, dash="dot"),
            opacity=0.3,
            showlegend=False, hoverinfo="skip",
        ))

    # ── 경고 드론 (시간 임박) ──
    # User 4에 경고 링
    warn_theta = np.linspace(0, 2 * math.pi, 30)
    wr = 1.5
    fig.add_trace(go.Scatter3d(
        x=(user_x[3] + wr * np.cos(warn_theta)).tolist(),
        y=(user_y[3] + wr * np.sin(warn_theta)).tolist(),
        z=[user_z[3]] * 30,
        mode="lines",
        line=dict(color="#FF9800", width=3),
        name="시간 임박 경고",
    ))

    # ── 지상국 (GCS) ──
    fig.add_trace(go.Scatter3d(
        x=[0], y=[-RADIUS - 2], z=[0],
        mode="markers+text",
        marker=dict(size=15, color="#795548", symbol="square",
                    line=dict(width=2, color="white")),
        text=["지상 관제국\n(Ground Control)"],
        textposition="top center",
        textfont=dict(size=12, color="#795548", family="Arial Black"),
        name="지상 관제국",
    ))

    # GCS ↔ 군집 드론 통신선
    fig.add_trace(go.Scatter3d(
        x=[0, 0], y=[-RADIUS - 2, 0], z=[0, sentinel_alt],
        mode="lines",
        line=dict(color="#795548", width=2, dash="dash"),
        opacity=0.4,
        showlegend=False, hoverinfo="skip",
    ))

    # ── 고도 라벨 (충분히 떨어진 위치) ──
    fig.add_trace(go.Scatter3d(
        x=[-RADIUS - 5], y=[-RADIUS - 2], z=[0],
        mode="text", text=["지면 0m"],
        textfont=dict(size=10, color="#999"),
        showlegend=False,
    ))
    fig.add_trace(go.Scatter3d(
        x=[-RADIUS - 5], y=[-RADIUS - 2], z=[60],
        mode="text", text=["유저 드론 30~90m"],
        textfont=dict(size=10, color="#2196F3"),
        showlegend=False,
    ))
    fig.add_trace(go.Scatter3d(
        x=[-RADIUS - 5], y=[-RADIUS - 2], z=[sentinel_alt],
        mode="text", text=["군집 드론 120m"],
        textfont=dict(size=10, color="#F44336"),
        showlegend=False,
    ))

    fig.update_layout(
        title=dict(
            text="군집 드론 레이더 망 + 유저 드론 관제 시스템",
            font=dict(size=22, family="Arial Black"),
            x=0.5,
        ),
        scene=dict(
            xaxis=dict(title="East-West (m)", range=[-18, 18],
                       gridcolor="#eee", zerolinecolor="#ddd"),
            yaxis=dict(title="North-South (m)", range=[-15, 15],
                       gridcolor="#eee", zerolinecolor="#ddd"),
            zaxis=dict(title="고도 Altitude (m)", range=[-5, 150],
                       gridcolor="#eee", zerolinecolor="#ddd"),
            camera=dict(eye=dict(x=1.5, y=1.5, z=0.9)),
            bgcolor="white",
        ),
        paper_bgcolor="white",
        margin=dict(l=0, r=0, t=60, b=0),
        width=1300, height=850,
        legend=dict(font=dict(size=11), x=0.01, y=0.99,
                    bgcolor="rgba(255,255,255,0.9)"),
    )
    save(fig, "radar_1_system_overview")


# ═══════════════════════════════════════════════════════
# 2. 레이더 망 구조 (Mesh Network)
# ═══════════════════════════════════════════════════════

def radar_mesh_network():
    """
    군집 드론 간 레이더 망이 어떻게 형성되는지,
    각 드론의 감지 반경과 중첩 영역을 보여줌
    """
    print("[2] 레이더 망 구조 (Mesh Network)")

    fig = go.Figure()

    # 7대 군집 드론 (정육각형 + 중심)
    positions = [(0, 0)]  # 중심
    for i in range(6):
        ang = i * math.pi / 3
        positions.append((5 * math.cos(ang), 5 * math.sin(ang)))

    alt = 100  # 고도

    # 각 드론의 레이더 감지 범위 (원형, 반경 4m)
    DETECT_R = 4.0
    theta = np.linspace(0, 2 * math.pi, 50)

    colors_7 = ["#F44336", "#E91E63", "#9C27B0", "#3F51B5",
                "#009688", "#FF9800", "#795548"]

    for i, (px, py) in enumerate(positions):
        col = colors_7[i]

        # 드론 (짧은 라벨만 표시)
        fig.add_trace(go.Scatter3d(
            x=[px], y=[py], z=[alt],
            mode="markers+text",
            marker=dict(size=12, color=col, symbol="diamond",
                        line=dict(width=2, color="white")),
            text=[f"S{i+1}"],
            textposition="top center",
            textfont=dict(size=10, color=col, family="Arial Black"),
            hovertext=f"Sentinel {i+1} (감지 반경 {DETECT_R}m)",
            hoverinfo="text",
            name=f"Sentinel {i+1}" if i < 3 else None,
            showlegend=(i < 3),
        ))

        # 감지 범위 (고도에서 수평 원)
        cx = px + DETECT_R * np.cos(theta)
        cy = py + DETECT_R * np.sin(theta)
        fig.add_trace(go.Scatter3d(
            x=cx.tolist(), y=cy.tolist(), z=[alt] * len(theta),
            mode="lines",
            line=dict(color=col, width=2),
            opacity=0.4,
            showlegend=False, hoverinfo="skip",
        ))

        # 감지 범위 지면 투영 (어떤 영역을 커버하는지)
        ground_r = DETECT_R * 1.5  # 지면에서 더 넓어짐
        gx = px + ground_r * np.cos(theta)
        gy = py + ground_r * np.sin(theta)
        fig.add_trace(go.Scatter3d(
            x=gx.tolist(), y=gy.tolist(), z=[0] * len(theta),
            mode="lines",
            line=dict(color=col, width=1, dash="dot"),
            opacity=0.15,
            showlegend=False, hoverinfo="skip",
        ))

        # 수직 감지 콘 (드론 → 지면)
        for ang_sample in range(0, 360, 60):
            rad = math.radians(ang_sample)
            fig.add_trace(go.Scatter3d(
                x=[px, px + ground_r * math.cos(rad)],
                y=[py, py + ground_r * math.sin(rad)],
                z=[alt, 0],
                mode="lines",
                line=dict(color=col, width=1),
                opacity=0.05,
                showlegend=False, hoverinfo="skip",
            ))

    # 드론 간 통신 링크 (Mesh)
    for i in range(len(positions)):
        for j in range(i + 1, len(positions)):
            dx = positions[i][0] - positions[j][0]
            dy = positions[i][1] - positions[j][1]
            dist = math.sqrt(dx**2 + dy**2)
            if dist <= 6.0:
                fig.add_trace(go.Scatter3d(
                    x=[positions[i][0], positions[j][0]],
                    y=[positions[i][1], positions[j][1]],
                    z=[alt, alt],
                    mode="lines",
                    line=dict(color="#FF5252", width=4),
                    opacity=0.5,
                    showlegend=False,
                    hovertext="Mesh Link (통신 연결)",
                ))

    # 중첩 감지 영역 — 2곳만 표시 (겹침 방지)
    for i in [0, 3]:
        ang = i * math.pi / 3 + math.pi / 6
        mid_r = 2.8
        mx = mid_r * math.cos(ang)
        my = mid_r * math.sin(ang)
        fig.add_trace(go.Scatter3d(
            x=[mx], y=[my], z=[alt - 5],
            mode="text",
            text=["중첩 감지"],
            textfont=dict(size=8, color="#FF6F00"),
            showlegend=False,
        ))

    # 설명 라벨 (위쪽 별도 공간)
    fig.add_trace(go.Scatter3d(
        x=[0], y=[-10], z=[alt + 20],
        mode="text",
        text=["레이더 Mesh Network (7대 Sentinel, 감지 반경 4m)"],
        textfont=dict(size=13, color="#333", family="Arial Black"),
        showlegend=False,
    ))

    fig.add_trace(go.Scatter3d(
        x=[10], y=[0], z=[50],
        mode="text",
        text=["감지 범위 중첩 →\n빈틈 없는 망 형성"],
        textfont=dict(size=10, color="#666"),
        showlegend=False,
    ))

    fig.update_layout(
        title=dict(text="군집 드론 레이더 망 구조 (Mesh Network)",
                   font=dict(size=20, family="Arial Black"), x=0.5),
        scene=dict(
            xaxis=dict(title="X (m)", range=[-12, 12]),
            yaxis=dict(title="Y (m)", range=[-12, 12]),
            zaxis=dict(title="고도 (m)", range=[-5, 130]),
            camera=dict(eye=dict(x=1.3, y=1.3, z=1.0)),
            bgcolor="white",
        ),
        paper_bgcolor="white",
        margin=dict(l=0, r=0, t=60, b=0),
        width=1200, height=800,
    )
    save(fig, "radar_2_mesh_network")


# ═══════════════════════════════════════════════════════
# 3. 유저 드론 감지 + 시간 할당 시나리오
# ═══════════════════════════════════════════════════════

def radar_user_detection():
    """
    유저 드론 진입 → 감지 → 시간 할당 → 비행 → 알림 → 착륙
    전체 운용 시나리오를 타임라인으로 시각화
    """
    print("[3] 유저 드론 감지 + 시간 할당 시나리오")

    fig = go.Figure()

    # 시나리오 타임라인 (왼→오, 간격 넓힘)
    events = [
        {"time": 0, "label": "공역 진입",
         "icon": "circle", "color": "#4CAF50", "size": 16,
         "desc": "레이더 망 경계 통과",
         "label_side": "top"},
        {"time": 5, "label": "ID 인식",
         "icon": "circle", "color": "#2196F3", "size": 16,
         "desc": "삼각 측량 위치 특정",
         "label_side": "bottom"},
        {"time": 10, "label": "시간 할당(30분)",
         "icon": "diamond", "color": "#FF6F00", "size": 18,
         "desc": "비행 허가 + 타이머",
         "label_side": "top"},
        {"time": 15, "label": "정상 비행",
         "icon": "circle", "color": "#2196F3", "size": 14,
         "desc": "위치 추적 + 모니터링",
         "label_side": "bottom"},
        {"time": 20, "label": "5분전 경고",
         "icon": "circle", "color": "#FF9800", "size": 16,
         "desc": "잔여 시간 경고 알림",
         "label_side": "top"},
        {"time": 25, "label": "만료! 착륙유도",
         "icon": "x", "color": "#F44336", "size": 18,
         "desc": "강제 알림 + 착륙 안내",
         "label_side": "bottom"},
    ]

    # 타임라인 메인 라인
    fig.add_trace(go.Scatter3d(
        x=[e["time"] for e in events],
        y=[0] * len(events),
        z=[3] * len(events),
        mode="lines",
        line=dict(color="#333", width=6),
        showlegend=False, hoverinfo="skip",
    ))

    for e in events:
        t = e["time"]
        is_top = e["label_side"] == "top"

        # 이벤트 노드
        fig.add_trace(go.Scatter3d(
            x=[t], y=[0], z=[3],
            mode="markers",
            marker=dict(size=e["size"], color=e["color"],
                        symbol=e["icon"],
                        line=dict(width=2, color="white")),
            showlegend=False,
            hovertext=e["desc"],
            hoverinfo="text",
        ))

        # 이벤트 라벨 (위/아래 교대 배치 — 겹침 방지)
        label_z = 5.5 if is_top else 0.5
        fig.add_trace(go.Scatter3d(
            x=[t], y=[0], z=[label_z],
            mode="text",
            text=[e["label"]],
            textfont=dict(size=11, color=e["color"], family="Arial Black"),
            showlegend=False,
        ))

        # 세로선
        line_z = [3.5, 5.0] if is_top else [1.0, 2.5]
        fig.add_trace(go.Scatter3d(
            x=[t, t], y=[0, 0], z=line_z,
            mode="lines",
            line=dict(color=e["color"], width=1, dash="dot"),
            opacity=0.4,
            showlegend=False, hoverinfo="skip",
        ))

    # 시간 축 라벨
    fig.add_trace(go.Scatter3d(
        x=[12.5], y=[0], z=[7.5],
        mode="text",
        text=["유저 드론 운용 타임라인 ────────▶"],
        textfont=dict(size=13, color="#333", family="Arial Black"),
        showlegend=False,
    ))

    # 하단: 상태 변화 색상 바 (간격 넓힘)
    for i, (start, end, label, col) in enumerate([
        (0, 5, "감지", "#4CAF50"),
        (5, 10, "인증", "#2196F3"),
        (10, 20, "비행 허가", "#FF6F00"),
        (20, 25, "경고/착륙", "#F44336"),
    ]):
        for t_val in np.linspace(start, end, 15):
            fig.add_trace(go.Scatter3d(
                x=[t_val], y=[0], z=[-0.5],
                mode="markers",
                marker=dict(size=5, color=col, opacity=0.5),
                showlegend=False, hoverinfo="skip",
            ))
        fig.add_trace(go.Scatter3d(
            x=[(start + end) / 2], y=[0], z=[-1.5],
            mode="text",
            text=[label],
            textfont=dict(size=9, color=col),
            showlegend=False,
        ))

    fig.update_layout(
        title=dict(text="유저 드론 운용 시나리오: 진입 → 감지 → 시간할당 → 알림 → 착륙",
                   font=dict(size=18, family="Arial Black"), x=0.5),
        scene=dict(
            xaxis=dict(title="시간 →", range=[-2, 28]),
            yaxis=dict(visible=False, range=[-3, 3]),
            zaxis=dict(visible=False, range=[-3, 9]),
            camera=dict(eye=dict(x=0, y=-2.5, z=0.5)),
            bgcolor="white",
        ),
        paper_bgcolor="white",
        margin=dict(l=0, r=0, t=60, b=0),
        width=1300, height=600,
    )
    save(fig, "radar_3_user_scenario")


# ═══════════════════════════════════════════════════════
# 4. 전체 운용 개념도 (조감도)
# ═══════════════════════════════════════════════════════

def radar_operation_concept():
    """
    도시/필드 위에 군집 드론 배치,
    유저 드론들이 비행하는 조감도 (Bird's Eye)
    """
    print("[4] 전체 운용 개념도 (조감도)")

    fig = go.Figure()

    np.random.seed(123)

    # ── 지면 (도시 그리드) ──
    for x in range(-10, 11, 2):
        fig.add_trace(go.Scatter3d(
            x=[x, x], y=[-10, 10], z=[0, 0],
            mode="lines", line=dict(color="#E0E0E0", width=1),
            showlegend=False, hoverinfo="skip",
        ))
    for y in range(-10, 11, 2):
        fig.add_trace(go.Scatter3d(
            x=[-10, 10], y=[y, y], z=[0, 0],
            mode="lines", line=dict(color="#E0E0E0", width=1),
            showlegend=False, hoverinfo="skip",
        ))

    # 건물 (장애물)
    buildings = [(-4, -3, 20), (3, 5, 15), (-2, 6, 25), (6, -4, 18), (0, 0, 10)]
    for bx, by, bh in buildings:
        # 건물 기둥
        for corner in [(-0.5, -0.5), (0.5, -0.5), (0.5, 0.5), (-0.5, 0.5)]:
            fig.add_trace(go.Scatter3d(
                x=[bx + corner[0]] * 2, y=[by + corner[1]] * 2, z=[0, bh],
                mode="lines", line=dict(color="#B0BEC5", width=2),
                showlegend=False, hoverinfo="skip",
            ))
        # 건물 상단
        cx = [bx - 0.5, bx + 0.5, bx + 0.5, bx - 0.5]
        cy = [by - 0.5, by - 0.5, by + 0.5, by + 0.5]
        fig.add_trace(go.Mesh3d(
            x=cx, y=cy, z=[bh] * 4,
            i=[0, 0], j=[1, 2], k=[2, 3],
            color="#90A4AE", opacity=0.3,
            showlegend=False, hoverinfo="skip",
        ))

    # ── 군집 드론 (고도 100m, 정육각형) ──
    sentinel_alt = 100
    sentinel_pos = []
    for i in range(6):
        ang = i * math.pi / 3
        sentinel_pos.append((7 * math.cos(ang), 7 * math.sin(ang)))
    sentinel_pos.append((0, 0))  # 중심

    fig.add_trace(go.Scatter3d(
        x=[p[0] for p in sentinel_pos],
        y=[p[1] for p in sentinel_pos],
        z=[sentinel_alt] * len(sentinel_pos),
        mode="markers",
        marker=dict(size=10, color="#F44336", symbol="diamond",
                    line=dict(width=2, color="white")),
        hovertext=[f"Sentinel {i+1}" for i in range(len(sentinel_pos))],
        hoverinfo="text",
        name="군집 드론 (Sentinel) @ 100m",
    ))

    # 레이더 망 (Mesh)
    for i in range(len(sentinel_pos)):
        for j in range(i + 1, len(sentinel_pos)):
            dx = sentinel_pos[i][0] - sentinel_pos[j][0]
            dy = sentinel_pos[i][1] - sentinel_pos[j][1]
            if math.sqrt(dx**2 + dy**2) <= 8:
                fig.add_trace(go.Scatter3d(
                    x=[sentinel_pos[i][0], sentinel_pos[j][0]],
                    y=[sentinel_pos[i][1], sentinel_pos[j][1]],
                    z=[sentinel_alt, sentinel_alt],
                    mode="lines",
                    line=dict(color="#FF5252", width=3),
                    opacity=0.35,
                    showlegend=False, hoverinfo="skip",
                ))

    # 레이더 커버리지 원 (지면에 투영)
    cov_theta = np.linspace(0, 2 * math.pi, 80)
    cov_r = 9
    fig.add_trace(go.Scatter3d(
        x=(cov_r * np.cos(cov_theta)).tolist(),
        y=(cov_r * np.sin(cov_theta)).tolist(),
        z=[0] * 80,
        mode="lines",
        line=dict(color="#FF6F00", width=3, dash="dash"),
        name="관제 공역 경계",
    ))

    # ── 유저 드론 (다양한 고도, 간격 확보) ──
    users = [
        {"x": 4, "y": 3, "z": 50, "short": "A", "hover": "User A: 잔여 25:00", "color": "#2196F3"},
        {"x": -6, "y": 4, "z": 65, "short": "B", "hover": "User B: 잔여 12:30", "color": "#2196F3"},
        {"x": 3, "y": -5, "z": 40, "short": "C", "hover": "User C: 잔여 03:00 (경고)", "color": "#FF9800"},
        {"x": -4, "y": -6, "z": 55, "short": "D", "hover": "User D: 시간 만료!", "color": "#F44336"},
        {"x": 7, "y": -1, "z": 75, "short": "E", "hover": "User E: 진입 중...", "color": "#4CAF50"},
    ]

    for u in users:
        fig.add_trace(go.Scatter3d(
            x=[u["x"]], y=[u["y"]], z=[u["z"]],
            mode="markers+text",
            marker=dict(size=10, color=u["color"],
                        line=dict(width=2, color="white")),
            text=[u["short"]],
            textposition="top center",
            textfont=dict(size=11, color=u["color"], family="Arial Black"),
            hovertext=u["hover"],
            hoverinfo="text",
            showlegend=False,
        ))

        # 고도선
        fig.add_trace(go.Scatter3d(
            x=[u["x"], u["x"]], y=[u["y"], u["y"]], z=[0, u["z"]],
            mode="lines",
            line=dict(color=u["color"], width=1, dash="dot"),
            opacity=0.3,
            showlegend=False, hoverinfo="skip",
        ))

    # User D 경고 링
    wr = 2.0
    fig.add_trace(go.Scatter3d(
        x=(-4 + wr * np.cos(cov_theta[:40])).tolist(),
        y=(-6 + wr * np.sin(cov_theta[:40])).tolist(),
        z=[55] * 40,
        mode="lines",
        line=dict(color="#F44336", width=3),
        name="시간 만료 경고",
    ))

    # 착륙 유도 경로 (User D → 지면)
    land_t = np.linspace(0, 1, 20)
    fig.add_trace(go.Scatter3d(
        x=(-4 + land_t * 2).tolist(),
        y=(-6 + land_t * 3).tolist(),
        z=(55 * (1 - land_t)).tolist(),
        mode="lines",
        line=dict(color="#F44336", width=2, dash="dash"),
        name="착륙 유도 경로",
    ))

    # 유저 드론 범례
    for status, col in [("비행 허가 (정상)", "#2196F3"),
                         ("시간 임박 (경고)", "#FF9800"),
                         ("시간 만료 (착륙 유도)", "#F44336"),
                         ("신규 진입 (감지 중)", "#4CAF50")]:
        fig.add_trace(go.Scatter3d(
            x=[0], y=[0], z=[-10],  # 화면 밖
            mode="markers",
            marker=dict(size=8, color=col),
            name=status,
        ))

    # 고도 구간 라벨 (개별 배치로 겹침 방지)
    fig.add_trace(go.Scatter3d(
        x=[-12], y=[-10], z=[0],
        mode="text", text=["지면"],
        textfont=dict(size=10, color="#999"),
        showlegend=False,
    ))
    fig.add_trace(go.Scatter3d(
        x=[-12], y=[-10], z=[50],
        mode="text", text=["유저 비행구간 30~90m"],
        textfont=dict(size=9, color="#2196F3"),
        showlegend=False,
    ))
    fig.add_trace(go.Scatter3d(
        x=[-12], y=[-10], z=[100],
        mode="text", text=["군집 드론 100m"],
        textfont=dict(size=9, color="#F44336"),
        showlegend=False,
    ))

    fig.update_layout(
        title=dict(text="군집 드론 레이더 관제: 전체 운용 개념도",
                   font=dict(size=20, family="Arial Black"), x=0.5),
        scene=dict(
            xaxis=dict(title="X (m)", range=[-13, 13],
                       gridcolor="#f0f0f0"),
            yaxis=dict(title="Y (m)", range=[-13, 13],
                       gridcolor="#f0f0f0"),
            zaxis=dict(title="고도 (m)", range=[-5, 120],
                       gridcolor="#f0f0f0"),
            camera=dict(eye=dict(x=1.4, y=1.4, z=1.0)),
            bgcolor="#f8f9fa",
        ),
        paper_bgcolor="white",
        margin=dict(l=0, r=0, t=60, b=0),
        width=1300, height=900,
        legend=dict(font=dict(size=11), x=0.01, y=0.99,
                    bgcolor="rgba(255,255,255,0.9)"),
    )
    save(fig, "radar_4_operation_concept")


# ═══════════════════════════════════════════════════════
# Main
# ═══════════════════════════════════════════════════════

if __name__ == "__main__":
    print("=" * 60)
    print("군집 드론 레이더 망 + 유저 드론 ATC 시각화")
    print("=" * 60)

    radar_system_overview()
    radar_mesh_network()
    radar_user_detection()
    radar_operation_concept()

    print("\n" + "=" * 60)
    files = sorted(f for f in os.listdir(OUTPUT_DIR) if f.startswith("radar_"))
    print(f"완료! {len(files)}개 파일 생성:")
    for f in files:
        print(f"  {f}")
    print("=" * 60)
