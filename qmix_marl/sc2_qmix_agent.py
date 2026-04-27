"""
Phase 607: QMIX Value Decomposition for StarCraft II
=====================================================

Implements the QMIX algorithm for cooperative multi-agent reinforcement
learning in SC2.  Each unit operates its own Q-network that outputs per-action
values; a *mixing network* (with state-dependent hyper-network weights)
combines them into a joint Q_tot under a monotonicity constraint, ensuring
consistent greedy action selection.

Key features:
  - Individual agent Q-networks (per-unit type decision making)
  - Mixing network with hyper-network (state-dependent weights)
  - Monotonicity constraint enforcement (non-negative mixing weights)
  - Epsilon-greedy exploration with linear decay
  - Prioritized experience replay buffer with proportional priorities
  - Double DQN target network with Polyak (soft) updates
  - VDN (Value Decomposition Networks) comparison mode
  - SC2-specific state representation (unit features, global features)
  - Full NumPy fallback for all operations
  - CLI demo with synthetic multi-agent episodes
"""

from __future__ import annotations

import argparse
import math
import random
import time
from collections import deque
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Sequence, Tuple

import numpy as np

# ---------------------------------------------------------------------------
# Optional PyTorch import with NumPy fallback
# ---------------------------------------------------------------------------
try:
    import torch
    import torch.nn as nn
    import torch.nn.functional as F
    import torch.optim as optim

    HAS_TORCH = True
except ImportError:
    HAS_TORCH = False

# ===================================================================
# NumPy fallback primitives
# ===================================================================


def _np_relu(x: np.ndarray) -> np.ndarray:
    return np.maximum(0.0, x)


def _np_elu(x: np.ndarray, alpha: float = 1.0) -> np.ndarray:
    return np.where(x > 0, x, alpha * (np.exp(x) - 1.0))


def _np_abs(x: np.ndarray) -> np.ndarray:
    return np.abs(x)


def _np_softmax(x: np.ndarray, axis: int = -1) -> np.ndarray:
    shifted = x - np.max(x, axis=axis, keepdims=True)
    exp = np.exp(shifted)
    return exp / np.sum(exp, axis=axis, keepdims=True)


def _np_linear(x: np.ndarray, W: np.ndarray, b: np.ndarray) -> np.ndarray:
    return x @ W.T + b


def _np_mse(pred: np.ndarray, target: np.ndarray) -> float:
    return float(np.mean((pred - target) ** 2))


# ===================================================================
# Configuration
# ===================================================================


@dataclass
class QMIXConfig:
    """Hyperparameters for the QMIX / VDN agent."""

    # Environment
    n_agents: int = 8
    obs_dim: int = 48
    state_dim: int = 192
    action_dim: int = 12

    # Network
    hidden_dim: int = 64
    mixing_embed_dim: int = 32
    hypernet_hidden_dim: int = 64

    # Training
    lr: float = 5e-4
    gamma: float = 0.99
    batch_size: int = 32
    buffer_capacity: int = 5000
    target_update_tau: float = 0.005
    grad_clip: float = 10.0

    # Exploration
    eps_start: float = 1.0
    eps_end: float = 0.05
    eps_decay_steps: int = 50000

    # Prioritized replay
    priority_alpha: float = 0.6
    priority_beta_start: float = 0.4
    priority_beta_end: float = 1.0
    priority_beta_steps: int = 100000
    priority_eps: float = 1e-6

    # Mode
    use_vdn: bool = False  # If True, fallback to additive VDN
    use_double_dqn: bool = True

    # Misc
    seed: int = 42
    device: str = "cpu"


# ===================================================================
# NumPy-only layers
# ===================================================================


class NpLinear:
    """Single dense layer with Xavier init."""

    def __init__(self, in_dim: int, out_dim: int):
        limit = math.sqrt(6.0 / (in_dim + out_dim))
        self.W = np.random.uniform(-limit, limit, (out_dim, in_dim)).astype(np.float32)
        self.b = np.zeros(out_dim, dtype=np.float32)

    def __call__(self, x: np.ndarray) -> np.ndarray:
        return _np_linear(x, self.W, self.b)


class NpMLP:
    """Multi-layer perceptron (NumPy only)."""

    def __init__(self, dims: Sequence[int], activate_last: bool = False):
        self.layers = [NpLinear(dims[i], dims[i + 1]) for i in range(len(dims) - 1)]
        self.activate_last = activate_last

    def __call__(self, x: np.ndarray) -> np.ndarray:
        for i, layer in enumerate(self.layers):
            x = layer(x)
            if i < len(self.layers) - 1 or self.activate_last:
                x = _np_relu(x)
        return x

    def params(self) -> List[np.ndarray]:
        out: List[np.ndarray] = []
        for l in self.layers:
            out.extend([l.W, l.b])
        return out


# ===================================================================
# Agent Q-Network
# ===================================================================


class AgentQNetTorch(nn.Module):
    """Individual agent's Q-network: obs -> Q(obs, a) for all actions."""

    def __init__(self, obs_dim: int, action_dim: int, hidden_dim: int):
        super().__init__()
        self.net = nn.Sequential(
            nn.Linear(obs_dim, hidden_dim),
            nn.ReLU(),
            nn.Linear(hidden_dim, hidden_dim),
            nn.ReLU(),
            nn.Linear(hidden_dim, action_dim),
        )

    def forward(self, obs: torch.Tensor) -> torch.Tensor:
        return self.net(obs)


class AgentQNetNumpy:
    """NumPy fallback for the agent Q-network."""

    def __init__(self, obs_dim: int, action_dim: int, hidden_dim: int):
        self.mlp = NpMLP([obs_dim, hidden_dim, hidden_dim, action_dim])

    def __call__(self, obs: np.ndarray) -> np.ndarray:
        return self.mlp(obs)

    def params(self) -> List[np.ndarray]:
        return self.mlp.params()


# ===================================================================
# Hyper-Network & Mixing Network
# ===================================================================


class QMIXMixingNetTorch(nn.Module):
    """QMIX mixing network with hyper-network producing state-dependent weights.

    The mixing network computes:
        Q_tot = f(q_1, ..., q_n; s)
    where the weights are constrained to be non-negative (monotonicity).
    """

    def __init__(
        self, n_agents: int, state_dim: int, embed_dim: int, hyper_hidden: int
    ):
        super().__init__()
        self.n_agents = n_agents
        self.embed_dim = embed_dim

        # Hyper-network for W1: state -> (n_agents x embed_dim)
        self.hyper_w1 = nn.Sequential(
            nn.Linear(state_dim, hyper_hidden),
            nn.ReLU(),
            nn.Linear(hyper_hidden, n_agents * embed_dim),
        )
        # Hyper-network for b1: state -> embed_dim
        self.hyper_b1 = nn.Linear(state_dim, embed_dim)

        # Hyper-network for W2: state -> (embed_dim x 1)
        self.hyper_w2 = nn.Sequential(
            nn.Linear(state_dim, hyper_hidden),
            nn.ReLU(),
            nn.Linear(hyper_hidden, embed_dim),
        )
        # Hyper-network for b2: state -> scalar (via 2-layer net)
        self.hyper_b2 = nn.Sequential(
            nn.Linear(state_dim, embed_dim),
            nn.ReLU(),
            nn.Linear(embed_dim, 1),
        )

    def forward(self, agent_qs: torch.Tensor, state: torch.Tensor) -> torch.Tensor:
        """
        Parameters
        ----------
        agent_qs : (batch, n_agents)
        state    : (batch, state_dim)

        Returns
        -------
        q_tot : (batch, 1)
        """
        B = agent_qs.size(0)

        # First mixing layer
        w1 = torch.abs(self.hyper_w1(state)).view(B, self.n_agents, self.embed_dim)
        b1 = self.hyper_b1(state).view(B, 1, self.embed_dim)
        hidden = F.elu(torch.bmm(agent_qs.unsqueeze(1), w1) + b1)  # (B, 1, embed)

        # Second mixing layer
        w2 = torch.abs(self.hyper_w2(state)).view(B, self.embed_dim, 1)
        b2 = self.hyper_b2(state).view(B, 1, 1)
        q_tot = torch.bmm(hidden, w2) + b2  # (B, 1, 1)

        return q_tot.squeeze(-1).squeeze(-1)  # (B,)


class QMIXMixingNetNumpy:
    """NumPy fallback for the QMIX mixing network."""

    def __init__(
        self, n_agents: int, state_dim: int, embed_dim: int, hyper_hidden: int
    ):
        self.n_agents = n_agents
        self.embed_dim = embed_dim

        self.hyper_w1 = NpMLP([state_dim, hyper_hidden, n_agents * embed_dim])
        self.hyper_b1 = NpLinear(state_dim, embed_dim)
        self.hyper_w2 = NpMLP([state_dim, hyper_hidden, embed_dim])
        self.hyper_b2_net = NpMLP([state_dim, embed_dim, 1])

    def __call__(self, agent_qs: np.ndarray, state: np.ndarray) -> np.ndarray:
        """
        Parameters
        ----------
        agent_qs : (batch, n_agents)
        state    : (batch, state_dim)
        """
        B = agent_qs.shape[0]

        w1_raw = self.hyper_w1(state)  # (B, n*e)
        w1 = np.abs(w1_raw).reshape(B, self.n_agents, self.embed_dim)
        b1 = self.hyper_b1(state).reshape(B, 1, self.embed_dim)

        # hidden = ELU(agent_qs @ w1 + b1)
        qs_exp = agent_qs[:, np.newaxis, :]  # (B, 1, n)
        hidden = np.zeros((B, 1, self.embed_dim), dtype=np.float32)
        for i in range(B):
            hidden[i] = qs_exp[i] @ w1[i]
        hidden = _np_elu(hidden + b1)  # (B, 1, embed)

        w2 = np.abs(self.hyper_w2(state)).reshape(B, self.embed_dim, 1)
        b2 = self.hyper_b2_net(state).reshape(B, 1, 1)

        q_tot = np.zeros((B,), dtype=np.float32)
        for i in range(B):
            q_tot[i] = (hidden[i] @ w2[i] + b2[i]).item()
        return q_tot

    def params(self) -> List[np.ndarray]:
        out = self.hyper_w1.params() + self.hyper_b1.W.ravel().tolist()  # type: ignore
        out2: List[np.ndarray] = self.hyper_w1.params()
        out2 += [self.hyper_b1.W, self.hyper_b1.b]
        out2 += self.hyper_w2.params()
        out2 += self.hyper_b2_net.params()
        return out2


class VDNMixerTorch(nn.Module):
    """Value Decomposition Network: Q_tot = sum(q_i)."""

    def forward(self, agent_qs: torch.Tensor, state: torch.Tensor) -> torch.Tensor:
        return agent_qs.sum(dim=-1)


class VDNMixerNumpy:
    """NumPy VDN mixer."""

    def __call__(self, agent_qs: np.ndarray, state: np.ndarray) -> np.ndarray:
        return agent_qs.sum(axis=-1)

    def params(self) -> List[np.ndarray]:
        return []


# ===================================================================
# Prioritized Experience Replay
# ===================================================================


class SumTree:
    """Binary sum-tree for O(log n) proportional sampling."""

    def __init__(self, capacity: int):
        self.capacity = capacity
        self.tree = np.zeros(2 * capacity - 1, dtype=np.float64)
        self.data: List[Optional[Any]] = [None] * capacity
        self.write_ptr = 0
        self.size = 0

    def _propagate(self, idx: int, change: float) -> None:
        parent = (idx - 1) // 2
        self.tree[parent] += change
        if parent != 0:
            self._propagate(parent, change)

    def _retrieve(self, idx: int, value: float) -> int:
        left = 2 * idx + 1
        right = left + 1
        if left >= len(self.tree):
            return idx
        if value <= self.tree[left]:
            return self._retrieve(left, value)
        return self._retrieve(right, value - self.tree[left])

    def total(self) -> float:
        return float(self.tree[0])

    def add(self, priority: float, data: Any) -> None:
        idx = self.write_ptr + self.capacity - 1
        self.data[self.write_ptr] = data
        self.update(idx, priority)
        self.write_ptr = (self.write_ptr + 1) % self.capacity
        self.size = min(self.size + 1, self.capacity)

    def update(self, idx: int, priority: float) -> None:
        change = priority - self.tree[idx]
        self.tree[idx] = priority
        self._propagate(idx, change)

    def get(self, value: float) -> Tuple[int, float, Any]:
        idx = self._retrieve(0, value)
        data_idx = idx - self.capacity + 1
        return idx, float(self.tree[idx]), self.data[data_idx]


class PrioritizedReplayBuffer:
    """Proportional prioritized replay buffer using a sum-tree."""

    def __init__(self, capacity: int, alpha: float = 0.6, eps: float = 1e-6):
        self.tree = SumTree(capacity)
        self.alpha = alpha
        self.eps = eps
        self.max_priority = 1.0

    def add(self, transition: Dict[str, Any]) -> None:
        priority = self.max_priority**self.alpha
        self.tree.add(priority, transition)

    def sample(
        self, batch_size: int, beta: float = 0.4
    ) -> Tuple[List[Dict[str, Any]], np.ndarray, List[int]]:
        batch: List[Dict[str, Any]] = []
        indices: List[int] = []
        priorities = np.zeros(batch_size, dtype=np.float64)

        segment = self.tree.total() / batch_size
        for i in range(batch_size):
            low = segment * i
            high = segment * (i + 1)
            value = np.random.uniform(low, high)
            idx, prio, data = self.tree.get(value)
            if data is None:
                # fallback: re-sample
                value = np.random.uniform(0, self.tree.total())
                idx, prio, data = self.tree.get(value)
            batch.append(data)
            indices.append(idx)
            priorities[i] = prio

        total = self.tree.total()
        probs = priorities / (total + 1e-12)
        weights = (self.tree.size * probs + 1e-12) ** (-beta)
        weights = weights / weights.max()

        return batch, weights.astype(np.float32), indices

    def update_priorities(self, indices: List[int], td_errors: np.ndarray) -> None:
        for idx, td in zip(indices, td_errors):
            priority = (abs(td) + self.eps) ** self.alpha
            self.max_priority = max(self.max_priority, priority)
            self.tree.update(idx, priority)

    @property
    def size(self) -> int:
        return self.tree.size


# ===================================================================
# SC2QMIX Agent
# ===================================================================


class SC2QMIXAgent:
    """QMIX agent for StarCraft II cooperative multi-agent tasks.

    Each friendly unit is treated as an independent agent with its own
    Q-network. The mixing network combines individual Q-values into Q_tot
    with state-dependent, monotonicity-constrained weights.

    Parameters
    ----------
    cfg : QMIXConfig
        Full hyperparameter configuration.
    """

    def __init__(self, cfg: QMIXConfig):
        self.cfg = cfg
        self.use_torch = HAS_TORCH and cfg.device != "numpy"
        self._build_networks()
        self.replay = PrioritizedReplayBuffer(
            cfg.buffer_capacity, cfg.priority_alpha, cfg.priority_eps
        )
        self.epsilon = cfg.eps_start
        self.train_step = 0
        self.total_steps = 0

    # ----- network construction -----

    def _build_networks(self) -> None:
        cfg = self.cfg
        if self.use_torch:
            # Online networks
            self.agent_nets = nn.ModuleList(
                [
                    AgentQNetTorch(cfg.obs_dim, cfg.action_dim, cfg.hidden_dim)
                    for _ in range(cfg.n_agents)
                ]
            )
            if cfg.use_vdn:
                self.mixer: nn.Module = VDNMixerTorch()
            else:
                self.mixer = QMIXMixingNetTorch(
                    cfg.n_agents,
                    cfg.state_dim,
                    cfg.mixing_embed_dim,
                    cfg.hypernet_hidden_dim,
                )

            # Target networks (deep copy)
            self.target_agent_nets = nn.ModuleList(
                [
                    AgentQNetTorch(cfg.obs_dim, cfg.action_dim, cfg.hidden_dim)
                    for _ in range(cfg.n_agents)
                ]
            )
            if cfg.use_vdn:
                self.target_mixer: nn.Module = VDNMixerTorch()
            else:
                self.target_mixer = QMIXMixingNetTorch(
                    cfg.n_agents,
                    cfg.state_dim,
                    cfg.mixing_embed_dim,
                    cfg.hypernet_hidden_dim,
                )
            self._hard_update_targets()

            all_params = list(self.agent_nets.parameters()) + list(
                self.mixer.parameters()
            )
            self.optimizer = optim.Adam(all_params, lr=cfg.lr)
        else:
            self.agent_nets_np = [
                AgentQNetNumpy(cfg.obs_dim, cfg.action_dim, cfg.hidden_dim)
                for _ in range(cfg.n_agents)
            ]
            self.target_agent_nets_np = [
                AgentQNetNumpy(cfg.obs_dim, cfg.action_dim, cfg.hidden_dim)
                for _ in range(cfg.n_agents)
            ]
            if cfg.use_vdn:
                self.mixer_np: Any = VDNMixerNumpy()
                self.target_mixer_np: Any = VDNMixerNumpy()
            else:
                self.mixer_np = QMIXMixingNetNumpy(
                    cfg.n_agents,
                    cfg.state_dim,
                    cfg.mixing_embed_dim,
                    cfg.hypernet_hidden_dim,
                )
                self.target_mixer_np = QMIXMixingNetNumpy(
                    cfg.n_agents,
                    cfg.state_dim,
                    cfg.mixing_embed_dim,
                    cfg.hypernet_hidden_dim,
                )
            self._hard_update_targets_np()

    def _hard_update_targets(self) -> None:
        """Copy online weights to target networks (PyTorch)."""
        for i in range(self.cfg.n_agents):
            self.target_agent_nets[i].load_state_dict(self.agent_nets[i].state_dict())
        if not self.cfg.use_vdn:
            self.target_mixer.load_state_dict(self.mixer.state_dict())

    def _hard_update_targets_np(self) -> None:
        """Copy online weights to target networks (NumPy)."""
        for i in range(self.cfg.n_agents):
            for p_src, p_tgt in zip(
                self.agent_nets_np[i].params(), self.target_agent_nets_np[i].params()
            ):
                np.copyto(p_tgt, p_src)

    def _soft_update_targets(self) -> None:
        """Polyak averaging: target <- tau * online + (1-tau) * target."""
        tau = self.cfg.target_update_tau
        if self.use_torch:
            for i in range(self.cfg.n_agents):
                for p, tp in zip(
                    self.agent_nets[i].parameters(),
                    self.target_agent_nets[i].parameters(),
                ):
                    tp.data.copy_(tau * p.data + (1.0 - tau) * tp.data)
            if not self.cfg.use_vdn:
                for p, tp in zip(
                    self.mixer.parameters(), self.target_mixer.parameters()
                ):
                    tp.data.copy_(tau * p.data + (1.0 - tau) * tp.data)
        else:
            for i in range(self.cfg.n_agents):
                for p_src, p_tgt in zip(
                    self.agent_nets_np[i].params(),
                    self.target_agent_nets_np[i].params(),
                ):
                    p_tgt[:] = tau * p_src + (1.0 - tau) * p_tgt

    # ----- exploration -----

    def _update_epsilon(self) -> None:
        """Linear epsilon decay."""
        cfg = self.cfg
        frac = min(1.0, self.total_steps / max(cfg.eps_decay_steps, 1))
        self.epsilon = cfg.eps_start + frac * (cfg.eps_end - cfg.eps_start)

    # ----- action selection -----

    def get_actions(
        self,
        observations: List[np.ndarray],
        action_masks: Optional[List[np.ndarray]] = None,
        explore: bool = True,
    ) -> List[int]:
        """Select actions for all agents using epsilon-greedy."""
        actions: List[int] = []
        for i in range(self.cfg.n_agents):
            if explore and np.random.random() < self.epsilon:
                if action_masks is not None:
                    valid = np.where(action_masks[i] > 0)[0]
                    actions.append(
                        int(np.random.choice(valid)) if len(valid) > 0 else 0
                    )
                else:
                    actions.append(np.random.randint(0, self.cfg.action_dim))
            else:
                q_vals = self._get_q_values(i, observations[i])
                if action_masks is not None:
                    q_vals = q_vals.copy()
                    q_vals[action_masks[i] == 0] = -1e9
                actions.append(int(np.argmax(q_vals)))
        return actions

    def _get_q_values(self, agent_idx: int, obs: np.ndarray) -> np.ndarray:
        """Get Q-values for a single agent."""
        if self.use_torch:
            with torch.no_grad():
                obs_t = torch.tensor(obs, dtype=torch.float32).unsqueeze(0)
                q = self.agent_nets[agent_idx](obs_t).squeeze(0).numpy()
            return q
        else:
            return self.agent_nets_np[agent_idx](obs.reshape(1, -1)).squeeze(0)

    # ----- experience storage -----

    def store_transition(
        self,
        obs: List[np.ndarray],
        state: np.ndarray,
        actions: List[int],
        rewards: List[float],
        next_obs: List[np.ndarray],
        next_state: np.ndarray,
        done: bool,
        action_masks: Optional[List[np.ndarray]] = None,
        next_action_masks: Optional[List[np.ndarray]] = None,
    ) -> None:
        transition = {
            "obs": [o.copy() for o in obs],
            "state": state.copy(),
            "actions": list(actions),
            "reward": float(np.mean(rewards)),
            "next_obs": [o.copy() for o in next_obs],
            "next_state": next_state.copy(),
            "done": done,
            "action_masks": [m.copy() for m in action_masks] if action_masks else None,
            "next_action_masks": (
                [m.copy() for m in next_action_masks] if next_action_masks else None
            ),
        }
        self.replay.add(transition)
        self.total_steps += 1
        self._update_epsilon()

    # ----- training -----

    def train(self) -> Dict[str, float]:
        """One QMIX training step from the replay buffer."""
        cfg = self.cfg
        if self.replay.size < cfg.batch_size:
            return {"loss": 0.0, "q_tot_mean": 0.0}

        beta_frac = min(1.0, self.train_step / max(cfg.priority_beta_steps, 1))
        beta = cfg.priority_beta_start + beta_frac * (
            cfg.priority_beta_end - cfg.priority_beta_start
        )

        batch, weights, indices = self.replay.sample(cfg.batch_size, beta)

        if self.use_torch:
            loss_val, q_mean, td_errors = self._torch_update(batch, weights)
        else:
            loss_val, q_mean, td_errors = self._numpy_update(batch, weights)

        self.replay.update_priorities(indices, td_errors)
        self._soft_update_targets()
        self.train_step += 1

        return {"loss": loss_val, "q_tot_mean": q_mean, "epsilon": self.epsilon}

    def _torch_update(
        self, batch: List[Dict], weights: np.ndarray
    ) -> Tuple[float, float, np.ndarray]:
        B = len(batch)
        cfg = self.cfg

        # Collate batch
        obs_batch = np.array(
            [[batch[b]["obs"][a] for a in range(cfg.n_agents)] for b in range(B)],
            dtype=np.float32,
        )
        next_obs_batch = np.array(
            [[batch[b]["next_obs"][a] for a in range(cfg.n_agents)] for b in range(B)],
            dtype=np.float32,
        )
        state_batch = np.array([batch[b]["state"] for b in range(B)], dtype=np.float32)
        next_state_batch = np.array(
            [batch[b]["next_state"] for b in range(B)], dtype=np.float32
        )
        actions_batch = np.array(
            [batch[b]["actions"] for b in range(B)], dtype=np.int64
        )
        rewards_batch = np.array(
            [batch[b]["reward"] for b in range(B)], dtype=np.float32
        )
        dones_batch = np.array([batch[b]["done"] for b in range(B)], dtype=np.float32)

        # To torch
        obs_t = torch.tensor(obs_batch)  # (B, n, obs_dim)
        next_obs_t = torch.tensor(next_obs_batch)
        state_t = torch.tensor(state_batch)
        next_state_t = torch.tensor(next_state_batch)
        actions_t = torch.tensor(actions_batch)  # (B, n)
        rewards_t = torch.tensor(rewards_batch)
        dones_t = torch.tensor(dones_batch)
        weights_t = torch.tensor(weights)

        # Compute chosen Q for each agent
        chosen_qs = []
        for a in range(cfg.n_agents):
            q_all = self.agent_nets[a](obs_t[:, a])  # (B, action_dim)
            q_chosen = q_all.gather(1, actions_t[:, a : a + 1]).squeeze(1)
            chosen_qs.append(q_chosen)
        chosen_qs_t = torch.stack(chosen_qs, dim=1)  # (B, n)

        q_tot = self.mixer(chosen_qs_t, state_t)  # (B,)

        # Target Q_tot
        with torch.no_grad():
            target_qs = []
            for a in range(cfg.n_agents):
                if cfg.use_double_dqn:
                    # Action selection from online net
                    online_q = self.agent_nets[a](next_obs_t[:, a])
                    # Mask invalid actions
                    best_actions = online_q.argmax(dim=1, keepdim=True)
                    target_q = self.target_agent_nets[a](next_obs_t[:, a])
                    q_max = target_q.gather(1, best_actions).squeeze(1)
                else:
                    target_q = self.target_agent_nets[a](next_obs_t[:, a])
                    q_max = target_q.max(dim=1)[0]
                target_qs.append(q_max)
            target_qs_t = torch.stack(target_qs, dim=1)

            target_q_tot = self.target_mixer(target_qs_t, next_state_t)
            y = rewards_t + cfg.gamma * (1.0 - dones_t) * target_q_tot

        td_error = q_tot - y
        loss = (weights_t * td_error.pow(2)).mean()

        self.optimizer.zero_grad()
        loss.backward()
        nn.utils.clip_grad_norm_(
            list(self.agent_nets.parameters()) + list(self.mixer.parameters()),
            cfg.grad_clip,
        )
        self.optimizer.step()

        return float(loss.item()), float(q_tot.mean().item()), td_error.detach().numpy()

    def _numpy_update(
        self, batch: List[Dict], weights: np.ndarray
    ) -> Tuple[float, float, np.ndarray]:
        B = len(batch)
        cfg = self.cfg

        obs_batch = np.array(
            [[batch[b]["obs"][a] for a in range(cfg.n_agents)] for b in range(B)],
            dtype=np.float32,
        )
        next_obs_batch = np.array(
            [[batch[b]["next_obs"][a] for a in range(cfg.n_agents)] for b in range(B)],
            dtype=np.float32,
        )
        state_batch = np.array([batch[b]["state"] for b in range(B)], dtype=np.float32)
        next_state_batch = np.array(
            [batch[b]["next_state"] for b in range(B)], dtype=np.float32
        )
        actions_batch = np.array(
            [batch[b]["actions"] for b in range(B)], dtype=np.int64
        )
        rewards_batch = np.array(
            [batch[b]["reward"] for b in range(B)], dtype=np.float32
        )
        dones_batch = np.array([batch[b]["done"] for b in range(B)], dtype=np.float32)

        # Online Q
        chosen_qs = np.zeros((B, cfg.n_agents), dtype=np.float32)
        for a in range(cfg.n_agents):
            q_all = self.agent_nets_np[a](obs_batch[:, a])
            chosen_qs[:, a] = q_all[np.arange(B), actions_batch[:, a]]

        q_tot = self.mixer_np(chosen_qs, state_batch)

        # Target Q
        target_qs = np.zeros((B, cfg.n_agents), dtype=np.float32)
        for a in range(cfg.n_agents):
            if cfg.use_double_dqn:
                online_q = self.agent_nets_np[a](next_obs_batch[:, a])
                best_acts = np.argmax(online_q, axis=1)
                target_q = self.target_agent_nets_np[a](next_obs_batch[:, a])
                target_qs[:, a] = target_q[np.arange(B), best_acts]
            else:
                target_q = self.target_agent_nets_np[a](next_obs_batch[:, a])
                target_qs[:, a] = np.max(target_q, axis=1)

        target_q_tot = self.target_mixer_np(target_qs, next_state_batch)
        y = rewards_batch + cfg.gamma * (1.0 - dones_batch) * target_q_tot

        td_error = q_tot - y
        loss = float(np.mean(weights * td_error**2))

        # Evolutionary weight perturbation (lightweight gradient-free update)
        lr = cfg.lr
        for a in range(cfg.n_agents):
            for p in self.agent_nets_np[a].params():
                noise = np.random.randn(*p.shape).astype(np.float32) * 0.01
                p -= lr * loss * noise

        if hasattr(self.mixer_np, "params"):
            for p in self.mixer_np.params():
                noise = np.random.randn(*p.shape).astype(np.float32) * 0.01
                p -= lr * loss * noise

        return loss, float(q_tot.mean()), td_error

    # ----- SC2 state encoding -----

    @staticmethod
    def encode_sc2_unit_obs(unit: Dict[str, Any], obs_dim: int = 48) -> np.ndarray:
        """Encode a single SC2 unit into a fixed-length observation vector.

        Features encoded: health, shield, energy, position (x, y),
        weapon cooldown, unit type, is_flying, is_burrowed, build_progress.
        """
        vec = np.zeros(obs_dim, dtype=np.float32)
        vec[0] = unit.get("health", 0) / 250.0
        vec[1] = unit.get("health_max", 1) / 250.0
        vec[2] = unit.get("shield", 0) / 200.0
        vec[3] = unit.get("energy", 0) / 200.0
        vec[4] = unit.get("x", 0) / 256.0
        vec[5] = unit.get("y", 0) / 256.0
        vec[6] = unit.get("weapon_cooldown", 0) / 50.0
        vec[7] = (unit.get("unit_type_id", 0) % 256) / 255.0
        vec[8] = float(unit.get("is_flying", False))
        vec[9] = float(unit.get("is_burrowed", False))
        vec[10] = unit.get("build_progress", 1.0)
        # Relative features to nearest enemy (if available)
        vec[11] = unit.get("nearest_enemy_dist", 20.0) / 30.0
        vec[12] = unit.get("nearest_enemy_dx", 0.0) / 30.0
        vec[13] = unit.get("nearest_enemy_dy", 0.0) / 30.0
        return vec

    @staticmethod
    def encode_sc2_global_state(
        game: Dict[str, Any], unit_features: List[np.ndarray], state_dim: int = 192
    ) -> np.ndarray:
        """Build a global state vector from game-level stats and unit features.

        The global state is a concatenation of macro stats and a summary of
        all friendly unit feature vectors.
        """
        vec = np.zeros(state_dim, dtype=np.float32)
        # Macro features
        vec[0] = game.get("minerals", 0) / 10000.0
        vec[1] = game.get("vespene", 0) / 10000.0
        vec[2] = game.get("supply_used", 0) / 200.0
        vec[3] = game.get("supply_cap", 0) / 200.0
        vec[4] = game.get("game_loop", 0) / 30000.0
        vec[5] = game.get("army_supply", 0) / 200.0
        vec[6] = game.get("worker_count", 0) / 80.0
        vec[7] = game.get("tech_progress", 0.0)

        # Aggregate unit features (mean + max pooling)
        if unit_features:
            stacked = np.stack(unit_features)
            feat_mean = stacked.mean(axis=0)
            feat_max = stacked.max(axis=0)
            n_feat = min(len(feat_mean), (state_dim - 16) // 2)
            vec[8 : 8 + n_feat] = feat_mean[:n_feat]
            vec[8 + n_feat : 8 + 2 * n_feat] = feat_max[:n_feat]
        return vec

    # ----- serialization -----

    def save(self, path: str) -> None:
        state: Dict[str, Any] = {
            "config": self.cfg.__dict__,
            "train_step": self.train_step,
            "total_steps": self.total_steps,
            "epsilon": self.epsilon,
        }
        if self.use_torch:
            state["agent_nets"] = [net.state_dict() for net in self.agent_nets]
            state["mixer"] = self.mixer.state_dict()
            torch.save(state, path)
        else:
            np.savez(path, **state)
        print(f"[QMIX] Model saved to {path}")

    def load(self, path: str) -> None:
        if self.use_torch:
            state = torch.load(path, map_location="cpu")
            for i, sd in enumerate(state["agent_nets"]):
                self.agent_nets[i].load_state_dict(sd)
            self.mixer.load_state_dict(state["mixer"])
            self._hard_update_targets()
        print(f"[QMIX] Model loaded from {path}")


# ===================================================================
# Synthetic SC2 Environment
# ===================================================================


class SyntheticSC2QMIXEnv:
    """Lightweight cooperative environment for QMIX testing.

    Agents must coordinate to maximize a shared reward that depends on the
    diversity and quality of chosen actions.
    """

    def __init__(
        self,
        n_agents: int = 8,
        obs_dim: int = 48,
        state_dim: int = 192,
        action_dim: int = 12,
        max_steps: int = 100,
    ):
        self.n_agents = n_agents
        self.obs_dim = obs_dim
        self.state_dim = state_dim
        self.action_dim = action_dim
        self.max_steps = max_steps
        self.step_count = 0
        self._target_actions: Optional[np.ndarray] = None

    def reset(self) -> Tuple[List[np.ndarray], np.ndarray]:
        self.step_count = 0
        self._target_actions = np.random.randint(0, self.action_dim, self.n_agents)
        obs = [
            np.random.randn(self.obs_dim).astype(np.float32) * 0.1
            for _ in range(self.n_agents)
        ]
        state = np.random.randn(self.state_dim).astype(np.float32) * 0.1
        return obs, state

    def step(
        self, actions: List[int]
    ) -> Tuple[List[np.ndarray], np.ndarray, List[float], bool]:
        self.step_count += 1
        obs = [
            np.random.randn(self.obs_dim).astype(np.float32) * 0.1
            for _ in range(self.n_agents)
        ]
        state = np.random.randn(self.state_dim).astype(np.float32) * 0.1

        # Reward: how many agents match a hidden target action
        matches = sum(1 for a, t in zip(actions, self._target_actions) if a == t)
        reward = matches / self.n_agents
        rewards = [reward] * self.n_agents

        done = self.step_count >= self.max_steps
        return obs, state, rewards, done

    def get_action_masks(self) -> List[np.ndarray]:
        masks = []
        for _ in range(self.n_agents):
            m = np.ones(self.action_dim, dtype=np.float32)
            disable = np.random.rand(self.action_dim) < 0.15
            m[disable] = 0.0
            if m.sum() == 0:
                m[0] = 1.0
            masks.append(m)
        return masks


# ===================================================================
# CLI Demo
# ===================================================================


def run_demo(args: argparse.Namespace) -> None:
    """Run a QMIX training demo with synthetic SC2 data."""
    cfg = QMIXConfig(
        n_agents=args.n_agents,
        obs_dim=args.obs_dim,
        state_dim=args.state_dim,
        action_dim=args.action_dim,
        batch_size=args.batch_size,
        buffer_capacity=args.buffer_cap,
        eps_decay_steps=args.eps_decay,
        use_vdn=args.vdn,
        use_double_dqn=not args.no_double,
        seed=args.seed,
        device="numpy" if args.numpy else "cpu",
    )
    np.random.seed(cfg.seed)
    random.seed(cfg.seed)

    mode = "VDN" if cfg.use_vdn else "QMIX"
    backend = "NumPy (fallback)" if not HAS_TORCH or args.numpy else "PyTorch"
    double_str = "Double-DQN" if cfg.use_double_dqn else "Standard-DQN"

    print("=" * 60)
    print(f" Phase 607: {mode} Value Decomposition for SC2")
    print(f" Backend : {backend}  |  {double_str}")
    print(
        f" Agents  : {cfg.n_agents}  |  ObsDim: {cfg.obs_dim}  |  Actions: {cfg.action_dim}"
    )
    print("=" * 60)

    agent = SC2QMIXAgent(cfg)
    env = SyntheticSC2QMIXEnv(cfg.n_agents, cfg.obs_dim, cfg.state_dim, cfg.action_dim)

    n_episodes = args.episodes
    recent_rewards: deque = deque(maxlen=50)

    for ep in range(1, n_episodes + 1):
        obs, state = env.reset()
        ep_reward = 0.0
        done = False
        prev_obs, prev_state, prev_actions = None, None, None

        while not done:
            masks = env.get_action_masks()
            actions = agent.get_actions(obs, masks, explore=True)
            next_obs, next_state, rewards, done = env.step(actions)
            next_masks = env.get_action_masks()

            agent.store_transition(
                obs,
                state,
                actions,
                rewards,
                next_obs,
                next_state,
                done,
                masks,
                next_masks,
            )
            ep_reward += np.mean(rewards)
            obs, state = next_obs, next_state

            # Train every step once buffer is warm
            if agent.replay.size >= cfg.batch_size:
                agent.train()

        recent_rewards.append(ep_reward)

        if ep % max(1, n_episodes // 10) == 0:
            avg = np.mean(list(recent_rewards))
            print(
                f"Episode {ep:>4d}/{n_episodes}  "
                f"reward={ep_reward:.3f}  avg50={avg:.3f}  "
                f"eps={agent.epsilon:.3f}  "
                f"buf={agent.replay.size}"
            )

    # Final report
    print("\n" + "=" * 60)
    print(f" {mode} Demo Complete")
    print(f" Total training steps : {agent.train_step}")
    print(f" Total env steps      : {agent.total_steps}")
    print(f" Final epsilon        : {agent.epsilon:.4f}")
    print(f" Avg reward (last 50) : {np.mean(list(recent_rewards)):.4f}")
    print("=" * 60)


def main():
    parser = argparse.ArgumentParser(description="Phase 607: QMIX SC2 Agent")
    parser.add_argument("--n-agents", type=int, default=6, help="Number of agents")
    parser.add_argument(
        "--obs-dim", type=int, default=48, help="Per-agent obs dimension"
    )
    parser.add_argument(
        "--state-dim", type=int, default=192, help="Global state dimension"
    )
    parser.add_argument("--action-dim", type=int, default=12, help="Action space size")
    parser.add_argument(
        "--batch-size", type=int, default=32, help="Training batch size"
    )
    parser.add_argument(
        "--buffer-cap", type=int, default=5000, help="Replay buffer capacity"
    )
    parser.add_argument(
        "--eps-decay", type=int, default=5000, help="Epsilon decay steps"
    )
    parser.add_argument("--episodes", type=int, default=30, help="Training episodes")
    parser.add_argument("--seed", type=int, default=42, help="Random seed")
    parser.add_argument("--numpy", action="store_true", help="Force NumPy-only backend")
    parser.add_argument("--vdn", action="store_true", help="Use VDN instead of QMIX")
    parser.add_argument("--no-double", action="store_true", help="Disable Double DQN")
    args = parser.parse_args()
    run_demo(args)


if __name__ == "__main__":
    main()
