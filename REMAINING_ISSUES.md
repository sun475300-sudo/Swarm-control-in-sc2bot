# 🔍 Remaining Issues - 추가 검토 결과

## 📋 개요

통합 문제 해결 후 발견된 추가 개선 사항들입니다.

**Last refreshed:** 2026-07-11 (자동 점검 사이클 — 테스트 전수 실행 + 코드 검사로 재검증)

### 📊 현재 테스트 현황 (2026-07-11 검증)

- `tests/` (루트, 크립토/디스코드/JARVIS 등 포함): **502 passed, 14 skipped, 0 failed**
- `wicked_zerg_challenger/tests/` (봇 전용): **661 passed, 0 failed**
- `tests/test_combat_phase_fsm.py`에서 스위트 전체 실행 시에만 재현되는 테스트 격리 버그 발견 및 수정
  (`asyncio.get_event_loop().run_until_complete()` → `asyncio.run()`; pytest-asyncio가 이전 async
  테스트의 이벤트 루프를 닫아버려 이후 동기 테스트에서 `RuntimeError: There is no current event loop`
  발생 — 실행 순서에 따라 CI가 간헐적으로 깨질 수 있었음).

---

## ✅ 재검증 완료 — 문서가 stale했던 항목 (2026-07-11)

아래 N1~N4 및 Issue #3~#5는 코드에 이미 반영되어 있음을 grep/read로 직접 확인했습니다.
문서만 갱신되지 않았던 것으로, 별도 작업 없이 닫습니다.

| ID | 설명 | 검증 |
|----|------|------|
| N1 | `OpponentModeling.on_step` 중복 정의 | `opponent_modeling.py`에 `on_step` 정의 1개만 존재 (line 341) |
| N2 | `EconomyManager._prevent_resource_banking` / `_reduce_gas_workers` 재정의 | `economy_manager.py`에 각 1개 정의만 존재 |
| N3 | `combat_manager._find_harass_target` 재정의 | `combat_manager.py`에 정의 1개(line 4992), 호출부 다수 — 정상 |
| N4 | `production_resilience.build_terran_counters` 재정의 | `local_training/production_resilience.py`에 정의 1개만 존재 |
| Issue #3 | Transfusion 우선순위 시스템 | `economy/queen_transfusion_manager.py`에 `HEAL_PRIORITY`/`CANNOT_HEAL` 구현 완료, `test_queen_transfusion*.py` 통과 |
| Issue #4 | Resource Reservation Race Condition | `core/resource_manager.py`에 `asyncio.Lock` 기반 `try_reserve()` 구현 완료, `test_resource_manager.py` 통과 |
| Issue #5 | Position 계산 중복 | `utils/position_utils.py`에 `get_center_position` / `get_weighted_center` 구현 완료 |

전체 `wicked_zerg_challenger/` + `crypto_trading/`에 대해 `flake8 --select=F811,F821` 재실행 결과
0건 확인 (N1~N4가 F811로 재발하지 않음).

**잔존 항목:**
| ID | 설명 | 우선순위 | 상태 |
|----|------|---------|------|
| N5 | bare `except Exception:` 다수 | 🟢 LOW | open (미측정, 재조사 필요) |
| N6 | F841 unused local variables | 🟢 LOW | open — 2026-07-11 재측정: 134건 (대부분 `visuals/`, `make_pptx.py` 등 프레젠테이션 코드) |

---

## ✅ Resolved (확인일: 2026-04-27)

이전 버전(2026-01-29)에 남아있던 두 이슈는 코드에 이미 반영된 상태로 확인됐습니다.
문서가 stale했던 것으로, 별도 작업 없이 닫습니다.

### ✅ (PR #44) Issue #6 부분 해결: Queen Manager magic numbers

`queen_manager.py` 인스턴스 기본값 11종을 `GameConfig` 클래스 상수로 이동.
회귀 테스트 7건 추가 (`tests/test_queen_manager_constants.py`).

| 상수 | GameConfig 키 |
|------|--------------|
| inject_energy_threshold (25) | `QUEEN_INJECT_ENERGY_THRESHOLD` |
| inject_cooldown (29.0s) | `QUEEN_INJECT_COOLDOWN_SEC` |
| max_inject_distance (8.0) | `QUEEN_MAX_INJECT_DISTANCE` |
| creep_energy_threshold (20) | `QUEEN_CREEP_SPREAD_ENERGY` |
| creep_spread_cooldown (4.0s) | `QUEEN_CREEP_SPREAD_COOLDOWN_SEC` |
| inject_queen_creep_threshold (35) | `QUEEN_INJECT_QUEEN_CREEP_ENERGY` |
| transfuse_energy_threshold (50) | `QUEEN_TRANSFUSE_ENERGY_THRESHOLD` |
| transfuse_cooldown (1.0s) | `QUEEN_TRANSFUSE_COOLDOWN_SEC` |
| transfuse_health_threshold (0.5) | `QUEEN_TRANSFUSE_HP_THRESHOLD` |
| max_queens_per_base (2) | `QUEEN_MAX_PER_BASE` |
| creep_queen_bonus (4) | `QUEEN_CREEP_BONUS_QUEENS` |

### ✅ Issue #1: Queen Inject 쿨다운 — 25→29초 수정 완료

| Where | Verification |
|-------|--------------|
| `wicked_zerg_challenger/queen_manager.py:60` | `self.inject_cooldown = 29.0  # ★ FIXED: SC2 Spawn Larva 쿨다운 28.57초 + 0.43초 여유 ★` |
| `wicked_zerg_challenger/economy/queen_inject_optimizer.py:69` | `self.INJECT_COOLDOWN = 29.0  # 29초 쿨다운` |

### ✅ Issue #2: 누락 업그레이드 — Adrenal Glands + Grooved Spines 구현 완료

| Where | Verification |
|-------|--------------|
| `wicked_zerg_challenger/upgrade_manager.py:819-820` | `"""아드레날린 분비선 (Adrenal Glands) 연구 - 저글링 공속업 (Crackling)"""` → `adrenal = getattr(UpgradeId, "ZERGLINGATTACKSPEED", None)` |
| `wicked_zerg_challenger/upgrade_manager.py:740-741` | `"""홈 스파인 (Grooved Spines) 연구 - 히드라 사거리 +2"""` → `hydra_range = getattr(UpgradeId, "EVOLVEGROOVEDSPINES", None)` |

검증 출처: `ACTION_LOG_20260419.md` Task #6.

---

## ✅ Resolved — 상세 구현 계획 (참고용, 아카이브)

Issue #3 (Transfusion 우선순위), #4 (Resource Reservation Race Condition), #5 (Position
계산 중복)의 원래 제안 코드 스니펫은 위 '재검증 완료' 표에서 확인한 대로 이미 프로덕션
코드에 구현되어 있습니다. 원래 제안 예시 코드는 `git log`에서 이 문서의 과거 버전을
참고하세요 — 실제 구현은 `economy/queen_transfusion_manager.py`,
`core/resource_manager.py`, `utils/position_utils.py`를 참고할 것.

---

### Issue #6: 매직 넘버 (Magic Numbers)

**위치**: 여러 파일

**문제**:
```python
# 매직 넘버 남발
if unit.health_percentage < 0.4:  # 0.4가 뭔지 불명확
    burrow()

if distance < 15:  # 15가 무슨 의미인지 불명확
    retreat()

if iteration % 22 == 0:  # 22가 왜 22인지 불명확
    check_upgrades()
```

**해결 방법**:
```python
# constants.py (새 파일 또는 기존 파일에 추가)

# Combat Thresholds
BURROW_HP_THRESHOLD = 0.4  # 40% 이하 체력
RETREAT_HP_THRESHOLD = 0.3  # 30% 이하 체력
FULL_HP_THRESHOLD = 0.8    # 80% 이상 체력

# Distance Thresholds
DETECTOR_THREAT_RANGE = 15  # 디텍터 위협 거리
RETREAT_DISTANCE = 20       # 후퇴 안전 거리
MELEE_RANGE = 2             # 근접 사거리

# Timing Constants
GAME_FPS = 22               # SC2 게임 FPS
SECOND = GAME_FPS           # 1초 = 22 프레임
MINUTE = SECOND * 60        # 1분 = 1320 프레임

# Usage
if iteration % SECOND == 0:  # 1초마다
    check_upgrades()

if iteration % (5 * MINUTE) == 0:  # 5분마다
    major_check()
```

**개선된 코드**:
```python
from constants import BURROW_HP_THRESHOLD, DETECTOR_THREAT_RANGE, SECOND

# 명확한 의미
if unit.health_percentage < BURROW_HP_THRESHOLD:
    burrow()

if distance < DETECTOR_THREAT_RANGE:
    retreat()

if iteration % SECOND == 0:
    check_upgrades()
```

**우선순위**: 🟢 LOW (가독성 개선)

**2026-07-11 재검증**: `utils/game_constants.py`에 `GameFrequencies`/`BURROW_HP_THRESHOLD` 등
정확히 이 제안대로 구현되어 있음. 다만 실제로 `from utils.game_constants import`를 쓰는 파일은
`combat_manager.py`, `building_manager.py`, `economy_manager.py` 3개뿐 — 인프라는 완성되었으나
나머지 매니저 파일 전반에는 아직 롤아웃되지 않음 (Sprint 7.3 문서대로 여전히 하드코딩된 22/33/66
등의 iteration 상수가 다수 파일에 남아있을 가능성 높음). **부분 완료로 재분류.**

---

## 📊 이슈 우선순위 요약 (open만)

| 우선순위 | 이슈 | 상태 |
|---------|------|------|
| 🟢 LOW | #6 매직 넘버 → `GameFrequencies`/`GameConfig` 롤아웃 확대 | 부분 완료 — 인프라 존재, 3개 파일만 채택 |
| 🟢 LOW | N5 bare `except Exception:` 정리 | 미측정, 재조사 필요 |
| 🟢 LOW | N6 F841 unused local variables | 134건 (대부분 `visuals/` 프레젠테이션 코드) |

(Issue #1~#5, N1~N4 → ✅ 위 재검증 섹션에서 모두 해결 확인)

---

## 🎯 다음 작업 우선순위 (2026-07-11 갱신)

1. `GameFrequencies`/`GameConfig` 상수를 `combat_manager.py`/`building_manager.py`/
   `economy_manager.py` 외 나머지 매니저 파일로 확대 롤아웃 (Sprint 7.3).
2. `ROADMAP.md`의 테스트 카운트(`342/342`)가 stale — 실제로는 `tests/` 502 passed +
   `wicked_zerg_challenger/tests/` 661 passed로 이미 크게 초과 달성. 문서 갱신 필요.
3. N5 (bare except) 잔여 건수 재측정 후 우선순위 재산정.
4. Sprint 8 QA (Medium AI 30연전, Arena 패키지 검증)는 로컬에 SC2 게임 클라이언트가 필요해
   이 저장소 점검 세션(CI 컨테이너)에서는 실행 불가 — 실제 게임 환경에서 수행 필요.

---

## 🔍 추가 검토 필요 항목

### Performance Optimization
- [ ] Pathfinding 캐싱 확인
- [ ] Unit filtering 최적화 검토
- [ ] Blackboard 업데이트 빈도 분석

### Strategic Improvements
- [ ] Counter-build 시스템 확인 (적 유닛 조합 대응)
- [ ] Scouting 타이밍 최적화
- [ ] Expansion timing 검증

### Code Quality
- [ ] Type hints 추가 (Python 3.10+)
- [ ] Docstring 완성도 검토
- [ ] 에러 핸들링 일관성 확인 (N5)

---

## 📝 참고 사항

### 현재 상태 (2026-07-11 자동 점검 사이클 기준)
- ✅ **치명적 통합 문제**: 완전히 해결됨
- ✅ **전체 테스트**: `tests/` 502 passed / `wicked_zerg_challenger/tests/` 661 passed, 실패 0건
- ✅ **테스트 격리 버그**: `test_combat_phase_fsm.py` 이벤트 루프 버그 수정 완료
- ✅ **기본 기능**: 정상 작동
- ✅ **Issue #1~#5, N1~N4**: 모두 코드에 반영되어 있음을 재확인 (문서만 stale했음)

### 남은 이슈들은
- 모두 **선택적 개선 사항** (매직 넘버 롤아웃 확대, bare except 정리, 프레젠테이션 코드 unused 변수)
- 즉시 수정 불필요
- 점진적 개선 권장

---

**검토 완료일**: 2026-07-11
**상태**: 자동 점검 사이클 — 테스트 실행 + 이전 이슈 재검증 + 테스트 격리 버그 수정 완료
