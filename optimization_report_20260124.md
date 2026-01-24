# 2026-01-24 봇 시스템 최적화 및 개선 보고서

## 1. 개요 (Overview)
본 보고서는 WickedZergBotPro의 성능 향상, 로직 안정화, 그리고 건설 로직의 정확성을 개선하기 위해 2026년 1월 24일에 수행된 최적화 작업의 상세 내용을 기술합니다.

## 2. 주요 개선 사항 (Major Improvements)

### 2.1 전투 성능 최적화 (Micro Controller)
**문제점:**
대규모 교전 시 모든 유닛을 매 프레임 업데이트하려고 시도하여 연산 부하가 심각했습니다. 이로 인해 '프레임 드랍'이 발생하고 유닛 반응 속도가 저하되었습니다.

**개선 내용:**
*   **우선순위 기반 업데이트 (Priority-based Updates)**:
    *   전투 중이거나 적 근처에 있는 **중요 유닛(High Priority)**은 매 프레임 업데이트하도록 변경했습니다.
    *   전투에 참여하지 않는 **비전투 유닛(Low Priority)**은 4 프레임에 걸쳐 분산 처리(Staggered Processing)하도록 변경했습니다.
*   **처리 용량 증대**: 프레임당 처리 유닛 제한을 30기에서 **80기**로 대폭 상향하여 대규모 교전 시에도 반응성을 유지하도록 했습니다.
*   **업데이트 주기 조절**: 전체 업데이트 주기를 12프레임에서 **2프레임**으로 단축하여 반응성을 높이되, 위에서 언급한 분산 처리로 부하를 관리했습니다.

**관련 파일:** `wicked_zerg_challenger/micro_controller.py`

### 2.2 경제 관리 최적화 (Economy Manager)
**문제점:**
`_assign_idle_workers` 함수가 매 프레임 실행되면서 비효율적인 연산을 반복하여 CPU를 점유했습니다.

**개선 내용:**
*   **대기 일꾼 쿼리 최적화**: `self.bot.workers.filter(lambda w: w.is_idle)` 대신 내부적으로 훨씬 빠른 `self.bot.workers.idle`을 사용하도록 변경했습니다.
*   **미네랄 검색 캐싱 (Caching)**: 매번 `closer_than`으로 주변 미네랄을 검색하는 대신, 기지별 미네랄 정보를 캐싱하여 재사용하도록 개선했습니다.
*   **거리 계산 제거**: 가스 채취 할당 시 불필요한 거리 계산을 제거하고 즉시 할당하도록 변경했습니다.

**관련 파일:** `wicked_zerg_challenger/economy_manager.py`

### 2.3 건설 위치 탐색 최적화 (Building Placement)
**문제점:**
점막(Creep) 위 건설 위치를 찾을 때 `random` 함수를 이용한 무작위 샘플링 방식을 사용하여, 운이 나쁘면 위치를 찾지 못하거나 시간이 오래 걸리는 문제가 있었습니다.

**개선 내용:**
*   **나선형 탐색 알고리즘 (Spiral Search Algorithm)**: 무작위 방식 대신 중심점에서 밖으로 퍼져나가는 **결정론적(Deterministic) 나선형 탐색**을 도입했습니다.
*   **탐색 효율성**: 가까운 거리부터 체계적으로 탐색하므로 100% 확률로 가장 가까운 유효 위치를 즉시 찾아냅니다.

**관련 파일:** `wicked_zerg_challenger/building_placement_helper.py`

### 2.4 로직 안정성 강화 (System Stability)
**문제점:**
*   `IntelManager`에서 오래된 바이트코드(.pyc) 문제로 인한 `AttributeError` 발생.
*   저그 건물이 점막이 아닌 맨땅에 건설되려고 하여 `ErrorPlace` 오류 발생 및 빌드 오더 꼬임.

**개선 내용:**
*   **IntelManager 복구**: `__pycache__` 삭제 및 모듈 리로드로 오류 해결.
*   **점막 건설 강제 (Creep Enforcement)**: `BuildingPlacementHelper`를 통해 해처리/부화장을 제외한 모든 저그 건물이 **반드시 점막 위에 있는지 확인**한 후 건설 명령을 내리도록 수정했습니다.

**관련 파일:** `wicked_zerg_challenger/local_training/advanced_building_manager.py`

## 3. 향후 계획 (Next Steps)
현재 성능 및 안정성 최적화가 1차적으로 완료되었습니다. 다음 단계로는 아키텍처 개선을 추천합니다.

1.  **행동 트리(Behavior Tree) 도입**: 복잡한 `if-else` 구조의 전략 로직을 체계적인 행동 트리로 변환.
2.  **데이터 백업 시스템**: 봇 재시작 시에도 학습된 데이터(Intel)를 유지할 수 있는 JSON/Pickle 백업 구현.

훈련을 재개하여 최적화된 봇의 성능을 확인하시기 바랍니다.
