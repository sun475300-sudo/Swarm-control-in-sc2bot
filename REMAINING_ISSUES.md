# 🔍 Remaining Issues - 추가 검토 결과

## 📋 개요

통합 문제 해결 후 발견된 추가 개선 사항들입니다.

**Last refreshed:** 2026-07-16 (자동 점검 사이클 — N1~N4 해결 확인, 신규 테스트 안정성 버그 1건 수정)

---

## 🆕 신규 발견 (PR #44, 2026-04-27) — 2026-07-16 재검증

자동/수동 점검 사이클(테스트 → 코드 검사 → 개선 → 커밋/푸시 반복)에서 새로 식별된 항목.

| ID | 설명 | 우선순위 | 상태 |
|----|------|---------|------|
| N1 | `OpponentModeling.on_step` 중복 정의 (line 341 vs 765 — F811) | 🟠 HIGH | ✅ resolved — `flake8 --select=F811 wicked_zerg_challenger/`로 재검증, 중복 정의 없음 (단일 `on_step` at line 341) |
| N2 | `EconomyManager._prevent_resource_banking` / `_reduce_gas_workers` 재정의 (F811) | 🟡 MED | ✅ resolved — 각각 단일 정의만 존재 확인 |
| N3 | `combat_manager._find_harass_target` 재정의 (line 2377 vs 4278) | 🟡 MED | ✅ resolved — 단일 정의만 존재 확인 |
| N4 | `production_resilience.build_terran_counters` 재정의 (1369 vs 1866) | 🟡 MED | ✅ resolved — 해당 함수 자체가 현재 코드에 없음(제거됨) |
| N5 | bare `except Exception:` 다수 (≈360+) — 이번 PR에서 12건 처리, 잔여 다수 | 🟢 LOW | partial — 잔여 460건 (2026-07-16 재계산), cycle 6+에서 점진 처리 권장 |
| N6 | F841 unused local variables (visuals/make_pptx 등) | 🟢 LOW | open — 잔여 130건 (`wicked_zerg_challenger/`만 기준), presentation 코드라 영향 작음 |

**검증 방법**: `python3 -m flake8 --select=F811,F841 wicked_zerg_challenger/ --max-line-length=200`

**신규 버그 발견 및 수정 (2026-07-16)**: `tests/test_combat_phase_fsm.py`가 전체 스위트(`pytest tests/`)와 함께 실행될 때만 12개 테스트가 `RuntimeError: There is no current event loop`로 실패 — 단독 실행 시엔 통과하는 테스트 순서 의존성 버그. 원인: 이전 테스트(`asyncio.run()` 사용)가 종료되며 메인 스레드의 현재 이벤트 루프를 `None`으로 설정하는데, 이 파일은 `asyncio.get_event_loop().run_until_complete(...)`로 "이미 루프가 있다"고 가정하는 낡은 패턴을 사용해 실패. `asyncio.run(...)`으로 교체하여 수정 (5개 지점). 회귀 검증: `pytest tests/` 전체 502 passed / 14 skipped, `pytest wicked_zerg_challenger/tests/` 661 passed.

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

### ✅ Issue #3: Transfusion 우선순위 — 해결 확인 (2026-07-16)

`wicked_zerg_challenger/queen_manager.py:711` `_transfuse_injured_units()`에 `TRANSFUSE_PRIORITY` 딕셔너리 기반 우선순위 시스템이 이미 구현되어 있음 (CreepyBot 참고). 에너지/쿨다운/거리 체크 포함. 아래 원안은 참고용으로 보존.

### ✅ Issue #4: Resource Reservation Race Condition — 해결 확인 (2026-07-16)

`self.bot.resource_manager.try_reserve(minerals, gas, name)` (asyncio.Lock 기반)이 이미 구현되어 `economy_manager.py`, `defense_coordinator.py` 등에서 사용 중. 아래 원안과 사실상 동일한 설계로 반영됨.

### Issue #3 (원안, 참고용): Transfusion 우선순위 개선

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

**상태 (2026-07-16 재검증)**: 🟡 partial — `wicked_zerg_challenger/utils/position_utils.py`에 `get_center_position`/`get_weighted_center` 유틸리티는 이미 생성되어 있으나, 프로덕션 코드(`combat_manager.py`, `rally_point.py` 등) 어디에서도 import되어 사용되지 않음 (검증: `grep -rl "position_utils import" wicked_zerg_challenger --include=*.py` → 0건). 유틸은 만들어졌지만 호출부 교체가 안 된 상태 — 다음 사이클에서 실제 배선(wiring) 작업 필요.

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

## 📊 이슈 우선순위 요약 (open만, 2026-07-16 재검증)

| 우선순위 | 이슈 | 영향도 | 난이도 |
|---------|------|--------|--------|
| 🟢 LOW | #5 Position Utils 실제 배선 (유틸은 존재, 호출부 미교체) | 낮음 | 쉬움 |
| 🟢 LOW | #6 매직 넘버 | 낮음 | 쉬움 |
| 🟢 LOW | N5 bare `except Exception:` 잔여 460건 | 낮음 | 중간 (점진적) |
| 🟢 LOW | N6 F841 unused locals 잔여 130건 | 낮음 | 쉬움 |

(Issue #1~#4 → ✅ Resolved 섹션 참조. N1~N4 → ✅ 재검증 완료.)

---

## 🎯 권장 수정 순서

### 1단계: 완료 (✅)
~~1. Queen Inject 쿨다운 수정 (25 → 29)~~ — 완료
~~2. 누락된 업그레이드 추가~~ — 완료
~~3. Transfusion 우선순위 시스템 구현~~ — 완료 (queen_manager.py:711)
~~4. Resource Reservation 동기화~~ — 완료 (resource_manager.try_reserve)
~~N1~N4. F811 중복 정의 4건~~ — 완료

### 2단계: 배선/정리 (미진행)
5. Position Utils 유틸리티를 실제 호출부(combat_manager.py 등)에 연결
6. Constants 정리 (매직 넘버 → GameConfig/GameConstants)
7. bare except 460건 점진적 축소 (로그 남기는 except로 전환)
8. F841 unused locals 130건 정리

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

### 현재 상태 (2026-07-16 재검증)
- ✅ **치명적 통합 문제**: 완전히 해결됨
- ✅ **모든 단위 테스트**: 통과 (`tests/` 502 passed / 14 skipped, `wicked_zerg_challenger/tests/` 661 passed — 총 1163 passing)
- ✅ **기본 기능**: 정상 작동
- ✅ **테스트 순서 의존성 버그 1건 수정**: `tests/test_combat_phase_fsm.py`의 `asyncio.get_event_loop()` → `asyncio.run()` (자세한 내용은 상단 "신규 버그 발견 및 수정" 참조)

### 위의 이슈들은
- 모두 **선택적 개선 사항**
- 즉시 수정 불필요
- 점진적 개선 권장

---

**검토 완료일**: 2026-07-16 (자동 점검 사이클)
**상태**: 추가 개선 사항 문서화 완료
