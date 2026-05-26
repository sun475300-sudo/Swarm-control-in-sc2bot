# SC2 지휘관봇 개선 백로그

> 생성: 2026-05-10 · 출처: 테스트/정적 분석 자동 점검 사이클
> 상태: 활성 (반복 사이클로 항목 소화 중)

---

## 🚨 Critical (Iteration 1에서 처리 완료)

| ID | 이슈 | 위치 | 상태 |
|----|------|------|------|
| C1 | SyntaxError - 중복 except 절 + 잘못된 들여쓰기 (모듈 import 불가) | `wicked_zerg_challenger/game_analytics_system.py:419` | ✅ FIXED |
| C2 | F811 `build_terran_counters` 중복 정의 (첫 정의는 죽은 코드) | `wicked_zerg_challenger/local_training/production_resilience.py:1467 vs 1977` | ✅ FIXED |
| C3 | F811 `on_step` 중복 정의 (REMAINING_ISSUES.md N1 - 동작 영향) | `wicked_zerg_challenger/opponent_modeling.py:341 vs 765` | ✅ FIXED (guard 통합 후 두 번째 제거) |
| C4 | F823 `traceback` UnboundLocalError 위험 (런타임 크래시) | `wicked_zerg_challenger/wicked_zerg_bot_pro_impl.py:572` | ✅ FIXED |
| C5 | sc2 미설치 환경에서 `UnitTypeId.OVERLORD` 기본값으로 NameError | `wicked_zerg_challenger/scouting/advanced_scout_system_v2.py:1039` | ✅ FIXED |
| C6 | sc2 미설치 환경에서 test 모듈 import 에러 (collection 차단) | `tests/test_queen_transfusion.py:11` | ✅ FIXED (skip guard 추가) |
| C7 | pytest-asyncio 미설치로 인한 83건 async 테스트 실패 | `pytest` venv | ✅ FIXED (uv tool install) |
| C8 | F541 f-string 빈 placeholder 254건 (lint noise) | `wicked_zerg_challenger/**/*.py` | ✅ FIXED (ruff --fix) |
| C9 | F401 사용되지 않는 import 4건 | `wicked_zerg_challenger/**/*.py` | ✅ FIXED (ruff --fix) |

## 🟠 High Priority

| ID | 이슈 | 위치 | 우선순위 / 상태 |
|----|------|------|----------|
| H1 | `EconomyManager._prevent_resource_banking` 재정의 (F811) | `economy_manager.py` | ✅ Iter 2에서 처리 |
| H2 | `EconomyManager._reduce_gas_workers` 재정의 (F811) | `economy_manager.py` | ✅ Iter 2에서 처리 |
| H3 | `combat_manager._find_harass_target` 재정의 (line 2809 vs 5005) | `combat_manager.py` | ✅ Iter 2에서 처리 |
| H4 | `production_resilience.build_terran_counters` 재정의 | `production_resilience.py` | ✅ Iter 1에서 처리 |
| H5 | bare `except Exception:` 360+건 (silent failure 위험) | 전체 코드 | 🟡 점진적 |
| H6 | F841 unused-variable 131건 (잠재 버그/dead code) | 전체 코드 | 🟡 |
| H7 | F405 undefined-local-with-import-star 95건 (네임스페이스 오염) | 전체 코드 | 🟡 |
| H8 | black/isort 67/4 violations (Lint & Type Check CI fail) | 전체 코드 | ✅ Iter 2에서 처리 |
| H9 | `Blackboard` alias 부재 (production_controller import 깨짐) | `blackboard.py` | ✅ Iter 3에서 처리 |
| H10 | `should_expand()` typo `is_supply_block` (실제 attribute는 `is_supply_blocked`) | `blackboard.py:549` | ✅ Iter 3에서 처리 |
| H11 | `should_expand()` 미네랄 체크 누락 (Hatchery 300원 미달도 True 반환) | `blackboard.py` | ✅ Iter 3에서 처리 |
| H12 | `difficulty_progression._serialize_stats` 외부 stub과 호환 안됨 | `difficulty_progression.py:89` | ✅ Iter 3에서 처리 |
| H13 | wicked_zerg_challenger tests 24건 collection error (sc2 미설치) | `wicked_zerg_challenger/tests/` | ✅ Iter 3에서 처리 (conftest sc2 stub) |

## 🟡 Medium Priority

| ID | 이슈 | 비고 |
|----|------|------|
| M1 | E402 module-import-not-at-top 66건 | 코드 가독성 |
| M2 | E741 ambiguous-variable-name (l, I, O) 23건 | lint 위반 |
| M3 | E713 not-in-test 2건 | 가독성 |
| M4 | Transfusion 우선순위 개선 (REMAINING_ISSUES #3) | 게임 로직 최적화 |
| M5 | Queen energy 활용 효율화 | 게임 로직 |
| M6 | sc2 미설치 환경에서 collect 가능하도록 sc2 stub 통일 | 테스트 인프라 |

## 🟢 Low Priority / Long-term

| ID | 이슈 | 비고 |
|----|------|------|
| L1 | E501 line-too-long 973건 | black/ruff formatting |
| L2 | TODO/FIXME 27건 (MASTER_TODO_SC2 1.3) | 문서 정리 |
| L3 | pytest skip/xfail 라벨링 (MASTER_TODO_SC2 1.4) | 테스트 위생 |
| L4 | mypy strict-equality 정리 (PR #28 cycle 6+) | 타입 안전성 |
| L5 | detect-secrets 결과 점검 | 보안 |
| L6 | 16개 열린 PR redundancy 분석 | PR 위생 |

## 📊 메트릭 추이

### Iteration 1 종료
- 테스트: tests/ 392 passed, 34 skipped, 0 failed
- 정적 분석: critical errors 0건 (E9/F811/F823/F401/F541 → 0)
- wicked_zerg_challenger/tests: 24 collect error

### Iteration 2 종료
- 테스트: 변동 없음 (392 passed)
- 정적 분석: F811 0건 유지
- black 67건 위반 → 0건, isort 4건 위반 → 0건
- CI Lint & Type Check 통과 가능 상태

### Iteration 3 종료
- 테스트: tests/ 392 passed + wicked_zerg_challenger/tests/ 651 passed (합계 1043 passed)
- 신규 발견 + 처리: H9-H12 (Blackboard 관련 진짜 버그 4건)
- wicked_zerg_challenger tests collection error 0건

### Iteration 4 종료
- F841 130 → 75 (-55): except 절 `e` 47건 + regenerating/dead variables
- PR #147 CI: Lint & Type Check (3.10/3.11/3.12) 모두 success

### Iteration 5 종료
- production_controller bare-except 5건에 debug 로깅 추가 (silent fail 제거)

### Iteration 6 종료
- 실제 버그: integration_hub.py f-string {len(positions)} → 일반 문자열 (런타임 NameError 위험 제거, F821)
- F811 import 중복 2건 (discord_advanced_features, jax_flax_rl)
- F402 loop var가 future-import shadow (spacy_nlp/sc2_strategy_parser)

### Iteration 7 종료
- F841 75 → 66: game_time 미사용 변수 8건 일괄 제거

### Iteration 8 종료
- F841 66 → 60: micro_interval, current_mode_str, can_afford_*, excess

### Iteration 9 종료
- F841 60 → 58: start_loc, early_window, current_time

## 📈 누적 임팩트

- **실제 버그 수정**: 8건
  - SyntaxError 1건 (game_analytics_system)
  - UnboundLocalError 위험 1건 (wicked_zerg_bot_pro_impl traceback)
  - 중복 정의로 인한 silent override 4건 (build_terran_counters, on_step, _prevent_resource_banking, _reduce_gas_workers, _find_harass_target)
  - AttributeError 1건 (is_supply_block typo)
  - NameError 위험 1건 (integration_hub f-string)
- **테스트 인프라**: 392 → 1043 테스트 활성 (sc2 stub conftest)
- **CI 상태**: 모든 Lint & Type Check (3.10/3.11/3.12) 통과
- **F-class lint**: 489 → ~280건 (-209)
- **black/isort**: 67/4 violations → 0

## 🔁 다음 사이클 계획

1. F841 잔여 58건 점진적 정리
2. F405 import-star 95건 (네임스페이스 명시화)
3. bare except 470+건 (위험도 별 logging 우선순위 적용)
4. E402 module-import-not-at-top 66건
5. tests/ + wicked_zerg_challenger/tests/ 통합 실행 isolation 분석
