"""
Phase 350: Replay Buffer
Prioritized experience replay buffer for SC2 training data with SumTree.
"""

import os
import pickle
from dataclasses import dataclass
from typing import List, Optional, Tuple

import numpy as np


@dataclass
class Transition:
    obs: np.ndarray
    action: int
    reward: float
    next_obs: np.ndarray
    done: bool
    n_step_return: Optional[float] = None
    n_step_next_obs: Optional[np.ndarray] = None


class SumTree:
    """Binary SumTree for efficient priority sampling."""

    def __init__(self, capacity: int):
        self.capacity = capacity
        self.tree = np.zeros(2 * capacity - 1, dtype=np.float64)
        self.data: List[Optional[Transition]] = [None] * capacity
        self.write_ptr = 0
        self.size = 0

    def _propagate(self, idx: int, delta: float) -> None:
        parent = (idx - 1) // 2
        self.tree[parent] += delta
        if parent != 0:
            self._propagate(parent, delta)

    def _retrieve(self, idx: int, val: float) -> int:
        left = 2 * idx + 1
        right = left + 1
        if left >= len(self.tree):
            return idx
        if val <= self.tree[left]:
            return self._retrieve(left, val)
        return self._retrieve(right, val - self.tree[left])

    def total_priority(self) -> float:
        return self.tree[0]

    def add(self, priority: float, transition: Transition) -> None:
        leaf = self.write_ptr + self.capacity - 1
        self.data[self.write_ptr] = transition
        self.update(leaf, priority)
        self.write_ptr = (self.write_ptr + 1) % self.capacity
        self.size = min(self.size + 1, self.capacity)

    def update(self, leaf_idx: int, priority: float) -> None:
        delta = priority - self.tree[leaf_idx]
        self.tree[leaf_idx] = priority
        self._propagate(leaf_idx, delta)

    def sample(self, val: float) -> Tuple[int, float, Transition]:
        leaf = self._retrieve(0, val)
        data_idx = leaf - self.capacity + 1
        return leaf, self.tree[leaf], self.data[data_idx]


class PrioritizedReplayBuffer:
    """Prioritized Experience Replay buffer supporting n-step TD returns."""

    def __init__(
        self,
        capacity: int = 100_000,
        alpha: float = 0.6,
        beta: float = 0.4,
        beta_increment: float = 1e-5,
        n_step: int = 3,
        gamma: float = 0.99,
        epsilon: float = 1e-6,
    ):
        self.capacity = capacity
        self.alpha = alpha
        self.beta = beta
        self.beta_increment = beta_increment
        self.n_step = n_step
        self.gamma = gamma
        self.epsilon = epsilon
        self.tree = SumTree(capacity)
        self.n_step_buffer: List[Transition] = []
        self.max_priority = 1.0

    def _compute_n_step(self) -> Tuple[float, np.ndarray, bool]:
        """Compute n-step return for the oldest transition in the buffer."""
        n_return = 0.0
        for i, t in enumerate(self.n_step_buffer):
            n_return += (self.gamma**i) * t.reward
            if t.done:
                return n_return, t.next_obs, True
        last = self.n_step_buffer[-1]
        return n_return, last.next_obs, last.done

    def add(
        self,
        obs: np.ndarray,
        action: int,
        reward: float,
        next_obs: np.ndarray,
        done: bool,
    ) -> None:
        transition = Transition(
            obs=obs, action=action, reward=reward, next_obs=next_obs, done=done
        )
        self.n_step_buffer.append(transition)
        if len(self.n_step_buffer) < self.n_step and not done:
            return
        n_return, n_next_obs, n_done = self._compute_n_step()
        first = self.n_step_buffer.pop(0)
        first.n_step_return = n_return
        first.n_step_next_obs = n_next_obs
        priority = self.max_priority**self.alpha
        self.tree.add(priority, first)
        if done:
            self.n_step_buffer.clear()

    def sample(
        self, batch_size: int
    ) -> Tuple[List[Transition], np.ndarray, np.ndarray]:
        transitions, indices, weights = [], [], []
        total = self.tree.total_priority()
        segment = total / batch_size
        self.beta = min(1.0, self.beta + self.beta_increment)
        min_prob = (
            np.min(
                self.tree.tree[-self.capacity :][self.tree.tree[-self.capacity :] > 0]
            )
            / total
        )
        max_weight = (min_prob * self.tree.size) ** (-self.beta)
        for i in range(batch_size):
            val = np.random.uniform(segment * i, segment * (i + 1))
            leaf_idx, priority, transition = self.tree.sample(val)
            prob = priority / total
            weight = ((prob * self.tree.size) ** (-self.beta)) / max_weight
            transitions.append(transition)
            indices.append(leaf_idx)
            weights.append(weight)
        return transitions, np.array(indices), np.array(weights, dtype=np.float32)

    def update_priorities(self, indices: np.ndarray, td_errors: np.ndarray) -> None:
        for idx, err in zip(indices, td_errors):
            priority = (abs(err) + self.epsilon) ** self.alpha
            self.max_priority = max(self.max_priority, priority)
            self.tree.update(idx, priority)

    def save_to_disk(self, path: str) -> None:
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, "wb") as f:
            pickle.dump(
                {
                    "tree": self.tree,
                    "beta": self.beta,
                    "max_priority": self.max_priority,
                },
                f,
            )

    def load_from_disk(self, path: str) -> None:
        with open(path, "rb") as f:
            data = pickle.load(f)
        self.tree = data["tree"]
        self.beta = data["beta"]
        self.max_priority = data["max_priority"]

    def __len__(self) -> int:
        return self.tree.size
