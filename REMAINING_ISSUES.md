# 🔍 Remaining Issues - 추가 검토 결과

## 📋 개요

통합 문제 해결 후 발견된 추가 개선 사항들입니다.

**Last refreshed:** 2026-07-07 (테스트→코드 감사→수정→커밋 사이클 재실행; N1-N4, Issue #3/#4 stale 확인 후 종결, 신규 버그 6건 발견/수정)

---

## 🆕 신규 발견 (PR #44, 2026-04-27) — 2026-07-07 재검증

N1-N4 (F811 중복 정의)는 PR #218 (2026-06-01, "stabilize SC2 bot test suite")에서
이미 정리되었음을 `flake8 --select=F811,F821`로 재확인. 문서만 stale했음.

| ID | 설명 | 우선순위 | 상태 |
|----|------|---------|------|
| N1 | `OpponentModeling.on_step` 중복 정의 | 🟠 HIGH | ✅ Resolved (PR #218에서 처리 확인) |
| N2 | `EconomyManager` 메서드 재정의 | 🟡 MED | ✅ Resolved (PR #218에서 처리 확인) |
| N3 | `combat_manager._find_harass_target` 재정의 | 🟡 MED | ✅ Resolved (PR #218에서 처리 확인) |
| N4 | `production_resilience.build_terran_counters` 재정의 | 🟡 MED | ✅ Resolved (PR #218에서 처리 확인) |
| N5 | bare `except Exception:` 다수 | 🟢 LOW | open — 잔여 다수, 우선순위 낮음 |
| N6 | F841 unused local variables | 🟢 LOW | 대부분 harmless로 재확인됨 (아래 2026-07-07 감사 참조), 소수는 실버그였고 수정됨 |

---

## 🆕 2026-07-07 코드 감사 결과 (테스트→감사→수정→커밋 반복 사이클)

661개 테스트 전부 통과 상태에서, F841("assigned but never used") 플래그를 실마리로
combat_manager.py / economy_manager.py / strategy_manager.py / production_resilience.py /
upgrade_manager.py / opponent_modeling.py / unit_factory.py 를 4개 서브에이전트로
병렬 감사. 확인된 실제 버그와 조치:

| # | 파일:라인 | 결함 | 조치 |
|---|-----------|------|------|
| 1 | `combat_manager.py` (2곳) | 위협/공격 감지 유닛 집합에 `"LURKER"` 문자열 사용 — python-sc2 실제 enum명은 `LURKERMP`/`LURKERMPBURROWED`라 러커 단독 공격이 threat/attack으로 전혀 감지되지 않음 | ✅ Fixed — 두 집합 모두 `LURKERMP`, `LURKERMPBURROWED`로 교체 + 회귀 테스트 3건 (`tests/test_combat_manager_lurker_and_retreat.py`) |
| 2 | `combat_manager.py:_evaluate_army_retreat` | `enemy_supply` 계산 시 `can_attack` 필터 없이 모든 근처 `enemy_units` 포함 — 일꾼/오버로드 등 비전투 유닛이 아군 대비 열세 비율을 왜곡해 불필요한 후퇴 유발 | ✅ Fixed — `can_attack` 필터 추가 + 회귀 테스트 |
| 3 | `economy_manager.py:_redistribute_mineral_workers` | `under_saturated.remove((under_th, deficit))`가 로컬에서 변형된 `deficit` 값으로 튜플을 찾으려 해 거의 항상 `ValueError` 발생 → 상위 `except`에 잡혀 그 호출의 나머지 기지 재분배가 전부 취소됨 | ✅ Fixed — 인덱스 기반 in-place 갱신으로 교체 + 회귀 테스트 2건 |
| 4 | `economy_manager.py:_optimize_mineral_assignments` | `surplus_workers`에 실제 일꾼이 아니라 **미네랄 필드 객체**를 채워 넣어, 과잉 배정된 드론이 부족 패치로 절대 재배정되지 않음 (docstring이 약속한 기능이 통째로 죽어있었음) | ✅ Fixed — 패치별 실제 일꾼 리스트를 추적해 초과분만 `surplus_workers`에 담도록 수정 + 회귀 테스트 |
| 5 | `upgrade_manager.py:_get_upgrade_priority` | `race_priority_modifiers`가 대문자 키("Terran" 등)인데 조회는 소문자(`_normalize_enemy_race()` 결과)로 시도 — 항상 빈 dict 반환, 종족별 업그레이드 가중치가 전혀 반영되지 않음 | ✅ Fixed — `.capitalize()`로 키 매칭 수정 + 실제로 `priorities` 정렬에 반영 + 회귀 테스트 2건 |
| 6 | `opponent_modeling.py` → `strategy_manager.py` | 적 전략 예측/카운터 조합을 blackboard(`recommended_strategy`, `opponent_prediction`)에 기록만 하고 아무도 읽지 않음 — 정찰/모델링 결과가 실제 유닛 생산에 전혀 반영되지 않는 완전한 데드엔드 | ✅ Fixed — `StrategyManager.get_unit_ratios()`가 `recommended_strategy`를 읽어 해당 유닛 비율을 가중(1.25x) 후 재정규화 + 회귀 테스트 3건 |

각 수정은 "고치기 전 코드로 되돌리면 새 테스트가 실패한다"를 직접 확인한 뒤 커밋했음
(재현 가능한 회귀임을 검증).

### 이번 감사에서 확인했지만 이번 라운드에 수정하지 않은 항목 (다음 라운드 후보)

| # | 파일:라인 | 내용 | 우선순위 |
|---|-----------|------|---------|
| 7 | `strategy_manager.py:2536 _counter_zerg_units` | `ravager_count`를 가져오지만 카운터 로직에 전혀 사용 안 함 — ZvZ에서 적 라바짜기(bile) 물량에 대한 대응 부재 | 🟡 MED (기능 추가 필요, 단순 버그 수정 아님) |
| 8 | `local_training/production_resilience.py:787-829` | docstring은 "Muta > Hydra > Roach > Zergling" 우선순위를 명시하지만 실제로는 뮤탈리스크를 생산하지 않고 히드라 체크로 바로 넘어감 (다른 생산 경로에서 뮤탈 생산이 이뤄지므로 영향은 제한적) | 🟢 LOW-MED |

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

## ✅ Resolved (재확인: 2026-07-07)

### ✅ Issue #3: Transfusion 우선순위 — 이미 구현되어 있음

`queen_manager.py:_transfuse_injured_units()`에 CreepyBot 스타일의 우선순위 테이블
(`TRANSFUSE_PRIORITY`: Queen > Broodlord > Corruptor/Viper > Spine Crawler > Overseer
> Ultralisk > Ravager > Roach > Hydralisk > ...)과 치료 불가 유닛 제외 목록
(`UNHEALABLE_UNITS` = Baneling/Broodling/Locust)이 이미 구현되어 있음. 이 문서가
제안한 것보다 더 정교한 버전이 이미 코드에 있었음 — 문서만 stale했던 것으로 확인,
별도 작업 없이 종결.

### ✅ Issue #4: Resource Reservation Race Condition — 이미 구현되어 있음

`core/resource_manager.py`에 `asyncio.Lock` 기반 `try_reserve()`/`release()`가 이미
구현되어 있음 (`_reserved_minerals`/`_reserved_gas` 추적, lock으로 원자적 예약).
문서만 stale했던 것으로 확인, 별도 작업 없이 종결.

---

## 🟡 MEDIUM Priority Issues (still open)

### Issue #3 (구버전, 위 Resolved 섹션 참조 — 원문 보존용)

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

## 📊 이슈 우선순위 요약 (open만, 2026-07-07 갱신)

| 우선순위 | 이슈 | 영향도 | 난이도 |
|---------|------|--------|--------|
| 🟡 MED | #7 Ravager 카운터 전략 부재 (`strategy_manager.py:2536`) | 중간 (ZvZ) | 쉬움 |
| 🟢 LOW-MED | #8 late-game 뮤탈 생산 분기 미실행 (`production_resilience.py`) | 낮음 (중복 경로로 완화됨) | 쉬움 |
| 🟢 LOW | #5 코드 중복 제거 (Position 계산) | 낮음 | 쉬움 |
| 🟢 LOW | #6 매직 넘버 | 낮음 | 쉬움 |
| 🟢 LOW | N5 bare except 잔여 | 낮음 | 중간 |

(Issue #1-#4 → ✅ Resolved 섹션 참조. #3/#4는 이미 코드에 구현되어 있었음이 2026-07-07 재확인됨.)

---

## 🎯 권장 수정 순서

### 완료 (✅)
- ~~Queen Inject 쿨다운 수정 (25 → 29)~~
- ~~누락된 업그레이드 추가~~
- ~~Transfusion 우선순위 시스템~~ (이미 구현되어 있었음, 2026-07-07 확인)
- ~~Resource Reservation 동기화~~ (이미 구현되어 있었음, 2026-07-07 확인)
- ~~N1-N4 F811 중복 정의~~ (PR #218)
- ~~LURKER enum 이름 오타 (2건), 후퇴 판단 시 비전투 유닛 혼입, 미네랄 재분배 두 가지
  실버그, 종족별 업그레이드 가중치 미적용, OpponentModeling→StrategyManager 데드엔드~~
  (2026-07-07, 회귀 테스트 12건과 함께)

### 다음 라운드 후보 (미진행)
1. Ravager 카운터 전략 추가 (#7)
2. late-game 뮤탈 생산 분기 점검 (#8)
3. Position Utils 유틸리티 함수 분리 (#5)
4. Constants 정리 (#6)

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

### 현재 상태 (2026-07-07)
- ✅ **치명적 통합 문제**: 완전히 해결됨
- ✅ **모든 단위 테스트**: 통과 (673/673 — 661 기존 + 신규 회귀 테스트 12건)
- ✅ **기본 기능**: 정상 작동
- ⚠️ 이 문서는 지속적으로 stale해지는 경향이 있음 — 다음 라운드에서도
  "open"으로 표시된 항목은 실제 코드를 먼저 확인한 뒤 작업할 것 (많은 경우
  이미 해결되어 있었음).

### 위의 이슈들은
- 모두 **선택적 개선 사항**
- 즉시 수정 불필요
- 점진적 개선 권장

---

**검토 완료일**: 2026-07-07
**상태**: 테스트→코드 감사→수정→커밋 사이클 재실행, 신규 버그 6건 수정, stale 항목 정리 완료
