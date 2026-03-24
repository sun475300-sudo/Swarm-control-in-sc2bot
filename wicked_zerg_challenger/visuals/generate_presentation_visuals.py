# -*- coding: utf-8 -*-
"""
발표 시각화 자료 생성기
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
캡스톤 4개 + IR 4개 + 보고서 11개 = 총 19개 HTML

python generate_presentation_visuals.py
"""

import os
import math
import numpy as np
import plotly.graph_objects as go

OUTPUT_DIR = os.path.dirname(os.path.abspath(__file__))
DESKTOP_DIR = r"c:\Users\sun47\Desktop\캡스톤 디자인\visuals"


def save(fig, name):
    path = os.path.join(OUTPUT_DIR, f"{name}.html")
    fig.write_html(path, include_plotlyjs="cdn")
    print(f"  -> {path}")
    if os.path.isdir(DESKTOP_DIR):
        desktop_path = os.path.join(DESKTOP_DIR, f"{name}.html")
        fig.write_html(desktop_path, include_plotlyjs="cdn")


# ═══════════════════════════════════════════════════════════════
#  캡스톤 디자인 발표 시각화 (학술/기술 검증 집중)
# ═══════════════════════════════════════════════════════════════


# ───────────────────────────────────────────────────────────────
# 캡스톤 1. 비용/위험 비교 인포그래픽
# ───────────────────────────────────────────────────────────────

def capstone_cost_comparison():
    """
    실물 드론 R&D vs SC2 시뮬레이션 비용/위험/시간 비교
    드라마틱한 스케일 차이를 3D 막대 차트로 강조
    """
    print("[캡스톤 1] 비용/위험 비교 인포그래픽")

    fig = go.Figure()

    categories = [
        "하드웨어\n비용",
        "테스트\n반복 횟수",
        "추락\n위험도",
        "공역\n인허가",
        "개발\n기간",
    ]

    # 정규화된 비교 값 (시각화용, 0-100 스케일)
    real_vals = [95, 5, 90, 85, 80]
    sim_vals  = [2, 98, 2, 2, 20]

    # 실제 표시 라벨
    real_labels = ["~5,000만원", "~10회", "HIGH", "6개월+", "12개월"]
    sim_labels  = ["₩0", "100만회+", "ZERO", "불필요", "3개월"]

    bar_width = 0.35
    n = len(categories)

    for i in range(n):
        x_base = i * 2.5

        # 실물 드론 바 (빨강 계열)
        fig.add_trace(go.Mesh3d(
            x=[x_base - bar_width, x_base + bar_width,
               x_base + bar_width, x_base - bar_width,
               x_base - bar_width, x_base + bar_width,
               x_base + bar_width, x_base - bar_width],
            y=[-0.8, -0.8, -0.8, -0.8, -0.8, -0.8, -0.8, -0.8],
            z=[0, 0, real_vals[i], real_vals[i],
               0, 0, real_vals[i], real_vals[i]],
            i=[0, 0, 4, 4, 0, 2], j=[1, 2, 5, 6, 4, 6],
            k=[2, 3, 6, 7, 5, 7],
            color="#EF5350", opacity=0.8,
            showlegend=False, hoverinfo="skip",
        ))

        # SC2 시뮬 바 (파랑 계열)
        fig.add_trace(go.Mesh3d(
            x=[x_base - bar_width, x_base + bar_width,
               x_base + bar_width, x_base - bar_width,
               x_base - bar_width, x_base + bar_width,
               x_base + bar_width, x_base - bar_width],
            y=[0.8, 0.8, 0.8, 0.8, 0.8, 0.8, 0.8, 0.8],
            z=[0, 0, sim_vals[i], sim_vals[i],
               0, 0, sim_vals[i], sim_vals[i]],
            i=[0, 0, 4, 4, 0, 2], j=[1, 2, 5, 6, 4, 6],
            k=[2, 3, 6, 7, 5, 7],
            color="#42A5F5", opacity=0.8,
            showlegend=False, hoverinfo="skip",
        ))

        # 카테고리 라벨 (아래)
        fig.add_trace(go.Scatter3d(
            x=[x_base], y=[0], z=[-8],
            mode="text",
            text=[categories[i]],
            textfont=dict(size=13, color="#333", family="Arial Black"),
            showlegend=False, hoverinfo="skip",
        ))

        # 실물 값 라벨
        fig.add_trace(go.Scatter3d(
            x=[x_base], y=[-1.8], z=[real_vals[i] + 3],
            mode="text",
            text=[real_labels[i]],
            textfont=dict(size=11, color="#C62828", family="Arial Black"),
            showlegend=False, hoverinfo="skip",
        ))

        # SC2 값 라벨
        fig.add_trace(go.Scatter3d(
            x=[x_base], y=[1.8], z=[sim_vals[i] + 3],
            mode="text",
            text=[sim_labels[i]],
            textfont=dict(size=11, color="#1565C0", family="Arial Black"),
            showlegend=False, hoverinfo="skip",
        ))

    # 범례 라벨
    fig.add_trace(go.Scatter3d(
        x=[-2], y=[-1.5], z=[105],
        mode="markers+text",
        marker=dict(size=12, color="#EF5350"),
        text=["  실물 드론 R&D"],
        textposition="middle right",
        textfont=dict(size=14, color="#C62828", family="Arial Black"),
        showlegend=False,
    ))
    fig.add_trace(go.Scatter3d(
        x=[-2], y=[1.5], z=[105],
        mode="markers+text",
        marker=dict(size=12, color="#42A5F5"),
        text=["  SC2 시뮬레이션"],
        textposition="middle right",
        textfont=dict(size=14, color="#1565C0", family="Arial Black"),
        showlegend=False,
    ))

    fig.update_layout(
        title=dict(
            text="왜 SC2인가? — 실물 드론 vs 시뮬레이션 비교",
            font=dict(size=22, family="Arial Black"),
            x=0.5,
        ),
        scene=dict(
            xaxis=dict(visible=False, range=[-3, 13]),
            yaxis=dict(visible=False, range=[-4, 4]),
            zaxis=dict(visible=False, range=[-12, 115]),
            camera=dict(eye=dict(x=1.2, y=2.2, z=0.6)),
            bgcolor="white",
        ),
        paper_bgcolor="white",
        margin=dict(l=0, r=0, t=60, b=0),
        width=1200, height=750,
    )
    save(fig, "capstone_1_cost_comparison")


# ───────────────────────────────────────────────────────────────
# 캡스톤 2. SC2 = Digital Twin 레이더 차트
# ───────────────────────────────────────────────────────────────

def capstone_digital_twin():
    """
    SC2 엔진의 시뮬레이션 역량을 레이더(spider) 차트로 비교
    SC2 vs 전용 시뮬레이터(Gazebo) vs 실제 환경
    """
    print("[캡스톤 2] SC2 = Digital Twin 레이더 차트")

    fig = go.Figure()

    axes = [
        "물리 엔진\n(충돌/이동)",
        "시야 제약\n(Fog of War)",
        "다중 에이전트\n(200+ 유닛)",
        "실시간 반응\n(22.4 fps)",
        "경로 장애물\n(지형/건물)",
        "자원 관리\n(에너지/연료)",
    ]

    # 점수 (0~10)
    sc2_scores    = [8, 9, 10, 9, 8, 9]
    gazebo_scores = [10, 3, 5, 7, 9, 4]
    real_scores   = [10, 10, 3, 10, 10, 10]

    # Plotly polar (레이더 차트)
    fig.add_trace(go.Scatterpolar(
        r=sc2_scores + [sc2_scores[0]],
        theta=axes + [axes[0]],
        fill="toself",
        fillcolor="rgba(25,118,210,0.15)",
        line=dict(color="#1976D2", width=3),
        marker=dict(size=10, color="#1976D2"),
        name="SC2 게임 엔진",
    ))

    fig.add_trace(go.Scatterpolar(
        r=gazebo_scores + [gazebo_scores[0]],
        theta=axes + [axes[0]],
        fill="toself",
        fillcolor="rgba(123,31,162,0.12)",
        line=dict(color="#7B1FA2", width=3, dash="dash"),
        marker=dict(size=10, color="#7B1FA2"),
        name="Gazebo 시뮬레이터",
    ))

    fig.add_trace(go.Scatterpolar(
        r=real_scores + [real_scores[0]],
        theta=axes + [axes[0]],
        fill="toself",
        fillcolor="rgba(46,125,50,0.10)",
        line=dict(color="#2E7D32", width=3, dash="dot"),
        marker=dict(size=10, color="#2E7D32"),
        name="실제 드론 환경",
    ))

    fig.update_layout(
        title=dict(
            text="SC2 = 최적의 Digital Twin 시뮬레이터",
            font=dict(size=22, family="Arial Black"),
            x=0.5,
        ),
        polar=dict(
            radialaxis=dict(
                visible=True, range=[0, 11],
                tickfont=dict(size=11),
            ),
            angularaxis=dict(
                tickfont=dict(size=12, family="Arial Black", color="#333"),
            ),
            bgcolor="rgba(245,245,245,0.5)",
        ),
        paper_bgcolor="white",
        legend=dict(
            font=dict(size=13), x=0.02, y=0.98,
            bgcolor="rgba(255,255,255,0.9)",
            bordercolor="#ccc", borderwidth=1,
        ),
        margin=dict(l=80, r=80, t=80, b=40),
        width=1000, height=750,
        annotations=[
            dict(
                text="SC2는 다중 에이전트 + 시야 제약 + 실시간 반응에서 압도적 우위",
                x=0.5, y=-0.05, xref="paper", yref="paper",
                showarrow=False,
                font=dict(size=14, color="#1976D2", family="Arial Black"),
            )
        ],
    )
    save(fig, "capstone_2_digital_twin")


# ───────────────────────────────────────────────────────────────
# 캡스톤 3. LLM(JARVIS) + SC2 통합 아키텍처
# ───────────────────────────────────────────────────────────────

def capstone_llm_integration():
    """
    자연어 지휘관(Commander) → AgentRouter → 각 모듈 제어
    3D 계층 다이어그램 + 데이터 흐름 곡선
    """
    print("[캡스톤 3] LLM + SC2 통합 아키텍처")

    fig = go.Figure()

    # ── 계층 정의 ──
    # Layer 3 (최상단): 인간 지휘관 + LLM
    # Layer 2 (중간): AgentRouter + ModelSelector + Orchestrator
    # Layer 1 (하단): SC2 실행 모듈들
    # Layer 0 (바닥): SC2 게임 환경

    # Layer 3: Commander
    commander_nodes = [
        {"label": "인간 지휘관\n(자연어 명령)", "x": -3, "y": 0, "z": 9,
         "color": "#FF6F00", "size": 22},
        {"label": "JARVIS\n(LLM AI 두뇌)", "x": 3, "y": 0, "z": 9,
         "color": "#FFD600", "size": 22},
    ]

    # Layer 2: Agent System
    agent_nodes = [
        {"label": "AgentRouter\n(도메인 라우팅)", "x": -4, "y": 0, "z": 6,
         "color": "#7B1FA2", "size": 16},
        {"label": "ModelSelector\n(모델 선택)", "x": 0, "y": 0, "z": 6,
         "color": "#7B1FA2", "size": 16},
        {"label": "WorkflowOrchestrator\n(파이프라인 실행)", "x": 4, "y": 0, "z": 6,
         "color": "#7B1FA2", "size": 16},
    ]

    # Layer 1: SC2 Modules
    module_nodes = [
        {"label": "Boids\n군집 제어", "x": -6, "y": 0, "z": 3,
         "color": "#1976D2", "size": 14},
        {"label": "Strategy\n전략 관리", "x": -3, "y": 0, "z": 3,
         "color": "#1976D2", "size": 14},
        {"label": "Authority\n우선순위", "x": 0, "y": 0, "z": 3,
         "color": "#1976D2", "size": 14},
        {"label": "RL Agent\n강화학습", "x": 3, "y": 0, "z": 3,
         "color": "#1976D2", "size": 14},
        {"label": "Defense\n방어 체계", "x": 6, "y": 0, "z": 3,
         "color": "#1976D2", "size": 14},
    ]

    # Layer 0: SC2 Environment
    env_node = [
        {"label": "StarCraft II 게임 환경\n(200+ 유닛 실시간 시뮬레이션)",
         "x": 0, "y": 0, "z": 0, "color": "#2E7D32", "size": 20},
    ]

    all_layers = [
        (commander_nodes, "지휘 계층"),
        (agent_nodes, "AI 에이전트 계층"),
        (module_nodes, "실행 모듈 계층"),
        (env_node, "시뮬레이션 환경"),
    ]

    # 계층 배경 플랫폼
    layer_configs = [
        {"z": 8.5, "w": 6, "h": 1.5, "color": "#FFF3E0"},
        {"z": 5.5, "w": 7, "h": 1.5, "color": "#F3E5F5"},
        {"z": 2.5, "w": 8, "h": 1.5, "color": "#E3F2FD"},
        {"z": -0.5, "w": 5, "h": 1.5, "color": "#E8F5E9"},
    ]

    for lc in layer_configs:
        z, w, h = lc["z"], lc["w"], lc["h"]
        fig.add_trace(go.Mesh3d(
            x=[-w, w, w, -w], y=[-h, -h, h, h], z=[z] * 4,
            i=[0, 0], j=[1, 2], k=[2, 3],
            color=lc["color"], opacity=0.3,
            showlegend=False, hoverinfo="skip",
        ))

    # 노드 렌더링
    for layer, _ in all_layers:
        for node in layer:
            fig.add_trace(go.Scatter3d(
                x=[node["x"]], y=[node["y"]], z=[node["z"]],
                mode="markers+text",
                marker=dict(
                    size=node["size"], color=node["color"],
                    opacity=0.9,
                    line=dict(width=2, color="white"),
                    symbol="circle",
                ),
                text=[node["label"]],
                textposition="top center",
                textfont=dict(size=11, color=node["color"],
                              family="Arial Black"),
                showlegend=False,
            ))

    # ── 연결 곡선 (데이터 흐름) ──
    connections = [
        # 지휘관 → JARVIS
        (-3, 0, 9, 3, 0, 9, "#FF6F00"),
        # JARVIS → AgentRouter
        (3, 0, 9, -4, 0, 6, "#FFD600"),
        # JARVIS → ModelSelector
        (3, 0, 9, 0, 0, 6, "#FFD600"),
        # JARVIS → Orchestrator
        (3, 0, 9, 4, 0, 6, "#FFD600"),
        # Agent층 → Module층
        (-4, 0, 6, -6, 0, 3, "#7B1FA2"),
        (-4, 0, 6, -3, 0, 3, "#7B1FA2"),
        (0, 0, 6, 0, 0, 3, "#7B1FA2"),
        (4, 0, 6, 3, 0, 3, "#7B1FA2"),
        (4, 0, 6, 6, 0, 3, "#7B1FA2"),
        # Module층 → 환경
        (-6, 0, 3, 0, 0, 0, "#1976D2"),
        (-3, 0, 3, 0, 0, 0, "#1976D2"),
        (0, 0, 3, 0, 0, 0, "#1976D2"),
        (3, 0, 3, 0, 0, 0, "#1976D2"),
        (6, 0, 3, 0, 0, 0, "#1976D2"),
    ]

    for x1, y1, z1, x2, y2, z2, col in connections:
        t = np.linspace(0, 1, 20)
        cx = x1 + (x2 - x1) * t
        cy = np.sin(t * math.pi) * 0.8
        cz = z1 + (z2 - z1) * t

        fig.add_trace(go.Scatter3d(
            x=cx, y=cy, z=cz,
            mode="lines",
            line=dict(color=col, width=3),
            opacity=0.5,
            showlegend=False, hoverinfo="skip",
        ))

    # 계층 라벨 (좌측)
    layer_labels = [
        (9.5, "Layer 3: 지휘 (Commander)", "#FF6F00"),
        (6.5, "Layer 2: AI 에이전트", "#7B1FA2"),
        (3.5, "Layer 1: 실행 모듈", "#1976D2"),
        (0.5, "Layer 0: SC2 환경", "#2E7D32"),
    ]

    for z, label, col in layer_labels:
        fig.add_trace(go.Scatter3d(
            x=[-9], y=[0], z=[z],
            mode="text",
            text=[label],
            textfont=dict(size=12, color=col, family="Arial Black"),
            showlegend=False,
        ))

    # 데이터 흐름 화살표 라벨
    flow_labels = [
        (0, 1.5, 7.5, "\"적 기지를 공격해\"", "#FF6F00"),
        (-2, 1.5, 4.5, "라우팅 + 모델 선택", "#7B1FA2"),
        (-3, 1.5, 1.5, "Boids 군집 이동 실행", "#1976D2"),
    ]

    for x, y, z, label, col in flow_labels:
        fig.add_trace(go.Scatter3d(
            x=[x], y=[y], z=[z],
            mode="text",
            text=[label],
            textfont=dict(size=11, color=col),
            showlegend=False,
        ))

    fig.update_layout(
        title=dict(
            text="LLM(JARVIS) + SC2 통합 지휘 아키텍처",
            font=dict(size=22, family="Arial Black"),
            x=0.5,
        ),
        scene=dict(
            xaxis=dict(visible=False, range=[-11, 9]),
            yaxis=dict(visible=False, range=[-3, 4]),
            zaxis=dict(visible=False, range=[-2, 12]),
            camera=dict(
                eye=dict(x=0.8, y=2.5, z=0.5),
                up=dict(x=0, y=0, z=1),
            ),
            bgcolor="white",
        ),
        paper_bgcolor="white",
        margin=dict(l=0, r=0, t=60, b=0),
        width=1200, height=800,
    )
    save(fig, "capstone_3_llm_integration")


# ───────────────────────────────────────────────────────────────
# 캡스톤 4. 자가 복구(Self-Healing) 로직 흐름도
# ───────────────────────────────────────────────────────────────

def capstone_self_healing():
    """
    Authority Mode 5단계 상태 전이 + 자가 복구 순환
    BALANCED → ECONOMY → STRATEGY → COMBAT → EMERGENCY → 복구 → BALANCED
    """
    print("[캡스톤 4] 자가 복구 로직 흐름도")

    fig = go.Figure()

    # 원형 배치의 5개 상태 (시계방향, 아래→위가 긴급도 상승)
    states = [
        {"name": "BALANCED\n(균형 모드)", "angle": 270,
         "color": "#4CAF50", "desc": "모든 시스템\n정상 협업",
         "threat": "위협 없음", "r": 4},
        {"name": "ECONOMY\n(경제 모드)", "angle": 342,
         "color": "#8BC34A", "desc": "자원 수집\n우선",
         "threat": "위협 낮음", "r": 4},
        {"name": "STRATEGY\n(전략 모드)", "angle": 54,
         "color": "#FFC107", "desc": "공격 타이밍\n계획",
         "threat": "위협 감지", "r": 4},
        {"name": "COMBAT\n(전투 모드)", "angle": 126,
         "color": "#FF9800", "desc": "전투 유닛\n최우선 생산",
         "threat": "교전 중", "r": 4},
        {"name": "EMERGENCY\n(긴급 모드)", "angle": 198,
         "color": "#F44336", "desc": "전 유닛\n긴급 회피",
         "threat": "생존 위기", "r": 4},
    ]

    # 상태 노드 렌더링
    for i, s in enumerate(states):
        rad = math.radians(s["angle"])
        x = s["r"] * math.cos(rad)
        y = s["r"] * math.sin(rad)
        z = i * 1.5  # 위쪽으로 갈수록 긴급도 상승

        # 노드
        fig.add_trace(go.Scatter3d(
            x=[x], y=[y], z=[z],
            mode="markers+text",
            marker=dict(size=22, color=s["color"], opacity=0.9,
                        line=dict(width=3, color="white"),
                        symbol="circle"),
            text=[s["name"]],
            textposition="top center",
            textfont=dict(size=13, color=s["color"], family="Arial Black"),
            showlegend=False,
        ))

        # 설명 텍스트
        desc_x = (s["r"] + 2.5) * math.cos(rad)
        desc_y = (s["r"] + 2.5) * math.sin(rad)
        fig.add_trace(go.Scatter3d(
            x=[desc_x], y=[desc_y], z=[z],
            mode="text",
            text=[s["desc"]],
            textfont=dict(size=10, color="#666"),
            showlegend=False,
        ))

        # 위협 수준 라벨
        fig.add_trace(go.Scatter3d(
            x=[x], y=[y], z=[z - 0.6],
            mode="text",
            text=[f"[{s['threat']}]"],
            textfont=dict(size=9, color=s["color"]),
            showlegend=False,
        ))

    # ── 전이 화살표 (상태 간 연결) ──
    for i in range(len(states)):
        j = (i + 1) % len(states)
        si, sj = states[i], states[j]

        rad_i = math.radians(si["angle"])
        rad_j = math.radians(sj["angle"])

        x1 = si["r"] * math.cos(rad_i)
        y1 = si["r"] * math.sin(rad_i)
        z1 = i * 1.5

        x2 = sj["r"] * math.cos(rad_j)
        y2 = sj["r"] * math.sin(rad_j)
        z2 = j * 1.5

        t = np.linspace(0, 1, 25)
        cx = x1 + (x2 - x1) * t
        cy = y1 + (y2 - y1) * t
        # 약간 안쪽으로 볼록하게
        mid_rad = math.radians((si["angle"] + sj["angle"]) / 2)
        bulge = np.sin(t * math.pi) * 1.0
        cx += bulge * math.cos(mid_rad + math.pi)
        cy += bulge * math.sin(mid_rad + math.pi)
        cz = z1 + (z2 - z1) * t

        # 위협 상승 시 빨강, 복구 시 초록
        if j > i or (i == 4 and j == 0):
            col = "#F44336" if i != 4 else "#4CAF50"
            dash_style = "solid" if i != 4 else "dash"
        else:
            col = "#4CAF50"
            dash_style = "dash"

        fig.add_trace(go.Scatter3d(
            x=cx, y=cy, z=cz,
            mode="lines",
            line=dict(color=col, width=4),
            showlegend=False, hoverinfo="skip",
        ))

    # 복구 경로 강조 (EMERGENCY → BALANCED)
    fig.add_trace(go.Scatter3d(
        x=[0], y=[0], z=[3],
        mode="text",
        text=["자가 복구 순환\n(Self-Healing Cycle)"],
        textfont=dict(size=16, color="#333", family="Arial Black"),
        showlegend=False,
    ))

    # 화살표 라벨
    fig.add_trace(go.Scatter3d(
        x=[2], y=[-3], z=[7.5],
        mode="text",
        text=["위협 감지 →\n모드 자동 전환"],
        textfont=dict(size=12, color="#F44336"),
        showlegend=False,
    ))

    fig.add_trace(go.Scatter3d(
        x=[-3], y=[-2], z=[1],
        mode="text",
        text=["위협 해소 →\n자동 복구 ↩"],
        textfont=dict(size=12, color="#4CAF50"),
        showlegend=False,
    ))

    # 좌측 긴급도 축
    fig.add_trace(go.Scatter3d(
        x=[-8, -8], y=[0, 0], z=[0, 6],
        mode="lines+text",
        line=dict(color="#333", width=3),
        text=["낮음", "높음"],
        textposition=["bottom center", "top center"],
        textfont=dict(size=12, color="#333"),
        showlegend=False,
    ))
    fig.add_trace(go.Scatter3d(
        x=[-9], y=[0], z=[3],
        mode="text",
        text=["긴\n급\n도"],
        textfont=dict(size=14, color="#333", family="Arial Black"),
        showlegend=False,
    ))

    fig.update_layout(
        title=dict(
            text="Authority Mode: 자가 복구(Self-Healing) 상태 전이",
            font=dict(size=22, family="Arial Black"),
            x=0.5,
        ),
        scene=dict(
            xaxis=dict(visible=False, range=[-11, 9]),
            yaxis=dict(visible=False, range=[-8, 8]),
            zaxis=dict(visible=False, range=[-2, 9]),
            camera=dict(
                eye=dict(x=1.5, y=1.5, z=0.8),
                up=dict(x=0, y=0, z=1),
            ),
            bgcolor="white",
        ),
        paper_bgcolor="white",
        margin=dict(l=0, r=0, t=60, b=0),
        width=1100, height=800,
    )
    save(fig, "capstone_4_self_healing")


# ═══════════════════════════════════════════════════════════════
#  IR/기업 설명회 시각화 (비즈니스/가치 창출 집중)
# ═══════════════════════════════════════════════════════════════


# ───────────────────────────────────────────────────────────────
# IR 1. 시장 페인포인트 시각화
# ───────────────────────────────────────────────────────────────

def ir_market_painpoint():
    """
    드론 군집 R&D의 3대 난제를 3D 인포그래픽으로 시각화
    비용 / 시간 / 위험
    """
    print("[IR 1] 시장 페인포인트 시각화")

    fig = go.Figure()

    painpoints = [
        {
            "name": "비용\n(COST)",
            "x": -5, "z": 0,
            "color": "#F44336",
            "icon_size": 25,
            "stats": [
                "드론 1대: ~500만원",
                "10대 편대: ~5,000만원",
                "추락 1회: ~300만원 손실",
                "연간 테스트 예산: ~2억원+",
            ],
            "highlight": "시뮬레이션: ₩0",
        },
        {
            "name": "시간\n(TIME)",
            "x": 0, "z": 0,
            "color": "#FF9800",
            "icon_size": 25,
            "stats": [
                "공역 인허가: 2~6개월",
                "테스트장 확보: 1~3개월",
                "1회 비행 테스트: 반나절",
                "데이터 분석: 1~2주",
            ],
            "highlight": "시뮬레이션: 즉시 실행",
        },
        {
            "name": "위험\n(RISK)",
            "x": 5, "z": 0,
            "color": "#9C27B0",
            "icon_size": 25,
            "stats": [
                "추락 시 장비 전파",
                "비행 데이터 유실",
                "인명 사고 가능성",
                "보험/법적 리스크",
            ],
            "highlight": "시뮬레이션: 제로 리스크",
        },
    ]

    for pp in painpoints:
        x = pp["x"]
        col = pp["color"]

        # 큰 아이콘 마커
        fig.add_trace(go.Scatter3d(
            x=[x], y=[0], z=[6],
            mode="markers+text",
            marker=dict(size=pp["icon_size"], color=col, opacity=0.9,
                        symbol="diamond",
                        line=dict(width=3, color="white")),
            text=[pp["name"]],
            textposition="top center",
            textfont=dict(size=16, color=col, family="Arial Black"),
            showlegend=False,
        ))

        # 통계 항목들 (아래로 나열)
        for i, stat in enumerate(pp["stats"]):
            fig.add_trace(go.Scatter3d(
                x=[x], y=[0], z=[4.5 - i * 1.2],
                mode="markers+text",
                marker=dict(size=6, color=col, opacity=0.6),
                text=[f"  {stat}"],
                textposition="middle right",
                textfont=dict(size=11, color="#444"),
                showlegend=False,
            ))

        # 하이라이트 (솔루션)
        fig.add_trace(go.Scatter3d(
            x=[x], y=[0], z=[-0.8],
            mode="text",
            text=[f"→ {pp['highlight']}"],
            textfont=dict(size=13, color="#2E7D32", family="Arial Black"),
            showlegend=False,
        ))

    # 상단 시장 규모 배너
    fig.add_trace(go.Scatter3d(
        x=[0], y=[0], z=[8.5],
        mode="text",
        text=["군용 드론 시장: 2030년 $58.4B 전망 (CAGR 12.7%)"],
        textfont=dict(size=15, color="#333", family="Arial Black"),
        showlegend=False,
    ))

    fig.add_trace(go.Scatter3d(
        x=[0], y=[0], z=[7.5],
        mode="text",
        text=["우크라이나 전쟁 이후 Drone Swarm 수요 급증 — 그러나 R&D 비용이 진입장벽"],
        textfont=dict(size=12, color="#666"),
        showlegend=False,
    ))

    # 하단 결론
    fig.add_trace(go.Scatter3d(
        x=[0], y=[0], z=[-2.5],
        mode="text",
        text=["\"실물 없이 검증할 수 있다면?\" — 우리의 솔루션이 답입니다"],
        textfont=dict(size=15, color="#1976D2", family="Arial Black"),
        showlegend=False,
    ))

    fig.update_layout(
        title=dict(
            text="드론 군집 R&D의 3대 페인포인트",
            font=dict(size=22, family="Arial Black"),
            x=0.5,
        ),
        scene=dict(
            xaxis=dict(visible=False, range=[-9, 9]),
            yaxis=dict(visible=False, range=[-3, 3]),
            zaxis=dict(visible=False, range=[-4, 10]),
            camera=dict(
                eye=dict(x=0, y=2.5, z=0.3),
                up=dict(x=0, y=0, z=1),
            ),
            bgcolor="white",
        ),
        paper_bgcolor="white",
        margin=dict(l=0, r=0, t=60, b=0),
        width=1200, height=800,
    )
    save(fig, "ir_1_market_painpoint")


# ───────────────────────────────────────────────────────────────
# IR 2. Virtual Testbed + AI C2 솔루션 개요
# ───────────────────────────────────────────────────────────────

def ir_virtual_testbed():
    """
    비즈니스 친화적 3블록 아키텍처:
    Virtual Testbed → AI Brain (C2) → Real Deployment
    """
    print("[IR 2] Virtual Testbed + AI C2 솔루션 개요")

    fig = go.Figure()

    blocks = [
        {
            "title": "가상 테스트베드\n(Virtual Testbed)",
            "subtitle": "SC2 기반 초정밀 시뮬레이터",
            "x": -5, "z": 0,
            "color": "#1976D2",
            "features": [
                "200+ 에이전트 동시 운용",
                "물리 충돌 + 시야 제약",
                "수백만 회 무한 반복",
                "비용: ₩0 / 위험: Zero",
            ],
            "value": "R&D 비용 90%+ 절감",
        },
        {
            "title": "AI 지휘 두뇌\n(AI C2 Brain)",
            "subtitle": "LLM 기반 자율 관제 시스템",
            "x": 0, "z": 3,
            "color": "#FFD600",
            "features": [
                "자연어 → 군집 명령 변환",
                "실시간 위협 감지/대응",
                "자가 복구(Self-Healing)",
                "관제사 1인 = 수십 대 통제",
            ],
            "value": "인력 비용 70% 절감",
        },
        {
            "title": "실전 배치\n(Real Deployment)",
            "subtitle": "Sim-to-Real 기술 전이",
            "x": 5, "z": 6,
            "color": "#2E7D32",
            "features": [
                "검증된 알고리즘 즉시 이식",
                "ROS2 + Pixhawk 연동",
                "WiFi Mesh 편대 통신",
                "단계적 스케일업 가능",
            ],
            "value": "개발 기간 75% 단축",
        },
    ]

    for blk in blocks:
        x, z = blk["x"], blk["z"]
        col = blk["color"]

        # 플랫폼 박스 (큰 투명 사각)
        w, h = 3.2, 2.0
        fig.add_trace(go.Mesh3d(
            x=[x - w/2, x + w/2, x + w/2, x - w/2],
            y=[-h/2, -h/2, h/2, h/2],
            z=[z] * 4,
            i=[0, 0], j=[1, 2], k=[2, 3],
            color=col, opacity=0.15,
            showlegend=False, hoverinfo="skip",
        ))

        # 테두리
        corners_x = [x - w/2, x + w/2, x + w/2, x - w/2, x - w/2]
        corners_y = [-h/2, -h/2, h/2, h/2, -h/2]
        fig.add_trace(go.Scatter3d(
            x=corners_x, y=corners_y, z=[z] * 5,
            mode="lines",
            line=dict(color=col, width=4),
            showlegend=False, hoverinfo="skip",
        ))

        # 제목
        fig.add_trace(go.Scatter3d(
            x=[x], y=[0], z=[z + 1.5],
            mode="text",
            text=[blk["title"]],
            textfont=dict(size=15, color=col, family="Arial Black"),
            showlegend=False,
        ))

        # 부제목
        fig.add_trace(go.Scatter3d(
            x=[x], y=[0], z=[z + 0.8],
            mode="text",
            text=[blk["subtitle"]],
            textfont=dict(size=11, color="#666"),
            showlegend=False,
        ))

        # 핵심 기능 리스트 (측면)
        for i, feat in enumerate(blk["features"]):
            fig.add_trace(go.Scatter3d(
                x=[x + w/2 + 0.5], y=[0], z=[z - 0.3 - i * 0.5],
                mode="text",
                text=[f"• {feat}"],
                textposition="middle right",
                textfont=dict(size=10, color="#555"),
                showlegend=False,
            ))

        # 비즈니스 가치 (강조)
        fig.add_trace(go.Scatter3d(
            x=[x], y=[0], z=[z - 1.8],
            mode="text",
            text=[f"💰 {blk['value']}"],
            textfont=dict(size=13, color="#C62828", family="Arial Black"),
            showlegend=False,
        ))

    # 블록 간 연결 화살표
    for x1, z1, x2, z2, label in [
        (-5, 0, 0, 3, "알고리즘 학습 완료"),
        (0, 3, 5, 6, "검증된 AI 이식"),
    ]:
        t = np.linspace(0, 1, 25)
        cx = x1 + (x2 - x1) * t
        cy = np.sin(t * math.pi) * 1.2
        cz = z1 + (z2 - z1) * t

        fig.add_trace(go.Scatter3d(
            x=cx, y=cy, z=cz,
            mode="lines",
            line=dict(color="#FF6F00", width=8),
            showlegend=False, hoverinfo="skip",
        ))

        fig.add_trace(go.Scatter3d(
            x=[(x1 + x2) / 2], y=[1.8], z=[(z1 + z2) / 2 + 0.5],
            mode="text",
            text=[label],
            textfont=dict(size=12, color="#FF6F00", family="Arial Black"),
            showlegend=False,
        ))

    fig.update_layout(
        title=dict(
            text="Swarm-Net 솔루션 아키텍처",
            font=dict(size=22, family="Arial Black"),
            x=0.5,
        ),
        scene=dict(
            xaxis=dict(visible=False, range=[-10, 12]),
            yaxis=dict(visible=False, range=[-4, 4]),
            zaxis=dict(visible=False, range=[-3, 9]),
            camera=dict(
                eye=dict(x=1.2, y=2.0, z=0.6),
                up=dict(x=0, y=0, z=1),
            ),
            bgcolor="white",
        ),
        paper_bgcolor="white",
        margin=dict(l=0, r=0, t=60, b=0),
        width=1200, height=800,
    )
    save(fig, "ir_2_virtual_testbed")


# ───────────────────────────────────────────────────────────────
# IR 3. ROI 분석 차트
# ───────────────────────────────────────────────────────────────

def ir_roi_analysis():
    """
    기존 방식 vs 우리 솔루션 비용/기간 비교 + 절감률
    깔끔한 2D 그룹 바 차트 (투자자가 보기 편하게)
    """
    print("[IR 3] ROI 분석 차트")

    from plotly.subplots import make_subplots

    fig = make_subplots(
        rows=1, cols=2,
        subplot_titles=(
            "단계별 비용 비교 (억원)",
            "단계별 소요 기간 비교 (개월)",
        ),
        horizontal_spacing=0.12,
    )

    categories = [
        "알고리즘\n검증",
        "충돌 회피\n테스트",
        "군집 비행\n훈련",
        "실전\n배치",
    ]

    # 비용 (억원)
    cost_traditional = [3, 5, 8, 15]
    cost_ours        = [0.1, 0.2, 0.5, 5]

    # 기간 (개월)
    time_traditional = [6, 8, 12, 18]
    time_ours        = [1, 2, 3, 6]

    # 비용 차트
    fig.add_trace(go.Bar(
        name="기존 방식",
        x=categories,
        y=cost_traditional,
        marker_color="#EF5350",
        text=[f"{v}억" for v in cost_traditional],
        textposition="outside",
        textfont=dict(size=12, family="Arial Black"),
    ), row=1, col=1)

    fig.add_trace(go.Bar(
        name="Swarm-Net",
        x=categories,
        y=cost_ours,
        marker_color="#42A5F5",
        text=[f"{v}억" for v in cost_ours],
        textposition="outside",
        textfont=dict(size=12, family="Arial Black"),
    ), row=1, col=1)

    # 기간 차트
    fig.add_trace(go.Bar(
        name="기존 방식",
        x=categories,
        y=time_traditional,
        marker_color="#EF5350",
        text=[f"{v}개월" for v in time_traditional],
        textposition="outside",
        textfont=dict(size=12, family="Arial Black"),
        showlegend=False,
    ), row=1, col=2)

    fig.add_trace(go.Bar(
        name="Swarm-Net",
        x=categories,
        y=time_ours,
        marker_color="#42A5F5",
        text=[f"{v}개월" for v in time_ours],
        textposition="outside",
        textfont=dict(size=12, family="Arial Black"),
        showlegend=False,
    ), row=1, col=2)

    # 절감률 표시 (annotation)
    cost_savings = [round((1 - c2/c1) * 100) for c1, c2
                    in zip(cost_traditional, cost_ours)]
    time_savings = [round((1 - t2/t1) * 100) for t1, t2
                    in zip(time_traditional, time_ours)]

    total_cost_trad = sum(cost_traditional)
    total_cost_ours = sum(cost_ours)
    total_cost_save = round((1 - total_cost_ours / total_cost_trad) * 100)

    total_time_trad = sum(time_traditional)
    total_time_ours = sum(time_ours)
    total_time_save = round((1 - total_time_ours / total_time_trad) * 100)

    fig.update_layout(
        title=dict(
            text="ROI 분석: 기존 방식 vs Swarm-Net 솔루션",
            font=dict(size=22, family="Arial Black"),
            x=0.5,
        ),
        barmode="group",
        paper_bgcolor="white",
        plot_bgcolor="rgba(245,245,245,0.5)",
        legend=dict(
            font=dict(size=14),
            x=0.5, y=-0.12,
            xanchor="center",
            orientation="h",
            bgcolor="rgba(255,255,255,0.9)",
        ),
        margin=dict(l=60, r=60, t=100, b=100),
        width=1200, height=650,
        annotations=[
            dict(
                text=f"총 비용 절감: {total_cost_save}%  |  "
                     f"총 기간 단축: {total_time_save}%",
                x=0.5, y=-0.2, xref="paper", yref="paper",
                showarrow=False,
                font=dict(size=16, color="#C62828", family="Arial Black"),
                bgcolor="rgba(255,235,238,0.8)",
                bordercolor="#EF5350",
                borderwidth=2,
                borderpad=8,
            ),
            dict(
                text=f"기존: {total_cost_trad}억원 → "
                     f"Swarm-Net: {total_cost_ours}억원",
                x=0.22, y=1.08, xref="paper", yref="paper",
                showarrow=False,
                font=dict(size=12, color="#1565C0"),
            ),
            dict(
                text=f"기존: {total_time_trad}개월 → "
                     f"Swarm-Net: {total_time_ours}개월",
                x=0.78, y=1.08, xref="paper", yref="paper",
                showarrow=False,
                font=dict(size=12, color="#1565C0"),
            ),
        ],
    )

    fig.update_yaxes(
        title_text="비용 (억원)", row=1, col=1,
        gridcolor="rgba(200,200,200,0.5)",
    )
    fig.update_yaxes(
        title_text="기간 (개월)", row=1, col=2,
        gridcolor="rgba(200,200,200,0.5)",
    )

    save(fig, "ir_3_roi_analysis")


# ───────────────────────────────────────────────────────────────
# IR 4. 비즈니스 모델 & 로드맵
# ───────────────────────────────────────────────────────────────

def ir_business_roadmap():
    """
    3단계 비즈니스 확장 타임라인
    Phase 1: B2B SaaS → Phase 2: 군 납품 → Phase 3: 글로벌 확장
    """
    print("[IR 4] 비즈니스 모델 & 로드맵")

    fig = go.Figure()

    phases = [
        {
            "title": "Phase 1\nB2B SaaS",
            "period": "2026~2027",
            "x": -6, "z": 0,
            "color": "#1976D2",
            "target": "방산 기업\n알고리즘 검증",
            "revenue": "월 구독 모델\n₩500만~₩2,000만/월",
            "product": "가상 테스트베드\nSaaS 플랫폼",
            "tam": "TAM: ₩500억",
        },
        {
            "title": "Phase 2\n군 납품",
            "period": "2027~2029",
            "x": 0, "z": 3,
            "color": "#FF6F00",
            "target": "국방부/ADD\n군 무인체계",
            "revenue": "라이선스 납품\n₩10억~₩50억/건",
            "product": "C2 지휘통제\n소프트웨어",
            "tam": "TAM: ₩5,000억",
        },
        {
            "title": "Phase 3\n글로벌 확장",
            "period": "2029~",
            "x": 6, "z": 6,
            "color": "#2E7D32",
            "target": "글로벌 UTM\n드론 관제",
            "revenue": "플랫폼 수수료\n+ API 과금",
            "product": "AI 드론 관제\n글로벌 플랫폼",
            "tam": "TAM: ₩10조+",
        },
    ]

    for ph in phases:
        x, z = ph["x"], ph["z"]
        col = ph["color"]

        # 메인 플랫폼
        w, h = 3.5, 2.5
        fig.add_trace(go.Mesh3d(
            x=[x - w/2, x + w/2, x + w/2, x - w/2],
            y=[-h/2, -h/2, h/2, h/2],
            z=[z] * 4,
            i=[0, 0], j=[1, 2], k=[2, 3],
            color=col, opacity=0.12,
            showlegend=False, hoverinfo="skip",
        ))

        # 테두리
        bx = [x - w/2, x + w/2, x + w/2, x - w/2, x - w/2]
        by = [-h/2, -h/2, h/2, h/2, -h/2]
        fig.add_trace(go.Scatter3d(
            x=bx, y=by, z=[z] * 5,
            mode="lines",
            line=dict(color=col, width=4),
            showlegend=False, hoverinfo="skip",
        ))

        # Phase 제목 (크게)
        fig.add_trace(go.Scatter3d(
            x=[x], y=[0], z=[z + 2.0],
            mode="text",
            text=[ph["title"]],
            textfont=dict(size=16, color=col, family="Arial Black"),
            showlegend=False,
        ))

        # 기간
        fig.add_trace(go.Scatter3d(
            x=[x], y=[0], z=[z + 1.2],
            mode="text",
            text=[ph["period"]],
            textfont=dict(size=12, color="#888"),
            showlegend=False,
        ))

        # 상세 정보 (카드 내부)
        details = [
            (f"🎯 {ph['target']}", 0.3),
            (f"📦 {ph['product']}", -0.5),
            (f"💰 {ph['revenue']}", -1.3),
        ]
        for detail_text, y_off in details:
            fig.add_trace(go.Scatter3d(
                x=[x], y=[0], z=[z + y_off],
                mode="text",
                text=[detail_text],
                textfont=dict(size=10, color="#444"),
                showlegend=False,
            ))

        # TAM (시장 규모)
        fig.add_trace(go.Scatter3d(
            x=[x], y=[0], z=[z - 2.0],
            mode="text",
            text=[ph["tam"]],
            textfont=dict(size=12, color=col, family="Arial Black"),
            showlegend=False,
        ))

    # Phase 간 화살표
    for x1, z1, x2, z2 in [(-6, 0, 0, 3), (0, 3, 6, 6)]:
        t = np.linspace(0, 1, 25)
        cx = x1 + (x2 - x1) * t
        cy = np.sin(t * math.pi) * 1.5
        cz = z1 + (z2 - z1) * t

        fig.add_trace(go.Scatter3d(
            x=cx, y=cy, z=cz,
            mode="lines",
            line=dict(color="#FF6F00", width=8),
            showlegend=False, hoverinfo="skip",
        ))

    # 화살표 위 라벨
    fig.add_trace(go.Scatter3d(
        x=[-3], y=[2.0], z=[2],
        mode="text",
        text=["기술 검증 완료\n→ 군 시장 진출"],
        textfont=dict(size=11, color="#FF6F00", family="Arial Black"),
        showlegend=False,
    ))
    fig.add_trace(go.Scatter3d(
        x=[3], y=[2.0], z=[5],
        mode="text",
        text=["실전 실적 기반\n→ 글로벌 확장"],
        textfont=dict(size=11, color="#FF6F00", family="Arial Black"),
        showlegend=False,
    ))

    # 성장 방향 표시
    fig.add_trace(go.Scatter3d(
        x=[-8, 8], y=[0, 0], z=[-1, 7],
        mode="lines",
        line=dict(color="#ccc", width=2, dash="dot"),
        showlegend=False, hoverinfo="skip",
    ))
    fig.add_trace(go.Scatter3d(
        x=[8.5], y=[0], z=[7.5],
        mode="text",
        text=["성장 →"],
        textfont=dict(size=13, color="#999"),
        showlegend=False,
    ))

    fig.update_layout(
        title=dict(
            text="Swarm-Net 비즈니스 로드맵",
            font=dict(size=22, family="Arial Black"),
            x=0.5,
        ),
        scene=dict(
            xaxis=dict(visible=False, range=[-10, 12]),
            yaxis=dict(visible=False, range=[-4, 4]),
            zaxis=dict(visible=False, range=[-3, 10]),
            camera=dict(
                eye=dict(x=1.0, y=2.2, z=0.6),
                up=dict(x=0, y=0, z=1),
            ),
            bgcolor="white",
        ),
        paper_bgcolor="white",
        margin=dict(l=0, r=0, t=60, b=0),
        width=1200, height=800,
    )
    save(fig, "ir_4_business_roadmap")


# ═══════════════════════════════════════════════════════════════
#  캡스톤 보고서 섹션별 시각화 (정밀 데이터 기반)
# ═══════════════════════════════════════════════════════════════


# ───────────────────────────────────────────────────────────────
# 섹션 2-1. 드론 등록 수 폭발적 증가 추이
# ───────────────────────────────────────────────────────────────

def section2_drone_growth():
    """드론 등록 수 증가 추이 + 성장률 이중축 차트"""
    print("[섹션2-1] 드론 등록 수 폭발적 증가 추이")

    from plotly.subplots import make_subplots

    fig = make_subplots(specs=[[{"secondary_y": True}]])

    years = [2019, 2020, 2021, 2022, 2023, 2024, 2025, 2026, 2027, 2028, 2030]
    labels = ["2019", "2020", "2021", "2022", "2023", "2024",
              "2025e", "2026e", "2027e", "2028e", "2030e"]

    consumer   = [9, 12, 17, 22, 28, 36, 43, 50, 58, 65, 80]
    commercial = [4.5, 6, 10, 14, 20, 36, 50, 70, 95, 125, 250]
    military   = [1.5, 2, 3, 4, 7, 18, 27, 40, 57, 80, 170]
    total = [c + m + d for c, m, d in zip(consumer, commercial, military)]
    growth = [0] + [round((total[i] - total[i-1]) / total[i-1] * 100)
                    for i in range(1, len(total))]

    fig.add_trace(go.Bar(
        x=labels, y=consumer, name="소비자 (Consumer)",
        marker_color="#42A5F5", opacity=0.85,
    ), secondary_y=False)
    fig.add_trace(go.Bar(
        x=labels, y=commercial, name="상업 (Commercial)",
        marker_color="#66BB6A", opacity=0.85,
    ), secondary_y=False)
    fig.add_trace(go.Bar(
        x=labels, y=military, name="군사/공공 (Defense)",
        marker_color="#EF5350", opacity=0.85,
    ), secondary_y=False)

    fig.add_trace(go.Scatter(
        x=labels, y=growth, name="전년 대비 성장률 (%)",
        line=dict(color="#FF6F00", width=3, dash="dot"),
        marker=dict(size=8, color="#FF6F00"),
        mode="lines+markers+text",
        text=[f"{g}%" if g > 0 else "" for g in growth],
        textposition="top center",
        textfont=dict(size=10, color="#FF6F00", family="Arial Black"),
    ), secondary_y=True)

    fig.update_layout(
        title=dict(
            text="국내 드론 등록 수 추이 및 성장률 전망",
            font=dict(size=22, family="Arial Black"), x=0.5,
        ),
        barmode="stack",
        paper_bgcolor="white",
        plot_bgcolor="rgba(245,245,245,0.5)",
        legend=dict(font=dict(size=12), x=0.01, y=0.99,
                    bgcolor="rgba(255,255,255,0.9)"),
        margin=dict(l=60, r=60, t=90, b=80),
        width=1200, height=700,
        annotations=[
            dict(text="2023.9 FAA Remote ID 의무화",
                 x="2023", y=55, xref="x", yref="y",
                 showarrow=True, arrowhead=2, ax=60, ay=-40,
                 font=dict(size=11, color="#C62828"),
                 bgcolor="rgba(255,235,238,0.9)", borderpad=4),
            dict(text="UAM 본격 상용화 예상",
                 x="2028e", y=270, xref="x", yref="y",
                 showarrow=True, arrowhead=2, ax=-50, ay=-30,
                 font=dict(size=11, color="#1565C0"),
                 bgcolor="rgba(227,242,253,0.9)", borderpad=4),
            dict(text="현재: 90만 대 돌파 (2024)",
                 x="2024", y=90, xref="x", yref="y",
                 showarrow=True, arrowhead=2, ax=0, ay=-50,
                 font=dict(size=12, color="#333", family="Arial Black"),
                 bgcolor="rgba(255,255,200,0.9)", borderpad=4),
        ],
    )
    fig.update_yaxes(title_text="드론 등록 수 (만 대)", secondary_y=False,
                     gridcolor="rgba(200,200,200,0.5)")
    fig.update_yaxes(title_text="성장률 (%)", secondary_y=True,
                     showgrid=False, range=[0, 100])

    save(fig, "section2_drone_growth")


# ───────────────────────────────────────────────────────────────
# 섹션 2-2. 문제 심각도 히트맵
# ───────────────────────────────────────────────────────────────

def section2_problem_heatmap():
    """4대 문제 × 4대 환경 심각도 히트맵"""
    print("[섹션2-2] 문제 심각도 히트맵")

    problems = [
        "수동 운용\n(인적 오류)",
        "소형 드론\n탐지 한계",
        "신속 전개\n불가",
        "탐지\n사각지대",
    ]
    environments = ["도심 지역", "산간 지역", "해안 지역", "군사 지역"]

    severity = [
        [7, 5, 4, 8],   # 수동 운용
        [9, 6, 7, 10],  # 소형 드론 탐지
        [8, 9, 7, 10],  # 신속 전개
        [10, 9, 6, 8],  # 탐지 사각지대
    ]

    annotations_text = [
        ["관제관 부족", "접근 곤란", "해상 관할", "24시간 감시"],
        ["RCS<2dBsm", "위장 용이", "해무 간섭", "적국 소형 UAV"],
        ["인프라 부재", "도로 미비", "부두 한정", "긴급 전개 필수"],
        ["67% 미감시", "전파 음영", "원거리 한계", "GPS 재밍"],
    ]

    fig = go.Figure(data=go.Heatmap(
        z=severity,
        x=environments,
        y=problems,
        colorscale=[
            [0, "#E8F5E9"],
            [0.3, "#FFF9C4"],
            [0.5, "#FFE0B2"],
            [0.7, "#FFAB91"],
            [1.0, "#E53935"],
        ],
        zmin=0, zmax=10,
        text=[[f"{severity[i][j]}\n{annotations_text[i][j]}"
               for j in range(4)] for i in range(4)],
        texttemplate="%{text}",
        textfont=dict(size=12, family="Arial Black"),
        hovertemplate="문제: %{y}<br>환경: %{x}<br>심각도: %{z}/10<extra></extra>",
        colorbar=dict(title="심각도", tickvals=[0, 2, 4, 6, 8, 10],
                      ticktext=["낮음", "2", "4", "6", "8", "심각"]),
    ))

    fig.update_layout(
        title=dict(
            text="공역 통제 문제 심각도 매트릭스 (환경별 × 문제별)",
            font=dict(size=22, family="Arial Black"), x=0.5,
        ),
        xaxis=dict(title="운용 환경", tickfont=dict(size=13, family="Arial Black")),
        yaxis=dict(title="핵심 문제", tickfont=dict(size=12, family="Arial Black")),
        paper_bgcolor="white",
        margin=dict(l=120, r=40, t=80, b=60),
        width=1000, height=600,
        annotations=[
            dict(text="평균 심각도: 7.6/10 — 전 환경에서 자동화 관제 시급",
                 x=0.5, y=-0.15, xref="paper", yref="paper",
                 showarrow=False,
                 font=dict(size=14, color="#C62828", family="Arial Black")),
        ],
    )
    save(fig, "section2_problem_heatmap")


# ───────────────────────────────────────────────────────────────
# 섹션 2-3. 비행 승인 절차 Before/After 비교
# ───────────────────────────────────────────────────────────────

def section2_approval_flow():
    """현행 수동 프로세스 vs Swarm-Net 자동화 비교 타임라인"""
    print("[섹션2-3] 비행 승인 절차 Before/After")

    fig = go.Figure()

    # 현행 프로세스 (상단)
    current_steps = [
        ("비행 신청\n서류 작성", 15, "#EF5350"),
        ("관할 기관\n심사", 60, "#EF5350"),
        ("공역\n확인", 30, "#FF9800"),
        ("승인/거부\n통보", 7, "#FF9800"),
        ("비행 감시\n(수동)", 1, "#FFC107"),
        ("위반 시\n수동 대응", 1, "#F44336"),
    ]

    # Swarm-Net 자동화 (하단)
    auto_steps = [
        ("드론 출격\n돔 형성", 0.02, "#4CAF50"),
        ("자동 탐지\n+ 식별", 0.0007, "#2196F3"),
        ("시간 할당\n+ 추적", 0.0007, "#1976D2"),
        ("자동 경고\n+ 퇴각", 0.0007, "#7B1FA2"),
    ]

    # 현행 프로세스 바
    x_pos = 0
    for i, (label, days, color) in enumerate(current_steps):
        width = max(days * 0.8, 3)
        fig.add_trace(go.Bar(
            x=[width], y=["현행 수동 프로세스"],
            orientation="h", base=x_pos,
            marker_color=color, opacity=0.8,
            text=[label], textposition="inside",
            textfont=dict(size=10, color="white", family="Arial Black"),
            hovertext=f"{label}: {days}일",
            showlegend=False,
        ))
        x_pos += width

    # Swarm-Net 바
    x_pos_auto = 0
    for i, (label, days, color) in enumerate(auto_steps):
        width = max(20, 20)
        fig.add_trace(go.Bar(
            x=[width], y=["Swarm-Net 자동화"],
            orientation="h", base=x_pos_auto,
            marker_color=color, opacity=0.8,
            text=[label], textposition="inside",
            textfont=dict(size=10, color="white", family="Arial Black"),
            showlegend=False,
        ))
        x_pos_auto += width

    fig.update_layout(
        title=dict(
            text="비행 승인·관제 절차 비교: 현행 vs Swarm-Net",
            font=dict(size=22, family="Arial Black"), x=0.5,
        ),
        barmode="stack",
        xaxis=dict(title="소요 시간 (상대 스케일)",
                   showticklabels=False,
                   gridcolor="rgba(200,200,200,0.3)"),
        yaxis=dict(tickfont=dict(size=14, family="Arial Black")),
        paper_bgcolor="white",
        plot_bgcolor="rgba(250,250,250,0.5)",
        margin=dict(l=180, r=40, t=90, b=80),
        width=1200, height=400,
        annotations=[
            dict(text="총 소요: 2~6개월 (최대 114일+)",
                 x=0.85, y=1, xref="paper", yref="y domain",
                 showarrow=False,
                 font=dict(size=13, color="#C62828", family="Arial Black"),
                 bgcolor="rgba(255,235,238,0.9)", borderpad=6),
            dict(text="총 소요: 30분 + 실시간 (<1초 레이턴시)",
                 x=0.85, y=0, xref="paper", yref="y domain",
                 showarrow=False,
                 font=dict(size=13, color="#2E7D32", family="Arial Black"),
                 bgcolor="rgba(232,245,233,0.9)", borderpad=6),
            dict(text="시간 절감: 99.98%+",
                 x=0.5, y=-0.25, xref="paper", yref="paper",
                 showarrow=False,
                 font=dict(size=16, color="#1565C0", family="Arial Black")),
        ],
    )
    save(fig, "section2_approval_flow")


# ───────────────────────────────────────────────────────────────
# 섹션 3-1. KPI 대시보드
# ───────────────────────────────────────────────────────────────

def section3_kpi_dashboard():
    """4개 핵심 성과 지표 게이지 대시보드"""
    print("[섹션3-1] KPI 대시보드")

    from plotly.subplots import make_subplots

    fig = make_subplots(
        rows=2, cols=2,
        specs=[
            [{"type": "indicator"}, {"type": "indicator"}],
            [{"type": "indicator"}, {"type": "indicator"}],
        ],
        subplot_titles=[
            "관제 인력 절감률", "탐지 레이턴시",
            "배치 소요 시간", "확장 비용 효율",
        ],
    )

    # KPI 1: 관제 인력 절감
    fig.add_trace(go.Indicator(
        mode="gauge+number+delta",
        value=80,
        number=dict(suffix="%", font=dict(size=36)),
        delta=dict(reference=0, suffix="%", increasing=dict(color="#2E7D32")),
        gauge=dict(
            axis=dict(range=[0, 100], ticksuffix="%"),
            bar=dict(color="#4CAF50"),
            bgcolor="white",
            steps=[
                dict(range=[0, 50], color="#FFCDD2"),
                dict(range=[50, 75], color="#FFF9C4"),
                dict(range=[75, 100], color="#C8E6C9"),
            ],
            threshold=dict(line=dict(color="#C62828", width=4),
                           thickness=0.8, value=80),
        ),
        title=dict(text="목표: 80%<br>현행: 1관제사=1드론",
                   font=dict(size=12)),
    ), row=1, col=1)

    # KPI 2: 탐지 레이턴시
    fig.add_trace(go.Indicator(
        mode="gauge+number",
        value=0.8,
        number=dict(suffix="초", font=dict(size=36)),
        gauge=dict(
            axis=dict(range=[0, 15], ticksuffix="s"),
            bar=dict(color="#2196F3"),
            bgcolor="white",
            steps=[
                dict(range=[0, 1], color="#C8E6C9"),
                dict(range=[1, 5], color="#FFF9C4"),
                dict(range=[5, 15], color="#FFCDD2"),
            ],
            threshold=dict(line=dict(color="#C62828", width=4),
                           thickness=0.8, value=1.0),
        ),
        title=dict(text="목표: <1초<br>현행: ~15초 (수동)",
                   font=dict(size=12)),
    ), row=1, col=2)

    # KPI 3: 배치 시간
    fig.add_trace(go.Indicator(
        mode="gauge+number",
        value=30,
        number=dict(suffix="분", font=dict(size=36)),
        gauge=dict(
            axis=dict(range=[0, 360], ticksuffix="분",
                      tickvals=[0, 30, 60, 120, 180, 360]),
            bar=dict(color="#FF6F00"),
            bgcolor="white",
            steps=[
                dict(range=[0, 30], color="#C8E6C9"),
                dict(range=[30, 120], color="#FFF9C4"),
                dict(range=[120, 360], color="#FFCDD2"),
            ],
            threshold=dict(line=dict(color="#C62828", width=4),
                           thickness=0.8, value=30),
        ),
        title=dict(text="목표: 30분 이내<br>현행: 수개월 (인프라 설치)",
                   font=dict(size=12)),
    ), row=2, col=1)

    # KPI 4: 확장 비용 효율 (선형 계수)
    fig.add_trace(go.Indicator(
        mode="gauge+number",
        value=1.0,
        number=dict(suffix="x", font=dict(size=36)),
        gauge=dict(
            axis=dict(range=[0, 5], ticksuffix="x"),
            bar=dict(color="#7B1FA2"),
            bgcolor="white",
            steps=[
                dict(range=[0, 1.5], color="#C8E6C9"),
                dict(range=[1.5, 3], color="#FFF9C4"),
                dict(range=[3, 5], color="#FFCDD2"),
            ],
            threshold=dict(line=dict(color="#C62828", width=4),
                           thickness=0.8, value=1.0),
        ),
        title=dict(text="목표: 1.0x (선형)<br>현행: 3~5x (기하급수적)",
                   font=dict(size=12)),
    ), row=2, col=2)

    fig.update_layout(
        title=dict(
            text="핵심 성과 지표 (KPI) 대시보드",
            font=dict(size=22, family="Arial Black"), x=0.5,
        ),
        paper_bgcolor="white",
        margin=dict(l=30, r=30, t=100, b=30),
        width=1100, height=750,
    )
    save(fig, "section3_kpi_dashboard")


# ───────────────────────────────────────────────────────────────
# 섹션 3-2. 구현 일정 간트 차트
# ───────────────────────────────────────────────────────────────

def section3_gantt_timeline():
    """Phase 1~3 구현 일정 + 산출물 마일스톤"""
    print("[섹션3-2] 구현 일정 간트 차트")

    import plotly.figure_factory as ff

    tasks = [
        # Phase 1: 스케치
        dict(Task="개념 정의 + SRS",        Start="2026-03-01", Finish="2026-03-21",
             Resource="Phase 1"),
        dict(Task="유사 시스템 조사",        Start="2026-03-01", Finish="2026-03-14",
             Resource="Phase 1"),
        dict(Task="SC2 프로토타이핑",        Start="2026-03-10", Finish="2026-04-11",
             Resource="Phase 1"),
        dict(Task="기술 스택 선정",          Start="2026-03-15", Finish="2026-04-04",
             Resource="Phase 1"),
        # Phase 2: 개념 설계
        dict(Task="시스템 아키텍처 설계",    Start="2026-04-12", Finish="2026-05-02",
             Resource="Phase 2"),
        dict(Task="Gazebo SITL 환경 구축",   Start="2026-04-12", Finish="2026-05-16",
             Resource="Phase 2"),
        dict(Task="Boids 알고리즘 검증",     Start="2026-04-19", Finish="2026-05-30",
             Resource="Phase 2"),
        dict(Task="대시보드 UI/UX 설계",     Start="2026-05-01", Finish="2026-05-23",
             Resource="Phase 2"),
        # Phase 3: 작품 개발
        dict(Task="3D Boids + Authority FSM", Start="2026-06-01", Finish="2026-06-28",
             Resource="Phase 3"),
        dict(Task="LLM(JARVIS) 지휘 시스템", Start="2026-06-08", Finish="2026-07-05",
             Resource="Phase 3"),
        dict(Task="Redis 타이머 + FastAPI",  Start="2026-06-08", Finish="2026-06-28",
             Resource="Phase 3"),
        dict(Task="관제 대시보드 개발",      Start="2026-06-22", Finish="2026-07-12",
             Resource="Phase 3"),
        dict(Task="통합 테스트 + 데모 준비", Start="2026-07-06", Finish="2026-07-26",
             Resource="Phase 3"),
    ]

    colors = {
        "Phase 1": "#42A5F5",
        "Phase 2": "#7B1FA2",
        "Phase 3": "#FF6F00",
    }

    fig = ff.create_gantt(
        tasks,
        colors=colors,
        index_col="Resource",
        show_colorbar=True,
        group_tasks=True,
        showgrid_x=True,
        showgrid_y=True,
        title="프로젝트 구현 일정 (간트 차트)",
    )

    # 마일스톤 추가
    milestones = [
        ("2026-04-11", "설계서 완성", "#42A5F5"),
        ("2026-05-30", "시뮬 환경 + 알고리즘 검증", "#7B1FA2"),
        ("2026-07-26", "최종 데모", "#FF6F00"),
    ]
    for date, label, color in milestones:
        fig.add_trace(go.Scatter(
            x=[date], y=[0],
            mode="markers+text",
            marker=dict(size=14, color=color, symbol="diamond"),
            text=[f"  {label}"],
            textposition="top right",
            textfont=dict(size=10, color=color, family="Arial Black"),
            showlegend=False,
        ))

    fig.update_layout(
        title=dict(
            text="프로젝트 구현 일정 (3단계 간트 차트)",
            font=dict(size=22, family="Arial Black"), x=0.5,
        ),
        paper_bgcolor="white",
        plot_bgcolor="rgba(250,250,250,0.5)",
        margin=dict(l=200, r=40, t=80, b=60),
        width=1200, height=600,
        xaxis=dict(title="일정", tickfont=dict(size=11)),
        yaxis=dict(tickfont=dict(size=11)),
    )
    save(fig, "section3_gantt_timeline")


# ───────────────────────────────────────────────────────────────
# 섹션 3-3. End-to-End 자동화 관제 파이프라인
# ───────────────────────────────────────────────────────────────

def section3_e2e_pipeline():
    """탐지 → 식별 → 시간 할당 → 경고 → 퇴각 유도 5단계 자동화 파이프라인"""
    print("[섹션3-3] End-to-End 자동화 관제 파이프라인")

    fig = go.Figure()

    stages = [
        {"name": "1. 탐지\n(Detection)", "tech": "RF + RemoteID\n+ YOLO",
         "latency": "<0.5초", "color": "#1976D2"},
        {"name": "2. 식별\n(Identification)", "tech": "MAC/RF 매칭\n+ DB 조회",
         "latency": "<0.3초", "color": "#42A5F5"},
        {"name": "3. 시간 할당\n(Timer)", "tech": "Redis TTL\n+ Keyspace Event",
         "latency": "즉시", "color": "#FFC107"},
        {"name": "4. 경고\n(Alert)", "tech": "FCM Push\n+ MQTT",
         "latency": "잔여 2분", "color": "#FF9800"},
        {"name": "5. 퇴각 유도\n(Eviction)", "tech": "자동 명령\n+ 인터셉트",
         "latency": "만료 즉시", "color": "#F44336"},
    ]

    bar_width = 18
    for i, stage in enumerate(stages):
        base = i * (bar_width + 2)

        # 메인 파이프라인 바 (상단)
        fig.add_trace(go.Bar(
            x=[bar_width], y=["자동화 파이프라인"],
            orientation="h", base=base,
            marker_color=stage["color"], opacity=0.85,
            text=[stage["name"]], textposition="inside",
            textfont=dict(size=11, color="white", family="Arial Black"),
            showlegend=False,
        ))

        # 기술 스택 바 (하단)
        fig.add_trace(go.Bar(
            x=[bar_width], y=["기술 스택"],
            orientation="h", base=base,
            marker_color=stage["color"], opacity=0.4,
            text=[stage["tech"]], textposition="inside",
            textfont=dict(size=10, color="#333", family="Arial"),
            showlegend=False,
        ))

        # 레이턴시 주석 (상단에 표시)
        fig.add_annotation(
            x=base + bar_width / 2, y="자동화 파이프라인",
            text=stage["latency"],
            showarrow=False, yshift=25,
            font=dict(size=11, color=stage["color"], family="Arial Black"),
            bgcolor="rgba(255,255,255,0.8)", borderpad=3,
        )

    # 화살표 (각 단계 사이)
    for i in range(4):
        x_start = (i + 1) * (bar_width + 2) - 2
        fig.add_annotation(
            x=x_start, y="자동화 파이프라인",
            ax=x_start - (bar_width - 14), ay=0,
            xref="x", yref="y", axref="x", ayref="y",
            showarrow=True, arrowhead=3, arrowsize=1.5,
            arrowwidth=2, arrowcolor="#555",
        )

    # Redis TTL 라이프사이클 (하단 주석)
    fig.add_annotation(
        x=50, y="기술 스택",
        text="Redis TTL: 15/30/60분 카운트다운 → Keyspace Notification → 자동 만료 이벤트",
        showarrow=False, yshift=-35,
        font=dict(size=12, color="#7B1FA2", family="Arial Black"),
        bgcolor="rgba(243,229,245,0.9)", borderpad=6,
    )

    fig.update_layout(
        title=dict(
            text="End-to-End 자동화 관제 파이프라인",
            font=dict(size=22, family="Arial Black"), x=0.5,
        ),
        barmode="stack",
        xaxis=dict(showticklabels=False, showgrid=False, zeroline=False),
        yaxis=dict(tickfont=dict(size=13, family="Arial Black")),
        paper_bgcolor="white",
        plot_bgcolor="rgba(250,250,250,0.5)",
        margin=dict(l=160, r=40, t=90, b=100),
        width=1200, height=420,
        annotations=[
            dict(text="Total E2E Latency: < 1초  |  전 과정 완전 자동화",
                 x=0.5, y=-0.28, xref="paper", yref="paper",
                 showarrow=False,
                 font=dict(size=16, color="#1565C0", family="Arial Black"),
                 bgcolor="rgba(227,242,253,0.9)", borderpad=8),
        ],
    )
    save(fig, "section3_e2e_pipeline")


# ───────────────────────────────────────────────────────────────
# 섹션 3-4. 3중 센서 퓨전 파이프라인
# ───────────────────────────────────────────────────────────────

def section3_sensor_fusion():
    """RF + Remote ID + Vision AI → Kalman Filter → 통합 탐지 Sankey 다이어그램"""
    print("[섹션3-4] 3중 센서 퓨전 파이프라인")

    fig = go.Figure(data=[go.Sankey(
        arrangement="snap",
        node=dict(
            pad=20,
            thickness=25,
            line=dict(color="white", width=1),
            label=[
                # Layer 0: 센서 입력 (0-2)
                "RF 스캐너\n(2.4/5.8GHz SDR)",
                "Remote ID 수신\n(BLE/WiFi Beacon)",
                "비전 AI\n(YOLO v8 + Jetson)",
                # Layer 1: 처리 (3-5)
                "RF 신호\n패턴 분석",
                "OpenDroneID\n프로토콜 파싱",
                "객체 탐지\n+ 분류 (실시간)",
                # Layer 2: 퓨전 (6)
                "멀티센서 퓨전\n(Extended Kalman Filter)",
                # Layer 3: 출력 (7-9)
                "3D 위치 추적\n(삼각측량)",
                "관제 DB 등록\n(PostgreSQL)",
                "실시간 스트림\n(WebSocket 1Hz)",
            ],
            color=[
                # 센서
                "#1976D2", "#4CAF50", "#FF9800",
                # 처리
                "#42A5F5", "#66BB6A", "#FFB74D",
                # 퓨전
                "#7B1FA2",
                # 출력
                "#0D47A1", "#1565C0", "#1976D2",
            ],
        ),
        link=dict(
            source=[0, 1, 2, 3, 4, 5, 6, 6, 6],
            target=[3, 4, 5, 6, 6, 6, 7, 8, 9],
            value= [8, 6, 5, 8, 6, 5, 10, 7, 7],
            color=[
                "rgba(25,118,210,0.3)",   # RF → 패턴분석
                "rgba(76,175,80,0.3)",    # RID → 프로토콜파싱
                "rgba(255,152,0,0.3)",    # YOLO → 객체탐지
                "rgba(25,118,210,0.3)",   # 패턴분석 → 퓨전
                "rgba(76,175,80,0.3)",    # 프로토콜파싱 → 퓨전
                "rgba(255,152,0,0.3)",    # 객체탐지 → 퓨전
                "rgba(123,31,162,0.3)",   # 퓨전 → 3D위치
                "rgba(123,31,162,0.3)",   # 퓨전 → 관제DB
                "rgba(123,31,162,0.3)",   # 퓨전 → 실시간
            ],
        ),
    )])

    fig.update_layout(
        title=dict(
            text="3중 센서 퓨전 파이프라인 (RF + Remote ID + Vision AI)",
            font=dict(size=22, family="Arial Black"), x=0.5,
        ),
        paper_bgcolor="white",
        margin=dict(l=20, r=20, t=80, b=100),
        width=1200, height=600,
        font=dict(size=12, family="Arial"),
        annotations=[
            dict(text="탐지 범위 — RF: 500m~5km | Remote ID: 300m~1km | Vision: 50~300m",
                 x=0.5, y=-0.12, xref="paper", yref="paper",
                 showarrow=False,
                 font=dict(size=13, color="#555", family="Arial Black")),
            dict(text="협조 드론: 3중 센서 교차 검증  |  비협조 드론: RF + Vision 2중 탐지",
                 x=0.5, y=-0.18, xref="paper", yref="paper",
                 showarrow=False,
                 font=dict(size=13, color="#C62828", family="Arial Black"),
                 bgcolor="rgba(255,235,238,0.9)", borderpad=5),
        ],
    )
    save(fig, "section3_sensor_fusion")


# ───────────────────────────────────────────────────────────────
# 섹션 3-5. 4계층 시스템 아키텍처
# ───────────────────────────────────────────────────────────────

def section3_4layer_architecture():
    """공중-지상-백엔드-사용자 4계층 시스템 3D 아키텍처"""
    print("[섹션3-5] 4계층 시스템 아키텍처")

    fig = go.Figure()

    layers = [
        {
            "name": "Layer 4: 사용자 계층 (User Interface)",
            "z": 9, "color": "#FF6F00", "bg": "#FFF3E0",
            "nodes": [
                {"label": "관제 대시보드\n(React + Mapbox 3D)", "x": -3},
                {"label": "모바일 앱\n(Flutter + FCM Push)", "x": 3},
            ],
        },
        {
            "name": "Layer 3: 백엔드 계층 (Backend Server)",
            "z": 6, "color": "#7B1FA2", "bg": "#F3E5F5",
            "nodes": [
                {"label": "FastAPI\n(REST + WebSocket)", "x": -4},
                {"label": "Redis\n(TTL Timer +\nKeyspace)", "x": 0},
                {"label": "PostgreSQL\n(TimescaleDB)", "x": 4},
            ],
        },
        {
            "name": "Layer 2: 지상 관제 (Ground Control)",
            "z": 3, "color": "#1976D2", "bg": "#E3F2FD",
            "nodes": [
                {"label": "ROS2 Humble\n(uXRCE-DDS)", "x": -3},
                {"label": "MAVSDK\n(MAVLink 2.0)", "x": 0},
                {"label": "MQTT Broker\n(Mosquitto)", "x": 3},
            ],
        },
        {
            "name": "Layer 1: 공중 계층 (Airborne Swarm)",
            "z": 0, "color": "#2E7D32", "bg": "#E8F5E9",
            "nodes": [
                {"label": "Boids 군집\n(Sentinel Drone)", "x": -5},
                {"label": "3중 센서\n(RF+RID+YOLO)", "x": -1.5},
                {"label": "Authority Mode\n(FSM 5단계)", "x": 1.5},
                {"label": "802.11s Mesh\n+ LoRa 백업", "x": 5},
            ],
        },
    ]

    # 계층 배경 플랫폼
    for layer in layers:
        z = layer["z"] - 0.5
        w = 7 if len(layer["nodes"]) <= 3 else 8
        h = 1.5
        fig.add_trace(go.Mesh3d(
            x=[-w, w, w, -w], y=[-h, -h, h, h], z=[z] * 4,
            i=[0, 0], j=[1, 2], k=[2, 3],
            color=layer["bg"], opacity=0.3,
            showlegend=False, hoverinfo="skip",
        ))

    # 노드 렌더링
    for layer in layers:
        for node in layer["nodes"]:
            fig.add_trace(go.Scatter3d(
                x=[node["x"]], y=[0], z=[layer["z"]],
                mode="markers+text",
                marker=dict(
                    size=16, color=layer["color"],
                    opacity=0.9, line=dict(width=2, color="white"),
                    symbol="circle",
                ),
                text=[node["label"]],
                textposition="top center",
                textfont=dict(size=10, color=layer["color"],
                              family="Arial Black"),
                showlegend=False,
            ))

    # 계층 간 연결 곡선
    connections = [
        # 공중 → 지상
        (-5, 0, -3, 3, "#2E7D32"),
        (-1.5, 0, 0, 3, "#2E7D32"),
        (1.5, 0, 0, 3, "#2E7D32"),
        (5, 0, 3, 3, "#2E7D32"),
        # 지상 → 백엔드
        (-3, 3, -4, 6, "#1976D2"),
        (0, 3, 0, 6, "#1976D2"),
        (3, 3, 4, 6, "#1976D2"),
        # 백엔드 → 사용자
        (-4, 6, -3, 9, "#7B1FA2"),
        (0, 6, -3, 9, "#7B1FA2"),
        (4, 6, 3, 9, "#7B1FA2"),
    ]

    for x1, z1, x2, z2, col in connections:
        t = np.linspace(0, 1, 20)
        cx = x1 + (x2 - x1) * t
        cy = np.sin(t * math.pi) * 0.8
        cz = z1 + (z2 - z1) * t
        fig.add_trace(go.Scatter3d(
            x=cx, y=cy, z=cz,
            mode="lines",
            line=dict(color=col, width=3),
            opacity=0.4, showlegend=False, hoverinfo="skip",
        ))

    # 계층 라벨 (좌측)
    for layer in layers:
        fig.add_trace(go.Scatter3d(
            x=[-10], y=[0], z=[layer["z"] + 0.5],
            mode="text",
            text=[layer["name"]],
            textfont=dict(size=11, color=layer["color"], family="Arial Black"),
            showlegend=False,
        ))

    # 계층 간 프로토콜 라벨
    proto_labels = [
        (7, 1.5, "802.11s WiFi Mesh\n+ LoRa 이중화", "#2E7D32"),
        (7, 4.5, "MQTT + MAVLink\n+ REST API", "#1976D2"),
        (7, 7.5, "WebSocket + FCM\n+ gRPC", "#7B1FA2"),
    ]
    for x, z, label, col in proto_labels:
        fig.add_trace(go.Scatter3d(
            x=[x], y=[0], z=[z],
            mode="text",
            text=[label],
            textfont=dict(size=10, color=col),
            showlegend=False,
        ))

    fig.update_layout(
        title=dict(
            text="Swarm-Net 4계층 시스템 아키텍처",
            font=dict(size=22, family="Arial Black"), x=0.5,
        ),
        scene=dict(
            xaxis=dict(visible=False, range=[-12, 10]),
            yaxis=dict(visible=False, range=[-3, 4]),
            zaxis=dict(visible=False, range=[-2, 12]),
            camera=dict(
                eye=dict(x=0.8, y=2.5, z=0.5),
                up=dict(x=0, y=0, z=1),
            ),
            bgcolor="white",
        ),
        paper_bgcolor="white",
        margin=dict(l=0, r=0, t=60, b=0),
        width=1200, height=800,
    )
    save(fig, "section3_4layer_architecture")


# ───────────────────────────────────────────────────────────────
# 섹션 5-0. 기대 효과 Before/After 비교
# ───────────────────────────────────────────────────────────────

def section5_expected_effects():
    """현행 시스템 vs Swarm-Net 4대 효과 비교 수평 막대"""
    print("[섹션5-0] 기대 효과 Before/After 비교")

    metrics = [
        "확장 비용\n(배율)",
        "배치 소요\n(시간)",
        "탐지 레이턴시\n(초)",
        "관제 인력\n(명/100대)",
    ]

    # 정규화된 비교 값 (시각적 비교용)
    current_vals  = [3.5, 4320, 15.0, 100]   # 3.5x, 180일(4320시간), 15초, 100명
    swarm_vals    = [1.0, 0.5,   0.8,  20]   # 1.0x, 0.5시간(30분), 0.8초, 20명

    # 표시 라벨
    current_labels = ["3~5x (기하급수적)", "6개월+ (수개월)", "~15초 (수동)", "100명 (1:1)"]
    swarm_labels   = ["1.0x (선형)", "30분", "<1초 (자동)", "20명 (1:수십)"]
    improvements   = ["75% 절감", "99.9% 단축", "93%+ 단축", "80% 절감"]

    # 로그 스케일로 정규화
    import math as m
    current_norm = [m.log10(max(v, 0.1)) + 1 for v in current_vals]
    swarm_norm   = [m.log10(max(v, 0.1)) + 1 for v in swarm_vals]

    fig = go.Figure()

    fig.add_trace(go.Bar(
        name="현행 시스템",
        y=metrics,
        x=current_norm,
        orientation="h",
        marker_color="#EF5350",
        opacity=0.8,
        text=current_labels,
        textposition="outside",
        textfont=dict(size=12, family="Arial Black"),
    ))

    fig.add_trace(go.Bar(
        name="Swarm-Net",
        y=metrics,
        x=swarm_norm,
        orientation="h",
        marker_color="#42A5F5",
        opacity=0.8,
        text=swarm_labels,
        textposition="outside",
        textfont=dict(size=12, family="Arial Black"),
    ))

    # 개선률 주석 (우측)
    for i, imp in enumerate(improvements):
        fig.add_annotation(
            x=max(current_norm[i], swarm_norm[i]) + 1.5,
            y=metrics[i],
            text=f"▼ {imp}",
            showarrow=False,
            font=dict(size=13, color="#2E7D32", family="Arial Black"),
            bgcolor="rgba(232,245,233,0.9)", borderpad=4,
        )

    fig.update_layout(
        title=dict(
            text="기대 효과: 현행 시스템 vs Swarm-Net",
            font=dict(size=22, family="Arial Black"), x=0.5,
        ),
        barmode="group",
        xaxis=dict(showticklabels=False, showgrid=False,
                   zeroline=False, title=""),
        yaxis=dict(tickfont=dict(size=13, family="Arial Black")),
        paper_bgcolor="white",
        plot_bgcolor="rgba(250,250,250,0.5)",
        legend=dict(
            font=dict(size=14),
            x=0.5, y=-0.12,
            xanchor="center",
            orientation="h",
            bgcolor="rgba(255,255,255,0.9)",
        ),
        margin=dict(l=130, r=120, t=90, b=80),
        width=1200, height=500,
        annotations=[
            dict(text="모든 지표에서 Swarm-Net이 현행 대비 75~99.9% 개선",
                 x=0.5, y=-0.22, xref="paper", yref="paper",
                 showarrow=False,
                 font=dict(size=15, color="#1565C0", family="Arial Black"),
                 bgcolor="rgba(227,242,253,0.9)", borderpad=8),
        ],
    )
    save(fig, "section5_expected_effects")


# ───────────────────────────────────────────────────────────────
# 섹션 5-1. 적용 분야 히트맵
# ───────────────────────────────────────────────────────────────

def section5_application_matrix():
    """4대 적용 분야 × 5대 역량 히트맵"""
    print("[섹션5-1] 적용 분야 히트맵")

    domains = ["법 집행", "상업/민간", "국방/방산", "공공 안전"]
    capabilities = ["탐지 정확도", "실시간 통제", "자동 대응",
                    "규제 준수", "수익 잠재력"]

    scores = [
        [9, 6, 4, 9, 5],   # 법 집행
        [8, 7, 5, 8, 9],   # 상업
        [10, 9, 9, 7, 10],  # 국방
        [9, 8, 6, 9, 6],   # 공공 안전
    ]

    use_cases = [
        ["NFZ 위반 감지", "증거 영상", "자동 경고", "FAA 호환", "공공 사업"],
        ["배송 경로", "교통 관리", "충돌 회피", "Remote ID", "UAM 플랫폼"],
        ["적 드론 식별", "전술 통제", "자동 요격", "군 표준", "방산 계약"],
        ["VIP 경호", "행사 관제", "긴급 퇴각", "국토부 준수", "SaaS"],
    ]

    hover_text = [[f"분야: {domains[i]}<br>역량: {capabilities[j]}"
                   f"<br>점수: {scores[i][j]}/10<br>활용: {use_cases[i][j]}"
                   for j in range(5)] for i in range(4)]

    fig = go.Figure(data=go.Heatmap(
        z=scores,
        x=capabilities,
        y=domains,
        colorscale=[
            [0, "#E3F2FD"], [0.3, "#90CAF9"],
            [0.5, "#42A5F5"], [0.7, "#1976D2"],
            [1.0, "#0D47A1"],
        ],
        zmin=0, zmax=10,
        text=[[f"{scores[i][j]}\n{use_cases[i][j]}"
               for j in range(5)] for i in range(4)],
        texttemplate="%{text}",
        textfont=dict(size=11, color="white", family="Arial Black"),
        hovertext=hover_text,
        hovertemplate="%{hovertext}<extra></extra>",
        colorbar=dict(title="적합도", tickvals=[0, 2, 4, 6, 8, 10]),
    ))

    fig.update_layout(
        title=dict(
            text="Swarm-Net 적용 분야별 역량 매트릭스",
            font=dict(size=22, family="Arial Black"), x=0.5,
        ),
        xaxis=dict(title="시스템 역량",
                   tickfont=dict(size=13, family="Arial Black"), side="top"),
        yaxis=dict(title="적용 분야",
                   tickfont=dict(size=13, family="Arial Black")),
        paper_bgcolor="white",
        margin=dict(l=120, r=40, t=100, b=60),
        width=1050, height=550,
        annotations=[
            dict(text="국방/방산 분야: 전 역량 최고 적합도 (평균 9.0/10)",
                 x=0.5, y=-0.12, xref="paper", yref="paper",
                 showarrow=False,
                 font=dict(size=14, color="#0D47A1", family="Arial Black")),
        ],
    )
    save(fig, "section5_application_matrix")


# ───────────────────────────────────────────────────────────────
# 섹션 5-2. 글로벌 시장 규모 및 TAM 성장
# ───────────────────────────────────────────────────────────────

def section5_market_tam():
    """글로벌 드론 시장 + 국내 시장 + Swarm-Net TAM"""
    print("[섹션5-2] 글로벌 시장 규모 및 TAM 성장")

    from plotly.subplots import make_subplots

    fig = make_subplots(specs=[[{"secondary_y": True}]])

    years = [2023, 2024, 2025, 2026, 2027, 2028, 2029, 2030, 2032, 2035]
    labels = [str(y) for y in years]

    global_market = [45, 50, 56, 62, 68, 75, 82, 88, 94, 99]
    korea_market  = [1.2, 1.5, 1.8, 2.2, 2.7, 3.2, 3.8, 4.2, 4.8, 5.5]

    defense   = [18, 21, 24, 27, 30, 34, 38, 41, 45, 50]
    commercial = [16, 17, 18, 20, 22, 24, 26, 28, 30, 33]
    public    = [7, 7.5, 8, 9, 9.5, 10, 11, 12, 12.5, 10]
    infra     = [4, 4.5, 6, 6, 6.5, 7, 7, 7, 6.5, 6]

    fig.add_trace(go.Scatter(
        x=labels, y=defense, fill="tozeroy", name="국방 (Defense)",
        fillcolor="rgba(239,83,80,0.3)", line=dict(color="#EF5350", width=0),
        stackgroup="market",
    ), secondary_y=False)
    fig.add_trace(go.Scatter(
        x=labels, y=commercial, fill="tonexty", name="상업 (Commercial)",
        fillcolor="rgba(66,165,245,0.3)", line=dict(color="#42A5F5", width=0),
        stackgroup="market",
    ), secondary_y=False)
    fig.add_trace(go.Scatter(
        x=labels, y=public, fill="tonexty", name="공공 안전 (Public)",
        fillcolor="rgba(102,187,106,0.3)", line=dict(color="#66BB6A", width=0),
        stackgroup="market",
    ), secondary_y=False)
    fig.add_trace(go.Scatter(
        x=labels, y=infra, fill="tonexty", name="인프라 (Infra)",
        fillcolor="rgba(255,167,38,0.3)", line=dict(color="#FFA726", width=0),
        stackgroup="market",
    ), secondary_y=False)

    fig.add_trace(go.Scatter(
        x=labels, y=global_market, name="글로벌 합계 ($B)",
        line=dict(color="#333", width=3),
        mode="lines+markers",
        marker=dict(size=8, color="#333"),
    ), secondary_y=False)

    fig.add_trace(go.Scatter(
        x=labels, y=korea_market, name="국내 시장 (₩조)",
        line=dict(color="#1976D2", width=3, dash="dash"),
        mode="lines+markers+text",
        marker=dict(size=8, color="#1976D2"),
        text=[f"₩{v}조" if i % 2 == 0 else "" for i, v in enumerate(korea_market)],
        textposition="top center",
        textfont=dict(size=10, color="#1976D2"),
    ), secondary_y=True)

    fig.update_layout(
        title=dict(
            text="글로벌 드론 시장 규모 전망 및 Swarm-Net TAM",
            font=dict(size=22, family="Arial Black"), x=0.5,
        ),
        paper_bgcolor="white",
        plot_bgcolor="rgba(250,250,250,0.5)",
        legend=dict(font=dict(size=11), x=0.01, y=0.99,
                    bgcolor="rgba(255,255,255,0.9)"),
        margin=dict(l=60, r=80, t=90, b=80),
        width=1200, height=700,
        annotations=[
            dict(text="Phase 1 TAM\n₩500억",
                 x="2026", y=62, xref="x", yref="y",
                 showarrow=True, arrowhead=2, ax=50, ay=30,
                 font=dict(size=11, color="#42A5F5", family="Arial Black"),
                 bgcolor="rgba(227,242,253,0.9)", borderpad=4),
            dict(text="Phase 2 TAM\n₩5,000억",
                 x="2028", y=75, xref="x", yref="y",
                 showarrow=True, arrowhead=2, ax=50, ay=30,
                 font=dict(size=11, color="#FF6F00", family="Arial Black"),
                 bgcolor="rgba(255,243,224,0.9)", borderpad=4),
            dict(text="Phase 3 TAM\n₩10조+",
                 x="2032", y=94, xref="x", yref="y",
                 showarrow=True, arrowhead=2, ax=40, ay=-30,
                 font=dict(size=11, color="#2E7D32", family="Arial Black"),
                 bgcolor="rgba(232,245,233,0.9)", borderpad=4),
            dict(text="2035년: $99B (약 ₩130조) — CAGR 12~15%",
                 x=0.5, y=-0.15, xref="paper", yref="paper",
                 showarrow=False,
                 font=dict(size=14, color="#333", family="Arial Black")),
        ],
    )
    fig.update_yaxes(title_text="글로벌 시장 ($B)", secondary_y=False,
                     gridcolor="rgba(200,200,200,0.5)")
    fig.update_yaxes(title_text="국내 시장 (₩조)", secondary_y=True,
                     showgrid=False, range=[0, 7])

    save(fig, "section5_market_tam")


# ═══════════════════════════════════════════════════════════════
# Main
# ═══════════════════════════════════════════════════════════════

if __name__ == "__main__":
    print("=" * 60)
    print("발표 시각화 자료 생성 (캡스톤 4개 + IR 4개 + 보고서 11개)")
    print("=" * 60)

    print("\n── 캡스톤 디자인 발표 시각화 ──")
    capstone_cost_comparison()
    capstone_digital_twin()
    capstone_llm_integration()
    capstone_self_healing()

    print("\n── IR/기업 설명회 시각화 ──")
    ir_market_painpoint()
    ir_virtual_testbed()
    ir_roi_analysis()
    ir_business_roadmap()

    print("\n── 캡스톤 보고서 섹션별 시각화 ──")
    section2_drone_growth()
    section2_problem_heatmap()
    section2_approval_flow()
    section3_kpi_dashboard()
    section3_gantt_timeline()
    section3_e2e_pipeline()
    section3_sensor_fusion()
    section3_4layer_architecture()
    section5_expected_effects()
    section5_application_matrix()
    section5_market_tam()

    print("\n" + "=" * 60)
    all_html = sorted(f for f in os.listdir(OUTPUT_DIR)
                      if f.endswith(".html") and
                      (f.startswith("capstone_") or f.startswith("ir_")
                       or f.startswith("section")))
    print(f"완료! 총 {len(all_html)}개 파일 생성:")
    for f in all_html:
        print(f"  {f}")
    print("=" * 60)
