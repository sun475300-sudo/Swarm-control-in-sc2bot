# 🔍 Remaining Issues - 추가 검토 결과

## 📋 개요

통합 문제 해결 후 발견된 추가 개선 사항들입니다.

**Last refreshed:** 2026-07-06 (자동 점검 사이클 재개 — N1~N6, Issue #3/#4/#5/#6 전부 코드에서 재확인 후 Resolved로 이동; 새 이슈 N7~N9 발견)

---

## ✅ N1~N6 재검증 결과 (2026-07-06)

PR #44 이후 진행된 별도 작업들(PR #218 "stabilize SC2 bot test suite" 포함)에서 이미 전부
해결된 것으로 코드에서 확인됨. 문서만 stale했던 상태 — 아래 표는 검증 근거.

| ID | 설명 | 확인 결과 |
|----|------|---------|
| N1 | `OpponentModeling.on_step` 중복 정의 | `opponent_modeling.py`에 `on_step` 단일 정의만 존재 (line 341). Resolved. |
| N2 | `EconomyManager._prevent_resource_banking` / `_reduce_gas_workers` 재정의 | `economy_manager.py`에 각각 단일 정의만 존재 (3198, 3995). Resolved. |
| N3 | `combat_manager._find_harass_target` 재정의 | 단일 정의만 존재 (4992). Resolved. |
| N4 | `production_resilience.build_terran_counters` 재정의 | 단일 정의만 존재 (`local_training/production_resilience.py:1961`). Resolved. |
| N5 | bare `except Exception:` 다수 | 잔여 건은 있으나 실행 경로에 영향 주는 케이스는 못 찾음 — 재우선순위 하향, 별도 추적 안함. |
| N6 | F841 unused locals (presentation 코드) | 영향 없음(발표 자료), 낮은 우선순위 유지. |

전체 리포 AST 스캔(클래스 내 중복 메서드 정의) 결과 실질적 중복은 0건
(`canary_deploy/sc2_canary_release.py`의 `canary_weight` property/setter 쌍은 정상 패턴, 오탐).

## ✅ Issue #3, #4, #5, #6 재검증 결과 (2026-07-06)

- Issue #3 (Transfusion 우선순위): `queen_manager.py:711` `_transfuse_injured_units`에
  CreepyBot 스타일 `TRANSFUSE_PRIORITY` 테이블 + 체력 가중치까지 구현되어 있음 (제안보다 더 정교함). Resolved.
- Issue #4 (Resource Reservation race condition): `wicked_zerg_challenger/core/resource_manager.py:36`
  `asyncio.Lock` 기반 `try_reserve`/`release` 구현 확인, `tests/test_resource_manager.py`에
  `test_concurrent_reservations`/`test_race_condition_prevention` 회귀 테스트 존재. Resolved.
- Issue #5 (Position 계산 중복): `wicked_zerg_challenger/utils/position_utils.py` 존재, 구현됨. Resolved.
- Issue #6 (매직 넘버): `wicked_zerg_challenger/utils/game_constants.py`,
  `wicked_zerg_challenger/utils/distance_cache.py` 둘 다 존재. Resolved.

---

## 🆕 신규 발견 (2026-07-06 자동 점검 사이클)

| ID | 설명 | 우선순위 | 상태 |
|----|------|---------|------|
| N7 | `tests/test_combat_phase_fsm.py`의 5개 헬퍼가 `asyncio.get_event_loop().run_until_complete(...)` 사용 → Python 3.11 + pytest-asyncio(auto mode) 조합에서 "There is no current event loop in thread 'MainThread'"로 12개 테스트 실패 | 🟠 HIGH | ✅ FIXED (이번 세션) — `asyncio.run(...)`으로 교체, 23/23 통과 확인 |
| N8 | 샌드박스 환경에 `sc2`(burnysc2) 패키지가 없으면 `pip install burnysc2`가 실패함 — 전이 의존성 `mpyq`의 setup.py가 최신 setuptools(83.x)에서 제거된 distutils shim(`install_layout`)에 의존 → 빌드 실패. 이 때문에 `pytest tests/`가 전체 컬렉션 에러로 죽어 테스트를 아예 못 돌림 | 🟠 HIGH (CI/신규 환경 재현성) | 우회 확인: `setuptools==68.2.2` 선install 후 `mpyq` → `burnysc2` 순서로 install하면 해결. `.claude/hooks/session-start.sh`에 자동화 스크립트 작성함 (사용자 승인 대기 — 자동 실행 훅이라 별도 확인 필요) |
| N9 | `wicked_zerg_challenger/tests/`를 root `tests/`와 같은 pytest 프로세스에서 함께 collect하면 (`pytest tests/ wicked_zerg_challenger/tests/`) `scripts.ladder_tracker`/`scripts.meta_adapter` 임포트가 간헐적으로 실패함. 원인: 거의 모든 `wicked_zerg_challenger/tests/*.py`가 파일 상단에서 `sys.path.insert(0, ...)`로 sys.path를 직접 조작하는데, `scripts/`가 repo-root와 `wicked_zerg_challenger/` 양쪽에 동명 네임스페이스 패키지로 존재해서 먼저 캐싱되는 쪽에 따라 결과가 갈림 | 🟢 LOW (두 스위트를 분리 실행하면 문제 없음 — `pytest.ini`의 기본 testpaths도 분리되어 있어 정상 사용 시 발현 안 됨) | open, 재현 조건이 좁아 낮은 우선순위로 보류 |

**이번 세션 실측 결과**: `sc2`/`numpy`/`torch` 등 실제 설치 후 전체 스위트 실행 —
root `tests/`: 502 passed, 14 skipped, 0 failed (N7 수정 전 12 failed).
`wicked_zerg_challenger/tests/`: 661 passed, 0 failed.

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

## 📊 이슈 우선순위 요약 (open만, 2026-07-06 기준)

| 우선순위 | 이슈 | 영향도 | 난이도 |
|---------|------|--------|--------|
| 🟠 HIGH | N8 샌드박스 sc2/mpyq 설치 실패 (신규 환경 재현성) | 높음(테스트 자체가 불가) | 쉬움 (우회 스크립트 작성 완료, 훅 활성화만 남음) |
| 🟢 LOW | N5 bare except 잔여 | 낮음 | 쉬움 |
| 🟢 LOW | N6 F841 unused locals (프레젠테이션 코드) | 낮음 | 쉬움 |
| 🟢 LOW | N9 두 테스트 스위트 동시 collect 시 namespace 패키지 충돌 | 낮음(분리 실행 시 미발현) | 중간 |

(Issue #1~#6, N1~N4, N7 → ✅ Resolved 섹션 참조 — 전부 이번 세션에 코드로 재확인 또는 수정 완료)

---

## 🎯 권장 수정 순서 (2026-07-06 갱신)

### 완료 (✅)
- Queen Inject 쿨다운, 누락 업그레이드, N1~N4 중복 정의, Issue #3(Transfusion 우선순위),
  Issue #4(Resource Reservation 동기화), Issue #5(Position Utils), Issue #6(Constants 정리) —
  전부 코드에 이미 반영되어 있음을 확인.
- N7 (`test_combat_phase_fsm.py` asyncio 이벤트 루프 버그) — 이번 세션에 수정, 23/23 통과.

### 다음 우선순위
1. N8 — SessionStart 훅(`​.claude/hooks/session-start.sh`) 활성화 여부 사용자 확인
   (자동 실행 훅 생성은 승인이 필요해 이번 세션에서는 파일만 준비, 미등록 상태).
2. ROADMAP.md Sprint 4/6/7의 미구현 항목 (별도 감사 결과 참조 — `ROADMAP_AUDIT.md` 또는
   커밋 메시지 참고).

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

### 현재 상태 (2026-07-06 실측)
- ✅ **치명적 통합 문제**: 완전히 해결됨
- ✅ **root `tests/`**: 502 passed, 14 skipped, 0 failed
- ✅ **`wicked_zerg_challenger/tests/`**: 661 passed, 0 failed
- ✅ **기본 기능**: 정상 작동

### 위의 이슈들은
- 모두 **선택적 개선 사항** (N8 제외)
- 즉시 수정 불필요
- 점진적 개선 권장

---

**검토 완료일**: 2026-07-06
**상태**: 자동/수동 점검 사이클 재실행 완료 — N1~N9, Issue #1~#6 전부 재검증.
다음 사이클에서는 ROADMAP.md Sprint 4/6/7 미구현 항목 작업 예정.
