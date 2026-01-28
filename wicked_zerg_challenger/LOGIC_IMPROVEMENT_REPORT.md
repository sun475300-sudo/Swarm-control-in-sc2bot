# WickedZergBot 로직 발전 보고서 (Past, Present, and Future)

본 보고서는 WickedZergBot의 초기 로직부터 현재의 아키텍처, 그리고 향후 계획된 로직의 진화 과정을 정리합니다.

---

## 1. 과거 (The Past): 분산 제어와 혼란

### 구조: 분산된 제어 (Decentralized Control)
초기 버전의 봇은 여러 매니저(Manager)들이 각자의 판단하에 독립적으로 행동하는 구조였습니다.
- **StrategyManager**: 빌드 오더와 거시적 전략 담당.
- **CombatManager**: 전투 유닛 컨트롤 담당.
- **ProductionManager**: 유닛 생산 담당.

### ⚠️ 주요 문제점: "Split Brain" (분열된 두뇌)
가장 큰 문제는 **권한의 중복**이었습니다.
1.  **명령 충돌**: `HierarchicalRLSystem`(강화학습)이 유닛에게 "공격" 명령을 내리는 동시에, `CombatManager`가 "후퇴" 명령을 내리는 현상이 발생했습니다. 이로 인해 유닛이 제자리에서 버벅거리는(Stuttering) 문제가 있었습니다.
2.  **하드코딩된 지식**: 모든 빌드 오더와 전략이 Python 코드 내에 하드코딩되어 있어, 전략 수정 시 코드를 직접 고쳐야 했습니다.
3.  **방어 로직 분산**: 긴급 방어 로직이 여러 곳에 흩어져 있어, 위기 상황에서 우선순위가 뒤엉켰습니다.

---

## 2. 현재 (The Present): 통합된 지휘와 효율화 (구현 완료)

최근 업데이트를 통해 다음과 같은 아키텍처로 진화했습니다.

### A. 지휘권 통합 (Unified Command Authority)
"Split Brain" 문제를 해결하기 위해 지휘 체계를 **두뇌(Decision Maker)**와 **손발(Executor)**로 명확히 분리했습니다.
- **RL Agent ("Brain")**: 오직 **"전략 모드(Attack/Expand/Defend)"**만 결정합니다. 유닛을 직접 건드리지 않습니다.
- **Strategy Manager ("Executor")**: RL의 결정을 받아 구체적인 명령(전군 공격, 후퇴 등)을 하달합니다.

### B. 데이터 기반 지식 (Commander Knowledge)
- **Commander Knowledge**: 하드코딩된 빌드 오더를 `commander_knowledge.json`으로 추출했습니다.
- **MLOps 파이프라인**: 50개 이상의 리플레이를 학습하여 최적의 드론 비율과 확장 타이밍을 도출해냈습니다.

### C. 중앙 칠판 아키텍처 (Blackboard Pattern)
- 모든 매니저가 게임 상태를 **`Blackboard`**에 공유합니다.
- 복잡한 스파게티 의존성을 제거하고, 중앙에서 데이터를 관리하여 안정성을 확보했습니다.

### D. 통합 방어 코디네이터 (Defense Coordinator)
- 흩어져 있던 방어 로직을 **`DefenseCoordinator`**로 통합했습니다.
- "러쉬" vs "견제"를 구분하여 적절한 수의 유닛만 방어에 투입합니다.

---

## 3. 미래 (The Future): 초지능과 정밀 제어

향후 개발은 **마이크로 컨트롤의 고도화**와 **학습 범위의 확대**에 초점을 맞춥니다.

### A. 고급 마이크로 컨트롤 (Advanced Micro)
- **잠재력장(Potential Fields)**: 유닛이 적에게서는 멀어지려 하고, 목표물에는 가까워지려 하는 물리력을 시뮬레이션하여, 자연스러운 산개(Splitting)와 포위 진형을 구현합니다.
- **군집 제어(Boids Algorithm)**: 뮤탈리스크 짤짤이나 저글링의 빈집털이 등 프로급 컨트롤을 자동화합니다.

### B. 완전 자율 학습 (End-to-End RL)
- 현재는 "전략 모드"만 결정하지만, 앞으로는 **유닛 생산 비율**, **멀티 타이밍**, **병력 분배**까지 RL Agent가 직접 학습하도록 권한을 확대합니다.
- 룰(Rule) 기반 코드를 줄이고, 수천 판의 자가 대전을 통해 스스로 최적해를 찾도록 만듭니다.

---

## 요약

| 구분 | 과거 (Past) | 현재 (Present) [구현됨] | 미래 (Future) [계획됨] |
| :--- | :--- | :--- | :--- |
| **의사결정** | 각 매니저 독단 실행 | **RL (결정) -> 매니저 (실행)** (Unified) | **End-to-End RL** (자율 학습 확대) |
| **데이터공유**| 1:1 직접 호출 (Coupling) | **Blackboard** (중앙 공유) | 실시간 전술 맵 공유 |
| **방어체계** | 로직 분산 (충돌 발생) | **DefenseCoordinator** (통합) | 협동 방어 AI |
| **유닛컨트롤**| 단순 어택땅 | **StrategyManager** 통합 지휘 | **Potential Fields** (정밀 마이크로) |
