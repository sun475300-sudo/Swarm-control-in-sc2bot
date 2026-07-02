# 🔍 Remaining Issues - 추가 검토 결과

## 📋 개요

통합 문제 해결 후 발견된 추가 개선 사항들입니다.

**Last refreshed:** 2026-07-02 (자동 점검 사이클 — N1~N4, Issue #3, Issue #4 모두 코드에 이미 반영된 상태로 재확인 후 종결. 새 항목 3건 발견/수정.)

---

## ✅ N1~N4 재검증 결과 (2026-07-02): 이미 해결됨

이전에 open으로 표시됐던 N1~N4는 `grep -n`으로 재확인한 결과 모두 단일 정의만 남아있어
**이미 해결된 상태**입니다 (PR #218 "stabilize SC2 bot test suite" 계열 커밋에서 정리된 것으로 보임).
문서가 stale했던 것으로, 별도 작업 없이 닫습니다.

| ID | 설명 | 재검증 결과 |
|----|------|------|
| N1 | `OpponentModeling.on_step` 중복 정의 | `opponent_modeling.py`에 `on_step` 정의 1건만 존재 — 해결됨 |
| N2 | `EconomyManager._prevent_resource_banking` / `_reduce_gas_workers` 재정의 | 각 1건만 존재 — 해결됨 |
| N3 | `combat_manager._find_harass_target` 재정의 | 1건만 존재 — 해결됨 |
| N4 | `production_resilience.build_terran_counters` 재정의 | 1건만 존재 — 해결됨 |
| N5 | bare `except Exception:` 다수 | 🟢 LOW, 잔여 다수 — 여전히 open (아래 참고 항목 참조) |
| N6 | F841 unused local variables (visuals/make_pptx 등) | 🟢 LOW — 여전히 open, presentation 코드라 영향 작음 |

`flake8 wicked_zerg_challenger --select=F811,F821` 결과: 0건 (2026-07-02 기준).

---

## 🆕 이번 세션 발견 및 수정 (2026-07-02)

| ID | 설명 | 상태 |
|----|------|------|
| S1 | CI: `ci.yml`의 "Python 린트 & 테스트" job이 `PROTOCOL_BUFFERS_PYTHON_IMPLEMENTATION=python` 없이 pytest 실행 → sc2 import 시 protobuf 에러로 14개 테스트 파일 collection 실패, main CI 전체(Docker 빌드 등) 차단 | ✅ Fixed |
| S2 | `tests/test_combat_phase_fsm.py`가 동기 테스트 안에서 `asyncio.get_event_loop().run_until_complete()` 사용 → pytest-asyncio auto 모드가 이전 비동기 테스트 뒤에 루프를 정리해버려서 실행 순서에 따라 12개 테스트가 실패 | ✅ Fixed (asyncio.run()으로 교체) |
| S3 | `test_production_resilience.py`, `test_opponent_modeling.py`의 테스트 클래스가 일반 `unittest.TestCase`인데 `async def test_*` 메서드를 갖고 있어서, 코루틴이 await되지 않고 버려짐 → 18개 테스트가 실제로는 전혀 실행되지 않은 채 항상 "통과"로 표시됨 | ✅ Fixed (`unittest.IsolatedAsyncioTestCase`로 전환, 실제 실행되자 `_get_counter_unit()` 시그니처가 바뀐 걸 반영 못한 stale 테스트 3건이 드러나 같이 수정) |
| S4 | `sc2bot-ci.yml`의 "Lint & Type Check" job(black/isort 강제)이 main에서 장기간 실패 중 — 65개 파일이 black 미준수 (`wicked_zerg_challenger/strategy_manager.py`, `visuals/*` 등). 이번 PR과 무관한 기존 문제 | 🟡 open — 전체 리포 대상 대규모 리포맷이라 사용자 확인 후 별도 PR로 진행 예정 |

검증: `pytest tests/` 502 passed/14 skipped/0 failed, `pytest wicked_zerg_challenger/tests/` 661 passed/0 failed (수정 전: root suite 20 failed).

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

## ✅ Issue #3, #4 재검증 결과 (2026-07-02): 이미 해결됨

아래 두 항목도 코드에 이미 구현되어 있는 것을 확인했습니다 (문서가 stale했음).

- **Issue #3 (Transfusion 우선순위)**: `wicked_zerg_challenger/economy/queen_transfusion_manager.py`에
  `HEAL_PRIORITY` 딕셔너리와 우선순위 기반 타겟 선택 로직이 이미 구현되어 있음 (라인 26, 134, 166-169).
- **Issue #4 (Resource Reservation Race Condition)**: `wicked_zerg_challenger/core/resource_manager.py`에
  `asyncio.Lock()` 기반 `try_reserve()` / `release()`가 이미 구현되어 있음 (라인 36, 50, 62).

원안(구현 제안 코드)은 과거 참고용으로 아래에 남겨둔다.

### Issue #3 (원안, 참고용): Transfusion 우선순위 개선 필요

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

### Issue #4 (원안, 참고용): Resource Reservation Race Condition

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

## 📊 이슈 우선순위 요약 (open만, 2026-07-02 재검증)

| 우선순위 | 이슈 | 영향도 | 난이도 |
|---------|------|--------|--------|
| 🟡 MED | N5 bare except 잔여 다수 | 낮음 | 중간 (범위 큼) |
| 🟢 LOW | #5 코드 중복 제거 (position_utils) | 낮음 | 쉬움 |
| 🟢 LOW | #6 매직 넘버 정리 | 낮음 | 쉬움 |
| 🟢 LOW | N6 F841 unused vars (visuals) | 낮음 | 쉬움 |
| 🟡 개방 | S4 전체 리포 black 리포맷 (65 파일) | CI 신호 차단 | 큼 (범위 확인 필요) |

(Issue #1~#4, N1~N4 → ✅ 모두 코드에 이미 반영 확인, 위 섹션 참조)

---

## 🎯 권장 수정 순서

### 1단계: 완료 (✅)
~~1. Queen Inject 쿨다운 수정 (25 → 29)~~ — 완료
~~2. 누락된 업그레이드 추가~~ — 완료
~~3. Transfusion 우선순위 시스템~~ — 완료 (`queen_transfusion_manager.py`)
~~4. Resource Reservation 동기화~~ — 완료 (`core/resource_manager.py`)
~~5. N1~N4 중복 정의 제거~~ — 완료
~~6. CI protobuf env, 테스트 이벤트루프 순서의존성, silently-skipped async 테스트 18건~~ — 완료 (2026-07-02, PR #234)

### 2단계: 남은 작업 (미진행)
7. bare except 잔여 정리 (N5)
8. Position Utils 유틸리티 함수 분리 (#5)
9. Constants 정리 (#6)
10. 전체 리포 black/isort 리포맷 — 사용자 확인 후 진행 (S4, 범위가 SC2 봇 외 다른 서브시스템까지 포함)

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

### 현재 상태 (2026-07-02 재검증)
- ✅ **치명적 통합 문제**: 완전히 해결됨
- ✅ **`tests/` (repo 루트)**: 502 passed / 14 skipped / 0 failed
- ✅ **`wicked_zerg_challenger/tests/`**: 661 passed / 0 failed
- ✅ **기본 기능**: 정상 작동
- 🟡 **`sc2bot-ci.yml`의 Lint & Type Check job**: black 미준수 65개 파일로 인해 실패 중 (S4 참조, 이 PR과 무관한 기존 문제)

주의: 이 문서(REMAINING_ISSUES.md)와 ROADMAP.md/PLAN-NIGHTLY.md의 "현재 상태" 수치가 실제 코드와 어긋나 있던
사례가 여러 건 있었음 (N1~N4, Issue #3/#4가 실제로는 이미 해결된 상태인데 open으로 표시됨). 다음 점검 시
반드시 `grep`/`pytest` 등으로 실측 후 문서를 갱신할 것 — 문서 상 "open"이라고 실제로 열려있다고 가정하지 말 것.

### 위의 이슈들은
- 모두 **선택적 개선 사항**
- 즉시 수정 불필요
- 점진적 개선 권장

---

**검토 완료일**: 2026-07-02
**상태**: 자동 점검 사이클 — 실측 재검증 및 CI/테스트 버그 3건 수정 완료 (PR #234)
