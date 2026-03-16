# SC2 Zerg Commander Bot - Architecture Visualization

## 1. System Overview

```mermaid
graph TB
    subgraph SC2["StarCraft 2 Engine"]
        GameState["Game State<br/>(Units, Buildings, Resources, Map)"]
        GameOutput["Game Output<br/>(Unit Commands, Abilities)"]
    end

    subgraph Bot["WickedZergBotProImpl"]
        direction TB
        BotMain["on_step()"]
        StepInt["BotStepIntegrator<br/>프레임별 매니저 오케스트레이션"]
    end

    subgraph Core["Core Systems"]
        BB["Blackboard<br/>중앙 게임 상태 허브"]
        MF["ManagerFactory<br/>매니저 초기화"]
        GC["GameConfig<br/>설정 상수"]
    end

    subgraph Managers["Game Managers"]
        Intel["IntelManager<br/>적 정보 수집"]
        Econ["EconomyManager<br/>일꾼/자원/확장"]
        Strat["StrategyManager<br/>전략 선택"]
        Combat["CombatManager<br/>전투 실행"]
        Queen["QueenManager<br/>여왕 관리"]
        Creep["CreepManager<br/>점막 확장"]
        Spell["SpellCasterAutomation<br/>능력 자동 시전"]
        OVL["OverlordVisionNetwork<br/>대군주 시야"]
        Early["EarlyDefenseSystem<br/>초반 방어"]
        Harass["HarassmentExtension<br/>견제"]
    end

    subgraph Learning["Learning & Training"]
        RL["RLAgent (DQN)<br/>강화학습"]
        HRL["HierarchicalRL<br/>계층적 의사결정"]
        Curriculum["CurriculumManager<br/>난이도 진행"]
        HotReload["HotReloader<br/>실시간 모델 교체"]
    end

    subgraph Safety["Error Handling & Self-Healing"]
        ErrH["ErrorHandler<br/>에러 관리"]
        Runtime["RuntimeSelfHealing<br/>자동 복구"]
        GenAI["GenAISelfHealing<br/>AI 코드 패치"]
        Monitor["IntegrationMonitor<br/>시스템 모니터링"]
    end

    GameState --> BotMain
    BotMain --> StepInt
    StepInt --> BB
    MF --> Managers
    GC --> Managers

    BB <--> Intel
    BB <--> Econ
    BB <--> Strat
    BB <--> Combat
    BB <--> Queen
    BB <--> Creep

    Intel --> Strat
    Intel --> Combat
    Intel --> Early
    Econ --> Queen
    Strat --> Combat
    Queen --> Creep

    StepInt --> Spell
    StepInt --> OVL
    StepInt --> Early
    StepInt --> Harass

    Combat --> GameOutput
    Queen --> GameOutput
    Spell --> GameOutput
    Econ --> GameOutput

    RL -.->|shadow learning| StepInt
    HRL -.->|경험 수집| StepInt
    Curriculum -.->|난이도 조절| Bot
    HotReload -.->|모델 교체| RL

    ErrH --> StepInt
    Runtime --> Managers
    GenAI -.->|API 패치| Runtime
    Monitor --> Safety

    style BB fill:#ff9,stroke:#333,stroke-width:3px
    style StepInt fill:#9cf,stroke:#333,stroke-width:2px
    style BotMain fill:#9cf,stroke:#333,stroke-width:2px
    style Combat fill:#f99,stroke:#333
    style Econ fill:#9f9,stroke:#333
    style Intel fill:#fc9,stroke:#333
    style Strat fill:#c9f,stroke:#333
```

---

## 2. Game Loop Sequence (on_step)

```mermaid
sequenceDiagram
    participant SC2 as SC2 Engine
    participant Bot as WickedZergBot
    participant SI as BotStepIntegrator
    participant BB as Blackboard
    participant Intel as IntelManager
    participant Econ as EconomyManager
    participant Strat as StrategyManager
    participant Combat as CombatManager
    participant Queen as QueenManager
    participant Creep as CreepManager
    participant Spell as SpellCaster
    participant OVL as OverlordVision
    participant ED as EarlyDefense

    SC2->>Bot: on_step(iteration)
    Bot->>SI: on_step(iteration)

    Note over SI: Phase 0: State Update
    SI->>BB: update_game_info()
    BB-->>SI: game_phase, game_time

    Note over SI: Phase 1: Intelligence (8프레임마다)
    SI->>Intel: on_step()
    Intel->>BB: update_threat()
    Intel-->>SI: enemy_composition

    Note over SI: Phase 2: Early Defense (0~180초)
    alt game_time < 180s
        SI->>ED: execute()
        ED->>BB: request_production(zergling)
    end

    Note over SI: Phase 3: Economy (4프레임마다)
    SI->>Econ: on_step()
    Econ->>BB: update_resources()
    Econ-->>SI: drone_orders, expansion_plan

    Note over SI: Phase 4: Strategy (22프레임마다)
    SI->>Strat: on_step()
    Strat->>BB: set_authority_mode()
    Strat-->>SI: unit_composition_target

    Note over SI: Phase 5: Combat (2프레임마다)
    SI->>Combat: on_step()
    Combat-->>SC2: unit.attack() / unit.move()

    Note over SI: Phase 6: Queen Management
    SI->>Queen: on_step()
    Queen-->>SC2: inject_larva() / spread_creep()

    Note over SI: Phase 7: Creep (10프레임마다)
    SI->>Creep: on_step()
    Creep-->>SC2: place_tumor()

    Note over SI: Phase 8: Spells (11프레임마다)
    SI->>Spell: on_step()
    Spell-->>SC2: cast_ability()

    Note over SI: Phase 9: Vision
    SI->>OVL: on_step()
    OVL-->>SC2: overlord.move()

    SI-->>Bot: step_complete
    Bot-->>SC2: actions_queued
```

---

## 3. Blackboard Data Flow (Central State Hub)

```mermaid
graph LR
    subgraph Inputs["Data Inputs"]
        GS["Game State<br/>(SC2 API)"]
        Enemy["Enemy Units<br/>(detected)"]
        Resources["Minerals / Gas<br/>/ Supply"]
        Time["Game Time"]
    end

    subgraph BB["Blackboard"]
        direction TB
        Phase["GamePhase<br/>OPENING → EARLY<br/>→ MID → LATE"]
        Auth["AuthorityMode<br/>EMERGENCY / COMBAT<br/>/ ECONOMY / BALANCED"]
        Threat["ThreatInfo<br/>level: NONE~CRITICAL<br/>rush_detected: bool"]
        Units["UnitCounts<br/>current + pending"]
        Res["ResourceState<br/>minerals, gas, supply"]
        Cache["Cache<br/>TTL-based key-value"]
        ProdQ["ProductionQueue<br/>priority-sorted"]
    end

    subgraph Consumers["Data Consumers"]
        C_Intel["IntelManager<br/>reads: units, enemy<br/>writes: threat"]
        C_Econ["EconomyManager<br/>reads: resources, phase<br/>writes: production"]
        C_Strat["StrategyManager<br/>reads: threat, phase<br/>writes: authority"]
        C_Combat["CombatManager<br/>reads: threat, units<br/>writes: commands"]
        C_Queen["QueenManager<br/>reads: units, resources<br/>writes: queen orders"]
        C_Creep["CreepManager<br/>reads: phase, units<br/>writes: tumor positions"]
    end

    GS --> Phase
    GS --> Units
    Enemy --> Threat
    Resources --> Res
    Time --> Phase

    Phase --> C_Econ
    Phase --> C_Strat
    Phase --> C_Creep
    Auth --> C_Econ
    Auth --> C_Combat
    Threat --> C_Strat
    Threat --> C_Combat
    Threat --> C_Queen
    Units --> C_Econ
    Units --> C_Combat
    Res --> C_Econ
    ProdQ --> C_Econ
    Cache --> C_Intel

    C_Intel -->|update_threat| Threat
    C_Econ -->|request_production| ProdQ
    C_Strat -->|set_authority_mode| Auth
    C_Combat -->|update_unit_count| Units

    style BB fill:#fff3cd,stroke:#856404,stroke-width:2px
    style Phase fill:#ffeeba
    style Auth fill:#ffeeba
    style Threat fill:#f8d7da
    style ProdQ fill:#d4edda
```

---

## 4. Authority Mode & Decision Flow

```mermaid
stateDiagram-v2
    [*] --> BALANCED : Game Start

    BALANCED --> ECONOMY : No threats, resources low
    BALANCED --> COMBAT : Medium threat detected
    BALANCED --> EMERGENCY : Rush detected / Critical threat

    ECONOMY --> BALANCED : Drone target reached
    ECONOMY --> COMBAT : Threat escalation
    ECONOMY --> EMERGENCY : Rush detected

    COMBAT --> BALANCED : Threat cleared
    COMBAT --> EMERGENCY : Critical threat
    COMBAT --> ECONOMY : Enemy retreated

    EMERGENCY --> COMBAT : Rush defended
    EMERGENCY --> BALANCED : All clear

    note right of EMERGENCY
        Priority 0 (Highest)
        All resources → defense
        Cancel econ upgrades
        Pull workers if needed
    end note

    note right of COMBAT
        Priority 1
        Army production focus
        Maintain worker count
        Active defense posture
    end note

    note right of ECONOMY
        Priority 3
        Drone saturation focus
        Tech/upgrade priority
        Expansion planning
    end note

    note right of BALANCED
        Priority 2
        50/50 drone:army
        Standard macro cycle
        Default state
    end note
```

---

## 5. Combat System Architecture

```mermaid
graph TB
    subgraph CombatSys["Combat System"]
        direction TB
        CM["CombatManager<br/>전투 총괄"]

        subgraph Micro["Micro Control"]
            Boids["BoidsSwarmControl<br/>군집 이동 알고리즘"]
            Form["FormationTactics<br/>대형 제어"]
            Assign["AssignmentManager<br/>유닛 역할 배정"]
        end

        subgraph Tactics["Tactical Modules"]
            Bane["BanelingTactics<br/>맹독충 돌진"]
            BaneBomb["BanelingBomb<br/>맹독충 투하"]
            Doom["DoomDrop<br/>다방면 공격"]
            Infest["InfestorTactics<br/>감염충 마법"]
        end

        subgraph Defense["Defense"]
            BaseDef["BaseDefense<br/>본진 방어"]
            ExpDef["ExpansionDefense<br/>확장 방어"]
            CreepDen["CreepDenialSystem<br/>적 점막 제거"]
        end

        subgraph Offense["Offense"]
            Attack["AttackController<br/>공격 그룹화"]
            HarassC["HarassmentCoordinator<br/>견제 조율"]
            OVLHunt["OverlordHunter<br/>적 대군주 사냥"]
        end
    end

    CM --> Micro
    CM --> Tactics
    CM --> Defense
    CM --> Offense

    subgraph BoidsDetail["Boids Algorithm"]
        Sep["Separation (1.5)<br/>간격 유지"]
        Ali["Alignment (1.0)<br/>방향 통일"]
        Coh["Cohesion (1.0)<br/>중심 이동"]
        Avoid["Threat Avoidance<br/>위험 회피"]
    end

    Boids --> BoidsDetail

    style CM fill:#f99,stroke:#333,stroke-width:2px
    style Boids fill:#ffb,stroke:#333
    style Sep fill:#fdd
    style Avoid fill:#faa
```

---

## 6. Learning & Training Pipeline

```mermaid
graph TB
    subgraph GameLoop["Game Execution"]
        Play["게임 플레이"]
        Result["게임 결과<br/>승리 +100 / 패배 -100"]
    end

    subgraph RL["Reinforcement Learning"]
        DQN["RLAgent (DQN)<br/>상태 → 행동"]
        PPO["PPOAgent<br/>정책 경사"]
        Reward["RewardSystem<br/>다목적 보상"]
    end

    subgraph HierRL["Hierarchical RL (Shadow Mode)"]
        Macro["Level 1: Macro<br/>빌드오더, 확장"]
        Strategic["Level 2: Strategic<br/>공격 타이밍, 조합"]
        Tactical["Level 3: Tactical<br/>유닛 그룹화"]
        MicroRL["Level 4: Micro<br/>개별 유닛 위치"]
    end

    subgraph Curriculum["Curriculum Learning"]
        L1["Level 1: Easy AI"]
        L2["Level 2: Hard AI"]
        L3["Level 3: Harder AI"]
        L4["Level 4: Very Hard AI"]
        L5["Level 5: CheatInsane AI"]
    end

    subgraph Support["Support Systems"]
        Imitate["ImitationLearner<br/>행동 복제"]
        Fund["FundamentalsManager<br/>빌드오더 학습"]
        Balance["EconomyCombatBalancer<br/>일꾼:군대 비율"]
        Hot["HotReloader<br/>실시간 모델 교체"]
    end

    Play -->|경험 수집| DQN
    Play -->|shadow 관찰| HierRL
    Result -->|보상 계산| Reward
    Reward --> DQN
    Reward --> PPO

    DQN -->|행동 선택| Play
    HierRL -.->|미래 배포| Play

    Result -->|승리 5회| Curriculum
    L1 -->|승급| L2
    L2 -->|승급| L3
    L3 -->|승급| L4
    L4 -->|승급| L5

    Hot -->|30초마다 확인| DQN
    Fund -->|빌드 타이밍| Play
    Balance -->|비율 최적화| Play
    Imitate -->|프로 게이머 학습| DQN

    Macro --> Strategic
    Strategic --> Tactical
    Tactical --> MicroRL

    style DQN fill:#c9f,stroke:#333,stroke-width:2px
    style HierRL fill:#e9e,stroke:#333
    style Curriculum fill:#9fc,stroke:#333
```

---

## 7. Strategy Decision Tree

```mermaid
graph TD
    Start["메시지 수신: on_step()"]
    Phase{"현재 게임 단계?"}
    Threat{"위협 레벨?"}

    Start --> Phase

    Phase -->|OPENING 0~3분| Opening
    Phase -->|EARLY 3~6분| Early
    Phase -->|MID 6~12분| Mid
    Phase -->|LATE 12분+| Late

    subgraph Opening["Opening Phase"]
        O1["13 드론 → 스포닝 풀"]
        O2["17 서플 → 자연 확장"]
        O3["여왕 2기 + 저글링 4~8기"]
    end

    subgraph Early["Early Phase"]
        E1{"적 종족?"}
        E1 -->|테란| ET["뮤탈+바퀴+맹독충"]
        E1 -->|프로토스| EP["히드라+바퀴+점막확장"]
        E1 -->|저그| EZ["저글링+맹독충+뮤탈"]
    end

    Early --> Threat

    Threat -->|CRITICAL| Emergency["EMERGENCY MODE<br/>전 자원 방어 투입"]
    Threat -->|HIGH| Defensive["COMBAT MODE<br/>방어 우선"]
    Threat -->|MEDIUM| Balanced["BALANCED MODE<br/>견제 + 방어"]
    Threat -->|LOW/NONE| Offensive["ECONOMY MODE<br/>확장 + 드론"]

    subgraph Mid["Mid Phase"]
        M1["3확장 포화"]
        M2["업그레이드 시작"]
        M3["조합 전환"]
    end

    subgraph Late["Late Phase"]
        L1["4~5확장"]
        L2["상위 유닛 전환"]
        L3["다방면 공격"]
    end

    style Emergency fill:#f66,color:#fff
    style Defensive fill:#fa0
    style Balanced fill:#ff0
    style Offensive fill:#0f0
```

---

## 8. Error Handling & Self-Healing Flow

```mermaid
graph TB
    Error["에러 발생"]
    Mode{"DEBUG_MODE?"}

    Error --> Mode

    Mode -->|True| Crash["즉시 크래시<br/>(개발 모드)"]
    Mode -->|False| Log["로그 기록 + 계속"]

    Log --> Runtime["RuntimeSelfHealing<br/>자동 감지 (10~30초)"]

    Runtime --> Check1{"경제 정체?"}
    Runtime --> Check2{"생산 중단?"}
    Runtime --> Check3{"자원 낭비?"}
    Runtime --> Check4{"매니저 오류?"}

    Check1 -->|Yes| Fix1["강제 드론 생산"]
    Check2 -->|Yes| Fix2["생산 큐 초기화"]
    Check3 -->|Yes| Fix3["강제 소비 시작"]
    Check4 -->|Yes| Fix4["매니저 리셋"]

    Fix4 --> GenAI{"GenAI 패치 가능?"}
    GenAI -->|Yes| Patch["Gemini API<br/>코드 패치 생성"]
    GenAI -->|No| Manual["수동 복구 필요"]

    Patch --> Validate{"ast.parse 통과?"}
    Validate -->|Yes| Apply["패치 적용"]
    Validate -->|No| Discard["패치 폐기"]

    style Error fill:#f66,color:#fff
    style Crash fill:#f00,color:#fff
    style Runtime fill:#ff9
    style Patch fill:#9cf
    style Apply fill:#9f9
```

---

## 9. File Structure & Module Map

```mermaid
graph LR
    subgraph Root["wicked_zerg_challenger/"]
        Bot["wicked_zerg_bot_pro_impl.py<br/>메인 봇 클래스"]
        Step["bot_step_integration.py<br/>게임 루프 오케스트레이터"]
        BB["blackboard.py<br/>중앙 상태"]
        GC["game_config.py<br/>설정 상수"]
        SM["strategy_manager.py<br/>전략 v1"]
        SM2["strategy_manager_v2.py<br/>전략 v2 (ML)"]
        EM["economy_manager.py<br/>경제 관리"]
        IM["intel_manager.py<br/>정보 수집"]
        QM["queen_manager.py<br/>여왕 관리"]
        CM["creep_manager.py<br/>점막 확장"]
        SC["spellcaster_automation.py<br/>능력 시전"]
        OVL["overlord_vision_network.py<br/>대군주 시야"]
        ED["early_defense_system.py<br/>초반 방어"]
        HE["harassment_extension.py<br/>견제"]
        EH["error_handler.py<br/>에러 처리"]
        RSH["runtime_self_healing.py<br/>자동 복구"]
        GSH["genai_self_healing.py<br/>AI 패치"]
        MI["monitor_integration.py<br/>모니터링"]
    end

    subgraph CoreDir["core/"]
        MF["manager_factory.py<br/>매니저 팩토리"]
    end

    subgraph CombatDir["combat/"]
        Boids["boids_swarm_control.py"]
        CD["creep_denial_system.py"]
        FC["flanking_coordinator.py"]
        CH["creep_highway.py"]
    end

    subgraph TrainDir["local_training/"]
        RLA["rl_agent.py<br/>DQN"]
        PPO["ppo_agent.py<br/>PPO"]
        CurrM["curriculum_manager.py"]
        FM["fundamentals_manager.py"]
        HR["hot_reload.py"]
        TP["training_pipeline.py"]
    end

    subgraph UtilDir["utils/"]
        GConst["game_constants.py"]
        Logger["logger.py"]
        KD["kd_tree.py"]
        SP["spatial_partition.py"]
    end

    Bot --> Step
    Bot --> BB
    Bot --> MF
    Step --> BB
    MF --> EM
    MF --> IM
    MF --> SM
    MF --> QM
    MF --> CM
    Step --> SC
    Step --> OVL
    Step --> ED

    style Bot fill:#9cf,stroke:#333,stroke-width:2px
    style Step fill:#9cf,stroke:#333,stroke-width:2px
    style BB fill:#ff9,stroke:#333,stroke-width:2px
```

---

## 10. Game Phase Timeline

```mermaid
gantt
    title SC2 Game Phase Timeline
    dateFormat mm:ss
    axisFormat %M:%S

    section Game Phases
    OPENING (풀/여왕/저글링)    :opening, 00:00, 03:00
    EARLY (확장/조합 결정)       :early, 03:00, 06:00
    MID (3확장/업그레이드)       :mid, 06:00, 12:00
    LATE (상위유닛/다방면공격)    :late, 12:00, 20:00

    section Key Timings
    13 드론 → 스포닝 풀          :milestone, 01:30, 0
    17 서플 → 자연 확장          :milestone, 02:00, 0
    저글링 4기 생산              :milestone, 02:00, 0
    저글링 8기 + 여왕 2기        :milestone, 03:00, 0
    3번째 확장                   :milestone, 04:30, 0
    업그레이드 시작              :milestone, 06:00, 0
    4번째 확장                   :milestone, 08:00, 0

    section Update Intervals
    IntelManager (8프레임)       :active, 00:00, 20:00
    EconomyManager (4프레임)     :active, 00:00, 20:00
    CombatManager (2프레임)      :active, 00:00, 20:00
    StrategyManager (22프레임)   :active, 00:00, 20:00
    CreepManager (10프레임)      :active, 00:00, 20:00
    SpellCaster (11프레임)       :active, 00:00, 20:00
```

---

## 11. Unit Production Priority (Authority-Based)

```mermaid
graph TD
    subgraph Authority["Authority Mode Priority"]
        direction LR
        P0["Priority 0<br/>EMERGENCY"]
        P1["Priority 1<br/>COMBAT"]
        P2["Priority 2<br/>STRATEGY"]
        P3["Priority 3<br/>ECONOMY"]
    end

    P0 --> |최우선| EmUnits["스파인/스포어<br/>저글링 긴급 생산<br/>일꾼 징집"]
    P1 --> |높음| CombatUnits["바퀴/히드라/뮤탈<br/>맹독충/울트라"]
    P2 --> |보통| StratUnits["업그레이드<br/>테크 건물<br/>조합 전환"]
    P3 --> |낮음| EconUnits["드론 생산<br/>확장<br/>대군주"]

    subgraph Queue["Production Queue"]
        Q1["큐 1: EMERGENCY 요청"]
        Q2["큐 2: COMBAT 요청"]
        Q3["큐 3: STRATEGY 요청"]
        Q4["큐 4: ECONOMY 요청"]
    end

    EmUnits --> Q1
    CombatUnits --> Q2
    StratUnits --> Q3
    EconUnits --> Q4

    Q1 -->|먼저 실행| Larva["라바 할당"]
    Q2 -->|다음| Larva
    Q3 -->|그 다음| Larva
    Q4 -->|마지막| Larva

    style P0 fill:#f66,color:#fff
    style P1 fill:#fa0
    style P2 fill:#ff0
    style P3 fill:#0f0
```

---

## Component Summary Table

| Component | File | Role | Update Interval |
|-----------|------|------|-----------------|
| **Blackboard** | `blackboard.py` | Central state hub | Every frame |
| **BotStepIntegrator** | `bot_step_integration.py` | Frame orchestrator | Every frame |
| **ManagerFactory** | `core/manager_factory.py` | Manager initialization | Game start |
| **IntelManager** | `intel_manager.py` | Enemy tracking | 8 frames |
| **EconomyManager** | `economy_manager.py` | Workers/supply/expansion | 4 frames |
| **StrategyManager** | `strategy_manager.py` | Strategy selection | 22 frames |
| **CombatManager** | Combat modules | Battle execution | 2 frames |
| **QueenManager** | `queen_manager.py` | Queen production/inject | Every frame |
| **CreepManager** | `creep_manager.py` | Creep spread | 10 frames |
| **SpellCaster** | `spellcaster_automation.py` | Auto-abilities | 11 frames |
| **EarlyDefense** | `early_defense_system.py` | Rush defense | Every frame (0~180s) |
| **OverlordVision** | `overlord_vision_network.py` | Map vision | Periodic |
| **RLAgent** | `local_training/rl_agent.py` | Decision ML | Per episode |
| **CurriculumManager** | `local_training/curriculum_manager.py` | Difficulty progression | Per game |
| **RuntimeSelfHealing** | `runtime_self_healing.py` | Auto-recovery | 10~30s |

---

> This document uses Mermaid diagrams for visualization.
> Render in any Mermaid-compatible viewer (GitHub, VSCode Mermaid plugin, mermaid.live).
