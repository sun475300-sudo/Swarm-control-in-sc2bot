# 주요 모듈 분석 보고서 (Specific Module Analysis)

요청하신 4가지 핵심 기능에 대한 코드베이스 분석 결과입니다. 요청하신 파일명과 정확히 일치하는 파일은 없으나, **동일한 기능을 수행하는 모듈들이 다른 이름으로 존재함**을 확인했습니다.

## 1. 신경망 모델 및 RL 학습기
*   **요청 파일:** `zerg_net.py`
*   **실제 파일:** `local_training/rl_agent.py`
*   **상태:** **존재함 (Active)**
*   **분석:**
    *   `PolicyNetwork` 클래스가 `ZergNet`의 역할을 수행합니다 (15입력 -> 64은닉 -> 5출력의 3층 신경망).
    *   `RLAgent` 클래스가 강화학습(REINFORCE 알고리즘)을 담당하며, 상태 저장, 행동 선택, 역전파 학습을 수행합니다.
    *   NumPy 기반으로 구현되어 있어 가볍고 빠릅니다.

## 2. 전투 분석 및 보상 함수
*   **요청 파일:** `battle_analyzer.py`
*   **실제 파일:** `local_training/reward_system.py`
*   **상태:** **존재함 (Active)**
*   **분석:**
    *   `ZergRewardSystem` 클래스가 이 역할을 완벽하게 수행합니다.
    *   **전투 분석:** 전투 교환비(Kill/Lost)를 계산하여 이득을 분석합니다.
    *   **보상 함수:** 점막(Creep), 애벌레(Larva), 위협 요소 제거, 확장 타이밍 등 11가지 세부 항목으로 나누어 정교한 보상을 계산합니다.

## 3. 학습 진행 상황 시각화
*   **요청 파일:** `visualize_integrated.py`
*   **실제 파일:** `tools/monitor_background_training.py` (일부 기능)
*   **상태:** **부분 구현 (Console Only)**
*   **분석:**
    *   `monitor_background_training.py`가 텍스트 기반의 실시간 대시보드를 제공합니다.
    *   **제한사항:** 그래프나 차트를 그려주는 시각화 도구(`matplotlib` 등 사용)는 현재 구현되어 있지 않습니다. 웹 UI(`monitoring/server_manager.py`)도 누락되어 있어 시각화 기능은 보강이 필요합니다.

## 4. 자가 진화 (하이퍼파라미터 자동 튜닝)
*   **요청 파일:** `self_evolve.py`
*   **실제 파일:** `adaptive_learning_rate.py`
*   **상태:** **존재함 (Active)**
*   **분석:**
    *   `AdaptiveLearningRate` 클래스가 자가 진화 엔진 역할을 합니다.
    *   최근 20게임의 승률을 분석하여 학습률(Learning Rate)을 자동으로 높이거나 낮춥니다.
    *   성능이 정체되면 학습률을 조정하여 로컬 미니마(Local Minima)를 탈출하려는 시도를 합니다.

---

## 요약 (Summary)

| 요청 기능 | 실제 구현 파일 | 상태 | 비고 |
| :--- | :--- | :--- | :--- |
| **ZergNet** | `local_training/rl_agent.py` | ✅ **완료** | NumPy 기반 정책 신경망 |
| **Battle Analyzer** | `local_training/reward_system.py` | ✅ **완료** | 11개 항목 정밀 보상 체계 |
| **Visualization** | `tools/monitor_background_training.py` | ⚠️ **미흡** | 텍스트 대시보드만 존재 (그래프 X) |
| **Self Evolve** | `adaptive_learning_rate.py` | ✅ **완료** | 승률 기반 학습률 자동 조절 |

**결론:** 시각화(Visualization)를 제외한 핵심 기능은 이미 강력하게 구현되어 있습니다. 시각화 기능만 추가한다면 완전한 시스템이 될 것입니다.
