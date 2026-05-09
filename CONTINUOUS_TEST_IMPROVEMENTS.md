# Continuous Test Improvements — SC2 Commander Bot

> 시작: 2026-05-09
> 브랜치: `claude/stoic-shannon-ygtAO`
> 목표: 테스트 → 개선사항 발견 → 대규모 리스트화 → 적용 → 커밋·푸시 → 반복

---

## Cycle 1 (현재 진행) — 테스트 수집·실행 정상화

### 발견된 이슈 (테스트 수행 중)

| # | 카테고리 | 이슈 | 우선순위 |
|---|---|---|---|
| C1.1 | Test infra | `tests/test_queen_transfusion.py` 모듈 import 단계에서 `sc2` 미설치 환경 collection-fail | High |
| C1.2 | Test infra | pytest 도구 환경(uv tool venv)에 `pytest-asyncio` 미설치 → async 테스트 83건 일괄 실패 | High |
| C1.3 | Test infra | pytest 도구 환경에 `numpy`/`pyyaml` 미설치 → 14건 skip | Medium |
| C1.4 | Test names | `tests/test_p606_infra.py`가 실제로는 존재하지 않는 클래스명(`FuzzTarget`, `ContractViolation`, `PackageType`, `ProfileMetric`)을 import 시도 → 4건 skip | Medium |
| C1.5 | Test stub | `comprehensive_test_suite.py`는 하드코딩된 가짜 결과(700개 fuzz 중 300 통과 등)를 반환 — 실제 테스트가 아님 | Low |
| C1.6 | Test infra | `tests/test_security.py::test_no_hardcoded_keys_in_yaml`가 `config.yaml` 부재로 skip | Low |
| C1.7 | Test infra | `tests/test_crypto_trading.py`의 `pyupbit/pandas` 의존성 skip 9건 — bot 본업과 무관한 영역 | Low |

### Cycle 1 적용된 fix
- C1.1 fix: `tests/test_queen_transfusion.py` — `try/except ImportError` + `pytest.skip(allow_module_level=True)` 가드 추가
- C1.2 fix: pytest 도구 환경 재설치 (uv tool install --with pytest-asyncio --with pytest-timeout --with pytest-mock)
- C1.3 fix: pytest 도구 환경에 numpy/pyyaml 추가
- C1.4 fix: `tests/test_p606_infra.py` — Fuzz/Contract/SBOM/Performance 클래스명을 실제 모듈에 존재하는 이름으로 수정 (`SC2Fuzzer`, `Contract`, `SBOMGenerator`, `SC2Profiler`)

### Cycle 1 결과
- pytest 시작점: collection 실패(1) + 5 skip
- pytest-asyncio 설치 후: 392 pass / 34 skip (async 83건 복구)
- numpy 설치 후: 425 pass / 20 skip
- p606_infra 클래스명 fix 후: **429 pass / 16 skip**

---

## Cycle 2 (완료) — 코드 품질 / 정적 분석 / 잠재적 결함

### 발견된 이슈

| # | 카테고리 | 이슈 | 우선순위 |
|---|---|---|---|
| C2.1 | Real bug | `wicked_zerg_challenger/opponent_modeling.py`에 `OpponentModeling.on_step`이 두 번 정의(341, 765) → 두 번째가 첫 번째를 덮어 build-order/timing-attack/tech-progression 추적 + blackboard 업데이트가 dead code | **High (게임 로직 회귀)** |
| C2.2 | Dead code | `combat_manager.py`의 `_find_harass_target`가 두 번 정의 (2809, 5005) | Medium |
| C2.3 | Dead code | `economy_manager.py`의 `_prevent_resource_banking` 두 번 정의 (1685, 3262) — queens+spores 정적 방어 로직이 무효화 | Medium |
| C2.4 | Dead code | `economy_manager.py`의 `_reduce_gas_workers` 두 번 정의 (3395, 4086) | Medium |
| C2.5 | Dead code | `local_training/production_resilience.py`의 `build_terran_counters` 두 번 정의 (1450, 1960) — TechCoordinator 인지 버전이 단순 버전을 덮음 | Medium |
| C2.6 | Lint | `scouting/phase_scout_cadence.py`에 `typing.Tuple` 사용처 없음 | Low |
| C2.7 | Lint | `scouting_system.py`에 `typing.Iterable` 사용처 없음 | Low |
| C2.8 | Test infra | `requirements-dev.txt`에 `numpy`/`pyyaml` 누락 → 신규 환경에서 다시 14건 skip 발생 | Medium |
| C2.9 | Test infra | `pytest.ini`의 `addopts`에 `-ra` 누락 → skip 사유가 표시되지 않아 회귀 추적이 어려움 | Low |

### Cycle 2 적용된 fix

- C2.1: `opponent_modeling.py` — 단순한 두 번째 `on_step` 삭제, 완전한 첫 번째 `on_step`(blackboard 업데이트 포함)이 실행되도록 복원
- C2.2: `combat_manager.py` — 단순한 첫 번째 `_find_harass_target` 삭제, 정교한 worker-priority 두 번째 버전 유지
- C2.3: `economy_manager.py` — 첫 번째 `_prevent_resource_banking`을 `_legacy_prevent_resource_banking_static_defense`로 rename (코드 보존)
- C2.4: `economy_manager.py` — 첫 번째 `_reduce_gas_workers`를 `_legacy_reduce_gas_workers_simple`로 rename
- C2.5: `production_resilience.py` — 첫 번째 `build_terran_counters`를 `_legacy_build_terran_counters_simple`로 rename
- C2.6/2.7: 미사용 typing import 제거
- C2.8: `requirements-dev.txt`에 numpy/pyyaml 추가
- C2.9: `pytest.ini` `addopts`에 `-ra` 추가

### Cycle 2 결과

- flake8 F811 경고: **5건 → 0건**
- flake8 F401 (production code): **2건 → 0건**
- pytest: **429 pass / 16 skip 유지** (회귀 없음)
- 잠재 위험 회귀 1건(`opponent_modeling.on_step`) 실제로 게임 로직 영향이 있었던 것으로 판단

---

## Cycle 3 (완료) — F841 / E713 정리 + 변경 파일 black 포맷

### 발견된 이슈

| # | 카테고리 | 이슈 | 우선순위 |
|---|---|---|---|
| C3.1 | Real bug | `bot_step_integration.py:1225-1229` `micro_interval` 변수가 두 번 할당되지만 어디에도 사용되지 않음 (`micro_focus.update()`의 반환값 사용처 없음) | Low (no behavior loss, just dead) |
| C3.2 | Real bug | `bot_step_integration.py:2907` `current_mode_str = "Unknown"` 후 사용처 없음 (의도된 로깅이 누락된 흔적) | Low |
| C3.3 | Lint | `bot_step_integration.py`에 silent exception swallow 패턴 11곳 (`except Exception as e:` + `if debug_mode: raise`) — `e`만 미사용 | Low |
| C3.4 | Lint | `base_destruction_coordinator.py:189`, `combat/infestor_tactics.py:256` E713: `not x in y` → `x not in y` (가독성) | Low |
| C3.5 | CI | PR #128의 sc2bot-ci.yml `Lint & Type Check (3.11)`가 black 검사에서 실패 — Cycle 1/2 변경 파일이 black 미적용 | Medium |

### Cycle 3 적용된 fix

- C3.1: `micro_interval` 변수 제거, `self.bot.micro_focus.update(iteration)` 반환값 무시 + 코멘트 추가
- C3.2: `current_mode_str = "Unknown"` 라인 삭제
- C3.3: 11건의 `except Exception as e:` → `except Exception:` (e 미사용)
- C3.4: 두 곳 `not x in y` → `x not in y`
- C3.5: 변경한 9개 파일에 `black` 적용 (touched-files-only 정책 준수)

### Cycle 3 결과

- F841 (production code): **30+ → 19** (남은 19건은 cycle 4+에서 검토)
- E713: **2 → 0**
- pytest: **429 pass / 16 skip 유지**
- black: 변경 파일 9개 모두 통과

---

## Cycle 4 (완료) — 잔여 F841 의심 항목 4건 + 추가 정적분석 후속

### 발견된 이슈

| # | 카테고리 | 이슈 | 우선순위 |
|---|---|---|---|
| C4.1 | Dead code | `combat_manager.py:3482` `non_combat_names` set이 정의만 되고 필터에 적용되지 않음 (`nearby_combat`은 `combat_unit_names`만 사용) | Low |
| C4.2 | Dead code | `economy_manager.py:328` `early_window = game_time <= 240.0` — pressure 게이트 리팩터링 후 잔재 | Low |
| C4.3 | Latent config bypass | `creep_manager.py:280` `spread_range = self.TUMOR_SPREAD_RANGE` 후 하드코딩 `[7.0, 9.0]` 사용. 변수만 죽었지만 동시에 config 상수가 무력화됨을 노출 | Medium (config-vs-hardcode 일관성) |
| C4.4 | Latent priority bypass | `build_order_system.py:1058` `PRIORITY_EXPANSION = 55` 정의 후 `tech_coordinator.request_structure(...)`를 호출하지 않고 `worker.build` 직접 호출 → 우선순위 시스템 우회 | Medium (TechCoordinator 일관성) |

### Cycle 4 적용된 fix

- C4.1: 사용되지 않던 `non_combat_names` 삭제
- C4.2: `early_window` 변수 삭제
- C4.3: `spread_range` 변수 삭제 + 하드코딩 의도를 코멘트로 명시 (실제 배선은 cycle 5+에서)
- C4.4: `PRIORITY_EXPANSION` 변수 삭제 + 우선순위 미배선이 의도적이라기보다 누락임을 코멘트로 표시 (실제 배선은 cycle 5+에서)

### Cycle 4 결과

- F841 (production code, non-e): 30+ → **26** (의심 4건 정리)
- pytest: 429 pass / 16 skip 유지
- C4.3, C4.4는 후속 사이클에서 본격 배선 검토 필요한 latent bug로 식별

---

## Cycle 5 (완료) — TechCoordinator 배선 + silent-swallow 가시화

### 발견된 이슈 / 적용

| # | 카테고리 | 이슈 | 적용 |
|---|---|---|---|
| C5.1 | Real fix (latent) | C4.4 후속: `build_order_system.py`의 자연 확장이 `TechCoordinator.request_structure`를 거치지 않아 우선순위 시스템 우회 | `request_structure(UnitTypeId.HATCHERY, location, PRIORITY_EXPANSION=55, requester_name=...)`로 라우팅. 동일 슬롯에 더 낮은 우선순위 요청이 들어와 있으면 거절되도록 동작 |
| C5.2 | Visibility | C3.3 후속: bot_step_integration.py에 silent-swallow 11곳이 catch-all + `if debug_mode: raise`만 가지고 있어 비-디버그 운영에서 모든 매니저 step 실패가 묻힘 | `_log_swallowed(name, exc)` 헬퍼 추가 (canonical CreepDenial 패턴과 동일한 rate-limited 로깅) + 11개 사이트(SpatialOptimizer, DataCache, BaseDestruction, BuildingDestroyer, SelfHealing, Personality, BattlePrep, DestructibleAware, NydusTrainer, OverlordSafety, AstarHighway)에 호출 추가 |
| C5.3 | Process | C4.3(`creep_manager.py` ring distances ↔ `TUMOR_SPREAD_RANGE`)는 행동을 바꾸는 변경이므로 cycle 6 이후로 보류 | 기록만 |

### Cycle 5 자가 회귀 (helper 메서드 위치 실수 → 즉시 fix)

- `_log_swallowed`를 처음에는 `__init__` 본문 도중에 삽입 → __init__가 거기서 종료되어 lines 397+에서 `bot` 파라미터가 F821 미정의로 떨어짐
- 헬퍼를 `__init__` 다음(`initialize_managers` 직전)으로 이동 후 회복
- 교훈: 메서드 삽입 시 항상 인접 메서드 boundary 확인

### Cycle 5 결과

- F821 (production code): 0 유지 (자가 회귀 즉시 fix)
- pytest: 429 pass / 16 skip 유지
- 행동 변화 (의도된 것)
  - 자연 확장이 TechCoordinator queue로 라우팅되며 우선순위 55 이하 요청은 거절될 수 있음
  - 11개 매니저 step 실패가 비-디버그 모드에서도 rate-limited 로그로 표시됨 (이전: 완전 침묵)

---

## Cycle 6 (완료) — 봇 외부 디렉토리 F811 정리

### 발견된 이슈

| # | 카테고리 | 이슈 | 우선순위 |
|---|---|---|---|
| C6.1 | Lint | `discord_advanced_features.py`에 함수 안에서 모듈 레벨로 이미 import된 `os`, `asyncio`를 재import (3곳) | Low |
| C6.2 | Lint | `cirq_quantum/quantum_circuits.py:187` `cirq` 재import (try 블록에서 이미 import됨, 함수 진입은 CIRQ_AVAILABLE 게이트로 보호됨) | Low |
| C6.3 | Lint | `jax_flax_rl/flax_policy.py:208` `math` 재import (모듈 레벨에 이미 있음) | Low |
| C6.4 | Lint | `pennylane_qml/quantum_policy.py`에 `import numpy as np` 함수 내 재import 2곳 (PENNYLANE_AVAILABLE 게이트로 보호되어 모듈 레벨 import는 항상 살아있음) | Low |
| C6.5 | Lint | `spark_jobs/sc2_replay_analytics.py:11`에서 `dataclasses.fields` import → 같은 이름의 함수 파라미터로 shadow됨. import는 다른 곳에서 사용 안 됨 | Low |
| C6.6 | Lint | `tianshou_rl/tianshou_trainer.py`에 `torch` 재import 3곳 (TIANSHOU_AVAILABLE 게이트 안쪽) | Low |

### Cycle 6 적용된 fix

- C6.1: 함수 내 redundant `import os`, `import asyncio` 제거
- C6.2: 함수 내 `import cirq` 제거 (모듈 레벨에 이미 있음)
- C6.3: 함수 내 `import math` 제거
- C6.4: 함수 내 `import numpy as np` 두 곳 제거 + 코멘트로 게이트 의존성 명시
- C6.5: `from dataclasses import` 줄에서 사용처 없는 `fields` 제거
- C6.6: 함수/메서드 내 `import torch` 세 곳 제거

### Cycle 6 결과

- F811 (전체 codebase): **16 → 5** (남은 5건은 wicked_zerg_challenger/ 외부 노이즈가 아닌 실제 wicked_zerg_challenger 자체의 5건이 cycle 2에서 이미 처리됨)
- pytest: 429 pass / 16 skip 유지
- black: 변경 6개 파일 모두 통과

---

## Cycle 7 (완료) — comprehensive_test_suite.py 실제 pytest 연동

### 발견된 이슈

| # | 카테고리 | 이슈 | 우선순위 |
|---|---|---|---|
| C7.1 | Test infra (가짜 데이터) | `comprehensive_test_suite.py`가 하드코딩 결과(unit 7/7, fuzz 700/300, etc.)를 반환하여 비과적/오해 유발 보고서 생성 | Medium |
| C7.2 | Test infra | `python-sc2`는 `mpyq` wheel 빌드 실패로 일반 환경에 설치 불가 → sc2 의존 5건은 stub 작업이 cycle 8+ 후속 | Note |

### Cycle 7 적용된 fix

- C7.1:
  - `comprehensive_test_suite.py`를 실제 `pytest tests/` 호출로 교체
  - 결과를 파일명 휴리스틱(`unit/integration/matchup/edge/fuzz/regression/benchmark`)으로 카테고리화
  - ANSI 색상 escape 코드 strip + `--color=no`로 안전한 파싱
  - 실행 binary는 PATH의 `pytest` 우선 (uv tool venv가 plugin 셋업되어 있음), 폴백으로 `python -m pytest`
  - 수치: 0/759(가짜) → 429/445(실측)
- C7.2: 별도 사이클로 보류 (real fix는 sc2 stub 패키지 작업 필요)

### Cycle 7 결과

- 실측 보고: **445 total / 429 pass / 0 fail / 16 skip / 96.4% pass rate**
- 카테고리별 정확한 분류 출력
- pytest: 회귀 없음 (테스트 자체는 변경되지 않음, runner만 교체)

---

## Cycle 8 (완료) — 최소 sc2 stub 주입으로 5건 sc2-skip 해소

### 발견된 이슈

| # | 카테고리 | 이슈 | 우선순위 |
|---|---|---|---|
| C8.1 | Test infra | `python-sc2`/`burnysc2`가 `mpyq` wheel 빌드 실패로 일반 환경 설치 불가 → 5개 테스트 모듈(74개 테스트) 영구 skip | High |

### Cycle 8 적용된 fix

- `tests/conftest.py`에 모듈 레벨 sc2 stub 주입자 추가:
  - 실제 `sc2`가 import 가능하면 그대로 사용
  - 없으면 `sys.modules`에 다음을 채워 넣음:
    - `sc2`, `sc2.ids`, `sc2.ids.unit_typeid`, `sc2.ids.ability_id`, `sc2.ids.upgrade_id`, `sc2.position`, `sc2.unit`, `sc2.units`, `sc2.bot_ai`
  - `_Identifier`(UnitTypeId/AbilityId/UpgradeId)는 attribute access 시 캐시된 `_Member` 반환
  - `_Member`는 `__slots__ + __eq__ + __hash__`로 dict key 사용 가능 (`HEAL_PRIORITY: Dict[UnitTypeId, int]`에서 필수)
  - `_Point2`는 tuple 서브클래스 + `x/y/distance_to`
  - `_Unit`/`_Units`/`_BotAI`는 빈 placeholder

### Cycle 8 결과

- pytest: **429 → 503 pass / 16 → 10 skip** (74개 테스트 신규 활성화)
- 활성화된 테스트 모듈:
  - `test_advanced_scout_system_v2.py`
  - `test_harassment_coordinator.py`
  - `test_queen_transfusion.py`
  - `test_queen_transfusion_manager.py`
  - `test_spatial_query_optimizer.py`
- 남은 10 skip: 모두 crypto_trading (pyupbit/config.yaml 의존) + security (config.yaml 의존)
- 회귀: 기존 테스트 0건 영향 (실제 sc2가 있으면 stub 우회 — 안전)

### 누적 진척

| Cycle | pass | skip | F811 (prod) | F401 (prod) | E713 |
|---|---|---|---|---|---|
| 시작 | collection-fail | 5 | 5 | 2 | 2 |
| C1 | 392 | 34 | 5 | 2 | 2 |
| C2 | 429 | 16 | 0 | 0 | 2 |
| C3 | 429 | 16 | 0 | 0 | 0 |
| C4 | 429 | 16 | 0 | 0 | 0 |
| C5 | 429 | 16 | 0 | 0 | 0 |
| C6 | 429 | 16 | 0 | 0 | 0 |
| C7 | 429 | 16 | 0 | 0 | 0 |
| C8 | **503** | **10** | 0 | 0 | 0 |

---

## Cycle 9 (예정)

- C4.3: `creep_manager.py` ring distances를 `TUMOR_SPREAD_RANGE` 기반으로 결정 (행동 변경 — 회귀 시나리오 확인 필요)
- 잔여 F841 22+ 건 audit
- 10건 skip 검토 (config.yaml stub vs. 진짜 환경 게이트)
- pytest 커버리지 측정 도입

### 후보 작업 영역

#### 2.1 정적 분석 / Lint
- `flake8 wicked_zerg_challenger/` 실행 → 미해결 lint 위반 카운트
- 핵심 모듈(combat_manager, economy_manager, expansion_manager) 한정 type hint 보강
- 상위 30개 함수 cyclomatic complexity 측정

#### 2.2 봇 핵심 로직 단위테스트 보강
- `wicked_zerg_challenger/economy/queen_transfusion_manager.py` — 추가 엣지케이스 (다중 큐인, 동시 캐스트 경합)
- `wicked_zerg_challenger/expansion/expansion_timing.py` — 자원/공급/적정 타이밍 테스트 확장
- `wicked_zerg_challenger/combat/combat_manager.py` — 후퇴/재공격 경계 조건

#### 2.3 의존성 / 환경 정합성
- `requirements-dev.txt`에 numpy/pyyaml 추가하여 신규 환경에서도 동일 결과 보장
- pytest config — `addopts`에 `--strict-markers`/`-ra`(skip 사유 표시) 추가 검토

#### 2.4 테스트 더미 정리
- `comprehensive_test_suite.py` 등 하드코딩된 가짜 결과 테스트 → 실제 pytest 호출로 교체 또는 deprecation 표시

#### 2.5 CI / 메타
- `.github/workflows/ci.yml` 의존성 설치 단계에 `pip install -r requirements-dev.txt` 포함 여부 검사

---

## Cycle 3+ (백로그)

- `MASTER_TODO_SC2.md` S2/S3/S4 항목 흡수 (mypy strict, ruff 통합, codecov threshold)
- `agent_inspector.py`, `modification_finder.py`의 TODO 5건씩 티켓화
- skip된 sc2 라이브러리 의존 테스트 — 모듈 단위 stub로 대체 가능 영역 식별
- `discord_jarvis.py`(155K) / `discord_bot_features.py`(46K) 분할/리팩터 검토

---

## 운영 규칙 (반복 사이클)

1. 사이클 시작 시 `pytest tests/ -rs` 실행 → 변동 사항 캡처
2. 발견된 이슈를 본 문서의 새 cycle 섹션에 기록
3. 가장 안전·고이득 fix 1~3건 우선 적용
4. 각 fix는 별도 commit (이유 위주 메시지)
5. 완료 후 push → 다음 사이클로
6. **머지/PR 자동 머지 금지, force push 금지, 메인 브랜치 직접 변경 금지**
