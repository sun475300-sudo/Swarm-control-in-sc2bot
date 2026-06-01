# SC2 지휘관봇 테스트 개선 리스트 (대규모)

테스트 실행 결과 및 점검을 통해 발견된 개선 사항 우선순위 리스트.
실행 환경: Python 3.11.15, pytest 9.0.3, burnysc2 7.3.0, protobuf 3.20.3

## 현재 테스트 현황
- **수집된 테스트:** 502개 이상
- **통과:** 482
- **실패:** 20
- **건너뜀:** 14
- **에러:** 0 (이전: 19에서 해결)

## P0 - 즉시 수정 (테스트가 시스템 사용성 영향)

### 1. `tests/test_combat_phase_fsm.py` asyncio 이벤트 루프 문제
- **문제:** `asyncio.get_event_loop().run_until_complete(...)` 패턴은 Python 3.10+에서 deprecate됨
- **증상:** `RuntimeError: There is no current event loop in thread 'MainThread'`
- **영향:** 12개의 테스트 실패
- **수정:** `asyncio.run()` 또는 `asyncio.new_event_loop()` 사용

### 2. `tests/test_combat_phase_fsm.py` `mock_patch` import 미사용
- 코드: `from unittest.mock import MagicMock, patch, patch as mock_patch`
- 그러나 `mock_patch`은 사용되지 않음

### 3. `tests/test_harassment_coordinator.py` Mock 사이드이펙트 잘못
- **문제:** `Mock(side_effect=lambda *args: EmptyUnits())` - `side_effect`가 callable이면 호출되지만 인자 처리가 모호
- **수정:** Mock 객체 callable로 명시적 설정

## P1 - 환경 문제 (이미 일부 해결)

### 4. SC2 의존성 설치 (해결됨)
- `loguru`, `scipy`, `burnysc2`, `s2clientprotocol`, `protobuf<4` 모두 설치 완료
- requirements.txt에 protobuf<4 명시 필요

### 5. `tests/test_crypto_trading.py` cryptography PyO3 에러
- **문제:** `pyo3_runtime.PanicException: Python API call failed`
- **원인:** 시스템 cryptography가 cffi와 충돌
- **영향:** 3개 테스트 실패
- **수정:** cryptography 재설치 또는 venv 사용

### 6. `tests/test_security.py` 같은 cryptography 문제
- **영향:** 5개 테스트 실패
- 위와 동일

## P2 - 코드 품질 개선

### 7. `advanced_scout_system_v2.py` 기본 인자 평가 시점 문제
- **문제:** `def method(self, ..., unit_type: UnitTypeId = UnitTypeId.OVERLORD)`
- **원인:** import 실패시 stub class에 `OVERLORD` 없음 → 클래스 정의 시점에 AttributeError
- **수정:** 기본값을 None으로 하고 본문에서 처리

### 8. 광범위한 `try: import sc2 except ImportError: class Stub: pass` 패턴
- **문제:** Stub class들이 attribute 없음 → 디폴트 인자 평가 실패
- **현재 영향:** advanced_scout_system_v2.py 외 다수 파일
- **수정:** 모든 stub을 더 완전하게 만들거나 sentinel 사용

### 9. 테스트 파일 중복 import
- `from unittest.mock import MagicMock, patch, patch as mock_patch` 등

### 10. 비동기 테스트 패턴 일관성 부족
- 어떤 파일은 `pytest.mark.asyncio` 사용, 어떤 파일은 직접 `run_until_complete`

## P3 - 신규 테스트 / 커버리지 강화

### 11. `wicked_zerg_challenger/` 메인 봇 클래스 통합 테스트 부재
- 메인 BotAI 서브클래스 인스턴스화 테스트 없음

### 12. `bot_step_integration.py` 통합 테스트 부족

### 13. 빌드 오더 시스템 회귀 테스트

### 14. 멀티 매치업 시나리오 통합 테스트

## P4 - 문서/메타

### 15. CHANGELOG.md, BUG_FIXES_REPORT.md 등 다수의 보고서 파일 정리 필요

### 16. README 일관성 (영문/한국어 동시 유지)

### 17. requirements.txt에 dev-only 의존성 분리

## 처리 진행

- [x] 1) test_combat_phase_fsm.py asyncio 수정
- [x] 2) test_harassment_coordinator.py BANELING Mock 수정
- [x] 3) advanced_scout_system_v2.py 디폴트 인자 수정
- [x] 4) requirements.txt에 protobuf<4 명시
- [ ] 5) cryptography 환경 의존 문제
- [ ] 6) 추가 회귀 테스트
