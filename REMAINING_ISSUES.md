# 🔍 Remaining Issues - 추가 검토 결과

## 📋 개요

통합 문제 해결 후 발견된 추가 개선 사항들입니다.

**Last refreshed:** 2026-07-04 (Issue #1-#5 confirmed resolved in code; N1-N4 confirmed resolved; Issue #6/N5/N6 partial, ongoing)

---

## 🆕 신규 발견 (PR #44, 2026-04-27) — N1~N4 2026-07-04 재검증 결과 모두 해결됨

자동/수동 점검 사이클(테스트 → 코드 검사 → 개선 → 커밋/푸시 반복)에서 새로 식별된 항목.

| ID | 설명 | 우선순위 | 상태 |
|----|------|---------|------|
| N1 | `OpponentModeling.on_step` 중복 정의 (line 341 vs 765 — F811) | 🟠 HIGH | ✅ resolved — `flake8 --select=F811` 결과 0건, 정의 1개만 존재 (line 341) |
| N2 | `EconomyManager._prevent_resource_banking` / `_reduce_gas_workers` 재정의 (F811) | 🟡 MED | ✅ resolved — 각각 정의 1개만 존재 |
| N3 | `combat_manager._find_harass_target` 재정의 (line 2377 vs 4278) | 🟡 MED | ✅ resolved — 정의 1개만 존재 (line 4992) |
| N4 | `production_resilience.build_terran_counters` 재정의 (1369 vs 1866) | 🟡 MED | ✅ resolved — 정의 1개만 존재 |
| N5 | bare `except Exception:` 다수 (≈360+) — 이번 PR에서 12건 처리, 잔여 다수 | 🟢 LOW | partial — 점진 진행 |
| N6 | F841 unused local variables (visuals/make_pptx 등) | 🟢 LOW | partial — `flake8 --select=F841` 130건 잔여 (대부분 presentation/visuals 코드) |

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

## ✅ Resolved (확인일: 2026-07-04)

코드베이스가 이 문서보다 앞서 있었던 항목들. 실제 구현을 확인 후 종결합니다.

### ✅ Issue #3: Transfusion 우선순위 개선 — 구현 완료

`wicked_zerg_challenger/economy/queen_transfusion_manager.py`에 `HEAL_PRIORITY`
딕셔너리, `CANNOT_HEAL` 제외 목록, 우선순위 기반 타겟 정렬 로직이 모두 존재.
문서가 제안한 설계와 사실상 동일하게 구현되어 있음 (line 26 `HEAL_PRIORITY`,
line 43 `CANNOT_HEAL`, line 172 정렬 키).

### ✅ Issue #4: Resource Reservation Race Condition — 구현 완료

`wicked_zerg_challenger/core/resource_manager.py`의 `ResourceManager`에
`asyncio.Lock()` (line 36) + `try_reserve()` (line 50) + `_reserved_minerals`/
`_reserved_gas` 추적이 모두 구현되어 있음. 문서가 제안한 설계와 일치.

### ✅ Issue #5: 코드 중복 - Position 계산 — 구현 완료

`wicked_zerg_challenger/utils/position_utils.py`에 `get_center_position()`,
`get_weighted_center()` 유틸리티 존재 및 사용 중.

---

## 🟢 LOW Priority Issues (still open)

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

---

## 📊 이슈 우선순위 요약 (open만)

| 우선순위 | 이슈 | 영향도 | 난이도 |
|---------|------|--------|--------|
| 🟢 LOW | #6 매직 넘버 | 낮음 | 쉬움 (부분 진행 중 — `utils/game_constants.py` 존재, 전체 교체는 미완) |

(Issue #1~#5 → ✅ Resolved 섹션 참조. 2026-07-04 코드 감사 결과 #3/#4/#5는 이미 구현되어 있었음.)

---

## 🎯 권장 수정 순서

### 1단계: 완료 (✅)
~~1. Queen Inject 쿨다운 수정 (25 → 29)~~ — 코드 반영 완료, 본 문서 ✅ Resolved 섹션 참조
~~2. 누락된 업그레이드 추가~~ — 코드 반영 완료, 본 문서 ✅ Resolved 섹션 참조
~~3. Transfusion 우선순위 시스템~~ — 구현 완료 (2026-07-04 확인)
~~4. Resource Reservation 동기화~~ — 구현 완료 (2026-07-04 확인)
~~5. Position Utils 유틸리티 함수 분리~~ — 구현 완료 (2026-07-04 확인)

### 2단계: 남은 작업
6. Constants 정리 (매직 넘버 → `game_constants.py` 전체 교체, 점진 진행)

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
- [ ] 에러 핸들링 일관성 확인

---

## 📝 참고 사항

### 현재 상태 (2026-07-04 재검증)
- ✅ **치명적 통합 문제**: 완전히 해결됨
- ✅ **전체 테스트 스위트**: 502 passed, 14 skipped, 0 failed
- ✅ **CI lint gate (black/isort)**: 66개 파일 포맷 드리프트 수정, 통과
- ✅ **기본 기능**: 정상 작동

### 남은 이슈들은
- 모두 **선택적 개선 사항** (Issue #6 매직 넘버, N5/N6 코드 품질)
- 즉시 수정 불필요
- 점진적 개선 권장

---

**검토 완료일**: 2026-07-04
**상태**: 코드 감사로 Issue #3~#5, N1~N4 해결 확인 및 문서 정리 완료
