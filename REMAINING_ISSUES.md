# 🔍 Remaining Issues - 추가 검토 결과

## 📋 개요

통합 문제 해결 후 발견된 추가 개선 사항들입니다.

**Last refreshed:** 2026-07-10 (자동 점검 사이클 — 아래 "2026-07-10 검증 결과" 참조. Issue #1, #2 → Resolved; Issue #3~#6, N1~N4 → 코드 재검증 결과 모두 이미 구현 완료된 것으로 확인, Resolved로 이동)

---

## ✅ 2026-07-10 검증 결과 (전수 재검증)

`python3 -m pytest tests/ wicked_zerg_challenger/tests/` 전체 그린 상태에서 아래 문서 항목을 코드와 대조 재검증함. **N1~N4, Issue #3~#6은 모두 이전 세션에서 이미 구현되어 있었고, 이 문서만 갱신되지 않은 상태(stale)였음** — 별도 코드 변경 불필요, 문서만 정정.

| ID | 검증 결과 |
|----|-----------|
| N1 | `opponent_modeling.py`에 `on_step` 정의 1개뿐 (line 341). 중복 없음. |
| N2 | `economy_manager.py`에 `_prevent_resource_banking`/`_reduce_gas_workers` 정의 각 1개뿐. 중복 없음. |
| N3 | `combat_manager.py`에 `_find_harass_target` 정의 1개뿐 (line 4992). 중복 없음. |
| N4 | 해당 로직은 `local_training/production_resilience.py:1961 build_terran_counters` 1곳에만 존재 (구 경로 `production_resilience.py`는 더 이상 루트에 없음). 중복 없음. |
| N5 | 여전히 다수 잔존 (점진 개선 대상, 우선순위 낮음). |
| N6 | 여전히 다수 잔존 (`wicked_zerg_challenger` 전역 F841 130건 — visuals 외 combat/economy 파일에도 분포). 점진 개선 대상. |
| Issue #3 | `queen_manager.py:711 _transfuse_injured_units`에 CreepyBot 스타일 우선순위 테이블(퀸>브루드로드>커럽터>스파인>오버시어>...)로 이미 구현됨. 제안보다 더 정교함. |
| Issue #4 | `core/resource_manager.py`에 `asyncio.Lock` 기반 `try_reserve`/`release`/`release_partial` 이미 구현됨. |
| Issue #5 | `utils/position_utils.py`에 `get_center_position`/`get_weighted_center` 등 이미 구현됨. |
| Issue #6 | `utils/game_constants.py` 등 상수 클래스 존재. 매직넘버는 일부 파일에 잔존(점진 개선 대상). |

### 이번 사이클에서 실제로 발견/수정한 버그 (신규)

| 항목 | 파일 | 내용 |
|------|------|------|
| ✅ 수정 | `tests/test_combat_phase_fsm.py` | `asyncio.get_event_loop().run_until_complete(...)` 5곳이 다른 테스트 뒤에 실행되면 "no current event loop" 로 실패 (테스트 순서 의존적 flaky). `asyncio.run(...)`으로 교체하여 격리. |
| ✅ 수정 | `wicked_zerg_challenger/tests/test_production_resilience.py`, `test_opponent_modeling.py` | `class TestX(unittest.TestCase)`에 `async def test_...` 메서드가 있어 코루틴이 **실행조차 되지 않고** 항상 "통과"하던 18개 테스트 발견 (`RuntimeWarning: coroutine was never awaited`). `unittest.IsolatedAsyncioTestCase`로 교체해 실제로 실행되게 수정 — 그 결과 `_get_counter_unit` 관련 테스트 3개가 실제로는 이미 변경된 시그니처(`enemy_units, has_roach_warren, has_hydra_den, has_spire`)와 맞지 않는 stale 테스트였음이 드러나 함께 수정. |
| ✅ 수정 | 루트 `pytest/` 디렉토리 | 실제 pytest 패키지와 이름이 충돌해 `python -m pytest`가 로컬에서 깨지는 문제(`run_combat_tests.bat`, `PUSH_FIX_TO_MAIN.bat` 등에서 사용) — `python_pytest_example/`로 이름 변경. |
| ✅ 수정 | `requirements.txt` | `cryptography>=41.0.0`가 `cffi`를 암묵적으로 필요로 함 (미설치 시 `test_crypto_trading.py`/`test_security.py` 8건 실패). `cffi>=1.15.0` 명시 추가. |

### 신규 발견, 아직 미수정 (다음 사이클 후보)

| ID | 설명 | 우선순위 |
|----|------|---------|
| N7 | `combat_manager.py`의 `manage_combat`/`_should_skip_combat_frame` (Sprint 4.5 전투 프레임 스킵, `tests/test_sprint4_combat_micro.py`로 테스트까지 있음)이 실제 on_step 경로(`bot_step_integration.py`의 `_safe_manager_step(self.bot.combat, ...)`)에서 전혀 호출되지 않는 죽은 코드. 대신 `logic_optimizer.py`가 "Combat" 시스템을 `interval=1`(매 프레임)로 하드코딩 관리 중이라 실질적 영향은 제한적이지만, 테스트된 기능이 실전에서 비활성 상태인 점은 정리 필요. 실제 게임(SC2 클라이언트) 없이는 프레임 스킵 동작 변경의 안전성을 검증할 수 없어 이번 사이클에서는 코드 변경 보류. |

---

## 🆕 신규 발견 (PR #44, 2026-04-27) — 재검증 결과 모두 Resolved (위 표 참조)

<details>
<summary>원본 기록 (참고용, 접기)</summary>

| ID | 설명 | 우선순위 | 상태 |
|----|------|---------|------|
| N1 | `OpponentModeling.on_step` 중복 정의 (line 341 vs 765 — F811) | 🟠 HIGH | ✅ Resolved (2026-07-10 재검증) |
| N2 | `EconomyManager._prevent_resource_banking` / `_reduce_gas_workers` 재정의 (F811) | 🟡 MED | ✅ Resolved (2026-07-10 재검증) |
| N3 | `combat_manager._find_harass_target` 재정의 (line 2377 vs 4278) | 🟡 MED | ✅ Resolved (2026-07-10 재검증) |
| N4 | `production_resilience.build_terran_counters` 재정의 (1369 vs 1866) | 🟡 MED | ✅ Resolved (2026-07-10 재검증) |
| N5 | bare `except Exception:` 다수 (≈360+) — 이번 PR에서 12건 처리, 잔여 다수 | 🟢 LOW | partial |
| N6 | F841 unused local variables (visuals/make_pptx 등) | 🟢 LOW | open (전역 130건, 점진 개선) |

</details>

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

## 🟡 MEDIUM Priority Issues (✅ Resolved — 2026-07-10 재검증, 아래는 원래 제안 기록)

### Issue #3: Transfusion 우선순위 개선 필요 — ✅ Resolved (`queen_manager.py:711 _transfuse_injured_units`)

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

### Issue #4: Resource Reservation Race Condition — ✅ Resolved (`core/resource_manager.py` — `asyncio.Lock` + `try_reserve`/`release`)

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

## 🟢 LOW Priority Issues (#5 ✅ Resolved, #6 부분 완료 — 2026-07-10 재검증)

### Issue #5: 코드 중복 - Position 계산 — ✅ Resolved (`utils/position_utils.py`)

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

### Issue #6: 매직 넘버 (Magic Numbers) — 부분 완료 (`utils/game_constants.py` 존재, 잔존분 점진 개선 대상)

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

## 📊 이슈 우선순위 요약

**2026-07-10 갱신: #3~#6 모두 코드에 이미 구현되어 있음이 확인되어 Resolved.** 아래는 과거 기록.

| 우선순위 | 이슈 | 상태 |
|---------|------|------|
| 🟡 MEDIUM | #3 Transfusion 우선순위 | ✅ Resolved (`queen_manager.py:711`) |
| 🟡 MEDIUM | #4 Resource Race Condition | ✅ Resolved (`core/resource_manager.py`) |
| 🟢 LOW | #5 코드 중복 제거 | ✅ Resolved (`utils/position_utils.py`) |
| 🟢 LOW | #6 매직 넘버 | 부분 완료 (`utils/game_constants.py` 존재, 잔존분은 점진 개선) |

(Issue #1, #2 → ✅ Resolved 섹션 참조. N1~N7은 상단 "2026-07-10 검증 결과" 참조)

---

## 🎯 권장 수정 순서

### 완료 (✅)
- Queen Inject 쿨다운 수정 (25 → 29)
- 누락된 업그레이드 추가
- Transfusion 우선순위 시스템
- Resource Reservation 동기화
- Position Utils 유틸리티 함수 분리
- N1~N4 (중복 정의 의심) — 재검증 결과 중복 없음

### 다음 후보 (미진행)
- N5/N6: bare except / F841 잔존분 점진 정리
- N7: Sprint 4.5 전투 프레임 스킵 죽은 코드 정리 (실전 게임 검증 필요, 상단 참조)
- Constants 정리 (매직넘버 잔존분)

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
