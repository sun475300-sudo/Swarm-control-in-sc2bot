# MASTER TODO — Swarm-control-in-sc2bot

> 생성: 2026-04-26 · 출처: PR #28 unblock 작업 중 백로그 전수조사
> 범위: 열린 PR / TODO·FIXME / pytest skip / IMPROVEMENT_TRACKER 사이클 6+ / CI 워크플로 / 의존성 / 포맷터

---

## 0. 2026-07-06 재점검 — ⚠️ PR 적체 심각 (최우선 조치 필요)

> 본 사이클(테스트→개선점검→커밋/푸시 반복) 재개 중 발견. 아래 항목이 다른 모든 작업보다 우선.

- **열린 draft PR 271건** (`#15` ~ `#309`, 전부 `claude/optimistic-edison-*` 브랜치). 표본 확인 결과
  대다수가 **동일한 결함**(`tests/test_combat_phase_fsm.py`의 `asyncio.get_event_loop()` →
  Python 3.11에서 `RuntimeError: no current event loop` 유발)을 반복해서 고치는 내용이었음.
  원인: 세션마다 새 브랜치에서 시작 → 아무 PR도 머지되지 않음 → `main`이 그대로 → 다음 세션이
  같은 버그를 "새로 발견"해서 또 고침 → PR만 계속 누적. `MASTER_TODO_SC2.md` §1.1(2026-04-26, 당시
  14건)에서 이미 경고했던 패턴이 방치되어 20배 가까이 악화됨.
- **실측**: 이번 세션 기준 `main`에는 여전히 버그가 살아있었음 — `pytest tests/`가 12 failed로 시작.
  `tests/test_combat_phase_fsm.py`(`asyncio.run()`로 교체) + `tests/conftest.py`
  (`PROTOCOL_BUFFERS_PYTHON_IMPLEMENTATION=python` 추가, 신규 환경에서 sc2/protobuf 임포트가
  깨지는 문제)를 고쳐서 **`tests/`: 505 passed / 11 skipped, `wicked_zerg_challenger/tests/`:
  661 passed — 0 failed**로 확인. 동일 수정이 담긴 PR이 이미 30개 이상 떠 있음(예: #309, #308, #307...).
- **권장 조치 (사용자 승인 필요 — 자동 실행 안 함)**:
  1. 위 PR 중 가장 완성도 높은 것(예: #309 — asyncio 수정 + conftest protobuf 수정 + 이슈 문서 정리 포함)을
     골라 **머지**하고 나머지 269건은 **일괄 close**. (본 리포의 원칙상 머지/대량 close는 사용자 승인 필요.)
  2. 향후 "매일 테스트/점검" 자동화는 **같은 브랜치·같은 PR을 이어서 갱신**하는 방식으로 바꿔야
     동일 문제 재발 방지 가능 (세션마다 새 브랜치를 파는 현재 방식이 근본 원인).
  3. 정리 전까지는 신규 PR 생성을 최소화하고, 실제로 아직 처리되지 않은 항목(§4 갱신판 참조)에
     집중 권장.

---

## 1. 백로그 인벤토리

### 1.1 열린 PR (16건)

| # | 브랜치 | 종류 | 상태 | 비고 |
|---|---|---|---|---|
| 28 | `claude/stoic-shannon-1YXPl` | Claude 개선 (사이클 1-5) | Draft, **CI fail → 패치 진행 중** | 본 작업의 primary target |
| 30 | `claude/stoic-shannon-Z9vz5` | "test/ci continuous" | Draft, UNSTABLE | PR #28과 동일 의존성 충돌로 fail (확인됨) |
| 29 | dependabot postcss 8.5.6 → 8.5.10 | npm | Open | 머지 가능성 검토 (sc2-ai-dashboard) |
| 27 | `claude/stoic-shannon-oIXtD` | Claude 개선 사이클 | Draft | #28과 중복/유사 가능성 |
| 26 | `claude/stoic-shannon-KzEhd` | Claude 개선 사이클 | Draft | 동일 |
| 25 | `claude/stoic-shannon-uPnyF` | "중심점 계산 통합" | Draft | 좁은 스코프 — 분리 머지 후보 |
| 24 | `claude/stoic-shannon-u6gfg` | "pytest-asyncio, encoding" | Draft | #28에 흡수됨 가능성 — 내용 비교 필요 |
| 23 | `claude/stoic-shannon-5hmXe` | "LURKER API + 로깅 잔재" | Draft | |
| 22 | `claude/stoic-shannon-AFhhZ` | "테스트 인프라 복구" | Draft | #28에 흡수됨 가능성 |
| 21 | dependabot npm group 9 updates | npm | Open | 머지 가능성 검토 |
| 20 | `claude/stoic-shannon-sRyBK` | "하네스 복구 + 품질 스윕" | Draft | |
| 19 | `claude/stoic-shannon-qsje5` | "sc2 미설치 환경" | Draft | #28에 흡수됨 가능성 |
| 18 | `claude/stoic-shannon-MJORZ` | "테스트 수집 오류 + sc2 stub" | Draft | #28에 흡수됨 가능성 |
| 17 | `claude/amazing-mccarthy-efzn4` | "P606 테스트 강화" | Draft | |
| 16 | `claude/amazing-mccarthy-Dc7bq` | "11-round +1130 tests" | Draft | 거대 PR — 분할 검토 |
| 15 | `claude/amazing-mccarthy-BsI3f` | "6가지 개선 + 353 passed" | Draft | |

**관찰**: Claude 사이클 PR이 14건 누적. 대부분 동일 영역(테스트 인프라/lint/dead-code)을 반복 작업한 흔적. 가장 최신·완성도 높은 PR(#28)을 baseline으로 삼고 나머지는 **전수 redundant 분석 후 close 또는 흡수**하는 게 합리적. 단, close 결정은 사용자 권한.

### 1.2 열린 이슈
**0건**. 백로그가 PR로만 쌓여있는 상태.

### 1.3 TODO/FIXME (27건 / 7 파일)

| 파일 | 건수 |
|---|---|
| `agent_inspector.py` | 5 |
| `code_gen_agent/sc2_code_generator.py` | 1 |
| `jarvis_features/productivity_features.py` | 8 |
| `modification_finder.py` | 5 |
| `tests/test_crypto_trading.py` | 1 |
| `wicked_zerg_challenger/local_training/advanced_building_manager.py` | 1 |
| `wicked_zerg_challenger/tools/check_missing_logic.py` | 6 |

대부분 보조 도구/테스트 영역. 봇 핵심 코드의 TODO는 적음. **티켓화 후 cycle 6+에서 일괄 처리**.

### 1.4 pytest skip / xfail (15건 / 4 파일)

| 파일 | 건수 |
|---|---|
| `tests/test_core_modules.py` | 2 |
| `tests/test_crypto_trading.py` | 5 |
| `tests/test_new_modules.py` | 2 |
| `tests/test_p606_modules.py` | 6 |

각 skip/xfail의 **이유 라벨링**이 필요 — 임시 회피인지, 환경 의존(sc2/torch)인지 분류해서 cycle 6+에서 정리.

### 1.5 IMPROVEMENT_TRACKER 사이클 6+ 후보 (PR #28 본문 기준)
- [ ] `integration_hub.py` 추가 결함 audit
- [ ] mypy strict-equality 정리
- [ ] 봇 핵심 코드 path-dependency / config-loader 일관성
- [ ] 보안 스캔(detect-secrets) 결과 점검
- [ ] CI에 `pytest tests/` 실패가 fail 빌드로 전파되는지 PR로 검증

### 1.6 CI 워크플로 분석

#### `ci.yml` (JARVIS CI/CD)
- 7개 잡: python-lint-test, sc2-bot-test, node-lint-test, docker-build, arena-package, replay-feedback, release-check, multi-language-benchmark, rust-check, go-check
- **현재 fail 원인**: `pip install -r requirements.txt` 단계에서 resolution-too-deep
- **PR #28 패치로 해소 예정** (S0)
- **추가 개선 후보**:
  - `pip install`을 `uv pip install`로 교체 (해석기가 ~10x 빠름, resolution-too-deep 거의 없음)
  - 의존성 캐시 최적화 (이미 cache: pip 활성)
  - matrix `fail-fast: false` 추가 (현재는 누락 — 한 잡 실패가 다른 매트릭스 잡 cancel)

#### `sc2bot-ci.yml` (SC2 Bot CI/CD Pipeline)
- lint matrix 3.10/3.11/3.12 → test → docker → push → deploy
- **lint 단계가 매우 엄격**: `black --check --diff .` + `isort --check-only --diff .` + `flake8 --max-line-length=100` + `mypy --strict` + `bandit -ll`
- **현재 main에서 모두 fail 추정** (black: 48+ 파일 미포맷, mypy strict: 거대 type 작업 필요, bandit -ll: 보안 경고)
- **현실적 옵션**:
  1. lint 잡을 **non-blocking으로 변경** (`continue-on-error: true`) — 단기 해법
  2. **점진적 도입**: 변경된 파일만 검사 (`black --check $(git diff --name-only origin/main...HEAD)`)
  3. main을 한 번에 black/isort 통과시키는 **포맷팅 전용 PR**을 별도로 운영
  4. 워크플로 자체 보류(disable) — `on:` 조건에서 PR 제외

### 1.7 의존성 강화 옵션
- **uv 도입**: pip 대비 해석기 빠름, lockfile 지원, resolution-too-deep 사실상 없음. `pyproject.toml` 추가 필요.
- **pip-tools(`pip-compile`)**: requirements.txt에서 `requirements.lock` 생성. CI는 lock 사용. 가장 가벼운 해법.
- **lockfile 미존재** → **deterministic 빌드 부재**. dependabot이 잘 작동하려면 lock 필요.
- 추천 단계: pip-tools 먼저 도입(저비용) → 안정화되면 uv 검토.

### 1.8 black / isort / ruff 통일
- 현재 `sc2bot-ci.yml`은 black + isort + flake8 + mypy 분리 설치
- **ruff 1개로 통합 권장**: black-호환 포맷, isort-호환 import order, flake8 룰 다수 포함, ~100x 빠름
- 이행 단계: ruff 추가 → 룰 매핑 → flake8/isort 제거 → black은 유지 또는 `ruff format` 사용
- 별도 PR로 진행 권장

### 1.9 테스트 커버리지 구멍
- PR #28 진척: 340 pass / 19 skip / 0 fail
- **커버리지 측정 부재**: `sc2bot-ci.yml`에 codecov 업로드는 있지만 임계값(threshold) 강제 없음
- 추천: `--cov-fail-under=70` 같은 임계값 추가, 핵심 모듈(combat_manager, economy_manager, opponent_modeling)은 더 높게(85%+)

---

## 2. 실행 계획 (S0–S4)

### S0 — PR #28 머지 가능 상태 만들기 ⏳ 진행 중
- [x] requirements.txt 핀 정비 (resolution-too-deep 회피)
- [x] black 포맷 적용 (PR #28이 변경한 파일에 한정, 48 files)
- [x] commit (`59c5b03`) 생성
- [ ] **push** (진행 중 — background)
- [ ] 새 CI run에서 `Python 의존성 설치` + `SC2 봇 의존성 설치` step 통과 확인
- [ ] `Lint & Type Check (3.10/3.11/3.12)` 통과 확인 (black 한정 — isort/mypy/bandit은 별 PR로 분리)
- [ ] PR #28 ready-for-review 전환 권장 (사용자 결정)

### S1 — 다른 열린 PR 정리 (사용자 결정 필요)
- [ ] PR #18~#27 vs #28 내용 redundancy 매트릭스 작성 (자동 가능)
- [ ] redundant PR은 close 권장 (실제 close는 사용자 승인)
- [ ] dependabot #21, #29는 머지 가능성 검토 — security/dev-dep 위주
- [ ] PR #16(거대) #17, #20, #23, #25 등 좁은 스코프 PR은 우선 검토 후 분할 머지 검토

### S2 — IMPROVEMENT_TRACKER 사이클 6+
- [ ] `integration_hub.py` 추가 결함 audit (PR #28 후속, 별 PR)
- [ ] mypy strict 도입 가능 영역 측정 — 모듈별 통과율 베이스라인
- [ ] config-loader 일관성 점검
- [ ] detect-secrets 결과 정밀 분석
- [ ] pytest 실패가 CI fail로 전파되는지 시나리오 PR

### S3 — CI 인프라 보강
- [ ] `ci.yml` `fail-fast: false` (간단)
- [ ] `pip` → `uv pip` 교체 (lockfile 필요 시 pip-compile 먼저)
- [ ] `sc2bot-ci.yml` lint 잡을 non-blocking 또는 변경 파일 한정 검사로 전환 (혹은 disable)
- [ ] black/isort/flake8 → ruff 통합 (별 PR)
- [ ] codecov threshold 추가

### S4 — 테스트 커버리지 / 문서
- [ ] pytest skip/xfail 15건 라벨링 + 분류
- [ ] TODO/FIXME 27건 티켓화 (issue 또는 코드 옆 주석에 ID)
- [ ] `IMPROVEMENT_TRACKER.md` 사이클 6+ 진행 표 추가
- [ ] 봇 핵심 모듈 README 보강 (combat/economy/opponent_modeling)

---

## 3. 위험 / 제약

- **머지 금지**: 모든 PR은 사용자 검토 후 머지. 자동 머지 안 함.
- **main/master 직접 push 금지**.
- **force push 금지** — 모든 변경은 신규 commit/신규 브랜치.
- **Secrets 미공개** — detect-secrets 결과는 외부로 노출 안 함.
- **광범위 black 포맷팅을 main에서 일괄 적용**하면 Claude PR 14건과 충돌 폭발. **PR 정리 후** 진행 필요.

---

## 4. 다음 액션 (추천 순서)

1. **S0 마무리** (자동, 진행 중): push → CI 통과 확인 → 사용자에게 PR #28 ready-for-review 권장
2. **S1.1 redundancy 매트릭스** 작성 (자동, 사용자 승인 불필요): PR #18~#27 vs #28 비교 표를 별 문서로
3. **S3.1 CI fail-fast: false** (단순 패치, 별 PR, 자동 가능)
4. **S3.2 pip-tools 도입** (별 PR, 검토 후 자동)
5. 그 외 S2/S3/S4 항목은 사용자 우선순위 협의 후 진행

---

## 5. 2026-07-06 백로그 재수집 (실제 미구현/중단 항목만 — §0 PR 중복 제외)

> 테스트 실행 + 코드 audit으로 재확인. §1.5/§1.9와 `PLAN-NIGHTLY.md` P2 항목 중 아직도 코드에
> 반영 안 된 것만 남김 (P2.1 FSM, 큐 트랜스퓨전 등은 이미 코드에 구현되어 있어 제외).

| 우선순위 | 항목 | 근거 | 상태 |
|---|---|---|---|
| 🟠 HIGH | PR 적체 정리 (§0) | 271건 open, 신규 작업 전 필수 | 사용자 승인 대기 |
| 🟡 MED | 벤치마크 러너 (`PLAN-NIGHTLY.md` P2.2) — 단일 커맨드로 N판 실행, APM/승률/서플라이 리포트 | 코드베이스에 `*benchmark*` 관련 실행 스크립트 부재 확인 | ❌ 미구현 |
| 🟡 MED | 빌드오더 설정 외부화 (P2.3) — `config/build_orders.yaml`로 상위 20개 하드코딩 값 이전 | `config/build_orders.yaml` 파일 부재 확인 | ❌ 미구현 |
| 🟢 LOW | 핵심 모듈 타입힌트/문서화 (P2.5) — `core/resource_manager.py`, `core/manager_factory.py` | 미착수 | ❌ 미구현 |
| 🟢 LOW | flake8 F401 (미사용 import) 49건 (`wicked_zerg_challenger/`, `tests/`) | 실측 (`flake8 --select=F401`) | ❌ 미정리 |
| 🟢 LOW | black 미포맷 61 파일 / isort 오류 다수 | 실측. §3 위험 항목대로 PR 적체 해소 전에는 대규모 적용 보류 권장 | ❌ 보류 |
| 🟢 LOW | REMAINING_ISSUES.md N9 — `tests/`+`wicked_zerg_challenger/tests/` 동시 collect 시 namespace 패키지 충돌 | 재현 조건 좁음, 분리 실행 시 미발현 | ❌ 미수정, 낮은 우선순위 |
| 🟢 LOW | codecov 임계값(`--cov-fail-under`) 미설정 | `sc2bot-ci.yml`에 업로드는 있으나 강제 없음 | ❌ 미구현 |
| ✅ DONE | `tests/test_combat_phase_fsm.py` asyncio 이벤트루프 버그 | 이번 세션 수정, 505+661 passed 확인 | 커밋 완료 (본 세션) |
| ✅ DONE | 신규 샌드박스에서 sc2/protobuf 임포트 깨짐 (`conftest.py`) | 이번 세션 수정 | 커밋 완료 (본 세션) |
