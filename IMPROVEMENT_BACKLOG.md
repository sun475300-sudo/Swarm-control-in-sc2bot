# SC2 지휘관봇 개선 백로그 (반복 점검 결과)

테스트 + 정적 분석으로 식별한 개선 항목.
사이클별로 위에서부터 진행하고, 완료 시 [x] 체크.

## 사이클 1 - 테스트 인프라 + 안전한 정리 (최우선)

- [x] **T1**: pytest-asyncio 미설치로 84개 async 테스트 실패 → CI 의존성 정리 + 개발 가이드
- [x] **T2**: `tests/test_phase10_improvements.py` `test_gas_overflow_threshold_lowered`이 1000을 기대하지만 실제 코드는 800으로 개선됨 → 테스트 갱신 (improvement 반영)
- [x] **T3**: `wicked_zerg_challenger/combat_manager.py` 미사용 import 제거 (assignment_manager·rally_point_calculator 등)
- [x] **T4**: `wicked_zerg_challenger/spell_unit_manager.py:57` 중복 `Dict` import 제거
- [x] **T5**: `wicked_zerg_challenger/creep_manager.py` 중복 `math/Set/Tuple` re-import 제거
- [x] **T6**: `wicked_zerg_challenger/run_with_training.py` 중복 `random/time/datetime` re-import 제거
- [x] **T7**: `wicked_zerg_challenger/combat/micro_combat.py:410` 함수 안 중복 `import math` 제거
- [x] **T8**: `wicked_zerg_challenger/economy_manager.py` placeholder 없는 f-string → 일반 문자열 (로그 메시지 정확성)

## 사이클 2 - 로직 결함 / 죽은 코드

- [ ] **L1**: `economy_manager.py`에서 `_prevent_resource_banking` 함수가 1298행과 2507행에 두 번 정의됨 → Python 메서드 재정의로 첫 번째(스포어/스파인 방어 로직 포함)가 완전히 죽은 코드. 두 번째 버전에 방어 건물 로직을 통합하거나 별도 메서드로 분리.
- [ ] **L2**: `economy_manager.py`에서 `_reduce_gas_workers`가 2630행과 3286행에 두 번 정의됨 → 동일 문제, 첫 번째가 죽은 코드.
- [ ] **L3**: `opponent_modeling.py:766` `on_step` 메서드 중복 정의 - 첫 번째가 무시됨, 검증 필요.
- [ ] **L4**: `combat_manager.py:4284` `_find_harass_target` 중복 정의.
- [ ] **L5**: `local_training/production_resilience.py:1875` `build_terran_counters` 중복 정의.
- [ ] **L6**: `combat_manager.py` except 블록의 미사용 `e` 변수 (50+개) → `except Exception:` 또는 로깅 추가.
- [ ] **L7**: `economy_manager.py` 미사용 로컬 변수 `early_window`, `vespene`, `base_count`, `start_loc`, `minerals` → 의도된 로직 누락 가능성 검토.

## 사이클 3+ - 향후

- [ ] 테스트 커버리지 확장: 통합 테스트 강화, `tests/integration/` 활성화
- [ ] 매뉴얼 문서 (PROJECT_REVIEW_REPORT, BUG_ERROR_LOG) 정리/통합
- [ ] CI 워크플로 통합 (sc2bot-ci.yml + ci.yml 중복 제거)
