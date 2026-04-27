"""
Phase 612: Curriculum Learning
SC2 Bot progressive curriculum RL trainer with adaptive difficulty staging.

Stages:
  1. Economy (drone management, expansion timing)
  2. Basic Combat (attack-move with army)
  3. Micro Control (individual unit tactics)
  4. Full Game (economy + army + tech + micro)
"""

from __future__ import annotations
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple
from enum import IntEnum
import math
import random
import time
import json
import os
import sys
import collections

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

try:
    import numpy as np

    NP_AVAILABLE = True
except ImportError:
    NP_AVAILABLE = False


# ─────────────────────────────────────────────
# NumPy fallback helpers
# ─────────────────────────────────────────────


def _np_zeros(shape):
    """Create zero array."""
    if NP_AVAILABLE:
        return np.zeros(shape, dtype=np.float32)
    if isinstance(shape, int):
        return [0.0] * shape
    # 2-D
    return [[0.0] * shape[1] for _ in range(shape[0])]


def _np_array(data):
    if NP_AVAILABLE:
        return np.array(data, dtype=np.float32)
    return list(data)


def _np_mean(arr):
    if NP_AVAILABLE:
        return float(np.mean(arr))
    if not arr:
        return 0.0
    return sum(arr) / len(arr)


def _np_std(arr):
    if NP_AVAILABLE:
        return float(np.std(arr))
    if len(arr) < 2:
        return 0.0
    m = _np_mean(arr)
    return math.sqrt(sum((x - m) ** 2 for x in arr) / len(arr))


def _np_clip(val, lo, hi):
    if NP_AVAILABLE:
        return float(np.clip(val, lo, hi))
    return max(lo, min(hi, val))


def _np_softmax(arr):
    """Numerically stable softmax."""
    if NP_AVAILABLE:
        a = np.array(arr, dtype=np.float64)
        a -= a.max()
        e = np.exp(a)
        return (e / e.sum()).tolist()
    mx = max(arr)
    exps = [math.exp(x - mx) for x in arr]
    s = sum(exps)
    return [e / s for e in exps]


def _np_argmax(arr):
    if NP_AVAILABLE:
        return int(np.argmax(arr))
    return arr.index(max(arr))


def _np_random_choice(n, p=None):
    """Weighted random choice returning index."""
    if NP_AVAILABLE and p is not None:
        return int(np.random.choice(n, p=p))
    if p is None:
        return random.randint(0, n - 1)
    r = random.random()
    cumulative = 0.0
    for i, pi in enumerate(p):
        cumulative += pi
        if r <= cumulative:
            return i
    return len(p) - 1


# ─────────────────────────────────────────────
# Curriculum Stage Definition
# ─────────────────────────────────────────────


class CurriculumStage(IntEnum):
    ECONOMY = 1
    BASIC_COMBAT = 2
    MICRO_CONTROL = 3
    FULL_GAME = 4


STAGE_NAMES = {
    CurriculumStage.ECONOMY: "Economy Only",
    CurriculumStage.BASIC_COMBAT: "Basic Combat",
    CurriculumStage.MICRO_CONTROL: "Micro Control",
    CurriculumStage.FULL_GAME: "Full Game",
}


@dataclass
class StageConfig:
    """Configuration for a single curriculum stage."""

    stage: CurriculumStage
    obs_dim: int
    act_dim: int
    action_names: List[str]
    promotion_win_rate: float = 0.65
    min_episodes_before_promotion: int = 50
    max_game_length: int = 5000
    reward_scale: float = 1.0
    difficulty_range: Tuple[float, float] = (0.0, 1.0)
    description: str = ""


STAGE_CONFIGS: Dict[CurriculumStage, StageConfig] = {
    CurriculumStage.ECONOMY: StageConfig(
        stage=CurriculumStage.ECONOMY,
        obs_dim=8,
        act_dim=4,
        action_names=["train_drone", "build_overlord", "expand", "build_extractor"],
        promotion_win_rate=0.70,
        min_episodes_before_promotion=40,
        max_game_length=3000,
        reward_scale=1.0,
        difficulty_range=(0.0, 0.5),
        description="Focus on economy: drone saturation, expansion timing, supply management",
    ),
    CurriculumStage.BASIC_COMBAT: StageConfig(
        stage=CurriculumStage.BASIC_COMBAT,
        obs_dim=12,
        act_dim=6,
        action_names=[
            "train_drone",
            "train_zergling",
            "train_roach",
            "build_overlord",
            "attack_move",
            "defend_base",
        ],
        promotion_win_rate=0.65,
        min_episodes_before_promotion=60,
        max_game_length=5000,
        reward_scale=1.2,
        difficulty_range=(0.2, 0.7),
        description="Economy + basic army production and attack-move commands",
    ),
    CurriculumStage.MICRO_CONTROL: StageConfig(
        stage=CurriculumStage.MICRO_CONTROL,
        obs_dim=20,
        act_dim=10,
        action_names=[
            "train_drone",
            "train_zergling",
            "train_roach",
            "train_hydra",
            "build_overlord",
            "attack_move",
            "defend_base",
            "focus_fire",
            "retreat_wounded",
            "flank_maneuver",
        ],
        promotion_win_rate=0.60,
        min_episodes_before_promotion=80,
        max_game_length=6000,
        reward_scale=1.5,
        difficulty_range=(0.3, 0.8),
        description="Unit micro: focus fire, retreating wounded units, flanking",
    ),
    CurriculumStage.FULL_GAME: StageConfig(
        stage=CurriculumStage.FULL_GAME,
        obs_dim=28,
        act_dim=14,
        action_names=[
            "train_drone",
            "train_zergling",
            "train_roach",
            "train_hydra",
            "train_mutalisk",
            "train_ultralisk",
            "build_overlord",
            "expand",
            "attack_move",
            "defend_base",
            "focus_fire",
            "retreat_wounded",
            "flank_maneuver",
            "tech_upgrade",
        ],
        promotion_win_rate=0.55,
        min_episodes_before_promotion=100,
        max_game_length=8000,
        reward_scale=2.0,
        difficulty_range=(0.4, 1.0),
        description="Full game: economy, army, tech, micro all combined",
    ),
}


# ─────────────────────────────────────────────
# Task Difficulty Scorer
# ─────────────────────────────────────────────


@dataclass
class TaskDifficultyScorer:
    """Scores and adaptively schedules task difficulty within a stage."""

    current_difficulty: float = 0.0
    difficulty_history: List[float] = field(default_factory=list)
    success_at_difficulty: Dict[str, List[bool]] = field(default_factory=dict)
    step_size: float = 0.05
    ema_alpha: float = 0.1
    ema_success: float = 0.5

    def bucket_key(self, difficulty: float) -> str:
        return f"{difficulty:.2f}"

    def record_result(self, difficulty: float, success: bool):
        """Record success/failure at a given difficulty level."""
        key = self.bucket_key(difficulty)
        if key not in self.success_at_difficulty:
            self.success_at_difficulty[key] = []
        self.success_at_difficulty[key].append(success)
        # Keep only last 50 results per bucket
        if len(self.success_at_difficulty[key]) > 50:
            self.success_at_difficulty[key] = self.success_at_difficulty[key][-50:]

        self.ema_success = (
            self.ema_alpha * (1.0 if success else 0.0)
            + (1.0 - self.ema_alpha) * self.ema_success
        )
        self.difficulty_history.append(difficulty)

    def next_difficulty(self, lo: float, hi: float) -> float:
        """Adapt difficulty based on recent performance."""
        if self.ema_success > 0.7:
            self.current_difficulty = min(hi, self.current_difficulty + self.step_size)
        elif self.ema_success < 0.4:
            self.current_difficulty = max(lo, self.current_difficulty - self.step_size)
        # Add small noise for exploration
        noise = random.gauss(0, self.step_size * 0.3)
        diff = _np_clip(self.current_difficulty + noise, lo, hi)
        return diff

    def mastery_score(self) -> float:
        """Overall mastery: weighted average of success rates across difficulties."""
        if not self.success_at_difficulty:
            return 0.0
        total_w = 0.0
        total_s = 0.0
        for key, results in self.success_at_difficulty.items():
            d = float(key)
            w = d + 0.1  # weight harder difficulties more
            sr = sum(results) / len(results) if results else 0.0
            total_w += w
            total_s += w * sr
        return total_s / total_w if total_w > 0 else 0.0


# ─────────────────────────────────────────────
# Hindsight Experience Replay Buffer
# ─────────────────────────────────────────────


@dataclass
class Transition:
    """Single environment transition."""

    state: Any
    action: int
    reward: float
    next_state: Any
    done: bool
    goal: Any = None
    info: Dict[str, Any] = field(default_factory=dict)


class HindsightReplayBuffer:
    """
    Experience replay buffer with Hindsight Experience Replay (HER).
    Re-labels failed episodes with achieved goals as intended goals.
    """

    def __init__(self, capacity: int = 100_000, her_ratio: float = 0.8):
        self.capacity = capacity
        self.buffer: collections.deque = collections.deque(maxlen=capacity)
        self.episode_buffer: List[Transition] = []
        self.her_ratio = her_ratio
        self.total_added = 0
        self.total_her = 0

    def add(self, transition: Transition):
        """Add transition to current episode."""
        self.episode_buffer.append(transition)

    def end_episode(
        self, achieved_goal: Any = None, desired_goal: Any = None, success: bool = False
    ):
        """End episode and optionally apply HER relabeling."""
        if not self.episode_buffer:
            return

        # Store original episode
        for t in self.episode_buffer:
            self.buffer.append(t)
            self.total_added += 1

        # HER: relabel failed episodes with achieved goal
        if (
            not success
            and achieved_goal is not None
            and random.random() < self.her_ratio
        ):
            for t in self.episode_buffer:
                relabeled = Transition(
                    state=t.state,
                    action=t.action,
                    reward=self._compute_her_reward(t, achieved_goal),
                    next_state=t.next_state,
                    done=t.done,
                    goal=achieved_goal,
                    info={**t.info, "her_relabeled": True},
                )
                self.buffer.append(relabeled)
                self.total_her += 1

        self.episode_buffer = []

    def _compute_her_reward(self, transition: Transition, achieved_goal: Any) -> float:
        """Compute reward as if achieved_goal was the intended goal."""
        # In HER, reaching the achieved goal = success
        if transition.done:
            return 1.0
        return -0.01  # small step penalty

    def sample(self, batch_size: int) -> List[Transition]:
        """Random sample from buffer."""
        if len(self.buffer) < batch_size:
            return list(self.buffer)
        indices = random.sample(range(len(self.buffer)), batch_size)
        return [self.buffer[i] for i in indices]

    def __len__(self) -> int:
        return len(self.buffer)

    def stats(self) -> Dict[str, Any]:
        return {
            "size": len(self.buffer),
            "capacity": self.capacity,
            "total_added": self.total_added,
            "total_her_relabeled": self.total_her,
            "her_ratio_actual": self.total_her / max(1, self.total_added),
        }


# ─────────────────────────────────────────────
# Simple SC2 Simulation Environment
# ─────────────────────────────────────────────


@dataclass
class SC2SimState:
    """Lightweight SC2 game state for curriculum training."""

    minerals: float = 50.0
    gas: float = 0.0
    supply_used: int = 12
    supply_max: int = 14
    workers: int = 12
    army_supply: int = 0
    army_value: float = 0.0
    bases: int = 1
    frame: int = 0
    enemy_army_value: float = 0.0
    tech_level: float = 0.0
    units_killed: int = 0
    units_lost: int = 0
    damage_dealt: float = 0.0
    damage_taken: float = 0.0
    micro_score: float = 0.0
    game_over: bool = False
    won: bool = False

    def to_obs(self, obs_dim: int) -> list:
        """Convert state to observation vector of given dimension."""
        full = [
            self.minerals / 1000.0,
            self.gas / 500.0,
            self.supply_used / 200.0,
            self.supply_max / 200.0,
            self.workers / 80.0,
            self.army_supply / 200.0,
            self.frame / 10000.0,
            self.bases / 5.0,
            # Extended features
            self.enemy_army_value / 5000.0,
            self.tech_level,
            self.army_value / 5000.0,
            self.damage_dealt / 3000.0,
            self.damage_taken / 3000.0,
            self.micro_score,
            self.units_killed / 100.0,
            self.units_lost / 100.0,
            # Derived features
            min(1.0, self.workers / max(1, self.bases * 16)),  # saturation
            self.supply_used / max(1, self.supply_max),  # supply ratio
            1.0 if self.gas > 0 else 0.0,
            min(1.0, self.army_value / max(1.0, self.enemy_army_value)),
            # Additional for full game
            min(1.0, (self.minerals + self.gas) / 2000.0),
            self.tech_level**2,
            min(1.0, self.bases / 4.0),
            self.frame / 20000.0,
            min(
                1.0, self.damage_dealt / max(1.0, self.damage_dealt + self.damage_taken)
            ),
            self.army_supply / max(1, self.supply_max),
            min(1.0, self.units_killed / max(1, self.units_killed + self.units_lost)),
            _np_clip(self.micro_score * 2.0, 0.0, 1.0),
        ]
        return [_np_clip(v, 0.0, 1.0) for v in full[:obs_dim]]


class SC2CurriculumEnv:
    """
    Simulated SC2 environment that adapts to curriculum stage and difficulty.
    """

    def __init__(self, stage_config: StageConfig, difficulty: float = 0.5):
        self.config = stage_config
        self.difficulty = difficulty
        self.state = SC2SimState()
        self.step_count = 0
        self._enemy_aggression_timer = 0

    def reset(self, difficulty: Optional[float] = None) -> list:
        """Reset environment for new episode."""
        if difficulty is not None:
            self.difficulty = difficulty
        self.state = SC2SimState()
        self.step_count = 0
        self._enemy_aggression_timer = int(200 + 300 * (1.0 - self.difficulty))
        # Scale enemy based on difficulty
        self.state.enemy_army_value = 100.0 * self.difficulty
        return self.state.to_obs(self.config.obs_dim)

    def step(self, action: int) -> Tuple[list, float, bool, Dict[str, Any]]:
        """Execute action and return (obs, reward, done, info)."""
        self.step_count += 1
        reward = 0.0
        info: Dict[str, Any] = {"action": action}

        # Income per step
        income_per_worker = 0.8 + 0.1 * min(self.state.bases, 4)
        self.state.minerals += self.state.workers * income_per_worker * 0.1
        if self.state.bases >= 2:
            self.state.gas += self.state.workers * 0.03

        self.state.frame += 16  # ~1 game second

        # Execute action based on stage
        stage = self.config.stage
        if action < len(self.config.action_names):
            act_name = self.config.action_names[action]
            reward += self._execute_action(act_name, stage)

        # Enemy pressure scaling with difficulty
        self._enemy_aggression_timer -= 1
        if self._enemy_aggression_timer <= 0:
            enemy_attack_power = (
                50.0 * self.difficulty * (1.0 + self.state.frame / 5000.0)
            )
            defense = self.state.army_value * (1.0 + self.state.micro_score * 0.3)
            if defense >= enemy_attack_power:
                self.state.damage_dealt += enemy_attack_power * 0.5
                self.state.units_killed += max(1, int(enemy_attack_power / 50))
                reward += 0.5 * self.config.reward_scale
            else:
                loss = (enemy_attack_power - defense) * 0.5
                self.state.damage_taken += loss
                self.state.army_value = max(0, self.state.army_value - loss)
                self.state.army_supply = max(0, int(self.state.army_value / 25))
                self.state.units_lost += max(1, int(loss / 30))
                reward -= 0.3 * self.config.reward_scale
                if self.state.army_value <= 0 and self.state.workers < 5:
                    self.state.game_over = True
                    self.state.won = False
            self._enemy_aggression_timer = int(100 + 200 * (1.0 - self.difficulty))
            self.state.enemy_army_value += 20.0 * self.difficulty

        # Check win conditions
        if self.state.frame >= self.config.max_game_length * 16:
            self.state.game_over = True
            score = self._compute_game_score()
            self.state.won = score > 0.5
            reward += (2.0 if self.state.won else -1.0) * self.config.reward_scale

        done = self.state.game_over
        info["won"] = self.state.won
        info["frame"] = self.state.frame
        info["score"] = self._compute_game_score()

        obs = self.state.to_obs(self.config.obs_dim)
        return obs, reward, done, info

    def _execute_action(self, action_name: str, stage: CurriculumStage) -> float:
        """Execute named action, return immediate reward."""
        s = self.state
        reward = 0.0

        if action_name == "train_drone":
            if s.minerals >= 50 and s.supply_used < s.supply_max:
                s.minerals -= 50
                s.workers += 1
                s.supply_used += 1
                reward = 0.1 if s.workers <= s.bases * 16 else -0.05

        elif action_name == "build_overlord":
            if s.minerals >= 100:
                s.minerals -= 100
                s.supply_max += 8
                needed = s.supply_used >= s.supply_max - 2
                reward = 0.15 if needed else 0.0

        elif action_name == "expand":
            if s.minerals >= 300:
                s.minerals -= 300
                s.bases += 1
                timing_bonus = 1.0 if s.workers >= s.bases * 12 else 0.3
                reward = 0.3 * timing_bonus

        elif action_name == "build_extractor":
            if s.minerals >= 25 and s.bases >= 1:
                s.minerals -= 25
                reward = 0.05

        elif action_name == "train_zergling":
            if s.minerals >= 50 and s.supply_used + 1 <= s.supply_max:
                s.minerals -= 50
                s.supply_used += 1
                s.army_supply += 1
                s.army_value += 25
                reward = 0.08

        elif action_name == "train_roach":
            if s.minerals >= 75 and s.gas >= 25 and s.supply_used + 2 <= s.supply_max:
                s.minerals -= 75
                s.gas -= 25
                s.supply_used += 2
                s.army_supply += 2
                s.army_value += 50
                reward = 0.1

        elif action_name == "train_hydra":
            if s.minerals >= 100 and s.gas >= 50 and s.supply_used + 2 <= s.supply_max:
                s.minerals -= 100
                s.gas -= 50
                s.supply_used += 2
                s.army_supply += 2
                s.army_value += 65
                reward = 0.12

        elif action_name == "train_mutalisk":
            if s.minerals >= 100 and s.gas >= 100 and s.supply_used + 2 <= s.supply_max:
                s.minerals -= 100
                s.gas -= 100
                s.supply_used += 2
                s.army_supply += 2
                s.army_value += 80
                reward = 0.15

        elif action_name == "train_ultralisk":
            if (
                s.minerals >= 275
                and s.gas >= 200
                and s.supply_used + 6 <= s.supply_max
                and s.tech_level >= 0.8
            ):
                s.minerals -= 275
                s.gas -= 200
                s.supply_used += 6
                s.army_supply += 6
                s.army_value += 200
                reward = 0.2

        elif action_name == "attack_move":
            if s.army_value > 0:
                effectiveness = (
                    s.army_value
                    / max(1.0, s.enemy_army_value)
                    * (1.0 + s.micro_score * 0.2)
                )
                if effectiveness > 1.0:
                    dealt = s.army_value * 0.3
                    s.damage_dealt += dealt
                    s.enemy_army_value = max(0, s.enemy_army_value - dealt)
                    s.units_killed += max(1, int(dealt / 40))
                    reward = 0.3
                else:
                    lost = s.enemy_army_value * 0.15
                    s.damage_taken += lost
                    s.army_value = max(0, s.army_value - lost)
                    s.units_lost += max(1, int(lost / 40))
                    reward = -0.15

        elif action_name == "defend_base":
            if s.army_value > 0:
                s.army_value *= 1.05  # defensive bonus
                reward = 0.05

        elif action_name == "focus_fire":
            if stage.value >= CurriculumStage.MICRO_CONTROL and s.army_value > 0:
                s.micro_score = min(1.0, s.micro_score + 0.1)
                s.army_value *= 1.02
                reward = 0.08

        elif action_name == "retreat_wounded":
            if stage.value >= CurriculumStage.MICRO_CONTROL:
                s.micro_score = min(1.0, s.micro_score + 0.05)
                preserved = s.army_value * 0.05
                s.army_value += preserved * 0.5  # save some units
                reward = 0.06

        elif action_name == "flank_maneuver":
            if stage.value >= CurriculumStage.MICRO_CONTROL and s.army_value > 100:
                s.micro_score = min(1.0, s.micro_score + 0.15)
                reward = 0.1

        elif action_name == "tech_upgrade":
            if s.minerals >= 150 and s.gas >= 100 and s.tech_level < 1.0:
                s.minerals -= 150
                s.gas -= 100
                s.tech_level = min(1.0, s.tech_level + 0.2)
                reward = 0.15

        return reward * self.config.reward_scale

    def _compute_game_score(self) -> float:
        """Compute overall game score for win/loss determination."""
        s = self.state
        eco = min(1.0, s.workers / 60.0) * 0.25
        army = min(1.0, s.army_value / 2000.0) * 0.25
        tech = s.tech_level * 0.15
        kd = s.units_killed / max(1, s.units_killed + s.units_lost) * 0.2
        bases = min(1.0, s.bases / 3.0) * 0.15
        return eco + army + tech + kd + bases


# ─────────────────────────────────────────────
# Performance Metrics
# ─────────────────────────────────────────────


@dataclass
class StageMetrics:
    """Performance metrics for a single curriculum stage."""

    stage: CurriculumStage
    episodes: int = 0
    wins: int = 0
    total_reward: float = 0.0
    reward_history: List[float] = field(default_factory=list)
    win_history: List[bool] = field(default_factory=list)
    difficulty_history: List[float] = field(default_factory=list)
    avg_episode_length: float = 0.0
    total_steps: int = 0
    best_reward: float = float("-inf")
    promotion_time: Optional[float] = None
    entry_time: Optional[float] = None

    @property
    def win_rate(self) -> float:
        if not self.win_history:
            return 0.0
        window = self.win_history[-50:]
        return sum(window) / len(window)

    @property
    def recent_avg_reward(self) -> float:
        if not self.reward_history:
            return 0.0
        window = self.reward_history[-50:]
        return _np_mean(window)

    @property
    def reward_std(self) -> float:
        if len(self.reward_history) < 2:
            return 0.0
        return _np_std(self.reward_history[-50:])

    def record_episode(self, reward: float, won: bool, steps: int, difficulty: float):
        self.episodes += 1
        self.total_reward += reward
        self.reward_history.append(reward)
        self.win_history.append(won)
        self.difficulty_history.append(difficulty)
        self.total_steps += steps
        self.avg_episode_length = self.total_steps / self.episodes
        if reward > self.best_reward:
            self.best_reward = reward
        if won:
            self.wins += 1

    def summary(self) -> Dict[str, Any]:
        return {
            "stage": STAGE_NAMES[self.stage],
            "episodes": self.episodes,
            "win_rate": f"{self.win_rate:.1%}",
            "avg_reward": f"{self.recent_avg_reward:.2f}",
            "reward_std": f"{self.reward_std:.2f}",
            "best_reward": f"{self.best_reward:.2f}",
            "avg_episode_length": f"{self.avg_episode_length:.0f}",
            "avg_difficulty": (
                f"{_np_mean(self.difficulty_history[-20:]):.2f}"
                if self.difficulty_history
                else "N/A"
            ),
        }


# ─────────────────────────────────────────────
# Simple Policy Network (NumPy)
# ─────────────────────────────────────────────


class SimplePolicy:
    """
    Lightweight policy using a 2-layer neural network (NumPy).
    Supports forward pass and simple policy-gradient updates.
    """

    def __init__(self, obs_dim: int, act_dim: int, hidden: int = 64, lr: float = 0.001):
        self.obs_dim = obs_dim
        self.act_dim = act_dim
        self.hidden = hidden
        self.lr = lr

        # Initialize weights (Xavier)
        scale1 = math.sqrt(2.0 / (obs_dim + hidden))
        scale2 = math.sqrt(2.0 / (hidden + act_dim))

        if NP_AVAILABLE:
            self.w1 = np.random.randn(obs_dim, hidden).astype(np.float32) * scale1
            self.b1 = np.zeros(hidden, dtype=np.float32)
            self.w2 = np.random.randn(hidden, act_dim).astype(np.float32) * scale2
            self.b2 = np.zeros(act_dim, dtype=np.float32)
        else:
            self.w1 = [
                [random.gauss(0, scale1) for _ in range(hidden)] for _ in range(obs_dim)
            ]
            self.b1 = [0.0] * hidden
            self.w2 = [
                [random.gauss(0, scale2) for _ in range(act_dim)] for _ in range(hidden)
            ]
            self.b2 = [0.0] * act_dim

    def forward(self, obs: list) -> list:
        """Forward pass returning action logits."""
        if NP_AVAILABLE:
            x = np.array(obs, dtype=np.float32)
            h = np.maximum(0, x @ self.w1 + self.b1)  # ReLU
            logits = (h @ self.w2 + self.b2).tolist()
        else:
            # Manual matmul
            h = []
            for j in range(self.hidden):
                val = self.b1[j]
                for i in range(self.obs_dim):
                    val += obs[i] * self.w1[i][j]
                h.append(max(0.0, val))  # ReLU

            logits = []
            for j in range(self.act_dim):
                val = self.b2[j]
                for i in range(self.hidden):
                    val += h[i] * self.w2[i][j]
                logits.append(val)

        return logits

    def select_action(self, obs: list, epsilon: float = 0.1) -> Tuple[int, list]:
        """Select action using softmax policy with epsilon exploration."""
        logits = self.forward(obs)
        probs = _np_softmax(logits)

        if random.random() < epsilon:
            action = random.randint(0, self.act_dim - 1)
        else:
            action = _np_random_choice(self.act_dim, p=probs)

        return action, probs

    def update(self, trajectory: List[Tuple[list, int, float]]):
        """
        Simple REINFORCE policy gradient update.
        trajectory: list of (obs, action, discounted_return)
        """
        if not trajectory:
            return

        for obs, action, G in trajectory:
            logits = self.forward(obs)
            probs = _np_softmax(logits)

            # Gradient: increase prob of action proportional to return
            grad_logits = [-p for p in probs]
            grad_logits[action] += 1.0  # d_log_softmax / d_logit

            # Scale by return
            for i in range(self.act_dim):
                grad_logits[i] *= G

            # Update output layer
            if NP_AVAILABLE:
                x = np.array(obs, dtype=np.float32)
                h = np.maximum(0, x @ self.w1 + self.b1)
                g = np.array(grad_logits, dtype=np.float32)
                self.w2 += self.lr * np.outer(h, g)
                self.b2 += self.lr * g
            else:
                # Compute hidden
                h = []
                for j in range(self.hidden):
                    val = self.b1[j]
                    for i in range(self.obs_dim):
                        val += obs[i] * self.w1[i][j]
                    h.append(max(0.0, val))

                for i in range(self.hidden):
                    for j in range(self.act_dim):
                        self.w2[i][j] += self.lr * h[i] * grad_logits[j]
                for j in range(self.act_dim):
                    self.b2[j] += self.lr * grad_logits[j]


# ─────────────────────────────────────────────
# SC2 Curriculum Trainer
# ─────────────────────────────────────────────


class SC2CurriculumTrainer:
    """
    Progressive curriculum RL trainer for StarCraft II.

    Advances the agent through four stages of increasing complexity:
    1) Economy -> 2) Basic Combat -> 3) Micro Control -> 4) Full Game

    Features:
    - Automatic promotion based on win rate threshold
    - Adaptive difficulty scheduling per stage
    - Hindsight Experience Replay for sample efficiency
    - Per-stage performance tracking and visualization
    """

    def __init__(
        self,
        start_stage: CurriculumStage = CurriculumStage.ECONOMY,
        gamma: float = 0.99,
        epsilon_start: float = 0.3,
        epsilon_end: float = 0.05,
        epsilon_decay: float = 0.995,
        replay_capacity: int = 50_000,
        her_ratio: float = 0.8,
        batch_size: int = 32,
        lr: float = 0.001,
        hidden_size: int = 64,
        seed: Optional[int] = None,
    ):
        if seed is not None:
            random.seed(seed)
            if NP_AVAILABLE:
                np.random.seed(seed)

        self.current_stage = start_stage
        self.gamma = gamma
        self.epsilon = epsilon_start
        self.epsilon_end = epsilon_end
        self.epsilon_decay = epsilon_decay
        self.batch_size = batch_size
        self.lr = lr
        self.hidden_size = hidden_size

        # Per-stage components
        self.policies: Dict[CurriculumStage, SimplePolicy] = {}
        self.difficulty_scorers: Dict[CurriculumStage, TaskDifficultyScorer] = {}
        self.metrics: Dict[CurriculumStage, StageMetrics] = {}
        self.replay_buffers: Dict[CurriculumStage, HindsightReplayBuffer] = {}

        for stage in CurriculumStage:
            cfg = STAGE_CONFIGS[stage]
            self.policies[stage] = SimplePolicy(
                cfg.obs_dim, cfg.act_dim, hidden_size, lr
            )
            self.difficulty_scorers[stage] = TaskDifficultyScorer()
            self.metrics[stage] = StageMetrics(stage=stage)
            self.replay_buffers[stage] = HindsightReplayBuffer(
                capacity=replay_capacity, her_ratio=her_ratio
            )

        self.total_episodes = 0
        self.promotion_log: List[Dict[str, Any]] = []
        self.training_start_time = time.time()

    def _get_config(self) -> StageConfig:
        return STAGE_CONFIGS[self.current_stage]

    def train_episode(self) -> Dict[str, Any]:
        """Run one training episode in the current curriculum stage."""
        cfg = self._get_config()
        scorer = self.difficulty_scorers[self.current_stage]
        difficulty = scorer.next_difficulty(*cfg.difficulty_range)

        env = SC2CurriculumEnv(cfg, difficulty)
        policy = self.policies[self.current_stage]
        replay = self.replay_buffers[self.current_stage]

        obs = env.reset(difficulty)
        trajectory: List[Tuple[list, int, float]] = []
        episode_reward = 0.0
        done = False
        step_count = 0

        while not done:
            action, probs = policy.select_action(obs, self.epsilon)
            next_obs, reward, done, info = env.step(action)

            replay.add(
                Transition(
                    state=obs,
                    action=action,
                    reward=reward,
                    next_state=next_obs,
                    done=done,
                    goal=None,
                    info=info,
                )
            )

            trajectory.append((obs, action, reward))
            episode_reward += reward
            obs = next_obs
            step_count += 1

            if step_count >= cfg.max_game_length:
                done = True

        # Compute discounted returns for REINFORCE
        returns: List[float] = []
        G = 0.0
        for _, _, r in reversed(trajectory):
            G = r + self.gamma * G
            returns.insert(0, G)

        # Normalize returns
        if len(returns) > 1:
            mean_r = _np_mean(returns)
            std_r = _np_std(returns)
            if std_r > 1e-8:
                returns = [(r - mean_r) / std_r for r in returns]

        # Build training data
        training_data = [(obs, act, G) for (obs, act, _), G in zip(trajectory, returns)]

        # Update policy
        policy.update(training_data)

        # End episode in replay buffer (with HER)
        won = info.get("won", False)
        achieved = {"score": info.get("score", 0.0), "frame": env.state.frame}
        replay.end_episode(achieved_goal=achieved, success=won)

        # Record metrics
        scorer.record_result(difficulty, won)
        self.metrics[self.current_stage].record_episode(
            episode_reward, won, step_count, difficulty
        )

        # Decay epsilon
        self.epsilon = max(self.epsilon_end, self.epsilon * self.epsilon_decay)

        self.total_episodes += 1

        # Check promotion
        promoted = self._check_promotion()

        return {
            "episode": self.total_episodes,
            "stage": STAGE_NAMES[self.current_stage],
            "reward": episode_reward,
            "won": won,
            "steps": step_count,
            "difficulty": difficulty,
            "epsilon": self.epsilon,
            "win_rate": self.metrics[self.current_stage].win_rate,
            "promoted": promoted,
        }

    def _check_promotion(self) -> bool:
        """Check if agent should be promoted to next curriculum stage."""
        cfg = self._get_config()
        m = self.metrics[self.current_stage]

        if m.episodes < cfg.min_episodes_before_promotion:
            return False

        if m.win_rate >= cfg.promotion_win_rate:
            if self.current_stage < CurriculumStage.FULL_GAME:
                old_stage = self.current_stage
                m.promotion_time = time.time() - self.training_start_time

                self.current_stage = CurriculumStage(self.current_stage + 1)
                self.metrics[self.current_stage].entry_time = (
                    time.time() - self.training_start_time
                )

                # Transfer knowledge: initialize new policy from old
                self._transfer_weights(old_stage, self.current_stage)

                self.promotion_log.append(
                    {
                        "from_stage": STAGE_NAMES[old_stage],
                        "to_stage": STAGE_NAMES[self.current_stage],
                        "episode": self.total_episodes,
                        "win_rate": m.win_rate,
                        "time_elapsed": m.promotion_time,
                    }
                )
                return True
        return False

    def _transfer_weights(self, from_stage: CurriculumStage, to_stage: CurriculumStage):
        """
        Transfer learned weights from previous stage to next stage.
        Copies overlapping dimensions.
        """
        old_p = self.policies[from_stage]
        new_p = self.policies[to_stage]

        min_obs = min(old_p.obs_dim, new_p.obs_dim)
        min_hid = min(old_p.hidden, new_p.hidden)
        min_act = min(old_p.act_dim, new_p.act_dim)

        if NP_AVAILABLE:
            new_p.w1[:min_obs, :min_hid] = old_p.w1[:min_obs, :min_hid].copy()
            new_p.b1[:min_hid] = old_p.b1[:min_hid].copy()
            new_p.w2[:min_hid, :min_act] = old_p.w2[:min_hid, :min_act].copy()
            new_p.b2[:min_act] = old_p.b2[:min_act].copy()
        else:
            for i in range(min_obs):
                for j in range(min_hid):
                    new_p.w1[i][j] = old_p.w1[i][j]
            for j in range(min_hid):
                new_p.b1[j] = old_p.b1[j]
            for i in range(min_hid):
                for j in range(min_act):
                    new_p.w2[i][j] = old_p.w2[i][j]
            for j in range(min_act):
                new_p.b2[j] = old_p.b2[j]

    def train(
        self, total_episodes: int = 500, log_interval: int = 25, verbose: bool = True
    ) -> Dict[str, Any]:
        """
        Run full curriculum training loop.

        Args:
            total_episodes: Maximum episodes to train
            log_interval: Print progress every N episodes
            verbose: Whether to print progress

        Returns:
            Training summary dictionary
        """
        if verbose:
            print("=" * 70)
            print("  SC2 Curriculum Trainer - Training Start")
            print(f"  Starting stage: {STAGE_NAMES[self.current_stage]}")
            print(f"  Total episodes: {total_episodes}")
            print("=" * 70)

        for ep in range(total_episodes):
            result = self.train_episode()

            if verbose and (ep + 1) % log_interval == 0:
                print(
                    f"  Ep {result['episode']:4d} | "
                    f"Stage: {result['stage']:<14s} | "
                    f"R: {result['reward']:7.2f} | "
                    f"WR: {result['win_rate']:.1%} | "
                    f"Diff: {result['difficulty']:.2f} | "
                    f"Eps: {result['epsilon']:.3f}"
                )

            if result.get("promoted"):
                if verbose:
                    print(
                        f"\n  >>> PROMOTED to {STAGE_NAMES[self.current_stage]}! <<<\n"
                    )

        return self.training_summary()

    def training_summary(self) -> Dict[str, Any]:
        """Generate comprehensive training summary."""
        summary = {
            "total_episodes": self.total_episodes,
            "final_stage": STAGE_NAMES[self.current_stage],
            "training_time": time.time() - self.training_start_time,
            "promotions": self.promotion_log,
            "stage_metrics": {},
        }
        for stage in CurriculumStage:
            m = self.metrics[stage]
            if m.episodes > 0:
                summary["stage_metrics"][STAGE_NAMES[stage]] = m.summary()
                summary["stage_metrics"][STAGE_NAMES[stage]]["replay_stats"] = (
                    self.replay_buffers[stage].stats()
                )
                summary["stage_metrics"][STAGE_NAMES[stage]][
                    "mastery"
                ] = f"{self.difficulty_scorers[stage].mastery_score():.2f}"
        return summary

    def visualize_progression(self, width: int = 60) -> str:
        """
        Generate ASCII visualization of learning progression.

        Returns:
            Multi-line string with charts showing reward and win-rate per stage.
        """
        lines = []
        lines.append("=" * 70)
        lines.append("  Learning Progression Visualization")
        lines.append("=" * 70)

        for stage in CurriculumStage:
            m = self.metrics[stage]
            if m.episodes == 0:
                continue

            lines.append(f"\n  Stage {stage.value}: {STAGE_NAMES[stage]}")
            lines.append(
                f"  Episodes: {m.episodes} | Win Rate: {m.win_rate:.1%} | "
                f"Best Reward: {m.best_reward:.2f}"
            )

            # Win rate moving average chart
            lines.append(f"\n  Win Rate (moving avg, window=10):")
            if len(m.win_history) >= 10:
                bucket_size = max(1, len(m.win_history) // width)
                chart_vals = []
                for i in range(0, len(m.win_history), bucket_size):
                    chunk = m.win_history[i : i + bucket_size]
                    chart_vals.append(sum(chunk) / len(chunk))

                max_bars = min(width, len(chart_vals))
                chart_vals = chart_vals[:max_bars]

                for row_thresh in [0.8, 0.6, 0.4, 0.2]:
                    row = f"  {row_thresh:.0%}|"
                    for v in chart_vals:
                        row += "#" if v >= row_thresh else " "
                    lines.append(row)
                lines.append(f"    +" + "-" * len(chart_vals))
            else:
                lines.append("    (insufficient data)")

            # Reward trend
            lines.append(f"\n  Reward Trend (last 20 episodes):")
            recent = m.reward_history[-20:]
            if recent:
                r_min = min(recent)
                r_max = max(recent)
                r_range = r_max - r_min if r_max > r_min else 1.0
                bar_width = 40
                for i, r in enumerate(recent):
                    norm = (r - r_min) / r_range
                    bar_len = int(norm * bar_width)
                    lines.append(f"    {i:2d}|{'#' * bar_len}")

            # Difficulty progression
            if m.difficulty_history:
                lines.append(
                    f"\n  Difficulty: {m.difficulty_history[0]:.2f} -> "
                    f"{m.difficulty_history[-1]:.2f} "
                    f"(avg: {_np_mean(m.difficulty_history):.2f})"
                )

            # Promotion marker
            if m.promotion_time is not None:
                lines.append(
                    f"  Promoted at episode {m.episodes} "
                    f"(t={m.promotion_time:.1f}s)"
                )

        # Overall summary
        lines.append("\n" + "=" * 70)
        lines.append("  Overall Progress:")
        reached = max(
            (s for s in CurriculumStage if self.metrics[s].episodes > 0),
            default=CurriculumStage.ECONOMY,
        )
        progress_bar = ""
        for s in CurriculumStage:
            if s.value <= reached.value:
                progress_bar += f"[{STAGE_NAMES[s]}]-->"
            else:
                progress_bar += f"({STAGE_NAMES[s]})-->"
        lines.append(f"  {progress_bar[:-3]}")
        lines.append(f"  Promotions: {len(self.promotion_log)}")
        lines.append(f"  Total Episodes: {self.total_episodes}")
        lines.append("=" * 70)

        return "\n".join(lines)

    def save_checkpoint(self, path: str):
        """Save training state to JSON."""
        data = {
            "current_stage": self.current_stage.value,
            "total_episodes": self.total_episodes,
            "epsilon": self.epsilon,
            "promotion_log": self.promotion_log,
            "stage_metrics": {},
        }
        for stage in CurriculumStage:
            m = self.metrics[stage]
            data["stage_metrics"][stage.value] = {
                "episodes": m.episodes,
                "wins": m.wins,
                "total_reward": m.total_reward,
                "best_reward": m.best_reward,
                "avg_episode_length": m.avg_episode_length,
            }
        with open(path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)

    def load_checkpoint(self, path: str):
        """Load training state from JSON."""
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
        self.current_stage = CurriculumStage(data["current_stage"])
        self.total_episodes = data["total_episodes"]
        self.epsilon = data["epsilon"]
        self.promotion_log = data["promotion_log"]


# ─────────────────────────────────────────────
# CLI Demo
# ─────────────────────────────────────────────


def demo_single_stage():
    """Demo: train a single curriculum stage."""
    print("\n--- Single Stage Demo (Economy) ---\n")
    trainer = SC2CurriculumTrainer(
        start_stage=CurriculumStage.ECONOMY,
        seed=42,
    )
    for i in range(30):
        result = trainer.train_episode()
        if (i + 1) % 10 == 0:
            print(
                f"  Episode {result['episode']:3d}: "
                f"reward={result['reward']:.2f}, "
                f"won={result['won']}, "
                f"wr={result['win_rate']:.1%}, "
                f"diff={result['difficulty']:.2f}"
            )

    m = trainer.metrics[CurriculumStage.ECONOMY]
    print(f"\n  Summary: {m.summary()}")


def demo_full_curriculum():
    """Demo: full curriculum training with progression."""
    print("\n--- Full Curriculum Training Demo ---\n")
    trainer = SC2CurriculumTrainer(
        start_stage=CurriculumStage.ECONOMY,
        epsilon_start=0.3,
        epsilon_decay=0.99,
        seed=123,
    )
    summary = trainer.train(total_episodes=200, log_interval=20)

    print("\n--- Training Summary ---")
    print(f"  Final stage: {summary['final_stage']}")
    print(f"  Promotions: {len(summary['promotions'])}")
    for p in summary["promotions"]:
        print(
            f"    {p['from_stage']} -> {p['to_stage']} "
            f"(ep {p['episode']}, wr {p['win_rate']:.1%})"
        )
    print(f"\n  Stage Metrics:")
    for name, metrics in summary["stage_metrics"].items():
        print(f"    {name}: {metrics}")

    print("\n" + trainer.visualize_progression())


def demo_her_buffer():
    """Demo: Hindsight Experience Replay buffer."""
    print("\n--- HER Buffer Demo ---\n")
    buf = HindsightReplayBuffer(capacity=1000, her_ratio=0.8)

    for ep in range(10):
        for step in range(20):
            t = Transition(
                state=[random.random() for _ in range(8)],
                action=random.randint(0, 3),
                reward=random.gauss(0, 1),
                next_state=[random.random() for _ in range(8)],
                done=(step == 19),
            )
            buf.add(t)
        buf.end_episode(
            achieved_goal={"score": random.random()},
            success=(random.random() > 0.6),
        )

    print(f"  Buffer stats: {buf.stats()}")
    sample = buf.sample(5)
    print(f"  Sampled {len(sample)} transitions")
    for i, t in enumerate(sample):
        print(
            f"    [{i}] action={t.action}, reward={t.reward:.2f}, "
            f"her={t.info.get('her_relabeled', False)}"
        )


def demo_difficulty_scorer():
    """Demo: adaptive difficulty scoring."""
    print("\n--- Difficulty Scorer Demo ---\n")
    scorer = TaskDifficultyScorer()
    for i in range(50):
        d = scorer.next_difficulty(0.0, 1.0)
        success = random.random() < (0.8 - d * 0.5)
        scorer.record_result(d, success)
        if (i + 1) % 10 == 0:
            print(
                f"  Step {i+1:3d}: difficulty={d:.3f}, "
                f"ema_success={scorer.ema_success:.3f}, "
                f"mastery={scorer.mastery_score():.3f}"
            )


def main():
    """Main CLI entry point."""
    import argparse

    parser = argparse.ArgumentParser(
        description="Phase 612: SC2 Curriculum Learning Trainer"
    )
    parser.add_argument(
        "--demo",
        choices=["single", "full", "her", "difficulty", "all"],
        default="all",
        help="Demo to run",
    )
    parser.add_argument(
        "--episodes", type=int, default=200, help="Training episodes for full demo"
    )
    parser.add_argument("--seed", type=int, default=42, help="Random seed")
    args = parser.parse_args()

    print("=" * 70)
    print("  Phase 612: SC2 Curriculum Learning Trainer")
    print(f"  NumPy available: {NP_AVAILABLE}")
    print("=" * 70)

    demos = {
        "single": demo_single_stage,
        "full": demo_full_curriculum,
        "her": demo_her_buffer,
        "difficulty": demo_difficulty_scorer,
    }

    if args.demo == "all":
        for name, fn in demos.items():
            fn()
    else:
        demos[args.demo]()

    print("\nPhase 612 demo complete.")


if __name__ == "__main__":
    main()
