<div align="center">

# Swarm Control System in StarCraft II

### 멀티 에이전트 드론 군집 연구를 위한 지능형 통합 관제 시스템

**From Simulation to Reality: Reinforcement Learning · Self-Healing DevOps · Mobile GCS**

[![GitHub](https://img.shields.io/badge/GitHub-Swarm--control--in--sc2bot-181717?logo=github)](https://github.com/sun475300-sudo/Swarm-control-in-sc2bot)
[![Python](https://img.shields.io/badge/Python-3.10+-3776AB?logo=python&logoColor=white)](https://python.org)
[![SC2 API](https://img.shields.io/badge/StarCraft%20II-burnysc2-FF6600?logo=data:image/svg+xml;base64,PHN2ZyB4bWxucz0iaHR0cDovL3d3dy53My5vcmcvMjAwMC9zdmciIHdpZHRoPSIyNCIgaGVpZ2h0PSIyNCI+PHRleHQgeT0iMjAiIGZvbnQtc2l6ZT0iMjAiPvCfjq48L3RleHQ+PC9zdmc+)](https://github.com/BurnySc2/python-sc2)
[![PyTorch](https://img.shields.io/badge/PyTorch-RL%20Engine-EE4C2C?logo=pytorch&logoColor=white)](https://pytorch.org)
[![Gemini](https://img.shields.io/badge/Google-Gemini%20AI-4285F4?logo=google&logoColor=white)](https://cloud.google.com/vertex-ai)
[![Files](https://img.shields.io/badge/Python%20Files-541-success)]()
[![Tests](https://img.shields.io/badge/Tests-167%20Passing-brightgreen)]()
[![Bugs Fixed](https://img.shields.io/badge/Bugs%20Fixed-142-critical)]()
[![Coverage](https://img.shields.io/badge/Syntax%20Check-100%25-brightgreen)]()

</div>

---

## Overview

> 이 프로젝트는 **게임이 아닙니다.**
> **Google DeepMind(AlphaStar)** 와 **미국 공군(USAF VISTA X-62A)** 이 실제로 사용하는 방식 그대로,
> 스타크래프트 II를 **드론 군집 제어(Swarm Control)** 실험 환경으로 활용한 연구입니다.

```
실제 드론 50~200대 실험  →  수천만~수억 원
시뮬레이션 기반 실험       →  안전 · 무비용 · 무한 반복
```

---

## System Architecture — Full Stack

```mermaid
graph TB
    subgraph "🖥️ Edge Device — Simulation Server"
        SC2[("⚙️ StarCraft II<br/>Game Engine")]
        BOT{"🤖 Wicked Zerg<br/>AI Bot"}
        SC2 <-->|"burnysc2 API"| BOT
    end

    subgraph "🧠 AI Core — Bot Internal"
        ECO["💰 Economy<br/>Manager"]
        COM["⚔️ Combat<br/>Manager"]
        STR["📋 Strategy<br/>Manager"]
        PRD["🏭 Production<br/>Controller"]
        SCT["👁️ Scouting<br/>System"]
        DEF["🛡️ Defense<br/>Coordinator"]
        INTEL["🔎 Intel<br/>Manager"]
        MICRO["🎯 Advanced Micro<br/>Controller v3"]
        BOT --> ECO & COM & STR & PRD & SCT & DEF & INTEL & MICRO
    end

    subgraph "☁️ Cloud Intelligence — Vertex AI"
        GEM["🔮 Gemini 1.5 Pro"]
        BOT -->|"Traceback + Source"| GEM
        GEM -->|"Self-Healing Patch"| BOT
    end

    subgraph "📱 Remote Monitoring — Mobile GCS"
        DASH["📊 Flask Dashboard"]
        APP["📱 Android App"]
        BOT -->|"Real-time Telemetry"| DASH
        DASH <-->|"WebSocket"| APP
    end

    subgraph "🎓 Training Pipeline"
        RL["🧬 Reinforcement<br/>Learning"]
        IL["📚 Imitation<br/>Learning (Rogue)"]
        MON["📈 Auto Monitor<br/>(1h cycle)"]
        BOT --> RL & IL
        MON -->|"Bug Detection"| BOT
    end

    style SC2 fill:#1a1a2e,stroke:#e94560,color:#fff
    style BOT fill:#0f3460,stroke:#e94560,color:#fff
    style GEM fill:#4285f4,stroke:#fff,color:#fff
    style DASH fill:#16213e,stroke:#0f3460,color:#fff
    style APP fill:#16213e,stroke:#0f3460,color:#fff
    style INTEL fill:#533483,stroke:#fff,color:#fff
    style MICRO fill:#b71540,stroke:#fff,color:#fff
```

---

## Sim-to-Real Mapping

```mermaid
graph LR
    subgraph "🎮 StarCraft II — Virtual"
        A1["🌫️ Fog of War"]
        A2["🐜 200 Units Control"]
        A3["💎 Resource Optimization"]
        A4["🏗️ Build Dedup Logic"]
        A5["⚡ Dynamic Tactics"]
        A6["🔄 Async Concurrency"]
    end

    subgraph "🚁 Real-World Drone — Physical"
        B1["📡 Sensor Uncertainty"]
        B2["🤖 Multi-UAV Swarm"]
        B3["🔋 Battery/Priority Mgmt"]
        B4["🔒 SSoT Integrity"]
        B5["📋 Mission Reallocation"]
        B6["⚡ Real-time C2"]
    end

    A1 -.->|"1:1"| B1
    A2 -.->|"1:1"| B2
    A3 -.->|"1:1"| B3
    A4 -.->|"1:1"| B4
    A5 -.->|"1:1"| B5
    A6 -.->|"1:1"| B6

    style A1 fill:#0f3460,color:#fff
    style A2 fill:#0f3460,color:#fff
    style A3 fill:#0f3460,color:#fff
    style A4 fill:#0f3460,color:#fff
    style A5 fill:#0f3460,color:#fff
    style A6 fill:#0f3460,color:#fff
    style B1 fill:#e94560,color:#fff
    style B2 fill:#e94560,color:#fff
    style B3 fill:#e94560,color:#fff
    style B4 fill:#e94560,color:#fff
    style B5 fill:#e94560,color:#fff
    style B6 fill:#e94560,color:#fff
```

---

## Key Features

### 1) Swarm Reinforcement Learning

```mermaid
graph LR
    STATE["📊 15-D State Vector<br/>전투력 · 적군 · 테크 · 확장"]
    POLICY["🧠 RL Policy Network<br/>Epsilon-Greedy + LR Schedule"]
    ACTION["⚡ Action Output"]

    STATE --> POLICY --> ACTION

    ACTION -->|"공격"| ATK["⚔️ Attack"]
    ACTION -->|"방어"| DEF["🛡️ Defend"]
    ACTION -->|"확장"| EXP["🏗️ Expand"]
    ACTION -->|"테크업"| TECH["🔬 Tech Up"]

    style STATE fill:#2d3436,color:#fff
    style POLICY fill:#6c5ce7,color:#fff
    style ACTION fill:#00b894,color:#fff
    style ATK fill:#d63031,color:#fff
    style DEF fill:#0984e3,color:#fff
    style EXP fill:#fdcb6e,color:#000
    style TECH fill:#a29bfe,color:#fff
```

| 항목 | 세부 사항 |
|------|----------|
| 유닛 수 | 200기 저그 유닛 → 드론 군집 모델링 |
| 상태 표현 | **15차원 벡터** (전투력, 적군 규모, 테크, 확장 등) |
| 전략 전환 | Epsilon-Greedy + Learning Rate Scheduling |
| 모방 학습 | 프로게이머 **이병렬(Rogue)** 리플레이 기반 IL |
| 보상 함수 | 전투 승리 + 자원 효율 + 인구 성장 가중치 |

### 2) Gen-AI Self-Healing DevOps

```mermaid
sequenceDiagram
    participant Bot as 🤖 Bot
    participant Detect as 🔍 Error Detector
    participant Gemini as 🔮 Gemini AI
    participant Patch as 🔧 Auto Patcher
    participant Monitor as 📈 Monitor

    Bot->>Detect: Runtime Error (Traceback)
    Detect->>Gemini: Send traceback + source code
    Gemini->>Gemini: Analyze & generate fix
    Gemini->>Patch: Return patch code
    Patch->>Bot: Apply patch + restart
    Bot->>Monitor: Health check OK
    Monitor-->>Detect: Continue monitoring
    Note over Bot,Monitor: ⏱️ 24/7 무중단 자율 운영
```

### 3) Mobile Ground Control Station (GCS)

```mermaid
graph TB
    subgraph "📱 Mobile GCS Features"
        direction TB
        M1["💎 미네랄/가스 실시간"]
        M2["⚔️ 유닛 생산/전투 현황"]
        M3["📈 승률 그래프"]
        M4["🌡️ CPU 온도/부하"]
        M5["🎮 원격 명령 전송"]
    end

    subgraph "🔐 Connectivity"
        NG["ngrok IoT Tunnel"]
        LTE["LTE/5G Network"]
    end

    M1 & M2 & M3 & M4 & M5 --> NG --> LTE

    style M1 fill:#00b894,color:#fff
    style M2 fill:#d63031,color:#fff
    style M3 fill:#6c5ce7,color:#fff
    style M4 fill:#fdcb6e,color:#000
    style M5 fill:#0984e3,color:#fff
```

---

## Bot Decision Flow — State Machine

```mermaid
stateDiagram-v2
    [*] --> GameStart
    GameStart --> EarlyGame: 0~3분

    state EarlyGame {
        [*] --> WorkerSplit
        WorkerSplit --> ScoutEnemy
        ScoutEnemy --> EarlyDefense: 적 러시 감지
        ScoutEnemy --> EarlyExpand: 안전 확인
    }

    EarlyGame --> MidGame: 3~8분

    state MidGame {
        [*] --> TechChoice
        TechChoice --> RoachHydra: vs Terran Bio
        TechChoice --> MutaLing: vs Protoss Gate
        TechChoice --> LingBane: vs Zerg Pool
        RoachHydra --> AttackOrDefend
        MutaLing --> AttackOrDefend
        LingBane --> AttackOrDefend
    }

    MidGame --> LateGame: 8분+

    state LateGame {
        [*] --> MaxArmy
        MaxArmy --> FinalPush
        FinalPush --> MultiprongAttack
    }

    LateGame --> [*]: GG
```

### on_step() 실행 흐름

```mermaid
flowchart TD
    START(["🎮 on_step() 호출"]) --> SENSE["👁️ 상황 인식<br/>적군 위치 · 자원 · 인구"]
    SENSE --> BLACKBOARD["📋 Blackboard 업데이트<br/>공유 상태 동기화"]
    BLACKBOARD --> INTEL["🔎 Intel 분석<br/>적 빌드 패턴 감지"]
    INTEL --> DECIDE{"🧠 전략 결정"}

    DECIDE -->|"위협 감지"| DEFEND["🛡️ 방어 모드<br/>스파인 건설 · 병력 집결"]
    DECIDE -->|"자원 풍부"| EXPAND["🏗️ 확장 모드<br/>해처리 건설 · 일꾼 생산"]
    DECIDE -->|"병력 우세"| ATTACK["⚔️ 공격 모드<br/>멀티프롱 · 저글링 러시"]
    DECIDE -->|"테크 필요"| TECH["🔬 테크 모드<br/>업그레이드 · 상위 유닛"]

    DEFEND --> MICRO["🎯 마이크로 실행<br/>Stutter Step · Kiting"]
    EXPAND --> MACRO["📊 매크로 실행<br/>일꾼 배분 · 가스 타이밍"]
    ATTACK --> MICRO
    TECH --> MACRO

    MICRO --> EXEC["✅ 유닛 명령 전달<br/>self.bot.do()"]
    MACRO --> EXEC
    EXEC --> END(["⏭️ 다음 프레임"])

    style START fill:#6c5ce7,color:#fff
    style BLACKBOARD fill:#533483,color:#fff
    style INTEL fill:#e17055,color:#fff
    style DECIDE fill:#e17055,color:#fff
    style DEFEND fill:#0984e3,color:#fff
    style EXPAND fill:#00b894,color:#fff
    style ATTACK fill:#d63031,color:#fff
    style TECH fill:#a29bfe,color:#fff
    style EXEC fill:#2d3436,color:#fff
```

---

## Combat Micro System

```mermaid
graph TB
    subgraph "🎯 Advanced Micro Controller v3"
        direction TB
        RAVAGER["💥 Ravager<br/>Corrosive Bile 예측 사격"]
        LURKER["🕳️ Lurker<br/>Burrow 타이밍 최적화"]
        QUEEN["👸 Queen<br/>Transfuse 자동 힐"]
        VIPER["🐍 Viper<br/>Abduct 고가치 타겟"]
        CORRUPTOR["🦅 Corruptor<br/>Caustic Spray 집중"]
        BANELING["💣 Baneling<br/>최적 폭발 위치"]
        MUTA["🦇 Mutalisk<br/>Magic Box + 견제"]
        INFESTOR["🧠 Infestor<br/>Fungal + Neural"]
    end

    subgraph "🔥 Focus Fire Coordinator"
        FF["타겟 집중 사격<br/>Overkill 방지"]
    end

    subgraph "💃 Movement Tactics"
        STUTTER["Stutter Step Kiting"]
        FLANK["Multiprong Flanking"]
        RETREAT["Dynamic Retreat"]
    end

    RAVAGER & LURKER & QUEEN & VIPER & CORRUPTOR & BANELING & MUTA & INFESTOR --> FF
    FF --> STUTTER & FLANK & RETREAT

    style RAVAGER fill:#d63031,color:#fff
    style LURKER fill:#636e72,color:#fff
    style QUEEN fill:#6c5ce7,color:#fff
    style VIPER fill:#00b894,color:#fff
    style BANELING fill:#fdcb6e,color:#000
    style MUTA fill:#0984e3,color:#fff
    style FF fill:#e17055,color:#fff
```

### Counter Unit Matrix

```mermaid
graph LR
    subgraph "🔴 vs Terran"
        T1["Marine/Marauder"] -->|"counter"| TC1["💣 Baneling + 저글링"]
        T2["Siege Tank"] -->|"counter"| TC2["🦇 뮤탈 우회"]
        T3["Battlecruiser"] -->|"counter"| TC3["🦅 Corruptor 집중"]
    end

    subgraph "🔵 vs Protoss"
        P1["Zealot/Stalker"] -->|"counter"| PC1["🐛 바퀴 + 히드라"]
        P2["Void Ray"] -->|"counter"| PC2["🐛 히드라 + 포자"]
        P3["Immortal"] -->|"counter"| PC3["🐜 저글링 물량"]
    end

    subgraph "🟣 vs Zerg"
        Z1["Zergling Rush"] -->|"counter"| ZC1["💣 바네 + 스파인"]
        Z2["Roach/Ravager"] -->|"counter"| ZC2["🐛 히드라 + 럴커"]
    end

    style T1 fill:#d63031,color:#fff
    style P1 fill:#0984e3,color:#fff
    style Z1 fill:#6c5ce7,color:#fff
    style TC1 fill:#00b894,color:#fff
    style PC1 fill:#00b894,color:#fff
    style ZC1 fill:#00b894,color:#fff
```

---

## Intel & Scouting Pipeline

```mermaid
sequenceDiagram
    participant Scout as 👁️ Scout Unit
    participant Intel as 🔎 Intel Manager
    participant BB as 📋 Blackboard
    participant Strategy as 🧠 Strategy
    participant Combat as ⚔️ Combat

    Scout->>Intel: 적 건물/유닛 발견
    Intel->>Intel: 빌드 패턴 분석<br/>(terran_bio / protoss_stargate / ...)
    Intel->>Intel: 위협 수준 판정<br/>(none → light → medium → heavy → critical)
    Intel->>BB: 패턴 + 신뢰도 + 위협 저장
    BB->>Strategy: 전략 결정 요청
    Strategy->>Combat: 카운터 유닛 생산 지시
    Note over Scout,Combat: 실시간 정보 → 즉시 전략 반영
```

```mermaid
pie title 적 빌드 패턴 감지 분류
    "terran_bio (Marine/Marauder)" : 25
    "terran_mech (Tank/Thor)" : 15
    "terran_rush (2Rax 러시)" : 10
    "protoss_stargate (Oracle/Carrier)" : 15
    "protoss_robo (Immortal/Colossus)" : 15
    "protoss_gateway (Zealot/Stalker)" : 10
    "zerg_pool_first (저글링)" : 5
    "zerg_hatch_first (확장)" : 5
```

---

## Module Structure — 541 Python Files

```mermaid
graph TB
    subgraph "📦 wicked_zerg_challenger/ — 541 Python Files"
        MAIN["🤖 wicked_zerg_bot_pro_impl.py<br/><i>메인 봇 엔진</i>"]
        STEP["🔄 bot_step_integration.py<br/><i>on_step 통합 루프</i>"]

        subgraph "🧠 Core Systems"
            CORE["core/<br/>매니저 팩토리·레지스트리"]
            CFG["config/<br/>설정 로더·유닛 설정"]
            CMD["commander/<br/>AI 지휘관 (vLLM/Gemini)"]
        end

        subgraph "⚔️ Combat (12+ modules)"
            CMB["combat/<br/>harassment · baneling<br/>stutter_step · kiting<br/>creep_denial · focus_fire"]
        end

        subgraph "💰 Economy & Production"
            ECO["economy_manager<br/>자원·일꾼 최적화"]
            PRD["production_controller<br/>유닛 생산 큐"]
            RES["resource_manager<br/>가스/미네랄 비율"]
        end

        subgraph "👁️ Intel & Defense"
            SCT["scouting/<br/>정찰 시스템 v2"]
            INTL["intel_manager<br/>적 빌드 분석"]
            DEFS["defense_coordinator<br/>방어 조율"]
            EARLY["early_defense_system<br/>초반 방어"]
        end

        subgraph "🎓 Learning"
            AI["ai/<br/>행동 트리·전략 트리"]
            TRN["local_training/<br/>로컬 훈련"]
            KB["knowledge/<br/>빌드오더 DB (9개)"]
        end

        subgraph "🧪 Tests"
            TST["tests/<br/>314 tests passing<br/>1 skipped"]
        end

        MAIN --> STEP
        STEP --> CORE & CMB & ECO & SCT & DEFS & AI
        CORE --> CFG & CMD
        ECO --> RES
        SCT --> INTL
    end

    style MAIN fill:#e94560,color:#fff
    style STEP fill:#0f3460,color:#fff
    style TST fill:#00b894,color:#fff
```

---

## Engineering Troubleshooting

### 1) `self.bot.do()` 래핑 누락 → 유닛 명령 불발 해결

```mermaid
graph LR
    subgraph "❌ Before — 44건 발견"
        B1["unit.attack(target)"] --> B2["반환값 무시"] --> B3["SC2 엔진 미수신"]
        B3 --> B4["유닛 멈춤<br/>미네랄 축적"]
    end

    subgraph "✅ After — self.bot.do() 래핑"
        A1["result = self.bot.do(<br/>unit.attack(target))"] --> A2["await 체크"] --> A3["SC2 엔진 수신"]
        A3 --> A4["유닛 정상 작동"]
    end

    style B4 fill:#d63031,color:#fff
    style A4 fill:#00b894,color:#fff
```

### 2) `.exists` 가드 누락 → 빈 컬렉션 크래시 방지

```mermaid
graph LR
    subgraph "❌ Before — 6건"
        C1["units.first"] --> C2["units가 비었으면?"] --> C3["💥 IndexError<br/>크래시"]
    end

    subgraph "✅ After — .exists 가드"
        D1["if units.exists:"] --> D2["units.first"] --> D3["안전 접근"]
    end

    style C3 fill:#d63031,color:#fff
    style D3 fill:#00b894,color:#fff
```

### 3) Division by Zero → health_max 가드

```mermaid
graph LR
    subgraph "❌ Before — 3건"
        E1["health / health_max"] --> E2["health_max == 0?"] --> E3["💥 ZeroDivisionError"]
    end

    subgraph "✅ After"
        F1["if health_max > 0:"] --> F2["health / health_max"] --> F3["안전 계산"]
    end

    style E3 fill:#d63031,color:#fff
    style F3 fill:#00b894,color:#fff
```

### 4) Race Condition → 중복 건설 0%

```mermaid
graph LR
    subgraph "❌ Before"
        C1["매니저 A: 산란못 없음!"] --> C3["산란못 x3 건설"]
        C2["매니저 B: 산란못 없음!"] --> C3
    end

    subgraph "✅ After — SSoT"
        D1["매니저 A: 건설 예약 Flag"] --> D3["산란못 x1 건설"]
        D2["매니저 B: Flag 확인 → Skip"] --> D3
    end

    style C3 fill:#d63031,color:#fff
    style D3 fill:#00b894,color:#fff
```

### 5) 미네랄 Overflow → Flush 알고리즘

```mermaid
graph TD
    CHECK{"💎 미네랄 > 500?"}
    CHECK -->|"Yes"| FLUSH["🐜 Emergency Flush Mode<br/>저글링 폭생산"]
    CHECK -->|"No"| NORMAL["📊 Normal Production"]
    FLUSH --> BALANCE["⚖️ 자원 균형 회복"]
    NORMAL --> BALANCE

    style FLUSH fill:#fdcb6e,color:#000
    style BALANCE fill:#00b894,color:#fff
```

---

## Blackboard Architecture — 공유 상태 관리

```mermaid
graph TB
    subgraph "📋 Blackboard (Single Source of Truth)"
        direction LR
        THREAT["threat_level<br/><i>none~critical</i>"]
        PATTERN["enemy_build_pattern<br/><i>terran_bio, protoss_robo...</i>"]
        ARMY["army_supply<br/><i>아군/적군 전투력</i>"]
        ECON["economy_status<br/><i>미네랄/가스/일꾼수</i>"]
        SCOUT["scout_data<br/><i>정찰 결과</i>"]
    end

    INTEL_W["🔎 Intel Manager"] -->|"write"| THREAT & PATTERN
    ECON_W["💰 Economy Manager"] -->|"write"| ECON
    SCOUT_W["👁️ Scout System"] -->|"write"| SCOUT
    COMBAT_W["⚔️ Combat Manager"] -->|"write"| ARMY

    THREAT -->|"read"| STRAT_R["🧠 Strategy"]
    PATTERN -->|"read"| PROD_R["🏭 Production"]
    ARMY -->|"read"| DEF_R["🛡️ Defense"]
    ECON -->|"read"| PROD_R
    SCOUT -->|"read"| STRAT_R

    style THREAT fill:#d63031,color:#fff
    style PATTERN fill:#6c5ce7,color:#fff
    style ARMY fill:#e17055,color:#fff
    style ECON fill:#00b894,color:#fff
    style SCOUT fill:#0984e3,color:#fff
```

---

## Potential Field Navigation

```mermaid
graph TB
    subgraph "🗺️ Potential Field System"
        direction TB
        ALLY["🟢 Ally Units<br/>Weight: 1.0 · Radius: 4.0<br/><i>인력 (Attraction)</i>"]
        ENEMY["🔴 Enemy Units<br/>Weight: 1.4 · Radius: 6.0<br/><i>척력 (Repulsion)</i>"]
        STRUCT["🏗️ Structures<br/>Weight: 6.0 · Radius: 8.0<br/><i>고가치 목표</i>"]
        TERRAIN["🌍 Terrain<br/>Weight: 8.0 · Radius: 5.0<br/><i>지형 장벽</i>"]
        SPLASH["💥 Splash Zone<br/>Weight: 3.0<br/><i>범위 피해 회피</i>"]
    end

    ALLY & ENEMY & STRUCT & TERRAIN & SPLASH --> FIELD["⚡ Combined Field Vector"]
    FIELD --> MOVE["🎯 Optimal Movement Direction"]

    style ALLY fill:#00b894,color:#fff
    style ENEMY fill:#d63031,color:#fff
    style STRUCT fill:#fdcb6e,color:#000
    style TERRAIN fill:#636e72,color:#fff
    style SPLASH fill:#e17055,color:#fff
    style FIELD fill:#6c5ce7,color:#fff
```

---

## Project Stats

```mermaid
pie title 버그 심각도 분포 (누적 103건)
    "CRITICAL" : 1
    "HIGH" : 82
    "MEDIUM" : 14
```

```mermaid
pie title 버그 유형 분포 (103건)
    "self.bot.do() 래핑 누락" : 57
    "빈 컬렉션 .exists 가드" : 10
    "Division by Zero" : 13
    "타입 에러" : 2
    "잘못된 API 구문" : 1
    "로직 에러/충돌" : 14
```

```mermaid
pie title 테스트 결과 (329건)
    "Passed" : 322
    "Skipped" : 7
    "Failed" : 0
```

### Quality Dashboard

| Metric | Value | Status |
|--------|-------|--------|
| Python 파일 수 | 541 | ✅ 전체 구문 검사 통과 |
| 누적 버그 수정 | 103건 (11 세션) | ✅ CRITICAL 0건 잔존 |
| 테스트 스위트 | 322 passed / 0 failed / 7 skipped | ✅ 전체 통과 |
| 빌드오더 | 9개 | ✅ Roach Rush, 12Pool 등 |
| 종족 대응 비율 | 4개 종족 | ✅ Terran, Protoss, Zerg, Random |
| 마이크로 컨트롤러 | 8종 유닛별 전술 | ✅ Ravager, Lurker, Queen, Viper... |
| 자동 모니터링 | 1시간 주기 | ✅ 스케줄 태스크 운영 중 |

### Bug Fix Timeline

```mermaid
gantt
    title 버그 수정 타임라인 (103건)
    dateFormat YYYY-MM-DD
    section Session 1-4
        13건 수정 (CRITICAL 1, HIGH 8, MEDIUM 4)   :done, s1, 2026-03-25, 1d
    section Session 5 — Large Scale
        30건 수정 (HIGH 28, MEDIUM 2)              :done, s5, 2026-03-26, 1d
    section Session 6 — Deep Scan
        17건 수정 (HIGH 16, MEDIUM 1)              :done, s6, 2026-03-26, 1d
    section Session 7 — Logic Inspection
        27건 수정 (do래핑 13 + 0나누기 10 + 가드 4) :done, s7, 2026-03-27, 1d
    section Session 8 — System Conflict
        파괴시스템 4개 충돌 해결 + ZvP 빌드 수정    :done, s8, 2026-03-27, 1d
    section Architecture
        189개 MD 정리 + 대용량 파일 제거            :done, s9, 2026-03-27, 1d
    section Session 9 — Win Rate Fix
        자살공격 방지 + 테크알림 + ZvZ 대응         :done, s10, 2026-03-28, 1d
    section Session 10 — Phase 12
        집결복원 + 폴백전략 + 디컨플릭트 + Hive가속 :done, s11, 2026-03-28, 1d
    section Session 11 — Phase 13
        자동생산 + MicroV3 + 테스트 0건 달성       :done, s12, 2026-03-28, 1d
    section Session 12 — Phase 14
        변이유닛 활성화 + 테크건물 보장 + 동적비율  :done, s13, 2026-03-28, 1d
    section Session 13 — Phase 15
        전투마이크로 강화 + 점진적후퇴 + 포커스파이어 :done, s14, 2026-03-28, 1d
    section Session 14 — Phase 16
        경제최적화 + 66드론컷오프 + 가스밸런스     :done, s15, 2026-03-28, 1d
    section Session 15 — Phase 17
        정찰대응 강화 + 카운터빌드 + 오버로드정찰   :done, s16, 2026-03-28, 1d
    section Session 16 — Phase 18
        맵컨트롤 + 크립교전 + 전진스파인 + 공격크립 :done, s17, 2026-03-28, 1d
    section Session 17 — Phase 19
        후반전환 + 울트라 + 미네랄소비 + 재확장    :done, s18, 2026-03-28, 1d
    section Session 18 — Phase 20
        공격타이밍 + 적약점감지 + 멀티프롱공격     :done, s19, 2026-03-28, 1d
    section Session 19 — Phase 21
        ZvT카운터 + ZvP바이퍼 + ZvZ럴커전환      :done, s20, 2026-03-28, 1d
    section Session 20 — Phase 22
        DeadCode 10대매니저 일괄활성화            :done, s21, 2026-03-28, 1d
    section Session 21 — Phase 23
        퀸인젝트우선 + 오버로드선행생산          :done, s22, 2026-03-28, 1d
    section Monitoring
        자동 모니터링 운영 중                        :active, mon, 2026-03-25, 7d
```

---

## Build Order Database

```mermaid
graph LR
    subgraph "🏗️ 9 Build Orders"
        direction TB
        BO1["🐜 12 Pool Rush<br/><i>초반 저글링 러시</i>"]
        BO2["🐛 Roach Rush<br/><i>바퀴 타이밍 공격</i>"]
        BO3["🏭 Macro Hatch<br/><i>확장 우선</i>"]
        BO4["🦇 Muta Ling Bane<br/><i>뮤탈 견제 + 바네링</i>"]
        BO5["🐍 Hydra Lurker<br/><i>히드라/럴커 조합</i>"]
        BO6["🐛 Roach Hydra<br/><i>바퀴/히드라 올인</i>"]
        BO7["💣 Baneling Bust<br/><i>바네링 벽파괴</i>"]
        BO8["🔬 Lair Tech<br/><i>레어 테크업 빌드</i>"]
        BO9["⚡ Speed Ling<br/><i>스피드 저글링 물량</i>"]
    end

    BO1 & BO2 & BO7 --> AGGRO["🔴 Aggressive"]
    BO3 & BO8 --> MACRO["🟢 Macro"]
    BO4 & BO5 & BO6 & BO9 --> MID["🟡 Midgame"]

    style AGGRO fill:#d63031,color:#fff
    style MACRO fill:#00b894,color:#fff
    style MID fill:#fdcb6e,color:#000
```

---

## Tech Stack

```mermaid
graph LR
    subgraph "🔧 Language & Runtime"
        PY["🐍 Python 3.10+"]
    end

    subgraph "🧠 AI / ML"
        PT["PyTorch"]
        RL["RL Policy Network"]
        IL["Imitation Learning"]
        RPL["SC2 Replay Mining"]
    end

    subgraph "🎮 Simulation"
        SC2["StarCraft II API"]
        BSC["burnysc2"]
    end

    subgraph "☁️ Cloud / DevOps"
        VTX["Vertex AI"]
        GMN["Gemini 1.5 Pro"]
        SH["Self-Healing Pipeline"]
    end

    subgraph "📱 Frontend / GCS"
        FLK["Flask Dashboard"]
        RCT["TypeScript / React"]
        AND["Android App"]
    end

    subgraph "🧪 QA / CI"
        MON["Auto Monitor (1h)"]
        PYC["py_compile Scan"]
        TST["329 Tests"]
    end

    PY --> PT & SC2 & FLK & MON

    style PY fill:#3776AB,color:#fff
    style PT fill:#EE4C2C,color:#fff
    style SC2 fill:#FF6600,color:#fff
    style GMN fill:#4285F4,color:#fff
    style RCT fill:#61DAFB,color:#000
```

| Category | Technology |
|----------|-----------|
| **Language** | Python 3.10+ |
| **AI/ML** | PyTorch, RL Policy Network, Imitation Learning, SC2 Replay Mining |
| **Simulation** | StarCraft II API (burnysc2/python-sc2) |
| **DevOps** | Vertex AI (Gemini) Self-Healing Pipeline |
| **GCS** | Flask Dashboard + TypeScript/React + Android App |
| **Algorithms** | Potential-Field Navigation, Async Concurrency Control |
| **CI/QA** | Auto Monitoring (1h cycle), py_compile full scan, 314+ tests, GitHub Actions CI |

---

## Data Flow — Real-time Processing

```mermaid
graph LR
    subgraph "⏱️ Every Game Frame (~22.4 FPS)"
        FRAME["🎮 Game Frame"] --> OBSERVE["👁️ Observe<br/>Units · Resources · Map"]
        OBSERVE --> CACHE["💾 Data Cache<br/>1s TTL"]
        CACHE --> ANALYZE["🔎 Analyze<br/>Threat · Pattern · Income"]
        ANALYZE --> DECIDE["🧠 Decide<br/>Strategy · Targets"]
        DECIDE --> EXECUTE["⚡ Execute<br/>Unit Commands"]
        EXECUTE --> FRAME
    end

    style FRAME fill:#2d3436,color:#fff
    style OBSERVE fill:#0984e3,color:#fff
    style CACHE fill:#636e72,color:#fff
    style ANALYZE fill:#6c5ce7,color:#fff
    style DECIDE fill:#e17055,color:#fff
    style EXECUTE fill:#00b894,color:#fff
```

---

## Career Roadmap

```mermaid
mindmap
  root((Swarm Control<br/>System))
    UAV/UGV
      자율제어 시스템
      군집 알고리즘
      실시간 C2
      경로 계획
    AI/ML
      Multi-Agent RL
      Imitation Learning
      Strategy Planning
      Behavior Tree
    DevOps/MLOps
      Self-Healing Infra
      Auto Training Pipeline
      Monitoring System
      CI/CD Pipeline
    Robotics
      Swarm Navigation
      Sensor Fusion
      Path Planning
      Formation Control
    Defense/Aerospace
      무인체계 군집 전술
      ISR Mission Planning
      Command & Control
      Anti-Swarm Defense
```

이 프로젝트는 아래 분야와 직접 연결됩니다:

- **UAV/UGV 자율제어 시스템** — 군집 드론 실시간 관제
- **방산 무인체계 군집 알고리즘** — Multi-Agent 전술 의사결정
- **AI/ML Engineer** — 강화학습, 모방학습, 멀티에이전트 AI
- **DevOps/MLOps** — Self-Healing Infrastructure, 자동화 파이프라인
- **로봇/자율주행 C2** — Command & Control 시스템 설계
- **방위산업/항공우주** — ISR 임무 계획, 대군집 방어

---

## Project Metrics Summary

```mermaid
xychart-beta
    title "버그 수정 누적 현황"
    x-axis ["S1-4", "S5", "S6", "S7", "S8", "S9-10", "S11"]
    y-axis "누적 수정 건수" 0 --> 110
    bar [13, 43, 60, 87, 87, 99, 103]
    line [13, 43, 60, 87, 87, 99, 103]
```

```mermaid
xychart-beta
    title "모듈별 코드 규모"
    x-axis ["Combat", "Economy", "AI/Strategy", "Scouting", "Defense", "Core", "Tests"]
    y-axis "파일 수" 0 --> 80
    bar [65, 30, 45, 20, 25, 40, 35]
```

### Win Rate Analysis (100 Games)

```mermaid
pie title 종족별 승률 분석 (100게임)
    "vs Protoss 패배" : 40
    "vs Protoss 승리" : 3
    "vs Terran 패배" : 17
    "vs Terran 승리" : 6
    "vs Zerg 패배" : 29
    "vs Zerg 승리" : 5
```

| 매치업 | 승 | 패 | 승률 | 주요 원인 |
|--------|---|---|------|----------|
| **vs Terran** | 6 | 17 | 26% | Hatch First 전환 적용 |
| **vs Zerg** | 5 | 29 | 15% | ZvZ 카운터 유닛 시스템 추가 |
| **vs Protoss** | 3 | 40 | 7% | DT/Oracle 감지 + 포자 자동건설 |
| **전체** | 14 | 86 | 14% | 집결시스템 복원 + 폴백전략 + 방어디컨플릭트 |

### Recent Architecture Improvements (2026-03-28)

```mermaid
graph LR
    subgraph "🔧 Session 10 — Phase 12 대규모 승률 개선"
        direction TB
        FIX1["🛡️ 공격 집결 복원<br/>즉시공격→70% 집결 후 공격<br/>분할공격 100서플+만 허용"]
        FIX2["🧠 카운터 폴백 전략<br/>정찰 실패 시 종족별<br/>안전 유닛비율 자동 적용"]
        FIX3["⚔️ 방어-공격 디컨플릭트<br/>유닛태그 추적+Blackboard<br/>방어유닛 공격명령 제외"]
        FIX4["📦 서플라이 버퍼 강화<br/>MID 3→8 EARLY 4→6<br/>서플블록 방지"]
        FIX5["🏗️ Hive 8분 완성<br/>인페핏 7분→5분<br/>하이브 7분→6분"]
    end

    subgraph "🔧 Session 11 — Phase 13 실전 검증"
        direction TB
        FIX6["🏭 비율 기반 자동생산<br/>빌드오더 후 unit_ratios<br/>부족 유닛 자동 생산"]
        FIX7["🎯 MicroV3 활성화<br/>8종 유닛 마이크로<br/>초기화 코드 추가"]
        FIX8["✅ 테스트 전체 통과<br/>14 failed → 0 failed<br/>322 passed / 7 skipped"]
    end

    subgraph "🔧 Session 12 — Phase 14 변이유닛 활성화"
        direction TB
        FIX9["🦎 UnitMorphManager 활성화<br/>4종 변이 유닛 시스템<br/>베인/래버저/럴커/브루드로드"]
        FIX10["🏗️ 테크건물 자동보장<br/>Baneling Nest 3분<br/>Lurker Den 7분 자동건설"]
        FIX11["📊 동적 비율 연동<br/>Blackboard unit_ratios<br/>전략→변이비율 실시간 반영"]
    end

    subgraph "🔧 Session 13 — Phase 15 전투 마이크로 강화"
        direction TB
        FIX12["💀 저체력 자동후퇴<br/>HP 30% 이하 유닛<br/>후방 이동 (전멸 방지)"]
        FIX13["🎯 포커스파이어 개선<br/>가장 약한 적 우선 제거<br/>anti-splash 밸런스 조정"]
        FIX14["🏹 원거리 카이팅 강화<br/>히드라 사거리 경계 카이팅<br/>쿨다운 기반 접근/후퇴"]
        FIX15["📉 점진적 후퇴 시스템<br/>1.3x→재집결 1.5x→기지후퇴<br/>2.0x→본진 긴급후퇴"]
    end

    style FIX1 fill:#d63031,color:#fff
    style FIX2 fill:#6c5ce7,color:#fff
    style FIX3 fill:#00b894,color:#fff
    style FIX4 fill:#fdcb6e,color:#000
    style FIX5 fill:#0984e3,color:#fff
    style FIX6 fill:#e17055,color:#fff
    style FIX7 fill:#533483,color:#fff
    style FIX8 fill:#b71540,color:#fff
    style FIX9 fill:#00cec9,color:#000
    style FIX10 fill:#fab1a0,color:#000
    style FIX11 fill:#a29bfe,color:#000
    subgraph "🔧 Session 14 — Phase 16 경제 최적화"
        direction TB
        FIX16["💰 66드론 하드 컷오프<br/>3기지 포화 시 군대 전환<br/>명시적 전환점 설정"]
        FIX17["⛽ 가스 뱅킹 조기감지<br/>500→300 임계값<br/>과잉 자원 방지"]
        FIX18["🏠 매크로 해처리 강화<br/>미네랄 1500→600<br/>라바 부족 즉시 대응"]
    end

    subgraph "🔧 Session 15 — Phase 17 정찰/대응 강화"
        direction TB
        FIX19["⚡ 카운터빌드 속도↑<br/>confidence 0.2→0.1<br/>폴백 3분→2분30초"]
        FIX20["🚨 치즈 즉시 대응<br/>Blackboard 긴급전파<br/>저글링60% 비상비율"]
        FIX21["👁️ 오버로드 정찰 개선<br/>맵센터→적 자연확장<br/>확장여부 즉시 확인"]
        FIX22["🔔 Hidden Tech 경보<br/>DT/공중위협 즉시<br/>스포어/스파인 플래그"]
    end

    subgraph "🔧 Session 16 — Phase 18 맵 컨트롤 시스템"
        direction TB
        FIX23["🟢 크립 위 교전 유도<br/>랠리포인트 크립 우선<br/>45%→25% 스캔"]
        FIX24["🏗️ 전진 스파인 방어<br/>8분+ 3기지+ 크립 위<br/>최대 4개 전진 배치"]
        FIX25["🔥 공격적 크립 확장<br/>적진 75%까지 다단계<br/>종양 릴레이 자동화"]
    end

    subgraph "🔧 Session 17 — Phase 19 후반 전환 시스템"
        direction TB
        FIX26["🦣 HiveTechMaximizer<br/>활성화 (dead code 해결)<br/>울트라/브루드/바이퍼"]
        FIX27["⚔️ 후반 유닛 비율<br/>울트라 20%+ 추가<br/>3종족 모두 업데이트"]
        FIX28["💎 미네랄뱅킹 소비<br/>1500+ 저글링 스팸<br/>800+ 울트라 우선"]
        FIX29["🏠 자동 재확장<br/>기지파괴 시 즉시 재건<br/>2기지 이하 트리거"]
    end

    subgraph "🔧 Session 18 — Phase 20 공격 타이밍 최적화"
        direction TB
        FIX30["📊 점진적 공격 임계값<br/>4분12/8분20/10분30/40<br/>후반 강력 공격"]
        FIX31["🎯 적 약점 감지 공격<br/>확장/테크 중 임계값 70%<br/>타이밍 러시"]
        FIX32["🔱 멀티프롱 공격<br/>80서플+ 저글링 견제팀<br/>확장기지 동시 압박"]
    end

    subgraph "🔧 Session 19 — Phase 21 종족별 특화 대응"
        direction TB
        FIX33["🔵 ZvT 카운터 신규<br/>바이오→바네돌진<br/>메카→레바저담즙<br/>공중→히드라코럽터"]
        FIX34["🟡 ZvP 바이퍼 추가<br/>캐리어 3+→바이퍼<br/>어둠 집어삼키기"]
        FIX35["🟢 ZvZ 럴커 전환<br/>6분+ 로치미러 시<br/>럴커 포지셔닝 우위"]
    end

    subgraph "🔧 Session 20 — Phase 22 Dead Code 일괄 활성화"
        direction TB
        FIX36["💀 10대 매니저 활성화<br/>CreepExpansion/Denial<br/>Spellcaster/Overlord 등"]
        FIX37["🔗 CreepHighway 연결<br/>이름 불일치 수정<br/>기지간 크립 고속도로"]
        FIX38["⚡ 36개 Dead Code 발견<br/>승률 저하 핵심 원인<br/>10개 우선 활성화"]
    end

    style FIX1 fill:#d63031,color:#fff
    style FIX2 fill:#6c5ce7,color:#fff
    style FIX3 fill:#00b894,color:#fff
    style FIX4 fill:#fdcb6e,color:#000
    style FIX5 fill:#0984e3,color:#fff
    style FIX6 fill:#e17055,color:#fff
    style FIX7 fill:#533483,color:#fff
    style FIX8 fill:#b71540,color:#fff
    style FIX9 fill:#00cec9,color:#000
    style FIX10 fill:#fab1a0,color:#000
    style FIX11 fill:#a29bfe,color:#000
    style FIX12 fill:#ff7675,color:#fff
    style FIX13 fill:#74b9ff,color:#000
    style FIX14 fill:#55efc4,color:#000
    style FIX15 fill:#636e72,color:#fff
    style FIX16 fill:#ffeaa7,color:#000
    style FIX17 fill:#dfe6e9,color:#000
    style FIX18 fill:#81ecec,color:#000
    style FIX19 fill:#fd79a8,color:#fff
    style FIX20 fill:#e84393,color:#fff
    style FIX21 fill:#6c5ce7,color:#fff
    style FIX22 fill:#00b894,color:#fff
    style FIX23 fill:#00b894,color:#fff
    style FIX24 fill:#d63031,color:#fff
    style FIX25 fill:#e17055,color:#fff
    style FIX26 fill:#fdcb6e,color:#000
    style FIX27 fill:#0984e3,color:#fff
    style FIX28 fill:#fab1a0,color:#000
    style FIX29 fill:#a29bfe,color:#000
    style FIX30 fill:#ff7675,color:#fff
    style FIX31 fill:#74b9ff,color:#000
    style FIX32 fill:#55efc4,color:#000
    style FIX33 fill:#0984e3,color:#fff
    style FIX34 fill:#fdcb6e,color:#000
    style FIX35 fill:#00b894,color:#fff
    style FIX36 fill:#d63031,color:#fff
    style FIX37 fill:#e17055,color:#fff
    style FIX38 fill:#636e72,color:#fff
```

---

## 한국어 요약 (Korean Summary)

<details>
<summary><b>클릭하여 한국어 설명 보기 / Click to expand Korean description</b></summary>

### 개요

> 이 프로젝트는 **게임이 아닙니다.**
> **Google DeepMind(AlphaStar)** 와 **미국 공군(USAF VISTA X-62A)** 이 실제로 사용하는 방식 그대로,
> 스타크래프트 II를 **드론 군집 제어(Swarm Control)** 실험 환경으로 활용한 연구입니다.

### 주요 기능
1. **지능형 전략 관리**: 종족별 맞춤 빌드오더 (ZvP 로치 러쉬, ZvT 해처리 퍼스트, ZvZ 14풀)
2. **경제 최적화**: 동적 가스 일꾼 관리 (뱅킹 500+ 시 자동 감소), 강제 확장 시스템
3. **고급 전투**: 8종 유닛별 마이크로 (레바저 담즙, 럴커 잠복, 퀸 힐, 살모사 유인)
4. **정찰 시스템 V2**: 동적 주기 (25초~15초), 순찰 경로, 젤나가 감시탑 확보
5. **자가치유 DevOps**: Gemini AI 자동 패치 + 1시간 주기 모니터링

### 승률 분석 (100게임)

| 매치업 | 승률 | 대응 전략 |
|--------|------|----------|
| vs Terran | 26% | Hatch First 16 → 링/바네 전환 |
| vs Zerg | 15% | 14풀 안정 오프닝 |
| vs Protoss | 7% | Roach Rush 타이밍 전환 적용 |

### 최근 개선 (2026-03-28)
- **[Phase 23] 퀸/서플라이 최적화**: 방어 중 인젝트 유지, 오버로드 동적 버퍼(4/6/8/10) 선행생산
- **[Phase 22] Dead Code 일괄 활성화**: 36개 미활성 매니저 발견, 10대 핵심(크립/주술/오버로드 등) 활성화
- **[Phase 21] 종족별 특화 대응**: ZvT 바이오/메카/공중 카운터, ZvP 바이퍼 추가, ZvZ 럴커 전환
- **[Phase 20] 공격 타이밍 최적화**: 점진적 임계값, 적 확장/테크 감지 타이밍공격, 멀티프롱 저글링 견제
- **[Phase 19] 후반 전환 시스템**: HiveTechMaximizer 활성화, 울트라리스크 비율 추가, 미네랄뱅킹 소비, 자동 재확장
- **[Phase 18] 맵 컨트롤 시스템**: 크립 위 교전 유도, 전진 스파인 방어, 공격적 크립 확장
- **[Phase 17] 카운터빌드 속도↑**: confidence 0.2→0.1, 폴백 2분30초, 긴급 Blackboard 전파
- **[Phase 16] 경제 최적화**: 66드론 컷오프, 가스 300 임계값, 매크로해처리 600
- **[Phase 15] 전투 마이크로 강화**: 저HP 자동후퇴, 3단계 점진후퇴, 포커스파이어
- **[Phase 14] 변이유닛 활성화**: 바네링/레바저/럴커/브루드로드 4종 모프 + 동적비율
- **[Phase 13] 자동생산 + MicroV3**: 비율기반 자동생산, AdvancedMicroControllerV3 활성화
- **[Phase 12] 디컨플릭트**: 방어-공격 유닛태그 추적, Blackboard 연동, Hive 가속
- 테스트 167 passed / 0 failed / 20 skipped

### 기술 스택

| 카테고리 | 기술 |
|----------|------|
| **언어** | Python 3.10+ |
| **AI/ML** | PyTorch, RL Policy Network, 모방학습, SC2 리플레이 마이닝 |
| **시뮬레이션** | StarCraft II API (burnysc2/python-sc2) |
| **DevOps** | Vertex AI (Gemini) 자가치유 파이프라인 |
| **GCS** | Flask Dashboard + TypeScript/React + Android App |
| **CI/QA** | GitHub Actions, py_compile, 314+ tests |

### 시뮬레이션-현실 매핑

| StarCraft II (가상) | 실제 드론 (물리) |
|---------------------|-----------------|
| 전장의 안개 | 센서 불확실성 |
| 200기 유닛 제어 | 멀티 UAV 군집 |
| 자원 최적화 | 배터리/우선순위 관리 |
| 동적 전술 전환 | 임무 재할당 |
| 비동기 동시성 | 실시간 C2 |

### 커리어 연결
- **UAV/UGV 자율제어 시스템** — 군집 드론 실시간 관제
- **방산 무인체계 군집 알고리즘** — Multi-Agent 전술 의사결정
- **AI/ML Engineer** — 강화학습, 모방학습, 멀티에이전트 AI
- **DevOps/MLOps** — Self-Healing Infrastructure, 자동화 파이프라인
- **방위산업/항공우주** — ISR 임무 계획, 대군집 방어

</details>

---

## Contact

<div align="center">

**장선우 (Jang Sun Woo)**

Drone Application Engineering

[![Email](https://img.shields.io/badge/Email-sun475300%40naver.com-03C75A?logo=naver&logoColor=white)](mailto:sun475300@naver.com)
[![GitHub](https://img.shields.io/badge/GitHub-sun475300--sudo-181717?logo=github)](https://github.com/sun475300-sudo)

</div>

---

<div align="center">

<sub>Built with Python · StarCraft II API · PyTorch · Gemini AI</sub>

</div>
