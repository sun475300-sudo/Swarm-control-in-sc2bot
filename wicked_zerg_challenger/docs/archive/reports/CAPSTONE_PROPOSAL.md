# 캡스톤 디자인 과제 계획서

---

## 1. 프로젝트명

### **SC2-Swarm: 다중 에이전트 AI 기반 분산형 군집 드론 제어 시스템 (Sim-to-Real)**

> *SC2-Swarm: Decentralized Swarm Drone Control System based on Multi-Agent AI (Sim-to-Real Transfer)*

---

## 2. 과제 선정 배경 및 필요성

### 2-1. 문제 제기

현재 산업 및 국방 분야에서 운용되는 군집 드론은 대부분 **지상 통제국(GCS)의 중앙 집중식 제어**에 의존하고 있습니다.
이는 다음과 같은 치명적 취약점을 가집니다:

| 취약점 | 설명 | 위험도 |
|--------|------|--------|
| **통신 음영** | 산악/도심 지역에서 전파 도달 불가 | 높음 |
| **전파 교란(Jamming)** | 야전/분쟁 환경에서 의도적 교란 | 매우 높음 |
| **단일 실패점(SPOF)** | GCS 장애 시 전체 시스템 마비 | 치명적 |
| **확장성 한계** | 드론 수 증가 시 통제 부하 급증 | 중간 |

### 2-2. 해결 방안

각 개체가 **독립적으로 주변을 인식하고 판단**하여 대열을 유지하는 유기적 시스템이 필요합니다.

본 프로젝트는 **스타크래프트 2(SC2)의 다중 에이전트 AI**가 보여주는 고도화된 **'분산형 군집 제어(Swarm Control)'** 및 **충돌 회피 알고리즘**을 실제 물리 환경의 드론 비행 제어에 이식(**Sim-to-Real**)하는 **자율 군집 비행 시스템**을 제안합니다.

### 2-3. 기술적 근거: SC2 → 드론 기술 전이 타당성

```
SC2 게임 환경                          실제 드론 환경
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Blackboard (중앙 상태 관리)  ══►  Flight Data Hub (비행 데이터)
Boids Algorithm (군집 이동)   ══►  Formation Flight (편대 비행)
Authority Mode (우선순위)     ══►  ATC Priority Levels (관제 우선순위)
IntelManager (정찰/탐지)      ══►  Sensor Fusion (LiDAR/Camera/GPS)
StrategyManager (전략 FSM)    ══►  Route Planner (경로 계획)
CreepManager (영역 확장)      ══►  Airspace Corridor (비행 회랑)
RL Agent (강화학습)           ══►  Adaptive AI (적응형 경로 최적화)
RuntimeSelfHealing (자가복구)  ══►  Fail-Safe System (자동 착륙/회피)
```

> **핵심 인사이트**: SC2의 2D 군집 제어 알고리즘은 **고도(altitude) 차원만 추가**하면 드론 편대 비행의 핵심 제어 로직으로 **직접 전이 가능**합니다.

---

## 3. 과제 목표 및 주요 개발 내용

### 3-1. 최종 목표

가상 환경(SC2)의 **2D 기반 군집 제어 로직을 3D 물리 공간에 이식**하고, 중앙 통제 없이 **3대 이상의 실제 드론이 스스로 충돌을 회피하며 목적지까지 대열을 유지**하는 분산 통제 시스템 실증.

### 3-2. 주요 개발 내용 (3단계 접근)

#### Stage 1: 소프트웨어 및 알고리즘 (Algorithm)

SC2 봇 개발 환경에서 사용된 핵심 군집 유지 및 회피 로직을 **수학적 모델로 추출**하여 범용 알고리즘(Python/C++)으로 변환.

**핵심 알고리즘: Boids Swarm Control**

```
최종 이동 벡터 V = w₁·Separation + w₂·Alignment + w₃·Cohesion + w₄·Avoid + w₅·Altitude

  Separation (분리) : 개체 간 최소 거리 유지 → 충돌 방지
  Alignment  (정렬) : 이웃 유닛과 이동 방향 통일 → 대형 유지
  Cohesion   (응집) : 그룹 중심을 향해 이동 → 밀집 유지
  Avoid      (회피) : 위험 요소 감지 → 긴급 회피
  Altitude   (고도) : 3D 고도 분리 → SC2에 없는 새 차원
```

**SC2 → 드론 파라미터 매핑:**

| SC2 파라미터 | SC2 값 | 드론 값 | 변환 |
|-------------|--------|--------|------|
| separation_radius | 2.0 tile | 5.0 m | × 2.5 |
| max_speed | 3.0 game unit | 15 m/s | × 5 |
| cohesion_weight | 1.0 | 0.8 | 공중 확장 보정 |
| **altitude_weight** | **0.0 (2D)** | **1.2** | **3D 신규 추가** |

```
📊 시각자료: boids_swarm_attack.gif — 60기 Boids 군집 공격 시뮬레이션
📊 시각자료: part3_2_boids_forces.html — Boids 힘 벡터 3D 시각화
```

#### Stage 2: 시뮬레이션 검증 (Sim)

ROS 2 미들웨어와 Gazebo 시뮬레이터를 활용하여 **중력, 관성, 센서 노이즈**가 반영된 가상 3D 환경에서 가상 기체 다수의 군집 비행 1차 검증.

**시뮬레이션 환경 구성:**

```
┌──────────────────────────────────────────────┐
│              ROS 2 Middleware                  │
│                                               │
│   ┌─────────┐   ┌─────────┐   ┌─────────┐   │
│   │ Drone 1 │   │ Drone 2 │   │ Drone 3 │   │
│   │  Node   │◄──│  Node   │◄──│  Node   │   │
│   └────┬────┘   └────┬────┘   └────┬────┘   │
│        │              │              │        │
│   ┌────▼────────────────────────────▼────┐   │
│   │       Boids Swarm Controller          │   │
│   │  (SC2 알고리즘 Python → ROS 2 노드)    │   │
│   └────────────────┬─────────────────────┘   │
│                    │                          │
│   ┌────────────────▼─────────────────────┐   │
│   │          Gazebo Simulator             │   │
│   │   중력 / 관성 / 센서 노이즈 / 바람     │   │
│   └──────────────────────────────────────┘   │
└──────────────────────────────────────────────┘
```

**검증 기준:**
- 편대 유지율 ≥ 90%
- 충돌 발생률 < 0.01%
- 통신 지연 100ms 내 대응

```
📊 시각자료: formation_flight.gif — V자/원형/라인 편대 전환 시뮬레이션
📊 시각자료: collision_avoidance.gif — 8기 교차 비행 충돌 회피
```

#### Stage 3: 하드웨어 통합 및 실증 (Real)

Pixhawk(비행제어기)와 보조 컴퓨터(Raspberry Pi 등)를 MAVLink로 연동. **통신 지연(Latency) 보정 수식**을 적용하여 실제 기체 간 통신망을 구축하고 실내/외 비행 실증.

**하드웨어 스택:**

| 구성요소 | 사양 | 역할 |
|---------|------|------|
| 비행제어기 | Pixhawk 4/6 | 기체 자세/고도 제어 (PID) |
| 보조 컴퓨터 | Raspberry Pi 4/5 | Boids 알고리즘 실행 |
| 통신 | WiFi Mesh / MAVLink | 드론 간 P2P 통신 |
| 센서 | GPS + LiDAR/ToF | 위치 + 장애물 감지 |
| 프레임워크 | ROS 2 + PX4 | 미들웨어 통합 |

**통신 지연 보정:**

```
보정된 위치 = 현재 위치 + 속도 × Δt_latency
  Δt_latency = 측정된 통신 지연 (ms)
  속도 = 마지막 수신된 속도 벡터
```

```
📊 시각자료: sim_to_real_pipeline.gif — Sim-to-Real 파이프라인 진행
📊 시각자료: part4_2_drone_airspace.html — 3D 공역 관리 시각화
```

---

## 4. 추진 내용 (개발 프로세스)

### 4-1. 스케치 (Concept Sketch)

**SC2 봇 아키텍처 → 드론 ATC 시스템 개념 매핑**

```
📊 시각자료: part4_1_concept_bridge.html — SC2↔ATC 기술 전이 3D 브릿지
```

**기술 전이 신뢰도 매트릭스:**

| SC2 컴포넌트 | 드론 ATC 대응 | 전이 신뢰도 |
|-------------|--------------|-----------|
| Blackboard (중앙 상태) | Flight Data Hub | ★★★★★ Direct |
| Boids Algorithm | Formation Flight Control | ★★★★★ Direct |
| Authority Mode (우선순위) | ATC Priority Levels | ★★★★★ Direct |
| IntelManager (정찰) | Sensor Fusion | ★★★★☆ Adapt |
| StrategyManager (FSM) | Route Planning | ★★★★☆ Adapt |
| CreepManager (영역) | Airspace Corridor | ★★★☆☆ Concept |
| RL Agent (학습) | Adaptive AI | ★★★★☆ Adapt |
| RuntimeSelfHealing | Fail-Safe System | ★★★★★ Direct |

### 4-2. 개념 설계 (Conceptual Design)

**시스템 아키텍처 (FSM + Rule-Based + RL Hybrid)**

```
📊 시각자료: part1_1_fsm_timeline.html — Game Phase FSM 3D 타임라인
📊 시각자료: part1_2_authority_mode.html — Authority Mode 3D 상태 전이
📊 시각자료: part1_3_hybrid_architecture.html — Rule+RL 하이브리드 3D 레이어
```

**의사결정 프로세스:**

```
정찰(Scout) → 판단(Decide) → 집결(Rally) → 교전(Engage) → 평가(Evaluate)
    ↑                                                          │
    └──────────────── 순환 (Feedback Loop) ◄──────────────────┘
```

```
📊 시각자료: part2_1_tactical_spiral.html — 전술 의사결정 3D 나선
📊 시각자료: part2_2_engagement_tree.html — 교전 결정 트리 3D
```

**ATC 우선순위 시스템 (Authority Mode 전이):**

| 우선순위 | SC2 모드 | ATC 레벨 | 동작 |
|---------|---------|---------|------|
| Level 0 | EMERGENCY | 충돌 회피 | 모든 드론 즉각 회피 |
| Level 1 | COMBAT | 의료/긴급 | 일반 드론 대기, 긴급 통과 |
| Level 2 | STRATEGY | 계획 배송 | 스케줄 기반 경로 할당 |
| Level 3 | ECONOMY | 순찰/측량 | 여유 공역 자유 비행 |

```
📊 시각자료: authority_mode_switch.gif — Authority Mode 실시간 전환
```

### 4-3. 작품 개발 (Development)

**핵심 개발 결과물:**

1. **SC2 Boids Swarm Controller** (Python, 검증 완료)
   - 60+ 유닛 실시간 군집 제어
   - Separation/Alignment/Cohesion + Threat Avoidance
   - 10,000+ 게임 학습 데이터

2. **ROS 2 Swarm Node** (Python/C++)
   - SC2 알고리즘의 ROS 2 노드 변환
   - MAVLink 통신 인터페이스
   - 고도 차원(altitude_weight) 추가

3. **Gazebo 시뮬레이션 환경**
   - 멀티 드론 비행 시나리오
   - 바람/노이즈/통신지연 시뮬레이션

4. **실제 드론 비행 시스템**
   - Pixhawk + Raspberry Pi 통합
   - WiFi Mesh P2P 통신
   - 3대 실증 비행

---

## 5. 팀 구성 및 역할 (R&R)

본 과제는 하드웨어, 소프트웨어, 시스템 통합의 **융합 프로젝트**이므로 세분화된 역할 분담이 필수적입니다.

| 역할 | 담당 | 주요 업무 |
|------|------|----------|
| **팀장** (HW 제어 / 비행 총괄) | [본인] | 드론 기체 설계/조립, Pixhawk PID 튜닝, 비행 안전 통제, 메인 파일럿 |
| **팀원 1** (AI / 시뮬레이션) | [팀원1] | SC2 경로 계획/충돌 회피 코드 최적화, ROS 2 노드 설계, Gazebo 환경 구축 |
| **팀원 2** (통신망 / SI) | [팀원2] | 드론 간 Mesh Network 설계, 데이터 파이프라인 구축, Sim↔Real 인터페이스 |

---

## 6. 추진 일정 (1학기 기준 마일스톤)

```
주차    마일스톤                                    산출물
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

1~3     기획 및 설계                                요구사항 정의서
        ├ 요구사항 정의                             기체 부품 BOM
        ├ 기체 부품 선정 및 발주                     알고리즘 추상화 문서
        └ SC2 알고리즘 수학적 추상화 완료

4~6     시뮬레이션 구현                              ROS 2 패키지
        ├ ROS 2 + Gazebo 환경 구축                  Gazebo 월드 파일
        ├ Boids 알고리즘 → ROS 2 노드 변환          시뮬레이션 영상
        └ 가상 군집 비행 성공률 90% 달성

7~8     중간 점검                                    하드웨어 완성 사진
        ├ 드론 조립 완료                             PID 튜닝 로그
        ├ 단일 기체 호버링 성공                      중간 발표 자료
        └ PID 정밀 튜닝 완료

9~12    Sim-to-Real 통합                            통합 테스트 영상
        ├ 보조 컴퓨터(RPi) 연동                     통신 프로토콜 문서
        ├ 실제 기체 2~3대 지상 통신 테스트           비행 로그 데이터
        └ 소규모 실내 비행 실증

13~15   디버깅 및 최종 실증                          야외 비행 영상
        ├ 통신 지연 보정 적용                        최종 보고서
        ├ 야외 비행 테스트                           시연 영상
        └ 결과 보고서 및 시연 영상 제작               포스터
```

---

## 7. 프로젝트 결과물 활용

### 7-1. 파급 효과

| 분야 | 활용 | 기대 효과 |
|------|------|----------|
| **국방** | 감시/정찰 군집 드론 | 전파 교란 환경에서도 자율 비행 유지 |
| **재난 대응** | 수색/구조 드론 | 통신 음영 지역 독립 운용 |
| **물류** | 군집 배송 드론 | 중앙 서버 의존도 제거, 확장성 확보 |
| **농업** | 정밀 농업 드론 | 넓은 농경지 자율 분담 작업 |

### 7-2. 사업화 → 경진대회

| 대회/프로그램 | 적합도 | 비고 |
|-------------|--------|------|
| 국방부 드론봇 챌린지 | ★★★★★ | 군집 드론 핵심 기술 |
| KARI 무인기 대회 | ★★★★★ | 자율비행 기술 실증 |
| 창업진흥원 예비창업패키지 | ★★★★☆ | 드론 물류 사업화 |
| IEEE IROS / ICRA | ★★★★☆ | 학술 논문 발표 |
| 한국로봇학회 학술대회 | ★★★★☆ | Sim-to-Real 기술 |

---

## 8. 기대 효과 및 진로 연계

본 캡스톤 결과물은 단순 학점 취득을 넘어, **졸업 후의 뚜렷한 커리어를 개척하는 핵심 실적물**이 됩니다.

취업과 진학이라는 중요한 선택의 기로에서, 하드웨어(정비/조종) 기반의 탄탄한 기본기에 최신 소프트웨어(AI/제어) 역량까지 융합할 수 있음을 입증하는 **확실한 지표**가 됩니다.

특히 무인기 및 로봇 자산을 총괄 운용하는 장교로 임관하거나, 첨단 방위산업체 및 로봇 연구소로 나아갈 때, **시뮬레이션의 가상 코드를 실제 비행 기체의 물리적 제어로 완벽히 구현해 낸(Sim-to-Real) 경험**은 현장에서 즉시 전력감으로 인정받을 수 있는 강력한 경쟁력으로 작용할 것입니다.

---

## 9. 참고 자료

### 레퍼런스 프로젝트

| 프로젝트 | 링크 | 참고 내용 |
|---------|------|----------|
| DRONAI (군 해커톤 2021) | [GitHub](https://github.com/osamhack2021/app_web_dronai_62bn) | 64기 편대 비행 시뮬레이션, 자동 회피, 웹 대시보드 |
| PathFindingEnhanced | [GitHub](https://github.com/supercontact/PathFindingEnhanced) | Unity 기반 경로 탐색 시각화, A* / Dijkstra 알고리즘 |
| SC2-Swarm (본 프로젝트) | 본 레포지토리 | Boids + FSM + RL 하이브리드 군집 제어 |

### 기술 문서

| 기술 | 핵심 내용 |
|------|----------|
| Boids Algorithm (Reynolds, 1987) | Separation + Alignment + Cohesion |
| PX4 Autopilot | 오픈소스 비행 제어 스택 |
| ROS 2 (Humble/Iron) | 로봇 미들웨어 |
| Gazebo (Ignition) | 물리 시뮬레이터 |
| MAVLink Protocol | 드론-GCS 통신 프로토콜 |

---

## 시각 자료 목록

### 3D 인터랙티브 (HTML — 브라우저에서 회전/줌 가능)

| 파일명 | 내용 |
|--------|------|
| `part1_1_fsm_timeline.html` | Game Phase FSM 3D 타임라인 |
| `part1_2_authority_mode.html` | Authority Mode 상태 전이 3D |
| `part1_3_hybrid_architecture.html` | Rule + RL 하이브리드 3D 레이어 |
| `part2_1_tactical_spiral.html` | 전술 의사결정 3D 나선 |
| `part2_2_engagement_tree.html` | 교전 결정 트리 3D |
| `part3_1_boids_simulation.html` | Boids 군집 공격 3D (애니메이션) |
| `part3_2_boids_forces.html` | Boids 힘 벡터 3D |
| `part4_1_concept_bridge.html` | SC2 → ATC 기술 전이 3D 브릿지 |
| `part4_2_drone_airspace.html` | 드론 ATC 3D 공역 관리 |
| `part4_3_vision_roadmap.html` | End-to-End 로드맵 3D |

### 애니메이션 GIF (프레젠테이션/README 삽입용)

| 파일명 | 내용 | 크기 |
|--------|------|------|
| `boids_swarm_attack.gif` | 60기 Boids 군집 공격 시뮬레이션 | 884 KB |
| `formation_flight.gif` | V자→원형→라인 편대 전환 | 1.9 MB |
| `collision_avoidance.gif` | 8기 교차 비행 충돌 회피 | 481 KB |
| `sim_to_real_pipeline.gif` | Sim-to-Real 파이프라인 진행 | 775 KB |
| `authority_mode_switch.gif` | Authority Mode 실시간 전환 | 897 KB |

---

> **생성 도구**: `visuals/generate_3d_visuals.py` (Plotly 3D) + `visuals/generate_animated_gifs.py` (Matplotlib Animation)
>
> 모든 시각 자료는 `wicked_zerg_challenger/visuals/` 디렉토리에 위치합니다.
