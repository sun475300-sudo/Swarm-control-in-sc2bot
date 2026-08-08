# MASTER TODO — Swarm-control-in-sc2bot

> 갱신: 2026-07-16 · 출처: 반복 테스트/점검 자동화 세션 중 발견한 **PR 적체 위기** 전수조사
> 이전 갱신: 2026-04-26 (PR #28 unblock 작업 중 백로그 전수조사, 아래 "부록"에 원문 보존)

---

## 0. 긴급 — PR 적체 위기 (오늘 발견, 최우선)

### 요약

**열린 PR이 443건**이며 (`#15` ~ `#481`, 2026-04-20 ~ 2026-07-16), 이 중 실제로 **main에 머지된 것은 단 1건**(`#218`, 2026-06-01)뿐이다. 나머지는 전부 draft 상태로 방치되어 있다. `claude/stoic-shannon-*` 계열(초기 ~14건)은 2026-04-27에 일괄 close 되었으나 머지는 안 됨. 그 이후 `claude/optimistic-edison-*` 계열이 시작되어 현재까지 멈추지 않고 계속 쌓이고 있다 — 2026-07-16 하루에만 `#457`~`#481` 약 25건이 생성됨(시간당 약 1건 페이스).

### 근본 원인

이 반복 작업(테스트 → 개선 → commit/push → PR 생성)을 트리거하는 자동화가 **매번 `main`에서 새 브랜치를 새로 분기**하고, **기존에 열려 있는 동일 목적의 draft PR을 확인하거나 이어서 작업하지 않는다.** 그 결과:

1. `main`의 `tests/test_combat_phase_fsm.py`가 Python 3.11에서 `asyncio.get_event_loop().run_until_complete(...)`가 깨지는 버그(12개 테스트 실패)를 계속 가지고 있고,
2. 매 세션이 이 버그를 "새로" 발견해서 거의 동일한 diff로 고치고,
3. 그 결과물을 새 draft PR로 올리기만 하고 머지하지 않으니,
4. `main`은 계속 깨진 상태로 남고, 다음 세션이 또 1번부터 반복.

**동일한 asyncio.get_event_loop() 수정을 제안하는 draft PR이 최소 40개 이상 존재한다** (`#436`~`#481` 대부분 + 그 이전 다수). 오늘 세션에서도 로컬에서 동일 수정을 만들었으나, 이미 `#481`(가장 최근, `mergeable_state: clean`, CI green)에 동등한 수정이 포함되어 있어 **중복 PR 생성을 하지 않고 이 문서만 갱신**하기로 했다.

### 권장 조치 (사용자 결정 필요 — 자동 머지/close 안 함)

1. **`#481`을 main에 머지** — 가장 최근이고, CI green(`mergeable_state: clean`), FSM asyncio 수정 + CI protobuf env var 수정 + silent-exception 로깅 개선 포함. 이걸 머지하면 최소한 `main`의 FSM 테스트 깨짐은 해결된다.
2. **나머지 ~440여 개 draft PR 중 `#481`과 목적이 겹치는 것들을 일괄 close** — 거의 전부 "동일 asyncio 버그 수정 + 부수적 개선"이 반복된 것이라 `#481` 머지 후에는 실질적으로 redundant.
3. **자동화 트리거 재검토** — 현재 페이스(하루 최대 25건, 시간당 ~1건)로는 세션들이 서로의 작업을 볼 수 없어 동일 작업을 무한 반복한다. 다음 중 하나 필요:
   - 트리거 주기를 늘리기 (예: 하루 1회) — "매일 확인" 요청과도 부합
   - 트리거 프롬프트에 "새 브랜치 만들기 전에 열린 PR 목록을 먼저 확인하고, 겹치는 작업이 있으면 그 브랜치를 이어서 작업하라"는 지시 추가
   - **가장 근본적**: CI green인 PR은 자동 머지 허용 (현재는 "머지 금지, 사용자 검토 필수" 정책이 명시돼 있어 이게 병목의 핵심 원인)

### 검증한 사실

- `pytest tests/ -q` (main 기준, PR #481 반영 전): **12 failed** (전부 `test_combat_phase_fsm.py`, `RuntimeError: no current event loop`), 490 passed, 14 skipped
- `pytest wicked_zerg_challenger/tests/ -q`: 661 passed, 0 failed (이 스위트는 문제 없음)
- `flake8 . --select=E9,F63,F7,F82`: 0 errors (구문 오류 없음)
- PR `#481` 브랜치 기준 재실행: `tests/` 502 passed / 14 skipped / **0 failed**, `wicked_zerg_challenger/tests/` 661 passed — 즉 `#481`을 머지하면 두 스위트 모두 green.
- git 머지 이력상 실제 머지는 `#218`, `#49`, `#29`(dependabot), 그리고 PR 없이 직접 merge commit 된 소수(예: "merge: apply SC2 lint cleanup branch")뿐.

---

## 1. 로드맵 상태 (부록 갱신)

`ROADMAP.md`의 Sprint 1~7 태스크는 **테스트 파일 기준으로는 대부분 이미 구현되어 있음**을 확인했다 (`test_worker_harassment_defense.py`, `test_sprint2_scouting_intel.py`, `test_sprint4_combat_micro.py`, `test_sprint5_defense_systems.py`, `test_sprint6_rl_pipeline.py`, `test_sprint7_architecture.py`, `test_distance_cache.py`, `test_frame_skip_manager.py` 등 존재 + 통과). `ROADMAP.md` 자체가 실제 구현 상태를 반영하지 못하는 stale 문서일 가능성이 높다 — **다음 세션에서 로드맵 문서와 실제 코드를 대조해 "완료" 표시로 갱신 필요** (코드 재작업 불필요, 문서만 갱신).

Sprint 8(QA/Arena 배포)은 실제 게임 실행이 필요해 자동 세션에서는 검증 불가 — 사람이 `run_mass_test.py` 30연전을 직접 돌려야 함.

---

## 부록: 2026-04-26 원문 백로그 (대부분 해소되었거나 재발생함)

### 1.3 TODO/FIXME, 1.4 skip/xfail, 1.6~1.9 CI/의존성 항목

이 항목들은 4월 조사 당시 기준이며 재검증이 필요하다. 오늘 세션에서는 위 "0. PR 적체 위기"가 압도적으로 우선순위가 높아 재조사하지 못했다. 다음 세션에서:

- TODO/FIXME 27건(당시 기준) 재카운트
- pytest skip/xfail 15건(당시 기준) 재카운트 + 사유 라벨링
- `black --check .` 전체 통과 여부 재확인 (4월 기준 다수 파일 미포맷)

### 위험/제약 (계속 유효)

- **머지 금지**: 모든 PR은 사용자 검토 후 머지. 자동 머지 안 함. → **이 정책이 현재 PR 적체 위기의 핵심 원인이므로 재검토 권장** (위 "0. 긴급" 참조).
- **main/master 직접 push 금지**.
- **force push 금지** — 모든 변경은 신규 commit/신규 브랜치.
- **Secrets 미공개**.

---

## 다음 세션 액션 (추천 순서)

1. **새 브랜치를 만들기 전에 이 문서(`MASTER_TODO_SC2.md`)와 열린 PR 목록을 먼저 읽을 것.** 동일한 asyncio FSM 수정을 또 만들지 말 것 — `#481`이 이미 존재.
2. 사용자에게 `#481` 머지 + 나머지 draft PR 정리를 권장하는 상태로 대기.
3. 머지/정리가 완료된 후에는 `ROADMAP.md` 문서 갱신(코드는 이미 구현됨, "완료" 표시만 필요) 및 Sprint 8 QA 30연전을 다음 우선순위로.
