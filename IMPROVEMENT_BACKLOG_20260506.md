# SC2 지휘관 봇 개선 백로그 (2026-05-06)

테스트 점검 결과: `pytest tests/` → 306 passed, 34 skipped, 1 failure
(stale assertion fixed). 이를 토대로 도출한 대규모 개선 리스트.

## 1차: 전투/경제/전략 핵심 로직 개선 (이번 라운드)

| #   | 영역      | 항목                                                              | 우선순위 |
|-----|----------|-------------------------------------------------------------------|---------|
| A1  | tests    | `test_phase10_improvements.test_gas_overflow_threshold_lowered`<br/>stale 800 vs 1000 → 한도 비교로 전환 | 완료 |
| A2  | combat   | 공격 임계값 단(tier) 표를 dict로 분리 (분기 절감, 가독성) | 1차 |
| A3  | economy  | 가스 오버플로우 시 옮길 일꾼 수를 가스 잔량에 비례 (6 고정 → 4~10) | 1차 |
| A4  | economy  | macro hatchery 임계값 race 배수 (vs P 가속, vs Z 둔화) | 1차 |
| A5  | strategy | harassment_interval / log_cooldown 등을 `utils.game_constants`에 흡수 | 1차 |
| A6  | combat   | 재집결→공격 hysteresis (임계값 ±10% 버퍼)로 토글링 방지 | 1차 |
| A7  | utils    | 공격 임계값 헬퍼 `get_attack_threshold(game_time, vs_protoss)` 추가 | 1차 |

## 2차: 테스트 보강 및 추가 최적화

| #    | 영역  | 항목                                                                  |
|------|-------|----------------------------------------------------------------------|
| B1   | tests | `test_economy_manager.py` 에 gas overflow boundary 테스트 추가 |
| B2   | tests | `test_combat_manager.py` 에 protoss tier별 임계값 시나리오 추가 |
| B3   | tests | resource manager 다중-매니저 동시 예약 회귀 테스트 |
| B4   | utils | `position_utils.angle_to_target`, `dispersion_score` 추가 |
| B5   | utils | `game_constants.race_gas_timing` 헬퍼 추가 |
| B6   | tests | game_constants `seconds_to_iterations` round-trip 검증 |

## 3차: 코드 정리 및 회귀 테스트

| #   | 영역    | 항목                                                                      |
|-----|---------|---------------------------------------------------------------------------|
| C1  | combat  | `min_attack_threshold` 분기를 `utils` 헬퍼로 위임 |
| C2  | docs    | CHANGELOG / STATUS 갱신 (오늘 작업분 누적) |
| C3  | tests   | 회귀: 전체 pytest -q 통과 확인 |
| C4  | guard   | empty `logger()` 정규식 회귀 가드 (PLAN-NIGHTLY P0.2 idea) |

## 후속 (Future)

- D1 self-play harness 시작 (PLAN-NIGHTLY long-term)
- D2 build-order config 외부화 (TASK_WISHLIST 248 hardcoded values)
- D3 30+ 루트 .md 문서 정리 → docs/history/ (PLAN-NIGHTLY P1.5)
