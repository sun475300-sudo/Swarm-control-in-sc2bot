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

## Iteration 4 (완료)
- [x] T4-01: 전체 트리에서 254개의 placeholder 없는 f-string 제거 (F541 lint clean)

## Iteration 5 (완료)
### CI 진단
- [ ] T5-01: PR CI `Lint & Type Check` 의 black 단계 실패 → main 자체에서도 black 비호환이므로 PR 변경과 무관 (사전 존재 이슈)
- [x] T5-02: critical flake8 (E9,F63,F7,F82) 통과 확인 → 0 errors
- [ ] T5-03: CI 의 black 단계는 향후 일괄 black format PR 필요 (대규모 diff 위험)
- [x] T5-04: F841 unused 'as e' 47건 정리

## Iteration 6 (완료) - 실버그 발견
- [x] T6-01: `request_production(priority=5)` 처럼 미리 정의되지 않은 priority 사용 시 KeyError → setdefault 로 수정
- [x] T6-02: auto_adjust_authority 권한 모드 전이 회귀 테스트 7건 추가
- [x] T6-03: production queue 회귀 테스트 4건 추가

## Iteration 7-13 (완료) - 테스트 커버리지 확대
- [x] T7-01: QueenManager static 헬퍼 (_score_creep_target, _find_closest_queen, _find_queen_by_tag) 11건
- [x] T8-01: utils/common_helpers (has_units, safe_first, safe_closest, safe_amount, clamp, percentage) 29건
- [x] T9-01: utils/pid_controller (PIDController, PID2D, UnitMovementController) 12건
- [x] T9-02: utils/position_utils (get_center, weighted_center, closest, furthest, ...) 21건
- [x] T10-01: utils/error_handler (safe_execute, retry_on_failure, validators) 21건
- [x] T11-01: utils/kd_tree (build, nearest, range, knn - brute-force 비교) 10건
- [x] T12-01: utils/frame_cache + cached_per_frame **kwargs 버그 수정** 13건
- [x] T13-01: utils/game_constants lock-in 19건

## 누적 통계 (Iteration 1 → 13)
- 테스트 통과 수: 661 → 806 (+145)
- 발견·수정한 진짜 버그:
  - Blackboard alias 누락 (4개 모듈 ImportError)
  - should_expand `is_supply_block` 오타 + 광물 체크 누락
  - game_analytics_system.py SyntaxError
  - request_production KeyError on unknown priority
  - cached_per_frame kwargs 무시 (잠재 버그)
  - 80+ 파일의 protobuf TypeError 대응

## 향후 후보 (위험도 있음 - 깊은 분석 필요)
- T-Future-01: opponent_modeling.py 의 on_step 중복 정의 (위에서 발견)
- T-Future-02: economy_manager.py 의 `_prevent_resource_banking`, `_reduce_gas_workers` 중복
- T-Future-03: combat_manager.py 의 `_find_harass_target` 중복
- T-Future-04: 전체 트리 black 포맷팅 일괄 적용 (CI 정상화)

