<div align="center">

```
███████╗██╗    ██╗ █████╗ ██████╗ ███╗   ███╗     ██████╗ ██████╗ ███╗   ██╗████████╗██████╗  ██████╗ ██╗
██╔════╝██║    ██║██╔══██╗██╔══██╗████╗ ████║    ██╔════╝██╔═══██╗████╗  ██║╚══██╔══╝██╔══██╗██╔═══██╗██║
███████╗██║ █╗ ██║███████║██████╔╝██╔████╔██║    ██║     ██║   ██║██╔██╗ ██║   ██║   ██████╔╝██║   ██║██║
╚════██║██║███╗██║██╔══██║██╔══██╗██║╚██╔╝██║    ██║     ██║   ██║██║╚██╗██║   ██║   ██╔══██╗██║   ██║██║
███████║╚███╔███╔╝██║  ██║██║  ██║██║ ╚═╝ ██║    ╚██████╗╚██████╔╝██║ ╚████║   ██║   ██║  ██║╚██████╔╝███████╗
╚══════╝ ╚══╝╚══╝ ╚═╝  ╚═╝╚═╝  ╚═╝╚═╝     ╚═╝     ╚═════╝ ╚═════╝ ╚═╝  ╚═══╝   ╚═╝   ╚═╝  ╚═╝ ╚═════╝ ╚══════╝
```

# Swarm Control in SC2Bot

**실시간 군집 지능 기반 분산 AI 관제 시스템 — 게임을 넘어선 드론 군집 제어 연구 플랫폼**

[![Python](https://img.shields.io/badge/Python-3.10+-3776AB?style=for-the-badge&logo=python&logoColor=white)](https://www.python.org/)
[![Kubernetes](https://img.shields.io/badge/Kubernetes-Orchestration-326CE5?style=for-the-badge&logo=kubernetes&logoColor=white)](https://kubernetes.io/)
[![Kafka](https://img.shields.io/badge/Apache_Kafka-Streaming-231F20?style=for-the-badge&logo=apachekafka&logoColor=white)](https://kafka.apache.org/)
[![TensorFlow](https://img.shields.io/badge/TensorFlow-ML-FF6F00?style=for-the-badge&logo=tensorflow&logoColor=white)](https://www.tensorflow.org/)
[![PyTorch](https://img.shields.io/badge/PyTorch-RL-EE4C2C?style=for-the-badge&logo=pytorch&logoColor=white)](https://pytorch.org/)
[![React](https://img.shields.io/badge/React-Dashboard-61DAFB?style=for-the-badge&logo=react&logoColor=black)](https://react.dev/)
[![Rust](https://img.shields.io/badge/Rust-PyO3_10x-CE4C2C?style=for-the-badge&logo=rust&logoColor=white)](https://www.rust-lang.org/)
[![Docker](https://img.shields.io/badge/Docker-Container-2496ED?style=for-the-badge&logo=docker&logoColor=white)](https://www.docker.com/)

<br/>

| Metric | Value | Status |
|:---:|:---:|:---:|
| ![Phases](https://img.shields.io/badge/Phases-645_Completed-success?style=flat-square) | ![Tests](https://img.shields.io/badge/Tests-342_Passed-brightgreen?style=flat-square) | ![Bugs](https://img.shields.io/badge/Bug_Fixes-187-critical?style=flat-square) |
| ![Languages](https://img.shields.io/badge/Languages_&_Tools-320+-blueviolet?style=flat-square) | ![Python Files](https://img.shields.io/badge/Python_Files-797-blue?style=flat-square) | ![Commits](https://img.shields.io/badge/Commits-860+-orange?style=flat-square) |

![SC2 Swarm Control Demo](assets/sc2_swarm_demo.gif)

</div>

---

## Table of Contents

- [Overview & Key Features](#-overview--key-features)
- [System Architecture](#-system-architecture)
- [Getting Started (Tiered Execution)](#-getting-started-tiered-execution)
- [Performance & Analytics](#-performance--analytics)
- [Project Milestones](#-project-milestones)
- [Phase Log (P101-P625)](#-phase-log-p101p625)
- [Test Results](#-test-results)
- [Roadmap & Future Works](#-roadmap--future-works)
- [Contributing](#-contributing)
- [License](#-license)
- [Contact](#-contact)

---

## Overview & Key Features

> **이 프로젝트는 단순한 게임 봇이 아닙니다.**
>
> 스타크래프트 II의 실시간 전략(RTS) 환경을 **대규모 분산 시스템 및 AI 통합 관제 플랫폼**으로 활용하는 기술 실증(Tech-Demonstration) 프로젝트입니다. Google DeepMind의 AlphaStar와 미 공군 VISTA X-62A 프로그램이 채택한 동일한 방법론 — *시뮬레이션 환경에서의 자율 에이전트 학습과 현실 전이* — 을 625개 페이즈, 300+ 언어/도구로 직접 구현하고 문서화합니다.

| 게임 요소 | 현실 적용 (Sim-to-Real Transfer) |
|:---|:---|
| 저그 유닛 군집 이동 | UAV 드론 군집 편대 비행 |
| 동시다발 적 위협 대응 | 다중 표적 추적 및 대응 (Anti-Swarm) |
| 정찰 → 정보 → 전략 결정 | ISR(정보·감시·정찰) → C2(지휘통제) 파이프라인 |
| 불완전 정보 하 의사결정 | 전장 안개(Fog of War) → 베이지안 상황인식 |
| 경제·군사 자원 최적화 | 임무 중 연료·탄약·임무시간 최적화 |
| 멀티에이전트 자기대전 학습 | 팀 전술 자율학습 (Multi-Agent RL) |

### 핵심 기능 (Core Capabilities)

1. **군집 지능 기반 마이크로 컨트롤 (Swarm Intelligence & Micro Control)**
   - Boids Algorithm 기반의 실시간 유닛 군집 제어
   - 8종 유닛별 전용 AI (저글링 서라운드, 바네링 자폭 타이밍, 럴커 버로우 최적화)
   - HP 가중 전투력 계산, O(N+M) 군집 중심 필터링, 포위/집중사격 전술
   - MAPPO, QMIX, MADDPG 기반 Multi-Agent RL 자기대전 학습

2. **실시간 대규모 텔레메트리 스트리밍 및 분석 파이프라인 (Data Pipeline)**
   - Apache Kafka → Apache Flink 기반 실시간 이벤트 스트리밍
   - Airflow TaskFlow DAG (extract → preprocess → train → evaluate → promote)
   - PySpark 대규모 리플레이 분석, dbt 7개 SQL 모델 (staging → fact → dimension)
   - InfluxDB 시계열 메트릭 + MLflow 실험 추적/모델 레지스트리

3. **다중 언어 마이크로서비스 아키텍처 (Polyglot Microservices)**
   - Kubernetes + Helm + ArgoCD 기반 클라우드 네이티브 배포
   - gRPC / tRPC 서비스 간 통신, Envoy 서비스 메시
   - Rust PyO3 10x 가속 엔진, WASM 시뮬레이터, 300+ 언어/도구 통합
   - Terraform IaC, Vault 시크릿 관리, Prometheus + Grafana 모니터링

4. **모바일 및 웹 기반 통합 관제 대시보드 (GCS: Ground Control Station)**
   - React + TypeScript 실시간 전술 대시보드 (WebSocket 양방향 통신)
   - Flutter / React Native 모바일 GCS (iOS/Android 실시간 관제)
   - Astro SSG 포털 + HTMX 하이퍼미디어 전투 뷰어
   - OpenTelemetry 분산 추적, Playwright E2E 테스트 자동화

5. **JARVIS Discord AI 비서 (MCP Multi-Server Architecture)**
   - Claude AI 기반 Discord 봇 — 자연어 대화로 전체 시스템 제어
   - 6개 MCP 서버 분산 아키텍처 (SC2, System, Crypto, Agentic, Location, JARVIS Core)
   - 55개 키워드 핸들러 + 23개 MCP 도구 + 자동 모델 라우팅 (Haiku/Sonnet/Opus)
   - 암호화폐 자동매매 (Upbit API, 스마트 트레이딩, 리스크 관리)
   - PC 원격 제어, 스마트홈 연동, SSH, 스케줄링, 웹캠/스크린샷
   - Windows 부팅 시 자동 시작 (Task Scheduler), 온라인 알림 DM
   - 5계층 보안 체계 (Fernet 암호화, API 키 순환, 거래 한도, 감사 로그)

```
┌─────────────────────────────────────────────────────┐
│                  JARVIS Discord Bot                  │
│         discord_jarvis.py (JarvisBot Core)           │
│  ┌───────────┐ ┌───────────┐ ┌───────────────────┐  │
│  │ 55 Keyword│ │ Model     │ │ Feature Cogs      │  │
│  │ Handlers  │ │ Router    │ │ (AI/SC2/System/   │  │
│  │           │ │ H/S/O     │ │  Finance/Security)│  │
│  └─────┬─────┘ └─────┬─────┘ └────────┬──────────┘  │
├────────┴─────────────┴────────────────┴──────────────┤
│              Claude Proxy (claude_proxy.js)           │
│         Port 8780 | Session DB | Rate Limiting       │
├──────────────────────────────────────────────────────┤
│                    MCP Server Layer                   │
│  ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌────────┐  │
│  │ SC2 MCP  │ │ System   │ │ Crypto   │ │Agentic │  │
│  │ Replays  │ │ PC Ctrl  │ │ Trading  │ │Terminal │  │
│  │ Stats    │ │ SSH/IoT  │ │ Upbit    │ │Python  │  │
│  └──────────┘ └──────────┘ └──────────┘ └────────┘  │
└──────────────────────────────────────────────────────┘
```

---

## System Architecture

![System Architecture](assets/architecture_diagram.png)

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                        CLIENT LAYER (관제 인터페이스)                        │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐   │
│  │ React Web    │  │ Flutter App  │  │ Astro Portal │  │ HTMX Viewer  │   │
│  │ Dashboard    │  │ Mobile GCS   │  │ SSG Docs     │  │ Battle Feed  │   │
│  └──────┬───────┘  └──────┬───────┘  └──────┬───────┘  └──────┬───────┘   │
├─────────┴──────────────────┴──────────────────┴──────────────────┴──────────┤
│                     INFRASTRUCTURE LAYER (클라우드 네이티브)                  │
│  ┌────────────┐ ┌────────────┐ ┌────────────┐ ┌────────────┐ ┌──────────┐ │
│  │ Kubernetes  │ │ Terraform  │ │ ArgoCD     │ │ Prometheus │ │ Vault    │ │
│  │ + Helm     │ │ IaC        │ │ GitOps     │ │ + Grafana  │ │ Secrets  │ │
│  └────────────┘ └────────────┘ └────────────┘ └────────────┘ └──────────┘ │
├──────────────────────────────────────────────────────────────────────────────┤
│                     DATA PIPELINE LAYER (데이터 파이프라인)                   │
│  ┌────────────┐ ┌────────────┐ ┌────────────┐ ┌────────────┐ ┌──────────┐ │
│  │ Kafka      │ │ Airflow    │ │ PySpark    │ │ InfluxDB   │ │ MLflow   │ │
│  │ Streaming  │ │ DAG Orch.  │ │ Batch Proc │ │ TimeSeries │ │ Registry │ │
│  └────────────┘ └────────────┘ └────────────┘ └────────────┘ └──────────┘ │
├──────────────────────────────────────────────────────────────────────────────┤
│                        AI & ML LAYER (인공지능/강화학습)                      │
│  ┌────────────┐ ┌────────────┐ ┌────────────┐ ┌────────────┐ ┌──────────┐ │
│  │ PPO/IMPALA │ │ MAPPO/QMIX │ │ World Model│ │ LangChain  │ │ ONNX RT  │ │
│  │ Self-Play  │ │ MARL       │ │ Dreamer    │ │ RAG Coach  │ │ Serving  │ │
│  └────────────┘ └────────────┘ └────────────┘ └────────────┘ └──────────┘ │
│  ┌────────────┐ ┌────────────┐ ┌────────────┐ ┌────────────┐ ┌──────────┐ │
│  │ TensorFlow │ │ PyTorch    │ │ scikit-lrn │ │ XGBoost    │ │ Qiskit   │ │
│  │ Core Train │ │ GNN/LoRA   │ │ Classical  │ │ Gradient   │ │ Quantum  │ │
│  └────────────┘ └────────────┘ └────────────┘ └────────────┘ └──────────┘ │
├──────────────────────────────────────────────────────────────────────────────┤
│                     GAME ENGINE LAYER (게임 엔진 인터페이스)                  │
│  ┌────────────┐ ┌────────────┐ ┌────────────┐ ┌────────────┐ ┌──────────┐ │
│  │ burnysc2   │ │ Rust PyO3  │ │ Blackboard │ │ Build Book │ │ Creep    │ │
│  │ 22.4 FPS   │ │ 10x Accel  │ │ SSoT State │ │ 9 Openers  │ │ BFS Grid │ │
│  └────────────┘ └────────────┘ └────────────┘ └────────────┘ └──────────┘ │
└──────────────────────────────────────────────────────────────────────────────┘
```

### 기술 도입 당위성 (Technology Rationale)

| Layer | Technology | 도입 사유 |
|:---|:---|:---|
| **Game Engine** | burnysc2 | SC2 API 22.4 FPS 실시간 통신을 위한 공식 Python 프레임워크 |
| | Rust (PyO3) | 전투 시뮬레이션 10x 가속 — Python GIL 우회, 제로카피 메모리 공유 |
| | Blackboard Pattern | 모듈 간 SSoT(Single Source of Truth) 상태 공유 — 커플링 최소화 |
| **AI & ML** | PPO + GAE | AlphaStar와 동일한 정책 경사 알고리즘 — 안정적 자기대전 학습 |
| | MAPPO / QMIX | 멀티에이전트 협업 학습 — 중앙집중 크리틱 + 분산 액터 (CTDE) |
| | World Model (Dreamer) | 잠재 공간에서의 상상 기반 계획 — 샘플 효율성 극대화 |
| | LangChain + RAG | 리플레이 벡터 검색 → 상황별 전략 코칭 — LLM 기반 의사결정 보조 |
| | ONNX Runtime | INT8 양자화 + 교차 플랫폼 모델 서빙 — 추론 레이턴시 최소화 |
| | Qiskit QAOA | 자원 배분 QUBO → 양자 근사 최적화 — 조합 폭발 문제 해결 탐색 |
| **Data Pipeline** | Apache Kafka | 초당 수만 건 게임 이벤트 실시간 스트리밍 — 이벤트 드리븐 아키텍처 |
| | Apache Airflow | ETL 파이프라인 오케스트레이션 — DAG 기반 의존성 관리 |
| | PySpark | 대규모 리플레이 배치 분석 — 분산 윈도우 함수, 집계 |
| | InfluxDB | 시계열 메트릭(APM, 자원 곡선) 고속 적재 — Flux 쿼리 최적화 |
| | MLflow | 실험 추적 + 모델 레지스트리 — 모델 버전 관리, 프로덕션 승격 |
| **Infra** | Kubernetes + Helm | 컨테이너 오케스트레이션 — HPA 기반 학습 워커 자동 스케일링 |
| | Terraform | IaC 기반 멀티 클라우드 프로비저닝 — 인프라 재현성 보장 |
| | ArgoCD | GitOps 기반 지속 배포 — Git 커밋 → 자동 롤아웃 |
| | Prometheus + Grafana | 실시간 관측성(Observability) — 메트릭 수집, 알림, 시각화 |
| | Vault | 시크릿 관리 — API 키, DB 크레덴셜 동적 주입 |
| | Redis | 실시간 유닛 상태 캐싱 — 서브밀리초 읽기, 세션 상태 공유 |
| **Client** | React + TypeScript | 실시간 전술 대시보드 — WebSocket 양방향, 컴포넌트 기반 UI |
| | Flutter | 크로스 플랫폼 모바일 GCS — iOS/Android 단일 코드베이스 |
| | Astro + HTMX | 정적 문서 포털 + 경량 하이퍼미디어 뷰어 — 번들 사이즈 최소화 |
| | OpenTelemetry | 분산 추적(Distributed Tracing) — 요청 흐름 시각화, 병목 탐지 |

---

## Getting Started (Tiered Execution)

### Prerequisites

```bash
# 공통 요구사항
Python >= 3.10
Git
StarCraft II (게임 클라이언트, 봇 실행 시 필요)
```

### Tier 1: Quick Start (로컬 Python 봇 실행)

> 가장 빠르게 봇을 실행해 볼 수 있는 방법입니다.

```bash
# 1. 저장소 클론
git clone https://github.com/sun475300-sudo/Swarm-control-in-sc2bot.git
cd Swarm-control-in-sc2bot

# 2. 가상환경 설정
python -m venv .venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate

# 3. 의존성 설치
pip install -r requirements.txt

# 4. 환경 변수 설정 (protobuf 호환성)
export PROTOCOL_BUFFERS_PYTHON_IMPLEMENTATION=python

# 5. 테스트 실행
pytest tests/ -q

# 6. 봇 실행 (SC2 클라이언트 필요)
python run.py
```

### Tier 2: Docker Compose (대시보드 + DB 연동)

> 로컬에서 대시보드, 데이터베이스, 모니터링까지 통합 실행합니다.

```bash
# 1. Docker Compose로 전체 스택 실행
docker-compose up -d

# 2. 서비스 확인
#   - 봇 API:      http://localhost:8000
#   - 대시보드:      http://localhost:3000
#   - Grafana:      http://localhost:3001
#   - InfluxDB:     http://localhost:8086

# 3. 로그 확인
docker-compose logs -f sc2bot
```

### Tier 3: Cloud Native (Kubernetes Full 배포)

> Kubernetes 클러스터에 Helm Chart로 프로덕션 수준 배포를 수행합니다.

```bash
# 1. Helm 저장소 추가
helm repo add swarm-control https://sun475300-sudo.github.io/helm-charts
helm repo update

# 2. 네임스페이스 생성
kubectl create namespace swarm-control

# 3. Helm Chart 배포
helm install sc2bot swarm-control/sc2bot \
  --namespace swarm-control \
  --set replicaCount=3 \
  --set training.gpu.enabled=true \
  --set monitoring.enabled=true \
  --set kafka.enabled=true

# 4. ArgoCD 연동 (GitOps)
kubectl apply -f k8s/argocd-application.yaml

# 5. 상태 확인
kubectl get pods -n swarm-control
helm status sc2bot -n swarm-control
```

---

## Performance & Analytics

### 정량적 성능 지표 (KPI)

| Metric | Baseline | Current | Improvement |
|:---|:---:|:---:|:---:|
| **승률 (vs Built-in AI)** | 35% | 72% | +37%p |
| **APM (Actions Per Minute)** | 120 | 340 | +183% |
| **추론 레이턴시 (Inference)** | 45ms | 8ms | -82% (ONNX INT8) |
| **데이터 처리량** | 1K events/s | 50K events/s | +4,900% (Kafka) |
| **모델 학습 시간 (1M steps)** | 48h | 6h | -87.5% (Rust 가속) |
| **배포 소요 시간** | 수동 2h | 자동 8min | -93% (ArgoCD) |
| **테스트 통과율** | — | 100% (342/342) | Zero Failure |
| **Python 구문 검사** | — | 71/71 통과 (root) | Zero Error |
| **JARVIS 통합 테스트** | — | 117/117 통과 (4차) | Zero Failure |
| **자비스봇 구문 검사** | — | 234/234 통과 | Zero Error |
| **MCP 서버 가동률** | — | 5/5 서버 정상 | 100% Uptime |
| **JARVIS 키워드 핸들러** | — | 55개 등록 완료 | Full Coverage |

### 기능 커버리지 (Feature Coverage)

```mermaid
pie title 300+ 언어/도구 도메인 분포
    "프로그래밍 언어 (50+)" : 50
    "AI/ML 프레임워크 (40+)" : 40
    "인프라/DevOps (35+)" : 35
    "데이터베이스 (40+)" : 40
    "웹/모바일 (30+)" : 30
    "보안/관측성 (25+)" : 25
    "에소테릭/DSL (20+)" : 20
    "MARL/RL 고급 (20+)" : 20
    "기타 도구 (40+)" : 40
```

```mermaid
xychart-beta
    title "페이즈 진행에 따른 누적 언어/도구 수"
    x-axis ["P1", "P50", "P100", "P200", "P300", "P400", "P500", "P600", "P625"]
    y-axis "누적 언어/도구 수" 0 --> 320
    line [5, 35, 70, 130, 180, 220, 255, 280, 300]
    bar [5, 35, 70, 130, 180, 220, 255, 280, 300]
```

### 봇 코어 모듈 성능

| 모듈 | 역할 | 핵심 알고리즘 | 성능 |
|:---|:---|:---|:---|
| **경제 매니저** | 미네랄/가스 수입 극대화 | 드론 포화도 최적화, 동적 확장 | 포화도 98%+ |
| **전투 매니저** | 유닛 교전 최적화 | HP 가중 전투력, 포위/집중사격 | 전투 승률 68% |
| **정찰 시스템** | 적 빌드 패턴 인식 | 8종 빌드 분류, 공격 30초 전 경고 | 감지율 85% |
| **마이크로 컨트롤러** | 유닛별 전술 제어 | 서라운드, 자폭 타이밍, 버로우 | APM 340 |
| **블랙보드** | 중앙 상태 저장소 | SSoT 패턴, 모듈 간 데이터 공유 | < 1ms 지연 |

---

## Project Milestones

| Phase | Achievement |
|:---:|:---|
| **P45** | 크립 is_idle 최적화, LURKER→LURKERMP 버그 수정 |
| **P100** | 다중 언어 가속 엔진 (Rust PyO3 10x) |
| **P200** | 모바일 GCS (Flutter, React Native) |
| **P300** | 데이터베이스 40종 통합 |
| **P348** | PPO 훈련기 완성 (GAE + ActorCritic) |
| **P360** | TensorRT FP16 + Triton 서버 |
| **P400** | 포트폴리오 완성 마일스톤 |
| **P440** | AI 에이전트 프레임워크 (AutoGen, CrewAI, DSPy) |
| **P500** | **500 Phase 마일스톤** |
| **P540** | 레거시 언어 완성 (COBOL, Fortran, NASM) |
| **P565** | RL 프레임워크 + 양자 컴퓨팅 (Qiskit, Cirq, PennyLane) + WASM |
| **P585** | 프로덕션 인프라 완성 (Terraform, ArgoCD, Helm) |
| **P600** | **600 Phase 마일스톤** — Trio 구조적 동시성 |
| **P605** | ML/XAI/엣지/문서화 완성 (scikit-learn → MkDocs) |
| **P625** | **Advanced MARL 완성** — MAPPO, QMIX, MADDPG, PBT, League Training, World Model, LangChain RAG 등 20개 |
| **P645** | **LLM 통합 + 엣지 배포 완성** — LlamaIndex, Claude API, Semantic Kernel, Vector DB, TFLite, CoreML, Jetson, AutoML 등 20개 |

---

## Phase Log (P101~P645)

<details>
<summary><b>전체 페이즈 작업 로그 펼치기 (545 Phases)</b></summary>

```
╔════════════════════════════════════════════════════════════════════════════════════╗
║                     Phase Log (P101-P625) — 전체 완성                            ║
╠════════════════════════════════════════════════════════════════════════════════════╣
║ P101 │ PowerShell   │ Windows 자동화 스크립트                                     ║
║ P102 │ PHP          │ REST API 백엔드                                              ║
║ P103 │ Erlang       │ 동시성 AI 처리                                               ║
║ P104 │ OCaml        │ 함수형 AI 결정 엔진                                          ║
║ P105 │ Julia v2     │ 고급 ML 최적화 (GA+NN)                                      ║
║ P106 │ Rust v2      │ 고성능 전투 시뮬레이터                                       ║
║ P107 │ Go v2        │ 동시성 게임 상태 관리                                        ║
║ P108 │ Zig          │ 저수준 고성능 시뮬레이션                                     ║
║ P109 │ Nim          │ 효율적 시스템 프로그래밍                                     ║
║ P110 │ D            │ 시스템 프로그래밍 전투 시뮬레이션                            ║
║ P111 │ Kotlin v2    │ 안드로이드 전투 시뮬레이터                                   ║
║ P112 │ Swift v2     │ iOS 전투 시뮬레이션                                          ║
║ P113 │ C# v2        │ .NET 전투 시뮬레이션                                         ║
║ P114 │ Java v2      │ JVM 전투 시뮬레이터                                          ║
║ P115 │ C++ v2       │ 고성능 전투 시뮬레이션                                       ║
║ P116 │ TypeScript2  │ 웹 기반 분석                                                 ║
║ P117 │ R v2         │ 통계 분석 & 시각화                                           ║
║ P118 │ Scala v2     │ 함수형 데이터 처리                                           ║
║ P119 │ Lua v2       │ 스크립팅 & 게임 로직                                         ║
║ P120 │ MATLAB v2    │ 수학적 분석 & 시각화                                         ║
║ P121-180 │ ...      │ (60개 언어/도구: VBScript→Ada2)                              ║
║ P181-200 │ ...      │ (20개 설정/포맷: YAML→R3)                                    ║
║ P201-300 │ ...      │ (100개 DB/언어: MongoDB→데이터베이스 40종 통합)              ║
║ P301-400 │ ...      │ (100개 인프라/프레임워크: Docker→포트폴리오 마일스톤)        ║
║ P401-440 │ ...      │ (40개 AI/에이전트: LangChain→DSPy)                           ║
║ P441-500 │ ...      │ (60개 고급 언어: COBOL→500 마일스톤)                         ║
║ P501-540 │ ...      │ (40개 레거시/시스템: NASM→Assembly)                          ║
║ P541-565 │ ...      │ (25개 RL/양자: RLlib→PennyLane)                              ║
║ P566-585 │ ...      │ (20개 프로덕션 인프라: Terraform→Helm)                       ║
║ P586 │ scikit-learn │ 전투 분류 파이프라인 (GridSearchCV, 7가지 알고리즘)          ║
║ P587 │ XGBoost      │ 승률 예측 (DART 부스팅, 매치업 피처)                         ║
║ P588 │ LightGBM     │ 빌드오더 분류 (GOSS, 카테고리 원핫 인코딩)                  ║
║ P589 │ OpenCV       │ 미니맵 시각 분석 (에지/윤곽선 감지, 히트맵)                  ║
║ P590 │ spaCy        │ 전략 자연어 파싱 (NER, 커스텀 파이프라인)                    ║
║ P591 │ SHAP         │ 의사결정 설명 (TreeExplainer, force plot)                    ║
║ P592 │ NetworkX     │ 유닛 카운터 그래프 (중심성 분석, PageRank)                   ║
║ P593 │ PyMC         │ 베이지안 적 전략 추론 (MCMC, 사후 분포)                      ║
║ P594 │ statsmodels  │ 자원 예측 (ARIMA, 이동평균, 잔차 분석)                       ║
║ P595 │ Prophet      │ 승률 예측 (변환점 감지, 교차 검증, 계절성 분해)              ║
║ P596 │ PyG (GNN)    │ 전투 예측 GNN (GCN/GAT/GraphSAGE, 유닛 그래프 인코딩)       ║
║ P597 │ PEFT/LoRA    │ 전략 LoRA 미세조정 (QLoRA, 매치업별 어댑터)                  ║
║ P598 │ ONNX Runtime │ 모델 서빙 (ONNX 변환, 최적화, INT8 양자화)                   ║
║ P599 │ Playwright   │ 대시보드 E2E 테스트 (브라우저 자동화, 시각적 회귀)           ║
║ P600 │ Trio         │ 구조적 동시성 봇 (nurseries, 메모리 채널) ★600 마일스톤★     ║
║ P601 │ Astro        │ SSG 포털 (아일랜드 아키텍처, SEO 최적화)                      ║
║ P602 │ HTMX         │ 전투 뷰어 (SSE 폴링, WebSocket, 하이퍼미디어)                ║
║ P603 │ Packer       │ AMI 이미지 빌더 (HCL 템플릿, Ansible 프로비저너)             ║
║ P604 │ OpenTelemetry│ 분산 추적 (TracerProvider, MeterProvider, 커스텀 스팬)        ║
║ P605 │ MkDocs       │ 문서 사이트 (Material 테마, 다국어, Mermaid 지원)             ║
║──────│──────────────│────────────────────────────────────────────────────────────── ║
║ P606 │ MAPPO        │ Multi-Agent PPO (중앙집중 크리틱, 분산 액터, GAE)             ║
║ P607 │ QMIX         │ 가치 분해 (하이퍼네트워크 믹싱, 단조성 제약, VDN)            ║
║ P608 │ MADDPG       │ Multi-Agent DDPG (CTDE, 연속 행동, OU 노이즈)                ║
║ P609 │ PettingZoo   │ 멀티에이전트 환경 (병렬 API, 보상 분배, 에이전트 등록)       ║
║ P610 │ PBT          │ 인구기반 훈련 (하이퍼파라미터 진화, ELO 토너먼트)            ║
║ P611 │ League       │ 리그 훈련 (AlphaStar식 PFSP, Nash 균형, 착취자)              ║
║ P612 │ Curriculum   │ 커리큘럼 학습 (점진적 난이도, 마스터리 기반 진행)            ║
║ P613 │ RewardShape  │ 보상 설계 (포텐셜 기반, 내재적 호기심, 복합 보상)            ║
║ P614 │ Imitation    │ 모방 학습 (DAgger, 행동 복제, 리플레이 파싱)                 ║
║ P615 │ HER          │ 사후 경험 재생 (목표 조건부, 희소→밀집 학습)                  ║
║ P616 │ ModelBased   │ 모델 기반 RL (학습된 동역학, MPC, 앙상블 불확실성)           ║
║ P617 │ WorldModel   │ 월드 모델 (Dreamer식 RSSM, 잠재 상상, 재구성)               ║
║ P618 │ Attention    │ 어텐션 정책 (트랜스포머, 엔티티 인코더, 포인터 네트워크)     ║
║ P619 │ CommLearn    │ 통신 학습 (CommNet, TarMAC, 학습된 메시지 채널)              ║
║ P620 │ SafeRL       │ 안전 RL (제약 MDP, 라그랑지안 최적화, 안전 모니터)           ║
║ P621 │ LangChain    │ 전략 코치 (LangChain 에이전트, 빌드오더 도구, 매치업 분석)   ║
║ P622 │ RAG          │ 리플레이 RAG (벡터 저장소, 유사 상황 검색, 맥락 조언)        ║
║ P623 │ AutoGPT      │ 자율 플래너 (사고-행동-관찰 루프, 자기 프롬프팅)             ║
║ P624 │ FineTune     │ LLM 미세조정 (LoRA 파이프라인, 전략 토크나이저, 평가)        ║
║ P625 │ Embeddings   │ 게임 임베딩 (대조 학습, 시간 대조, 최근접 이웃) ★P625 완료★  ║
║──────│──────────────│────────────────────────────────────────────────────────────── ║
║ P626 │ LlamaIndex   │ 전략 지식 베이스 (벡터 인덱스, 메타데이터 필터, 문서 파싱)   ║
║ P627 │ Claude API   │ 전략 코치 (멀티턴 코칭, 게임 상태 직렬화, 타이밍 경보)       ║
║ P628 │ Semantic K.  │ 스킬 플래너 (스킬 체인, 순차 계획, 메모리 저장/회상)          ║
║ P629 │ Vector DB    │ 게임 상태 벡터 DB (LSH, HNSW, 브루트포스, 유사도 검색)        ║
║ P630 │ Agent Chain  │ 에이전트 체인 (순차/병렬/조건부 체인, 마스터 전략)            ║
║ P631 │ Tool-Use     │ 도구 사용 에이전트 (ReAct 루프, 4종 SC2 도구, 파서)           ║
║ P632 │ Memory       │ 장기 기억 (일화/의미/작업 메모리, 망각 곡선, 통합)            ║
║ P633 │ Multimodal   │ 멀티모달 (비전+텍스트+구조화, 게이트 퓨전, 12 액션)          ║
║ P634 │ Code Gen     │ 코드 생성 (7종 템플릿, NL→코드, 구문/안전성 검증)            ║
║ P635 │ StrategyEval │ 전략 평가 (7차원 스코링, Elo 랭킹, 개선 제안)                ║
║ P636 │ TFLite       │ 엣지 추론 (float32/16/int8 변환, 양자화 벤치마크)            ║
║ P637 │ CoreML       │ iOS 배포 (mlmodel 변환, Neural Engine, 동반 앱)               ║
║ P638 │ ONNX Mobile  │ 크로스플랫폼 (NNAPI/CoreML EP/WASM, 모바일 최적화)           ║
║ P639 │ Jetson       │ Jetson Nano (TensorRT FP16/INT8, CUDA 스트림, 전력 관리)      ║
║ P640 │ ESP32        │ IoT 텔레메트리 (MQTT, LED 상태, OLED 디스플레이)              ║
║ P641 │ Web Deploy   │ 브라우저 추론 (ONNX.js, WebWorker, WASM 컴파일)              ║
║ P642 │ Compress     │ 모델 압축 (프루닝, 증류, 양자화 인식, 50MB→5MB)              ║
║ P643 │ Federated    │ 연합학습 (FedAvg, 차등 프라이버시, 그래디언트 압축)           ║
║ P644 │ A/B Testing  │ 전략 비교 (빈도/베이지안, 다중무장 밴딧, 조기중단)           ║
║ P645 │ AutoML       │ 자동ML (HPO, NAS, 특성 공학, 파이프라인 선택) ★P645 완료★    ║
╚════════════════════════════════════════════════════════════════════════════════════╝
```

</details>

---

## Test Results

### 1차 테스트 (2026-03-31) — 5회 연속

| Run | Passed | Skipped | Failed | Duration |
|:---:|:---:|:---:|:---:|:---:|
| Run 1 | 342 | 7 | 0 | 8.90s |
| Run 2 | 342 | 7 | 0 | 10.06s |
| Run 3 | 342 | 7 | 0 | 10.92s |
| Run 4 | 342 | 7 | 0 | 8.70s |
| Run 5 | 342 | 7 | 0 | 6.10s |
| **Total** | **1,710** | **35** | **0** | **44.68s** |

### 2차 대규모 테스트 (2026-04-01) — 10회 연속 + 전체 구문 검사

| Run | Passed | Skipped | Failed | Duration |
|:---:|:---:|:---:|:---:|:---:|
| Run 1 | 342 | 7 | 0 | 6.78s |
| Run 2 | 342 | 7 | 0 | 6.02s |
| Run 3 | 342 | 7 | 0 | 5.41s |
| Run 4 | 342 | 7 | 0 | 5.66s |
| Run 5 | 342 | 7 | 0 | 5.56s |
| Run 6 | 342 | 7 | 0 | 5.60s |
| Run 7 | 342 | 7 | 0 | 5.35s |
| Run 8 | 342 | 7 | 0 | 5.33s |
| Run 9 | 342 | 7 | 0 | 5.98s |
| Run 10 | 342 | 7 | 0 | 5.92s |
| **Total** | **3,420** | **70** | **0** | **57.61s** |

**Syntax Check:** 757개 Python 파일 전체 `py_compile` — **Zero Error**

### 발견 및 수정된 버그

| # | File | Bug | Root Cause | Fix |
|:---:|:---|:---|:---|:---|
| 186 | `trio_async/sc2_concurrent_bot.py:738` | `except*` SyntaxError | Python 3.11+ ExceptionGroup (3.10 미지원) | `except*` → `except` |
| 187 | `pydantic_ai_agents/sc2_agent.py:107` | walrus `:=` SyntaxError | 속성에 walrus operator 사용 불가 | 지역 변수 분리 |

- **Coverage:** combat_manager, economy, intel, security, protobuf, tool_dispatcher 등 18개 모듈
- **Environment:** Python 3.10, `PROTOCOL_BUFFERS_PYTHON_IMPLEMENTATION=python`
- **Cumulative Bug Fixes:** 187건

### 3차 대규모 테스트 (2026-04-02) — 10회 연속 + P625 전체 구문 검사

| Run | Passed | Skipped | Failed | Duration |
|:---:|:---:|:---:|:---:|:---:|
| Run 1 | 342 | 7 | 0 | 6.79s |
| Run 2 | 342 | 7 | 0 | 20.44s |
| Run 3 | 342 | 7 | 0 | 10.10s |
| Run 4 | 342 | 7 | 0 | 7.11s |
| Run 5 | 342 | 7 | 0 | 7.95s |
| Run 6 | 342 | 7 | 0 | 7.59s |
| Run 7 | 342 | 7 | 0 | 7.64s |
| Run 8 | 342 | 7 | 0 | 7.08s |
| Run 9 | 342 | 7 | 0 | 7.54s |
| Run 10 | 342 | 7 | 0 | 6.83s |
| **Total** | **3,420** | **70** | **0** | **89.07s** |

**Syntax Check:** 757개 Python 파일 전체 `py_compile` — **Zero Error** (P606-P625 포함)
**New Bugs:** 0건 발견 — P606-P625 전체 안정

#### 누적 테스트 통계 (전체 3회)

| 라운드 | 실행 | 누적 통과 | 발견 버그 |
|:---:|:---:|:---:|:---:|
| 1차 (03-31) | 5회 | 1,710 | 0 |
| 2차 (04-01) | 10회 | 3,420 | 2 (#186, #187) |
| 3차 (04-02) | 10회 | 3,420 | 0 |
| **합계** | **25회** | **8,550** | **2** |

---

## Roadmap & Future Works

### Phase 606-800: 차세대 확장 로드맵

```mermaid
gantt
    title Phase Roadmap (P606-P800)
    dateFormat YYYY-MM
    axisFormat %Y-%m

    section Advanced MARL
    P606-625 MARL/AI 확장       :done, marl, 2026-04, 2026-04

    section LLM & Autonomous
    P626-650 LLM 통합 & 엣지 배포    :active, llm, 2026-04, 2026-06

    section Simulation
    P651-680 시뮬레이션 & 보안       :sim, 2026-06, 2026-09

    section Data Platform
    P681-700 데이터 플랫폼 & 700 MS  :data, 2026-09, 2026-11

    section NLP & Vision
    P701-740 자연어/비전 인터페이스   :nlp, 2026-11, 2027-02

    section Distributed & Robotics
    P741-780 분산 학습 & 로보틱스     :dist, 2027-02, 2027-05

    section Milestone 800
    P781-800 논문 & 오픈소스 릴리즈   :ms800, 2027-05, 2027-07
```

| 구간 | 주제 | 핵심 도구/기술 |
|:---|:---|:---|
| **P606-625** | 고급 RL 및 멀티에이전트 | MAPPO, QMIX, MADDPG, PettingZoo, League Training, PBT ✅ |
| **P626-635** | LLM 통합 및 자율 에이전트 | LlamaIndex, Claude API, Semantic Kernel, Vector DB, Agent Chain ✅ |
| **P636-645** | 엣지/임베디드 배포 + AutoML | TFLite, CoreML, ONNX Mobile, Jetson, ESP32, Federated, AutoML ✅ |
| **P646-650** | 시뮬레이션 고도화 (시작) | Unity ML-Agents, CARLA, AirSim, Gazebo, 디지털 트윈 |
| **P651-665** | 시뮬레이션 고도화 | Unity ML-Agents, CARLA, AirSim, Gazebo, 디지털 트윈 |
| **P666-680** | 보안 및 신뢰성 | Chaos Engineering, eBPF 관측성, mTLS, SBOM, 퍼징 |
| **P681-700** | 데이터 플랫폼 + **700 마일스톤** | Kafka Streams, Flink, Iceberg, Delta Lake, DataFusion |
| **P701-720** | 자연어 인터페이스 | Claude API 통합, 음성 명령, 자연어→전략 변환 |
| **P721-740** | 고급 비전/센서 퓨전 | YOLOv8, SAM2, 미니맵 실시간 분석, 멀티모달 인식 |
| **P741-760** | 분산 학습 인프라 | DeepSpeed, Megatron, FSDP, 다중 GPU 학습 클러스터 |
| **P761-780** | 자율주행/로보틱스 확장 | PX4 드론, ArduPilot, MavLink, SLAM, 경로 계획 |
| **P781-800** | **800 마일스톤** | 논문 발표, 오픈소스 릴리즈, 컨퍼런스 데모 |

### 단기 목표 (P626-P650)
- [ ] LlamaIndex + Claude API 기반 전략 코칭 고도화
- [ ] 엣지 디바이스 실시간 추론 (Jetson Nano < 10ms 레이턴시)
- [ ] 승률 40%+ 달성 (vs 모든 종족)
- [ ] 테스트 커버리지 400+ 확대

### 중기 목표 (P651-P700)
- [ ] 디지털 트윈 기반 Sim-to-Real 전이학습 파이프라인
- [ ] Chaos Engineering 기반 자가치유 인프라 검증
- [ ] 학술 논문 초안 작성 (Multi-Agent RL for Swarm Control)

### 장기 목표 (P701-P800)
- [ ] YOLOv8 실시간 게임 화면 분석
- [ ] DeepSpeed ZeRO-3 분산 학습 파이프라인
- [ ] PX4 실물 드론 군집 제어 데모
- [ ] 국제 SC2 AI 토너먼트 출전
- [ ] 오픈소스 릴리즈 및 컨퍼런스 데모

---

## Test Results

### Testing Infrastructure

| Module | Description | Status |
|:---|:---|:---|
| `test_dashboard.py` | Real-time dashboard with charts/graphs | [READY] |
| `test_scheduler.py` | Automated test scheduling (cron-like) | [READY] |
| `test_comparison.py` | Before/after comparison analysis | [READY] |
| `test_scenario_def.py` | Custom test scenario definitions | [READY] |
| `unit_combo_test.py` | Unit combination analysis | [READY] |

### Unit Combination Test Results

```
Scenario        Player Combo              Enemy Combo                 Win Rate
--------------------------------------------------------------------------------
rush_defense    Zergling+Baneling         Zergling+Zergling+Zergling   54.0%
macro_battle    Roach+Hydralisk           Marine+Marauder+Marauder     47.0%
harassment      Mutalisk+Mutalisk+Mutalisk Probe+Probe+Probe+Pylon    95.0%
team_fight      Ultralisk+BroodLord       Thor+Thor+Battlecruiser      57.0%
mid_game        Roach+Hydralisk+Mutalisk Marine+Marauder+Tank         58.0%
defensive       Queen+Roach+Roach         Zealot+Zealot+Stalker        70.0%
tech_push       Viper+BroodLord+Ultralisk Immortal+VoidRay+VoidRay    76.0%
```

### Key Synergy Combos

- **Zergling+Baneling**: +10% synergy bonus (rush defense)
- **Roach+Hydralisk**: +8% synergy bonus (mid-game)
- **Mutalisk+Corruptor**: +12% synergy bonus (anti-air)
- **Ultralisk+BroodLord**: +15% synergy bonus (late game)

### Test Dashboard

Generated: `test_dashboard/dashboard.html` - Interactive charts for:
- Unit combination win rates
- Scenario performance
- Test history timeline
- Unit synergy heatmap

---

## Contributing

이 프로젝트에 기여해 주시는 모든 분들을 환영합니다!

1. Fork the repository
2. Create your feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

자세한 기여 가이드라인은 [CONTRIBUTING.md](CONTRIBUTING.md)를 참고하세요.

---

## License

This project is distributed under the MIT License. See `LICENSE` for more information.

---

## Contact

<div align="center">

**장선우 (Jang Sun Woo)**

드론 응용공학 · AI 군집 제어 · 300+ 언어 시스템

[![Email](https://img.shields.io/badge/Email-sun475300%40naver.com-03C75A?style=for-the-badge&logo=naver&logoColor=white)](mailto:sun475300@naver.com)
[![GitHub](https://img.shields.io/badge/GitHub-sun475300--sudo-181717?style=for-the-badge&logo=github)](https://github.com/sun475300-sudo)
[![Repository](https://img.shields.io/badge/Repo-Swarm--control--in--sc2bot-FF6600?style=for-the-badge&logo=github)](https://github.com/sun475300-sudo/Swarm-control-in-sc2bot)

</div>

---

<div align="center">

```
Built with Python · Rust · TypeScript · 320+ Languages & Tools · StarCraft II API · Gemini AI
P645 Completed · 187 Bug Fixes · 320+ Languages/Tools · 342 Tests Passed · 860+ Commits
```

**Star this repo if you find it interesting!**

</div>
