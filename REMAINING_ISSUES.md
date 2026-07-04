# 🔍 Remaining Issues - 추가 검토 결과

## 📋 개요

통합 문제 해결 후 발견된 추가 개선 사항들입니다.

**Last refreshed:** 2026-07-04 (재검증 사이클 — N1~N4, Issue #3~#5 코드 확인 결과 모두 해결됨으로 정정; 새 이슈 N7 발견 및 수정)

---

## 🆕 2026-07-04 재검증 결과

`test → 코드 검사 → 개선 → 커밋/푸시` 반복 사이클의 일환으로 아래 표의 모든 항목을 실제 코드에서 재확인했습니다.
문서가 stale했던 항목이 대부분이라 실제 상태로 정정합니다 (별도 작업 불필요했던 항목은 "이미 해결됨"으로 표시).

| ID | 설명 | 상태 |
|----|------|------|
| N1 | `OpponentModeling.on_step` 중복 정의 | ✅ 이미 해결됨 — `opponent_modeling.py`에 `on_step` 정의 1개만 존재 확인 |
| N2 | `EconomyManager._prevent_resource_banking`/`_reduce_gas_workers` 재정의 | ✅ 이미 해결됨 — 각 메서드 정의 1개만 존재 확인 |
| N3 | `combat_manager._find_harass_target` 재정의 | ✅ 이미 해결됨 — 정의 1개만 존재 확인 |
| N4 | `production_resilience.build_terran_counters` 재정의 | ✅ 이미 해결됨 — 정의 1개만 존재 확인 |
| N5 | bare `except Exception:` 다수 | 🟢 LOW, 잔존 (457건, `tests/` 제외) — 품질 개선 과제로 유지 |
| N6 | F841 unused local variables | 🟢 LOW, 잔존 (127건, `tests/` 제외) — 대부분 `except ... as e:` 미사용, 저위험 |
| N7 | **(신규)** `BotStepIntegrator.execute_game_logic()` 내 11개 서브시스템(`spatial_optimizer`, `data_cache`, `base_destruction`, `building_destroyer`, `self_healing`, `personality`, `battle_prep`, `destructible_aware`, `nydus_trainer`, `overlord_safety`, `creep_highway_astar`)의 `on_step()` 예외가 production 모드에서 완전히 무음(無音) 처리됨 — `if error_handler.debug_mode: raise` 뿐이고 else 분기가 없어 로그/카운트가 전혀 남지 않음. 라이브 게임 중 해당 서브시스템이 예외로 죽으면 그 게임 내내 아무 흔적 없이 기능이 사라짐 | ✅ **fixed** — `bot_step_integration.py`에 파일 내 기존 관례(`CreepHighway`, `RLAgent` 등)와 동일하게 `error_handler.error_counts[...]` 증가 + capped `self.logger.error(...)` 추가. 회귀 방지용 정적 분석 테스트 `tests/test_execute_game_logic_error_visibility.py` 추가 (execute_game_logic의 모든 except 블록이 debug_mode 분기와 함께 error_counts를 참조하는지 AST로 검증) |

플레이그라운드 검증: 전체 스위트 662 passed (기존 661 + 신규 1), `flake8 --select=F811,F821,F823` 클린.

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

## 🟡 MEDIUM Priority Issues (2026-07-04 재검증: 모두 해결됨 확인)

### ✅ Issue #3: Transfusion 우선순위 개선 — 이미 구현됨

**확인**: `queen_manager.py:711` `_transfuse_injured_units()`에 `TRANSFUSE_PRIORITY` 테이블 기반
우선순위 정렬(고가 유닛 우선) + 쿨다운 + 거리 체크가 이미 구현되어 있음 ("CreepyBot-inspired priority system"
주석 확인). 아래 제안 코드는 참고용으로 남겨둠.

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

### ✅ Issue #4: Resource Reservation Race Condition — 이미 구현됨

**확인**: `core/resource_manager.py:36`에 `asyncio.Lock` 기반 `try_reserve()`/`release()`가
제안된 설계와 거의 동일하게 이미 구현되어 있음.

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

### ✅ Issue #5: 코드 중복 - Position 계산 — 이미 구현됨

**확인**: `utils/position_utils.py`에 `get_center_position()`/`get_weighted_center()`가
제안된 형태로 이미 구현되어 여러 파일에서 사용 중.

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

## 📊 이슈 우선순위 요약 (2026-07-04 재검증)

| 우선순위 | 이슈 | 상태 |
|---------|------|------|
| 🟠 HIGH | N7 서브시스템 예외 무음 처리 (`execute_game_logic`) | ✅ 이번 사이클에서 수정 |
| 🟡 MEDIUM | #3 Transfusion 우선순위 | ✅ 이미 구현됨 (재검증) |
| 🟡 MEDIUM | #4 Resource Race Condition | ✅ 이미 구현됨 (재검증) |
| 🟢 LOW | #5 코드 중복 제거 (Position) | ✅ 이미 구현됨 (재검증) |
| 🟢 LOW | #6 매직 넘버 | 🟡 대부분 해결 (`game_config.py` 153개 상수) — 잔여 산발적 매직넘버는 발견 시 개별 처리 |
| 🟢 LOW | N5 bare except (457건) | 열려있음 — 저위험, 점진 개선 대상 |
| 🟢 LOW | N6 F841 unused locals (127건) | 열려있음 — 저위험, 점진 개선 대상 |
| 🟢 LOW | P3-3 `combat_manager.py` 리팩토링 (`MASSIVE_FIX_PLAN.md`) | 열려있음 — 5,051줄, 고난이도/고위험이라 전용 세션 필요 |

(Issue #1, #2 → ✅ Resolved 섹션 참조)

---

## 🎯 다음 사이클 권장 작업 순서

1. **combat_manager.py 리팩토링 착수 준비** — 먼저 현재 동작을 고정하는 characterization test 추가 후 `MicroController`/`MacroDecisions`/`ThreatEvaluator` 분리 (`MASSIVE_FIX_PLAN.md` P3-3). 리스크가 크므로 작은 PR 여러 개로 분할 권장.
2. **N5/N6 점진적 정리** — bare except에 최소 로깅 추가, 미사용 지역변수 제거. 파일 단위로 작게 나눠 진행.
3. **잔여 매직넘버 스윕** — `game_config.py`에 없는 하드코딩 임계값 발견 시 상수화.

---

## 🔍 추가 검토 필요 항목 (미확인 — 다음 사이클에서 검증 필요)

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
- [ ] 에러 핸들링 일관성 확인 (N7 수정으로 `execute_game_logic`은 개선됨, 다른 파일도 동일 패턴 있는지 스윕 필요)

---

## 📝 참고 사항

### 현재 상태 (2026-07-04 재검증)
- ✅ **치명적 통합 문제**: 완전히 해결됨
- ✅ **SC2 봇 테스트 스위트**: 662/662 통과 (`wicked_zerg_challenger/tests/`)
- ✅ **기본 기능**: 정상 작동
- ⚠️ 이 문서의 과거 항목들은 실제로는 이미 해결된 채 "open"으로 방치되어 있었음 — 앞으로는 재검증 없이 "open" 항목을 그대로 신뢰하지 말 것. 매 사이클마다 grep/코드 확인으로 실제 상태를 재확인 후 갱신.

### 위의 이슈들은
- 대부분 이미 해결되었거나 저위험 품질 개선 사항
- 즉시 수정 불필요한 항목 위주
- 실질적으로 남은 큰 작업은 `combat_manager.py` 리팩토링 (P3-3) 하나

---

**검토 완료일**: 2026-01-29 (최초), 2026-07-04 (재검증 + N7 수정)
**상태**: 재검증 완료 — N1~N6, Issue #3~#5 실제로 이미 해결됨 확인; N7 신규 발견 후 수정; combat_manager.py 리팩토링이 유일한 대형 잔여 과제
