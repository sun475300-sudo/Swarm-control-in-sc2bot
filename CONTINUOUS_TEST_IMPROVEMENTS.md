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

## Cycle 2 (예정) — 코드 품질 / 정적 분석 / 잠재적 결함

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
