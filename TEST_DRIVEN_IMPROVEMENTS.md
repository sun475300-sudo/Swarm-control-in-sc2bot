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

## Iteration 2 발견 (2026-05-16)

### Fixed
- [x] T2-01: `game_analytics_system.py:418` 중복된 `except` 블록/잘못된 들여쓰기로 인한 SyntaxError 수정
- [x] T2-02: 80개 SC2 모듈의 `try:from sc2... except ImportError:` 를 `except (ImportError, TypeError):` 로 확장. protobuf descriptor 충돌 회피.
- [x] T2-03: blackboard.py 자체에 동일 import 처리 적용

### Pending (위험도 있음)
- [ ] T2-04: `opponent_modeling.py` 의 `on_step` 메서드가 같은 클래스에 두 번 정의됨 (line 341 vs 765). 두 번째가 첫 번째를 가림. Version A(341)이 더 풍부한 기능을 가지지만 Version B(765)만 실행됨.
- [ ] T2-05: `economy_manager.py` 의 `_prevent_resource_banking` (1681 vs 3258), `_reduce_gas_workers` (3391 vs 4082) 중복
- [ ] T2-06: `combat_manager.py` 의 `_find_harass_target` (2809 vs 5005) 중복

### Code smells (low priority, automated cleanup 가능)
- [ ] T2-07: `economy_manager.py` 다수의 F541 (empty f-string), F841 (unused local) 경고
- [ ] T2-08: 전체적으로 dead-code 제거 캠페인 필요

## Iteration 3 계획
- 추가 테스트 커버리지 (블랙보드 헬퍼, queen, economy 등)
- 더 많은 syntax/lint 점검
- combat 모듈 통합 테스트

