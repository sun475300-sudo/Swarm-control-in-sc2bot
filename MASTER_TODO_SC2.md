# MASTER TODO — Swarm-control-in-sc2bot

> 갱신: 2026-07-14 · 출처: nightly 점검 세션(claude/optimistic-edison-exn4oa)
> 이전 버전(2026-04-26)은 PR #15~#30 기준으로 작성되어 완전히 stale — 해당 PR들은
> 전부 closed(merge 없이) 상태이며 현재 open PR 목록과 무관. 이 문서를 최신 상태로
> 전면 교체함.

---

## 0. 가장 중요한 발견: PR이 쌓이기만 하고 머지되지 않는다

**open draft PR 30건** (#436~#465, 전부 2026-07-13~07-14 생성, 브랜치 전부
`claude/optimistic-edison-*`)이 사실상 전부 **동일한 문제**(black/isort 린트 게이트
red → CI 테스트 잡이 취소됨, `tests/test_combat_phase_fsm.py`의 `asyncio.get_event_loop()`
event-loop 버그)를 반복해서 고치고 있음. 각 세션이 이전 세션의 미머지 브랜치를 모르고
`main`(8a80b73, 여전히 CI red)에서 새로 시작하기 때문에 벌어지는 현상.

- **머지된 적 있는 PR**: 역대 전체 중 **#218**, **#44** 단 2건뿐.
- **가장 완성도 높은 미머지 PR**: **#465** (`claude/optimistic-edison-yjdipv`) —
  black+isort 전체 정리, FSM 테스트의 `asyncio.run()` 전환, CI 환경변수/의존성 수정.
  로컬 재검증 결과 **1163 passed, 14 skipped, 0 failed** 확인됨(이 세션에서 직접 재실행).
- **이 세션의 조치**: 새 PR을 또 만들지 않기 위해, 이 브랜치(`exn4oa`)를 PR #465의
  커밋(`17de1ea`)으로 **fast-forward 머지**해서 흡수함. 즉 이번 PR은 #465와 동일한
  CI 수정을 포함하되 중복 재작업은 하지 않았음.
- **사용자 액션 필요(자동화 불가)**: 저장소 정책상 "모든 PR은 사용자 검토 후 머지,
  자동 머지 금지"이므로, 이 정체를 풀려면 **사람이 #465(또는 이 PR)를 main에 머지**해야
  함. 머지되지 않는 한 다음 nightly 세션도 동일한 CI 수정을 또 반복 발견할 가능성이 큼.
  머지 후에는 #436~#464(및 stale해질 이 PR 이전 버전들) 중 남는 중복 PR을 close 권장.

---

## 1. 로드맵 재검증 결과 (ROADMAP.md 참고)

Sprint 1~6 태스크를 코드 기준으로 전수 재검증 — **거의 전부 이미 구현되어 테스트까지
통과 중**이었음. ROADMAP.md가 실제 구현 상태를 반영하지 못하고 있었을 뿐, 실제 미구현
기능은 아니었음. 상세 근거는 `ROADMAP.md`의 각 Sprint 섹션 `[검증 2026-07-14]` 참고.

### 실제로 남은 작업

| # | 항목 | 상태 | 비고 |
|---|---|---|---|
| 1 | `scouting_system.py:deploy_changeling()` dead code | 미사용 | 호출부 0건. changeling 자동 생산은 `advanced_scout_system_v2.py`/`spellcaster_automation.py`가 이미 수행 중이라 기능 공백은 아님. 정리(삭제 또는 중복 제거) 대상. |
| 2 | DistanceCache 채택률 낮음 (Sprint 7.2) | 부분 구현 | `combat_manager.py`/`economy_manager.py`에 캐시가 연결은 됐지만 실제 캐시 경유 호출은 4+3건, 미캐시 `distance_to()`는 60+24건. 핫패스부터 점진 전환 필요. |
| 3 | 매직넘버 → GameConstants 이행 미완 (Sprint 7.3) | 부분 구현 | `iteration % 11/22/33/44/55/66/88/110/165/220` 패턴이 65개 파일 174곳에 잔존. **주의**: 과거 대규모 일괄 치환 시도(PR #25, #37, #44 등)가 반복 충돌을 유발한 전례 — 파일 단위 소규모 배치로 진행할 것. |
| 4 | Sprint 8 QA 30연전 실행 기록 부재 | 미확인 | `run_mass_test.py`는 존재하나 실행 로그/승률 데이터가 저장소에 없음. "추정 승률 45~50%"는 미검증 수치. |
| 5 | Sprint 6 RL 실전 데이터 부재 | 미확인 | RL 토글/파이프라인 코드와 단위 테스트는 있으나, 실전 승률 비교(RL on vs off) 데이터 없음. |

### 코드 품질 (2026-04-26 조사 당시 기준, 재검증 필요)
- TODO/FIXME 27건(7개 파일, 대부분 보조 도구) — 이번 세션에서 재확인 안 함, 다음 라운드 후보.
- pytest skip 14건(이번 세션 재확인: 14 skipped, 이전 기록 15건과 거의 일치) — sc2/torch/numpy 등 선택적 의존성 미설치 환경에서의 skip으로 추정, 라벨링 필요.

---

## 2. CI 워크플로 현황

- `ci.yml`(JARVIS CI/CD): PR #465가 안정화 시도 중.
- `sc2bot-ci.yml`(SC2 Bot CI/CD): lint(`black --check` + `isort --check-only` +
  `flake8` + `mypy --strict` + `bandit -ll`)가 매우 엄격 — `main`이 8a80b73 이후
  black/isort red 상태로 추정(이 세션에서 로컬 재현: `black --check .` 66 files,
  `isort --check-only .` 19 files 미포맷 확인, 단 PR #465/이 브랜치에는 이미 적용됨).
- 이번 세션 로컬 검증: `flake8 wicked_zerg_challenger/ --select=E9,F63,F7,F82,F811,F821`
  → **0건** (치명적 런타임 버그 없음).

---

## 3. 위험 / 제약 (변경 없음)

- **머지 금지**: 모든 PR은 사용자 검토 후 머지. 자동 머지 안 함.
- **main/master 직접 push 금지**.
- **force push 금지** — 모든 변경은 신규 commit/신규 브랜치.
- **Secrets 미공개**.
- **대규모 일괄 치환(포맷팅/매직넘버 등)은 소규모 배치로 분할** — 과거 전례상 충돌·중복 PR 양산 위험.

---

## 4. 다음 액션 (추천 순서)

1. **[사용자 결정 필요]** PR #465 또는 이번 세션 PR을 review 후 `main`에 머지 — 이것이
   풀리지 않으면 나머지 모든 항목이 계속 재발견될 것.
2. **[사용자 결정 필요]** 머지 후 #436~#464 중 남은 중복 PR 정리(close).
3. DistanceCache 핫패스 채택 확대 (item #2) — 소규모 PR로 분리.
4. 매직넘버 이행 (item #3) — 파일 단위 배치로 분리, 회귀 테스트 필수.
5. Sprint 8 QA 30연전 실제 실행 + 결과 기록.
