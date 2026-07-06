# 🔍 Remaining Issues - 추가 검토 결과

## 📋 개요

통합 문제 해결 후 발견된 추가 개선 사항들입니다.

**Last refreshed:** 2026-07-06 (자동 점검 사이클 — 테스트 실행 → 실코드 검증 → 수정 → 커밋/푸시)

---

## 🆕 신규 발견 (2026-07-06 자동 점검 사이클)

`tests/`(502) + `wicked_zerg_challenger/tests/`(661) 전체 실행, ROADMAP.md/PLAN-NIGHTLY.md 전 항목을 실제 코드와 대조 검증한 결과.

| ID | 설명 | 우선순위 | 상태 |
|----|------|---------|------|
| N7 | `tests/test_combat_phase_fsm.py`가 `asyncio.get_event_loop().run_until_complete()`(deprecated) 사용 — 최신 Python에서 "no current event loop" RuntimeError로 12/23 테스트 실패 | 🔴 HIGH | ✅ **resolved** — `asyncio.run()`으로 교체 |
| N8 | **CI 맹점**: `.github/workflows/ci.yml`의 "pytest 실행 (전체)" 단계가 `pytest tests/ --co`(수집만, 미실행)였음 — 루트 `tests/` 502개 테스트가 CI에서 실제로 한 번도 실행되지 않아 N7 같은 회귀를 못 잡음 | 🔴 HIGH | ✅ **resolved** — `--co` 제거, `requirements-dev.txt` 설치 단계 추가 |
| N9 | `RLAgent.save_experience_data`(atomic save)가 `os.remove(path)` 후 `os.rename()` 방식 — rename이 중간에 실패(디스크 풀/인터럽트)하면 기존에 저장된 정상 데이터까지 삭제된 채로 남는 데이터 유실 버그 (PLAN-NIGHTLY P2.4) | 🟠 HIGH | ✅ **resolved** — `os.replace()`(원자적 덮어쓰기)로 교체, 회귀 테스트 3건 추가 (`wicked_zerg_challenger/tests/test_sprint6_rl_pipeline.py::TestSaveExperienceDataGuard`) |
| N10 | `utils/distance_cache.py` 캐시가 `combat_manager.py`/`economy_manager.py`에 부분 도입되었으나, 두 파일에 남은 `.distance_to(` 원시 호출이 각각 60건/24건 — 캐시 적용률 10% 미만 | 🟡 MED | open |
| N11 | `utils/game_constants.py`(`GameFrequencies`/`EconomyConstants`)가 4개 파일에만 채택, 나머지 67개 파일은 여전히 `% 22`, `% 110` 등 매직넘버 사용 | 🟢 LOW | open |
| N12 | PLAN-NIGHTLY P2.2 (N-replay 벤치마크 러너: win-rate/APM/supply 리포트)가 실제로 존재하지 않음 — 관련 스크립트 전무 확인 | 🟡 MED | open |
| N13 | PLAN-NIGHTLY P2.3 (`config/build_orders.yaml`로 하드코딩 상수 이전)가 실제로 존재하지 않음 — `config/`에 해당 파일 없음 확인 | 🟢 LOW | open |

### ✅ N1-N4 재검증 (2026-04-27 발견 → 2026-07-06 확인)

`flake8 wicked_zerg_challenger --select=F811` 결과 0건 — N1(`OpponentModeling.on_step` 중복), N2(`EconomyManager` 재정의), N3(`combat_manager._find_harass_target` 재정의), N4(`production_resilience.build_terran_counters` 재정의) 모두 이후 커밋(`refactor: delete shadowed duplicate methods`, `fix: 6 F821 NameError bugs`)에서 이미 해결됨. 문서만 stale했음 — 별도 작업 없이 닫음.

N5(bare except)는 `wicked_zerg_challenger/` 전역에 여전히 다수 잔존(우선순위 낮음, 점진 처리). N6(F841)은 130건으로 집계됨(대부분 presentation/visuals 코드, 영향 작음) — 계속 open 유지.

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

## 🟡 MEDIUM Priority Issues

> **2026-07-06 검증 결과: Issue #3, #4 모두 이미 구현 완료 확인됨.** 아래 제안 코드는
> 히스토리 참고용으로 남겨두며, 실제 구현 위치는 각 항목 상단에 명시.

### ✅ Issue #3: Transfusion 우선순위 개선 — 구현 완료 확인 (2026-07-06)

**구현 위치**: `wicked_zerg_challenger/economy/queen_transfusion_manager.py:26-39` (`HEAL_PRIORITY`),
`:43-56` (`CANNOT_HEAL`), `:169` (우선순위 정렬) — 아래 제안안의 상위 호환(더 많은 유닛 포함).
회귀 테스트: `tests/test_queen_transfusion.py`, `tests/test_queen_transfusion_manager.py`.

<details><summary>원본 제안 (참고용, 이미 반영됨)</summary>

### Issue #3: Transfusion 우선순위 개선 필요 (원본 제안)

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

### ✅ Issue #4: Resource Reservation Race Condition — 구현 완료 확인 (2026-07-06)

**구현 위치**: `wicked_zerg_challenger/core/resource_manager.py:36` (`asyncio.Lock()`),
`:50-96` (`try_reserve`, 원자적), `:98-116` (`release`) — 아래 제안안과 거의 동일하게 구현됨.
`defense_coordinator.py`, `economy_manager.py`에서 `self.bot.resource_manager`로 실사용 중.

<details><summary>원본 제안 (참고용, 이미 반영됨)</summary>

### Issue #4: Resource Reservation Race Condition (원본 제안)

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

## 📊 이슈 우선순위 요약 (open만, 2026-07-06 기준)

| 우선순위 | 이슈 | 영향도 | 난이도 |
|---------|------|--------|--------|
| 🟡 MED | N10 DistanceCache 적용률 &lt;10% (combat/economy manager 84건 미전환) | 중간 (성능) | 중간 |
| 🟡 MED | N12 PLAN-NIGHTLY P2.2 벤치마크 러너 부재 (N-replay win-rate/APM 리포트) | 중간 (검증 인프라) | 중간 |
| 🟢 LOW | N11 GameConstants 채택률 낮음 (67개 파일 매직넘버 잔존) | 낮음 (가독성) | 쉬움~중간 |
| 🟢 LOW | N13 PLAN-NIGHTLY P2.3 `config/build_orders.yaml` 미존재 | 낮음 (설정 유연성) | 중간 |
| 🟢 LOW | #5 코드 중복 제거 (position 계산 유틸) | 낮음 | 쉬움 |
| 🟢 LOW | #6 매직 넘버 (N11과 중복) | 낮음 | 쉬움 |
| 🟢 LOW | N5 bare `except Exception:` 잔존 (다수) | 낮음 | 점진적 |
| 🟢 LOW | N6 F841 미사용 지역변수 (130건, 대부분 presentation 코드) | 낮음 | 쉬움 |

(Issue #1~#4, N1~N4, N7~N9 → 모두 ✅ 해결 확인됨 — 위 각 섹션 참조)

---

## 🎯 다음 사이클 권장 작업 순서

1. **N12** — 벤치마크 러너 (`run_mass_test.py` 결과를 취합해 win-rate/APM/supply 리포트 생성) — 반복 회귀 감지에 직접 기여, 우선순위 상향 권장
2. **N10** — DistanceCache를 `combat_manager.py`/`economy_manager.py` 나머지 호출부에 확대 적용
3. **N13** — `config/build_orders.yaml` 도입 + 상위 20개 하드코딩 값 이전
4. **N11** — `GameConstants`/`GameFrequencies` 미채택 67개 파일 순차 정리
5. **N5/N6** — bare except / 미사용 변수 점진적 정리 (기능 영향 없음, 후순위)

---

## 📝 참고 사항 (2026-07-06 자동 점검 사이클 기준)

### 현재 상태
- ✅ 루트 `tests/`: 502 passed, 14 skipped, 0 failed
- ✅ `wicked_zerg_challenger/tests/`: 661 passed, 0 failed
- ✅ `flake8 --select=F811,F821`: 0건 (실제 실행 오류 유발 결함 없음)
- ✅ CI가 이제 루트 `tests/`를 실제로 실행함 (이전엔 `--co`로 수집만 하고 있었음 — N8)
- ✅ ROADMAP.md Sprint 1~8의 거의 모든 태스크가 실코드에 구현되어 있음을 file:line 단위로 재검증함 (문서가 실제보다 훨씬 stale했음)

### 이번 사이클에서 고친 것
- N7: 오래된 `asyncio.get_event_loop()` 패턴이 최신 Python에서 테스트 12건을 깨뜨리던 회귀
- N8: CI가 핵심 테스트를 collect만 하고 실행하지 않던 맹점
- N9: RL 에이전트 저장 로직의 rename 중단 시 데이터 유실 가능성

### 남은 이슈들은
- 모두 **성능/유지보수성 개선 사항** (게임 승률에 즉각 영향 없음)
- 다음 자동 점검 사이클에서 우선순위 순서대로 처리 예정

---

**검토 완료일**: 2026-07-06
**상태**: 자동 점검 사이클 반영 완료 — 다음 사이클에서 N10~N13 처리 예정
