# SC2 지휘관봇 개선 리스트 (2026-04-27)

테스트 + ruff 정적 분석 기반 우선순위 개선 항목.

## 베이스라인
- pytest: **305 passed, 1 failed, 34 skipped**
- ruff(E,F,W,B): **2168 errors** (941 auto-fixable)

## P1 — 정확성 / 실제 버그 (즉시 수정)

| # | 파일 | 위치 | 문제 | 영향 |
|---|---|---|---|---|
| 1 | `tests/test_phase10_improvements.py` | 319 | 테스트가 `gas_overflow_prevention_threshold == 1000`을 기대하나 실제 값은 800. 코멘트는 "1000→800 강화"로 의도된 변경. 테스트 stale. | 1 failed test |
| 2 | `wicked_zerg_challenger/wicked_zerg_bot_pro_impl.py` | 691 | 같은 함수 `on_end` 안에서 `import traceback` 로컬 재선언 → 라인 574에서 참조 전 사용(F823). 모듈 레벨에서 이미 import됨. | UnboundLocalError 가능 |
| 3 | `wicked_zerg_challenger/local_training/production_resilience.py` | 1875 | `build_terran_counters` 중복 정의(F811). 두 번째 정의가 첫 번째를 덮어씀. | 죽은 코드 / 의도와 다른 분기 |
| 4 | `wicked_zerg_challenger/opponent_modeling.py` | 766 | `on_step` 중복 정의(F811). | 두번째 정의만 호출됨 |
| 5 | `wicked_zerg_challenger/creep_manager.py` | 588-590 | `math`, `Set`, `Tuple` 함수 내부에서 재import (이미 모듈 레벨 import) | 코드 노이즈 |
| 6 | `wicked_zerg_challenger/run_with_training.py` | 103-104 | `random`, `time` 함수 내부 재import | 코드 노이즈 |
| 7 | `wicked_zerg_challenger/spell_unit_manager.py` | 57 | `Dict` 함수 시그니처 안 재import | 코드 노이즈 |

## P2 — 자동 수정 가능 정적 분석 (대량)

| # | 룰 | 건수 | 설명 |
|---|---|---|---|
| 8 | F541 | 255 | placeholder 없는 f-string → 일반 string |
| 9 | F401 | 355 | unused import 제거 |
| 10 | W293 | 283 | 빈 줄에 공백 |
| 11 | E713 | 2 | `not in` 패턴 정리 |

→ `ruff check --fix` 941건 자동 수정.

## P3 — 수동 정리

| # | 룰 | 건수 | 설명 |
|---|---|---|---|
| 12 | F841 | 128 | 미사용 로컬 변수 |
| 13 | E501 | 837 | 한 줄 길이 초과 (black 적용 후 잔여) |
| 14 | F405 | 95 | `from X import *` 충돌 |
| 15 | E402 | 69 | 모듈 import가 파일 상단이 아님 |
| 16 | B007 | 60 | 미사용 루프 변수 |
| 17 | B023 | 30 | 클로저가 루프 변수 캡처 (잠재 버그) |
| 18 | B905 | 15 | `zip()` strict 미지정 |
| 19 | F811 | 8 | 중복 정의 (P1 외 잔여) |
| 20 | F811/import | 5 | trailing-whitespace |

## P4 — 인프라 / DX

| # | 항목 | 설명 |
|---|---|---|
| 21 | requirements | `pytest-asyncio>=0.21` 명시적 의존 추가 (없으면 84개 테스트 fail) |
| 22 | CI | ruff strict 게이트 점진 적용 (P1 룰만 우선 차단) |
| 23 | conftest.py | `asyncio_mode=auto` pytest.ini에 이미 설정됨 — 검증만 |

## 작업 순서

1. **Iteration 1**: P1 (#1-#7) — 7건 실 버그/테스트 수정
2. **Iteration 2**: P2 (#8-#11) — `ruff --fix` 자동 수정 941건
3. **Iteration 3**: P3 일부 (#12, #19) — F841, F811 잔여 수동
4. **Iteration 4**: P4 — 의존성 핀 + CI guard

각 iteration 후 pytest 재실행으로 회귀 검증.
