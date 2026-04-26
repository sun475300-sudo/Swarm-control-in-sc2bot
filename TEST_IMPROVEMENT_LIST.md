# Test-Driven Improvement List (sc2지휘관봇)

작성일: 2026-04-26
브랜치: `claude/stoic-shannon-0ghVz`
방법: `pytest` 전체 수트 + 정적 스캔 → 발견된 결함을 우선순위로 정리

---

## 📊 베이스라인 결과 (수정 전)

| 수트 | 통과 | 실패 | 스킵 | 비고 |
|---|---:|---:|---:|---|
| `tests/` | 223 | **83** | 34 | `pytest-asyncio` 미설치로 async 테스트 전부 실패 |
| `pytest/` | 2 | 0 | 0 | OK |
| `wicked_zerg_challenger/tests/` | 0 | **6 ERROR** | - | `sc2` 패키지 없음 + 스텁 클래스 결함으로 컬렉션 단계 실패 |

총 89건이 인프라/스텁 문제로 실행조차 되지 않음.

---

## 🔥 P0 — 테스트 인프라 즉시 차단 이슈

### [P0-1] `pytest-asyncio` 누락 — 83 fails ✅ 수정됨
- 증상: `async def functions are not natively supported.`
- 원인: `pytest.ini`의 `asyncio_mode = auto`가 활성화되어 있으나 패키지 미설치
- 수정: `requirements.txt`에 `pytest-asyncio>=0.23.0` 추가

### [P0-2] `cffi` (cryptography 백엔드) 누락 — 7 fails ✅ 수정됨
- 증상: `pyo3_runtime.PanicException: Python API call failed` + `ModuleNotFoundError: No module named '_cffi_backend'`
- 영향: `tests/test_security.py`, `tests/test_crypto_trading.py`
- 수정: `requirements.txt`에 `cffi>=1.16.0` 추가

### [P0-3] `pytest-timeout` 누락 — 1 warning ✅ 수정됨
- 증상: `PytestConfigWarning: Unknown config option: timeout` (pytest.ini의 `timeout = 60` 무력화)
- 수정: `requirements.txt`에 `pytest-timeout>=2.0.0` 추가

### [P0-4] `wicked_zerg_challenger/tests/test_active_scouting_system.py` 컬렉션 실패
- 증상: `AttributeError: type object 'UnitTypeId' has no attribute 'OVERLORD'`
- 원인: `sc2` 미설치 환경에서 `class UnitTypeId: pass` 스텁이 로드되는데, 스텁이 빈 클래스라 `UnitTypeId.OVERLORD`를 함수 기본값으로 쓰는 코드가 모듈 로드 시점에 폭발
- 영향 파일: `wicked_zerg_challenger/scouting/advanced_scout_system_v2.py:837`
- 동일 패턴이 27개 파일에 분산되어 있음 (creep, combat, build_order, queen 등)

### [P0-5] `wicked_zerg_challenger/tests/test_combat_manager.py` 등 5개 — `ModuleNotFoundError: No module named 'sc2'`
- 증상: 테스트 모듈이 `from sc2.ids.unit_typeid import UnitTypeId`를 직접 import — 본 코드와 달리 try/except 미사용
- 영향: `test_economy_manager.py`, `test_opponent_modeling.py`, `test_production_resilience.py`, `test_difficulty_progression.py`, `test_combat_manager.py`

---

## 🟧 P1 — 코드 품질/일관성

### [P1-1] sc2 ImportError 스텁 패턴이 27개 파일에 중복
- 모든 파일이 동일한 `try: from sc2... except ImportError: class X: pass` 보일러플레이트
- 권장: `wicked_zerg_challenger/_sc2_compat.py`로 단일화하고 메타클래스로 자동 attribute fallback 제공
- 메타클래스 패턴 예:
  ```python
  class _StubMeta(type):
      def __getattr__(cls, name):
          v = type(name, (cls,), {})
          setattr(cls, name, v)
          return v
  class UnitTypeId(metaclass=_StubMeta): pass
  ```

### [P1-2] `wicked_zerg_challenger/tests/conftest.py` 가 매우 빈약함
- 현재: protobuf 환경변수 한 줄
- 개선: sc2 미설치 환경 자동 감지 + skip_if 마커, `MockBotAI` fixture, 공통 `mock_logger`

### [P1-3] `tests/conftest.py` — `mock_upbit_client` 등 트레이딩 픽스처가 SC2 봇 테스트 폴더에 섞여있음
- 권장: `tests/sc2/`와 `tests/trading/`로 분리 또는 `conftest.py` 모듈화

---

## 🟨 P2 — 테스트 커버리지/안정성

### [P2-1] 통합 테스트 부재
- 단위 테스트 306개 통과하지만 `tests/integration/` 디렉토리가 거의 비어있음 (확인 필요)
- 권장: 매니저 간 상호작용 테스트 (Economy ↔ Production ↔ Combat)

### [P2-2] 34개 스킵된 테스트
- `tests/test_security.py` 1 skip, `tests/test_crypto_trading.py` 11 skips, 등
- 스킵 사유 audit 후 환경 셋업으로 복구 가능한지 검증

### [P2-3] 무작위/픽스처 시드 고정 부재
- 일부 테스트가 random/timing 의존 가능성. 확인 후 `random.seed(42)` 픽스처 추가

### [P2-4] 커버리지 측정 비활성
- `pyproject.toml`에 `pytest-cov` 옵션 주석처리됨
- 권장: CI에서 커버리지 50% 이상 강제

---

## 🟩 P3 — 빌드/CI/문서

### [P3-1] `requirements.txt`에 테스트/dev 패키지 분리 부재
- 권장: `requirements-dev.txt` 분리 또는 `pyproject.toml` `[project.optional-dependencies] test = [...]`

### [P3-2] `burnysc2` 빌드 실패 (`mpyq` C 익스텐션) → CI 환경 도커화 필요
- 로컬에서 `pip install burnysc2` 시 `mpyq` 빌드 실패. Dockerfile에 빌드 의존성 명시

### [P3-3] README의 "263 통과 0 실패" 배지가 실제(306 통과)와 불일치
- README.md 배지 갱신 필요

---

## 📝 작업 진행 순서

1. ✅ P0-1, P0-2, P0-3 (test deps in requirements.txt) — **commit 1**
2. P0-4 (스텁 메타클래스 적용 in `advanced_scout_system_v2.py`) — **commit 2**
3. P1-1 (`_sc2_compat.py` 단일 모듈화) — **commit 3**
4. P0-5 (`wicked_zerg_challenger/tests/`도 동일 스텁 사용) — **commit 4**
5. P3-3 (README 배지/숫자 갱신) — **commit 5**
6. P2-2 (skipped tests 점검) — **commit 6 이후**

각 commit 후 push, 다음 라운드는 새 테스트 결과 기반으로 재분석.
