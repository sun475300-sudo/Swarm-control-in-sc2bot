# SC2 Commander Bot — 대규모 개선 백로그

> 자동 테스트/점검 사이클로 추출한 개선 항목을 우선순위별로 모아둔다.
> 각 항목은 batch 단위로 처리되며, batch 완료시 commit & push 후 다음 batch로 진행한다.

## Snapshot (현재 상태)

- 브랜치: `claude/stoic-shannon-CG7bM`
- pytest 결과: **340 passed, 20 skipped, 1 warning** (이전: 305 passed, 1 failed, 34 skipped)
- 베이스라인: pytest 9.0.3, pytest-asyncio 1.3.0, numpy 2.4.4, cffi 2.0.0

## ✅ BATCH 1 — 테스트 안정화 (완료)

| #     | 항목                                                                    | 파일                                                                        |
|-------|-------------------------------------------------------------------------|----------------------------------------------------------------------------|
| B1.1  | `test_gas_overflow_threshold_lowered` 실코드(=800)와 동기화 — 의도(≤1000) 검증 | `tests/test_phase10_improvements.py:282`                                   |
| B1.2  | `qmix_marl/sc2_qmix_agent.py` torch 미설치시 `nn.Module` import 실패 fix    | `qmix_marl/sc2_qmix_agent.py:39`                                           |
| B1.3  | `mappo_marl/sc2_mappo_agent.py` 동일 fix + `__init__.py` import 안정화       | `mappo_marl/sc2_mappo_agent.py:37`, `mappo_marl/__init__.py`               |
| B1.4  | `comm_learning/__init__.py` 존재하지 않는 클래스 import 제거                 | `comm_learning/__init__.py`                                                |
| B1.5  | empty `logger.<level>()` regression guard를 단위 테스트로 추가              | `tests/test_empty_logger_guard.py`                                         |

## 🔜 BATCH 2 — 코드 품질/일관성

| #     | 항목                                                                    |
|-------|-------------------------------------------------------------------------|
| B2.1  | `pytest.ini`의 `timeout` 옵션 → pytest-timeout 미설치시 경고. 경고 제거 또는 `pip install pytest-timeout` |
| B2.2  | numpy 미설치 환경에서 skip 처리되는 10개 테스트 → numpy 의존을 graceful fallback으로 분리 |
| B2.3  | `config.yaml` 미존재로 skip되는 8개 테스트 → 테스트용 fixture로 in-memory config 제공 |
| B2.4  | `sc2 library`가 없어 skip되는 5개 테스트 → MockBot 인프라 강화로 import-time skip 제거 |
| B2.5  | `wicked_zerg_challenger/` 안의 미사용 import 자동 제거 (lint pass) |
| B2.6  | `print()` 잔존 사용처 grep — 이미 logger 마이그레이션 후 잔여물 정리 |

## 🔜 BATCH 3 — 봇 로직 개선 (PLAN-NIGHTLY P1 매핑)

| #     | 항목                                                                    | 출처             |
|-------|-------------------------------------------------------------------------|------------------|
| B3.1  | scout cadence (initial overlord 30s, mid-zergling 60s, late-overseer cloak detect) | PLAN-NIGHTLY P1.1 |
| B3.2  | harassment loop polish — 적 본진 진입, HP 임계 후퇴, 적 일꾼 킬 카운트 추적 | PLAN-NIGHTLY P1.2 |
| B3.3  | first-expansion timing 회귀 테스트 (≤6분 보장)                          | PLAN-NIGHTLY P1.3 |
| B3.4  | scout system 중복 제거 (`advanced_scout_system_v2` vs `realtime_awareness_engine`) | PLAN-NIGHTLY P1.4 |
| B3.5  | top-level `*.md` 30+ 파일 → `docs/history/`로 이관                       | PLAN-NIGHTLY P1.5 |

## 🔜 BATCH 4 — Nice-to-have (PLAN-NIGHTLY P2)

| #     | 항목                                                                    | 출처             |
|-------|-------------------------------------------------------------------------|------------------|
| B4.1  | force-accumulation FSM 상태 전이 테스트                                 | PLAN-NIGHTLY P2.1 |
| B4.2  | 엔드포인트 벤치마크 (APM/supply/first-expand/win-rate) 단일 명령        | PLAN-NIGHTLY P2.2 |
| B4.3  | hardcoded build-order 248개 → `config/build_orders.yaml`로 외부화 (top 20) | PLAN-NIGHTLY P2.3 |
| B4.4  | RL agent save-experience disk-full/interrupted-rename 단위 테스트         | PLAN-NIGHTLY P2.4 |

## 🔜 BATCH 5 — 장기 방향성

- AI Arena 2주 제출 케이던스 정착
- self-play loop (P823) 기반 인프라
- macro/micro 디렉터리 분리 (`wicked_zerg_challenger/macro/` vs `micro/`)

---

## 사이클 운영 방식

1. 위에서 가장 위 batch 1개를 in_progress로 표시
2. 해당 batch의 모든 항목을 코드 변경
3. `python -m pytest tests/ -q` 실행 → 회귀 없음 확인
4. 의미 있는 commit 메시지로 commit
5. `git push -u origin claude/stoic-shannon-CG7bM`
6. 다음 batch로 진행 (1번부터 반복)
