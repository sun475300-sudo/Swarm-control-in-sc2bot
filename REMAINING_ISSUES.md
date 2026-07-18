# 🔍 Remaining Issues - 추가 검토 결과

## 📋 개요

통합 문제 해결 후 발견된 추가 개선 사항들입니다.

**Last refreshed:** 2026-07-18 (자동 점검 사이클 — N1~N4 재검증 완료, 신규 이슈 3건 발견/수정)

---

## 🆕 신규 발견 (2026-07-18 자동 점검 사이클)

테스트 실행 → flake8 정적 분석 → 코드 대조 검증을 통해 새로 식별/수정한 항목.

| ID | 설명 | 우선순위 | 상태 |
|----|------|---------|------|
| N7 | `unittest.TestCase` 하위 `async def test_*`가 pytest에서 실제로 await되지 않고 "coroutine was never awaited" 경고와 함께 조용히 PASS 처리됨 (`test_production_resilience.py`, `test_opponent_modeling.py`, 총 18개 테스트) | 🔴 HIGH | ✅ fixed — 두 클래스를 `unittest.IsolatedAsyncioTestCase`로 전환 |
| N8 | N7 수정 후 실제로 실행되자 `test_get_counter_unit_*` 3건이 진짜로 FAIL — 테스트가 구버전 `_get_counter_unit(race_name)` API를 호출하고 있었고, 실제 구현은 `_get_counter_unit(enemy_units, has_roach_warren, has_hydra_den, has_spire)`로 이미 리팩터링됨 | 🟠 HIGH | ✅ fixed — 테스트를 현재 시그니처에 맞게 재작성 (+ enemy_units=[] 케이스 추가) |
| N9 | `ProductionResilience._produce_army_unit`의 late-game(10분+) 블록 주석은 "Priority: Muta > Hydra > Roach > Zergling"이라고 되어 있으나, 실제 코드는 Mutalisk를 전혀 훈련하지 않고 Hydralisk부터 시작 — Spire 완성 후에도 뮤탈리스크를 생산하지 않는 실전 버그 | 🟠 HIGH | ✅ fixed — Mutalisk 우선 분기 추가 + 회귀 테스트(`test_late_game_prioritizes_mutalisk_over_hydralisk`) 추가 |

기존 N1~N4(중복 정의로 인한 동작 미실행 의심)는 flake8 F811 재검사 결과 **0건**으로 확인 — PR #218(2026-04-27 병합, "stabilize SC2 bot test suite and iterate on improvements")에서 이미 해결되었으나 본 문서가 stale 상태였음. N5(bare except)는 여전히 다수(455건) 남아있고 저위험 항목이라 점진적 개선 대상으로 유지. N6은 프레젠테이션/시각화 코드 한정이라 영향 낮음, 미착수.

검증 권장: 위 항목 모두 `pytest wicked_zerg_challenger/tests/` 663 passed로 회귀 없음 확인됨.

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

## 🟡 MEDIUM Priority Issues (still open)

### ✅ Issue #3: Transfusion 우선순위 개선 — Resolved (검증일: 2026-07-18)

`wicked_zerg_challenger/economy/queen_transfusion_manager.py`의 `QueenTransfusionManager`가
아래 제안보다 더 정교한 형태(중복 힐 방지, 큐 쿨다운, 13종 우선순위 맵, CANNOT_HEAL 13종)로
이미 구현되어 있고, `bot_step_integration.py`에서 `self.bot.queen_transfusion`으로 실제
매 스텝 호출됨을 확인. 문서가 stale했던 것으로 별도 작업 불필요.

<details><summary>원래 문제 설명 (참고용, 이미 해결됨)</summary>

**위치**: `queen_manager.py` 또는 `spell_unit_manager.py`

**현재 문제**:
- Transfusion 로직이 단순함
- 고가 유닛(울트라, 브루드로드) 우선순위 없음
- 군단 숙주, 맹독충 등 치료 불가 유닛에 낭비 가능성

**개선 방법**:
```python
async def smart_transfusion(self, queen, damaged_units):
    """
    스마트 수혈 - 우선순위 기반

    우선순위:
    1. 울트라리스크 (300/200 고가 유닛)
    2. 브루드로드 (150/150/2)
    3. 바퀴 (75/25)
    4. 히드라 (100/50)
    5. 저글링 (25/0)
    """
    if queen.energy < 50:
        return

    # 치료 우선순위 정의
    HEAL_PRIORITY = {
        UnitTypeId.ULTRALISK: 100,
        UnitTypeId.BROODLORD: 90,
        UnitTypeId.ROACH: 70,
        UnitTypeId.RAVAGER: 75,
        UnitTypeId.HYDRALISK: 60,
        UnitTypeId.MUTALISK: 50,
        UnitTypeId.CORRUPTOR: 50,
        UnitTypeId.ZERGLING: 30,
    }

    # 치료 불가 유닛 제외
    CANNOT_HEAL = {
        UnitTypeId.BANELING,  # 맹독충 (자폭 유닛)
        UnitTypeId.BROODLING,  # 무리 (일회용)
        UnitTypeId.LOCUSTMP,  # 군단 숙주 (일회용)
    }

    # 우선순위대로 정렬
    valid_targets = [
        u for u in damaged_units
        if u.type_id not in CANNOT_HEAL and u.health_percentage < 0.6
    ]

    if not valid_targets:
        return

    # 우선순위 정렬 (priority desc, health% asc)
    valid_targets.sort(
        key=lambda u: (
            -HEAL_PRIORITY.get(u.type_id, 0),  # 우선순위 높을수록
            u.health_percentage  # 체력 낮을수록
        )
    )

    best_target = valid_targets[0]

    # 수혈 실행 (50 에너지, +125 HP)
    if queen.distance_to(best_target) <= 7:
        from sc2.ids.ability_id import AbilityId
        self.bot.do(queen(AbilityId.TRANSFUSION_TRANSFUSION, best_target))
```

**우선순위**: 🟡 MEDIUM (자원 효율성 개선)

</details>

---

### ✅ Issue #4: Resource Reservation Race Condition — Resolved (검증일: 2026-07-18)

`wicked_zerg_challenger/core/resource_manager.py`의 `ResourceManager`가 아래 제안대로
`asyncio.Lock` 기반 `try_reserve`/`release`/`release_partial`을 구현하고 있고,
`economy_manager.py`, `defense_coordinator.py`에서 실제로 `await self.bot.resource_manager.try_reserve(...)`
호출을 확인. `bot_step_integration.py`에서 매니저 초기화 및 stale reservation 정리(`clear_stale_reservations`)도
함께 wiring됨. 문서가 stale했던 것으로 별도 작업 불필요.

<details><summary>원래 문제 설명 (참고용, 이미 해결됨)</summary>

**위치**: `resource_manager.py` (추정)

**문제**:
- 여러 매니저가 동시에 자원 예약 시도
- 경쟁 조건(race condition) 발생 가능
- 자원 이중 예약 위험

**예시**:
```python
# upgrade_manager가 저장된 자원 확인
if self.bot.minerals >= 200:
    # ★ 이 순간 다른 매니저도 200 미네랄 확인 가능 ★
    reserve_resources(200, 0)

# building_manager도 동시에
if self.bot.minerals >= 150:
    # ★ 같은 자원을 중복 예약! ★
    reserve_resources(150, 0)
```

**해결 방법**:
```python
class ResourceManager:
    def __init__(self):
        self._lock = asyncio.Lock()  # 동기화 잠금
        self._reserved_minerals = 0
        self._reserved_gas = 0

    async def try_reserve(self, minerals: int, gas: int, manager_name: str) -> bool:
        """
        자원 예약 시도 (thread-safe)

        Returns:
            성공 시 True, 실패 시 False
        """
        async with self._lock:  # 원자적 작업 보장
            available_minerals = self.bot.minerals - self._reserved_minerals
            available_gas = self.bot.vespene - self._reserved_gas

            if available_minerals >= minerals and available_gas >= gas:
                self._reserved_minerals += minerals
                self._reserved_gas += gas

                self.logger.debug(
                    f"{manager_name} reserved {minerals}M/{gas}G "
                    f"(Total reserved: {self._reserved_minerals}M/{self._reserved_gas}G)"
                )
                return True

            return False

    async def release(self, minerals: int, gas: int):
        """자원 예약 해제"""
        async with self._lock:
            self._reserved_minerals -= minerals
            self._reserved_gas -= gas
```

**사용 예시**:
```python
# upgrade_manager.py
if await self.bot.resource_manager.try_reserve(200, 100, "UpgradeManager"):
    # 예약 성공 - 업그레이드 시작
    await self.start_upgrade(UpgradeId.METABOLICBOOST)
else:
    # 예약 실패 - 다음 프레임 재시도
    return
```

**우선순위**: 🟡 MEDIUM (안정성 개선, 드물게 발생)

</details>

---

## 🟢 LOW Priority Issues

### ✅ Issue #5: 코드 중복 - Position 계산 — Resolved (수정일: 2026-07-18)

`wicked_zerg_challenger/utils/position_utils.py`에 `get_center_position()` /
`get_weighted_center()` 유틸이 이미 존재했으나 `battle_preparation_system.py`의
`_find_enemy_clusters()`에는 여전히 인라인 중복 계산이 남아있어 이번 점검에서
`get_center_position()` 호출로 교체. 나머지 위치 계산은 대부분 유틸을 사용 중.

<details><summary>원래 문제 설명 (참고용)</summary>

**위치**: 여러 파일에서 중복

**문제**:
```python
# combat_manager.py
center_x = sum(u.position.x for u in units) / len(units)
center_y = sum(u.position.y for u in units) / len(units)

# rally_point.py
center_x = sum(u.position.x for u in units) / len(units)
center_y = sum(u.position.y for u in units) / len(units)

# harassment_coord.py
center_x = sum(u.position.x for u in units) / len(units)
center_y = sum(u.position.y for u in units) / len(units)

# ★ 동일한 로직 반복 ★
```

**해결 방법**:
```python
# utils/position_utils.py (새 파일)

from typing import List
from sc2.position import Point2
from sc2.unit import Unit

def get_center_position(units: List[Unit]) -> Point2:
    """
    유닛들의 중심 위치 계산

    Args:
        units: 유닛 리스트

    Returns:
        중심 Point2
    """
    if not units:
        return Point2((0, 0))

    center_x = sum(u.position.x for u in units) / len(units)
    center_y = sum(u.position.y for u in units) / len(units)

    return Point2((center_x, center_y))

def get_weighted_center(units: List[Unit], weight_by_health: bool = False) -> Point2:
    """
    가중 중심 위치 (체력 가중치 가능)
    """
    if not units:
        return Point2((0, 0))

    if weight_by_health:
        total_health = sum(u.health for u in units)
        center_x = sum(u.position.x * u.health for u in units) / total_health
        center_y = sum(u.position.y * u.health for u in units) / total_health
    else:
        center_x = sum(u.position.x for u in units) / len(units)
        center_y = sum(u.position.y for u in units) / len(units)

    return Point2((center_x, center_y))
```

**사용 예시**:
```python
# combat_manager.py
from utils.position_utils import get_center_position

center = get_center_position(army_units)
```

**우선순위**: 🟢 LOW (코드 품질 개선)

</details>

---

### 🟡 Issue #6: 매직 넘버 (Magic Numbers) — 부분 진행 중

**진행 상황 (2026-07-18 확인)**: `wicked_zerg_challenger/utils/game_constants.py`(241줄)와
`wicked_zerg_challenger/config/constants.py`가 이미 존재하며 THRESHOLD/SECOND/MINUTE류 상수를
다수 정의하고 있음. 다만 개별 매니저 파일 곳곳에 여전히 인라인 매직 넘버가 남아있어 완전히
해결된 상태는 아님 — 점진적 마이그레이션 대상으로 유지.

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
| 🟢 LOW | #6 매직 넘버 (부분 진행 중) | 낮음 | 쉬움 |
| 🟢 LOW | N5 bare except 정리 (잔여 다수) | 낮음 | 쉬움 |

(Issue #1, #2, #3, #4, #5, N1-N4, N7-N9 → ✅ Resolved 섹션 참조)

---

## 🎯 권장 수정 순서

### 1단계: 완료 (✅)
~~1. Queen Inject 쿨다운 수정 (25 → 29)~~ — 코드 반영 완료
~~2. 누락된 업그레이드 추가~~ — 코드 반영 완료
~~3. Transfusion 우선순위 시스템 구현~~ — 코드 반영 완료 (`queen_transfusion_manager.py`)
~~4. Resource Reservation 동기화~~ — 코드 반영 완료 (`core/resource_manager.py`)
~~5. Position Utils 유틸리티 함수 분리~~ — 유틸 존재 + 마지막 잔여 호출부(`battle_preparation_system.py`) 정리 완료
~~N1-N4. 중복 메서드 정의(F811)~~ — PR #218에서 해결 확인
~~N7. 비동기 테스트 미실행(vacuous pass) 버그~~ — `IsolatedAsyncioTestCase`로 전환하여 해결
~~N8. `_get_counter_unit` 테스트-구현 시그니처 불일치~~ — 테스트 재작성으로 해결
~~N9. late-game Mutalisk 생산 누락~~ — 우선순위 분기 추가 + 회귀 테스트로 해결

### 2단계: 잔여 (미진행)
6. Constants 정리 (매직 넘버 마이그레이션 계속 진행)
7. bare `except Exception:` 정리 (N5, ≈455건 잔여)

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

### 현재 상태
- ✅ **치명적 통합 문제**: 완전히 해결됨
- ✅ **모든 단위 테스트**: 통과 (663/663, `wicked_zerg_challenger/tests/`)
- ✅ **기본 기능**: 정상 작동
- ✅ **비동기 테스트 실행 무결성**: 확인 완료 (N7 수정 후 전수 재검증)

### 위의 이슈들은
- 남은 항목(#6, N5)은 **선택적 개선 사항**
- 즉시 수정 불필요
- 점진적 개선 권장

---

**검토 완료일**: 2026-07-18
**상태**: 자동 점검 사이클 — 테스트 실행 → 정적 분석 → 코드 대조 검증 → 수정/커밋 반복 진행 중
