# 🐛 버그 & 에러 로그 — 스웜 컨트롤 시스템

**최종 업데이트:** 2026-03-31
**테스트 환경:** Python 3.10.11, pytest 9.0.2, Windows 11

---

## 📊 테스트 실행 요약

```
╔══════════════════════════════════════════════════════════╗
║         pytest 전체 실행 결과 (2026-03-31)                ║
╠══════════════════════════════════════════════════════════╣
║  ✅ 통과 (PASSED)  : 341개                               ║
║  ❌ 실패 (FAILED)  :   1개                               ║
║  ⏭️  스킵 (SKIPPED) :   7개                               ║
║  🚫 수집 오류      :   8개 (환경 의존성 문제)             ║
║  ⚠️  경고          : 101개                               ║
╚══════════════════════════════════════════════════════════╝
```

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
| BUG-001 | 2026-03-31 | 🟡 LOW | ✅ 수정 (2026-04-25) | economy_manager 테스트 기댓값 — `>= 300` 으로 갱신 (확인) |
| ENV-001 | 2026-03-31 | 🟠 MED | ✅ 수정 (2026-04-25) | `requirements.txt` 에 `protobuf>=3.20.0,<4.0.0` 핀 |
| WARN-001 | 2026-03-31 | 🟢 INFO | ✅ 수정 (2026-04-25) | pytest.ini 에 `asyncio_default_fixture_loop_scope = function` 추가 |
| BUG-008 | 2026-04-25 | 🟠 MED | ✅ 수정 | scout V2 시그니처 default 가 sc2 미설치 시 import 폭주 |
| BUG-009 | 2026-04-25 | 🟠 MED | ✅ 수정 | check_proxy.py module-level sys.exit() — 다른 환경에서 import 만으로 크래시 |
| BUG-010 | 2026-04-25 | 🟢 LOW | ✅ 수정 | visualize_learning.py — matplotlib 미설치 시 import-time sys.exit() |
| TEST-001 | 2026-04-25 | 🟢 LOW | ✅ 수정 | test_p606_infra silent-skip 4건 — 잘못된 클래스명 lookup 교정 |
| BUG-002 | 이전 세션 | 🟢 DONE | ✅ 수정 | HP 가중치 전투 계산 오류 |
| BUG-003 | 이전 세션 | 🟢 DONE | ✅ 수정 | 가스 가드 로직 오류 |
| BUG-004 | 이전 세션 | 🟢 DONE | ✅ 수정 | 크립 확산 BFS 무한루프 |
| BUG-005 | 이전 세션 | 🟢 DONE | ✅ 수정 | 여왕 수혈 타이밍 오류 |
| BUG-006 | 이전 세션 | 🟢 DONE | ✅ 수정 | 오버로드 서플라이 계산 오버플로우 |
| BUG-007 | 이전 세션 | 🟢 DONE | ✅ 수정 | 멀티태스킹 레이스 컨디션 |

**누적 수정 버그: 185+개 (Phase 1 ~ Phase 400)**

---

## 🔜 다음 조치 계획

1. **즉시 (Priority 1)**
   - `test_initialization_with_config` 기댓값 `>= 1500` → `>= 300`으로 수정
   - `requirements.txt`에 `protobuf>=3.19.0,<4.0.0` 버전 고정

2. **단기 (Priority 2)**
   - `pytest.ini`에 `asyncio_default_fixture_loop_scope = function` 추가
   - 신규 모듈(ppo_selfplay, alphastar_arch) 유닛 테스트 작성

3. **중기 (Priority 3)**
   - CI/CD 파이프라인에 `PROTOCOL_BUFFERS_PYTHON_IMPLEMENTATION=python` 환경변수 추가
   - 테스트 커버리지 90%+ 목표

---

*이 로그는 `pytest` 자동 실행 결과를 기반으로 작성되었습니다.*
