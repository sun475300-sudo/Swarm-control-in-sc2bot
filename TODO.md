# TODO — Live Backlog (재작성: 2026-07-05)

> 이전 버전(2026-01-26 작성)은 완전히 stale했습니다 — 정찰 강화, 견제 시스템,
> 1분 멀티, 전투 프레임 스킵, StrategyManager 역할 분담 등 나열된 항목이
> 전부 이미 구현/테스트되어 있었습니다 (scouting_system.py, combat frame-skip
> manager, strategy_manager_v2, test_worker_harassment_defense.py 등 확인).
> 아래는 2026-07-05 감사 사이클(테스트 실행 → 정적 분석 → 코드 대조)로 재작성한
> 실제 백로그입니다.

## 이 환경의 테스트 범위 (중요)

이 원격 실행 환경에는 StarCraft II 클라이언트가 설치되어 있지 않습니다
(`SC2PATH` 미설정, 맵 파일 없음). 따라서 여기서 "테스트"는 다음으로 제한됩니다:
- `pytest` 단위/통합 테스트 (root `tests/` + `wicked_zerg_challenger/tests/`)
- `black`/`isort`/`flake8` 정적 분석 및 CI 파이프라인 자체의 정합성
- `py_compile` 구문 검증

ROADMAP.md Sprint 8 (`Medium AI 30연전 테스트`, AI Arena 패키지 실전 검증)처럼
실제 SC2 게임 실행이 필요한 항목은 이 환경에서 실행할 수 없습니다 — SC2 클라이언트가
있는 환경에서 별도로 수행해야 합니다.

## 2026-07-05 감사 사이클에서 완료

- [x] `tests/test_combat_phase_fsm.py` 12개 테스트 실패 수정 (`asyncio.get_event_loop()`
      → `asyncio.run()`, Python 3.11/pytest-asyncio 비호환)
- [x] `black`/`isort` 포맷 드리프트 수정 (66+19 파일) — CI Lint 게이트 차단 해소
- [x] `REMAINING_ISSUES.md`의 stale한 "open" 표기 정정 (Transfusion 우선순위,
      Resource Reservation, N1-N4 중복 정의 — 전부 이미 코드에 구현되어 있었음)
- [x] `requirements.txt`의 `google-generativeai` 제거 → `requirements-genai.txt`로 분리
      (transitive dep `google-ai-generativelanguage`가 `protobuf<6` 강제,
      `s2clientprotocol`은 `protobuf>=6` 요구 — 두 요구사항이 상호 배타적이라
      전체 `requirements.txt` 설치 시 `import sc2`가 항상 깨지던 버그)
- [x] `.github/workflows/sc2bot-ci.yml`의 "Test Suite" job이 존재하지 않는
      `tests/unit`/`tests/integration` 경로를 참조 — 실제 테스트 경로로 수정
      (이 job은 `build_docker`/`push_to_registry`의 선행 조건이라, main 브랜치
      Docker 이미지 배포가 계속 조용히 막혀있었을 가능성)
- [x] 이 문서(TODO.md) 자체의 stale 내용 재작성

## 우선순위 높음 🔴

(현재 없음 — 위 라운드에서 발견된 HIGH 항목은 모두 처리 완료)

## 우선순위 중간 🟡

### 1. Position Utils 유틸리티 실채택 (REMAINING_ISSUES.md Issue #5)

`wicked_zerg_challenger/utils/position_utils.py`에 `get_center_position`/
`get_weighted_center`가 구현되어 있으나 아래 11개 파일이 여전히 동일 계산을
자체 구현 중:
`combat/expansion_defense.py`, `combat/combat_execution.py`,
`combat/infestor_tactics.py`, `combat/micro_combat.py` (2곳),
`combat_phase_controller.py`, `micro_controller.py`, `combat_manager.py` (2곳),
`battle_preparation_system.py`, `idle_unit_manager.py`.
순수 리팩터(동작 변화 없음) — 한 파일씩 교체 후 회귀 테스트 권장.

### 2. F841 unused-variable 정리 (130건, wicked_zerg_challenger/)

`flake8 --select=F841`로 130건 확인 (2026-07-05). 대부분 무해하지만
(exception 변수 `e` 미사용, 로그용으로만 남겨진 변수 등), 일부는 로직 누락을
가리킬 수 있음 — 예: `bot_step_integration.py:1229`의 `micro_interval`,
`combat/harassment_coordinator.py:699`의 `distance`는 계산은 해놓고 실제
조건문에 안 쓰인 것처럼 보여 개별 확인 필요.

### 3. bare `except Exception:` 감사 (105개 파일)

REMAINING_ISSUES.md N5. 방어적 코드로 의도된 것과 실제 에러를 삼켜서 버그를
숨기는 것을 구분하는 개별 리뷰가 필요 — 전수 조사는 비용이 크므로, 우선
`combat_manager.py`/`economy_manager.py`/`strategy_manager.py` 등 핵심 매니저
파일부터 표본 점검 권장.

## 우선순위 낮음 🟢

### 4. Constants 전역 스윕 마무리

`utils/game_constants.py`(241줄), `config/constants.py`(36줄)는 이미 존재.
남은 하드코딩된 iteration 주기 숫자(`% 22`, `% 66` 등)를 계속 검색해 교체.

### 5. 47개 이상의 루트 `*.md` 리포트 정리

STATUS.md에 이미 "docs/history/로 이동 예정(P1.5)"이라고 기록되어 있으나
아직 실행되지 않음. 이번 세션에서 TODO.md 자체가 stale했던 것처럼, 이 md
파일들도 실제 상태와 어긋날 위험이 있음 — 이동 자체보다 "이 문서는 과거
기록이며 최신 상태는 STATUS.md/TODO.md를 참고"라는 헤더를 붙이는 것부터
시작하는 게 비용 대비 효율적.

## 장기 (SC2 클라이언트 필요 — 이 환경에서 실행 불가)

- ROADMAP.md Sprint 6 (RL 실전 투입): PPO 에이전트 toggle, 커리큘럼 학습
  Stage 3, 셀프 플레이 파이프라인 — 코드 존재 여부는 확인했으나 실전 승률
  검증은 SC2 클라이언트 환경에서만 가능
- ROADMAP.md Sprint 8 (QA & AI Arena 배포): Medium AI 30연전, Arena 패키지
  실전 검증 (ZIP 크기, 320ms/step, 3개 이상 맵)
- 장기 비전: Elite AI 승률 50%+, AI Arena 래더 등록, MCTS/AlphaZero 실험,
  TensorRT 추론 가속, Rust 가속 모듈 확장
