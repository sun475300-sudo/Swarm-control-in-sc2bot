# 🔍 Remaining Issues - 추가 검토 결과

## 📋 개요

통합 문제 해결 후 발견된 추가 개선 사항들입니다.

**Last refreshed:** 2026-07-14 (자동 점검 사이클 — 테스트 → 코드 검사 → 개선 → 커밋/푸시)

---

## ✅ 2026-07-14 점검 사이클 결과

전체 테스트(502 tests) 재실행 + `flake8 --select=F811,F821,F401,F841`로 `wicked_zerg_challenger/` 전체 재스캔.

### 새로 발견 & 수정: 테스트 스위트 event-loop 버그

`tests/test_combat_phase_fsm.py`의 5개 헬퍼(`_run`)가 `asyncio.get_event_loop().run_until_complete(...)`를
사용하고 있어, 전체 스위트를 실행할 때 다른 비동기 테스트가 먼저 이벤트 루프를 소비/종료시키면
`RuntimeError: There is no current event loop in thread 'MainThread'`로 12개 테스트가 실패했음
(단독 실행 시엔 통과 — 순서 의존적 flaky 실패). `asyncio.run(...)`으로 교체하여 루프 생성/정리를
각 호출에 자기완결적으로 만듦. **502 passed, 0 failed, 14 skipped**로 회귀 확인 완료.

### 이전 N1–N4 (F811 재정의) — 이미 해결됨, 문서만 stale했음

재스캔 결과 `wicked_zerg_challenger/` 전체에서 **F811(재정의)/F821(미정의 이름) 0건**. 아래 항목은
이전 사이클(PR #218 근방)에서 이미 코드에 반영된 상태였고, 이 문서만 갱신되지 않았던 것으로 확인:

| ID | 설명 | 상태 |
|----|------|------|
| N1 | `OpponentModeling.on_step` 중복 정의 | ✅ 확인됨 — `opponent_modeling.py`에 `on_step` 정의 1개만 존재 |
| N2 | `EconomyManager._prevent_resource_banking` / `_reduce_gas_workers` 재정의 | ✅ 확인됨 — 각 1개 정의만 존재 |
| N3 | `combat_manager._find_harass_target` 재정의 | ✅ 확인됨 — 1개 정의만 존재 |
| N4 | `production_resilience.build_terran_counters` 재정의 | ✅ 확인됨 — 1개 정의만 존재 |
| N5 | bare `except Exception:` 다수 (468건) | 🟢 LOW — 대부분 의도된 방어적 코드(그레이스풀 디그레이드), 일괄 변경은 비권장 |
| N6 | F841 unused local variables (130건, 주로 presentation/시각화 코드) | 🟢 LOW — 영향 작음, 후속 사이클로 이월 |

### 이전 Issue #3 (Transfusion 우선순위) — 이미 해결됨

`wicked_zerg_challenger/economy/queen_transfusion_manager.py`에 `QueenTransfusionManager`로 완전
구현되어 있고 (`HEAL_PRIORITY` 13종 우선순위, `CANNOT_HEAL` 13종 제외 목록, 쿨다운/중복방지/오버힐
방지 포함), `bot_step_integration.py`에서 실전 `on_step` 경로에 연동되어 활성 사용 중임을 확인.
문서 제안보다 더 정교하게 이미 구현됨 — 별도 작업 불필요.

### 신규 발견: `utils/position_utils.py`가 어디서도 import되지 않음 (dead code)

Issue #5(포지션 계산 중복)를 해결하기 위해 만들어진 `get_center_position` 등 유틸리티 함수가 존재하지만
실제로는 어떤 파일에서도 import되지 않고 있음. 한편 중심좌표 계산이 중복된 9개 파일 중 다수
(`combat/expansion_defense.py`, `combat/combat_execution.py`, `combat/infestor_tactics.py`,
`combat/micro_combat.py`, `combat_manager.py`)는 `from sc2.position import Point2`를 **try/except로
가드**하여 sc2 미설치 환경에서도 임포트 가능하게 만든 의도적 설계인 반면, `position_utils.py`는
모듈 최상단에서 무조건 `from sc2.position import Point2`를 수행함 — 이 상태로 그대로 갖다붙이면
graceful-degradation 특성이 깨짐. 단순 치환은 **비권장**. 후속 작업 시 `position_utils.py`도
동일한 try/except 가드를 적용한 뒤, 무조건 임포트 파일(`battle_preparation_system.py`,
`idle_unit_manager.py`, `combat_phase_controller.py`, `micro_controller.py`)부터 우선 연동 권장.

### 신규 발견: 최상위 기획 문서가 실제 코드 상태보다 크게 뒤처짐

`TODO.md`(2026-01-25 작성)와 `ROADMAP.md`의 Sprint 1 항목(일꾼 괴롭힘 방어, 견제 유닛 복귀 로직,
인코딩 에러 제거)을 검증한 결과 **전부 이미 코드에 구현되어 있음**
(`combat_manager.py`의 `respond_to_worker_harassment` / `_return_worker_harassment_defenders` /
`harass_kill_count`, `early_defense_system.py`의 비ASCII 문자 0건). 두 문서 모두 실제 진행 상황을
반영하도록 갱신 필요 — 다음 사이클에서 `TODO.md`를 최신 상태로 재작성하거나 `docs/history/`로 이동
권장 (STATUS.md의 P1.5 계획과 일치).

검증 방법: PR 분리 없이 이번 커밋에 테스트 픽스 + 문서 갱신만 포함 (동작 변경 없음, 502/502 테스트 통과 확인).

### 신규 발견: CI "Lint & Type Check" 잡이 `main`에서부터 이미 깨져 있음 (black 포맷 66개 파일)

PR #457 CI에서 `black --check --diff .` 스텝이 실패로 나왔음. `main` 브랜치에서 동일 명령을 직접
실행해본 결과 **이 PR과 무관하게 66개 파일이 이미 black 미준수 상태**임을 확인 (`strategy_manager.py`,
`visuals/generate_*.py`, 다수의 `wicked_zerg_challenger/tests/*` 등). 이 PR에서 실제로 수정한
`tests/test_combat_phase_fsm.py`는 black/isort 적용해서 통과시켰지만, 잡 자체는 저장소 전체를
검사하므로 계속 실패로 표시될 것 — **이 PR이 유발한 문제가 아님**.

**우선순위**: 🟠 HIGH (모든 PR의 CI를 빨갛게 만들어 신호 노이즈 유발) — 단, 66개 파일 일괄 재포맷은
이번 PR과 무관한 대형 diff이므로 **별도 PR로 분리 권장** (기존 커밋 `940f521`도 "PR이 건드린 파일만"
포맷하는 동일한 관례를 따랐음). 다음 사이클에서 `black . && isort .` 전체 실행 → 전체 테스트 통과
확인 → 순수 포맷팅만 담은 단독 PR로 제출 권장.

### ✅ 수정: "Python 린트 & 테스트" CI 잡의 protobuf 충돌 (pre-existing, main에서도 5월부터 실패 중)

`.github/workflows/ci.yml`의 "pytest 실행 (전체)" 스텝이 `TypeError: Descriptors cannot be created
directly` 로 14개 테스트 파일 collection 자체가 실패하고 있었음. `main`의 최근 워크플로 실행 이력을
확인한 결과 **이 PR과 무관하게 최소 2026-05-28부터 반복적으로 실패 중**이었음 (2026-06-25 최신 완료
실행도 failure).

원인: 이 잡은 `requirements.txt` 전체(`google-generativeai` 등 포함)를 설치하는데, 이때 딸려오는
protobuf 버전이 `s2clientprotocol`(burnysc2 의존성)이 번들한 구버전 `_pb2.py`와 호환되지 않음.
반면 `burnysc2`만 좁게 설치하는 "SC2 봇 검증 & 테스트" 잡은 이 문제가 없어 통과함 — 즉 SC2 관련
패키지가 아니라 `requirements.txt`의 다른 서비스(genai/discord/crypto) 의존성이 원인.

**조치**: `requirements.txt`의 버전 고정 대신(다른 서비스에 영향 줄 위험), 해당 CI 스텝에만
`PROTOCOL_BUFFERS_PYTHON_IMPLEMENTATION=python` env var 추가 — protobuf 공식 문서가 안내하는
표준 워크어라운드로, 의존성 버전은 그대로 두고 순수 Python 구현으로 폴백시킴. 로컬에서 동일 env var로
전체 502개 테스트 재검증 통과 확인.

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
