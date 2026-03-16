# Swarm-Net Airspace Manager — 팀 공유 자료 패키지

> **프로젝트**: 군집 드론 기반 사용자 공역 통제 및 알림 시스템
> **최종 업데이트**: 2026-03-13

---

## 열어볼 파일 (우선순위 순)

### 핵심 자료 (발표/공유용)

| # | 파일명 | 설명 | 여는 방법 |
|---|--------|------|----------|
| 1 | `swarm_net_simulator.html` | **3D 인터랙티브 시뮬레이터** — 군집 드론 레이더 돔 + 유저 드론 카운트다운 | 브라우저로 열기 |
| 2 | `algorithm_viewer.html` | **알고리즘 구조도** — 4종 Mermaid 다이어그램 (탭 전환) | 브라우저로 열기 |
| 3 | `SYSTEM_ARCHITECTURE.md` | **전체 시스템 설계서** — 센서/통신/백엔드/PoC 4대 설계 | VS Code 또는 GitHub |
| 4 | `PROJECT_DESCRIPTION.md` | **발표용 프로젝트 설명서** — 개요, 로직, 기대효과, 로드맵 | VS Code 또는 GitHub |
| 5 | `ALGORITHM_FLOWCHART.md` | **알고리즘 Mermaid 원본** — GitHub에서 자동 렌더링됨 | GitHub 또는 Mermaid Live |

### Plotly 3D 시각화 (레이더망 관련)

| 파일명 | 내용 |
|--------|------|
| `radar_1_system_overview.html` | 전체 시스템 개요 — Sentinel 육각 그리드 + 유저 드론 + GCS |
| `radar_2_mesh_network.html` | 레이더 Mesh Network 구조 — 7대 Sentinel 중첩 감지 |
| `radar_3_user_scenario.html` | 유저 드론 타임라인 — 진입 → 감지 → 시간할당 → 경고 → 착륙 |
| `radar_4_operation_concept.html` | 전체 운용 조감도 — 도시 위 드론 관제 시나리오 |

### Plotly 3D 시각화 (심화/보조)

| 파일명 | 내용 |
|--------|------|
| `clear_1_system_overview.html` | 시스템 개요 (간결 버전) |
| `clear_2_boids_explained.html` | Boids 알고리즘 설명 |
| `clear_3_tech_transfer.html` | SC2 → 드론 기술 이전 |
| `clear_4_swarm_simulation.html` | 군집 시뮬레이션 |
| `clear_5_atc_priority.html` | ATC 우선순위 체계 |

### 애니메이션 GIF

| 파일명 | 내용 |
|--------|------|
| `boids_swarm_attack.gif` | 60유닛 Boids 군집 공격 |
| `formation_flight.gif` | V자 → 원형 → 직선 편대 전환 |
| `collision_avoidance.gif` | 8드론 교차 충돌 회피 |
| `sim_to_real_pipeline.gif` | Sim-to-Real 파이프라인 |
| `authority_mode_switch.gif` | 권한 모드 전환 애니메이션 |

### PoC 코드

| 파일명 | 설명 | 실행 방법 |
|--------|------|----------|
| `poc_simulation.py` | 백엔드 로직 시뮬레이션 | `python poc_simulation.py` |

---

## 빠른 시작

1. `swarm_net_simulator.html`을 브라우저에서 열기 (Chrome 권장)
2. "+" 버튼으로 유저 드론 추가, 타이머 카운트다운 관찰
3. `algorithm_viewer.html`으로 알고리즘 구조 확인
4. `SYSTEM_ARCHITECTURE.md`로 기술 상세 검토

---

## 필요 환경

- **HTML 파일**: 최신 브라우저 (Chrome/Edge/Firefox)
- **Markdown 파일**: VS Code, GitHub, 또는 Typora
- **Python 코드**: Python 3.10+ (`pip install numpy plotly` for regeneration)
- **GIF 파일**: 아무 이미지 뷰어
