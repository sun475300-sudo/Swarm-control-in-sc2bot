# SC2 Swarm Control → Drone ATC System
## Presentation Visual Diagrams

---

# Part 1: SC2 Bot Architecture (FSM + RL Hybrid)

---

## 1-1. Finite State Machine (FSM) — Game Phase Control

```mermaid
stateDiagram-v2
    direction LR

    [*] --> OPENING

    state OPENING {
        [*] --> BuildPool
        BuildPool --> ProduceQueen
        ProduceQueen --> FirstZerglings
        FirstZerglings --> NaturalExpansion
    }

    state EARLY_GAME {
        [*] --> ScoutEnemy
        ScoutEnemy --> IdentifyRace
        IdentifyRace --> SelectComposition
        SelectComposition --> DroneUp
    }

    state MID_GAME {
        [*] --> ThirdBase
        ThirdBase --> Upgrades
        Upgrades --> ArmyBuildup
        ArmyBuildup --> Engage
    }

    state LATE_GAME {
        [*] --> MaxSupply
        MaxSupply --> TechSwitch
        TechSwitch --> MultiProng
        MultiProng --> FinalPush
    }

    OPENING --> EARLY_GAME : 3:00
    EARLY_GAME --> MID_GAME : 6:00
    MID_GAME --> LATE_GAME : 12:00

    note right of OPENING
        🕐 0:00 ~ 3:00
        13 Supply → Pool
        17 Supply → Hatch
        Queen × 2 + Ling × 8
    end note

    note right of MID_GAME
        🕐 6:00 ~ 12:00
        3rd Base Saturation
        +1/+1 Upgrades
        Army 100+ Supply
    end note
```

---

## 1-2. Authority Mode FSM (Dynamic Priority Switching)

```mermaid
stateDiagram-v2
    direction TB

    BALANCED --> EMERGENCY : 🚨 Rush Detected
    BALANCED --> COMBAT : ⚔️ Medium Threat
    BALANCED --> ECONOMY : 💰 Coast Clear

    EMERGENCY --> COMBAT : Rush Defended
    COMBAT --> BALANCED : Threat Cleared
    ECONOMY --> BALANCED : Drones Saturated
    ECONOMY --> EMERGENCY : 🚨 Sudden Attack

    state EMERGENCY {
        direction LR
        [*] --> CancelEcon
        CancelEcon --> SpineRush
        SpineRush --> PullWorkers
        PullWorkers --> AllDefend
    }

    state COMBAT {
        direction LR
        [*] --> ArmyProduce
        ArmyProduce --> Rally
        Rally --> DefendBases
    }

    state ECONOMY {
        direction LR
        [*] --> MaxDrones
        MaxDrones --> Expand
        Expand --> TechUp
    }

    state BALANCED {
        direction LR
        [*] --> DroneArmyRatio
        DroneArmyRatio --> AdaptiveSpend
    }
```

---

## 1-3. Rule-Based + RL Hybrid Architecture

```mermaid
graph TB
    subgraph Input["🎮 Game State Input"]
        Units["아군/적군 유닛"]
        Resources["자원 (미네랄/가스)"]
        Map["맵 정보 (시야/지형)"]
        Time["게임 시간"]
    end

    subgraph RuleEngine["📏 Rule-Based Engine"]
        direction TB
        FSM["FSM Controller<br/>게임 단계별 상태 머신"]
        Priority["Authority System<br/>우선순위 기반 생산"]
        Trigger["Trigger Rules<br/>IF threat > HIGH → EMERGENCY"]
    end

    subgraph RLEngine["🧠 RL Engine (Shadow Mode)"]
        direction TB
        DQN["DQN Agent<br/>상태→행동 매핑"]
        HRL["Hierarchical RL<br/>매크로→마이크로 4계층"]
        Reward["Reward System<br/>승리 +100 / 패배 -100"]
    end

    subgraph Decision["⚡ Decision Fusion"]
        Merge["Rule 70% + RL 30%<br/>점진적 RL 비중 증가"]
    end

    subgraph Output["🎯 Action Output"]
        Build["건물/유닛 생산"]
        Move["유닛 이동/공격"]
        Ability["능력 시전"]
        Expand2["확장 결정"]
    end

    Input --> RuleEngine
    Input --> RLEngine
    RuleEngine --> Decision
    RLEngine --> Decision
    Decision --> Output

    Output -->|결과 피드백| Reward
    Reward -->|학습| DQN

    style RuleEngine fill:#e8f5e9,stroke:#2e7d32,stroke-width:2px
    style RLEngine fill:#e3f2fd,stroke:#1565c0,stroke-width:2px
    style Decision fill:#fff3e0,stroke:#e65100,stroke-width:2px
```

---

# Part 2: Operation Flow (Tactical Decision Process)

---

## 2-1. Tactical Decision Chain

```mermaid
graph LR
    subgraph Phase1["Phase 1: 정찰"]
        Scout["대군주 정찰<br/>적 본진 확인"]
        Analyze["적 빌드 분석<br/>테크/유닛 구성"]
        Threat["위협 평가<br/>NONE → CRITICAL"]
    end

    subgraph Phase2["Phase 2: 판단"]
        Strategy["전략 선택<br/>공격/방어/확장"]
        Comp["조합 결정<br/>바퀴/히드라/뮤탈"]
        Timing["타이밍 결정<br/>즉시/대기/올인"]
    end

    subgraph Phase3["Phase 3: 집결"]
        Rally["랠리 포인트<br/>자연 앞 집결"]
        Group["그룹 편성<br/>메인/서브/견제"]
        Formation["대형 구성<br/>전위/후위 배치"]
    end

    subgraph Phase4["Phase 4: 교전"]
        Engage["교전 개시<br/>engage_ratio > 0.7"]
        Micro["마이크로 제어<br/>Boids 알고리즘"]
        Spell["능력 시전<br/>자동 판단"]
        Retreat["후퇴 판단<br/>retreat_ratio < 0.4"]
    end

    subgraph Phase5["Phase 5: 평가"]
        Result["교전 결과"]
        Learn["RL 학습<br/>보상 계산"]
        Adapt["전략 수정"]
    end

    Phase1 --> Phase2 --> Phase3 --> Phase4 --> Phase5
    Phase5 -->|다음 교전| Phase1

    style Phase1 fill:#e3f2fd
    style Phase2 fill:#f3e5f5
    style Phase3 fill:#fff3e0
    style Phase4 fill:#ffebee
    style Phase5 fill:#e8f5e9
```

---

## 2-2. Engagement Decision Flowchart

```mermaid
graph TD
    Start["아군 부대 준비 완료"]

    Check1{"아군/적군<br/>전력비 > 0.7?"}
    Check2{"적 방어선<br/>취약점?"}
    Check3{"점막 위에서<br/>교전 가능?"}
    Check4{"스펠 유닛<br/>에너지 충분?"}

    Start --> Check1

    Check1 -->|Yes| Check2
    Check1 -->|No| Wait["대기 & 증원"]

    Check2 -->|Yes| Check3
    Check2 -->|No| Harass["견제 파견<br/>(저글링/뮤탈)"]

    Check3 -->|Yes| Check4
    Check3 -->|No| CreepPush["점막 확장 후<br/>재평가"]

    Check4 -->|Yes| FullEngage["전면 공격 🔥<br/>Boids + Spells"]
    Check4 -->|No| PartialEngage["부분 교전<br/>탱킹 유닛 선두"]

    FullEngage --> Result{"교전 결과?"}
    PartialEngage --> Result
    Harass --> Result

    Result -->|승리| Push["추격 & 확장"]
    Result -->|패배| Regroup["후퇴 & 재건"]
    Result -->|교착| Hold["라인 유지"]

    Wait --> |충원 완료| Check1

    style FullEngage fill:#4caf50,color:#fff
    style Wait fill:#ff9800
    style Regroup fill:#f44336,color:#fff
```

---

# Part 3: Unit Control Visualization (Swarm Simulation)

---

## 3-1. Boids Swarm Algorithm

```mermaid
graph TB
    subgraph BoidsForces["Boids 3대 힘"]
        direction LR

        subgraph Sep["🔄 Separation (1.5)"]
            SepDesc["개체 간 최소 거리 유지<br/>반경 2.0 내 유닛 밀어내기<br/>━━ 충돌 방지"]
        end

        subgraph Ali["➡️ Alignment (1.0)"]
            AliDesc["이웃 유닛과 이동 방향 일치<br/>그룹 이동 방향 통일<br/>━━ 대형 유지"]
        end

        subgraph Coh["🎯 Cohesion (1.0)"]
            CohDesc["그룹 중심을 향해 이동<br/>흩어진 유닛 재결집<br/>━━ 밀집 유지"]
        end
    end

    subgraph Additional["추가 행동 벡터"]
        Avoid["⚠️ Threat Avoidance<br/>시즈탱크, 거신, 템플러<br/>폭풍 범위 회피"]
        Target["🎯 Target Seeking<br/>우선순위 대상 추적<br/>일꾼 > 의료선 > 보병"]
    end

    subgraph Result["최종 이동 벡터"]
        Final["V = Sep×1.5 + Ali×1.0<br/>+ Coh×1.0 + Avoid<br/>+ Target"]
    end

    Sep --> Final
    Ali --> Final
    Coh --> Final
    Avoid --> Final
    Target --> Final

    Final --> Move["유닛 이동 명령"]

    style Sep fill:#ffcdd2
    style Ali fill:#c8e6c9
    style Coh fill:#bbdefb
    style Avoid fill:#fff9c4
    style Final fill:#e1bee7,stroke:#333,stroke-width:2px
```

---

## 3-2. Swarm Movement Simulation (Top-Down View)

```
    ┌─────────────────────────────────────────────────────────────┐
    │                    BATTLEFIELD MAP                          │
    │                                                             │
    │   🔴🔴🔴  ← Enemy Base                                     │
    │   🔴🔴                                                      │
    │                                                             │
    │          💥 Engagement Zone                                  │
    │        ╱─────────────╲                                      │
    │       ╱   🟡  🟡  🟡  ╲   ← Banelings (Flanking)          │
    │      ╱                  ╲                                   │
    │                                                             │
    │          🟢🟢🟢🟢        ← Roaches (Front Line)            │
    │          🟢🟢🟢🟢                                           │
    │                                                             │
    │       🔵🔵🔵              ← Hydras (Rear Support)          │
    │       🔵🔵🔵                                                │
    │                                                             │
    │    🟣  🟣                  ← Mutalisk (Flanking)            │
    │      🟣  🟣                                                 │
    │                                                             │
    │   ← Creep Highway ████████████████████████                  │
    │                                                             │
    │                    🟤🟤🟤  ← Rally Point                    │
    │                                                             │
    │   🟢🟢  ← Our Base                                          │
    └─────────────────────────────────────────────────────────────┘

    Movement Vectors:
    ──→  Main attack direction
    ╲  ╱  Flanking pincer
    ····>  Retreat path
```

---

## 3-3. Multi-Prong Attack Pattern (Doom Drop)

```mermaid
graph TB
    subgraph Command["지휘 본부"]
        CC["BotStepIntegrator<br/>공격 명령"]
    end

    subgraph Group1["🔴 Main Army (60%)"]
        G1["바퀴 + 히드라<br/>정면 돌격"]
    end

    subgraph Group2["🟡 Flank A (20%)"]
        G2["저글링 + 맹독충<br/>측면 우회"]
    end

    subgraph Group3["🟣 Flank B (15%)"]
        G3["뮤탈리스크<br/>일꾼 견제"]
    end

    subgraph Group4["🟢 Reserve (5%)"]
        G4["여왕 + 방어<br/>본진 수비"]
    end

    subgraph Enemy["적 기지"]
        EMain["정면 방어선"]
        EWorker["일꾼 라인"]
        EBase["본진"]
    end

    CC --> G1
    CC --> G2
    CC --> G3
    CC --> G4

    G1 -->|정면 공격| EMain
    G2 -->|좌측 우회| EWorker
    G3 -->|공중 견제| EBase
    G4 -->|본진 방어| Command

    style Group1 fill:#ffcdd2,stroke:#c62828
    style Group2 fill:#fff9c4,stroke:#f57f17
    style Group3 fill:#e1bee7,stroke:#6a1b9a
    style Group4 fill:#c8e6c9,stroke:#2e7d32
    style Enemy fill:#424242,color:#fff
```

---

# Part 4: SC2 Bot → Drone ATC System (Vision Bridge)

---

## 4-1. Concept Mapping: SC2 → Drone Swarm ATC

```mermaid
graph LR
    subgraph SC2["🎮 SC2 Swarm Control"]
        direction TB
        S1["Blackboard<br/>중앙 상태 관리"]
        S2["IntelManager<br/>적 탐지/추적"]
        S3["StrategyManager<br/>전략 의사결정"]
        S4["Boids Algorithm<br/>군집 이동 제어"]
        S5["Authority Mode<br/>우선순위 전환"]
        S6["SpellCaster<br/>능력 자동 시전"]
        S7["CreepManager<br/>영역 확장"]
        S8["RL Agent<br/>강화학습"]
    end

    subgraph ATC["✈️ Drone ATC System"]
        direction TB
        A1["Flight Data Hub<br/>전체 비행 상태"]
        A2["Radar/Sensor<br/>장애물/타 드론 감지"]
        A3["Route Planner<br/>경로 계획"]
        A4["Swarm Formation<br/>편대 비행 제어"]
        A5["Priority Manager<br/>긴급/일반 비행"]
        A6["Auto Maneuver<br/>자동 회피 기동"]
        A7["Airspace Control<br/>공역 관리"]
        A8["Adaptive AI<br/>적응형 경로 최적화"]
    end

    S1 ===|"1:1 매핑"| A1
    S2 ===|"1:1 매핑"| A2
    S3 ===|"1:1 매핑"| A3
    S4 ===|"핵심 전이"| A4
    S5 ===|"1:1 매핑"| A5
    S6 ===|"1:1 매핑"| A6
    S7 ===|"개념 전이"| A7
    S8 ===|"1:1 매핑"| A8

    style SC2 fill:#e3f2fd,stroke:#1565c0,stroke-width:2px
    style ATC fill:#fce4ec,stroke:#c62828,stroke-width:2px
```

---

## 4-2. Drone ATC System Architecture

```mermaid
graph TB
    subgraph Sensors["📡 Sensor Layer"]
        GPS["GPS Module<br/>위치 추적"]
        Lidar["LiDAR<br/>장애물 감지"]
        Camera["Camera<br/>시각 인식"]
        Comm["Communication<br/>드론 간 통신"]
    end

    subgraph Core["🧠 Core ATC Engine"]
        FDH["Flight Data Hub<br/>(= Blackboard)"]

        subgraph Planning["Route Planning"]
            Global["Global Planner<br/>출발→도착 경로"]
            Local["Local Planner<br/>실시간 회피"]
        end

        subgraph Swarm["Swarm Control"]
            BoidsD["Boids Formation<br/>편대 비행"]
            Spacing["Safe Spacing<br/>최소 간격 유지"]
            Sync["Speed Sync<br/>속도 동기화"]
        end

        subgraph Priority["Priority Manager"]
            Emergency["Emergency<br/>충돌 회피"]
            Medical["Medical<br/>의료 수송"]
            Delivery["Delivery<br/>일반 배송"]
            Survey["Survey<br/>측량/감시"]
        end
    end

    subgraph Airspace["🌐 Airspace Management"]
        Corridor["비행 회랑<br/>(= Creep Highway)"]
        Zone["구역 관리<br/>(= Territory)"]
        Altitude["고도 분리<br/>(= Authority Layers)"]
    end

    subgraph Output["🎯 Drone Commands"]
        Waypoint["Waypoint 이동"]
        Hover["호버링/대기"]
        Land["착륙/이륙"]
        Avoid2["긴급 회피"]
    end

    Sensors --> FDH
    FDH --> Planning
    FDH --> Swarm
    FDH --> Priority
    Planning --> Airspace
    Swarm --> Output
    Priority --> Planning
    Airspace --> Output

    style Core fill:#fff3e0,stroke:#e65100,stroke-width:2px
    style Swarm fill:#e8f5e9,stroke:#2e7d32
    style Priority fill:#ffebee,stroke:#c62828
```

---

## 4-3. Boids in Drone Formation Flight

```mermaid
graph TB
    subgraph SC2Boids["🎮 SC2 Boids"]
        direction LR
        ZSep["Separation<br/>저글링 간격 유지"]
        ZAli["Alignment<br/>이동 방향 통일"]
        ZCoh["Cohesion<br/>그룹 집결"]
        ZAvoid["Threat Avoid<br/>시즈탱크 회피"]
    end

    subgraph DroneTransfer["Transfer Formula"]
        Formula["V_drone = w₁·Sep + w₂·Ali<br/>+ w₃·Coh + w₄·Avoid<br/>+ w₅·Altitude"]
    end

    subgraph DroneBoids["✈️ Drone Boids"]
        direction LR
        DSep["Separation<br/>드론 간 안전거리 5m"]
        DAli["Alignment<br/>비행 방향 동기화"]
        DCoh["Cohesion<br/>편대 중심 유지"]
        DAvoid["Obstacle Avoid<br/>건물/지형 회피"]
        DAlt["Altitude Layer<br/>고도 분리"]
    end

    SC2Boids --> Formula
    Formula --> DroneBoids

    subgraph Params["Parameter Mapping"]
        P1["separation_radius<br/>2.0 tile → 5.0m"]
        P2["max_speed<br/>3.0 game → 15 m/s"]
        P3["cohesion_weight<br/>1.0 → 0.8 (공중 확장)"]
        P4["NEW: altitude_weight<br/>0.0 → 1.2 (3D 추가)"]
    end

    style SC2Boids fill:#e3f2fd
    style DroneBoids fill:#fce4ec
    style Formula fill:#fff9c4,stroke:#333,stroke-width:2px
```

---

## 4-4. ATC Priority System (= Authority Mode)

```mermaid
graph TD
    subgraph Priorities["ATC Priority Levels"]
        P0["🚨 Level 0: COLLISION AVOIDANCE<br/>(= EMERGENCY)<br/>즉각 회피 기동"]
        P1["🏥 Level 1: MEDICAL/EMERGENCY<br/>(= COMBAT)<br/>의료 수송 우선"]
        P2["📦 Level 2: SCHEDULED DELIVERY<br/>(= STRATEGY)<br/>계획된 배송"]
        P3["📸 Level 3: SURVEY/PATROL<br/>(= ECONOMY)<br/>측량/순찰"]
    end

    subgraph Actions["Priority Actions"]
        A0["모든 드론 경로 양보<br/>긴급 회피 실행"]
        A1["일반 드론 대기<br/>의료 드론 통과"]
        A2["스케줄 기반<br/>경로 할당"]
        A3["여유 공역<br/>자유 비행"]
    end

    P0 --> A0
    P1 --> A1
    P2 --> A2
    P3 --> A3

    P0 -->|해제| P1
    P1 -->|해제| P2
    P2 -->|완료| P3
    P3 -->|긴급 발생| P0

    style P0 fill:#f44336,color:#fff
    style P1 fill:#ff9800,color:#fff
    style P2 fill:#4caf50,color:#fff
    style P3 fill:#2196f3,color:#fff
```

---

## 4-5. End-to-End Vision: Game → Reality

```mermaid
graph LR
    subgraph Stage1["Stage 1: SC2 Simulation"]
        Game["SC2 게임 환경<br/>저그 유닛 군집 제어"]
        Algo["알고리즘 검증<br/>Boids + FSM + RL"]
        Data["학습 데이터 축적<br/>10,000+ 게임"]
    end

    subgraph Stage2["Stage 2: Sim Transfer"]
        Sim["3D 시뮬레이터<br/>(Gazebo/AirSim)"]
        Adapt["파라미터 적응<br/>2D→3D, 타일→미터"]
        Test["시뮬레이션 테스트<br/>충돌률 < 0.01%"]
    end

    subgraph Stage3["Stage 3: Real Drone"]
        HW["드론 하드웨어<br/>ROS2 + PX4"]
        Edge["Edge Computing<br/>실시간 연산"]
        Fly["실제 비행 테스트<br/>5대 편대 비행"]
    end

    subgraph Stage4["Stage 4: ATC Scale"]
        ATC["ATC 시스템<br/>100+ 드론 관제"]
        City["도시 공역 관리<br/>자율 비행 통합"]
        AI["AI 최적화<br/>실시간 경로 조정"]
    end

    Stage1 -->|알고리즘 이전| Stage2
    Stage2 -->|시뮬 검증| Stage3
    Stage3 -->|스케일업| Stage4

    style Stage1 fill:#e3f2fd,stroke:#1565c0
    style Stage2 fill:#f3e5f5,stroke:#6a1b9a
    style Stage3 fill:#e8f5e9,stroke:#2e7d32
    style Stage4 fill:#fff3e0,stroke:#e65100
```

---

## 4-6. Technology Transfer Matrix

```mermaid
graph TB
    subgraph Matrix["Technology Transfer: SC2 → Drone ATC"]
        direction TB

        subgraph Row1["Perception"]
            SC2_P["SC2: IntelManager<br/>Fog of War 탐색"]
            Arrow1["══►"]
            ATC_P["ATC: Sensor Fusion<br/>LiDAR + Camera + GPS"]
        end

        subgraph Row2["Decision"]
            SC2_D["SC2: StrategyManager<br/>FSM + Authority Mode"]
            Arrow2["══►"]
            ATC_D["ATC: Route Planner<br/>Priority Queue + Corridor"]
        end

        subgraph Row3["Control"]
            SC2_C["SC2: BoidsSwarmControl<br/>Separation/Alignment/Cohesion"]
            Arrow3["══►"]
            ATC_C["ATC: Formation Flight<br/>3D Boids + Altitude Layer"]
        end

        subgraph Row4["Learning"]
            SC2_L["SC2: DQN + Curriculum<br/>Easy → CheatInsane"]
            Arrow4["══►"]
            ATC_L["ATC: Adaptive RL<br/>Sim → Real Transfer"]
        end

        subgraph Row5["Safety"]
            SC2_S["SC2: RuntimeSelfHealing<br/>Manager Reset + GenAI Patch"]
            Arrow5["══►"]
            ATC_S["ATC: Fail-Safe System<br/>Auto-Land + Collision Avoidance"]
        end
    end

    style SC2_P fill:#bbdefb
    style SC2_D fill:#bbdefb
    style SC2_C fill:#bbdefb
    style SC2_L fill:#bbdefb
    style SC2_S fill:#bbdefb
    style ATC_P fill:#ffcdd2
    style ATC_D fill:#ffcdd2
    style ATC_C fill:#ffcdd2
    style ATC_L fill:#ffcdd2
    style ATC_S fill:#ffcdd2
```

---

## 4-7. Swarm-Net Airspace Control Algorithm (4-Phase Sequence)

```mermaid
sequenceDiagram
    autonumber
    participant CS as 🖥️ 관제 서버<br/>(ATC Server)
    participant SW as 📡 군집 드론<br/>(Swarm Fleet)
    participant RN as 🔷 레이더망<br/>(Mesh Radar)
    participant UD as 🚁 사용자 드론<br/>(User Drone)
    participant APP as 📱 사용자 앱<br/>(Controller)

    rect rgb(20, 40, 80)
    Note over CS,SW: 【1단계】 통제 구역 설정 & 레이더망 형성
    CS->>SW: 공역 좌표 할당 (GPS Waypoints)
    SW->>SW: 다각형 대형(Polygon Formation) 전개
    SW->>RN: Mesh Network 전개 (LiDAR + RF)
    RN-->>CS: 레이더 돔(Dome) 활성화 확인
    Note right of RN: 가상 돔 형성 완료<br/>통제 공역 ACTIVE
    end

    rect rgb(20, 60, 40)
    Note over RN,UD: 【2단계】 사용자 드론 탐지 & 식별
    UD->>RN: 공역 진입 (경계선 통과)
    RN->>RN: RF 신호 스캔 + MAC 주소 추출
    RN->>CS: 탐지 데이터 전송 (ID, 위치, 속도)
    CS->>CS: DB 등록 + 비행 허가 검증
    CS-->>UD: 인증 ACK (허가/거부)
    Note right of CS: 객체 등록 완료<br/>식별자: UD-1001
    end

    rect rgb(60, 50, 20)
    Note over CS,APP: 【3단계】 체공 시간 할당 & 실시간 추적
    CS->>CS: 타이머 시작 (예: 15:00)
    loop 매 1초마다
        SW->>RN: 삼각측량 (X, Y, Z 좌표)
        RN->>CS: 실시간 위치 동기화
        CS->>APP: 위치 + 잔여 시간 Push
    end
    Note right of APP: 대시보드 실시간 표시<br/>🟢 정상 비행 중
    end

    rect rgb(80, 20, 20)
    Note over CS,APP: 【4단계】 경고 알림 & 퇴각 통제
    CS->>APP: ⚠️ 1차 경고 (잔여 2분)
    APP-->>UD: 비행 시간 임박 알림 표시
    Note right of APP: 🟡 WARNING<br/>"2분 남았습니다"

    CS->>APP: 🔴 최종 경고 (시간 초과!)
    CS->>UD: 강제 복귀 명령 전송
    APP-->>UD: 즉시 착륙/복귀 명령
    Note right of UD: 🔴 UNAUTHORIZED<br/>"즉시 복귀하세요"

    alt 유저 드론 응답 (30초 이내)
        UD-->>CS: 복귀 ACK + 이탈 진행
        CS->>RN: 레이더망 추적 해제
    else 미응답 (30초 초과)
        CS->>SW: 긴급 프로토콜 발동
        SW->>UD: 물리적 차단/에스코트
        Note right of SW: 🚨 EMERGENCY<br/>관제 강제 개입
    end
    end
```

---

## 4-8. Communication Flow: Swarm → Server → User Drone

```mermaid
graph TD
    subgraph SwarmLayer["📡 Swarm Drone Layer (Mesh Network)"]
        direction LR
        SD1["Swarm Drone #1<br/>GPS + LiDAR"]
        SD2["Swarm Drone #2<br/>GPS + LiDAR"]
        SD3["Swarm Drone #3<br/>GPS + LiDAR"]
        SD1 <-->|"Mesh Link"| SD2
        SD2 <-->|"Mesh Link"| SD3
        SD3 <-->|"Mesh Link"| SD1
    end

    subgraph Detect["🔍 Detection Phase"]
        Scan["공역 스캔<br/>레이더망 활성 영역"]
        Identify["사용자 드론 식별<br/>ID / 위치 / 속도"]
        Validate["비행 허가 확인<br/>인증 토큰 검증"]
    end

    subgraph Server["🖥️ Central ATC Server"]
        FDH["Flight Data Hub<br/>전체 비행 상태 집계"]
        Timer["Timer Manager<br/>드론별 허가 시간 관리"]
        Judge["Status Judge<br/>상태 판정 엔진"]

        Judge -->|잔여 > 3분| Green["🟢 NORMAL<br/>정상 비행"]
        Judge -->|잔여 < 2분| Yellow["🟡 WARNING<br/>시간 임박"]
        Judge -->|잔여 = 0| Red["🔴 ALERT<br/>시간 초과"]
    end

    subgraph Notify["📢 User Drone Notification"]
        N_OK["비행 유지 확인<br/>(Heartbeat ACK)"]
        N_WARN["잔여 시간 경고<br/>'2분 남았습니다'"]
        N_EXPIRE["비행 종료 명령<br/>'즉시 복귀하세요'"]
        N_FORCE["긴급 프로토콜<br/>관제 강제 개입"]
    end

    subgraph Feedback["🔄 Feedback Loop"]
        ACK["User Drone → Server<br/>위치 업데이트 / ACK"]
        Reconfig["Server → Swarm<br/>공역 재구성 명령"]
    end

    SwarmLayer -->|"탐지 데이터 전송<br/>(5G / LoRa)"| Detect
    Detect --> FDH
    FDH --> Timer
    Timer --> Judge

    Green --> N_OK
    Yellow --> N_WARN
    Red --> N_EXPIRE
    N_EXPIRE -->|"미응답 30초"| N_FORCE

    N_OK -->|"ACK"| ACK
    N_WARN -->|"ACK"| ACK
    ACK --> FDH
    N_FORCE --> Reconfig
    Reconfig --> SwarmLayer

    style SwarmLayer fill:#1a237e,color:#fff,stroke:#42a5f5,stroke-width:2px
    style Server fill:#0d1b2a,color:#fff,stroke:#00e676,stroke-width:2px
    style Notify fill:#1b0000,color:#fff,stroke:#ff5252,stroke-width:2px
    style Detect fill:#263238,color:#fff,stroke:#80cbc4
    style Feedback fill:#1a1a2e,color:#fff,stroke:#ffd740
    style Green fill:#1b5e20,color:#fff
    style Yellow fill:#e65100,color:#fff
    style Red fill:#b71c1c,color:#fff
```

---

# Summary Slide

## SC2 Swarm Control → Drone ATC: Key Takeaways

| SC2 Component | Drone ATC Equivalent | Transfer Confidence |
|---------------|---------------------|-------------------|
| Blackboard (Central State) | Flight Data Hub | ★★★★★ Direct |
| Boids Algorithm | Formation Flight Control | ★★★★★ Direct |
| Authority Mode (Priority) | ATC Priority Levels | ★★★★★ Direct |
| IntelManager (Scouting) | Sensor Fusion | ★★★★☆ Adapt |
| StrategyManager (FSM) | Route Planning | ★★★★☆ Adapt |
| CreepManager (Territory) | Airspace Corridor | ★★★☆☆ Concept |
| RL Agent (Learning) | Adaptive AI | ★★★★☆ Adapt |
| RuntimeSelfHealing | Fail-Safe System | ★★★★★ Direct |

### Core Insight
> **SC2의 2D 군집 제어 알고리즘은 고도(altitude) 차원만 추가하면**
> **드론 편대 비행의 핵심 제어 로직으로 직접 전이 가능하다.**
>
> 10,000+ 게임의 시뮬레이션 데이터가 실제 드론 ATC의
> 안전성 검증 기반이 된다.

---

> **Rendering**: Use [mermaid.live](https://mermaid.live), GitHub, or VSCode Mermaid plugin.
> **Presentation**: Export diagrams as SVG/PNG for PowerPoint/Keynote slides.
