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

## 🟠 High Priority (Iteration 2+에서 처리 예정)

| ID | 이슈 | 위치 | 우선순위 |
|----|------|------|----------|
| H1 | `EconomyManager._prevent_resource_banking` 재정의 (F811) | `economy_manager.py` (REMAINING_ISSUES N2) | 🟠 |
| H2 | `EconomyManager._reduce_gas_workers` 재정의 (F811) | `economy_manager.py` (REMAINING_ISSUES N2) | 🟠 |
| H3 | `combat_manager._find_harass_target` 재정의 (line 2377 vs 4278) | `combat_manager.py` (REMAINING_ISSUES N3) | 🟠 |
| H4 | `production_resilience.build_terran_counters` 재정의 | `production_resilience.py` (REMAINING_ISSUES N4) | ✅ 본 사이클에서 처리 |
| H5 | bare `except Exception:` 360+건 (silent failure 위험) | 전체 코드 | 🟡 점진적 |
| H6 | F841 unused-variable 131건 (잠재 버그/dead code) | 전체 코드 | 🟡 |
| H7 | F405 undefined-local-with-import-star 95건 (네임스페이스 오염) | 전체 코드 | 🟡 |

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

## 📊 메트릭 (Iteration 1 종료 시점)

- 테스트: tests/ 392 passed, 34 skipped, 0 failed
- 정적 분석: critical errors 0건 (E9/F811/F823/F401/F541 → 0)
- 나머지 lint: 318건 (대부분 cosmetic)
- wicked_zerg_challenger/tests: sc2 의존성으로 24 collect error (환경 제약)

## 🔁 다음 사이클 계획

1. H1-H3 처리 (EconomyManager/CombatManager 중복 메서드 제거)
2. F841 unused-variable 안전한 항목부터 정리
3. bare except 가운데 silent-fail 위험 큰 곳 식별 후 logging 추가
4. sc2 stub conftest 도입으로 wicked_zerg_challenger 테스트 collect 가능하게
