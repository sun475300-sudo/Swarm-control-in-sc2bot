# 🔧 SC2 지휘관봇 — 점검 & 개선 백로그

자동 점검(테스트 → 분석 → 개선 → 커밋/푸시 반복) 사이클로 발견된 항목.

세션 시작: 2026-05-15
브랜치: `claude/stoic-shannon-fXFeQ`

---

## 📊 현재 테스트 상태

| 항목 | 값 |
|------|-----|
| 수집된 테스트 | 420 |
| **수집 차단(import 실패)** | 1 (test_queen_transfusion.py) |
| 통과 | 385 (수집 차단 이후) |
| 실패 (cryptography PyO3 패닉) | 7 |
| 통과 (의존성 우회) | 365 |
| 스킵 | 22~33 |

실행 명령: `python -m pytest tests/` (plain `pytest`는 uv-tool 격리로 plugin 미인식)

---

## 🔥 Critical: 실제 버그 (즉시 수정)

봇 프로덕션 동작에 영향을 주는 항목. Python은 동일 클래스 내 중복 메서드 정의 시 *후자가 전자를 덮어쓴다.* 즉 전자 구현이 전혀 실행되지 않는 dead code다.

| ID | 파일 | 라인 | 메서드 | 영향 |
|----|------|------|--------|------|
| C1 | `wicked_zerg_challenger/opponent_modeling.py` | 341 vs 765 | `on_step` | **풀 구현이 죽고 단순 구현만 실행됨** → 빌드오더 트래킹, 타이밍 공격 감지, 테크 추적, 블랙보드 업데이트 모두 미실행 |
| C2 | `wicked_zerg_challenger/economy_manager.py` | 1681 vs 3258 | `_prevent_resource_banking` | 자원 뱅킹 방지 로직 한쪽이 무시됨 |
| C3 | `wicked_zerg_challenger/economy_manager.py` | 3391 vs 4082 | `_reduce_gas_workers` | 가스 워커 감축 로직 중복 |
| C4 | `wicked_zerg_challenger/combat_manager.py` | 2809 vs 5005 | `_find_harass_target` | 견제 타깃 탐색 중복 |
| C5 | `wicked_zerg_challenger/local_training/production_resilience.py` | 1467 vs 1977 | `build_terran_counters` | 테란 카운터 빌드 중복 |

---

## 🟠 High: 테스트 인프라 (CI 신뢰성)

| ID | 파일/주제 | 문제 | 수정 방향 |
|----|-----------|------|----------|
| H1 | `tests/test_queen_transfusion.py` | top-level `from sc2.ids.unit_typeid import UnitTypeId` 가 모듈 부재 시 **수집 전체 차단** | 조건부 import + `pytest.importorskip` |
| H2 | `tests/test_crypto_trading.py` | `cryptography` 모듈 Rust 바인딩 PyO3 패닉 (`_cffi_backend` 부재) → 7건 실패 | `pytest.importorskip("cryptography")` + try/except |
| H3 | `tests/test_security.py` | 동일 (cryptography import 패닉) | 동일 패턴 |
| H4 | `pytest.ini` | 루트 pytest.ini가 testpaths=tests로 wicked_zerg_challenger 테스트는 발견 못함 | 별도 처리 또는 명시 |

---

## 🟡 Medium: 코드 품질

| ID | 항목 | 비고 |
|----|------|------|
| M1 | bare `except Exception:` 360+ 곳 (REMAINING_ISSUES.md N5) | 점진 개선 |
| M2 | F841 unused locals (presentation 등) | 점진 |

---

## ✅ 작업 순서 — 사이클 #1 진행 상황

| Phase | 항목 | 상태 |
|-------|------|------|
| 1 | H1/H2/H3 테스트 수집 차단/PyO3 패닉 해소 | ✅ **완료** (commit 35e2776) |
| 2 | C1 — opponent_modeling on_step + current_opponent_id 통일 | ✅ **완료** |
| 3 | C2/C3 — economy_manager `_prevent_resource_banking`/`_reduce_gas_workers` 중복 제거 | ✅ **완료** |
| 4 | C4 — combat_manager `_find_harass_target` 중복 제거 | ✅ **완료** |
| 5 | C5 — production_resilience `build_terran_counters` 중복 제거 | ✅ **완료** |
| 6 | 전체 테스트 재실행 + 커밋/푸시 | ✅ **완료** (365 passed / 25 skipped / 0 failed) |

다음 사이클 후보 (추가 점검 필요):
- M1 — bare `except Exception:` 360+ 곳 정리 (점진)
- 추가 F811 잔여 확인 (다른 매니저 파일)
- 통합 테스트(`tests/integration/`) 실행 가능성 점검
- `wicked_zerg_challenger/tests/` 별도 테스트 디렉토리 가시화

---

## 🔁 사이클 #2 — 추가 발견 (2026-05-15)

pyflakes 전체 스캔으로 새로 발견된 항목.

### 🔥 Critical

| ID | 파일/라인 | 문제 | 상태 |
|----|-----------|------|------|
| C6 | `wicked_zerg_challenger/game_analytics_system.py:419` | **IndentationError** — 중복된 `logger.info`와 `except` 블록 garbled. 파일이 import 불가능 | ✅ **수정** — 중복 4줄 삭제, 파싱 정상화 |
| C7 | `wicked_zerg_challenger/bot_step_integration.py` (11곳) | `except Exception as e: if debug_mode: raise` — 프로덕션에서 에러가 소리없이 사라짐. SpatialOptimizer / DataCache / BaseDestruction / BuildingDestroyer / SelfHealing / Personality / BattlePrep / DestructibleAwareness / NydusTrainer / OverlordSafety / CreepHighwayAStar 11개 서브시스템 영향 | ✅ **수정** — 기존 CreepDenial 패턴(rate-limited logger.error)으로 11곳 통일 |

### 🟡 Medium — 다음 사이클 후보

- f-string is missing placeholders 249곳 (스타일/일부 누락된 변수 보간 가능성) — 파일별로 정리 필요
- 미사용 지역 변수 (`game_time`, `regenerating`, `strategy_manager`, `non_combat_names` 등) — 죽은 코드 단서일 수 있음 ⇒ 각 케이스 검토 필요
- ursina 모듈의 `from ursina import *` 별 정의 누락 경고 (visuals 패키지) — 외부 라이브러리이므로 영향 작음
