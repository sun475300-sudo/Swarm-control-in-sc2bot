# 프로젝트 개선 제안서 (Project Improvement Report)

현재 프로젝트의 코드베이스, 실행 로직, 기능 구현 상태를 종합적으로 검토하여 도출한 개선 사항들입니다. **안정성(Stability)**, **기능 활성화(Features)**, **코드 정리(Cleanup)** 세 가지 관점에서 우선순위를 매겼습니다.

## 1. 🚨 긴급 수정 필요 (Critical - Stability)
**시스템 충돌 및 런타임 에러를 방지하기 위해 즉시 해결해야 합니다.**

### 1-1. 누락된 핵심 파일 복구
*   **문제점:** `run_with_training.py` 코드는 게임 종료 후 `tools.extract_and_train_from_training` 모듈을 임포트하려고 시도하지만, 해당 파일이 존재하지 않습니다.
*   **영향:** 첫 게임이 끝나고 데이터 추출 단계로 넘어가는 순간 **프로그램이 강제 종료(Crash)**될 가능성이 매우 높습니다.
*   **해결방안:**
    *   `tools/extract_and_train_from_training.py` 파일을 백업에서 복구하거나 새로 구현해야 합니다.
    *   또는 해당 기능을 복구 전까지 주석 처리하여 충돌을 방지해야 합니다.

### 1-2. 웹 UI 서버 모듈 누락
*   **문제점:** `monitoring/server_manager.py` 파일이 없어 웹 기반 모니터링 서버가 시작되지 않습니다.
*   **영향:** 시각화 기능을 사용할 수 없으며, 관련 에러 로그가 계속 발생할 수 있습니다.

---

## 2. 🚀 기능 활성화 (High - Code Activation)
**이미 구현되어 있으나 연결되지 않은(Dead Code) 강력한 기능들을 되살립니다.**

### 2-1. Vertex AI (Gemini) 자가 치유 연결
*   **상태:** `genai_self_healing.py`에 강력한 에러 분석 및 패치 생성 로직이 있으나, 메인 루프에 연결되어 있지 않습니다.
*   **제안:** `run_with_training.py`의 예외 처리(Exception Handling) 부분에 `GenAISelfHealing.analyze_error()`를 호출하도록 연결하여, 에러 발생 시 AI가 원인을 분석하고 리포트하도록 만듭니다.

### 2-2. 자가 진화(Adaptive LR) 시각화
*   **상태:** `adaptive_learning_rate.py`가 학습률을 잘 조정하고 로그를 `json`으로 저장하고 있습니다.
*   **제안:** 이 데이터를 읽어 `matplotlib`으로 '승률 변화 그래프'와 '학습률 변화 그래프'를 그려주는 스크립트(`plot_progress.py`)를 추가하면 학습 성과를 한눈에 볼 수 있습니다.

---

## 3. 🧹 코드 정리 (Medium - Code Cleanup)
**혼란을 줄이고 유지보수성을 높이기 위해 불필요한 코드를 제거합니다.**

### 3-1. Legacy PyTorch 코드 제거
*   **대상:** `batch_trainer.py`, `run_smoke_training.py`, `run_hybrid_supervised.py`
*   **이유:** 현재 프로젝트는 NumPy 기반의 가벼운 `RLAgent`로 완전히 전환되었습니다. 무거운 PyTorch 의존성을 가진 옛날 코드들은 혼란만 가중시키므로 삭제하거나 `archive/` 폴더로 격리해야 합니다.

### 3-2. 일관성 없는 파일명 정리
*   **이유:** `zerg_net` vs `rl_agent`, `battle_analyzer` vs `reward_system` 등 용어가 혼재되어 있습니다.
*   **제안:** 문서나 주석을 업데이트하여 용어를 통일하거나, 심볼릭 링크/래퍼 파일을 만들어 사용자가 직관적으로 찾을 수 있게 합니다.

---

## 4. 💡 추가 제안 (Low - Enhancement)

*   **다양한 상대 난이도:** 현재 `Easy`, `Medium` 난이도 위주로 설정되어 있습니다. 적응형 난이도(Curriculum)가 `Hard`, `VeryHard`까지 자연스럽게 확장되도록 설정값을 점검해야 합니다.
*   **리플레이 자동 저장 관리:** 학습이 계속되면 리플레이 파일이 많이 쌓입니다. 오래된 리플레이를 자동으로 압축하거나 삭제하는 로테이션 로직 추가를 권장합니다.

---

## ✅ 추천 작업 순서

1.  **[긴급]** `run_with_training.py`에서 누락된 `extract_and_train_from_training` 임포트 구문 주석 처리 (충돌 방지).
2.  **[정리]** PyTorch 레거시 파일 삭제.
3.  **[기능]** 간단한 시각화 스크립트 (`plot_progress.py`) 작성.
4.  **[확장]** Vertex AI 모듈 연결.
