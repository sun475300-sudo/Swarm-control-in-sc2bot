# 리플레이 비교 학습 로직 설명서

## 개요
리플레이 비교 학습 시스템은 프로게이머나 고수준의 리플레이 파일(`*.SC2Replay`)을 분석하여 **저그의 최적화된 빌드 오더와 유닛 생산 타이밍**을 추출하고, 이를 봇에 자동 적용하는 시스템입니다.

## 핵심 로직 (ReplayBuildOrderLearner)

시스템의 핵심은 `local_training/scripts/replay_build_order_learner.py`에 구현되어 있으며, 다음과 같은 4단계 프로세스로 작동합니다.

### 1단계: 리플레이 파싱 및 분류
*   **파일 스캔**: `replays` 폴더 내의 모든 `*.SC2Replay` 파일을 찾습니다.
*   **메타데이터 추출**: 맵 이름, 게임 길이, 승자, 플레이어 종족 등을 추출합니다.
*   **승리한 게임 필터링**: 배울 가치가 있는 "이긴 게임"(`zerg_wins`)만을 분석 대상으로 삼습니다.
*   **상대 종족별 분류**: 빌드를 `vs_terran`, `vs_protoss`, `vs_zerg`로 나누어 별도로 관리합니다.

### 2단계: 상세 빌드 오더 추출
각 리플레이의 이벤트 로그를 초 단위로 분석하여 다음 정보를 추출합니다:
*   **건물 건설**: `Hatchery`, `SpawningPool`, `Lair` 등이 건설된 정확한 시간과 인구수(Supply).
*   **유닛 생산**: `Drone`, `Zergling`, `Roach` 등이 생산된 시점.
*   **확장 타이밍**: 2멀티, 3멀티, 4멀티가 가져가진 시간을 별도로 추적합니다.

### 3단계: 통계적 학습 (파라미터 생성)
추출된 수십/수백 개의 리플레이 데이터를 종합하여 평균값을 계산합니다:
*   **평균 건설 타이밍**: "산란못은 평균 75초, 번식지는 300초에 건설됨"과 같은 최적 타이밍을 도출합니다.
*   **유닛 중요도(Priorities)**: 어떤 유닛이 얼마나 자주, 많이 생산되는지를 분석하여 생산 우선순위를 매깁니다.
*   **확장 패턴**: 평균적으로 언제 멀티를 확장하는지 학습합니다.

### 4단계: 적응형 적용
학습된 결과는 `learned_build_orders.json` 파일로 저장되며, 봇은 이를 읽어들여 자신의 행동을 수정합니다:
*   **`config.py` (또는 설정 로직)**: 저장된 JSON 파일을 로드하여 `BuildConstants` 값을 덮어씁니다.
*   **실제 효과**: 봇이 프로게이머의 타이밍에 맞춰 건물을 짓고 확장을 시도하게 됩니다.

## 데이터 흐름도

```mermaid
graph TD
    A[Replay Files (*.SC2Replay)] -->|Scan| B[ReplayBuildOrderLearner]
    B -->|Parse Events| C{Is Winner Zerg?}
    C -->|Yes| D[Extract Build Order]
    C -->|No| E[Discard]
    D -->|Accumulate| F[Statistical Analysis]
    F -->|Calculate Averages| G[learned_build_orders.json]
    G -->|Load at Startup| H[WickedZergBot]
    H -->|Execute| I[Optimized Gameplay]
```

## 주요 특징
1.  **자동화**: 사용자가 리플레이 파일만 폴더에 넣으면 모든 학습 과정이 자동으로 이루어집니다.
2.  **데이터 기반**: 하드코딩된 빌드가 아닌, 실제 승리 데이터에 기반한 "살아있는" 빌드를 사용합니다.
3.  **지속적 개선**: 리플레이가 쌓일수록 평균값은 더욱 정교해지고 신뢰도가 높아집니다.
