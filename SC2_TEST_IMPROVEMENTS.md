# SC2 지휘관봇 — 테스트 기반 개선 리스트

> 생성: 2026-05-09 · 출처: 테스트 환경 구축 + pytest 결과 분석
> 브랜치: `claude/stoic-shannon-x690U`

## 0. 테스트 환경 셋업 결과

| 항목 | 상태 |
|---|---|
| `wicked_zerg_challenger/` 테스트 수집 | 659 collected, **1 collection error** (test_sprint8_qa.py — needs mpyq) |
| `wicked_zerg_challenger/` 테스트 결과 | **659 passed** (sprint8 제외) |
| `wicked_zerg_challenger/` 경고 | **138 warnings** (119 DeprecationWarning + 18 RuntimeWarning + 1 ResourceWarning) |
| 루트 `tests/` 결과 | 478 passed, **5 failed** (test_security.py, pyo3_runtime), 5 skipped |
| 누락 의존성 발견 | `numpy`, `protobuf`, `loguru`, `s2clientprotocol`, `burnysc2`, `mpyq`(빌드 실패) |

## 1. 즉시 수정 가능한 이슈 (Batch 1)

### 1.1 `test_production_resilience.py` — async/unittest.TestCase 충돌 (RuntimeWarning + DeprecationWarning)
- **현상**: `class TestProductionResilience(unittest.TestCase):` 안에 `async def test_*` 메서드 9개가 정의돼 있음
- **결과**: 코루틴이 await 없이 반환 → 실제로는 테스트 본문이 실행되지 않고 통과로 판정됨
- **위험도**: 🚨 매우 높음 — 9개 테스트가 사실상 빈 통과
- **수정**: `unittest.TestCase` → `unittest.IsolatedAsyncioTestCase` 로 교체
- **영향 메서드** (9개):
  - `test_safe_train_success`
  - `test_safe_train_invalid_unit`
  - `test_safe_train_no_train_method`
  - `test_safe_train_with_retry`
  - `test_get_counter_unit_terran_marine`
  - `test_get_counter_unit_protoss`
  - `test_get_counter_unit_zerg`
  - `test_auto_extractors_wait_for_opening_hatchery`
  - `test_auto_second_extractor_waits_for_third_base`

### 1.2 `test_opponent_modeling.py` — 동일 문제 (TestOpponentModeling 클래스)
- **현상**: 같은 async-on-unittest.TestCase 패턴
- **수정**: `class TestOpponentModeling(unittest.TestCase):` → `IsolatedAsyncioTestCase`
- **영향 메서드** (9개):
  - `test_on_start_new_opponent`
  - `test_on_start_known_opponent`
  - `test_detect_fast_expand_signal`
  - `test_detect_early_pool_signal`
  - `test_detect_no_natural_signal`
  - `test_detect_early_army_signal`
  - `test_timing_attack_detection`
  - `test_timing_attack_cooldown`
  - `test_full_game_flow`

## 2. 수집 단계 오류 (Batch 2)

### 2.1 `test_sprint8_qa.py` 수집 실패 — mpyq 미설치
- **현상**: `run_mass_test.py`가 `from sc2.main import run_game` → `mpyq` 임포트 → 빌드 실패
- **근본 원인**: mpyq는 source-only 패키지이고 빌드 환경에 따라 컴파일 실패
- **수정**: `run_mass_test.py`의 sc2.main import를 try/except로 감싸 mpyq 미설치시 graceful skip
- **부수 효과**: CI에서 sprint8_qa 테스트가 항상 실행될 수 있음

### 2.2 `scouting/advanced_scout_system_v2.py` — silent stub 패턴이 위험함
- **현상**: `try: from sc2.* import * except ImportError: class UnitTypeId: pass` 패턴이 sc2 누락시 빈 스텁 생성 → 런타임 AttributeError를 collect time에야 잡음
- **수정 방향**:
  - 옵션 A: 스텁이 적어도 `OVERLORD` 등 자주 쓰는 enum 멤버는 표시하도록 fake enum 채움
  - 옵션 B: 스텁 진입시 명시적 로그/RuntimeError를 발생시켜 누락을 빨리 인지

## 3. 보안 테스트 실패 — 환경 의존 (Batch 3, 별도 PR 후보)
- `tests/test_security.py` 5건 실패 (pyo3_runtime.PanicException)
- 원인: cryptography 패키지 ABI 불일치 (Rust 바인딩)
- 수정 권장: 테스트 자체에 `pytest.importorskip` 또는 try/except로 graceful skip

## 4. 누락된 dev 의존성 정리 (Batch 3)
`requirements-dev.txt`에 다음을 추가/확인 권장:
- `pytest>=7.0`
- `pytest-asyncio>=0.21`
- `numpy`
- `protobuf`
- `loguru`
- `s2clientprotocol`
- `burnysc2`
- (선택) `mpyq` — wheel이 없어 빌드 실패 가능, optional dependency로 분리 추천

## 5. 추가 발견 사항

### 5.1 `pytest.ini`의 `--disable-warnings`
- 현재 `addopts = -v --strict-markers --tb=short --disable-warnings --color=yes`
- `--disable-warnings`가 138개의 의미있는 경고를 숨김
- 권장: 임시 제거 후 cleanup, 그 후 다시 활성화하거나 `filterwarnings` 화이트리스트로 대체

### 5.2 ResourceWarning 1건 (subprocess 미정리)
- 출처는 `_pytest`/내부 — 확인 필요

### 5.3 mpyq 패키지 정책
- mpyq는 SC2 리플레이 파싱에만 필요 — CI/단위 테스트에서는 optional 처리 가능

## 실행 계획

| 배치 | 작업 | 결과 |
|---|---|---|
| **Batch 1** ✅ | async TestCase → IsolatedAsyncioTestCase + 4 hidden bug 수정 | 659 → 660 pass, 138 → 102 warnings |
| **Batch 2** ✅ | run_mass_test mpyq guard + scout 스텁 안전화 | 660 → **662 pass** (sprint8_qa 복구) |
| **Batch 3** ✅ | pytest.ini cleanup + EnhancedScout lazy-import + dev deps | **662 pass, 0 warnings** (was 102) |
| **Batch 4+** | 추가 사이클 — 매 사이클마다 테스트 재실행 후 신규 발견 사항 처리 | 진행 중 |

## Batch 1-3 누적 성과

| 지표 | Before | After |
|---|---|---|
| 테스트 통과 수 | 659 | **662** |
| 수집 오류 | 1 | **0** |
| 경고 | 138 | **0** |
| 숨겨진 버그 (async 미실행으로 가려진) | 4 | **0** |
| `pytest.ini --disable-warnings` 차단막 | 활성 | 제거됨 (filterwarnings로 대체) |

## 다음 사이클 후보 (Batch 4+)

- [ ] 루트 `tests/test_security.py` 5건 실패 — pyo3_runtime 환경 의존성 graceful skip
- [ ] mypy strict 도입 가능 영역 측정 (PR #28에서 누락된 항목)
- [ ] 봇 핵심 모듈 커버리지 측정 (`pytest-cov` + `--cov-fail-under=70`)
- [ ] 다른 `try/except ImportError` 스텁 패턴 (`enhanced_scout_system.py`, `phase_scout_cadence.py`)에도 lenient stub 적용 검토
- [ ] CI 워크플로의 `pip install`을 `uv pip install`로 교체 (resolution-too-deep 해결)
- [ ] `mpyq`를 optional extra로 분리 (e.g. `pip install ".[replay]"`)
