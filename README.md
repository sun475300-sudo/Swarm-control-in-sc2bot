<div align="center">

# Swarm Control System in StarCraft II

### 멀티 에이전트 드론 군집 연구를 위한 지능형 통합 관제 시스템

**From Simulation to Reality: Reinforcement Learning · Self-Healing DevOps · Mobile GCS**

[![GitHub](https://img.shields.io/badge/GitHub-Swarm--control--in--sc2bot-181717?logo=github)](https://github.com/sun475300-sudo/Swarm-control-in-sc2bot)
[![Python](https://img.shields.io/badge/Python-3.10+-3776AB?logo=python&logoColor=white)](https://python.org)
[![SC2 API](https://img.shields.io/badge/StarCraft%20II-burnysc2-FF6600?logo=data:image/svg+xml;base64,PHN2ZyB4bWxucz0iaHR0cDovL3d3dy53My5vcmcvMjAwMC9zdmciIHdpZHRoPSIyNCIgaGVpZ2h0PSIyNCI+PHRleHQgeT0iMjAiIGZvbnQtc2l6ZT0iMjAiPvCfjq48L3RleHQ+PC9zdmc+)](https://github.com/BurnySc2/python-sc2)
[![PyTorch](https://img.shields.io/badge/PyTorch-RL%20Engine-EE4C2C?logo=pytorch&logoColor=white)](https://pytorch.org)
[![Gemini](https://img.shields.io/badge/Google-Gemini%20AI-4285F4?logo=google&logoColor=white)](https://cloud.google.com/vertex-ai)
[![Files](https://img.shields.io/badge/Python%20Files-362-success)]()
[![Bugs Fixed](https://img.shields.io/badge/Bugs%20Fixed-13-critical)]()
[![Tests](https://img.shields.io/badge/Tests-All%20Passing-brightgreen)]()

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

## System Architecture

```mermaid
graph TB
    subgraph "🖥️ Edge Device — Simulation Server"
        SC2[("⚙️ StarCraft II<br/>Game Engine")]
        BOT{"🤖 Wicked Zerg<br/>AI Bot"}
        SC2 <-->|"API"| BOT
    end

    subgraph "🧠 AI Core — Bot Internal"
        ECO["💰 Economy<br/>Manager"]
        COM["⚔️ Combat<br/>Manager"]
        STR["📋 Strategy<br/>Manager"]
        PRD["🏭 Production<br/>Controller"]
        SCT["👁️ Scouting<br/>System"]
        DEF["🛡️ Defense<br/>Coordinator"]
        BOT --> ECO & COM & STR & PRD & SCT & DEF
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
    end

    subgraph "🚁 Real-World Drone — Physical"
        B1["📡 Sensor Uncertainty"]
        B2["🤖 Multi-UAV Swarm"]
        B3["🔋 Battery/Priority Mgmt"]
        B4["🔒 SSoT Integrity"]
        B5["📋 Mission Reallocation"]
    end

    A1 -.->|"1:1"| B1
    A2 -.->|"1:1"| B2
    A3 -.->|"1:1"| B3
    A4 -.->|"1:1"| B4
    A5 -.->|"1:1"| B5

    style A1 fill:#0f3460,color:#fff
    style A2 fill:#0f3460,color:#fff
    style A3 fill:#0f3460,color:#fff
    style A4 fill:#0f3460,color:#fff
    style A5 fill:#0f3460,color:#fff
    style B1 fill:#e94560,color:#fff
    style B2 fill:#e94560,color:#fff
    style B3 fill:#e94560,color:#fff
    style B4 fill:#e94560,color:#fff
    style B5 fill:#e94560,color:#fff
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

    style STATE fill:#2d3436,color:#fff
    style POLICY fill:#6c5ce7,color:#fff
    style ACTION fill:#00b894,color:#fff
    style ATK fill:#d63031,color:#fff
    style DEF fill:#0984e3,color:#fff
    style EXP fill:#fdcb6e,color:#000
```

| 항목 | 세부 사항 |
|------|----------|
| 유닛 수 | 200기 저그 유닛 → 드론 군집 모델링 |
| 상태 표현 | **15차원 벡터** (전투력, 적군 규모, 테크, 확장 등) |
| 전략 전환 | Epsilon-Greedy + Learning Rate Scheduling |
| 모방 학습 | 프로게이머 **이병렬(Rogue)** 리플레이 기반 IL |

### 2) Gen-AI Self-Healing DevOps

```mermaid
sequenceDiagram
    participant Bot as 🤖 Bot
    participant Detect as 🔍 Error Detector
    participant Gemini as 🔮 Gemini AI
    participant Patch as 🔧 Auto Patcher

    Bot->>Detect: Runtime Error (Traceback)
    Detect->>Gemini: Send traceback + source code
    Gemini->>Gemini: Analyze & generate fix
    Gemini->>Patch: Return patch code
    Patch->>Bot: Apply patch + restart
    Note over Bot,Patch: ⏱️ 24/7 무중단 자율 운영
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

## Module Structure

```mermaid
graph TB
    subgraph "📦 wicked_zerg_challenger/ — 362 Python Files"
        MAIN["🤖 wicked_zerg_bot_pro_impl.py<br/><i>메인 봇 엔진</i>"]
        STEP["🔄 bot_step_integration.py<br/><i>on_step 통합 루프</i>"]

        subgraph "🧠 Core Systems"
            CORE["core/<br/>매니저 팩토리·레지스트리"]
            CFG["config/<br/>설정 로더·유닛 설정"]
            CMD["commander/<br/>AI 지휘관 (vLLM/Gemini)"]
        end

        subgraph "⚔️ Combat (12+ modules)"
            CMB["combat/<br/>harassment · baneling<br/>stutter_step · kiting"]
        end

        subgraph "💰 Economy & Production"
            ECO["economy/<br/>자원·일꾼 최적화"]
            PRD["production/<br/>생산 컨트롤러"]
        end

        subgraph "👁️ Intel & Defense"
            SCT["scouting/<br/>정찰 시스템"]
            DEF["defense/<br/>방어 조율"]
        end

        subgraph "🎓 Learning"
            AI["ai/<br/>행동 트리·전략 트리"]
            TRN["local_training/<br/>로컬 훈련"]
            KB["knowledge/<br/>빌드오더 DB (9개)"]
        end

        MAIN --> STEP
        STEP --> CORE & CMB & ECO & SCT & DEF & AI
        CORE --> CFG & CMD
    end

    style MAIN fill:#e94560,color:#fff
    style STEP fill:#0f3460,color:#fff
```

---

## Bot Decision Flow

```mermaid
flowchart TD
    START(["🎮 on_step() 호출"]) --> SENSE["👁️ 상황 인식<br/>적군 위치 · 자원 · 인구"]
    SENSE --> DECIDE{"🧠 전략 결정"}

    DECIDE -->|"위협 감지"| DEFEND["🛡️ 방어 모드<br/>스파인 건설 · 병력 집결"]
    DECIDE -->|"자원 풍부"| EXPAND["🏗️ 확장 모드<br/>해처리 건설 · 일꾼 생산"]
    DECIDE -->|"병력 우세"| ATTACK["⚔️ 공격 모드<br/>멀티프롱 · 저글링 러시"]

    DEFEND --> MICRO["🎯 마이크로 실행"]
    EXPAND --> MACRO["📊 매크로 실행"]
    ATTACK --> MICRO

    MICRO --> EXEC["✅ 유닛 명령 전달<br/>self.bot.do()"]
    MACRO --> EXEC
    EXEC --> END(["⏭️ 다음 프레임"])

    style START fill:#6c5ce7,color:#fff
    style DECIDE fill:#e17055,color:#fff
    style DEFEND fill:#0984e3,color:#fff
    style EXPAND fill:#00b894,color:#fff
    style ATTACK fill:#d63031,color:#fff
    style EXEC fill:#2d3436,color:#fff
```

---

## Engineering Troubleshooting

### 1) `await` 누락 → 생산 마비 해결

```mermaid
graph LR
    subgraph "❌ Before"
        B1["larva.train() 호출"] --> B2["await 누락!"] --> B3["SC2 엔진 무시"]
        B3 --> B4["미네랄 8000+<br/>병력 0"]
    end

    subgraph "✅ After"
        A1["await larva.train()"] --> A2["SC2 엔진 수신"] --> A3["생산 정상화"]
        A3 --> A4["생산 성능<br/>400% 상승"]
    end

    style B4 fill:#d63031,color:#fff
    style A4 fill:#00b894,color:#fff
```

### 2) Race Condition → 중복 건설 0%

```mermaid
graph LR
    subgraph "❌ Before"
        C1["매니저 A: 산란못 없음!"] --> C3["산란못 x3 건설"]
        C2["매니저 B: 산란못 없음!"] --> C3
    end

    subgraph "✅ After — SSoT"
        D1["매니저 A: 건설 예약 Flag ✓"] --> D3["산란못 x1 건설"]
        D2["매니저 B: Flag 확인 → Skip"] --> D3
    end

    style C3 fill:#d63031,color:#fff
    style D3 fill:#00b894,color:#fff
```

### 3) 미네랄 Overflow → Flush 알고리즘

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

## Project Stats

```mermaid
pie title 버그 심각도 분포 (누적 13건)
    "CRITICAL" : 1
    "HIGH" : 8
    "MEDIUM" : 4
```

```mermaid
pie title 버그 유형 분포
    "빈 컬렉션 .first 크래시" : 4
    "self.bot.do() 래핑 누락" : 5
    "Division by Zero" : 2
    "잘못된 API 구문" : 1
    "타입 에러" : 1
```

### Quality Dashboard

| Metric | Value | Status |
|--------|-------|--------|
| Python 파일 수 | 362 | ✅ 전체 구문 검사 통과 |
| 누적 버그 수정 | 13건 | ✅ CRITICAL 0건 잔존 |
| 테스트 스위트 | 3개 통과 | ✅ bot_init, strategy, knowledge |
| 빌드오더 | 9개 | ✅ Roach Rush, 12Pool 등 |
| 종족 대응 비율 | 4개 종족 | ✅ Terran, Protoss, Zerg, Random |
| 검증 완료 모듈 | 100% | ✅ core, combat, economy, scouting, defense 전체 |
| 자동 모니터링 | 1시간 주기 | ✅ 스케줄 태스크 운영 중 |

### Bug Fix Timeline

```mermaid
gantt
    title 버그 수정 타임라인
    dateFormat YYYY-MM-DD
    section Session 1
        4건 수정 (CRITICAL 1, HIGH 2, MEDIUM 1)   :done, s1, 2026-03-25, 1d
    section Session 2
        2건 수정 (HIGH 2)                          :done, s2, 2026-03-25, 1d
    section Session 3
        3건 수정 (HIGH 2, MEDIUM 1)                :done, s3, 2026-03-26, 1d
    section Session 4
        4건 수정 (HIGH 2, MEDIUM 2)                :done, s4, 2026-03-26, 1d
    section Monitoring
        자동 모니터링 운영 중                        :active, mon, 2026-03-26, 7d
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
        TST["36+ Tests"]
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
| **CI/QA** | Auto Monitoring (1h cycle), py_compile full scan, 36+ tests |

---

## Career Roadmap

```mermaid
mindmap
  root((Swarm Control<br/>System))
    UAV/UGV
      자율제어 시스템
      군집 알고리즘
      실시간 C2
    AI/ML
      Multi-Agent RL
      Imitation Learning
      Strategy Planning
    DevOps/MLOps
      Self-Healing Infra
      Auto Training Pipeline
      Monitoring System
    Robotics
      Swarm Navigation
      Sensor Fusion
      Path Planning
```

이 프로젝트는 아래 분야와 직접 연결됩니다:

- **UAV/UGV 자율제어 시스템** — 군집 드론 실시간 관제
- **방산 무인체계 군집 알고리즘** — Multi-Agent 전술 의사결정
- **AI/ML Engineer** — 강화학습, 모방학습, 멀티에이전트 AI
- **DevOps/MLOps** — Self-Healing Infrastructure, 자동화 파이프라인
- **로봇/자율주행 C2** — Command & Control 시스템 설계

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
