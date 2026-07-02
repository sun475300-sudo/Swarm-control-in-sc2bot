# 🔍 Remaining Issues - 추가 검토 결과

## 📋 개요

통합 문제 해결 후 발견된 추가 개선 사항들입니다.

**Last refreshed:** 2026-07-02 (자동 점검 사이클 — N1~N4 재검증 결과 이미 해결됨 확인; 신규 버그 3건 발견/수정)

---

## ✅ 신규 발견 & 해결 (2026-07-02 자동 점검 사이클)

`tests/` + `wicked_zerg_challenger/tests/` 전체 실행(1163 tests) 후 발견.

| ID | 설명 | 우선순위 | 상태 |
|----|------|---------|------|
| A1 | `tests/test_combat_phase_fsm.py`: `asyncio.get_event_loop().run_until_complete()` 사용으로 전체 스위트 실행 시 12개 테스트가 "no current event loop" 오류로 실패 (단독 실행 시엔 통과 — 테스트 격리 버그). `asyncio.run()`으로 교체하여 해결. | 🟠 HIGH | ✅ resolved |
| A2 | `wicked_zerg_challenger/tests/test_production_resilience.py`, `test_opponent_modeling.py`: `unittest.TestCase`에 `async def test_*` 메서드를 정의 — 표준 `unittest.TestCase`는 async 테스트 본문을 실행(await)하지 않으므로 코루틴 객체가 생성만 되고 어서션이 **한 번도 실행되지 않은 채 항상 PASS** 처리되던 심각한 버그(총 12개 테스트 무효화, `test_production_resilience.py` 27개 + `test_opponent_modeling.py`(TestOpponentModeling 클래스) 다수). `unittest.IsolatedAsyncioTestCase`로 교체하여 실제 실행되도록 수정. | 🔴 CRITICAL | ✅ resolved |
| A3 | A2를 고치자 실제로 숨어있던 버그 노출: `test_production_resilience.py`의 3개 counter-unit 테스트가 `_get_counter_unit(race_str)` 형태의 stale 시그니처로 호출 중이었음. 실제 구현은 `_get_counter_unit(enemy_units, has_roach_warren, has_hydra_den, has_spire)` (동기 함수, race 문자열 인자 없음). 테스트를 현재 시그니처에 맞게 재작성. | 🟠 HIGH | ✅ resolved |
| A4 | `tests/test_economy_manager.py::test_no_overlord_when_supply_sufficient` / `test_no_drone_when_workers_sufficient`: `call_count_before = bot.do.call_count`를 캡처만 하고 실제로 비교하지 않은 채 `assert True`로 끝남 — 오버로드/드론이 실제로 몇 번 생산되든 항상 PASS. `bot.do.call_count == call_count_before`로 실제 비교하도록 수정. | 🟠 HIGH | ✅ resolved |
| A5 | `wicked_zerg_challenger/tests/test_production_resilience.py` 파일 끝의 `if __name__ == "__main__":` 블록이 A2 수정 전 시절 유물로 `asyncio.get_event_loop().run_until_complete()`를 수동 재구현 — pytest 실행 경로에서는 도달 불가능하지만 방금 고친 버그 패턴을 그대로 복제하고 있어 혼란/재발 소지. `unittest.main()`으로 교체(단순화). | 🟢 LOW | ✅ resolved |

리포지토리 전체에서 동일 버그 클래스(`unittest.TestCase` + `async def test_*`) 재스캔 완료 — 추가 발견 없음.

### 🔜 다음 사이클 백로그 (자동 스캔으로 발견, 이번 사이클 미착수)

우선순위 순. 실제 프로덕션 동작에 영향을 줄 수 있는 항목(B1, B2)은 별도 PR + 리뷰 권장.

| ID | 설명 | 우선순위 | 비고 |
|----|------|---------|------|
| B1 | `wicked_zerg_challenger/combat_manager.py:283-287`의 `on_step` 전체가 하나의 `except Exception as e:`로 감싸여 있고, `iteration % 50 == 0`일 때만 로그 — 리팩터링 등으로 생긴 지속적 버그(예: AttributeError)가 있어도 프레임의 ~98%에서 조용히 무시되고 재발생/카운트되지 않음. 전투 판단 로직이 부분적으로 죽어도 알아채기 어려움. | 🟠 HIGH | 동작 변경 위험 — 별도 PR 권장, 에러율 메트릭 추가 고려 |
| B2 | `wicked_zerg_challenger/queen_manager.py:125-197`도 동일 패턴 — 퀸 `on_step`(inject/transfusion/creep/defense) 전체가 bare except + 50프레임마다 로그. | 🟠 HIGH | B1과 동일 처방 권장 |
| B3 | 다수 테스트 파일에 `assert True` / "no exception raised"만 확인하는 타우톨로지 어서션 존재: `tests/test_economy_manager.py`(7곳 잔여), `wicked_zerg_challenger/tests/test_production_resilience.py`(12곳), `tests/test_combat_manager.py`(3곳), `tests/test_expansion_manager.py`(1곳), `tests/test_phase10_improvements.py`(1곳). 크래시만 잡고 로직 회귀(잘못된 유닛 생산, 잘못된 타겟 선정 등)는 절대 못 잡음. A4와 동일 클래스의 버그 — 실제 상태 비교로 하나씩 교체 필요. | 🟡 MED | 건별로 실제 동작을 확인하며 재작성 필요 (일괄 자동화 불가) |
| B4 | `tests/test_combat_manager.py::test_rally_point_calculation`이 `hasattr(combat, "_update_rally_point")` 가드 뒤에 있어 메서드가 리네임/삭제되면 실패 대신 `pytest.skip()`으로 조용히 통과 — 회귀 감지 불가. | 🟡 MED | 가드 제거하고 직접 호출하도록 변경 |
| B5 | `wicked_zerg_challenger/tests/test_active_scouting_system.py:58-60,167`의 `patch(..., create=True)` — 패치 대상 이름 오타/드리프트 시 `AttributeError` 대신 가짜 속성을 조용히 생성. | 🟢 LOW | `create=True` 제거 가능한지 확인 |

---

## ✅ N1~N4 재검증 결과 (2026-07-02)

2026-04-27에 open으로 기록되었던 N1~N4는 이후 PR #218(`refactor: delete shadowed duplicate methods that silently disabled features` 등)에서 이미 해결된 것으로 코드 확인됨. 문서가 stale했음 — 별도 작업 없이 닫음.

| ID | 설명 | 검증 결과 |
|----|------|---------|
| N1 | `OpponentModeling.on_step` 중복 정의 (F811) | `opponent_modeling.py`에 `on_step` 단일 정의만 존재 (line 341) — resolved |
| N2 | `EconomyManager._prevent_resource_banking` / `_reduce_gas_workers` 재정의 | 각 메서드 단일 정의만 존재 — resolved |
| N3 | `combat_manager._find_harass_target` 재정의 | 단일 정의만 존재 (line 4992) — resolved |
| N4 | `production_resilience.build_terran_counters` 재정의 | 단일 정의만 존재 (line 1961) — resolved |
| N5 | bare `except Exception:` 다수 | 잔여 다수, 점진적 개선 대상으로 유지 | 
| N6 | F841 unused local variables (`wicked_zerg_challenger/visuals/*`) | flake8 재확인: 130건, 전량 presentation 코드 — 영향 작아 유지 |

검증 명령: `flake8 wicked_zerg_challenger --select=F811,F821,F823,F822` → 0 hits.

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

### Issue #3: Transfusion 우선순위 개선 필요

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

---

### Issue #4: Resource Reservation Race Condition

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

---

## 🟢 LOW Priority Issues

### Issue #5: 코드 중복 - Position 계산

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

---

## 📊 이슈 우선순위 요약 (open만)

| 우선순위 | 이슈 | 영향도 | 난이도 |
|---------|------|--------|--------|
| 🟡 MEDIUM | #3 Transfusion 우선순위 | 중간 | 중간 |
| 🟡 MEDIUM | #4 Resource Race Condition | 낮음 | 중간 |
| 🟢 LOW | #5 코드 중복 제거 | 낮음 | 쉬움 |
| 🟢 LOW | #6 매직 넘버 | 낮음 | 쉬움 |

(Issue #1, #2 → ✅ Resolved 섹션 참조)

---

## 🎯 권장 수정 순서

### 1단계: 완료 (✅)
~~1. Queen Inject 쿨다운 수정 (25 → 29)~~ — 코드 반영 완료, 본 문서 ✅ Resolved 섹션 참조
~~2. 누락된 업그레이드 추가~~ — 코드 반영 완료, 본 문서 ✅ Resolved 섹션 참조

### 2단계: 로직 개선 (30분, 미진행)
3. Transfusion 우선순위 시스템 구현

### 3단계: 구조 개선 (1시간, 미진행)
4. Resource Reservation 동기화
5. Position Utils 유틸리티 함수 분리
6. Constants 정리

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
- ✅ **모든 단위 테스트**: 통과 (16/16)
- ✅ **기본 기능**: 정상 작동

### 위의 이슈들은
- 모두 **선택적 개선 사항**
- 즉시 수정 불필요
- 점진적 개선 권장

---

**검토 완료일**: 2026-01-29
**상태**: 추가 개선 사항 문서화 완료
