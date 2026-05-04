# SC2 지휘관봇 개선 백로그 (2026-05-04)

테스트/점검 반복 사이클을 통해 식별된 개선 항목 모음. 각 항목에 우선순위(P0/P1/P2)와 카테고리를 부여한다.

## 카테고리
- **TEST**: 테스트 인프라/안정성
- **CODE**: 코드 품질/구조
- **LOGIC**: 봇 게임 로직
- **PERF**: 성능
- **DOC**: 문서

---

## P0 (즉시 처리)

| ID | 카테고리 | 설명 | 상태 |
|----|----------|------|------|
| I-001 | TEST | `test_gas_overflow_threshold_lowered`가 800인 코드와 1000 단언 불일치 | ✅ 해결 |
| I-002 | TEST | pytest-asyncio 미설치로 84 async 테스트 실패 | ✅ 해결 (uv tool install) |
| I-003 | TEST | 테스트마다 sys.path 조작이 중복됨 → conftest.py에 통합 | 🔧 진행 |
| I-004 | TEST | 테스트 단독 실행 시 EconomyManager import skip 문제 | 🔧 진행 |

## P1 (이번 주기)

| ID | 카테고리 | 설명 | 상태 |
|----|----------|------|------|
| I-010 | LOGIC | Transfusion 우선순위 — 고가 유닛(울트라/브루드로드) 우선 | 📋 |
| I-011 | LOGIC | Resource Reservation race condition | 📋 |
| I-012 | CODE | Position 계산 코드 중복 → util 함수로 통합 | 📋 |
| I-013 | CODE | 매직 넘버 → 명명된 상수로 추출 | 📋 |
| I-014 | TEST | conftest.py에 wicked_zerg_challenger sys.path 자동 추가 | 📋 |
| I-015 | TEST | sc2 의존성 누락 시 자동 mock fallback | 📋 |
| I-016 | LOGIC | 가스 오버플로우 임계치 800 검증 추가 (회귀 방지) | 📋 |

## P2 (다음 주기)

| ID | 카테고리 | 설명 |
|----|----------|------|
| I-020 | PERF | 빈번한 frame_cache 호출 프로파일링 |
| I-021 | LOGIC | DT(다크 템플러) 대응 spore 자동 배치 |
| I-022 | LOGIC | 히드라 사거리 업그레이드 우선순위 |
| I-023 | LOGIC | NYDUSCANAL 탐지/대응 강화 |
| I-024 | DOC | REMAINING_ISSUES.md 갱신 (해결된 이슈 정리) |
| I-025 | CODE | 97개 `from utils.logger` 일관성 (사용처 점검) |

---

## 사이클 진행 상황

- **Iter 1** (2026-05-04): I-001/I-002/I-003/I-014 해결 → 305→306 passed
- **Iter 2** (2026-05-04): I-016 신규 회귀 테스트 7건 추가 → 306→313 passed
  - gas_overflow_prevention_threshold, gas_worker_adjustment_interval,
    macro_hatchery_mineral_threshold, _expansion_cooldown, expansion_block_*
    gas_boost_duration, gas_timing_by_race 룩업
- **Iter 3** (2026-05-04): QueenManager(9건) + IntelManager(5건) 회귀 테스트 추가
  → 313→327 passed (tests/test_tuned_parameters.py 신설)
  - inject_cooldown 29.0, max_inject_distance 8.0, creep_energy 20,
    creep_spread_cooldown 4.0, max_queens_per_base 2, creep_queen_bonus 4,
    transfuse 임계값, update_interval 8, hidden_tech_alerts 매핑 검증
- **Iter 4** (예정): I-013 매직 넘버 / I-024 REMAINING_ISSUES.md 갱신
- **Iter N**: 점진 반복
