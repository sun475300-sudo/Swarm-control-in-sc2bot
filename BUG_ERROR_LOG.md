# 🐛 버그 & 에러 로그 — 스웜 컨트롤 시스템

**최종 업데이트:** 2026-07-04
**테스트 환경:** Python 3.11.15, pytest 9.1.1, Linux (Claude Code 원격 컨테이너)

---

## 📊 테스트 실행 요약 (2026-07-04, 신규 실측)

```
╔══════════════════════════════════════════════════════════╗
║         pytest 전체 실행 결과 (2026-07-04)                ║
╠══════════════════════════════════════════════════════════╣
║  ✅ 통과 (PASSED)  : 502개                               ║
║  ❌ 실패 (FAILED)  :   0개                               ║
║  ⏭️  스킵 (SKIPPED) :  14개                               ║
║  🚫 수집 오류      :   0개                               ║
╚══════════════════════════════════════════════════════════╝
```

BUG-001, ENV-001은 코드/의존성이 이미 갱신되어 재현되지 않아 ✅ 완료로 정정. ENV-002, BUG-008은 이번 세션에서 새로 발견 후 즉시 수정.

### ENV-002 | `cffi` 미설치로 crypto_trading 임포트 시 pyo3 패닉 (심각도: MED)

| 항목 | 내용 |
|:---|:---|
| **영향 범위** | `tests/test_crypto_trading.py`, `tests/test_security.py` (8개 테스트) |
| **오류** | `pyo3_runtime.PanicException: Python API call failed` (`ModuleNotFoundError: No module named '_cffi_backend'`) |
| **원인** | `cryptography` 패키지가 `_cffi_backend`에 의존하지만 `requirements.txt`에 `cffi`가 명시돼 있지 않아 일부 환경에서 누락 |
| **수정** | `requirements.txt`에 `cffi>=1.15.0` 명시 추가 |
| **상태** | ✅ 수정 완료 (2026-07-04) |

### BUG-008 | `test_combat_phase_fsm.py`가 Python 3.11에서 `asyncio.get_event_loop()` 크래시 (심각도: MED)

| 항목 | 내용 |
|:---|:---|
| **영향 범위** | `tests/test_combat_phase_fsm.py` (12개 테스트, FSM 전이 회귀 테스트 전체) |
| **오류** | `RuntimeError: There is no current event loop in thread 'MainThread'.` |
| **원인** | pytest-asyncio가 각 async 테스트 종료 시 이벤트 루프를 정리하면서 `asyncio.set_event_loop(None)`을 호출, 이후 동기 테스트가 `asyncio.get_event_loop()`을 호출하면 Python 3.10+에서 자동 생성되지 않고 예외 발생 |
| **수정** | 테스트 헬퍼 5곳에서 `asyncio.get_event_loop().run_until_complete(...)` → `asyncio.run(...)`로 교체 |
| **상태** | ✅ 수정 완료 (2026-07-04) — FSM 전이 규칙을 실제로 검증하지 못하고 있었던 회귀 테스트가 다시 살아남 |

---

## ❌ 실패한 테스트 (FAILED)

### BUG-001 | 테스트 기댓값 불일치 (심각도: LOW)

| 항목 | 내용 |
|:---|:---|
| **파일** | `tests/test_economy_manager.py:173` |
| **테스트명** | `TestEconomyManagerInitialization::test_initialization_with_config` |
| **오류 유형** | AssertionError — 기댓값 불일치 |
| **발견일** | 2026-03-31 |
| **심각도** | 🟡 LOW (운영 영향 없음) |

**에러 메시지:**
```
FAILED tests/test_economy_manager.py::TestEconomyManagerInitialization::test_initialization_with_config
AssertionError: assert 600 >= 1500
  +  where 600 = <economy_manager.EconomyManager object at 0x...>.macro_hatchery_mineral_threshold
```

**원인 분석:**
- `economy_manager.py:58` 에서 Phase 16 최적화 시 `macro_hatchery_mineral_threshold` 값을 **1500 → 600**으로 의도적으로 낮춤
- 코드 주석: `# ★ Phase 16: OVERFLOW→600 (더 빠른 매크로 해처리)`
- 테스트 코드는 구형 기댓값 `>= 1500` 을 여전히 사용 중 (테스트 미업데이트)

**근본 원인:** 코드 변경 후 테스트 동기화 누락 (코드는 올바름, 테스트가 구형)

**수정 방법:**
```python
# tests/test_economy_manager.py:173
# 변경 전 (잘못된 기댓값):
assert manager.macro_hatchery_mineral_threshold >= 1500

# 변경 후 (올바른 기댓값 — Phase 16 설계 반영):
assert manager.macro_hatchery_mineral_threshold >= 300  # 600이 기본값
```

**상태:** 🔧 수정 필요 (테스트 기댓값 업데이트)

---

## 🚫 수집 오류 (COLLECTION ERRORS) — 8개

### ENV-001 | protobuf 버전 호환성 오류 (심각도: MEDIUM)

| 항목 | 내용 |
|:---|:---|
| **영향 파일** | 8개 테스트 파일 |
| **오류 유형** | `TypeError: Descriptors cannot be created directly` |
| **원인 패키지** | `s2clientprotocol` + `google-protobuf >= 3.21.x` |
| **발견일** | 2026-03-31 |
| **심각도** | 🟠 MEDIUM (SC2 라이브러리 의존성 문제) |

**영향받는 파일:**
```
tests/test_advanced_scout_system_v2.py
tests/test_combat_components.py
tests/test_combat_manager.py
tests/test_economy_manager.py
tests/test_harassment_coordinator.py
tests/test_medium_opening_stability.py
tests/test_production_resilience.py
tests/test_spatial_query_optimizer.py
```

**에러 스택트레이스:**
```
s2clientprotocol/common_pb2.py:32: in <module>
    _descriptor.EnumValueDescriptor(...)
google/protobuf/descriptor.py:1027: in __new__
    _message.Message._CheckCalledFromGeneratedFile()
TypeError: Descriptors cannot be created directly.
If this call came from a _pb2.py file, your generated code is out of date
and must be regenerated with protoc >= 3.19.0.
```

**임시 해결책 (환경변수 설정):**
```bash
# 실행 전 환경변수 설정으로 우회 가능
PROTOCOL_BUFFERS_PYTHON_IMPLEMENTATION=python pytest tests/
```

**영구 해결책:**
```bash
# 방법 1: protobuf 다운그레이드
pip install protobuf==3.20.3

# 방법 2: s2clientprotocol 최신 버전으로 업그레이드
pip install s2clientprotocol --upgrade

# 방법 3: requirements.txt에 버전 고정
protobuf>=3.19.0,<4.0.0
```

**임시 해결 후 결과:** 환경변수 적용 시 8개 오류 모두 해소, 341 PASS 확인

**상태:** 🔧 영구 수정 필요 (requirements.txt 버전 고정 권장)

---

## ⏭️ 스킵된 테스트 (SKIPPED) — 7개

| 위치 | 이유 |
|:---|:---|
| `tests/test_crypto_trading.py` | 실시간 API 키 없음 (6개) |
| `tests/test_security.py` | 외부 네트워크 접근 필요 (1개) |

> 스킵 항목은 정상 — 외부 의존성 테스트이므로 CI 환경에서 항상 스킵됨

---

## ⚠️ 경고 (WARNINGS) — 101개

### WARN-001 | pytest-asyncio 설정 경고

```
PytestUnraisableExceptionWarning: Exception ignored in ...
DeprecationWarning: asyncio_default_fixture_loop_scope not set
```

**원인:** `pytest-asyncio` 구버전과 `asyncio_mode=auto` 혼용
**해결:** `pytest.ini`에 `asyncio_default_fixture_loop_scope = function` 추가

### WARN-002 | ResourceWarning

```
ResourceWarning: unclosed <ssl.SSLSocket ...>
```

**원인:** 일부 테스트에서 HTTP 세션 명시적 close 누락
**심각도:** 무시 가능 (테스트 환경 한정)

---

## 📈 테스트 커버리지 현황

```
모듈별 추정 커버리지:
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
economy_manager.py          ████████████████░░░░  85%
combat_manager.py           ████████████████████  98%
scout_system.py             ████████████████░░░░  82%
production_manager.py       ███████████████░░░░░  78%
tech_tree.py                ████████████░░░░░░░░  65%
ppo_trainer.py              ██░░░░░░░░░░░░░░░░░░  12% (신규)
alphastar_arch/             █░░░░░░░░░░░░░░░░░░░   5% (신규)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
전체 평균                   ████████████████░░░░  80%
```

---

## 🗂️ 버그 추적 이력

| ID | 날짜 | 심각도 | 상태 | 설명 |
|:---|:---|:---:|:---:|:---|
| BUG-001 | 2026-03-31 | 🟡 LOW | ✅ 완료 | economy_manager 테스트 기댓값 불일치 — 코드가 이미 300 기준으로 수정되어 있었음 (2026-07-04 재검증) |
| ENV-001 | 2026-03-31 | 🟠 MED | ✅ 완료 | protobuf 버전 호환성 — 최신 s2clientprotocol/protobuf 조합으로 재현 안 됨 (2026-07-04 재검증) |
| ENV-002 | 2026-07-04 | 🟡 MED | ✅ 완료 | `cffi` 미설치 시 crypto_trading import pyo3 패닉 (위 상세 참조) |
| BUG-008 | 2026-07-04 | 🟡 MED | ✅ 완료 | test_combat_phase_fsm.py `asyncio.get_event_loop()` 크래시 (위 상세 참조) |
| BUG-002 | 이전 세션 | 🟢 DONE | ✅ 수정 | HP 가중치 전투 계산 오류 |
| BUG-003 | 이전 세션 | 🟢 DONE | ✅ 수정 | 가스 가드 로직 오류 |
| BUG-004 | 이전 세션 | 🟢 DONE | ✅ 수정 | 크립 확산 BFS 무한루프 |
| BUG-005 | 이전 세션 | 🟢 DONE | ✅ 수정 | 여왕 수혈 타이밍 오류 |
| BUG-006 | 이전 세션 | 🟢 DONE | ✅ 수정 | 오버로드 서플라이 계산 오버플로우 |
| BUG-007 | 이전 세션 | 🟢 DONE | ✅ 수정 | 멀티태스킹 레이스 컨디션 |

**누적 수정 버그: 187+개 (Phase 1 ~ Phase 400 + 2026-07-04 세션)**

---

## 🔜 다음 조치 계획 (2026-07-04 갱신)

1. **즉시 (Priority 1) — 완료**
   - ~~`test_initialization_with_config` 기댓값 수정~~ ✅ 코드에 이미 반영됨
   - ~~crypto_trading cffi 의존성 누락~~ ✅ requirements.txt에 명시 추가

2. **단기 (Priority 2)**
   - `REMAINING_ISSUES.md` N5 (bare `except Exception:` 475건) 점진적 축소 — 모듈 단위로 나눠 동작 검증하며 진행
   - `REMAINING_ISSUES.md` N6 (F841 미사용 변수 130건) 정리
   - README/보고서류의 "90% 승률", "0 fail" 등 주장과 `mass_test_results.json` 실측치 간 괴리 해소 (실측 기반으로 표현 수정)

3. **중기 (Priority 3)**
   - 열린 PR 다수 정리 (중복 작업 파악 후 사용자 승인 하에 정리)
   - pip-tools/uv 기반 lockfile 도입으로 CI 재현성 확보
   - 테스트 커버리지 90%+ 목표

---

*이 로그는 `pytest` 자동 실행 결과를 기반으로 작성되었습니다.*
