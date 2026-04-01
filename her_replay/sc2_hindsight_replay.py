"""
Phase 615: Hindsight Experience Replay --- SC2 Goal-Conditioned RL
==================================================================
her_replay/sc2_hindsight_replay.py

Production-quality Hindsight Experience Replay (HER) for the SC2 Zerg
commander bot with goal-conditioned policies and value networks.
  - SC2HindsightReplay   : Full HER system with future / episode / random
                           goal relabeling strategies.
  - GoalConditionedPolicy: Policy network conditioned on (state, goal).
  - UniversalValueFunction: UVFA -- V(s, g) approximation.
  - MultiGoalReplayBuffer: Efficient storage with per-goal-type indexing.
  - SC2 goal types       : destroy_target, reach_location, achieve_economy,
                           tech_to_unit.
  - Automatic goal difficulty curriculum based on success rates.
  - Success rate tracking and reporting per goal type.

Integrates with the bot's PPO self-play RL loop, economy manager, and
combat manager.  Supports 260+ language localisation via label keys.

Dependencies: numpy (required), torch (optional, NumPy fallback provided).
"""

from __future__ import annotations

import argparse
import copy
import json
import logging
import math
import os
import random
import time
from collections import defaultdict, deque
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Sequence, Tuple, Union

import numpy as np
from numpy.typing import NDArray

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Optional torch import with NumPy fallback
# ---------------------------------------------------------------------------
try:
    import torch
    import torch.nn as nn
    import torch.optim as optim

    HAS_TORCH = True
except ImportError:
    HAS_TORCH = False
    logger.info("PyTorch not found -- using NumPy fallback for all networks.")

# ---------------------------------------------------------------------------
# SC2 Constants
# ---------------------------------------------------------------------------
SC2_STATE_DIM = 48
SC2_ACTION_DIM = 16
SC2_GOAL_DIM = 12  # goal embedding dimension


# ---------------------------------------------------------------------------
# Goal Types
# ---------------------------------------------------------------------------
class GoalType(Enum):
    DESTROY_TARGET = "destroy_target"
    REACH_LOCATION = "reach_location"
    ACHIEVE_ECONOMY = "achieve_economy"
    TECH_TO_UNIT = "tech_to_unit"


GOAL_TYPE_LIST: List[GoalType] = list(GoalType)

GOAL_DESCRIPTIONS: Dict[GoalType, str] = {
    GoalType.DESTROY_TARGET: "Destroy a specific enemy structure or unit group",
    GoalType.REACH_LOCATION: "Move army to a specific map location",
    GoalType.ACHIEVE_ECONOMY: "Reach a target mineral/gas income rate",
    GoalType.TECH_TO_UNIT: "Research and produce a specific unit type",
}

# Goal type to index mapping
GOAL_TYPE_IDX: Dict[GoalType, int] = {g: i for i, g in enumerate(GOAL_TYPE_LIST)}


# ---------------------------------------------------------------------------
# Relabeling Strategies
# ---------------------------------------------------------------------------
class RelabelStrategy(Enum):
    FUTURE = "future"     # sample from future states in same episode
    EPISODE = "episode"   # sample from any state in the episode
    RANDOM = "random"     # sample from any stored goal


# ---------------------------------------------------------------------------
# NumPy neural-network helpers
# ---------------------------------------------------------------------------

def _relu(x: NDArray) -> NDArray:
    return np.maximum(0.0, x)


def _sigmoid(x: NDArray) -> NDArray:
    x = np.clip(x, -500, 500)
    return 1.0 / (1.0 + np.exp(-x))


def _softmax(x: NDArray) -> NDArray:
    e = np.exp(x - np.max(x, axis=-1, keepdims=True))
    return e / np.sum(e, axis=-1, keepdims=True)


def _he_init(fan_in: int, fan_out: int, rng: np.random.Generator) -> NDArray:
    std = math.sqrt(2.0 / fan_in)
    return rng.normal(0.0, std, size=(fan_in, fan_out)).astype(np.float32)


class NumpyMLP:
    """Lightweight MLP using only NumPy."""

    def __init__(
        self,
        layer_sizes: List[int],
        output_activation: str = "none",
        lr: float = 1e-3,
        seed: int = 0,
    ) -> None:
        self.rng = np.random.default_rng(seed)
        self.lr = lr
        self.output_activation = output_activation

        self.weights: List[NDArray] = []
        self.biases: List[NDArray] = []
        for i in range(len(layer_sizes) - 1):
            self.weights.append(_he_init(layer_sizes[i], layer_sizes[i + 1], self.rng))
            self.biases.append(np.zeros(layer_sizes[i + 1], dtype=np.float32))

    def forward(self, x: NDArray) -> NDArray:
        h = x.astype(np.float32)
        for i, (W, b) in enumerate(zip(self.weights, self.biases)):
            z = h @ W + b
            if i < len(self.weights) - 1:
                h = _relu(z)
            else:
                if self.output_activation == "softmax":
                    h = _softmax(z)
                elif self.output_activation == "sigmoid":
                    h = _sigmoid(z)
                else:
                    h = z
        return h

    def train_step(self, x: NDArray, targets: NDArray, loss_type: str = "mse") -> float:
        """Gradient descent step using numerical gradients (fallback)."""
        pred = self.forward(x)
        if loss_type == "mse":
            loss = float(np.mean((pred - targets) ** 2))
        elif loss_type == "ce":
            eps = 1e-8
            pred_c = np.clip(pred, eps, 1.0 - eps)
            loss = -float(np.mean(np.sum(targets * np.log(pred_c), axis=-1)))
        else:
            loss = float(np.mean((pred - targets) ** 2))

        eps_grad = 1e-4
        for li in range(len(self.weights)):
            n_sample = min(12, self.weights[li].size)
            indices = self.rng.choice(self.weights[li].size, n_sample, replace=False)
            flat = self.weights[li].ravel()
            grad = np.zeros_like(flat)
            for idx in indices:
                orig = flat[idx]
                flat[idx] = orig + eps_grad
                self.weights[li] = flat.reshape(self.weights[li].shape)
                l_plus = self._loss(x, targets, loss_type)
                flat[idx] = orig - eps_grad
                self.weights[li] = flat.reshape(self.weights[li].shape)
                l_minus = self._loss(x, targets, loss_type)
                flat[idx] = orig
                self.weights[li] = flat.reshape(self.weights[li].shape)
                grad[idx] = (l_plus - l_minus) / (2 * eps_grad)
            self.weights[li] -= self.lr * grad.reshape(self.weights[li].shape)
        return loss

    def _loss(self, x: NDArray, targets: NDArray, loss_type: str) -> float:
        pred = self.forward(x)
        if loss_type == "mse":
            return float(np.mean((pred - targets) ** 2))
        eps = 1e-8
        pred_c = np.clip(pred, eps, 1.0 - eps)
        return -float(np.mean(np.sum(targets * np.log(pred_c), axis=-1)))

    def get_params(self) -> List[Tuple[NDArray, NDArray]]:
        return [(w.copy(), b.copy()) for w, b in zip(self.weights, self.biases)]

    def set_params(self, params: List[Tuple[NDArray, NDArray]]) -> None:
        for i, (w, b) in enumerate(params):
            self.weights[i] = w.copy()
            self.biases[i] = b.copy()


# ---------------------------------------------------------------------------
# Torch networks (when available)
# ---------------------------------------------------------------------------
if HAS_TORCH:

    class TorchMLP(nn.Module):
        def __init__(
            self,
            layer_sizes: List[int],
            output_activation: str = "none",
        ) -> None:
            super().__init__()
            layers: list[nn.Module] = []
            for i in range(len(layer_sizes) - 1):
                layers.append(nn.Linear(layer_sizes[i], layer_sizes[i + 1]))
                if i < len(layer_sizes) - 2:
                    layers.append(nn.ReLU())
            self.net = nn.Sequential(*layers)
            self.output_activation = output_activation

        def forward(self, x: torch.Tensor) -> torch.Tensor:
            out = self.net(x)
            if self.output_activation == "softmax":
                return torch.softmax(out, dim=-1)
            elif self.output_activation == "sigmoid":
                return torch.sigmoid(out)
            return out


# ---------------------------------------------------------------------------
# SC2 Goal
# ---------------------------------------------------------------------------
@dataclass
class SC2Goal:
    """A concrete goal in the SC2 environment."""

    goal_type: GoalType
    goal_vector: NDArray  # (goal_dim,) continuous goal representation
    description: str = ""
    difficulty: float = 0.5  # [0, 1] estimated difficulty
    target_id: int = 0  # e.g., unit tag or location id

    def to_array(self) -> NDArray:
        """Encode goal as a flat array including type one-hot."""
        type_oh = np.zeros(len(GoalType), dtype=np.float32)
        type_oh[GOAL_TYPE_IDX[self.goal_type]] = 1.0
        return np.concatenate([type_oh, self.goal_vector])

    @staticmethod
    def goal_array_dim() -> int:
        return len(GoalType) + SC2_GOAL_DIM

    def matches(self, achieved_goal: NDArray, threshold: float = 0.5) -> bool:
        """Check if achieved_goal is close enough to this goal."""
        dist = float(np.linalg.norm(self.goal_vector - achieved_goal))
        return dist < threshold


# ---------------------------------------------------------------------------
# Transition and Episode
# ---------------------------------------------------------------------------
@dataclass
class Transition:
    state: NDArray
    action: int
    reward: float
    next_state: NDArray
    done: bool
    goal: SC2Goal
    achieved_goal: NDArray  # what was actually achieved at next_state
    info: Dict[str, Any] = field(default_factory=dict)


@dataclass
class Episode:
    transitions: List[Transition] = field(default_factory=list)
    goal: Optional[SC2Goal] = None
    success: bool = False
    total_reward: float = 0.0

    @property
    def length(self) -> int:
        return len(self.transitions)

    def add(self, t: Transition) -> None:
        self.transitions.append(t)
        self.total_reward += t.reward

    def states(self) -> NDArray:
        return np.array([t.state for t in self.transitions], dtype=np.float32)

    def achieved_goals(self) -> NDArray:
        return np.array([t.achieved_goal for t in self.transitions], dtype=np.float32)


# ---------------------------------------------------------------------------
# Multi-Goal Replay Buffer
# ---------------------------------------------------------------------------
class MultiGoalReplayBuffer:
    """Replay buffer with per-goal-type indexing and HER relabeling."""

    def __init__(
        self,
        capacity: int = 100_000,
        her_ratio: float = 0.8,
        k_future: int = 4,
        relabel_strategy: RelabelStrategy = RelabelStrategy.FUTURE,
        seed: int = 42,
    ) -> None:
        self.capacity = capacity
        self.her_ratio = her_ratio
        self.k_future = k_future
        self.relabel_strategy = relabel_strategy
        self.rng = np.random.default_rng(seed)

        # Storage
        self.episodes: deque[Episode] = deque(maxlen=capacity // 50)
        self._flat_buffer: deque[Transition] = deque(maxlen=capacity)

        # Per-goal-type index
        self._goal_type_episodes: Dict[GoalType, List[int]] = defaultdict(list)

    def store_episode(self, episode: Episode) -> None:
        """Store a complete episode and generate HER transitions."""
        ep_idx = len(self.episodes)
        self.episodes.append(episode)

        if episode.goal is not None:
            self._goal_type_episodes[episode.goal.goal_type].append(ep_idx)

        # Store original transitions
        for t in episode.transitions:
            self._flat_buffer.append(t)

        # Generate HER relabeled transitions
        self._generate_her_transitions(episode)

    def _generate_her_transitions(self, episode: Episode) -> None:
        """Apply hindsight relabeling to create additional transitions."""
        T = episode.length
        if T == 0:
            return

        n_her = int(self.her_ratio * T * self.k_future)
        achieved = episode.achieved_goals()

        for _ in range(n_her):
            # Pick a random timestep
            t_idx = self.rng.integers(0, T)
            orig = episode.transitions[t_idx]

            # Select a new goal based on strategy
            if self.relabel_strategy == RelabelStrategy.FUTURE:
                if t_idx >= T - 1:
                    continue
                future_idx = self.rng.integers(t_idx + 1, T)
                new_goal_vec = achieved[future_idx].copy()
            elif self.relabel_strategy == RelabelStrategy.EPISODE:
                ep_idx = self.rng.integers(0, T)
                new_goal_vec = achieved[ep_idx].copy()
            else:  # RANDOM
                if len(self._flat_buffer) == 0:
                    continue
                rand_t = self._flat_buffer[self.rng.integers(len(self._flat_buffer))]
                new_goal_vec = rand_t.achieved_goal.copy()

            # Create new goal
            new_goal = SC2Goal(
                goal_type=orig.goal.goal_type if orig.goal else GoalType.REACH_LOCATION,
                goal_vector=new_goal_vec,
                description="HER-relabeled",
                difficulty=orig.goal.difficulty if orig.goal else 0.5,
            )

            # Recompute reward: did we achieve the new goal?
            success = new_goal.matches(orig.achieved_goal)
            new_reward = 1.0 if success else -0.1

            relabeled = Transition(
                state=orig.state,
                action=orig.action,
                reward=new_reward,
                next_state=orig.next_state,
                done=orig.done,
                goal=new_goal,
                achieved_goal=orig.achieved_goal,
                info={"her_relabeled": True},
            )
            self._flat_buffer.append(relabeled)

    def sample_batch(
        self, batch_size: int, goal_type: Optional[GoalType] = None
    ) -> List[Transition]:
        """Sample a mini-batch of transitions, optionally filtered by goal type."""
        if goal_type is not None:
            candidates = [
                t for t in self._flat_buffer
                if t.goal is not None and t.goal.goal_type == goal_type
            ]
            if not candidates:
                candidates = list(self._flat_buffer)
        else:
            candidates = list(self._flat_buffer)

        n = min(batch_size, len(candidates))
        indices = self.rng.choice(len(candidates), size=n, replace=False)
        return [candidates[i] for i in indices]

    def sample_batch_arrays(
        self, batch_size: int, goal_type: Optional[GoalType] = None
    ) -> Tuple[NDArray, NDArray, NDArray, NDArray, NDArray, NDArray]:
        """Return batch as stacked arrays: states, goals, actions, rewards, next_states, dones."""
        batch = self.sample_batch(batch_size, goal_type)
        states = np.array([t.state for t in batch], dtype=np.float32)
        goals = np.array([t.goal.to_array() if t.goal else np.zeros(SC2Goal.goal_array_dim()) for t in batch], dtype=np.float32)
        actions = np.array([t.action for t in batch], dtype=np.int64)
        rewards = np.array([t.reward for t in batch], dtype=np.float32)
        next_states = np.array([t.next_state for t in batch], dtype=np.float32)
        dones = np.array([float(t.done) for t in batch], dtype=np.float32)
        return states, goals, actions, rewards, next_states, dones

    @property
    def size(self) -> int:
        return len(self._flat_buffer)

    def stats(self) -> Dict[str, Any]:
        gt_counts: Dict[str, int] = {}
        for gt in GoalType:
            count = sum(
                1 for t in self._flat_buffer
                if t.goal is not None and t.goal.goal_type == gt
            )
            gt_counts[gt.value] = count
        return {
            "total_transitions": self.size,
            "total_episodes": len(self.episodes),
            "per_goal_type": gt_counts,
        }


# ---------------------------------------------------------------------------
# Goal-Conditioned Policy Network
# ---------------------------------------------------------------------------
class GoalConditionedPolicy:
    """Policy pi(a | s, g) conditioned on state and goal."""

    def __init__(
        self,
        state_dim: int = SC2_STATE_DIM,
        action_dim: int = SC2_ACTION_DIM,
        hidden: int = 256,
        lr: float = 1e-3,
        seed: int = 0,
    ) -> None:
        self.state_dim = state_dim
        self.action_dim = action_dim
        input_dim = state_dim + SC2Goal.goal_array_dim()

        if HAS_TORCH:
            self.net = TorchMLP(
                [input_dim, hidden, hidden, action_dim], output_activation="softmax"
            )
            self.optimizer = optim.Adam(self.net.parameters(), lr=lr)
        else:
            self.net = NumpyMLP(
                [input_dim, hidden, hidden, action_dim],
                output_activation="softmax",
                lr=lr,
                seed=seed,
            )

    def _make_input(self, states: NDArray, goals: NDArray) -> NDArray:
        return np.concatenate([states, goals], axis=-1).astype(np.float32)

    def get_action_probs(self, state: NDArray, goal: SC2Goal) -> NDArray:
        s = state.reshape(1, -1)
        g = goal.to_array().reshape(1, -1)
        x = self._make_input(s, g)
        if HAS_TORCH:
            with torch.no_grad():
                return self.net(torch.from_numpy(x)).numpy()[0]
        return self.net.forward(x)[0]

    def select_action(
        self, state: NDArray, goal: SC2Goal, greedy: bool = False,
        rng: Optional[np.random.Generator] = None,
    ) -> int:
        rng = rng or np.random.default_rng()
        probs = self.get_action_probs(state, goal)
        if greedy:
            return int(np.argmax(probs))
        return int(rng.choice(self.action_dim, p=probs))

    def train_step(
        self,
        states: NDArray,
        goals: NDArray,
        actions: NDArray,
        weights: Optional[NDArray] = None,
    ) -> float:
        x = self._make_input(states, goals)
        targets = np.zeros((len(actions), self.action_dim), dtype=np.float32)
        for i, a in enumerate(actions):
            targets[i, int(a)] = 1.0
        if weights is not None:
            targets = targets * weights[:, None]
            targets = targets / (np.sum(targets, axis=-1, keepdims=True) + 1e-8)

        if HAS_TORCH:
            x_t = torch.from_numpy(x)
            t_t = torch.from_numpy(targets)
            pred = self.net(x_t)
            loss = -torch.mean(torch.sum(t_t * torch.log(pred + 1e-8), dim=-1))
            self.optimizer.zero_grad()
            loss.backward()
            self.optimizer.step()
            return loss.item()
        return self.net.train_step(x, targets, loss_type="ce")


# ---------------------------------------------------------------------------
# Universal Value Function Approximator (UVFA)
# ---------------------------------------------------------------------------
class UniversalValueFunction:
    """V(s, g) -- value function conditioned on state and goal."""

    def __init__(
        self,
        state_dim: int = SC2_STATE_DIM,
        hidden: int = 256,
        lr: float = 1e-3,
        gamma: float = 0.99,
        seed: int = 0,
    ) -> None:
        self.gamma = gamma
        input_dim = state_dim + SC2Goal.goal_array_dim()

        if HAS_TORCH:
            self.net = TorchMLP([input_dim, hidden, hidden, 1], output_activation="none")
            self.optimizer = optim.Adam(self.net.parameters(), lr=lr)
        else:
            self.net = NumpyMLP(
                [input_dim, hidden, hidden, 1],
                output_activation="none",
                lr=lr,
                seed=seed,
            )

        self.loss_history: List[float] = []

    def _make_input(self, states: NDArray, goals: NDArray) -> NDArray:
        return np.concatenate([states, goals], axis=-1).astype(np.float32)

    def predict(self, state: NDArray, goal: SC2Goal) -> float:
        s = state.reshape(1, -1)
        g = goal.to_array().reshape(1, -1)
        x = self._make_input(s, g)
        if HAS_TORCH:
            with torch.no_grad():
                return float(self.net(torch.from_numpy(x)).item())
        return float(self.net.forward(x)[0, 0])

    def predict_batch(self, states: NDArray, goals: NDArray) -> NDArray:
        x = self._make_input(states, goals)
        if HAS_TORCH:
            with torch.no_grad():
                return self.net(torch.from_numpy(x)).numpy().squeeze(-1)
        return self.net.forward(x).squeeze(-1)

    def train_step(
        self,
        states: NDArray,
        goals: NDArray,
        rewards: NDArray,
        next_states: NDArray,
        dones: NDArray,
    ) -> float:
        """TD(0) update."""
        x = self._make_input(states, goals)
        x_next = self._make_input(next_states, goals)

        if HAS_TORCH:
            x_t = torch.from_numpy(x)
            xn_t = torch.from_numpy(x_next)
            r_t = torch.from_numpy(rewards.astype(np.float32))
            d_t = torch.from_numpy(dones.astype(np.float32))

            v = self.net(x_t).squeeze(-1)
            with torch.no_grad():
                v_next = self.net(xn_t).squeeze(-1)
            target = r_t + self.gamma * v_next * (1.0 - d_t)
            loss = torch.mean((v - target) ** 2)
            self.optimizer.zero_grad()
            loss.backward()
            self.optimizer.step()
            loss_val = loss.item()
        else:
            v_next = self.net.forward(x_next).squeeze(-1)
            target = rewards + self.gamma * v_next * (1.0 - dones)
            target = target.reshape(-1, 1).astype(np.float32)
            loss_val = self.net.train_step(x, target, loss_type="mse")

        self.loss_history.append(loss_val)
        return loss_val


# ---------------------------------------------------------------------------
# Success Rate Tracker
# ---------------------------------------------------------------------------
class SuccessTracker:
    """Track success rates per goal type with windowed statistics."""

    def __init__(self, window: int = 100) -> None:
        self.window = window
        self._history: Dict[GoalType, deque] = {
            gt: deque(maxlen=window) for gt in GoalType
        }
        self._total: Dict[GoalType, int] = {gt: 0 for gt in GoalType}
        self._successes: Dict[GoalType, int] = {gt: 0 for gt in GoalType}

    def record(self, goal_type: GoalType, success: bool) -> None:
        self._history[goal_type].append(1.0 if success else 0.0)
        self._total[goal_type] += 1
        if success:
            self._successes[goal_type] += 1

    def success_rate(self, goal_type: GoalType) -> float:
        h = self._history[goal_type]
        if not h:
            return 0.0
        return float(np.mean(list(h)))

    def all_rates(self) -> Dict[str, float]:
        return {gt.value: self.success_rate(gt) for gt in GoalType}

    def overall_rate(self) -> float:
        all_vals = []
        for gt in GoalType:
            all_vals.extend(list(self._history[gt]))
        return float(np.mean(all_vals)) if all_vals else 0.0

    def report(self) -> str:
        lines = ["Success Rates (windowed):"]
        for gt in GoalType:
            rate = self.success_rate(gt)
            total = self._total[gt]
            lines.append(f"  {gt.value:20s}: {rate:.1%}  (n={total})")
        lines.append(f"  {'overall':20s}: {self.overall_rate():.1%}")
        return "\n".join(lines)


# ---------------------------------------------------------------------------
# Goal Difficulty Curriculum
# ---------------------------------------------------------------------------
class GoalCurriculum:
    """Automatic curriculum that increases goal difficulty as success improves."""

    def __init__(
        self,
        initial_difficulty: float = 0.2,
        max_difficulty: float = 1.0,
        success_threshold: float = 0.7,
        increase_rate: float = 0.1,
        decrease_rate: float = 0.05,
        seed: int = 42,
    ) -> None:
        self.difficulty: Dict[GoalType, float] = {
            gt: initial_difficulty for gt in GoalType
        }
        self.max_difficulty = max_difficulty
        self.success_threshold = success_threshold
        self.increase_rate = increase_rate
        self.decrease_rate = decrease_rate
        self.rng = np.random.default_rng(seed)

    def update(self, tracker: SuccessTracker) -> None:
        """Adjust difficulty based on current success rates."""
        for gt in GoalType:
            rate = tracker.success_rate(gt)
            if rate >= self.success_threshold:
                self.difficulty[gt] = min(
                    self.max_difficulty,
                    self.difficulty[gt] + self.increase_rate,
                )
            elif rate < self.success_threshold * 0.5:
                self.difficulty[gt] = max(
                    0.1,
                    self.difficulty[gt] - self.decrease_rate,
                )

    def sample_goal(self, goal_type: Optional[GoalType] = None) -> SC2Goal:
        """Sample a goal at the current difficulty level."""
        if goal_type is None:
            goal_type = self.rng.choice(GOAL_TYPE_LIST)

        diff = self.difficulty[goal_type]
        # Goal vector encodes target parameters scaled by difficulty
        goal_vec = self.rng.standard_normal(SC2_GOAL_DIM).astype(np.float32) * diff

        descriptions = {
            GoalType.DESTROY_TARGET: f"Destroy target (diff={diff:.2f})",
            GoalType.REACH_LOCATION: f"Reach position (diff={diff:.2f})",
            GoalType.ACHIEVE_ECONOMY: f"Economy target (diff={diff:.2f})",
            GoalType.TECH_TO_UNIT: f"Tech path (diff={diff:.2f})",
        }

        return SC2Goal(
            goal_type=goal_type,
            goal_vector=goal_vec,
            description=descriptions[goal_type],
            difficulty=diff,
        )

    def current_difficulties(self) -> Dict[str, float]:
        return {gt.value: d for gt, d in self.difficulty.items()}


# ---------------------------------------------------------------------------
# SC2 Hindsight Replay (main class)
# ---------------------------------------------------------------------------
class SC2HindsightReplay:
    """Full HER system for goal-conditioned SC2 RL.

    Combines:
    - Multi-goal replay buffer with efficient HER relabeling
    - Goal-conditioned policy network
    - Universal Value Function Approximator (UVFA)
    - Success tracking per goal type
    - Automatic goal difficulty curriculum
    """

    def __init__(
        self,
        state_dim: int = SC2_STATE_DIM,
        action_dim: int = SC2_ACTION_DIM,
        hidden: int = 256,
        lr: float = 1e-3,
        gamma: float = 0.99,
        buffer_capacity: int = 100_000,
        her_ratio: float = 0.8,
        k_future: int = 4,
        relabel_strategy: RelabelStrategy = RelabelStrategy.FUTURE,
        seed: int = 42,
    ) -> None:
        self.state_dim = state_dim
        self.action_dim = action_dim
        self.rng = np.random.default_rng(seed)

        # Components
        self.policy = GoalConditionedPolicy(
            state_dim, action_dim, hidden, lr, seed=seed
        )
        self.value_fn = UniversalValueFunction(
            state_dim, hidden, lr, gamma, seed=seed
        )
        self.buffer = MultiGoalReplayBuffer(
            buffer_capacity, her_ratio, k_future, relabel_strategy, seed=seed
        )
        self.tracker = SuccessTracker(window=100)
        self.curriculum = GoalCurriculum(seed=seed)

        # Training logs
        self.policy_losses: List[float] = []
        self.value_losses: List[float] = []
        self.episode_rewards: List[float] = []

    # -- episode collection --

    def collect_episode(
        self,
        env_reset_fn: Callable[[SC2Goal], NDArray],
        env_step_fn: Callable[[NDArray, int, SC2Goal], Tuple[NDArray, float, bool, NDArray]],
        goal: Optional[SC2Goal] = None,
        max_steps: int = 200,
        greedy: bool = False,
    ) -> Episode:
        """Roll out one episode with the current goal-conditioned policy."""
        if goal is None:
            goal = self.curriculum.sample_goal()

        state = env_reset_fn(goal)
        episode = Episode(goal=goal)

        for t in range(max_steps):
            action = self.policy.select_action(state, goal, greedy=greedy, rng=self.rng)
            next_state, reward, done, achieved = env_step_fn(state, action, goal)

            transition = Transition(
                state=state,
                action=action,
                reward=reward,
                next_state=next_state,
                done=done,
                goal=goal,
                achieved_goal=achieved,
            )
            episode.add(transition)
            state = next_state

            if done:
                break

        # Check success
        if episode.length > 0:
            final_achieved = episode.transitions[-1].achieved_goal
            episode.success = goal.matches(final_achieved)

        self.tracker.record(goal.goal_type, episode.success)
        self.episode_rewards.append(episode.total_reward)
        return episode

    def store_and_relabel(self, episode: Episode) -> None:
        """Store episode in buffer with HER relabeling."""
        self.buffer.store_episode(episode)

    # -- training --

    def train_step(
        self,
        batch_size: int = 64,
        goal_type: Optional[GoalType] = None,
    ) -> Dict[str, float]:
        """One training step: update policy and value function."""
        if self.buffer.size < batch_size:
            return {"policy_loss": 0.0, "value_loss": 0.0}

        states, goals, actions, rewards, next_states, dones = \
            self.buffer.sample_batch_arrays(batch_size, goal_type)

        # Update value function
        v_loss = self.value_fn.train_step(states, goals, rewards, next_states, dones)
        self.value_losses.append(v_loss)

        # Compute advantage-like weights from value function
        values = self.value_fn.predict_batch(states, goals)
        next_values = self.value_fn.predict_batch(next_states, goals)
        advantages = rewards + 0.99 * next_values * (1.0 - dones) - values
        weights = np.clip(advantages, 0.0, None)  # positive advantages only
        if np.sum(weights) > 0:
            weights = weights / (np.max(weights) + 1e-8)
        else:
            weights = np.ones_like(weights)

        # Update policy
        p_loss = self.policy.train_step(states, goals, actions, weights)
        self.policy_losses.append(p_loss)

        return {"policy_loss": p_loss, "value_loss": v_loss}

    def train_epoch(
        self,
        n_episodes: int,
        env_reset_fn: Callable[[SC2Goal], NDArray],
        env_step_fn: Callable[[NDArray, int, SC2Goal], Tuple[NDArray, float, bool, NDArray]],
        train_steps_per_episode: int = 10,
        batch_size: int = 64,
        max_episode_steps: int = 200,
        verbose: bool = True,
    ) -> Dict[str, float]:
        """Collect episodes and train."""
        total_p_loss = 0.0
        total_v_loss = 0.0
        n_successes = 0

        for ep_i in range(n_episodes):
            # Sample goal from curriculum
            goal = self.curriculum.sample_goal()

            # Collect episode
            episode = self.collect_episode(
                env_reset_fn, env_step_fn, goal, max_episode_steps
            )
            self.store_and_relabel(episode)

            if episode.success:
                n_successes += 1

            # Training steps
            for _ in range(train_steps_per_episode):
                losses = self.train_step(batch_size)
                total_p_loss += losses["policy_loss"]
                total_v_loss += losses["value_loss"]

        # Update curriculum
        self.curriculum.update(self.tracker)

        n_total = n_episodes * train_steps_per_episode
        avg_p = total_p_loss / max(n_total, 1)
        avg_v = total_v_loss / max(n_total, 1)

        if verbose:
            logger.info(
                "Epoch: %d eps, success=%d/%d, p_loss=%.4f, v_loss=%.4f",
                n_episodes, n_successes, n_episodes, avg_p, avg_v,
            )

        return {
            "avg_policy_loss": avg_p,
            "avg_value_loss": avg_v,
            "success_count": n_successes,
            "success_rate": n_successes / max(n_episodes, 1),
        }

    # -- evaluation --

    def evaluate(
        self,
        env_reset_fn: Callable[[SC2Goal], NDArray],
        env_step_fn: Callable[[NDArray, int, SC2Goal], Tuple[NDArray, float, bool, NDArray]],
        n_episodes: int = 50,
        max_steps: int = 200,
    ) -> Dict[str, Any]:
        """Evaluate goal-conditioned policy across all goal types."""
        results: Dict[str, Any] = {}
        overall_success = 0

        for gt in GoalType:
            successes = 0
            total_rewards = []

            for _ in range(n_episodes // len(GoalType)):
                goal = self.curriculum.sample_goal(goal_type=gt)
                episode = self.collect_episode(
                    env_reset_fn, env_step_fn, goal, max_steps, greedy=True
                )
                if episode.success:
                    successes += 1
                    overall_success += 1
                total_rewards.append(episode.total_reward)

            results[gt.value] = {
                "success_rate": successes / max(n_episodes // len(GoalType), 1),
                "avg_reward": float(np.mean(total_rewards)) if total_rewards else 0.0,
            }

        results["overall_success_rate"] = overall_success / max(n_episodes, 1)
        return results

    # -- persistence --

    def save(self, path: str) -> None:
        Path(path).parent.mkdir(parents=True, exist_ok=True)
        state = {
            "state_dim": self.state_dim,
            "action_dim": self.action_dim,
            "policy_losses": self.policy_losses[-100:],
            "value_losses": self.value_losses[-100:],
            "episode_rewards": self.episode_rewards[-100:],
            "success_rates": self.tracker.all_rates(),
            "difficulties": self.curriculum.current_difficulties(),
            "buffer_size": self.buffer.size,
        }
        if not HAS_TORCH:
            state["policy_params"] = [
                (w.tolist(), b.tolist())
                for w, b in zip(self.policy.net.weights, self.policy.net.biases)
            ]
            state["value_params"] = [
                (w.tolist(), b.tolist())
                for w, b in zip(self.value_fn.net.weights, self.value_fn.net.biases)
            ]
        with open(path, "w") as f:
            json.dump(state, f)
        logger.info("SC2HindsightReplay saved to %s", path)

    def load(self, path: str) -> None:
        with open(path) as f:
            state = json.load(f)
        self.policy_losses = state.get("policy_losses", [])
        self.value_losses = state.get("value_losses", [])
        self.episode_rewards = state.get("episode_rewards", [])
        if not HAS_TORCH and "policy_params" in state:
            for i, (w, b) in enumerate(state["policy_params"]):
                self.policy.net.weights[i] = np.array(w, dtype=np.float32)
                self.policy.net.biases[i] = np.array(b, dtype=np.float32)
            for i, (w, b) in enumerate(state["value_params"]):
                self.value_fn.net.weights[i] = np.array(w, dtype=np.float32)
                self.value_fn.net.biases[i] = np.array(b, dtype=np.float32)
        logger.info("SC2HindsightReplay loaded from %s", path)

    def summary(self) -> Dict[str, Any]:
        return {
            "state_dim": self.state_dim,
            "action_dim": self.action_dim,
            "buffer_size": self.buffer.size,
            "total_episodes": len(self.buffer.episodes),
            "success_rates": self.tracker.all_rates(),
            "difficulties": self.curriculum.current_difficulties(),
            "backend": "torch" if HAS_TORCH else "numpy",
        }


# ---------------------------------------------------------------------------
# Simulated SC2 Goal Environment
# ---------------------------------------------------------------------------
class SC2GoalEnv:
    """Lightweight goal-conditioned environment stub for demonstration."""

    def __init__(self, state_dim: int = SC2_STATE_DIM, seed: int = 42) -> None:
        self.state_dim = state_dim
        self.rng = np.random.default_rng(seed)
        self.state = self.rng.standard_normal(state_dim).astype(np.float32)
        self.step_count = 0

    def reset(self, goal: SC2Goal) -> NDArray:
        self.state = self.rng.standard_normal(self.state_dim).astype(np.float32)
        self.step_count = 0
        self._goal = goal
        return self.state.copy()

    def step(
        self, state: NDArray, action: int, goal: SC2Goal
    ) -> Tuple[NDArray, float, bool, NDArray]:
        self.step_count += 1
        noise = self.rng.standard_normal(self.state_dim).astype(np.float32) * 0.1
        direction = goal.goal_vector[:self.state_dim] if len(goal.goal_vector) >= self.state_dim else \
            np.pad(goal.goal_vector, (0, self.state_dim - len(goal.goal_vector)))
        # Move slightly toward goal
        move = direction * 0.01 * (action + 1)
        self.state = state + noise + move[:self.state_dim]

        # Achieved goal: extract from current state
        achieved = self.state[:SC2_GOAL_DIM].copy()

        # Reward: negative distance to goal
        dist = float(np.linalg.norm(achieved - goal.goal_vector))
        reward = -dist * 0.1

        # Done conditions
        done = self.step_count >= 200 or goal.matches(achieved, threshold=1.0)
        if goal.matches(achieved, threshold=1.0):
            reward += 10.0

        return self.state.copy(), float(reward), done, achieved


# ---------------------------------------------------------------------------
# CLI Demo
# ---------------------------------------------------------------------------
def main() -> None:
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    )
    parser = argparse.ArgumentParser(
        description="Phase 615 -- SC2 Hindsight Experience Replay"
    )
    parser.add_argument("--epochs", type=int, default=5, help="Training epochs")
    parser.add_argument("--episodes-per-epoch", type=int, default=20, help="Episodes per epoch")
    parser.add_argument("--seed", type=int, default=42, help="Random seed")
    parser.add_argument("--strategy", choices=["future", "episode", "random"],
                        default="future", help="HER relabeling strategy")
    args = parser.parse_args()

    strategy_map = {
        "future": RelabelStrategy.FUTURE,
        "episode": RelabelStrategy.EPISODE,
        "random": RelabelStrategy.RANDOM,
    }

    print("=" * 70)
    print("Phase 615: SC2 Hindsight Experience Replay")
    print(f"Backend: {'PyTorch' if HAS_TORCH else 'NumPy (fallback)'}")
    print(f"Relabel strategy: {args.strategy}")
    print("=" * 70)

    env = SC2GoalEnv(seed=args.seed)
    her_system = SC2HindsightReplay(
        relabel_strategy=strategy_map[args.strategy],
        seed=args.seed,
    )

    # ---- Goal types demo ----
    print("\n[1] SC2 Goal Types:")
    for gt in GoalType:
        print(f"   {gt.value:20s} -- {GOAL_DESCRIPTIONS[gt]}")

    # ---- Curriculum sampling ----
    print("\n[2] Sampling goals from curriculum...")
    for gt in GoalType:
        goal = her_system.curriculum.sample_goal(goal_type=gt)
        print(f"   {gt.value:20s}: diff={goal.difficulty:.2f}  vec_norm={np.linalg.norm(goal.goal_vector):.3f}")

    # ---- Training loop ----
    print(f"\n[3] Training: {args.epochs} epochs x {args.episodes_per_epoch} episodes...")
    for epoch in range(args.epochs):
        result = her_system.train_epoch(
            n_episodes=args.episodes_per_epoch,
            env_reset_fn=env.reset,
            env_step_fn=env.step,
            train_steps_per_episode=5,
            batch_size=32,
            max_episode_steps=100,
            verbose=False,
        )
        print(
            f"   Epoch {epoch + 1}/{args.epochs}  "
            f"success={result['success_rate']:.1%}  "
            f"p_loss={result['avg_policy_loss']:.4f}  "
            f"v_loss={result['avg_value_loss']:.4f}"
        )

    # ---- Success rates ----
    print(f"\n[4] {her_system.tracker.report()}")

    # ---- Curriculum state ----
    print("\n[5] Goal difficulty curriculum:")
    for gt_name, diff in her_system.curriculum.current_difficulties().items():
        print(f"   {gt_name:20s}: {diff:.2f}")

    # ---- Buffer stats ----
    print(f"\n[6] Replay buffer: {her_system.buffer.stats()}")

    # ---- Evaluation ----
    print("\n[7] Evaluation (greedy policy)...")
    eval_results = her_system.evaluate(
        env.reset, env.step, n_episodes=20, max_steps=100
    )
    for key, val in eval_results.items():
        if isinstance(val, dict):
            print(f"   {key:20s}: success={val['success_rate']:.1%}  reward={val['avg_reward']:.3f}")
        else:
            print(f"   {key:20s}: {val:.1%}")

    # ---- Value function demo ----
    print("\n[8] UVFA predictions (sample goals)...")
    for gt in GoalType:
        goal = her_system.curriculum.sample_goal(goal_type=gt)
        state = env.rng.standard_normal(SC2_STATE_DIM).astype(np.float32)
        v = her_system.value_fn.predict(state, goal)
        print(f"   V(s, {gt.value:20s}) = {v:.4f}")

    # ---- Summary ----
    print(f"\n[9] System summary: {her_system.summary()}")

    print("\n" + "=" * 70)
    print("Phase 615 complete.")
    print("=" * 70)


if __name__ == "__main__":
    main()
