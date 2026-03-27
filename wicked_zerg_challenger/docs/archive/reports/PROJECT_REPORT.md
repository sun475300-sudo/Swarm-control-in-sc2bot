# WickedZergBot 프로젝트 보고서

**작성일**: 2026년 01월 28일
**프로젝트**: WickedZergBot (Swarm Control System)

---

## 1. 프로젝트 개요 (Executive Summary)

**WickedZergBot**은 StarCraft II API(python-sc2)를 기반으로 구축된 고성능 인공지능 저그(Zerg) 봇입니다. 
본 프로젝트의 핵심 목표는 단순한 하드코딩 스크립트의 한계를 넘어, **계층적 강화학습(Hierarchical Reinforcement Learning)**과 **데이터 기반(Data-Driven) 전술**을 결합하여, 상황에 유연하게 대처하는 프로급 AI를 구현하는 것입니다.

최근 대규모 리팩토링을 통해 "Split Brain(지휘권 분열)" 문제를 해결하고, **통합 지휘 체계(Unified Command Architecture)**를 완성하여 안정성과 확장성을 비약적으로 높였습니다.

---

## 2. 핵심 목표 (Key Objectives)

1.  **지능형 의사결정 (Intelligent Decision Making)**
    - 규칙(Rule) 기반의 경직된 플레이에서 벗어나, 학습된 모델(RL)을 통해 공격, 확장, 방어 타이밍을 동적으로 결정합니다.
2.  **구조적 안정성 (Architectural Stability)**
    - 유닛 제어 권한을 명확히 분리하여 명령 충돌을 방지하고 코드의 유지보수성을 극대화합니다.
3.  **지식의 데이터화 (Knowledge as Data)**
    - 빌드 오더와 유닛 조합 비율 등을 코드에서 분리하여 JSON 데이터로 관리함으로써, 비개발자도 전략을 수정할 수 있게 합니다.

---

## 3. 시스템 아키텍처 (System Architecture)

봇의 구조는 인체의 신경계와 유사하게 설계되었습니다.

### A. 두뇌: 계층적 강화학습 (Hierarchical RL System)
- **역할**: 전략적 사령관 (Commander)
- **기능**: 게임의 승패에 영향을 미치는 고수준 결정(Attack vs Expand vs Defend)만 수행합니다. 개별 유닛 컨트롤에는 관여하지 않습니다.
- **상태**: 현재 Exploration(탐험) 모드로 초기화되어 실전 데이터를 축적 중입니다.

### B. 신경망: 블랙보드 (Blackboard)
- **역할**: 중앙 정보 공유소 (Central Nervous System)
- **기능**: `IntelManager`(정찰), `EconomyManager`(경제), `DefenseCoordinator`(방어) 등 모든 모듈이 정보를 이곳에 기록하고 공유합니다.
- **효과**: 모듈 간의 직접적인 의존성(Coupling)을 끊어내고 스파게티 코드를 방지합니다.

### C. 손발: 실행 매니저 (Execution Managers)
- **Strategy Manager**: RL의 전략적 결정을 받아 구체적인 명령(전군 이동, 유닛 생산)으로 변환합니다.
- **Defense Coordinator**: 적의 위협 수준을 판단하고 필요한 만큼의 병력만 차출하여 방어합니다.
- **Production Resilience**: 빌드 오더가 막혔을 때 우회로를 찾아 끊김 없는 생산을 보장합니다.

---

## 4. 주요 성과 및 기술적 특징 (Key Achievements)

### 1) 통합 지휘 체계 (Unified Command)
과거 RL과 CombatManager가 동시에 명령을 내려 발생하던 유닛 버벅임 현상을 완벽히 해결했습니다. 이제 RL은 "방향"만 제시하고, 이동과 전투는 CombatManager가 전담합니다.

### 2) MLOps 파이프라인 (Automated Learning)
프로게이머 리플레이를 자동으로 다운로드하고 분석하는 파이프라인을 구축했습니다.
- **50+ 리플레이 학습 완료**: 상위 랭커들의 플레이에서 최적의 드론 비율(59.8%)과 멀티 타이밍(56초)을 추출해 봇에 적용했습니다.

### 3) 데이터 기반 빌드 시스템 (Data-Driven Builds)
`commander_knowledge.json` 파일을 통해 봇의 빌드 오더를 관리합니다. 새로운 빌드(예: 12 Pool)를 추가하려면 코드를 짤 필요 없이 JSON 파일에 몇 줄만 추가하면 됩니다.

---

## 5. 향후 로드맵 (Future Roadmap)

| 단계 | 목표 | 세부 내용 |
| :--- | :--- | :--- |
| **Phase 1** | **기반 구축 (완료)** | 아키텍처 리팩토링, MLOps 파이프라인, 기본 RL 연동 |
| **Phase 2** | **마이크로 고도화** | 잠재력장(Potential Fields) 알고리즘 도입으로 뮤탈/링 산개 컨트롤 구현 |
| **Phase 3** | **자율 학습 확대** | RL Agent가 유닛 생산 비율과 테크 트리 선택까지 직접 학습하도록 권한 확대 |
| **Ultimate**| **인간 초월** | 어떤 종족, 어떤 전략을 상대로도 스스로 파해법을 찾아내는 General AI 달성 |

---

## 6. 결론 (Conclusion)
WickedZergBot은 이제 단순한 스크립트 봇이 아닙니다. **보고 배우고 판단하는 지능형 시스템**으로 진화했습니다. 견고한 아키텍처 위에 쌓아 올린 이 시스템은 앞으로의 학습을 통해 더욱 강력해질 것입니다.
