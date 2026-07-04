# 🔍 Remaining Issues - 추가 검토 결과

## 📋 개요

통합 문제 해결 후 발견된 추가 개선 사항들입니다.

**Last refreshed:** 2026-07-04 (자동 점검 세션 — N1~N4 해결 확인, Issue #3/#5 해결 확인)

---

## 🆕 신규 발견 (PR #44, 2026-04-27) — 2026-07-04 재검증

자동/수동 점검 사이클(테스트 → 코드 검사 → 개선 → 커밋/푸시 반복)에서 새로 식별된 항목.

| ID | 설명 | 우선순위 | 상태 |
|----|------|---------|------|
| N1 | `OpponentModeling.on_step` 중복 정의 (line 341 vs 765 — F811) | 🟠 HIGH | ✅ Resolved — commit `e648ae4` (2026-06-01)에서 제거. `pyflakes` 재검증: F811 0건 |
| N2 | `EconomyManager._prevent_resource_banking` / `_reduce_gas_workers` 재정의 (F811) | 🟡 MED | ✅ Resolved — 위와 동일 커밋에서 정리 |
| N3 | `combat_manager._find_harass_target` 재정의 (line 2377 vs 4278) | 🟡 MED | ✅ Resolved — 위와 동일 커밋에서 정리 |
| N4 | `production_resilience.build_terran_counters` 재정의 (1369 vs 1866) | 🟡 MED | ✅ Resolved — 위와 동일 커밋에서 정리 |
| N5 | bare `except Exception:` 다수 (≈360+) | 🟢 LOW | open — 2026-07-04 기준 `wicked_zerg_challenger/`에 468건 잔존, 점진적 개선 필요 |
| N6 | F841 unused local variables (visuals/make_pptx 등) | 🟢 LOW | open — 125건 잔존 (presentation 코드라 영향 작음) |

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

## ✅ Issue #3: Transfusion 우선순위 — Resolved (확인일: 2026-07-04)

**위치**: `wicked_zerg_challenger/queen_manager.py:711` `_transfuse_injured_units()`

이 문서에 있던 개선 제안(`HEAL_PRIORITY`/`CANNOT_HEAL`)과 동일한 목적의 로직이 이미
`TRANSFUSE_PRIORITY`/`UNHEALABLE_UNITS`라는 이름으로 구현되어 있음을 확인. 제안보다
더 정교함 (CreepyBot 기준 `health_deficit >= 125 OR health_ratio < 0.25` 조건,
쿨다운·거리·에너지 체크, 스파인 크롤러 포함 옵션). 회귀 테스트:
`tests/test_queen_transfusion.py`, `tests/test_queen_transfusion_manager.py`
(`test_priority_ordering`, `test_cannot_heal_blacklist` 등). 문서만 stale했던 것으로
별도 작업 없이 닫음.

<details>
<summary>원래 제안 (참고용, 구현은 위 실제 코드 기준)</summary>

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

## 🟡 MEDIUM Priority Issues (still open)

### Issue #4: Resource Reservation Race Condition

**위치**: `resource_manager.py` — **파일 자체가 존재하지 않음 (확인일: 2026-07-04)**. 스코프를 정하거나
백로그에서 명시적으로 제외할지 결정 필요.

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

### Issue #5: 코드 중복 - Position 계산 — 🟡 PARTIAL (확인일: 2026-07-04)

`utils/position_utils.py`에 `get_center_position`/`get_weighted_center`가 구현되어
있으나, 실제 중복 계산부(`combat/expansion_defense.py:296`, `combat/combat_execution.py:262`,
`combat/infestor_tactics.py:189`, `combat/micro_combat.py:1345`, `combat_phase_controller.py:591`,
`micro_controller.py:525`, `combat_manager.py:3657`, `battle_preparation_system.py:166`,
`idle_unit_manager.py:179`)는 아직 하나도 유틸리티로 교체되지 않음. "DONE"이 아니라
유틸리티만 만들어지고 적용이 안 된 상태 — 다음 세션 후보 작업.

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

## 📊 이슈 우선순위 요약 (open만, 2026-07-04 갱신)

| 우선순위 | 이슈 | 영향도 | 난이도 |
|---------|------|--------|--------|
| 🟡 MEDIUM | #4 Resource Race Condition (`resource_manager.py` 부재) | 낮음 | 중간 |
| 🟡 MEDIUM | N5 bare except (468건 잔존) | 낮음 | 진행중 |
| 🟢 LOW | #5 Position Utils 적용 (유틸은 존재, 9개 호출부 미적용) | 낮음 | 쉬움 |
| 🟢 LOW | N6 unused locals (125건) | 낮음 | 쉬움 |

(Issue #1, #2, #3 → ✅ Resolved 섹션 참조 / N1-N4 → ✅ Resolved 섹션 참조)

---

## 🎯 권장 수정 순서

### 1단계: 완료 (✅)
~~1. Queen Inject 쿨다운 수정 (25 → 29)~~ — 코드 반영 완료
~~2. 누락된 업그레이드 추가~~ — 코드 반영 완료
~~3. Transfusion 우선순위 시스템~~ — 코드 반영 완료 (2026-07-04 확인)
~~N1-N4. F811 중복 정의 4건~~ — commit `e648ae4`에서 해결 (2026-07-04 확인)

### 2단계: 구조 개선 (미진행)
4. Resource Reservation 동기화 (`resource_manager.py` 신규 생성 필요)
5. Position Utils 실제 적용 (9개 파일의 중복 계산부를 `get_center_position`으로 교체)
6. Constants 정리 (계속 진행 중)

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

## 🔁 2026-07-04 자동 점검 세션

전체 리포지토리 점검(테스트 실행 → ROADMAP.md 항목별 코드 대조 → 이슈 재검증 →
수정/문서화 → 커밋/푸시) 결과:

- **테스트**: `tests/` 494 pass / 8 fail(무관한 crypto_trading 샌드박스 의존성 문제,
  SC2 봇과 무관) / 14 skip. `wicked_zerg_challenger/tests/` 661 pass / 0 fail.
- **수정**: `tests/test_combat_phase_fsm.py`의 `asyncio.get_event_loop()` deprecated 패턴
  → `asyncio.run()`으로 교체 (12건 실패 → 0건). `tests/conftest.py`에
  `PROTOCOL_BUFFERS_PYTHON_IMPLEMENTATION=python` 환경변수 설정 추가 (로컬 실행 시
  `tests/`만 단독 실행하면 protobuf 충돌로 collection error 발생하던 문제 해결).
- **재검증 결과**: N1-N4(F811 중복 정의), Issue #3(수혈 우선순위)은 이미 코드에
  구현되어 있었음 — 문서만 stale. Issue #5(Position Utils)는 유틸리티만 존재하고
  실제 적용은 안 된 반쪽짜리 상태로 재분류.
- **정체 확인**: `wicked_zerg_challenger/` 로직 커밋은 2026-06-01(`6947f1a`)이 마지막이고,
  이후 2026-06-25 CI yml 수정 1건 외에는 약 한 달간 활동 없음.
- **다음 우선순위**: Issue #4(`resource_manager.py` 신규 생성 여부 결정),
  Position Utils 9개 호출부 교체, `intel_manager.py` 빌드 패턴 12→25 확장,
  `NEXT_LARGE_PLAN.md`/`NEXT_PHASE_PLAN.md`의 P7xx/P8xx 항목 정리(코드/커밋 근거 없음).

---

**검토 완료일**: 2026-01-29
**상태**: 추가 개선 사항 문서화 완료
