# 🔍 Remaining Issues - 추가 검토 결과

## 📋 개요

통합 문제 해결 후 발견된 추가 개선 사항들입니다.

**Last refreshed:** 2026-07-13 (자동 점검 루프) — N1~N4, Issue #3, Issue #4는 이후 커밋(`e648ae4`, `fb0d61f` 등)에서
이미 해결된 것으로 코드 검증 완료. N5는 대부분(F811/F821/E722 0건), N6는 이번 세션에서 47건 자동 정리(잔여 83건).

## 🆕 신규 발견 (PR #44, 2026-04-27) — 검증 결과: 모두 해결됨

자동/수동 점검 사이클(테스트 → 코드 검사 → 개선 → 커밋/푸시 반복)에서 새로 식별된 항목.

| ID | 설명 | 우선순위 | 상태 |
|----|------|---------|------|
| N1 | `OpponentModeling.on_step` 중복 정의 (line 341 vs 765 — F811) | 🟠 HIGH | ✅ resolved — `opponent_modeling.py`에 `on_step` 단일 정의만 존재 확인 (2026-07-13) |
| N2 | `EconomyManager._prevent_resource_banking` / `_reduce_gas_workers` 재정의 (F811) | 🟡 MED | ✅ resolved — 각 메서드 단일 정의만 존재 확인 |
| N3 | `combat_manager._find_harass_target` 재정의 (line 2377 vs 4278) | 🟡 MED | ✅ resolved — 단일 정의만 존재 확인 |
| N4 | `production_resilience.build_terran_counters` 재정의 (1369 vs 1866) | 🟡 MED | ✅ resolved — 단일 정의만 존재 확인 |
| N5 | bare `except Exception:` 다수 (≈360+) — 이번 PR에서 12건 처리, 잔여 다수 | 🟢 LOW | partial — `ruff --select F811,F821,E722`는 0건. 미사용 `except ... as e` 변수 47건은 이번 세션에서 자동 정리 |
| N6 | F841 unused local variables (visuals/make_pptx 등) | 🟢 LOW | partial — 130건 중 47건 자동 수정 완료 (`ruff --fix`), 잔여 83건은 unsafe-fix 대상이라 수동 검토 필요 |

검증 근거: `git log`에서 N1~N4는 커밋 `e648ae4`("refactor: delete shadowed duplicate methods that silently disabled features")로,
관련 `NameError`류는 `fcf1004`로 이미 해결됨. 이 문서가 그 이후 갱신되지 않아 stale 상태였음.

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

## ✅ MEDIUM Priority Issues — 검증 결과: 해결됨 (2026-07-13)

### Issue #3: Transfusion 우선순위 개선 필요 — ✅ RESOLVED

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

**검증**: `queen_manager.py:711` `_transfuse_injured_units()`에 CreepyBot 스타일 우선순위 테이블
(Queen > Broodlord/Viper > Spine > Overseer > Ultra > Ravager > Roach > ... )이 이미 구현되어 있고,
체력 부족분(`health_max - health >= 125`) 조건과 치료 불가 유닛 제외까지 반영됨. 문서 제안보다 더 정교함.

---

### Issue #4: Resource Reservation Race Condition — ✅ RESOLVED

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

**검증**: `core/resource_manager.py`에 `asyncio.Lock` 기반 `try_reserve()`/`release()`가 문서 제안 그대로 구현되어 있고,
`defense_coordinator.py`, `economy_manager.py`에서 실제로 호출되어 사용 중임을 확인.

---

## 🟢 LOW Priority Issues (여전히 open — 이번 세션 부분 진행)

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

**진행 상황 (2026-07-13)**: 제안된 `utils/position_utils.py`는 이미 존재하며 `get_center_position`,
`get_weighted_center`, `get_closest_unit`, `get_bounding_box` 등 문서 제안보다 더 풍부한 API를 제공한다.
다만 테스트가 전혀 없었고(`tests/test_position_utils.py` 부재), 여전히 11개 이상의 파일
(`combat_manager.py`, `combat/combat_execution.py`, `combat/infestor_tactics.py`, `combat/micro_combat.py`,
`combat_phase_controller.py`, `micro_controller.py`, `battle_preparation_system.py`, `idle_unit_manager.py` 등)에서
동일한 계산이 인라인으로 중복되어 있어 유틸리티가 채택되지 않은 상태다.
이번 세션에서 `tests/test_position_utils.py`(19 케이스)를 추가해 회귀 안전망을 마련했다.
각 호출부는 반환 타입/빈 컬렉션 처리(`None` vs `Point2((0,0))`)가 미묘하게 달라 기계적 치환이 위험하므로,
호출부별로 개별 PR에서 동작 동등성을 확인하며 이관할 것을 권장한다 (다음 이터레이션 작업 항목).

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

## 📊 이슈 우선순위 요약 (2026-07-13 재검증)

| 우선순위 | 이슈 | 상태 | 영향도 | 난이도 |
|---------|------|------|--------|--------|
| 🟠 HIGH | N1 on_step 중복 정의 | ✅ resolved | - | - |
| 🟡 MED | N2-N4 메서드 중복 정의 | ✅ resolved | - | - |
| 🟡 MED | #3 Transfusion 우선순위 | ✅ resolved | - | - |
| 🟡 MED | #4 Resource Race Condition | ✅ resolved | - | - |
| 🟢 LOW | #5 코드 중복 제거 (position_utils 미채택 11곳) | open | 낮음 | 쉬움 (호출부별 개별 검증 필요) |
| 🟢 LOW | #6 매직 넘버 (Queen 외 잔여) | partial | 낮음 | 쉬움 |
| 🟢 LOW | N5 bare except 잔여 | partial | 낮음 | 쉬움 |
| 🟢 LOW | N6 F841 unused vars (잔여 83건, unsafe-fix 대상) | partial | 낮음 | 쉬움 |

(Issue #1, #2 → ✅ Resolved 섹션 참조)

---

## 🎯 권장 수정 순서 (다음 이터레이션)

### 완료 (✅, 2026-07-13 기준)
- Queen Inject 쿨다운, 누락 업그레이드, N1-N4 중복 정의, Issue #3/#4, F841 47건 자동 정리, position_utils 테스트 신설

### 다음 작업 (미진행)
1. `position_utils` 호출부 11곳을 개별 검토 후 이관 (Issue #5)
2. 잔여 F841 83건 수동 검토 (unsafe-fix라 부작용 가능성 있는 것들)
3. Queen 외 매직 넘버 정리 (Issue #6 나머지)
4. `MASSIVE_FIX_PLAN.md` P1 항목 중 실제 미구현분 재확인 (P1-2, P1-4, P1-6, P1-7 등 — 상세는 해당 문서 참조)

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
