# MASTER TODO — Swarm-control-in-sc2bot

> 생성: 2026-04-26 · 출처: PR #28 unblock 작업 중 백로그 전수조사
> 범위: 열린 PR / TODO·FIXME / pytest skip / IMPROVEMENT_TRACKER 사이클 6+ / CI 워크플로 / 의존성 / 포맷터

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

## 5. 2026-07-09 사이클 — 테스트 인프라 + 정적 감사 백로그

PR #360 (`claude/optimistic-edison-vtj9ds`)에서 처리/발견한 내용.

### 5.1 이번 사이클에서 수정 완료
- [x] `tests/test_queen_transfusion.py` — sc2 미설치 시 전체 423개 테스트 collection이 죽는 버그 (unguarded import) → skip guard 추가
- [x] `tests/test_combat_phase_fsm.py` — `asyncio.get_event_loop().run_until_complete()` deprecated 패턴이 12개 테스트를 fail시킴 → `asyncio.run()`으로 교체
- [x] `.github/workflows/ci.yml` `python-lint-test` 잡의 `pytest 실행 (전체)` 스텝에 `PROTOCOL_BUFFERS_PYTHON_IMPLEMENTATION: python` 누락 — main에서도 이미 fail 중이던 사전 존재 버그 (14개 파일 collection 실패, `TypeError: Descriptors cannot be created directly`). `sc2-bot-test` 잡에는 이미 있던 설정을 동일하게 추가.
- [x] `wicked_zerg_challenger/economy_manager.py::_check_proactive_expansion` — `_perform_smart_expansion()` 실패 시 `expand_now()`/황금기지 폴백(~40줄)이 도달 불가능한 dead code였음 (직전 unconditional `return`). 폴백이 실제로 실행되도록 수정 + 회귀 테스트 추가.

### 5.2 정적 감사로 발견, 아직 미착수 (우선순위순)
백그라운드 에이전트가 `wicked_zerg_challenger/`를 AST 파싱 + grep으로 감사 (sc2/numpy/torch 미설치 환경이라 런타임 실행은 불가, 전부 정적 분석 기반):

- [ ] **`strategy/timing_attacks.py`**: `ZERGLING_TIMING = 240`(4분) 상수가 정의만 되고 어디서도 비교에 쓰이지 않음. `_check_timing_windows`가 `ROACH_TIMING`(420s)과 `MUTA_TIMING`(360s)만 분기하며, `_ready_for_zergling_timing`/`_initiate_zergling_timing` 류의 메서드가 존재하지 않음 — 저글링/바네링 올인 타이밍이 실제로는 발동 안 함. 게다가 `if ROACH_TIMING: ... elif MUTA_TIMING: ...` 구조라 420초 이후엔 뮤탈 타이밍도 영구히 막힘 (roach push 조건이 안 맞으면 7분 이후 어떤 타이밍 공격도 발동 안 할 수 있음). **확인 필요**: 의도된 설계인지 미완성 스케줄러인지 사람 판단 필요 — 코드만 보고 "고쳐야 할 버그"로 단정하기엔 게임플레이 의도를 알아야 함.
- [ ] **`strategy_manager.py`**: `_blackboard_flag()`로 읽지만 어디서도 set되지 않는 플래그들 — `"dark_shrine_scouted"`(실제 생산자는 `"dark_shrine"`, 키 불일치), `"blink_stalker_allin"`, `"disruptor_nova"`, `"enemy_roach_all_in"`, `"dark_templar_detected"`. 각각 동일 조건을 직접 구조/구성 체크로도 백업하고 있어서 현재 동작에 영향은 없어 보이지만, 죽은 분기이므로 정리하거나 실제로 blackboard에 채워주는 producer를 추가해야 함.
- [ ] **`intel_manager.py:76-80`**: `BUILD_PATTERNS["nydus_rush"]["units"]`에 `QUEEN/ROACH/HYDRALISK`가 들어있음 — ZvZ에서 흔한 유닛이라 나이더스와 무관하게 confidence를 인위적으로 올릴 수 있음. 복붙 실수로 추정, 나이더스 웜 등으로 교체 검토.
- [ ] **`strategy_manager.py:2536`** `_counter_zerg_units()`: `ravager_count`를 계산만 하고 미사용 — Ravager 전용 카운터 룰이 빠진 것으로 보임 (사소, 크래시 없음).
- [ ] **`scouting_system.py:237`** `deploy_changeling()` — 어디서도 호출 안 되는 dead method. 실제 체인질링 배치는 `scouting/advanced_scout_system_v2.py::_manage_changelings()`에 중복 구현되어 있고 그게 실제 on_step에서 호출됨. 정리 대상(둘 중 하나로 통합) — 로드맵 Task 2.5가 가리키는 파일도 최신화 필요.
- [ ] **문서-코드 불일치**: `ROADMAP.md`가 참조하는 `wicked_zerg_challenger/build_order_executor.py`가 실제로 존재하지 않음 (`build_order_system.py`로 대체된 듯). 로드맵 파일맵 갱신 필요.
- [ ] **인코딩 잔재**: Task 1.1이 "완료"로 표기돼 있지만 `unit_factory.py`, `dynamic_resource_balancer.py`, `local_training/reward_system.py`, `local_training/aggressive_tech_builder.py`, 일부 `tools/*.py`에 이중 인코딩된 한글 주석(모지바케)이 남아있음. UTF-8로는 유효해서 컴파일엔 문제없음 — 가독성 이슈만.
- [ ] **`combat_manager.py:3490`** `non_combat_names` — 정의만 되고 미사용 (동일 결과가 앞선 early-return으로 이미 보장됨). 사소한 dead code.

### 5.3 감사에서 "문제 없음"으로 확인된 항목 (재작업 불필요)
- 핵심 6개 게임플레이 파일(`combat_manager.py`, `economy_manager.py`, `strategy_manager.py`, `intel_manager.py`, `scouting_system.py`, `early_defense_system.py`)에 TODO/FIXME 없음
- `wicked_zerg_challenger/` 전체에 AST 기준 중복/shadow 메서드 정의 없음 (이전 사이클에서 이미 정리됨)
- 로드맵 Sprint 1-8 중 1.2, 1.3, 2.1, 2.2, 2.3, 2.5(부분), 3.1, 3.2, 3.3, 4.1, 4.3, 4.5, 5.1, 6.1, 7.1, 7.2는 실제로 구현되어 on_step/매니저 등록에 연결되어 있음을 코드로 확인
