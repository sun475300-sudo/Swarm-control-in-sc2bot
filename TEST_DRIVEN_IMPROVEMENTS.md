# SC2 Commander Bot Test-Driven Improvement List

이 문서는 테스트와 코드 점검을 통해 발견된 개선 사항을 추적한다.
모든 항목은 반복 테스트와 commit/push 주기로 진행된다.

## Status Legend
- [ ] Pending
- [x] Done
- [~] In progress
- [!] Blocked

## Iteration 1 (2026-05-16)

### Critical Bugs (코드 임포트 오류로 모듈/테스트가 실패)
- [x] T1-01: `blackboard.py`에 `Blackboard = GameStateBlackboard` alias 추가
  - 영향: `wicked_zerg_bot_pro_impl.py`, `production_controller.py`, `test_blackboard.py`, `test_sprint8_qa.py`
- [ ] T1-02: 루트 `tests/test_queen_transfusion.py`의 `sc2.ids.unit_typeid` 의존성 처리 (skip if missing)
- [ ] T1-03: tests/__init__.py 정리 및 conftest 공통화

### Test infrastructure
- [ ] T1-04: `requirements-dev.txt`에 `pytest-asyncio`, `pytest-mock`, `pytest-timeout` 명시 확인
- [ ] T1-05: 테스트 실행 가이드(`tests/README.md` 또는 루트 `TESTING.md`) 갱신
- [ ] T1-06: CI 잡에서 dev requirements 설치 확인

### Code quality
- [ ] T1-07: 사용되지 않는 import 제거 (autoflake / 수동 점검)
- [ ] T1-08: 중복 / 사용되지 않은 함수 식별
- [ ] T1-09: docstring / 한국어 주석 일관성 점검

### SC2 도메인 개선
- [ ] T1-10: combat_phase_controller에서 mock 환경 robust 보강
- [ ] T1-11: economy_manager에서 lazy import 패턴 정리
- [ ] T1-12: queen_transfusion 쿨다운 및 타겟 중복 제거 확인

이후 Iteration N+1 에서 매번 새로운 발견 항목을 추가한다.
