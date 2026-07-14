# 🔍 Remaining Issues - 추가 검토 결과

## 📋 개요

통합 문제 해결 후 발견된 추가 개선 사항들입니다.

**Last refreshed:** 2026-04-27 (Issue #1, #2 → Resolved; Issue #6 partially resolved via Batch 3)

---

## 🔁 2026-07-14 재검증 (PR #454)

이 문서는 여러 사이클에 걸쳐 갱신되지 않은 항목이 많아 **코드 대조 검증** 없이는
신뢰할 수 없는 상태였음. 아래는 실제 코드를 직접 확인한 결과.

### ✅ 이번 세션에서 수정 완료 (PR #454)

| # | 항목 | 위치 | 커밋 |
|---|------|------|------|
| 1 | 테스트 순서 의존 실패 (event loop) | `tests/test_combat_phase_fsm.py` | `99a58d0` |
| 2 | sc2 미설치 시 전체 테스트 collection 중단 | `tests/test_queen_transfusion.py` | `99a58d0` |
| 3 | `generate_test_script()` 호출 시 100% NameError | `integration_hub.py:233` | `be2ebec` |
| 4 | 죽은 shadow import (F811) | `discord_advanced_features.py`, `jax_flax_rl/flax_policy.py` | `be2ebec` |
| 5 | black/isort CI 게이트 실패 (66+19 파일) | 저장소 전역 | `4f34299` |
| 6 | CI `python-lint-test`에서 sc2 임포트 100% collection 실패 (protobuf ABI) | `.github/workflows/ci.yml` | `22a1c94` |
| 7 | `sc2bot-ci.yml` test job이 존재하지 않는 `tests/unit` 참조 — 매 실행 실패 | `.github/workflows/sc2bot-ci.yml` | `22a1c94` |
| 8 | idle이 아니지만 끼인 일꾼 미구출 (TODO 미구현) | `local_training/advanced_building_manager.py:765` | `4bd400d` |
| 9 | 비암호 용도 MD5 bandit High 경고 13건 | 10개 파일 | `81c9bcc` |

### ❌ Stale로 확인됨 (문서는 open이라 하지만 코드는 이미 해결됨)

- N1 `OpponentModeling.on_step` 중복 정의 — 현재 1개만 존재
- N2 `EconomyManager._prevent_resource_banking`/`_reduce_gas_workers` 중복 — 각 1개만 존재
- N3 `combat_manager._find_harass_target` 중복 — 1개만 존재
- N4 `production_resilience.build_terran_counters` 중복 — 1개만 존재
- Issue #3 (Transfusion 우선순위) — `economy/queen_transfusion_manager.py`에 `HEAL_PRIORITY`/`CANNOT_HEAL`로 이미 구현됨
- Issue #4 (Resource Reservation Race Condition) — `core/resource_manager.py`에 `asyncio.Lock` 기반 `try_reserve`/`release`로 이미 구현됨
- pytest skip/xfail 15건 "라벨링 필요" — 전부 numpy/torch 등 환경 의존 skip으로 이미 사유가 명시되어 있음
- MASTER_TODO의 "TODO/FIXME 27건" — 실제로는 대부분 "TODO"라는 문자열을 검색하는 도구 코드/변수명이며, 진짜 미구현 TODO는 1~2건

### 🟡 확인된 실제 잔여 항목 (다음 우선순위, 미착수)

| # | 항목 | 위치 | 심각도 | 비고 |
|---|------|------|--------|------|
| A | bare `except Exception:` 577건 (160개 파일) | 저장소 전역, 특히 `combat_manager.py`/`economy_manager.py`/`core/resource_manager.py` | LOW-MED | 대부분 로깅 없이 조용히 삼킴 — 런타임 실패 진단 어려움. 일괄 자동 수정은 위험(의도적 방어 코드 포함 가능) → 파일별 리뷰 필요, 별도 PR 권장 |
| B | `get_center_position()` 유틸 존재하나 미채택 | `combat/expansion_defense.py:296`, `combat/combat_execution.py:262`, `combat/infestor_tactics.py:189`, `combat/micro_combat.py:1354`, `combat_manager.py:3657`, `micro_controller.py:525`, `battle_preparation_system.py:166`, `idle_unit_manager.py:179`, `combat_phase_controller.py:591` | LOW | 중복 인라인 계산 9곳, 동작 동일하나 유지보수 부담 |
| C | `make_pptx.py` 미사용 지역변수 (F841) | `visuals/make_pptx.py:346,500,583,647,887,986,1163` | LOW | 프레젠테이션 생성 스크립트, 런타임 영향 없음 |
| D | `AdvancedBuildingManager` 클래스 전체가 봇 루프에 미연결 | `local_training/advanced_building_manager.py` | MED (설계 판단 필요) | `rescue_stuck_workers()`를 이번에 고쳤지만, 클래스 자체를 import/instantiate하는 곳이 코드베이스 어디에도 없음 — 실제 게임에 영향 없는 dead code. 봇 step 루프에 연결할지는 인게임 검증이 필요한 아키텍처 결정이라 사용자 확인 필요 |
| E | bandit High: `verify=False` (SSL 검증 비활성) | `debug_api.py:17`, `debug_direct_dl.py:13`, `debug_html.py:11`, `debug_scraper.py:13`, `debug_scraper_v2.py:12` | MED | 로컬 디버그 스크립트로 보이나 실제 사용 여부 확인 필요 — 프로덕션 경로가 아니라면 스크립트 자체를 정리(삭제/격리)하는 편이 나을 수 있음 |
| F | bandit High: `shell=True`/`os.system` | `integration_final/multi_lang_hub.py:54`, `jarvis_system_ctl.py:241`, `wicked_zerg_challenger/tools/monitor_background_training.py:42` | LOW | 사용자 입력이 유입되는 경로인지 파일별 확인 필요 — `monitor_background_training.py`는 하드코딩된 `cls`/`clear`만 실행해 위험 낮음 |
| G | `requests` 호출에 timeout 누락 (bandit B113) | `wicked_zerg_challenger/tools/scrape_spawningtool.py:30,53` | LOW | 응답 지연 시 무한 대기 가능 |

### 📌 다음 세션 권장 순서

1. **D 우선 사용자 확인**: `AdvancedBuildingManager`를 봇에 연결할지 여부 (아키텍처 결정)
2. **A**: bare except 577건 — 파일 단위로 쪼개서 로깅 추가 (combat/economy 우선)
3. **E, G**: 보안/안정성 — verify=False, requests timeout
4. **B, C, F**: 저위험 정리

## 🆕 신규 발견 (PR #44, 2026-04-27)

자동/수동 점검 사이클(테스트 → 코드 검사 → 개선 → 커밋/푸시 반복)에서 새로 식별된 항목.

| ID | 설명 | 우선순위 | 상태 |
|----|------|---------|------|
| N1 | `OpponentModeling.on_step` 중복 정의 (line 341 vs 765 — F811) | 🟠 HIGH | open — 동작 영향(상위 on_step이 미실행) 가능 |
| N2 | `EconomyManager._prevent_resource_banking` / `_reduce_gas_workers` 재정의 (F811) | 🟡 MED | open |
| N3 | `combat_manager._find_harass_target` 재정의 (line 2377 vs 4278) | 🟡 MED | open |
| N4 | `production_resilience.build_terran_counters` 재정의 (1369 vs 1866) | 🟡 MED | open |
| N5 | bare `except Exception:` 다수 (≈360+) — 이번 PR에서 12건 처리, 잔여 다수 | 🟢 LOW | partial |
| N6 | F841 unused local variables (visuals/make_pptx 등) | 🟢 LOW | open (presentation 코드라 영향 작음) |

검증 권장: PR 분리 (N1 단독 PR 권장 — 동작 변화 가능성).

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
| 🟡 MEDIUM | #3 Transfusion 우선순위 | 중간 | 중간 |
| 🟡 MEDIUM | #4 Resource Race Condition | 낮음 | 중간 |
| 🟢 LOW | #5 코드 중복 제거 | 낮음 | 쉬움 |
| 🟢 LOW | #6 매직 넘버 | 낮음 | 쉬움 |

(Issue #1, #2 → ✅ Resolved 섹션 참조)

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
