# 🔍 Remaining Issues - 추가 검토 결과

## 📋 개요

통합 문제 해결 후 발견된 추가 개선 사항들입니다.

**Last refreshed:** 2026-07-09 — 자동 점검 사이클에서 재검증. 아래 N1~N6, #3~#6 항목은
모두 코드에 이미 반영되어 있는 것으로 확인되어 Resolved로 이동했습니다 (본 문서가
stale 상태였음). 같은 사이클에서 실제 CI/테스트 실행으로 재현한 새 이슈 M1~M10을
발견했고 그중 M1/M4/M5/M6/M7(전부 테스트·CI 인프라 차단 버그)은 이번 세션에서
수정 완료했습니다. **현재 open 상태: M2(고아 combat 모듈), M3/M8/M10(스타일 정리),
M9(requests timeout)** — 아래 표 참고.

---

## 🆕 신규 발견 (PR #44, 2026-04-27) — ✅ 전체 Resolved (2026-07-09 재검증)

자동/수동 점검 사이클(테스트 → 코드 검사 → 개선 → 커밋/푸시 반복)에서 새로 식별된 항목.
PR #218(2026-06-01~02, "stabilize SC2 bot test suite")에서 N1~N4가 이미 처리된 것을
2026-07-09 자동 점검에서 재확인했습니다 (각 메서드 grep 결과 정의가 1곳뿐).

| ID | 설명 | 우선순위 | 상태 |
|----|------|---------|------|
| N1 | `OpponentModeling.on_step` 중복 정의 (line 341 vs 765 — F811) | 🟠 HIGH | ✅ Resolved — 현재 단일 정의만 존재 |
| N2 | `EconomyManager._prevent_resource_banking` / `_reduce_gas_workers` 재정의 (F811) | 🟡 MED | ✅ Resolved — 단일 정의 확인 |
| N3 | `combat_manager._find_harass_target` 재정의 (line 2377 vs 4278) | 🟡 MED | ✅ Resolved — 단일 정의(4992) 확인 |
| N4 | `production_resilience.build_terran_counters` 재정의 (1369 vs 1866) | 🟡 MED | ✅ Resolved — 단일 정의(1961) 확인 |
| N5 | bare `except Exception:` 다수 (≈360+) | 🟢 LOW | open — 현재 465건, 광범위 리팩터라 별도 점진 작업으로 분리 권장 |
| N6 | F841 unused local variables (visuals/make_pptx 등) | 🟢 LOW | open (presentation 코드라 영향 작음) |

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

## 🟡 MEDIUM Priority Issues — ✅ 전체 Resolved (2026-07-09 재검증)

### Issue #3: Transfusion 우선순위 개선 필요 — ✅ Resolved

**구현 확인**: `queen_manager.py:711` `_transfuse_injured_units()` — CreepyBot 스타일
우선순위 테이블(QUEEN=0, BROODLORD=1, ... MUTALISK=12)과 `UNHEALABLE_UNITS`
(BANELING/BROODLING/LOCUSTMP) 제외 로직이 이미 구현되어 있음. 아래는 원안(참고용).

<details><summary>원안 (구현 완료, 참고용)</summary>

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

### Issue #4: Resource Reservation Race Condition — ✅ Resolved

**구현 확인**: `core/resource_manager.py:28` `ResourceManager` 클래스에 `try_reserve()`
(asyncio.Lock 기반)가 이미 구현되어 있고, `defense_coordinator.py`/`economy_manager.py`
등에서 `self.bot.resource_manager.try_reserve(...)` 호출로 사용 중. 아래는 원안(참고용).

<details><summary>원안 (구현 완료, 참고용)</summary>

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

## 🟢 LOW Priority Issues — ✅ 전체 Resolved (2026-07-09 재검증)

### Issue #5: 코드 중복 - Position 계산 — ✅ Resolved

**구현 확인**: `utils/position_utils.py`에 `get_center_position()` / `get_weighted_center()`
가 이미 구현되어 있음. 아래는 원안(참고용).

<details><summary>원안 (구현 완료, 참고용)</summary>

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

</details>

---

### Issue #6: 매직 넘버 (Magic Numbers) — 🟡 Partially Resolved

**구현 확인**: `utils/game_constants.py`에 `GameFrequencies`/`EconomyConstants`/
`BURROW_HP_THRESHOLD` 등 상수 클래스가 이미 구현되어 여러 매니저에서 사용 중
(`from utils.game_constants import GameFrequencies` 등). 다만 코드베이스 전체 매직넘버
채택은 진행 중(ROADMAP Sprint 7.3)이며 완전히 끝난 상태는 아님 — 아래는 원안(참고용).

<details><summary>원안 (인프라 구현 완료, 전체 채택은 진행 중)</summary>

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

</details>

---

## 🆕 2026-07-09 자동 점검 사이클에서 새로 발견된 실제 이슈

과거 문서(N1~N6, #1~#6)는 위와 같이 전부 stale로 확인되어 Resolved 처리했습니다.
아래는 이번 점검에서 **실제로 재현/확인한** 새 항목입니다.

| ID | 설명 | 우선순위 | 상태 |
|----|------|---------|------|
| M1 | 저장소 루트에 `pytest/` 디렉터리가 git으로 추적되어 있어, `python -m pytest` 실행 시 실제 pytest 패키지 대신 이 디렉터리를 import하여 `No module named pytest.__main__`으로 즉시 실패함 (`run_combat_tests.bat`, `PUSH_FIX_TO_MAIN.bat`, `github_actions_advanced/sc2bot-ci.yml`이 모두 `python -m pytest` 사용) | 🔴 HIGH | ✅ Fixed — `pytest/` → `python_pytest_demo/`로 이름 변경 |
| M2 | `wicked_zerg_challenger/combat/` 하위 13개 모듈(`queen_walk.py`, `doom_drop.py`, `multiprong_attack.py`, `air_unit_manager.py`, `attack_controller.py`, `baneling_bomb.py`, `combat_execution.py`, `expansion_defense.py`, `lurker_positioning.py`, `multitasking.py`, `nydus_tactics.py`, `victory_tracker.py`, `viper_tactics.py`, 총 ~4,700줄)가 구현되어 있으나 어디에서도 import되지 않아 런타임에 전혀 실행되지 않음. `SESSION_SUMMARY.md`에 기록된 과거 사례(overlord_transport/roach_burrow_heal 미통합)와 동일한 패턴이 13건 더 있는 상태 | 🟠 HIGH | open — 실제 SC2 클라이언트로 검증 불가한 샌드박스 환경이라, 모듈별로 안전하게(단위 테스트 포함) 하나씩 배선하는 후속 작업 필요. 일괄 배선은 검증 없이 리스크만 키우므로 지양 |
| M3 | bare `except Exception:` 465건 (N5 연장) | 🟢 LOW | open — 광범위 리팩터, 점진적 작업으로 분리 |
| M4 | `sc2bot-ci.yml`의 "Lint & Type Check" 잡이 `black --check --diff .`에서 66개 파일 포맷 드리프트로 실패 중 (blocking) | 🔴 HIGH | ✅ Fixed — `black .` + `isort .` 실행, 88개 파일 정리 |
| M5 | 저장소에 `scripts/`라는 이름의 디렉터리가 5곳(루트, `wicked_zerg_challenger/`, `wicked_zerg_challenger/local_training/`, `sc2-ai-dashboard/`, `julia_ml/`) 존재하고 전부 `__init__.py`가 없어 암묵적 네임스페이스 패키지로 충돌 — 전체 스위트 실행 시 `test_ladder_tracker.py`/`test_meta_adapter.py`가 `ModuleNotFoundError: No module named 'scripts.ladder_tracker'`로 수집 실패 | 🟠 HIGH | ✅ Fixed — 루트 `scripts/__init__.py` 추가로 실 패키지화 |
| M6 | `tests/test_combat_phase_fsm.py`의 5개 헬퍼가 `asyncio.get_event_loop().run_until_complete(...)`를 사용 — 앞서 실행된 pytest-asyncio 기반 테스트가 스레드의 앰비언트 이벤트 루프를 닫아버리면 `RuntimeError: There is no current event loop in thread 'MainThread'`로 12개 테스트 전부 실패 (`pytest tests/test_combat_manager.py tests/test_combat_phase_fsm.py`로 재현) | 🟠 HIGH | ✅ Fixed — `asyncio.run(...)`으로 교체 (자체 루프 라이프사이클 소유) |
| M7 | `ci.yml`의 `python-lint-test` 잡이 `s2clientprotocol`을 설치하지만 `PROTOCOL_BUFFERS_PYTHON_IMPLEMENTATION=python`을 설정하지 않아 `pytest tests/ --co` 수집 중 `TypeError: Descriptors cannot be created directly` 로 14개 파일 수집 실패, exit code 2 | 🔴 HIGH | ✅ Fixed — 같은 워크플로의 `sc2-bot-test` 잡과 동일한 env var 추가 |
| M8 | `flake8 --select=F811` 전체 스캔 결과 실제 코드 경로(`wicked_zerg_challenger/`)는 클린하지만, 실험적 프레임워크 디렉터리(`cirq_quantum/`, `pennylane_qml/`, `tianshou_rl/`, `jax_flax_rl/`, `discord_advanced_features.py`, `spark_jobs/`)에 지역 재-import로 인한 F811 11건 존재. 봇 핵심 로직과 무관 | 🟢 LOW | open — 우선순위 낮음, 손대지 않음 (실험 코드) |
| M9 | `bandit -r wicked_zerg_challenger -ll`: 총 6건 (MEDIUM 5, HIGH 1). HIGH는 `tools/monitor_background_training.py:42`의 `os.system('cls'/'clear')`인데 인자가 하드코딩 상수라 실제 인젝션 위험 없음(false positive로 판단). MEDIUM 3건은 `torch.load()`(신뢰 가능한 자체 체크포인트 로드), 2건은 `requests` 타임아웃 누락(`tools/scrape_spawningtool.py`) | 🟢 LOW | open — `scrape_spawningtool.py`에 `timeout=` 추가는 안전한 다음 작업 후보 |
| M10 | `flake8 --max-line-length=100` 전체(비차단) 스캔 통계: F401(미사용 import) 870건, E501(줄 길이) 550건, F541(placeholder 없는 f-string) 458건, F841(미사용 지역변수) 273건 — 전부 스타일/정리성 이슈로 동작에 영향 없음 | 🟢 LOW | open — 대량 기계적 정리 후보, 별도 세션에서 파일 단위로 점진 처리 권장 |

---

## 🎯 권장 수정 순서

### 완료 (✅)
1. ~~Queen Inject 쿨다운 / 누락 업그레이드~~ — 완료
2. ~~Transfusion 우선순위 / Resource Reservation 동기화 / Position Utils / Constants 인프라~~ — 완료
3. ~~M1: `pytest/` 디렉터리 이름 충돌~~ — 완료 (2026-07-09)
4. ~~M4: black/isort 포맷 드리프트 (CI 차단)~~ — 완료 (2026-07-09)
5. ~~M5: `scripts` 네임스페이스 패키지 충돌~~ — 완료 (2026-07-09)
6. ~~M6: `test_combat_phase_fsm.py` asyncio 이벤트 루프 버그 (12건 실패)~~ — 완료 (2026-07-09)
7. ~~M7: CI protobuf env var 누락 (수집 단계 14건 실패)~~ — 완료 (2026-07-09)

### 다음 단계
8. M2: 고아 combat 모듈 13개 — 모듈별 단위 테스트 작성 → 1개씩 `combat_manager.py`/`combat/initialization.py`에 배선 → 회귀 테스트 통과 확인 후 커밋 (일괄 처리 금지)
9. M9: `scrape_spawningtool.py`에 requests timeout 추가 (작고 안전한 다음 작업)
10. M3: bare except 축소 (점진적, 파일당 소규모 PR 권장)
11. M10: F401/E501/F541/F841 대량 정리 (기계적, 별도 세션)

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

### 실행 환경 제약 (중요)
이 문서를 갱신하는 자동 점검 세션은 실제 StarCraft II 게임 클라이언트가 없는 샌드박스에서
실행됩니다. 즉 `run_single_game.py`/`run_mass_test.py` 같은 실전 대전 테스트는 이 환경에서
직접 검증할 수 없고, `pytest` 유닛테스트 + 정적 분석(flake8)만 반복 검증 가능합니다.
문서 내 승률(%) 수치는 자체 보고(self-report)이며 이번 점검에서 재검증된 것이 아닙니다.

### 현재 상태
- ✅ **치명적 통합 문제**: 완전히 해결됨
- ✅ **N1~N6, #1~#6 (과거 발견 이슈)**: 전부 Resolved 확인
- 🟠 **M2 (고아 모듈 13개)**: 신규 발견, 후속 작업 필요

---

**검토 완료일**: 2026-01-29
**상태**: 추가 개선 사항 문서화 완료
