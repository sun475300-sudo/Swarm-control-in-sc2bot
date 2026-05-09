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

## Cycle 4 (예정) — 잔여 F841 + 함수 중복 추가 audit + CI fail-fast 검토

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
