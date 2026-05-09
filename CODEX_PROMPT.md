# Codex 마스터 프롬프트 — WickedZergBotPro 구현 & 테스트

> 이 파일은 Codex에게 전달하는 실행 지시서입니다.
> 세 계획서(ROADMAP.md, STRATEGY_PLAN.md, INFRA_PLAN.md)의 구현과 테스트를 자율적으로 수행합니다.

---

## 1. 프로젝트 개요

- **프로젝트**: WickedZergBotPro (StarCraft II 저그 봇)
- **프레임워크**: python-sc2 (burnysc2>=5.0.0)
- **목표**: Medium AI 승률 90%+, AI Arena 출전
- **현재 상태**: 342/342 테스트 통과, 추정 승률 45~50%

---

## 2. 실행 순서

아래 순서대로 작업하라. 각 Sprint/Phase 완료 시 반드시 테스트를 실행하고, 실패하면 수정 후 다음으로 넘어가라.

```
ROADMAP.md Sprint 1 (긴급 수정)
  → 테스트 실행
ROADMAP.md Sprint 2 (정찰 & 인텔)
  → 테스트 실행
STRATEGY_PLAN.md Phase 1 (ZvT 전략)
  → 테스트 실행
ROADMAP.md Sprint 3 (경제 & 매크로)
  → 테스트 실행
STRATEGY_PLAN.md Phase 2 (ZvP 전략)
  → 테스트 실행
ROADMAP.md Sprint 4 (전투 & 마이크로)
  → 테스트 실행
STRATEGY_PLAN.md Phase 3 (ZvZ 전략)
  → 테스트 실행
STRATEGY_PLAN.md Phase 4 (공통 전략 시스템)
  → 테스트 실행
ROADMAP.md Sprint 5 (방어 체계)
  → 테스트 실행
ROADMAP.md Sprint 6 (RL 실전 투입)
  → 테스트 실행
ROADMAP.md Sprint 7 (아키텍처 리팩토링)
  → 전체 회귀 테스트 실행

--- INFRA_PLAN.md 통합 ---

INFRA_PLAN.md Part 1 (성능 최적화)
  P1.1 PerformanceProfiler → P1.2 DistanceCache → P1.3 FrameSkipManager
  → 테스트 실행 (프로파일러/캐시/프레임스킵 단위테스트)
INFRA_PLAN.md Part 1 (Rust 가속)
  P1.4 Rust 래퍼 → P1.5 신규 Rust 함수 → P1.6 MemoryMonitor
  → 테스트 실행 (Rust fallback 검증, 메모리 누수 테스트)
INFRA_PLAN.md Part 2 (RL 파이프라인)
  P2.1 PPO+GAE → P2.2 관측/행동 공간 → P2.3 리플레이 파이프라인
  → 테스트 실행 (네트워크 출력 shape, 보상 신호 검증)
INFRA_PLAN.md Part 2 (자가대전)
  P2.4 SelfPlayLeague → P2.5 run_full_training.py
  → 테스트 실행 (ELO 계산, 매치메이킹 범위 검증)
INFRA_PLAN.md Part 3 (AI Arena 운영)
  P3.1 사전검증 → P3.2 LadderTracker → P3.3 MetaAdapter
  → 테스트 실행 (패키지 검증, 전적 분석 검증)
INFRA_PLAN.md Part 4 (모니터링 & 대시보드)
  P4.1 TelemetryCollector → P4.2 PostGameReport
  → P4.3 DashboardServer → P4.4 CI/CD 자동화
  → 테스트 실행 (텔레메트리 수집, HTML 리포트 생성 검증)

--- 최종 통합 ---

ROADMAP.md Sprint 8 + STRATEGY_PLAN.md Phase 5 (QA & 배포)
  → 전체 회귀 테스트 + INFRA 통합 검증
  → 최종 검증
```

---

## 3. 테스트 실행 방법

### 3.1 유닛 테스트 (매 Task 완료 후 실행)

```bash
# SC2 봇 테스트 (핵심 — 반드시 통과해야 함)
cd E:\GitHub\Swarm-control-in-sc2bot
pytest wicked_zerg_challenger/tests/ -v --tb=short

# 전체 프로젝트 테스트
pytest tests/ -v --tb=short

# 특정 파일만 테스트
pytest wicked_zerg_challenger/tests/test_combat_manager.py -v
pytest wicked_zerg_challenger/tests/test_strategy_manager_v2.py -v
pytest wicked_zerg_challenger/tests/test_economy_manager.py -v
pytest wicked_zerg_challenger/tests/test_intel_manager.py -v
pytest wicked_zerg_challenger/tests/test_blackboard.py -v
pytest wicked_zerg_challenger/tests/test_build_order_system.py -v
```

### 3.2 컴파일 검증 (코드 수정 후 즉시 실행)

```bash
# 수정한 파일의 문법 확인
python -m py_compile wicked_zerg_challenger/combat_manager.py
python -m py_compile wicked_zerg_challenger/strategy_manager.py
python -m py_compile wicked_zerg_challenger/economy_manager.py
python -m py_compile wicked_zerg_challenger/scouting_system.py
python -m py_compile wicked_zerg_challenger/intel_manager.py

# 전체 핵심 파일 일괄 컴파일 체크
python -c "
import py_compile, glob, sys
files = glob.glob('wicked_zerg_challenger/**/*.py', recursive=True)
errors = []
for f in files:
    try:
        py_compile.compile(f, doraise=True)
    except py_compile.PyCompileError as e:
        errors.append(str(e))
if errors:
    print(f'COMPILE ERRORS ({len(errors)}):')
    for e in errors:
        print(f'  {e}')
    sys.exit(1)
else:
    print(f'All {len(files)} files compiled successfully')
"
```

### 3.3 통합 검증 (Sprint 완료 후 실행)

```bash
# Phase 50 통합 검증
python phase50_integrated_validation.py --skip-package

# Arena 패키지 빌드 검증 (Sprint 8에서만)
python create_arena_package.py --output-dir dist --name test_package.zip --no-open
```

### 3.4 신규 테스트 작성 가이드

새 기능을 구현할 때 반드시 해당 테스트도 함께 작성하라.

**테스트 파일 위치:**
- SC2 봇 관련: `wicked_zerg_challenger/tests/test_<모듈명>.py`
- 기타: `tests/test_<모듈명>.py`

**테스트 작성 패턴:**

```python
# wicked_zerg_challenger/tests/test_<새기능>.py
import unittest
from unittest.mock import MagicMock, patch, AsyncMock

class TestNewFeature(unittest.TestCase):
    def setUp(self):
        """공통 Mock 객체 설정"""
        self.bot = MagicMock()
        self.bot.time = 120.0
        self.bot.supply_used = 40
        self.bot.minerals = 500
        self.bot.vespene = 200
        self.bot.workers = MagicMock()
        self.bot.workers.amount = 30
        self.bot.townhalls = MagicMock()
        self.bot.townhalls.ready = MagicMock()
        self.bot.units = MagicMock()
        self.bot.enemy_units = MagicMock()
        self.bot.enemy_race = MagicMock()
        self.bot.start_location = MagicMock()
        self.bot.enemy_start_locations = [MagicMock()]
        
        # Blackboard Mock
        self.blackboard = MagicMock()
        self.blackboard.get = MagicMock(return_value=None)
        self.blackboard.set = MagicMock()
    
    def test_feature_basic(self):
        """기본 동작 테스트"""
        # Arrange
        # Act
        # Assert
        pass
    
    def test_feature_edge_case(self):
        """엣지 케이스 테스트"""
        pass

if __name__ == "__main__":
    unittest.main()
```

**Mock 유닛 생성 헬퍼:**

```python
def create_mock_unit(unit_type, position=(50, 50), health=100, health_max=100, is_idle=True, tag=1):
    """SC2 유닛 Mock 생성"""
    unit = MagicMock()
    unit.type_id = unit_type
    unit.position = MagicMock()
    unit.position.x = position[0]
    unit.position.y = position[1]
    unit.position.towards = MagicMock(return_value=MagicMock())
    unit.position.distance_to = MagicMock(return_value=10.0)
    unit.distance_to = MagicMock(return_value=10.0)
    unit.health = health
    unit.health_max = health_max
    unit.health_percentage = health / health_max if health_max > 0 else 0
    unit.shield = 0
    unit.shield_max = 0
    unit.is_idle = is_idle
    unit.is_attacking = False
    unit.is_moving = False
    unit.tag = tag
    unit.can_attack = True
    unit.is_burrowed = False
    unit.attack = MagicMock()
    unit.move = MagicMock()
    unit.gather = MagicMock()
    return unit

def create_mock_units(unit_type, count, base_position=(50, 50)):
    """여러 Mock 유닛 생성"""
    from unittest.mock import MagicMock
    units = MagicMock()
    unit_list = []
    for i in range(count):
        pos = (base_position[0] + i, base_position[1] + i)
        unit_list.append(create_mock_unit(unit_type, position=pos, tag=i+1))
    units.__iter__ = MagicMock(return_value=iter(unit_list))
    units.__len__ = MagicMock(return_value=count)
    units.amount = count
    units.filter = MagicMock(return_value=units)
    units.closer_than = MagicMock(return_value=units)
    units.closest_to = MagicMock(return_value=unit_list[0] if unit_list else None)
    units.center = MagicMock()
    units.idle = units
    units.ready = units
    units.random = unit_list[0] if unit_list else None
    units.random_or = MagicMock(return_value=unit_list[0] if unit_list else MagicMock())
    units.take = MagicMock(return_value=unit_list[:min(3, count)])
    units.closest_n_units = MagicMock(return_value=unit_list[:min(4, count)])
    return units
```

---

## 4. 각 Task별 테스트 체크리스트

### ROADMAP Sprint 1 테스트

| Task | 컴파일 체크 | 유닛 테스트 | 확인 사항 |
|------|------------|------------|----------|
| 1.1 인코딩 제거 | `py_compile` 전체 | 기존 342개 통과 | 비ASCII 문자 0개 |
| 1.2 일꾼 방어 | combat_manager.py | test_worker_harassment_defense.py 신규 | 위협 감지→풀→복귀 |
| 1.3 견제 도달 | strategy_manager.py, combat_manager.py | test_harassment_system.py 신규 | 도달+킬카운트+복귀 |
| 1.4 1분 멀티 | economy_manager.py | test_economy_manager.py 보강 | 확장 시점 로그 |

### ROADMAP Sprint 2 테스트

| Task | 컴파일 체크 | 유닛 테스트 | 확인 사항 |
|------|------------|------------|----------|
| 2.1 오버로드 정찰 | scouting_system.py | test_scouting_system.py 보강 | 15초 주기 |
| 2.2 저글링 순찰 | scouting_system.py | test_scouting_system.py 보강 | 웨이포인트 순환 |
| 2.3 빌드 인식 확장 | intel_manager.py | test_intel_manager.py 보강 | 25개 패턴 |
| 2.4 공중 경보 | intel_manager.py | test_intel_manager.py 보강 | 플래그 설정 |
| 2.5 은폐 탐지 | scouting_system.py | test_scouting_system.py 보강 | 오버시어 배치 |

### STRATEGY_PLAN Phase 1~3 테스트

| Task | 컴파일 체크 | 유닛 테스트 | 확인 사항 |
|------|------------|------------|----------|
| ZvT 빌드 3종 | build_order_system.py | test_build_order_system.py 보강 | 빌드 선택 로직 |
| ZvT 유닛 구성 | strategy_manager.py | test_strategy_manager_v2.py 보강 | 비율 합계 1.0 |
| ZvT 마이크로 | combat/micro_combat.py | test_zvt_micro.py 신규 | 탱크 서라운드/베인 |
| ZvP 빌드 3종 | build_order_system.py | test_build_order_system.py 보강 | 빌드 선택 로직 |
| ZvP 카운터 | strategy_manager.py | test_strategy_manager_v2.py 보강 | 5개 카운터 룰 |
| ZvP 마이크로 | combat/micro_combat.py | test_zvp_micro.py 신규 | 폭풍 회피 |
| ZvZ 빌드 3종 | build_order_system.py | test_build_order_system.py 보강 | 빌드 선택 로직 |
| ZvZ 마이크로 | combat/micro_combat.py | test_zvz_micro.py 신규 | 베인 컨트롤 |

### ROADMAP Sprint 7 (리팩토링) 회귀 테스트

```bash
# 리팩토링 후 반드시 전체 회귀 테스트
pytest wicked_zerg_challenger/tests/ -v --tb=short
pytest tests/ -v --tb=short

# 기존 342개 테스트가 모두 통과해야 함
# 실패하는 테스트가 있으면 리팩토링을 롤백하거나 수정
```

---

## 5. 테스트 작성 시 규칙

### 5.1 필수 규칙

1. **새 기능 = 새 테스트**: 모든 새 메서드/클래스에 대해 최소 2개 테스트 (정상 + 엣지)
2. **기존 테스트 보호**: 기존 342개 테스트를 절대 삭제하지 마라. 수정만 허용
3. **Mock 사용**: SC2 게임 실행 없이 테스트 가능하도록 Mock 사용
4. **독립 실행**: 각 테스트는 다른 테스트에 의존하지 않아야 함
5. **protobuf 호환**: SC2 테스트 파일 상단에 반드시 포함:
   ```python
   import os
   os.environ["PROTOCOL_BUFFERS_PYTHON_IMPLEMENTATION"] = "python"
   ```

### 5.2 테스트 네이밍 규칙

```python
# 파일명: test_<모듈명>.py 또는 test_<기능명>.py
# 클래스명: Test<기능명>
# 메서드명: test_<동작>_<조건>_<기대결과>

class TestWorkerHarassDefense:
    def test_respond_when_enemy_near_base(self):
        """적이 기지 근처에 있을 때 방어 응답"""
    
    def test_no_response_when_no_threat(self):
        """위협이 없을 때 응답하지 않음"""
    
    def test_workers_return_after_threat_gone(self):
        """위협 제거 후 일꾼 복귀"""
```

### 5.3 비율 검증 패턴

```python
def test_unit_composition_ratios_sum_to_one(self):
    """유닛 구성 비율의 합이 1.0인지 확인"""
    for phase, compositions in ZVT_COMPOSITION_TIMELINE.items():
        for scenario, ratios in compositions.items():
            total = sum(ratios.values())
            self.assertAlmostEqual(total, 1.0, places=2,
                msg=f"Phase {phase}, scenario {scenario}: ratios sum to {total}")
```

### 5.4 Blackboard 이벤트 검증 패턴

```python
def test_blackboard_event_published(self):
    """정찰 결과가 Blackboard에 기록되는지 확인"""
    self.blackboard.set.assert_called_with("enemy_base_scouted", True)

def test_strategy_reacts_to_blackboard(self):
    """Blackboard 이벤트에 전략이 반응하는지 확인"""
    self.blackboard.get.return_value = "bio"
    result = self.strategy._counter_terran_units()
    self.assertIn("baneling", result)
```

---

## 6. 환경 설정

### 6.1 의존성 설치

```bash
cd E:\GitHub\Swarm-control-in-sc2bot
pip install -r requirements.txt
pip install -r requirements-dev.txt
```

### 6.2 pytest 설정 확인

프로젝트 루트의 `pytest.ini`가 이미 설정되어 있음:
- testpaths = tests
- asyncio_mode = auto
- timeout = 60

SC2 봇 테스트는 별도 경로: `wicked_zerg_challenger/tests/`

### 6.3 환경 변수

```bash
set PROTOCOL_BUFFERS_PYTHON_IMPLEMENTATION=python
set DRY_RUN=true
set LOG_LEVEL=DEBUG
```

---

## 7. 코딩 규칙

### 7.1 python-sc2 주의사항

```python
# ❌ 절대 사용 금지
UnitTypeId.LURKER           # python-sc2에 존재하지 않음

# ✅ 올바른 사용
UnitTypeId.LURKERMP         # 러커의 올바른 ID

# ❌ 위험한 패턴
power = len(units)          # 단순 유닛 수 비교

# ✅ 올바른 패턴
power = sum(u.health + u.shield for u in units)  # HP 가중 전투력

# ❌ 0 나눗셈 위험
ratio = unit.health / unit.health_max

# ✅ 안전한 패턴
ratio = unit.health / unit.health_max if unit.health_max > 0 else 0

# ❌ 직접 명령
unit.attack(target)

# ✅ bot.do() 래핑 (에러 방지)
self.bot.do(unit.attack(target))
# 또는 최신 API에서는 직접 호출 가능하나 try/except 래핑 권장
```

### 7.2 성능 제약

```python
# AI Arena 제한: 프레임당 320ms 이내
# 무거운 계산은 프레임 스킵 적용:
if iteration % 5 != 0:  # 5프레임마다 실행
    return

# 거리 계산 캐싱:
# 동일 프레임에서 같은 거리 계산 반복 금지
# utils/distance_cache.py 활용
```

### 7.3 로깅 규칙

```python
import logging
logger = logging.getLogger(__name__)

# ❌ print 사용 금지 (stdout 스팸)
print(f"Debug: {value}")

# ✅ logger 사용
logger.info(f"[EXPANSION] First expansion at {self.bot.time:.1f}s")
logger.debug(f"[COMBAT] Army power ratio: {ratio:.2f}")
logger.warning(f"[FLOAT] Minerals floating: {self.bot.minerals}")
```

---

## 8. 작업 완료 기준

각 Sprint/Phase가 "완료"로 인정되려면:

1. **컴파일 통과**: 수정한 모든 .py 파일이 `py_compile` 통과
2. **기존 테스트 통과**: `pytest wicked_zerg_challenger/tests/ -v` 전체 통과 (342개+)
3. **신규 테스트 통과**: 새로 작성한 테스트 전체 통과
4. **전체 테스트 통과**: `pytest tests/ -v` 전체 통과
5. **로그 없는 에러**: 런타임 에러/워닝 없음

### 최종 완료 기준 (Sprint 8)

```bash
# 1. 컴파일 검증
python -c "
import py_compile, glob
files = glob.glob('wicked_zerg_challenger/**/*.py', recursive=True)
for f in files:
    py_compile.compile(f, doraise=True)
print(f'All {len(files)} files OK')
"

# 2. 유닛 테스트 전체 통과
pytest wicked_zerg_challenger/tests/ -v --tb=short
pytest tests/ -v --tb=short

# 3. 통합 검증
python phase50_integrated_validation.py --skip-package

# 4. Arena 패키지 빌드
python create_arena_package.py --output-dir dist --no-open

# 5. 결과 리포트
# 모든 테스트 통과 + 패키지 빌드 성공이면 완료
```

---

## 9. 계획서 참조

구현할 내용의 상세 사양:

- **ROADMAP.md**: 시스템별 개선 (8 Sprint, 32 Task)
  - Sprint 1: 긴급 수정 (인코딩, 일꾼 방어, 견제, 멀티 타이밍)
  - Sprint 2: 정찰 & 인텔
  - Sprint 3: 경제 & 매크로
  - Sprint 4: 전투 & 마이크로
  - Sprint 5: 방어 체계
  - Sprint 6: RL 실전 투입
  - Sprint 7: 아키텍처 리팩토링
  - Sprint 8: QA & 배포

- **STRATEGY_PLAN.md**: 매치업별 전략 (5 Phase, 18 Task)
  - Phase 1: ZvT (빌드오더 3종, 유닛 구성, 마이크로, 정찰)
  - Phase 2: ZvP (빌드오더 3종, 카운터 강화, 마이크로, 정찰)
  - Phase 3: ZvZ (빌드오더 3종, 유닛 구성, 베인 컨트롤, 정찰)
  - Phase 4: 공통 시스템 (빌드 전환, 업그레이드, 타이밍 어택, 긴급 대응)
  - Phase 5: 종합 테스트 매트릭스

- **INFRA_PLAN.md**: 인프라 & 성능 (4 Part, 18+ Task)
  - Part 1: 성능 최적화 (PerformanceProfiler, DistanceCache, FrameSkipManager, Rust 가속, MemoryMonitor)
  - Part 2: RL 파이프라인 (PPO+GAE, 관측/행동 공간, 리플레이 파이프라인, SelfPlayLeague)
  - Part 3: AI Arena 운영 (사전검증, LadderTracker, MetaAdapter)
  - Part 4: 모니터링 & 대시보드 (TelemetryCollector, PostGameReport, DashboardServer, CI/CD)

세 파일을 읽고 각 Task의 파일 경로, 코드 예시, 검증 방법을 따라 구현하라.

---

## 10. INFRA_PLAN.md 테스트 가이드

### 10.1 Part 1 (성능) 테스트

```bash
# P1.1 PerformanceProfiler
pytest wicked_zerg_challenger/tests/test_performance_profiler.py -v

# P1.2 DistanceCache
pytest wicked_zerg_challenger/tests/test_distance_cache.py -v

# P1.3 FrameSkipManager
pytest wicked_zerg_challenger/tests/test_frame_skip_manager.py -v

# P1.4-P1.5 Rust 가속 (fallback 검증 필수)
pytest wicked_zerg_challenger/tests/test_rust_accel.py -v
python -c "
try:
    from rust_accel import find_unit_clusters
    print('Rust: OK')
except ImportError:
    print('Rust: FALLBACK (Python 사용)')
"

# P1.6 MemoryMonitor
pytest wicked_zerg_challenger/tests/test_memory_monitor.py -v
```

### 10.2 Part 2 (RL) 테스트

```bash
# P2.1 ActorCriticNetwork
pytest wicked_zerg_challenger/tests/test_actor_critic.py -v
python -c "
import torch
from wicked_zerg_challenger.local_training.hierarchical_rl.improved_hierarchical_rl import ActorCriticNetwork
net = ActorCriticNetwork(obs_dim=16, action_dim=7)
obs = torch.randn(1, 16)
policy, value = net(obs)
assert policy.shape == (1, 7), f'Policy shape mismatch: {policy.shape}'
assert value.shape == (1, 1), f'Value shape mismatch: {value.shape}'
print('ActorCriticNetwork: OK')
"

# P2.2 관측/행동 공간
pytest wicked_zerg_challenger/tests/test_observation_space.py -v

# P2.3 ReplayToTrainingPipeline
pytest wicked_zerg_challenger/tests/test_replay_pipeline.py -v

# P2.4 SelfPlayLeague
pytest wicked_zerg_challenger/tests/test_self_play_league.py -v
python -c "
from wicked_zerg_challenger.local_training.self_play_league import SelfPlayLeague
league = SelfPlayLeague(max_players=20)
league.add_player('bot_v1', elo=1000)
league.add_player('bot_v2', elo=1050)
opp = league.get_opponent('bot_v1')
assert opp is not None, 'Matchmaking failed'
print(f'SelfPlayLeague: Matched vs {opp}')
"
```

### 10.3 Part 3 (AI Arena) 테스트

```bash
# P3.1 사전검증
pytest wicked_zerg_challenger/tests/test_arena_preflight.py -v
python -c "
from wicked_zerg_challenger.arena.preflight_validator import PreflightValidator
v = PreflightValidator('.')
result = v.validate()
print(f'Preflight: {\"PASS\" if result.passed else \"FAIL\"} ({len(result.errors)} errors)')
"

# P3.2 LadderTracker
pytest wicked_zerg_challenger/tests/test_ladder_tracker.py -v

# P3.3 MetaAdapter
pytest wicked_zerg_challenger/tests/test_meta_adapter.py -v
```

### 10.4 Part 4 (모니터링) 테스트

```bash
# P4.1 TelemetryCollector
pytest wicked_zerg_challenger/tests/test_telemetry_collector.py -v

# P4.2 PostGameReport
pytest wicked_zerg_challenger/tests/test_post_game_report.py -v

# P4.3 DashboardServer
pytest wicked_zerg_challenger/tests/test_dashboard_server.py -v
python -c "
from wicked_zerg_challenger.monitoring.dashboard import DashboardServer
server = DashboardServer(data_dir='test_data')
html = server.generate_report()
assert '<html>' in html.lower(), 'HTML report generation failed'
print(f'Dashboard: Generated {len(html)} bytes HTML')
"
```

---

## 11. 실행 명령어 (Codex에 전달)

```
ROADMAP.md, STRATEGY_PLAN.md, INFRA_PLAN.md, CODEX_PROMPT.md를 읽어라.
CODEX_PROMPT.md의 섹션 2 "실행 순서"를 따라 Sprint 1부터 구현을 시작해라.
각 Task 구현 후:
  1. py_compile로 수정 파일 컴파일 체크
  2. 해당 모듈의 유닛 테스트 실행
  3. 신규 기능이면 테스트 파일도 함께 작성
  4. 전체 테스트 통과 확인 후 다음 Task로 이동
INFRA_PLAN.md 작업은 ROADMAP Sprint 7 이후에 시작하라.
  - Part 1~4 순서대로 구현, 각 Part 완료 후 섹션 10의 테스트 실행
  - Rust 함수는 fallback 패턴 필수 (ImportError 시 Python 대체)
  - RL 네트워크는 출력 shape 검증 필수
실패하는 테스트가 있으면 수정하고, 수정 후에도 실패하면 해당 Task를 스킵하고 이유를 기록해라.
```
