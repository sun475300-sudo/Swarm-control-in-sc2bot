# SC2 지휘관봇 개선 리스트 (2026-05-06)

테스트와 정적 분석을 통해 식별된 개선사항 대규모 리스트.

## 🔴 P0 — 즉시 수정 (테스트가 직접 실패/경고)

### 1. `tests/test_opponent_modeling.py` — 9개 async 테스트가 await 되지 않음
- **현상**: `unittest.TestCase` 상속 클래스에 `async def test_*` 메서드 → 코루틴 누설
- **영향**: `RuntimeWarning: coroutine ... was never awaited` + `DeprecationWarning: returning non-None value`
- **해결**: `TestOpponentModeling`을 `unittest.IsolatedAsyncioTestCase`로 변경
- 영향 메서드: `test_on_start_new_opponent`, `test_on_start_known_opponent`, `test_detect_fast_expand_signal`, `test_detect_early_pool_signal`, `test_detect_no_natural_signal`, `test_detect_early_army_signal`, `test_timing_attack_detection`, `test_timing_attack_cooldown`, `test_full_game_flow`

### 2. `tests/test_production_resilience.py` — 7개 async 테스트가 await 되지 않음
- **현상**: 동일 패턴
- **해결**: `TestProductionResilience`을 `unittest.IsolatedAsyncioTestCase`로 변경
- 영향 메서드: `test_safe_train_success`, `test_safe_train_invalid_unit`, `test_safe_train_no_train_method`, `test_safe_train_with_retry`, `test_get_counter_unit_terran_marine`, `test_get_counter_unit_protoss`, `test_get_counter_unit_zerg`

### 3. `pytest.ini` — Unknown config option: `timeout`
- **현상**: `pytest-timeout` 미설치 또는 ini 설정 누락
- **해결**: pytest.ini에 timeout 설정이 있다면 pytest-timeout 의존성 추가 또는 옵션 제거

### 4. `pytest.ini` — `asyncio_default_fixture_loop_scope` 미설정 (Deprecation)
- **현상**: 향후 pytest-asyncio 버전에서 동작이 바뀜
- **해결**: pytest.ini에 `asyncio_default_fixture_loop_scope = function` 명시

## 🟠 P1 — 코드 품질/방어 코딩

### 5. `scouting/advanced_scout_system_v2.py:33` — except 폭이 너무 넓음
- **현상**: `except ImportError:` 발생 시 fallback 클래스를 정의하지만 클래스 본문의 `UnitTypeId.OVERLORD` 같은 클래스 변수 기본값이 폭발함
- **해결**: 함수 시그니처에서 모듈 미사용 시 `Optional[UnitTypeId] = None`로 기본값 None 설정 후 함수 본문에서 lazy 결정

### 6. fallback `UnitTypeId` 등 placeholder 클래스가 attribute 접근에 약함
- **해결**: `class UnitTypeId: OVERLORD=None; ZERGLING=None ...` 식으로 미리 알려진 멤버 정의

## 🟡 P2 — 점진적 개선 (커버리지/문서화)

### 7. `tests/test_advanced_micro_v3.py` — Mock spec 잘못 사용 (실제로는 통과지만 위험)
- **현상**: `Mock(spec=[])` 등으로 인한 잠재적 NoneType 반환

### 8. 캐시된 .pyc가 import 충돌 유발 (이미 발견)
- **해결**: `__pycache__` 정리하는 ci 스크립트, 또는 `.gitignore`에 명시

### 9. test_active_scouting_system 에러는 sc2 의존성 미설치 시 collection 실패
- **해결**: `try/except` 블록의 catch 폭을 확장 (`AttributeError` 포함)

### 10. asyncio 모드 명시
- pytest.ini의 `asyncio_mode` 명시화

## 진행 계획

각 사이클에서:
1. 테스트 실행 → 이슈 수집
2. 우선순위로 수정 (P0 → P1 → P2)
3. 회귀 테스트
4. 커밋 + 푸시
5. 다음 사이클로 이동
