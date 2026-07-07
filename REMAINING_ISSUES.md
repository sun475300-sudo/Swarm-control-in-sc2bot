# 🔍 Remaining Issues - 추가 검토 결과

## 📋 개요

통합 문제 해결 후 발견된 추가 개선 사항들입니다.

**Last refreshed:** 2026-07-07 (자동 점검 사이클 재검증 — N1~N4, Issue #3/#4 코드에 이미 반영 확인)

---

## 🆕 신규 발견 (PR #44, 2026-04-27) — 2026-07-07 재검증 완료

자동/수동 점검 사이클(테스트 → 코드 검사 → 개선 → 커밋/푸시 반복)에서 새로 식별된 항목.

| ID | 설명 | 우선순위 | 상태 |
|----|------|---------|------|
| N1 | `OpponentModeling.on_step` 중복 정의 (line 341 vs 765 — F811) | 🟠 HIGH | ✅ Resolved — `opponent_modeling.py`에 `on_step` 정의 1건만 남음 (shadowed 사본 제거됨, `e648ae4`) |
| N2 | `EconomyManager._prevent_resource_banking` / `_reduce_gas_workers` 재정의 (F811) | 🟡 MED | ✅ Resolved — 각 메서드 정의 1건만 존재 확인 (`economy_manager.py:3198`, `:3995`) |
| N3 | `combat_manager._find_harass_target` 재정의 (line 2377 vs 4278) | 🟡 MED | ✅ Resolved — 정의 1건만 남음 (`combat_manager.py:4992`) |
| N4 | `production_resilience.build_terran_counters` 재정의 (1369 vs 1866) | 🟡 MED | ✅ Resolved — 정의 1건만 남음 (`local_training/production_resilience.py:1961`) |
| N5 | bare `except Exception:` 다수 (≈360+) — 이번 PR에서 12건 처리, 잔여 다수 | 🟢 LOW | open — 잔여 다수, 사이클 6+ 후보 |
| N6 | F841 unused local variables (visuals/make_pptx 등) | 🟢 LOW | open — `flake8 --select=F841` 기준 여전히 130건 (`wicked_zerg_challenger/`), 대부분 미사용 예외 변수(`except ... as e`) |

N1~N4는 이후 커밋(`e648ae4` "delete shadowed duplicate methods")에서 이미 정리됨 — 문서만 stale 상태였음.

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

### ✅ Issue #3: Transfusion 우선순위 개선 — 구현 완료 (재검증 2026-07-07)

**구현 위치**: `wicked_zerg_challenger/economy/queen_transfusion_manager.py`

아래 제안 코드와 동일한 `HEAL_PRIORITY` dict (line 26) + `CANNOT_HEAL` set (line 43)이
이미 구현되어 있고, `tests/test_queen_transfusion.py` /
`tests/test_queen_transfusion_manager.py`로 회귀 테스트도 갖춰짐. 문서만 stale했던 항목 —
아래는 원래 제안이었던 참고용 스니펫.

**당시 문제 (해결됨)**:
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

**우선순위**: ~~🟡 MEDIUM~~ ✅ Resolved

---

### ✅ Issue #4: Resource Reservation Race Condition — 구현 완료 (재검증 2026-07-07)

**구현 위치**: `wicked_zerg_challenger/core/resource_manager.py`

`asyncio.Lock` 기반 `ResourceManager` 클래스가 이미 존재하고 (`try_reserve` /
`release` / `release_partial`), `defense_coordinator.py`와 `economy_manager.py`에서
실제로 호출되고 있음 — 제안이 아니라 이미 배선까지 완료된 상태. 회귀 테스트:
`tests/test_resource_manager.py`. 아래는 원래 제안이었던 참고용 스니펫.

**당시 문제 (해결됨)**:
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

**우선순위**: ~~🟡 MEDIUM~~ ✅ Resolved

---

## 🟢 LOW Priority Issues

### 🟡 Issue #5: 코드 중복 - Position 계산 — 절반만 완료 (재검증 2026-07-07)

**현재 상태**: `wicked_zerg_challenger/utils/position_utils.py`에 `get_center_position()` /
`get_weighted_center()` 헬퍼가 이미 구현돼 있지만 **실제 호출부가 0건** — 만들기만 하고
배선(wiring)이 끝나지 않은 상태. 아래 11곳에 동일한 인라인 중심좌표 계산이 여전히 중복돼 있음:

- `combat/expansion_defense.py:296`
- `combat/combat_execution.py:262`
- `combat/infestor_tactics.py:189`
- `combat/micro_combat.py:442`, `:1345`
- `combat_phase_controller.py:591`
- `micro_controller.py:525`
- `combat_manager.py:1622`, `:3657`
- `battle_preparation_system.py:166`
- `idle_unit_manager.py:179`

**남은 작업**: 위 11개 호출부를 `position_utils.get_center_position()` 호출로 교체
(순수 리팩터 — 수학은 동일, 동작 변화 없음). 프로덕션 전투 코드를 다수 건드리므로
회귀 테스트 확인 후 별도 PR로 진행 권장.

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

### 🟡 Issue #6b: 매직 넘버 (Magic Numbers) — 부분 진행 (재검증 2026-07-07)

**현재 상태**: `wicked_zerg_challenger/config/constants.py`, `utils/game_constants.py`
등 상수 모듈이 이미 존재하고 Queen 관련 11종 상수는 이관 완료(위 "PR #44 Issue #6"
참조). 다만 전체 코드베이스 기준 잔여 매직넘버 규모는 별도로 측정된 적이 없음 —
전수 조사 후 사이클 6+에서 순차 정리 권장 (파일 하나씩, 동작 불변 리팩터).

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

## 📊 이슈 우선순위 요약 (2026-07-07 재검증 — 실제 open 항목만)

| 우선순위 | 이슈 | 영향도 | 난이도 |
|---------|------|--------|--------|
| 🟡 MED | N5 bare `except Exception:` 잔여분 | 낮음 (디버깅 어려움) | 중간 (다건) |
| 🟢 LOW | N6 / Issue #6b F841 unused vars (130건) | 낮음 | 쉬움~중간 |
| 🟢 LOW | #5 Position Utils 배선 (helper 존재, 호출부 0건 — 11곳 교체 필요) | 낮음 | 쉬움 |

(Issue #1~#4, N1~N4 → 모두 ✅ Resolved 섹션 참조로 이동. 이전 버전 문서가 stale했던 것으로 확인됨.)

---

## 🎯 권장 수정 순서 (2026-07-07 갱신)

### 완료 (✅) — 이전엔 "미진행"으로 잘못 표기돼 있었음
~~1. Queen Inject 쿨다운 수정 (25 → 29)~~
~~2. 누락된 업그레이드 추가~~
~~3. Transfusion 우선순위 시스템~~ — `queen_transfusion_manager.py`에 구현 완료
~~4. Resource Reservation 동기화~~ — `core/resource_manager.py`에 구현 완료
~~N1~N4. 중복 메서드 정의 4건~~ — `e648ae4`에서 제거 완료

### 남은 실작업
5. Position Utils 배선 — 헬퍼는 있으나 11개 호출부 미교체 (순수 리팩터, 별도 PR 권장)
6. Constants 정리 — Queen 11종은 완료, 전체 매직넘버 규모는 미측정
7. N5 bare except 잔여분 라벨링/정리
8. N6 F841 unused-variable 130건 정리 (대부분 `except ... as e`에서 `e` 미사용)

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

**검토 완료일**: 2026-01-29 (최초), 2026-07-07 (재검증 — 자동 테스트/점검 사이클)
**상태**: Issue #1~#4 및 N1~N4 모두 코드에 반영 완료 확인. 남은 실작업은 #5(Position
Utils 배선), #6b(매직넘버 잔여), N5/N6(예외처리·미사용 변수 정리) — 위 "권장 수정 순서"
참조.
