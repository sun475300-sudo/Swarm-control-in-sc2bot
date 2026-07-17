# 🔍 Remaining Issues - 추가 검토 결과

## 📋 개요

통합 문제 해결 후 발견된 추가 개선 사항들입니다.

**Last refreshed:** 2026-07-17 (자동 점검 사이클 — 테스트 전체 실행 후 코드 재검증)

---

## 🆕 2026-07-17 점검 결과

`tests/`(504 tests) + `wicked_zerg_challenger/tests/`(661 tests) 전체 실행, py_compile
전수 검사(417 files), flake8 E9/F63/F7/F82/F811/F821 검사를 수행했습니다.

### 신규 발견 및 수정 완료

| ID | 설명 | 우선순위 | 상태 |
|----|------|---------|------|
| N7 | 저장소 루트의 `pytest/` 디렉터리가 실제 `pytest` 패키지를 섀도잉 — `python -m pytest`가 루트에서 항상 `ModuleNotFoundError` 없이도 자기 자신을 import(빈 네임스페이스 패키지)해서 깨짐. 담긴 테스트(`test_battle.py`)는 `python_parallel/battle_sim.py`의 실제 함수를 import하지 않고 값만 복사해 사실상 아무것도 검증하지 않았음 | 🟠 HIGH | ✅ FIXED — `pytest/` 삭제, 실제 함수를 import하는 `tests/test_battle_sim.py`로 대체 |
| N8 | `tests/test_combat_phase_fsm.py`의 5개 헬퍼가 `asyncio.get_event_loop().run_until_complete(...)` (Python 3.10+ 비권장 패턴) 사용 — 같은 세션에서 `test_combat_manager.py`처럼 이벤트 루프를 닫는 테스트가 먼저 실행되면 스레드에 "현재 이벤트 루프"가 없어 `RuntimeError`로 12개 테스트가 순서 의존적으로 실패 | 🟠 HIGH | ✅ FIXED — `asyncio.run(...)`으로 교체, 전체 스위트 순서로 실행해도 통과 확인 |

### 재검증 결과 — 문서가 stale했던 항목 (별도 작업 불필요, 코드 확인 완료)

| ID | 설명 | 확인 결과 |
|----|------|---------|
| N1 | `OpponentModeling.on_step` 중복 정의 (F811) | flake8 F811 재실행 결과 0건 — 이미 해결됨 |
| N2 | `EconomyManager` 메서드 재정의 (F811) | 위와 동일, 0건 |
| N3 | `combat_manager._find_harass_target` 재정의 | 위와 동일, 0건 |
| N4 | `production_resilience.build_terran_counters` 재정의 | 위와 동일, 0건 |
| Issue #3 | Transfusion 우선순위 개선 | `queen_manager.py:711 _transfuse_injured_units`에 CreepyBot 기반 우선순위 테이블(퀸>브루드로드>커럽터>스파인>오버시어>울트라...) 및 치료 불가 유닛 제외 로직이 이미 구현되어 있음 |
| N5 | bare `except Exception:` (≈465건, `wicked_zerg_challenger/` 기준) | 잔존 확인 — 대부분 방어적 fallback 목적으로 의도된 패턴, 전수 리팩터링은 별도 대규모 PR 필요 (아래 백로그 참조) |
| N6 | F841 unused locals (130건) | 표본 점검 결과 `combat_manager.py`의 `regenerating`/`game_time`/`non_combat_names` 등은 실제 버그 아님(로직은 정상 동작, 변수만 미사용) — 코드 품질 이슈로 낮은 우선순위 유지 |

검증 권장: N7/N8은 테스트 인프라 안정성에 직접 영향이라 별도 확인 불필요(이미 diff로 검증됨).

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
| 🟡 MEDIUM | #4 Resource Race Condition | 낮음 (단일 스레드 협조형 asyncio 루프라 실측 경쟁 사례 미확인) | 중간 |
| 🟢 LOW | #5 코드 중복 제거 (position 계산) | 낮음 | 쉬움 |
| 🟢 LOW | #6 매직 넘버 | 낮음 | 쉬움 |
| 🟢 LOW | N5 bare except 전수 리팩터링 (≈465건) | 낮음 | 큼 (별도 PR 시리즈 필요) |
| 🟢 LOW | N6 F841 unused locals 정리 (130건) | 낮음 | 쉬움 |

(Issue #1, #2, #3 → ✅ Resolved 섹션 참조. N1-N4 → 재검증 완료, 이미 해결됨. N7, N8 → 이번 사이클에서 수정 완료.)

### 다음 사이클 작업 후보 (대규모 리스트)

우선순위 순. 각 항목은 독립적으로 PR 분리 가능:

1. **[MED]** `docs/history/` 이동 — `STATUS.md`의 P1.5 계획대로 47개 이상의 루트 `*.md` 리포트를 `docs/history/`로 이동해 리포지토리 루트 정리 (아직 미착수).
2. **[MED]** `ResourceManager.try_reserve` 실제 락(lock) 도입 여부 결정 — 현재 매니저들이 순차 실행되는지(`bot_step_integration.py`) 확인 후, 진짜 동시 실행 지점이 있으면 Issue #4 패치 적용, 없으면 문서에서 항목 제거.
3. **[LOW]** N5 bare `except Exception:` 465건 중 실제로 예외를 삼켜 버그를 숨길 수 있는 상위 20개 파일부터 `logger.warning(..., exc_info=True)` 등으로 로깅 추가 (전수 리팩터링은 리스크가 크므로 단계적 진행 권장).
4. **[LOW]** N6 F841 unused locals 130건 중 `combat_manager.py`(31건), `bot_step_integration.py`(13건) 정리 — 표본 검증 결과 실동작 버그는 아니었으나 코드 가독성 저하.
5. **[LOW]** Position 계산 중복 제거 (`utils/position_utils.py` 신설, Issue #5) — `combat_manager.py`/`rally_point.py`/`harassment_coord.py`에서 재사용.
6. **[검증 필요]** `ROADMAP.md`가 "Phase 56, 342 테스트" 기준으로 작성되어 있으나 실제로는 500+/661개 테스트가 존재하고 Sprint 1-7 태스크 대부분이 이미 구현되어 있음 — 문서가 크게 stale함. 다음 사이클에서 로드맵 전체를 현재 코드 상태 기준으로 재작성 필요.
7. **[테스트]** Sprint 8 QA 항목(`Task 8.1` Medium AI 30연전, `Task 8.2` AI Arena 패키지 검증)은 실제 SC2 클라이언트가 필요해 이 자동 점검 세션(샌드박스, SC2 게임 클라이언트 없음)에서는 실행 불가 — 별도 환경에서 수동/CI 실행 필요.

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
