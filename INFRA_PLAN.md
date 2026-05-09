# WickedZergBotPro 인프라 계획서

> 4개 영역: 성능 최적화 & Rust 가속 / RL 학습 파이프라인 / AI Arena 래더 운영 / 모니터링 & 대시보드
> 선행 문서: ROADMAP.md (시스템 개선), STRATEGY_PLAN.md (매치업 전략)
> 현재 상태: Rust 8함수 구현, RL 부분 완성, 모니터링 스텁만 존재, Arena 패키징 동작

---

## 프로젝트 컨텍스트

### 현재 인프라 상태 요약

| 컴포넌트 | 상태 | 설명 |
|---------|------|------|
| Rust 가속 | 80% | 8개 함수 구현, Rayon 병렬화. 봇 루프 미연동 |
| OpenCL 가속 | 10% | nearest_point만 구현, 스레드 비안전 |
| RL 학습 | 40% | PolicyNetwork 존재, 실전 미연동, Value Network 없음 |
| 모니터링 | 5% | dashboard.py/telemetry.py 전부 stub(빈 껍데기) |
| Arena 패키징 | 90% | ZIP 생성 동작, pre-flight 검증 없음 |
| 리플레이 분석 | 30% | 피드백 생성 가능, sc2reader 미연동, 학습 미연결 |
| 성능 프로파일러 | 25% | 데코레이터 존재, 봇 루프 미연동 |
| CI/CD | 75% | 9개 Job 동작, K8s 매니페스트 누락 |

### 주의사항
- `UnitTypeId.LURKERMP` 사용 (LURKER 아님)
- AI Arena 320ms/step 제한
- Rust 빌드: `maturin develop --release` (PyO3)
- protobuf 환경변수: `PROTOCOL_BUFFERS_PYTHON_IMPLEMENTATION=python`

---

## Part 1: 성능 최적화 & Rust 가속

### Task P1.1: 프레임 성능 프로파일러 봇 루프 연동

**파일:**
- `wicked_zerg_challenger/utils/performance_profiler.py` (기존)
- `wicked_zerg_challenger/bot.py` 또는 `bot_step_integration.py`

**현재:** PerformanceProfiler 클래스 존재하지만 봇에 미연동

**구현 지시:**
```python
# bot_step_integration.py에 프로파일러 통합
from utils.performance_profiler import PerformanceProfiler

class BotStepIntegration:
    def __init__(self):
        self.profiler = PerformanceProfiler()
        self.frame_times = []
    
    async def on_step(self, iteration):
        frame_start = time.perf_counter()
        
        # 각 매니저를 프로파일링 래핑
        with self.profiler.measure("strategy_manager"):
            await self.strategy_manager.execute(iteration)
        
        with self.profiler.measure("economy_manager"):
            await self.economy_manager.execute(iteration)
        
        with self.profiler.measure("combat_manager"):
            await self.combat_manager.execute(iteration)
        
        with self.profiler.measure("scouting_system"):
            await self.scouting_system.execute(iteration)
        
        frame_time = (time.perf_counter() - frame_start) * 1000  # ms
        self.frame_times.append(frame_time)
        
        # 320ms 경고
        if frame_time > 250:
            logger.warning(f"[PERF] Frame {iteration} took {frame_time:.1f}ms (limit: 320ms)")
        
        # 100프레임마다 성능 리포트
        if iteration % 100 == 0 and iteration > 0:
            self._log_performance_summary(iteration)
    
    def _log_performance_summary(self, iteration):
        recent = self.frame_times[-100:]
        avg = sum(recent) / len(recent)
        p95 = sorted(recent)[int(len(recent) * 0.95)]
        p99 = sorted(recent)[int(len(recent) * 0.99)]
        bottlenecks = self.profiler.get_top_bottlenecks(5)
        
        logger.info(f"[PERF] Frame {iteration}: avg={avg:.1f}ms, p95={p95:.1f}ms, p99={p99:.1f}ms")
        for name, time_ms in bottlenecks:
            logger.info(f"[PERF]   Bottleneck: {name} = {time_ms:.1f}ms")
```

**검증:**
```bash
python -m py_compile wicked_zerg_challenger/bot_step_integration.py
pytest wicked_zerg_challenger/tests/ -v --tb=short
```

---

### Task P1.2: 거리 계산 캐싱 시스템

**파일:** `wicked_zerg_challenger/utils/distance_cache.py` (신규 생성)

**구현 지시:**
```python
"""프레임 단위 거리 계산 캐싱 — 동일 프레임 내 중복 계산 제거"""
from typing import Dict, Tuple

class DistanceCache:
    def __init__(self):
        self._cache: Dict[Tuple[float, float, float, float], float] = {}
        self._frame: int = -1
        self._hits: int = 0
        self._misses: int = 0
    
    def get(self, pos_a, pos_b, current_frame: int) -> float:
        if current_frame != self._frame:
            self._cache.clear()
            self._frame = current_frame
            self._hits = 0
            self._misses = 0
        
        key = (round(pos_a.x, 1), round(pos_a.y, 1),
               round(pos_b.x, 1), round(pos_b.y, 1))
        
        if key not in self._cache:
            rev_key = (key[2], key[3], key[0], key[1])
            if rev_key in self._cache:
                self._cache[key] = self._cache[rev_key]
                self._hits += 1
            else:
                self._cache[key] = pos_a.distance_to(pos_b)
                self._misses += 1
        else:
            self._hits += 1
        
        return self._cache[key]
    
    @property
    def hit_rate(self) -> float:
        total = self._hits + self._misses
        return self._hits / total if total > 0 else 0.0

# 전역 인스턴스
_global_cache = DistanceCache()

def cached_distance(pos_a, pos_b, frame: int) -> float:
    return _global_cache.get(pos_a, pos_b, frame)
```

**적용:** combat_manager.py, economy_manager.py의 빈번한 `distance_to` 호출을 `cached_distance`로 교체

**검증:**
```bash
# 캐시 적중률 확인 (로그로)
# 목표: 프레임당 거리 계산 호출 50% 이상 캐시 적중
pytest wicked_zerg_challenger/tests/ -v
```

---

### Task P1.3: 프레임 스킵 관리자

**파일:** `wicked_zerg_challenger/utils/frame_skip.py` (신규 생성)

**구현 지시:**
```python
"""동적 프레임 스킵 — 부하에 따라 자동 조절"""

class FrameSkipManager:
    # 매니저별 기본 실행 주기 (프레임 단위)
    DEFAULT_INTERVALS = {
        "combat_manager": 1,       # 매 프레임 (전투 중)
        "economy_manager": 3,      # 3프레임마다
        "strategy_manager": 5,     # 5프레임마다
        "scouting_system": 11,     # 0.5초마다
        "creep_manager": 33,       # 1.5초마다
        "upgrade_manager": 22,     # 1초마다
        "intel_manager": 7,        # 7프레임마다
    }
    
    # 전투 중 축소 주기
    COMBAT_INTERVALS = {
        "combat_manager": 1,       # 매 프레임
        "economy_manager": 5,      # 덜 자주
        "strategy_manager": 3,     # 더 자주 (전략 재평가)
        "scouting_system": 22,     # 덜 자주
        "creep_manager": 66,       # 거의 안 함
        "upgrade_manager": 44,     # 덜 자주
        "intel_manager": 3,        # 더 자주
    }
    
    def __init__(self):
        self.in_combat = False
        self._overloaded = False
    
    def should_execute(self, manager_name: str, iteration: int) -> bool:
        intervals = self.COMBAT_INTERVALS if self.in_combat else self.DEFAULT_INTERVALS
        interval = intervals.get(manager_name, 1)
        return iteration % interval == 0
    
    def set_combat_mode(self, active: bool):
        self.in_combat = active
    
    def set_overloaded(self, overloaded: bool):
        """프레임 시간 250ms+ 시 호출 → 모든 간격 2배"""
        self._overloaded = overloaded
```

---

### Task P1.4: Rust 가속 봇 루프 통합

**파일:**
- `wicked_zerg_challenger/rust_accel.py` (기존 — 수정)
- `wicked_zerg_challenger/combat_manager.py` (연동)

**현재:** Rust 8개 함수가 있지만 봇 루프에서 호출하지 않음

**구현 지시:**
```python
# rust_accel.py — 안전한 Rust 호출 래퍼
import logging
logger = logging.getLogger(__name__)

_RUST_AVAILABLE = False
try:
    import swarm_rust_accel
    _RUST_AVAILABLE = True
    logger.info("[RUST] Rust acceleration module loaded")
except ImportError:
    logger.info("[RUST] Rust not available, using Python fallback")

def combat_power_comparison(friendly_units_data, enemy_units_data):
    """HP 가중 전투력 비교 — Rust 가속 또는 Python fallback"""
    if _RUST_AVAILABLE:
        try:
            return swarm_rust_accel.combat_power_comparison(
                friendly_units_data, enemy_units_data
            )
        except Exception as e:
            logger.warning(f"[RUST] combat_power error: {e}, fallback to Python")
    
    # Python fallback
    friendly_power = sum(hp + shield for hp, shield, *_ in friendly_units_data)
    enemy_power = sum(hp + shield for hp, shield, *_ in enemy_units_data)
    return friendly_power, enemy_power

def nearest_point_index(query, points):
    """가장 가까운 지점 인덱스 — Rust 가속"""
    if _RUST_AVAILABLE:
        try:
            return swarm_rust_accel.nearest_point_index(query, points)
        except Exception:
            pass
    
    # Python fallback
    min_dist = float('inf')
    min_idx = 0
    for i, p in enumerate(points):
        d = (query[0] - p[0])**2 + (query[1] - p[1])**2
        if d < min_dist:
            min_dist = d
            min_idx = i
    return min_idx

def batch_nearest_points(queries, points):
    """배치 최근접 지점 — Rust 가속"""
    if _RUST_AVAILABLE:
        try:
            return swarm_rust_accel.batch_nearest_points(queries, points)
        except Exception:
            pass
    return [nearest_point_index(q, points) for q in queries]
```

**combat_manager.py에서 호출:**
```python
from rust_accel import combat_power_comparison

def _calculate_combat_power(self, units):
    """Rust 가속 전투력 계산"""
    data = [(u.health, u.shield, u.ground_dps, u.air_dps) for u in units]
    return combat_power_comparison(data, [])
```

---

### Task P1.5: Rust 가속 모듈 확장

**파일:** `rust_accel/src/lib.rs`

**추가할 함수:**
```rust
/// 적 유닛 클러스터 탐지 — 밀집 지역 중심점 반환
#[pyfunction]
fn find_unit_clusters(positions: Vec<(f64, f64)>, radius: f64, min_count: usize) -> Vec<(f64, f64, usize)> {
    let mut clusters: Vec<(f64, f64, usize)> = Vec::new();
    for (i, &(x, y)) in positions.iter().enumerate() {
        let count = positions.iter()
            .filter(|&&(px, py)| {
                let dx = px - x;
                let dy = py - y;
                dx * dx + dy * dy <= radius * radius
            })
            .count();
        if count >= min_count {
            clusters.push((x, y, count));
        }
    }
    // 가장 밀집된 순서로 정렬
    clusters.sort_by(|a, b| b.2.cmp(&a.2));
    clusters
}

/// 위협 평가 점수 계산 — 다수 적 유닛의 복합 위협도
#[pyfunction]
fn threat_assessment(
    enemy_data: Vec<(f64, f64, f64, f64, f64)>,  // x, y, hp, dps, range
    base_position: (f64, f64),
    max_distance: f64,
) -> f64 {
    enemy_data.par_iter()
        .filter_map(|&(x, y, hp, dps, range)| {
            let dx = x - base_position.0;
            let dy = y - base_position.1;
            let dist = (dx * dx + dy * dy).sqrt();
            if dist <= max_distance {
                let proximity_factor = 1.0 - (dist / max_distance);
                Some(hp * dps * proximity_factor * (range / 6.0))
            } else {
                None
            }
        })
        .sum()
}

/// 후퇴 경로 계산 — 점막 위 + 스파인 근처 최적 경로
#[pyfunction]
fn calculate_retreat_path(
    unit_pos: (f64, f64),
    base_positions: Vec<(f64, f64)>,
    creep_positions: Vec<(f64, f64)>,
    spine_positions: Vec<(f64, f64)>,
) -> (f64, f64) {
    // 가장 가까운 기지 방향 + 점막/스파인 가산점
    let mut best_pos = base_positions[0];
    let mut best_score = f64::MIN;
    
    for &base in &base_positions {
        let dist = ((base.0 - unit_pos.0).powi(2) + (base.1 - unit_pos.1).powi(2)).sqrt();
        let mut score = -dist;  // 가까울수록 좋음
        
        // 점막 보너스
        for &creep in &creep_positions {
            let cd = ((creep.0 - base.0).powi(2) + (creep.1 - base.1).powi(2)).sqrt();
            if cd < 5.0 { score += 10.0; }
        }
        
        // 스파인 보너스
        for &spine in &spine_positions {
            let sd = ((spine.0 - base.0).powi(2) + (spine.1 - base.1).powi(2)).sqrt();
            if sd < 8.0 { score += 20.0; }
        }
        
        if score > best_score {
            best_score = score;
            best_pos = base;
        }
    }
    best_pos
}
```

**빌드 & 검증:**
```bash
cd rust_accel
maturin develop --release
python -c "import swarm_rust_accel; print(dir(swarm_rust_accel))"
```

---

### Task P1.6: 메모리 최적화

**파일:** `wicked_zerg_challenger/utils/memory_monitor.py` (신규 생성)

```python
"""게임 중 메모리 사용량 모니터링 & 누수 감지"""
import tracemalloc
import logging

logger = logging.getLogger(__name__)

class MemoryMonitor:
    def __init__(self, warn_threshold_mb=200, leak_check_interval=500):
        self.warn_threshold = warn_threshold_mb * 1024 * 1024
        self.check_interval = leak_check_interval
        self.snapshots = []
        tracemalloc.start()
    
    def check(self, iteration):
        if iteration % self.check_interval != 0:
            return
        
        current, peak = tracemalloc.get_traced_memory()
        
        if current > self.warn_threshold:
            logger.warning(f"[MEM] High memory: {current/1024/1024:.1f}MB (peak: {peak/1024/1024:.1f}MB)")
        
        snapshot = tracemalloc.take_snapshot()
        if self.snapshots:
            top_stats = snapshot.compare_to(self.snapshots[-1], 'lineno')
            leaks = [s for s in top_stats[:5] if s.size_diff > 100_000]
            for stat in leaks:
                logger.warning(f"[MEM LEAK] {stat}")
        
        self.snapshots.append(snapshot)
        if len(self.snapshots) > 10:
            self.snapshots.pop(0)
    
    def stop(self):
        tracemalloc.stop()
```

---

## Part 2: RL 학습 파이프라인

### Task P2.1: PolicyNetwork → Actor-Critic 업그레이드

**파일:** `wicked_zerg_challenger/local_training/rl_agent.py`

**현재:** REINFORCE만 구현 (PolicyNetwork 3층, softmax 출력)

**구현 지시:**
```python
class ActorCriticNetwork:
    """Actor-Critic 아키텍처 — Policy(Actor) + Value(Critic)"""
    
    def __init__(self, input_dim=16, hidden_dim=128, action_dim=7):
        # 공유 백본
        self.W_shared = xavier_init(input_dim, hidden_dim)
        self.b_shared = np.zeros(hidden_dim)
        
        # Actor (정책)
        self.W_actor = xavier_init(hidden_dim, action_dim)
        self.b_actor = np.zeros(action_dim)
        
        # Critic (가치)
        self.W_critic = xavier_init(hidden_dim, 1)
        self.b_critic = np.zeros(1)
        
        # 하이퍼파라미터
        self.lr_actor = 3e-4
        self.lr_critic = 1e-3
        self.gamma = 0.99
        self.gae_lambda = 0.95
        self.clip_epsilon = 0.2   # PPO 클리핑
        self.entropy_coef = 0.01
        self.max_grad_norm = 0.5
    
    def forward(self, state):
        """순전파 → (action_probs, state_value)"""
        # 공유 레이어
        shared = np.maximum(0, np.dot(state, self.W_shared) + self.b_shared)
        
        # Actor: 행동 확률
        logits = np.dot(shared, self.W_actor) + self.b_actor
        action_probs = softmax(logits)
        
        # Critic: 상태 가치
        value = np.dot(shared, self.W_critic) + self.b_critic
        
        return action_probs, value[0]
    
    def compute_gae(self, rewards, values, dones):
        """GAE (Generalized Advantage Estimation) 계산"""
        advantages = np.zeros_like(rewards)
        last_gae = 0
        
        for t in reversed(range(len(rewards))):
            if t == len(rewards) - 1:
                next_value = 0
            else:
                next_value = values[t + 1]
            
            delta = rewards[t] + self.gamma * next_value * (1 - dones[t]) - values[t]
            advantages[t] = last_gae = delta + self.gamma * self.gae_lambda * (1 - dones[t]) * last_gae
        
        returns = advantages + values
        return advantages, returns
```

---

### Task P2.2: 관찰 공간 & 행동 공간 정의

**파일:** `wicked_zerg_challenger/local_training/sc2_env.py` (신규 생성)

```python
"""SC2 Gymnasium 환경 — 봇 상태를 RL 관찰로 변환"""
import numpy as np

class SC2Observation:
    """16차원 관찰 벡터 구성"""
    
    @staticmethod
    def from_bot(bot) -> np.ndarray:
        return np.array([
            # 경제 (4D)
            min(bot.minerals / 2000, 1.0),
            min(bot.vespene / 1000, 1.0),
            min(bot.workers.amount / 80, 1.0),
            min(bot.supply_used / 200, 1.0),
            
            # 군사 (4D)
            min(bot.supply_army / 150, 1.0),
            min(len(bot.townhalls) / 5, 1.0),
            min(bot.supply_left / 20, 1.0),
            1.0 if bot.structures(UnitTypeId.LAIR).ready else 0.0,
            
            # 적 정보 (4D)
            min(len(bot.enemy_units) / 50, 1.0),
            min(len(bot.enemy_structures) / 20, 1.0),
            1.0 if bot.enemy_units.closer_than(30, bot.start_location) else 0.0,
            bot.time / 1200,  # 정규화된 게임 시간
            
            # 전투 상태 (4D)
            min(bot.units(UnitTypeId.QUEEN).amount / 6, 1.0),
            min(bot.units(UnitTypeId.ZERGLING).amount / 40, 1.0),
            min(bot.units(UnitTypeId.ROACH).amount / 20, 1.0),
            min(bot.units(UnitTypeId.HYDRALISK).amount / 15, 1.0),
        ], dtype=np.float32)

class SC2ActionSpace:
    """7개 이산 행동"""
    ACTIONS = {
        0: "MACRO_FOCUS",        # 드론 + 확장 우선
        1: "ARMY_FOCUS",         # 병력 생산 우선
        2: "TECH_UP",            # 테크 업그레이드
        3: "ATTACK",             # 전체 공격
        4: "DEFEND",             # 방어 모드
        5: "HARASS",             # 견제
        6: "EXPAND",             # 확장
    }
```

---

### Task P2.3: 리플레이 → 학습 데이터 파이프라인

**파일:** `wicked_zerg_challenger/local_training/replay_to_training.py` (신규 생성)

```python
"""리플레이 파일 → RL 학습 데이터 변환 파이프라인"""
import json
import logging
from pathlib import Path

logger = logging.getLogger(__name__)

class ReplayToTrainingPipeline:
    def __init__(self, replay_dir: str, output_dir: str):
        self.replay_dir = Path(replay_dir)
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)
    
    def process_replay_summaries(self):
        """replay_feedback JSON에서 학습 데이터 생성"""
        summaries = list(self.replay_dir.glob("*.json"))
        training_data = []
        
        for summary_path in summaries:
            with open(summary_path) as f:
                data = json.load(f)
            
            # 보상 신호 생성
            reward = self._compute_reward(data)
            
            # 상태-행동-보상 튜플
            episode = {
                "enemy_race": data.get("enemy_race", "Unknown"),
                "result": data.get("result", "Unknown"),
                "game_length": data.get("game_length_seconds", 0),
                "reward": reward,
                "loss_tags": data.get("loss_tags", []),
                "focus_areas": data.get("focus_areas", []),
            }
            training_data.append(episode)
        
        # 학습 데이터 저장
        output_path = self.output_dir / "training_episodes.json"
        with open(output_path, 'w') as f:
            json.dump(training_data, f, indent=2)
        
        logger.info(f"[REPLAY→TRAIN] {len(training_data)} episodes processed → {output_path}")
        return training_data
    
    def _compute_reward(self, data) -> float:
        """게임 결과 → 보상 신호"""
        base_reward = 10.0 if data.get("result") == "Victory" else -10.0
        
        # 보너스/패널티
        game_length = data.get("game_length_seconds", 600)
        if data.get("result") == "Victory":
            # 빠른 승리 보너스
            if game_length < 300:
                base_reward += 3.0
            elif game_length < 600:
                base_reward += 1.0
        else:
            # 패배 원인별 패널티
            tags = data.get("loss_tags", [])
            if "early_defense" in tags:
                base_reward -= 2.0  # 초반 방어 실패
            if "supply_block" in tags:
                base_reward -= 1.0
            if "float_minerals" in tags:
                base_reward -= 1.5
        
        return base_reward
```

---

### Task P2.4: 셀프 플레이 리그 시스템

**파일:** `wicked_zerg_challenger/local_training/self_play_league.py` (신규 생성)

```python
"""셀프 플레이 리그 — ELO 레이팅 기반 매치메이킹"""
import json
import random
import logging
from dataclasses import dataclass, field
from pathlib import Path
from typing import List, Dict

logger = logging.getLogger(__name__)

@dataclass
class LeaguePlayer:
    name: str
    model_path: str
    elo: float = 1200.0
    games_played: int = 0
    wins: int = 0

class SelfPlayLeague:
    def __init__(self, league_dir: str, max_players: int = 20):
        self.league_dir = Path(league_dir)
        self.league_dir.mkdir(parents=True, exist_ok=True)
        self.max_players = max_players
        self.players: List[LeaguePlayer] = []
        self._load_league()
    
    def add_player(self, name: str, model_path: str):
        """새 플레이어(모델 체크포인트) 추가"""
        player = LeaguePlayer(name=name, model_path=model_path)
        self.players.append(player)
        
        # 최대 인원 초과 시 최하위 제거
        if len(self.players) > self.max_players:
            self.players.sort(key=lambda p: p.elo)
            removed = self.players.pop(0)
            logger.info(f"[LEAGUE] Removed weakest: {removed.name} (ELO: {removed.elo:.0f})")
        
        self._save_league()
    
    def get_opponent(self, player_name: str) -> LeaguePlayer:
        """ELO 200 이내 상대 랜덤 매칭"""
        player = next(p for p in self.players if p.name == player_name)
        candidates = [
            p for p in self.players
            if p.name != player_name and abs(p.elo - player.elo) < 200
        ]
        if not candidates:
            candidates = [p for p in self.players if p.name != player_name]
        return random.choice(candidates) if candidates else player
    
    def report_result(self, winner_name: str, loser_name: str):
        """대전 결과 기록 + ELO 업데이트"""
        winner = next(p for p in self.players if p.name == winner_name)
        loser = next(p for p in self.players if p.name == loser_name)
        
        K = 32
        expected_w = 1 / (1 + 10 ** ((loser.elo - winner.elo) / 400))
        expected_l = 1 - expected_w
        
        winner.elo += K * (1 - expected_w)
        loser.elo += K * (0 - expected_l)
        winner.games_played += 1
        winner.wins += 1
        loser.games_played += 1
        
        logger.info(f"[LEAGUE] {winner_name}({winner.elo:.0f}) beat {loser_name}({loser.elo:.0f})")
        self._save_league()
    
    def get_leaderboard(self) -> List[Dict]:
        """리더보드 반환"""
        self.players.sort(key=lambda p: p.elo, reverse=True)
        return [
            {"rank": i+1, "name": p.name, "elo": round(p.elo),
             "games": p.games_played, "winrate": f"{p.wins/max(p.games_played,1)*100:.0f}%"}
            for i, p in enumerate(self.players)
        ]
    
    def _save_league(self):
        path = self.league_dir / "league.json"
        data = [{"name": p.name, "model_path": p.model_path, "elo": p.elo,
                  "games_played": p.games_played, "wins": p.wins} for p in self.players]
        with open(path, 'w') as f:
            json.dump(data, f, indent=2)
    
    def _load_league(self):
        path = self.league_dir / "league.json"
        if path.exists():
            with open(path) as f:
                data = json.load(f)
            self.players = [LeaguePlayer(**d) for d in data]
```

---

### Task P2.5: 학습 자동화 스크립트

**파일:** `wicked_zerg_challenger/local_training/scripts/run_full_training.py` (신규 생성)

```python
"""전체 학습 파이프라인 자동 실행 스크립트"""
import argparse
import logging
from pathlib import Path

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def main():
    parser = argparse.ArgumentParser(description="WickedZergBotPro Training Pipeline")
    parser.add_argument("--episodes", type=int, default=1000, help="총 학습 에피소드 수")
    parser.add_argument("--checkpoint-interval", type=int, default=50, help="체크포인트 저장 간격")
    parser.add_argument("--league-size", type=int, default=10, help="셀프플레이 리그 최대 인원")
    parser.add_argument("--replay-dir", type=str, default="data/replay_feedback", help="리플레이 피드백 디렉토리")
    parser.add_argument("--output-dir", type=str, default="data/training_output", help="학습 결과 저장 디렉토리")
    parser.add_argument("--stage", type=int, choices=[1, 2, 3], default=1, help="커리큘럼 단계 (1=매크로, 2=전투, 3=풀게임)")
    args = parser.parse_args()
    
    logger.info(f"=== Training Pipeline Start ===")
    logger.info(f"Episodes: {args.episodes}, Stage: {args.stage}")
    
    # 1. 리플레이 데이터 수집
    logger.info("[STEP 1] Processing replay feedback...")
    from replay_to_training import ReplayToTrainingPipeline
    replay_pipeline = ReplayToTrainingPipeline(args.replay_dir, args.output_dir)
    training_data = replay_pipeline.process_replay_summaries()
    
    # 2. 모델 로드 또는 초기화
    logger.info("[STEP 2] Loading model...")
    from rl_agent import ActorCriticNetwork
    model = ActorCriticNetwork(input_dim=16, hidden_dim=128, action_dim=7)
    
    model_path = Path(args.output_dir) / "latest_model.npz"
    if model_path.exists():
        model.load(str(model_path))
        logger.info(f"  Loaded existing model from {model_path}")
    else:
        logger.info("  Initialized new model")
    
    # 3. 셀프 플레이 리그 초기화
    logger.info("[STEP 3] Initializing self-play league...")
    from self_play_league import SelfPlayLeague
    league = SelfPlayLeague(str(Path(args.output_dir) / "league"), max_players=args.league_size)
    
    # 4. 학습 루프
    logger.info(f"[STEP 4] Starting training loop ({args.episodes} episodes)...")
    for episode in range(args.episodes):
        # 커리큘럼 단계별 보상 함수 선택
        # Stage 1: 매크로 보상만 (드론, 확장, 자원)
        # Stage 2: 전투 보상만 (킬, 생존, 전투력)
        # Stage 3: 통합 보상 (매크로 + 전투)
        
        # 체크포인트 저장
        if (episode + 1) % args.checkpoint_interval == 0:
            ckpt_path = Path(args.output_dir) / f"checkpoint_ep{episode+1}.npz"
            model.save(str(ckpt_path))
            league.add_player(f"v{episode+1}", str(ckpt_path))
            logger.info(f"  Checkpoint saved: {ckpt_path}")
    
    # 5. 최종 모델 저장
    model.save(str(model_path))
    logger.info(f"[STEP 5] Final model saved: {model_path}")
    
    # 6. 리더보드 출력
    logger.info("[STEP 6] Final Leaderboard:")
    for entry in league.get_leaderboard():
        logger.info(f"  #{entry['rank']} {entry['name']} ELO={entry['elo']} ({entry['winrate']})")
    
    logger.info("=== Training Pipeline Complete ===")

if __name__ == "__main__":
    main()
```

---

## Part 3: AI Arena 래더 운영

### Task P3.1: Arena 패키지 Pre-flight 검증

**파일:** `create_arena_package.py` (기존 수정)

**추가할 검증 단계:**
```python
def preflight_check() -> bool:
    """Arena 제출 전 사전 검증"""
    errors = []
    
    # 1. 필수 파일 존재 확인
    required = ["run.py", "ladderbots.json", "wicked_zerg_challenger/bot.py"]
    for f in required:
        if not Path(f).exists():
            errors.append(f"Missing required file: {f}")
    
    # 2. 전체 py_compile 검증
    import py_compile
    for py_file in Path("wicked_zerg_challenger").rglob("*.py"):
        if "test_" in py_file.name or "__pycache__" in str(py_file):
            continue
        try:
            py_compile.compile(str(py_file), doraise=True)
        except py_compile.PyCompileError as e:
            errors.append(f"Compile error: {e}")
    
    # 3. ladderbots.json 포맷 검증
    with open("ladderbots.json") as f:
        config = json.load(f)
    if "Bots" not in config:
        errors.append("ladderbots.json missing 'Bots' key")
    
    # 4. 금지 import 체크 (Arena에서 사용 불가한 패키지)
    banned_imports = ["torch", "tensorflow", "jax", "opencv"]
    for py_file in Path("wicked_zerg_challenger").rglob("*.py"):
        if "local_training" in str(py_file) or "test_" in py_file.name:
            continue
        content = py_file.read_text(errors='ignore')
        for banned in banned_imports:
            if f"import {banned}" in content and "try:" not in content.split(f"import {banned}")[0][-50:]:
                errors.append(f"{py_file}: unconditional import of '{banned}' (banned in Arena)")
    
    # 5. 패키지 크기 추정
    total_size = sum(f.stat().st_size for f in Path("wicked_zerg_challenger").rglob("*") if f.is_file())
    if total_size > 10 * 1024 * 1024:  # 10MB
        errors.append(f"Package too large: {total_size/1024/1024:.1f}MB (limit: 10MB)")
    
    if errors:
        for e in errors:
            logger.error(f"[PREFLIGHT FAIL] {e}")
        return False
    
    logger.info("[PREFLIGHT] All checks passed")
    return True
```

---

### Task P3.2: 래더 결과 자동 수집 & ELO 추적

**파일:** `scripts/ladder_tracker.py` (신규 생성)

```python
"""AI Arena 래더 결과 자동 추적 시스템"""
import json
import datetime
from pathlib import Path
from dataclasses import dataclass, asdict
from typing import List, Optional

@dataclass
class LadderMatch:
    date: str
    opponent: str
    opponent_race: str
    map_name: str
    result: str  # "win" | "loss" | "tie" | "crash"
    game_length_seconds: int
    our_elo_before: float
    our_elo_after: float
    crash_reason: Optional[str] = None

class LadderTracker:
    def __init__(self, data_dir: str = "data/ladder"):
        self.data_dir = Path(data_dir)
        self.data_dir.mkdir(parents=True, exist_ok=True)
        self.matches: List[LadderMatch] = []
        self._load()
    
    def record_match(self, match: LadderMatch):
        self.matches.append(match)
        self._save()
        self._update_analytics()
    
    def get_winrate(self, last_n: int = 0, vs_race: str = None) -> dict:
        """승률 분석"""
        matches = self.matches[-last_n:] if last_n > 0 else self.matches
        if vs_race:
            matches = [m for m in matches if m.opponent_race == vs_race]
        
        if not matches:
            return {"total": 0, "wins": 0, "losses": 0, "winrate": 0.0}
        
        wins = sum(1 for m in matches if m.result == "win")
        losses = sum(1 for m in matches if m.result == "loss")
        crashes = sum(1 for m in matches if m.result == "crash")
        
        return {
            "total": len(matches),
            "wins": wins,
            "losses": losses,
            "crashes": crashes,
            "winrate": wins / len(matches) * 100,
            "crash_rate": crashes / len(matches) * 100,
        }
    
    def get_weakness_report(self) -> dict:
        """약점 분석 — 가장 많이 지는 매치업/맵"""
        losses = [m for m in self.matches if m.result in ("loss", "crash")]
        
        race_losses = {}
        map_losses = {}
        opponent_losses = {}
        
        for m in losses:
            race_losses[m.opponent_race] = race_losses.get(m.opponent_race, 0) + 1
            map_losses[m.map_name] = map_losses.get(m.map_name, 0) + 1
            opponent_losses[m.opponent] = opponent_losses.get(m.opponent, 0) + 1
        
        return {
            "worst_matchup": max(race_losses, key=race_losses.get) if race_losses else None,
            "worst_map": max(map_losses, key=map_losses.get) if map_losses else None,
            "hardest_opponent": max(opponent_losses, key=opponent_losses.get) if opponent_losses else None,
            "race_breakdown": race_losses,
            "crash_reasons": [m.crash_reason for m in losses if m.crash_reason],
        }
    
    def get_elo_history(self) -> List[dict]:
        """ELO 변동 히스토리"""
        return [{"date": m.date, "elo": m.our_elo_after, "opponent": m.opponent} for m in self.matches]
    
    def _update_analytics(self):
        """분석 리포트 자동 생성"""
        report = {
            "last_updated": datetime.datetime.now().isoformat(),
            "total_matches": len(self.matches),
            "overall": self.get_winrate(),
            "last_20": self.get_winrate(last_n=20),
            "vs_terran": self.get_winrate(vs_race="Terran"),
            "vs_protoss": self.get_winrate(vs_race="Protoss"),
            "vs_zerg": self.get_winrate(vs_race="Zerg"),
            "weaknesses": self.get_weakness_report(),
            "elo_history": self.get_elo_history()[-50:],
        }
        
        with open(self.data_dir / "analytics.json", 'w') as f:
            json.dump(report, f, indent=2, ensure_ascii=False)
    
    def _save(self):
        with open(self.data_dir / "matches.json", 'w') as f:
            json.dump([asdict(m) for m in self.matches], f, indent=2)
    
    def _load(self):
        path = self.data_dir / "matches.json"
        if path.exists():
            with open(path) as f:
                data = json.load(f)
            self.matches = [LadderMatch(**d) for d in data]
```

---

### Task P3.3: 시즌별 메타 적응 시스템

**파일:** `scripts/meta_adapter.py` (신규 생성)

```python
"""래더 데이터 기반 메타 적응 — 자주 지는 패턴에 자동 대응"""
import json
from pathlib import Path

class MetaAdapter:
    def __init__(self, ladder_data_dir: str = "data/ladder"):
        self.data_dir = Path(ladder_data_dir)
    
    def generate_strategy_adjustments(self) -> dict:
        """최근 20경기 분석 → 전략 조정 제안"""
        analytics_path = self.data_dir / "analytics.json"
        if not analytics_path.exists():
            return {}
        
        with open(analytics_path) as f:
            data = json.load(f)
        
        adjustments = {}
        
        # 매치업별 승률 50% 미만이면 조정
        for race in ["Terran", "Protoss", "Zerg"]:
            key = f"vs_{race.lower()}"
            if key in data and data[key]["winrate"] < 50:
                adjustments[f"Zv{race[0]}"] = {
                    "winrate": data[key]["winrate"],
                    "action": self._suggest_adjustment(race, data.get("weaknesses", {})),
                }
        
        # 크래시율 5% 이상이면 안정성 경고
        overall = data.get("overall", {})
        if overall.get("crash_rate", 0) > 5:
            adjustments["stability"] = {
                "crash_rate": overall["crash_rate"],
                "action": "CRITICAL: 크래시율 5% 이상. try/except 강화 필요",
                "reasons": data.get("weaknesses", {}).get("crash_reasons", []),
            }
        
        # 조정 결과 저장
        with open(self.data_dir / "strategy_adjustments.json", 'w') as f:
            json.dump(adjustments, f, indent=2, ensure_ascii=False)
        
        return adjustments
    
    def _suggest_adjustment(self, race: str, weaknesses: dict) -> str:
        suggestions = {
            "Terran": "ZvT 약세: 베인 비율 증가, 드롭 방어 강화, 시즈 탱크 서라운드 연습",
            "Protoss": "ZvP 약세: 코럽터/바이퍼 비율 증가, DT 탐지 강화, 폭풍 회피 개선",
            "Zerg": "ZvZ 약세: 초반 베인 컨트롤 개선, 바퀴 전환 타이밍 앞당기기",
        }
        return suggestions.get(race, "분석 필요")
```

---

## Part 4: 모니터링 & 대시보드

### Task P4.1: 텔레메트리 수집기 구현

**파일:** `wicked_zerg_challenger/monitoring/telemetry_logger_atomic.py` (기존 — 완전 재작성)

```python
"""게임 중 텔레메트리 데이터 수집 — 프레임 단위 기록"""
import json
import time
import logging
from pathlib import Path
from dataclasses import dataclass, asdict, field
from typing import List, Dict

logger = logging.getLogger(__name__)

@dataclass
class FrameSnapshot:
    game_time: float
    frame: int
    minerals: int
    vespene: int
    supply_used: int
    supply_cap: int
    worker_count: int
    army_supply: int
    base_count: int
    enemy_units_visible: int
    army_value: float
    enemy_army_value: float
    frame_time_ms: float
    active_strategy: str = ""
    game_phase: str = ""

@dataclass
class GameTelemetry:
    game_id: str
    start_time: str
    enemy_race: str
    map_name: str
    result: str = ""
    end_time: str = ""
    total_frames: int = 0
    frames: List[FrameSnapshot] = field(default_factory=list)
    events: List[Dict] = field(default_factory=list)
    performance: Dict = field(default_factory=dict)

class TelemetryCollector:
    def __init__(self, output_dir: str = "data/telemetry"):
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.current_game: GameTelemetry = None
        self._sample_interval = 22  # 1초마다 샘플링
    
    def start_game(self, game_id: str, enemy_race: str, map_name: str):
        self.current_game = GameTelemetry(
            game_id=game_id,
            start_time=time.strftime("%Y-%m-%d %H:%M:%S"),
            enemy_race=enemy_race,
            map_name=map_name,
        )
        logger.info(f"[TELEMETRY] Game started: {game_id} vs {enemy_race} on {map_name}")
    
    def record_frame(self, bot, iteration: int, frame_time_ms: float):
        if not self.current_game or iteration % self._sample_interval != 0:
            return
        
        snapshot = FrameSnapshot(
            game_time=bot.time,
            frame=iteration,
            minerals=bot.minerals,
            vespene=bot.vespene,
            supply_used=bot.supply_used,
            supply_cap=bot.supply_cap,
            worker_count=bot.workers.amount,
            army_supply=bot.supply_army,
            base_count=len(bot.townhalls),
            enemy_units_visible=len(bot.enemy_units),
            army_value=sum(u.health + u.shield for u in bot.units if u.can_attack),
            enemy_army_value=sum(u.health + u.shield for u in bot.enemy_units),
            frame_time_ms=frame_time_ms,
        )
        self.current_game.frames.append(snapshot)
    
    def record_event(self, event_type: str, details: dict):
        if not self.current_game:
            return
        self.current_game.events.append({
            "time": time.time(),
            "type": event_type,
            **details,
        })
    
    def end_game(self, result: str):
        if not self.current_game:
            return
        
        self.current_game.result = result
        self.current_game.end_time = time.strftime("%Y-%m-%d %H:%M:%S")
        self.current_game.total_frames = len(self.current_game.frames)
        
        # 성능 통계 계산
        if self.current_game.frames:
            frame_times = [f.frame_time_ms for f in self.current_game.frames]
            self.current_game.performance = {
                "avg_frame_ms": sum(frame_times) / len(frame_times),
                "max_frame_ms": max(frame_times),
                "p95_frame_ms": sorted(frame_times)[int(len(frame_times) * 0.95)],
                "frames_over_250ms": sum(1 for t in frame_times if t > 250),
                "frames_over_320ms": sum(1 for t in frame_times if t > 320),
            }
        
        # 파일 저장
        filename = f"{self.current_game.game_id}_{result}.json"
        output_path = self.output_dir / filename
        with open(output_path, 'w') as f:
            json.dump(asdict(self.current_game), f, indent=2)
        
        logger.info(f"[TELEMETRY] Game ended: {result}. Saved to {output_path}")
        logger.info(f"[TELEMETRY] Performance: {self.current_game.performance}")
```

---

### Task P4.2: 게임 후 자동 리포트 생성

**파일:** `wicked_zerg_challenger/monitoring/post_game_report.py` (신규 생성)

```python
"""게임 종료 후 자동 분석 리포트 생성"""
import json
from pathlib import Path

class PostGameReport:
    def generate(self, telemetry_path: str) -> dict:
        with open(telemetry_path) as f:
            data = json.load(f)
        
        frames = data.get("frames", [])
        if not frames:
            return {"error": "No frame data"}
        
        report = {
            "summary": {
                "result": data["result"],
                "enemy_race": data["enemy_race"],
                "map": data["map_name"],
                "game_length_seconds": frames[-1]["game_time"] if frames else 0,
            },
            "economy": self._analyze_economy(frames),
            "military": self._analyze_military(frames),
            "performance": data.get("performance", {}),
            "events": data.get("events", []),
            "recommendations": [],
        }
        
        # 자동 추천 생성
        report["recommendations"] = self._generate_recommendations(report)
        return report
    
    def _analyze_economy(self, frames) -> dict:
        if not frames:
            return {}
        minerals = [f["minerals"] for f in frames]
        workers = [f["worker_count"] for f in frames]
        
        return {
            "peak_minerals": max(minerals),
            "avg_minerals": sum(minerals) / len(minerals),
            "float_frames": sum(1 for m in minerals if m > 1000),
            "peak_workers": max(workers),
            "final_workers": workers[-1],
            "max_bases": max(f["base_count"] for f in frames),
            "first_expansion_time": next(
                (f["game_time"] for f in frames if f["base_count"] >= 2), None
            ),
        }
    
    def _analyze_military(self, frames) -> dict:
        if not frames:
            return {}
        army = [f["army_supply"] for f in frames]
        return {
            "peak_army_supply": max(army),
            "avg_army_supply": sum(army) / len(army),
            "peak_army_value": max(f["army_value"] for f in frames),
        }
    
    def _generate_recommendations(self, report) -> list:
        recs = []
        econ = report.get("economy", {})
        
        if econ.get("float_frames", 0) > 20:
            recs.append("미네랄 플로팅 심각: 매크로 해처리 추가 또는 병력 덤프 필요")
        
        if econ.get("first_expansion_time") and econ["first_expansion_time"] > 180:
            recs.append(f"확장 지연: {econ['first_expansion_time']:.0f}초 (목표: 60~90초)")
        
        if econ.get("peak_workers", 0) < 50:
            recs.append(f"드론 부족: 최대 {econ['peak_workers']}마리 (목표: 66)")
        
        perf = report.get("performance", {})
        if perf.get("frames_over_320ms", 0) > 0:
            recs.append(f"타임아웃 위험: {perf['frames_over_320ms']}프레임이 320ms 초과")
        
        if report["summary"]["result"] != "Victory":
            recs.append("패배 분석: 이벤트 로그를 확인하여 전환점 파악 필요")
        
        return recs
```

---

### Task P4.3: 실시간 대시보드 서버

**파일:** `wicked_zerg_challenger/monitoring/dashboard.py` (기존 — 완전 재작성)

```python
"""텔레메트리 기반 웹 대시보드 — FastAPI + 정적 HTML"""
import json
import glob
from pathlib import Path
from http.server import HTTPServer, SimpleHTTPRequestHandler
import threading
import logging

logger = logging.getLogger(__name__)

class DashboardServer:
    def __init__(self, telemetry_dir: str = "data/telemetry", port: int = 8765):
        self.telemetry_dir = Path(telemetry_dir)
        self.port = port
    
    def get_recent_games(self, limit: int = 20) -> list:
        """최근 게임 결과 목록"""
        files = sorted(self.telemetry_dir.glob("*.json"), key=lambda f: f.stat().st_mtime, reverse=True)
        games = []
        for f in files[:limit]:
            try:
                with open(f) as fh:
                    data = json.load(fh)
                games.append({
                    "game_id": data.get("game_id", f.stem),
                    "result": data.get("result", "Unknown"),
                    "enemy_race": data.get("enemy_race", "Unknown"),
                    "map": data.get("map_name", "Unknown"),
                    "date": data.get("start_time", ""),
                    "performance": data.get("performance", {}),
                })
            except (json.JSONDecodeError, KeyError):
                continue
        return games
    
    def get_winrate_summary(self) -> dict:
        """전체 승률 요약"""
        games = self.get_recent_games(limit=100)
        if not games:
            return {}
        
        total = len(games)
        wins = sum(1 for g in games if g["result"] == "Victory")
        
        by_race = {}
        for race in ["Terran", "Protoss", "Zerg"]:
            race_games = [g for g in games if g["enemy_race"] == race]
            race_wins = sum(1 for g in race_games if g["result"] == "Victory")
            by_race[race] = {
                "total": len(race_games),
                "wins": race_wins,
                "winrate": race_wins / len(race_games) * 100 if race_games else 0,
            }
        
        return {
            "overall": {"total": total, "wins": wins, "winrate": wins / total * 100},
            "by_race": by_race,
        }
    
    def generate_dashboard_html(self) -> str:
        """정적 HTML 대시보드 생성"""
        summary = self.get_winrate_summary()
        recent = self.get_recent_games(10)
        
        html = f"""<!DOCTYPE html>
<html><head><meta charset="utf-8"><title>WickedZergBotPro Dashboard</title>
<style>
body {{ font-family: sans-serif; max-width: 900px; margin: 0 auto; padding: 20px; background: #111; color: #eee; }}
h1 {{ color: #6f6; }}
.card {{ background: #222; border-radius: 8px; padding: 16px; margin: 12px 0; }}
.win {{ color: #6f6; }} .loss {{ color: #f66; }}
table {{ width: 100%; border-collapse: collapse; }}
td, th {{ padding: 8px; text-align: left; border-bottom: 1px solid #333; }}
</style></head><body>
<h1>WickedZergBotPro Dashboard</h1>
<div class="card">
<h2>Overall: {summary.get('overall', {}).get('winrate', 0):.1f}% 
({summary.get('overall', {}).get('wins', 0)}/{summary.get('overall', {}).get('total', 0)})</h2>
</div>
<div class="card"><h3>Recent Games</h3>
<table><tr><th>Result</th><th>vs</th><th>Map</th><th>Date</th></tr>
"""
        for g in recent:
            css = "win" if g["result"] == "Victory" else "loss"
            html += f'<tr><td class="{css}">{g["result"]}</td><td>{g["enemy_race"]}</td><td>{g["map"]}</td><td>{g["date"]}</td></tr>\n'
        
        html += "</table></div></body></html>"
        return html
    
    def save_dashboard(self):
        """HTML 파일로 저장"""
        html = self.generate_dashboard_html()
        output = self.telemetry_dir / "dashboard.html"
        with open(output, 'w', encoding='utf-8') as f:
            f.write(html)
        logger.info(f"[DASHBOARD] Saved to {output}")
```

---

### Task P4.4: CI/CD 대시보드 자동 갱신

**파일:** `.github/workflows/ci.yml` (기존 수정 — Job 추가)

```yaml
  # 신규 Job: 대시보드 갱신
  update-dashboard:
    runs-on: ubuntu-latest
    needs: [sc2-bot-test]
    if: github.ref == 'refs/heads/main'
    steps:
      - uses: actions/checkout@v4
      
      - name: Setup Python
        uses: actions/setup-python@v5
        with:
          python-version: '3.11'
      
      - name: Generate Dashboard
        run: |
          python -c "
          from wicked_zerg_challenger.monitoring.dashboard import DashboardServer
          server = DashboardServer()
          server.save_dashboard()
          print('Dashboard generated')
          "
      
      - name: Upload Dashboard
        uses: actions/upload-artifact@v4
        with:
          name: dashboard
          path: data/telemetry/dashboard.html
          retention-days: 30
```

---

## Part 5: 통합 검증 체크리스트

### 전체 시스템 검증 순서

```bash
# 1. 컴파일 검증
python -c "
import py_compile, glob
files = glob.glob('wicked_zerg_challenger/**/*.py', recursive=True)
for f in files:
    py_compile.compile(f, doraise=True)
print(f'All {len(files)} files OK')
"

# 2. 유닛 테스트
pytest wicked_zerg_challenger/tests/ -v --tb=short
pytest tests/ -v --tb=short

# 3. 통합 검증
python phase50_integrated_validation.py --skip-package

# 4. Rust 빌드 (선택)
cd rust_accel && maturin develop --release && cd ..
python -c "import swarm_rust_accel; print('Rust OK:', dir(swarm_rust_accel))"

# 5. Arena 패키지 빌드
python create_arena_package.py --output-dir dist --no-open

# 6. 대시보드 생성
python -c "
from wicked_zerg_challenger.monitoring.dashboard import DashboardServer
DashboardServer().save_dashboard()
"
```

---

## 파일 맵 요약

```
wicked_zerg_challenger/
├── utils/
│   ├── performance_profiler.py   # P1.1 (프로파일러 연동)
│   ├── distance_cache.py         # P1.2 (신규)
│   ├── frame_skip.py             # P1.3 (신규)
│   └── memory_monitor.py         # P1.6 (신규)
├── rust_accel.py                 # P1.4 (Rust 래퍼 강화)
├── monitoring/
│   ├── telemetry_logger_atomic.py  # P4.1 (완전 재작성)
│   ├── post_game_report.py       # P4.2 (신규)
│   └── dashboard.py              # P4.3 (완전 재작성)
├── local_training/
│   ├── rl_agent.py               # P2.1 (Actor-Critic 업그레이드)
│   ├── sc2_env.py                # P2.2 (신규 — 관찰/행동 공간)
│   ├── replay_to_training.py     # P2.3 (신규)
│   ├── self_play_league.py       # P2.4 (신규)
│   └── scripts/
│       └── run_full_training.py  # P2.5 (신규)
├── rust_accel/
│   └── src/lib.rs                # P1.5 (함수 3개 추가)
├── scripts/
│   ├── ladder_tracker.py         # P3.2 (신규)
│   └── meta_adapter.py           # P3.3 (신규)
├── create_arena_package.py       # P3.1 (preflight 추가)
└── .github/workflows/ci.yml     # P4.4 (대시보드 Job 추가)
```
