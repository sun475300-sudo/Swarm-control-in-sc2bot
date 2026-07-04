# Claude 반복 점검/개선 로그 (Test → Fix → Commit Loop)

이 문서는 "계속 테스트하고 점검하고 개선하는" 반복 작업의 살아있는 상태 기록이다.
`MASTER_TODO_SC2.md` / `REMAINING_ISSUES.md` / `PLAN-NIGHTLY.md` / `CHANGELOG.md` 등
기존 로드맵 문서들은 최신 상태를 반영하지 못하는 부분이 많다는 것이 이번 점검에서
확인되었으므로, 이 문서가 "지금 실제로 무엇이 열려 있는지"의 1차 참고 자료다.

## 실행 환경 메모 (다음 세션이 반드시 알아야 할 것)

- 이 컨테이너의 시스템 pip/setuptools는 Debian 패치 버그로 `mpyq`(burnysc2 의존성)
  빌드가 실패한다. **반드시 venv를 새로 만들어서 그 안에 설치할 것**
  (`python3 -m venv <path> && source <path>/bin/activate`).
- `s2clientprotocol`가 최신 `protobuf`(6.x+)와 맞물리면
  `TypeError: Descriptors cannot be created directly` 오류가 난다.
  테스트 실행 시 항상 `PROTOCOL_BUFFERS_PYTHON_IMPLEMENTATION=python` 환경변수를 설정할 것
  (`ci.yml`의 `sc2-bot-test` job은 이미 이렇게 하고 있음).
- 두 개의 테스트 스위트가 존재: 루트 `tests/` (502 passed, 14 skipped, 0 failed 확인됨)와
  `wicked_zerg_challenger/tests/` (661 passed, 0 failed 확인됨). 둘 다 매번 돌릴 것.

## 이번 세션에서 완료한 작업 (커밋됨, PR #273)

1. **`tests/test_combat_phase_fsm.py`**: Python 3.11에서 제거된
   `asyncio.get_event_loop()` 암묵적 루프 생성 동작에 의존하던 5곳을 `asyncio.run()`으로 교체.
   12개 테스트가 `RuntimeError`로 실패하던 것을 수정 (490 pass/12 fail → 502 pass/0 fail).
2. **`.github/workflows/sc2bot-ci.yml`**: 존재하지 않는 `tests/unit/` 디렉터리를 참조하던
   버그 수정 (`pytest tests/unit` → `pytest tests/ --ignore=tests/integration`).
   이 job은 지금까지 매 실행마다 무조건 실패하고 있었음.
3. **저장소 전체 black + isort 포맷팅** (66개 파일): `sc2bot-ci.yml`의
   `Lint & Type Check` job이 `black --check .` / `isort --check-only .`에서
   매번 실패하던 것을 해소. 포맷팅 전후로 두 테스트 스위트를 모두 재실행해서
   동작 변화가 없음을 확인함 (순수 포맷팅 변경).
4. **`tests/test_queen_transfusion.py`**: 다른 형제 테스트 파일들과 달리
   `sc2.ids.unit_typeid` import에 try/except fallback이 없어서 `sc2`/`burnysc2`가
   설치되지 않은 환경에서는 `pytest tests/`가 collection 단계에서 전체가 죽었음.
   sibling 파일(`test_queen_transfusion_manager.py`)과 동일한 skip 패턴 적용, 검증 완료
   (sc2 미설치 venv에서 정상적으로 skip 되는 것 확인).
5. **`ci.yml`의 `python-lint-test` job**: `requirements.txt`로 burnysc2를 설치하면서도
   `PROTOCOL_BUFFERS_PYTHON_IMPLEMENTATION=python`을 설정하지 않아 매번
   `TypeError: Descriptors cannot be created directly`로 collection이 죽던 것 수정.
6. **`sc2bot-ci.yml`의 `test` job**: 동일한 원인(env var 누락)으로 unit/integration
   테스트 스텝이 모두 실패하던 것 수정. 실제 CI 실패 이벤트로 발견 → 로컬 재현 → 수정 → 검증.
7. **`sc2bot-ci.yml`의 `test` job (2차)**: `pytest tests/integration --timeout=120`이
   `pytest-timeout` 플러그인 없이 실행되어 `unrecognized arguments: --timeout=120`으로
   매번 죽던 것 발견·수정 (`pip install` 목록에 `pytest-timeout` 추가). 이것도 실제 CI 실패
   이벤트로 발견됨 — CI가 이전 버그를 가려서 이 버그는 그동안 드러나지 않고 있었음.

## 점검했지만 "이미 해결됨"으로 확인된 로드맵 항목 (문서만 낡은 것)

- `REMAINING_ISSUES.md` N1 (HIGH): `OpponentModeling.on_step` 중복 정의 →
  **이미 해결됨** (현재 `opponent_modeling.py`에 `on_step` 정의 1개뿐, line 341).
- `REMAINING_ISSUES.md` N2–N4: `EconomyManager`, `combat_manager._find_harass_target`,
  `production_resilience.build_terran_counters` 중복 정의 → **이미 해결됨**
  (AST로 `wicked_zerg_challenger/` 전체 클래스 메서드 중복 스캔, 0건).
- `MASTER_TODO_SC2.md`의 "pytest skip/xfail 15건 라벨링" → **이미 해결됨**
  (`tests/`의 모든 skip 호출에 이미 구체적인 reason 문자열이 있음, 라벨 없는 항목 없음).

이런 항목들은 git log상 2026-06-01~06-25 커밋 구간
(`refactor: delete shadowed duplicate methods...`, `fix: 6 F821 NameError...` 등)에서
이미 처리된 것으로 보임. **다음 세션은 이 항목들을 다시 조사하지 말고 아래 "실제로 열려 있는 작업"만 볼 것.**

## 실제로 열려 있는 작업 (우선순위 순, 다음 세션이 여기부터 시작)

1. **`REMAINING_ISSUES.md` Issue #3 (MED)** — Queen transfusion 우선순위 로직이
   고가 유닛(Ultralisk/Broodlord)을 우선하지 않고, 치료 불가능한 유닛을 제외하지 않음.
   `wicked_zerg_challenger/economy/queen_transfusion_manager.py` 확인 필요 (아직 미검증).
2. **`PLAN-NIGHTLY.md` P2.2** — 벤치마크 러너: 명령 한 번으로 N개 리플레이 실행,
   APM/서플라이/승률 리포트를 Hard AI 대비 생성. 미구현.
3. **`PLAN-NIGHTLY.md` P2.3** — 빌드오더 설정 외부화: 하드코딩된 상위 20개 값을
   `config/build_orders.yaml`로 이동. 미구현.
4. **`PLAN-NIGHTLY.md` P2.4** — RL agent 저장 가드: 디스크 풀/중단된 rename에 대한
   유닛 테스트. 미구현.
5. **`PLAN-NIGHTLY.md` P2.5** — `core/resource_manager.py`, `core/manager_factory.py`
   타입 힌트 + docstring 보강. 미구현.
6. **`INFRA_PLAN.md` 모니터링/대시보드 (5%)** — `dashboard.py`/`telemetry.py`가
   빈 스텁 상태. 실제 구현 필요 (규모가 큰 작업).
7. **`MASTER_TODO_SC2.md`의 열린 PR 14개 중복 정리** — 문서 자체가 "실제 close는
   사용자 승인 필요"라고 명시함. **자동으로 닫지 말고 사용자에게 먼저 물어볼 것.**
8. **저장소 루트의 50개 `지휘관bot*` 스텁 디렉터리** (언어별 보일러플레이트 78개 파일,
   실제 봇과 무관) — 정리하면 탐색성이 좋아지지만, 삭제/이동은 되돌리기 어려운 작업이므로
   **사용자에게 먼저 확인할 것.**

## 다음 세션 체크리스트

1. `git pull origin claude/optimistic-edison-6z7jms`
2. venv 활성화 (없으면 위 "실행 환경 메모"대로 새로 생성)
3. `PROTOCOL_BUFFERS_PYTHON_IMPLEMENTATION=python pytest tests/ wicked_zerg_challenger/tests/ -q` 로 baseline 확인 (계속 0 fail이어야 함)
4. 위 "실제로 열려 있는 작업" 목록에서 위에서부터 하나 골라 수정
5. 두 테스트 스위트 재실행 → green 확인
6. commit + push (PR #273 브랜치, `claude/optimistic-edison-6z7jms`)
7. 이 문서의 "완료한 작업" 섹션에 갱신, "열려 있는 작업"에서 제거
8. 사용자에게 짧게 보고
