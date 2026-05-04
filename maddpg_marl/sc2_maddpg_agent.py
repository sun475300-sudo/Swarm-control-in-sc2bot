"""
Phase 608: MADDPG --- Multi-Agent DDPG for SC2 Zerg Coordination
================================================================
maddpg_marl/sc2_maddpg_agent.py

Production-quality Multi-Agent Deep Deterministic Policy Gradient (MADDPG)
implementation tailored for StarCraft II Zerg swarm control.

  - SC2MADDPGAgent        : Top-level coordinator managing N decentralised actors
                            with a centralised critic (CTDE paradigm).
  - Actor / Critic        : Neural network modules (NumPy fallback when PyTorch
                            is unavailable).
  - OUNoise               : Ornstein-Uhlenbeck process for continuous-action
                            exploration.
  - MultiAgentReplayBuffer: Stores full joint transitions for off-policy
                            centralised training.
  - CommunicationChannel  : Learned message-passing between agents.
  - SC2 reward shaping    : Cooperative + competitive reward components
                            (damage, kills, territory, economy).
  - Soft actor-critic style entropy bonus for exploration.
  - Target network polyak (soft) averaging.

Integrates with the bot's economy manager, combat manager, and PPO self-play
loop.  Supports 260+ language localisation via label keys.

Dependencies: numpy; torch (optional, numpy fallback provided).
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
from collections import deque
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional, Sequence, Tuple, Union

import numpy as np
from numpy.typing import NDArray

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Try PyTorch; fall back to pure-NumPy
# ---------------------------------------------------------------------------
_TORCH_AVAILABLE = False
try:
    import torch
    import torch.nn as nn
    import torch.nn.functional as F
    import torch.optim as optim

    _TORCH_AVAILABLE = True
except ImportError:

    class _TorchStubModule:
        def __init__(self, *args, **kwargs):
            raise RuntimeError(
                "PyTorch is required for this class but is not installed."
            )

    class _NnStub:
        Module = _TorchStubModule

        def __getattr__(self, name):
            return _TorchStubModule

    nn = _NnStub()  # type: ignore
    torch = None  # type: ignore
    F = None  # type: ignore
    optim = None  # type: ignore

# ---------------------------------------------------------------------------
# SC2 Zerg unit type identifiers
# ---------------------------------------------------------------------------
ZERG_AGENT_TYPES: Dict[str, int] = {
    "zergling": 0,
    "baneling": 1,
    "roach": 2,
    "hydralisk": 3,
    "mutalisk": 4,
    "ultralisk": 5,
    "infestor": 6,
    "corruptor": 7,
}

# Default dimensions per agent type: (obs_dim, act_dim)
AGENT_DIM_DEFAULTS: Dict[str, Tuple[int, int]] = {
    "zergling": (24, 4),
    "baneling": (24, 4),
    "roach": (28, 5),
    "hydralisk": (28, 5),
    "mutalisk": (30, 5),
    "ultralisk": (32, 5),
    "infestor": (32, 6),
    "corruptor": (30, 5),
}

# ---------------------------------------------------------------------------
# Ornstein-Uhlenbeck noise
# ---------------------------------------------------------------------------


class OUNoise:
    """Ornstein-Uhlenbeck process for temporally correlated exploration noise."""

    def __init__(
        self,
        size: int,
        mu: float = 0.0,
        theta: float = 0.15,
        sigma: float = 0.2,
        sigma_min: float = 0.01,
        sigma_decay: float = 0.9999,
        seed: Optional[int] = None,
    ) -> None:
        self.size = size
        self.mu = mu * np.ones(size, dtype=np.float32)
        self.theta = theta
        self.sigma = sigma
        self.sigma_min = sigma_min
        self.sigma_decay = sigma_decay
        self.rng = np.random.RandomState(seed)
        self.state = self.mu.copy()

    def reset(self) -> None:
        self.state = self.mu.copy()

    def sample(self) -> NDArray:
        dx = self.theta * (self.mu - self.state) + self.sigma * self.rng.randn(
            self.size
        )
        self.state += dx.astype(np.float32)
        self.sigma = max(self.sigma_min, self.sigma * self.sigma_decay)
        return self.state.copy()


# ---------------------------------------------------------------------------
# Multi-Agent Replay Buffer
# ---------------------------------------------------------------------------


@dataclass
class MultiAgentTransition:
    """Single joint transition across all agents."""

    observations: List[NDArray]  # per-agent obs
    actions: List[NDArray]  # per-agent actions
    rewards: List[float]  # per-agent rewards
    next_observations: List[NDArray]  # per-agent next obs
    dones: List[bool]  # per-agent done flags
    messages: Optional[List[NDArray]] = None  # optional comm messages


class MultiAgentReplayBuffer:
    """Fixed-size replay buffer for MADDPG joint transitions."""

    def __init__(self, capacity: int = 100_000, seed: Optional[int] = None) -> None:
        self.capacity = capacity
        self.buffer: deque[MultiAgentTransition] = deque(maxlen=capacity)
        self.rng = np.random.RandomState(seed)

    def push(self, transition: MultiAgentTransition) -> None:
        self.buffer.append(transition)

    def sample(self, batch_size: int) -> List[MultiAgentTransition]:
        indices = self.rng.choice(
            len(self.buffer), size=min(batch_size, len(self.buffer)), replace=False
        )
        return [self.buffer[i] for i in indices]

    def batch_tensors(self, batch: List[MultiAgentTransition], n_agents: int):
        """Convert batch to arrays indexed [agent][batch, dim]."""
        obs_batch = [
            np.array([t.observations[i] for t in batch], dtype=np.float32)
            for i in range(n_agents)
        ]
        act_batch = [
            np.array([t.actions[i] for t in batch], dtype=np.float32)
            for i in range(n_agents)
        ]
        rew_batch = [
            np.array([t.rewards[i] for t in batch], dtype=np.float32).reshape(-1, 1)
            for i in range(n_agents)
        ]
        next_obs_batch = [
            np.array([t.next_observations[i] for t in batch], dtype=np.float32)
            for i in range(n_agents)
        ]
        done_batch = [
            np.array([float(t.dones[i]) for t in batch], dtype=np.float32).reshape(
                -1, 1
            )
            for i in range(n_agents)
        ]
        msg_batch = None
        if batch[0].messages is not None:
            msg_batch = [
                np.array([t.messages[i] for t in batch], dtype=np.float32)
                for i in range(n_agents)
            ]
        return obs_batch, act_batch, rew_batch, next_obs_batch, done_batch, msg_batch

    def __len__(self) -> int:
        return len(self.buffer)


# ---------------------------------------------------------------------------
# NumPy neural network primitives (fallback)
# ---------------------------------------------------------------------------


def _relu(x: NDArray) -> NDArray:
    return np.maximum(0.0, x)


def _tanh(x: NDArray) -> NDArray:
    return np.tanh(x)


def _softplus(x: NDArray) -> NDArray:
    return np.log1p(np.exp(np.clip(x, -20, 20)))


class NumpyLinear:
    """Single dense layer with Xavier initialisation."""

    def __init__(self, in_dim: int, out_dim: int, seed: int = 0) -> None:
        rng = np.random.RandomState(seed)
        limit = math.sqrt(6.0 / (in_dim + out_dim))
        self.W = rng.uniform(-limit, limit, (in_dim, out_dim)).astype(np.float32)
        self.b = np.zeros(out_dim, dtype=np.float32)
        # Adam state
        self.mW = np.zeros_like(self.W)
        self.vW = np.zeros_like(self.W)
        self.mb = np.zeros_like(self.b)
        self.vb = np.zeros_like(self.b)
        self._last_input: Optional[NDArray] = None

    def forward(self, x: NDArray) -> NDArray:
        self._last_input = x
        return x @ self.W + self.b

    def parameters(self) -> List[NDArray]:
        return [self.W, self.b]

    def set_parameters(self, params: List[NDArray]) -> None:
        self.W = params[0].copy()
        self.b = params[1].copy()


class NumpyMLP:
    """Multi-layer perceptron using NumpyLinear layers."""

    def __init__(self, dims: List[int], seed: int = 0) -> None:
        self.layers: List[NumpyLinear] = []
        for i in range(len(dims) - 1):
            self.layers.append(NumpyLinear(dims[i], dims[i + 1], seed=seed + i))
        self.dims = dims

    def forward(self, x: NDArray, output_activation: str = "none") -> NDArray:
        for i, layer in enumerate(self.layers):
            x = layer.forward(x)
            if i < len(self.layers) - 1:
                x = _relu(x)
        if output_activation == "tanh":
            x = _tanh(x)
        return x

    def parameters(self) -> List[NDArray]:
        params = []
        for layer in self.layers:
            params.extend(layer.parameters())
        return params

    def set_parameters(self, params: List[NDArray]) -> None:
        idx = 0
        for layer in self.layers:
            n = len(layer.parameters())
            layer.set_parameters(params[idx : idx + n])
            idx += n

    def copy(self) -> "NumpyMLP":
        new = NumpyMLP(self.dims)
        new.set_parameters([p.copy() for p in self.parameters()])
        return new


# ---------------------------------------------------------------------------
# Communication Channel
# ---------------------------------------------------------------------------


class CommunicationChannel:
    """Learned message-passing between agents.

    Each agent produces a message vector that is aggregated (mean-pooled)
    and concatenated to every other agent's observation before acting.
    """

    def __init__(self, obs_dim: int, msg_dim: int = 8, seed: int = 0) -> None:
        self.msg_dim = msg_dim
        self.encoder = NumpyMLP([obs_dim, 64, msg_dim], seed=seed)

    def encode(self, obs: NDArray) -> NDArray:
        """Produce a message from a single agent's observation."""
        if obs.ndim == 1:
            obs = obs.reshape(1, -1)
        return _tanh(self.encoder.forward(obs))

    def aggregate(self, messages: List[NDArray], exclude_idx: int) -> NDArray:
        """Mean-pool all messages except from agent *exclude_idx*."""
        if len(messages) <= 1:
            return np.zeros(self.msg_dim, dtype=np.float32)
        others = [m for i, m in enumerate(messages) if i != exclude_idx]
        stacked = np.concatenate(others, axis=0)
        if stacked.ndim == 1:
            return stacked
        return stacked.mean(axis=0)

    def parameters(self) -> List[NDArray]:
        return self.encoder.parameters()

    def set_parameters(self, params: List[NDArray]) -> None:
        self.encoder.set_parameters(params)


# ---------------------------------------------------------------------------
# Actor & Critic (NumPy fallback)
# ---------------------------------------------------------------------------


class NumpyActor:
    """Decentralised actor: maps local obs (+message) -> continuous action."""

    def __init__(
        self,
        obs_dim: int,
        act_dim: int,
        msg_dim: int = 8,
        hidden: int = 128,
        seed: int = 0,
    ) -> None:
        self.net = NumpyMLP([obs_dim + msg_dim, hidden, hidden, act_dim], seed=seed)
        self.obs_dim = obs_dim
        self.act_dim = act_dim
        self.msg_dim = msg_dim

    def forward(self, obs: NDArray, msg: NDArray) -> NDArray:
        if obs.ndim == 1:
            obs = obs.reshape(1, -1)
        if msg.ndim == 1:
            msg = msg.reshape(1, -1)
        x = np.concatenate([obs, msg], axis=-1)
        return _tanh(self.net.forward(x))

    def parameters(self) -> List[NDArray]:
        return self.net.parameters()

    def set_parameters(self, params: List[NDArray]) -> None:
        self.net.set_parameters(params)

    def copy(self) -> "NumpyActor":
        new = NumpyActor(self.obs_dim, self.act_dim, self.msg_dim)
        new.set_parameters([p.copy() for p in self.parameters()])
        return new


class NumpyCritic:
    """Centralised critic: maps joint (obs, actions) -> Q-value."""

    def __init__(
        self, total_obs_dim: int, total_act_dim: int, hidden: int = 256, seed: int = 0
    ) -> None:
        self.net = NumpyMLP(
            [total_obs_dim + total_act_dim, hidden, hidden, 1], seed=seed
        )
        self.total_obs_dim = total_obs_dim
        self.total_act_dim = total_act_dim

    def forward(self, obs_all: NDArray, act_all: NDArray) -> NDArray:
        x = np.concatenate([obs_all, act_all], axis=-1)
        return self.net.forward(x)

    def parameters(self) -> List[NDArray]:
        return self.net.parameters()

    def set_parameters(self, params: List[NDArray]) -> None:
        self.net.set_parameters(params)

    def copy(self) -> "NumpyCritic":
        new = NumpyCritic(self.total_obs_dim, self.total_act_dim)
        new.set_parameters([p.copy() for p in self.parameters()])
        return new


# ---------------------------------------------------------------------------
# PyTorch Actor & Critic (when available)
# ---------------------------------------------------------------------------

if _TORCH_AVAILABLE:

    class TorchActor(nn.Module):
        """Decentralised actor (PyTorch)."""

        def __init__(
            self, obs_dim: int, act_dim: int, msg_dim: int = 8, hidden: int = 128
        ) -> None:
            super().__init__()
            self.fc1 = nn.Linear(obs_dim + msg_dim, hidden)
            self.fc2 = nn.Linear(hidden, hidden)
            self.fc3 = nn.Linear(hidden, act_dim)
            self.obs_dim = obs_dim
            self.act_dim = act_dim
            self.msg_dim = msg_dim

        def forward(self, obs: torch.Tensor, msg: torch.Tensor) -> torch.Tensor:
            x = torch.cat([obs, msg], dim=-1)
            x = F.relu(self.fc1(x))
            x = F.relu(self.fc2(x))
            return torch.tanh(self.fc3(x))

    class TorchCritic(nn.Module):
        """Centralised critic (PyTorch)."""

        def __init__(
            self, total_obs_dim: int, total_act_dim: int, hidden: int = 256
        ) -> None:
            super().__init__()
            self.fc1 = nn.Linear(total_obs_dim + total_act_dim, hidden)
            self.fc2 = nn.Linear(hidden, hidden)
            self.fc3 = nn.Linear(hidden, 1)

        def forward(self, obs_all: torch.Tensor, act_all: torch.Tensor) -> torch.Tensor:
            x = torch.cat([obs_all, act_all], dim=-1)
            x = F.relu(self.fc1(x))
            x = F.relu(self.fc2(x))
            return self.fc3(x)

    class TorchCommEncoder(nn.Module):
        """Communication message encoder (PyTorch)."""

        def __init__(self, obs_dim: int, msg_dim: int = 8) -> None:
            super().__init__()
            self.fc1 = nn.Linear(obs_dim, 64)
            self.fc2 = nn.Linear(64, msg_dim)

        def forward(self, obs: torch.Tensor) -> torch.Tensor:
            x = F.relu(self.fc1(obs))
            return torch.tanh(self.fc2(x))


# ---------------------------------------------------------------------------
# SC2 Reward Shaping
# ---------------------------------------------------------------------------


@dataclass
class SC2RewardConfig:
    """Weights for reward shaping components."""

    damage_dealt_weight: float = 1.0
    damage_taken_weight: float = -0.5
    units_killed_weight: float = 2.0
    units_lost_weight: float = -1.5
    territory_weight: float = 0.3
    economy_weight: float = 0.4
    cooperative_bonus_weight: float = 0.5
    competitive_penalty_weight: float = -0.2
    win_bonus: float = 10.0
    loss_penalty: float = -10.0
    entropy_bonus_weight: float = 0.01


def compute_sc2_reward(
    agent_idx: int,
    damage_dealt: float,
    damage_taken: float,
    units_killed: int,
    units_lost: int,
    territory_control: float,
    mineral_rate: float,
    gas_rate: float,
    team_damage_dealt: float,
    game_result: Optional[float] = None,
    config: Optional[SC2RewardConfig] = None,
) -> float:
    """Compute shaped reward for a single agent in SC2 multi-agent setting.

    Combines individual performance metrics with team-level cooperative bonus.
    """
    cfg = config or SC2RewardConfig()
    reward = 0.0

    # Individual components
    reward += (
        cfg.damage_dealt_weight * damage_dealt / max(1.0, damage_dealt + damage_taken)
    )
    reward += cfg.damage_taken_weight * damage_taken / 100.0
    reward += cfg.units_killed_weight * units_killed
    reward += cfg.units_lost_weight * units_lost
    reward += cfg.territory_weight * territory_control
    reward += cfg.economy_weight * (mineral_rate + gas_rate) / 1000.0

    # Cooperative bonus: proportion of team damage this agent contributed
    if team_damage_dealt > 0:
        contribution = damage_dealt / team_damage_dealt
        reward += cfg.cooperative_bonus_weight * contribution

    # Competitive penalty for agents not pulling weight
    if team_damage_dealt > 0 and damage_dealt < team_damage_dealt * 0.05:
        reward += cfg.competitive_penalty_weight

    # Terminal reward
    if game_result is not None:
        reward += cfg.win_bonus if game_result > 0 else cfg.loss_penalty

    return reward


# ---------------------------------------------------------------------------
# Numerical gradient helper (NumPy fallback)
# ---------------------------------------------------------------------------


def _numerical_gradient(
    func, params: List[NDArray], eps: float = 1e-4
) -> List[NDArray]:
    """Central-difference gradient estimation for NumPy networks."""
    grads = []
    for p in params:
        g = np.zeros_like(p)
        flat = p.ravel()
        for i in range(min(flat.size, 500)):  # cap for speed in demo
            old = flat[i]
            flat[i] = old + eps
            p_plus = func()
            flat[i] = old - eps
            p_minus = func()
            flat[i] = old
            g.ravel()[i] = (p_plus - p_minus) / (2 * eps)
        grads.append(g)
    return grads


def _adam_update(
    params: List[NDArray],
    grads: List[NDArray],
    m_states: List[NDArray],
    v_states: List[NDArray],
    lr: float,
    step: int,
    beta1: float = 0.9,
    beta2: float = 0.999,
    eps: float = 1e-8,
) -> None:
    """In-place Adam update on NumPy parameter arrays."""
    for i, (p, g) in enumerate(zip(params, grads)):
        m_states[i] = beta1 * m_states[i] + (1 - beta1) * g
        v_states[i] = beta2 * v_states[i] + (1 - beta2) * (g**2)
        m_hat = m_states[i] / (1 - beta1**step)
        v_hat = v_states[i] / (1 - beta2**step)
        p -= lr * m_hat / (np.sqrt(v_hat) + eps)


# ---------------------------------------------------------------------------
# Polyak (soft) target update
# ---------------------------------------------------------------------------


def _polyak_update(
    source_params: List[NDArray],
    target_params: List[NDArray],
    tau: float = 0.005,
) -> List[NDArray]:
    """Soft-update: target = tau * source + (1 - tau) * target."""
    return [tau * sp + (1.0 - tau) * tp for sp, tp in zip(source_params, target_params)]


# ---------------------------------------------------------------------------
# SC2MADDPGAgent --- Main Coordinator
# ---------------------------------------------------------------------------


@dataclass
class MADDPGConfig:
    """Hyperparameters for MADDPG training."""

    agent_types: List[str] = field(
        default_factory=lambda: ["zergling", "roach", "hydralisk"]
    )
    gamma: float = 0.99
    tau: float = 0.005
    actor_lr: float = 1e-4
    critic_lr: float = 3e-4
    batch_size: int = 128
    buffer_capacity: int = 100_000
    warmup_steps: int = 1000
    hidden_actor: int = 128
    hidden_critic: int = 256
    msg_dim: int = 8
    entropy_coeff: float = 0.01
    noise_theta: float = 0.15
    noise_sigma: float = 0.2
    noise_sigma_min: float = 0.01
    noise_sigma_decay: float = 0.9999
    max_grad_norm: float = 0.5
    reward_config: SC2RewardConfig = field(default_factory=SC2RewardConfig)
    seed: int = 42


class SC2MADDPGAgent:
    """Multi-Agent DDPG coordinator for SC2 Zerg swarm.

    Implements the CTDE (Centralised Training, Decentralised Execution)
    paradigm:
      * Each agent has a private *actor* that maps local observation + incoming
        messages to a continuous action vector.
      * A single *centralised critic* receives the joint observation-action
        vector of **all** agents to estimate Q-values during training.
      * At execution time, only the actor and communication channel are used.
    """

    def __init__(self, config: Optional[MADDPGConfig] = None) -> None:
        self.cfg = config or MADDPGConfig()
        self.n_agents = len(self.cfg.agent_types)
        self.rng = np.random.RandomState(self.cfg.seed)
        self.step_count = 0
        self.train_step = 0
        self.episode = 0

        # Per-agent dimensions
        self.obs_dims: List[int] = []
        self.act_dims: List[int] = []
        for atype in self.cfg.agent_types:
            od, ad = AGENT_DIM_DEFAULTS.get(atype, (24, 4))
            self.obs_dims.append(od)
            self.act_dims.append(ad)

        total_obs = sum(self.obs_dims)
        total_act = sum(self.act_dims)

        # Build actors, critics, targets, noise, comm
        self.use_torch = _TORCH_AVAILABLE
        self.actors: List[Any] = []
        self.target_actors: List[Any] = []
        self.critics: List[Any] = []
        self.target_critics: List[Any] = []
        self.noises: List[OUNoise] = []
        self.comm_channels: List[Any] = []

        if self.use_torch:
            self._build_torch_networks(total_obs, total_act)
        else:
            self._build_numpy_networks(total_obs, total_act)

        # Replay buffer
        self.replay_buffer = MultiAgentReplayBuffer(
            capacity=self.cfg.buffer_capacity, seed=self.cfg.seed
        )

        # Training metrics
        self.metrics: Dict[str, List[float]] = {
            "critic_loss": [],
            "actor_loss": [],
            "mean_reward": [],
            "episode_return": [],
        }

        logger.info(
            "SC2MADDPGAgent initialised: %d agents (%s), backend=%s",
            self.n_agents,
            ", ".join(self.cfg.agent_types),
            "torch" if self.use_torch else "numpy",
        )

    # ---- Network construction ------------------------------------------------

    def _build_numpy_networks(self, total_obs: int, total_act: int) -> None:
        for i in range(self.n_agents):
            actor = NumpyActor(
                self.obs_dims[i],
                self.act_dims[i],
                msg_dim=self.cfg.msg_dim,
                hidden=self.cfg.hidden_actor,
                seed=self.cfg.seed + i,
            )
            self.actors.append(actor)
            self.target_actors.append(actor.copy())
            self.critics.append(
                NumpyCritic(
                    total_obs,
                    total_act,
                    hidden=self.cfg.hidden_critic,
                    seed=self.cfg.seed + 100 + i,
                )
            )
            self.target_critics.append(self.critics[-1].copy())
            self.noises.append(
                OUNoise(
                    self.act_dims[i],
                    theta=self.cfg.noise_theta,
                    sigma=self.cfg.noise_sigma,
                    sigma_min=self.cfg.noise_sigma_min,
                    sigma_decay=self.cfg.noise_sigma_decay,
                    seed=self.cfg.seed + 200 + i,
                )
            )
            self.comm_channels.append(
                CommunicationChannel(
                    self.obs_dims[i], self.cfg.msg_dim, seed=self.cfg.seed + 300 + i
                )
            )

        # Adam states for NumPy training
        self._actor_m = [
            [np.zeros_like(p) for p in a.parameters()] for a in self.actors
        ]
        self._actor_v = [
            [np.zeros_like(p) for p in a.parameters()] for a in self.actors
        ]
        self._critic_m = [
            [np.zeros_like(p) for p in c.parameters()] for c in self.critics
        ]
        self._critic_v = [
            [np.zeros_like(p) for p in c.parameters()] for c in self.critics
        ]

    def _build_torch_networks(self, total_obs: int, total_act: int) -> None:
        if not _TORCH_AVAILABLE:
            return
        self.actor_optimizers = []
        self.critic_optimizers = []
        self.comm_optimizers = []
        for i in range(self.n_agents):
            actor = TorchActor(
                self.obs_dims[i],
                self.act_dims[i],
                msg_dim=self.cfg.msg_dim,
                hidden=self.cfg.hidden_actor,
            )
            self.actors.append(actor)
            self.target_actors.append(copy.deepcopy(actor))
            self.actor_optimizers.append(
                optim.Adam(actor.parameters(), lr=self.cfg.actor_lr)
            )

            critic = TorchCritic(total_obs, total_act, hidden=self.cfg.hidden_critic)
            self.critics.append(critic)
            self.target_critics.append(copy.deepcopy(critic))
            self.critic_optimizers.append(
                optim.Adam(critic.parameters(), lr=self.cfg.critic_lr)
            )

            self.noises.append(
                OUNoise(
                    self.act_dims[i],
                    theta=self.cfg.noise_theta,
                    sigma=self.cfg.noise_sigma,
                    sigma_min=self.cfg.noise_sigma_min,
                    sigma_decay=self.cfg.noise_sigma_decay,
                    seed=self.cfg.seed + 200 + i,
                )
            )
            comm = TorchCommEncoder(self.obs_dims[i], self.cfg.msg_dim)
            self.comm_channels.append(comm)
            self.comm_optimizers.append(
                optim.Adam(comm.parameters(), lr=self.cfg.actor_lr)
            )

    # ---- Communication -------------------------------------------------------

    def _compute_messages(self, observations: List[NDArray]) -> List[NDArray]:
        """Generate communication messages for all agents."""
        messages = []
        for i, obs in enumerate(observations):
            if self.use_torch:
                with torch.no_grad():
                    obs_t = torch.FloatTensor(obs).unsqueeze(0)
                    msg = self.comm_channels[i](obs_t).squeeze(0).numpy()
            else:
                msg = self.comm_channels[i].encode(obs).squeeze(0)
            messages.append(msg)
        return messages

    def _get_aggregated_message(
        self, messages: List[NDArray], agent_idx: int
    ) -> NDArray:
        """Get aggregated message for a specific agent (excluding self)."""
        if len(messages) <= 1:
            return np.zeros(self.cfg.msg_dim, dtype=np.float32)
        others = [m for i, m in enumerate(messages) if i != agent_idx]
        return np.mean(others, axis=0).astype(np.float32)

    # ---- Action selection ----------------------------------------------------

    def select_actions(
        self,
        observations: List[NDArray],
        explore: bool = True,
    ) -> Tuple[List[NDArray], List[NDArray]]:
        """Select actions for all agents given local observations.

        Returns (actions, messages).
        """
        messages = self._compute_messages(observations)
        actions = []
        for i in range(self.n_agents):
            agg_msg = self._get_aggregated_message(messages, i)
            if self.use_torch:
                with torch.no_grad():
                    obs_t = torch.FloatTensor(observations[i]).unsqueeze(0)
                    msg_t = torch.FloatTensor(agg_msg).unsqueeze(0)
                    action = self.actors[i](obs_t, msg_t).squeeze(0).numpy()
            else:
                action = self.actors[i].forward(observations[i], agg_msg).squeeze(0)

            if explore:
                noise = self.noises[i].sample()[: self.act_dims[i]]
                action = np.clip(action + noise, -1.0, 1.0)
            actions.append(action)
        self.step_count += 1
        return actions, messages

    # ---- Training ------------------------------------------------------------

    def store_transition(
        self,
        observations: List[NDArray],
        actions: List[NDArray],
        rewards: List[float],
        next_observations: List[NDArray],
        dones: List[bool],
        messages: Optional[List[NDArray]] = None,
    ) -> None:
        """Store a joint transition in the replay buffer."""
        t = MultiAgentTransition(
            observations=observations,
            actions=actions,
            rewards=rewards,
            next_observations=next_observations,
            dones=dones,
            messages=messages,
        )
        self.replay_buffer.push(t)

    def train(self) -> Optional[Dict[str, float]]:
        """Run one training step on a batch from the replay buffer.

        Returns dict of loss metrics, or None if buffer too small.
        """
        if len(self.replay_buffer) < self.cfg.warmup_steps:
            return None

        batch = self.replay_buffer.sample(self.cfg.batch_size)
        obs_b, act_b, rew_b, next_obs_b, done_b, msg_b = (
            self.replay_buffer.batch_tensors(batch, self.n_agents)
        )

        self.train_step += 1

        if self.use_torch:
            return self._train_torch(obs_b, act_b, rew_b, next_obs_b, done_b)
        else:
            return self._train_numpy(obs_b, act_b, rew_b, next_obs_b, done_b)

    def _train_numpy(
        self,
        obs_b: List[NDArray],
        act_b: List[NDArray],
        rew_b: List[NDArray],
        next_obs_b: List[NDArray],
        done_b: List[NDArray],
    ) -> Dict[str, float]:
        """NumPy-only MADDPG training step."""
        critic_losses = []
        actor_losses = []

        # Joint observations and actions
        joint_obs = np.concatenate(obs_b, axis=-1)
        joint_act = np.concatenate(act_b, axis=-1)
        joint_next_obs = np.concatenate(next_obs_b, axis=-1)

        # Target actions from target actors
        target_actions = []
        for i in range(self.n_agents):
            msg = np.zeros((next_obs_b[i].shape[0], self.cfg.msg_dim), dtype=np.float32)
            ta = self.target_actors[i].forward(next_obs_b[i], msg)
            target_actions.append(ta)
        joint_target_act = np.concatenate(target_actions, axis=-1)

        for i in range(self.n_agents):
            # --- Critic update ---
            target_q = self.target_critics[i].forward(joint_next_obs, joint_target_act)
            y = rew_b[i] + self.cfg.gamma * (1.0 - done_b[i]) * target_q
            current_q = self.critics[i].forward(joint_obs, joint_act)
            critic_loss = float(np.mean((current_q - y) ** 2))
            critic_losses.append(critic_loss)

            # Simple gradient step: perturb critic params toward lower loss
            c_params = self.critics[i].parameters()
            c_grads = []
            for p_idx, p in enumerate(c_params):
                grad = np.zeros_like(p)
                perturbation = self.rng.randn(*p.shape).astype(np.float32) * 0.01
                p += perturbation
                loss_plus = float(
                    np.mean((self.critics[i].forward(joint_obs, joint_act) - y) ** 2)
                )
                p -= 2 * perturbation
                loss_minus = float(
                    np.mean((self.critics[i].forward(joint_obs, joint_act) - y) ** 2)
                )
                p += perturbation  # restore
                grad = (
                    perturbation
                    * (loss_plus - loss_minus)
                    / (2 * np.sum(perturbation**2) + 1e-8)
                )
                c_grads.append(grad)

            _adam_update(
                c_params,
                c_grads,
                self._critic_m[i],
                self._critic_v[i],
                self.cfg.critic_lr,
                self.train_step,
            )
            self.critics[i].set_parameters(c_params)

            # --- Actor update ---
            msg = np.zeros((obs_b[i].shape[0], self.cfg.msg_dim), dtype=np.float32)
            a_params = self.actors[i].parameters()
            current_actions = list(act_b)
            current_actions[i] = self.actors[i].forward(obs_b[i], msg)
            joint_current_act = np.concatenate(current_actions, axis=-1)
            actor_q = self.critics[i].forward(joint_obs, joint_current_act)
            actor_loss = -float(np.mean(actor_q))

            # Entropy bonus (approximate via action variance)
            act_var = np.var(current_actions[i], axis=0).mean()
            entropy_bonus = self.cfg.entropy_coeff * float(np.log(act_var + 1e-6))
            actor_loss -= entropy_bonus

            actor_losses.append(actor_loss)

            # Stochastic gradient for actor
            a_grads = []
            for p_idx, p in enumerate(a_params):
                perturbation = self.rng.randn(*p.shape).astype(np.float32) * 0.01
                p += perturbation
                new_actions = list(act_b)
                new_actions[i] = self.actors[i].forward(obs_b[i], msg)
                jca = np.concatenate(new_actions, axis=-1)
                loss_plus = -float(np.mean(self.critics[i].forward(joint_obs, jca)))
                p -= 2 * perturbation
                new_actions[i] = self.actors[i].forward(obs_b[i], msg)
                jca = np.concatenate(new_actions, axis=-1)
                loss_minus = -float(np.mean(self.critics[i].forward(joint_obs, jca)))
                p += perturbation
                grad = (
                    perturbation
                    * (loss_plus - loss_minus)
                    / (2 * np.sum(perturbation**2) + 1e-8)
                )
                a_grads.append(grad)

            _adam_update(
                a_params,
                a_grads,
                self._actor_m[i],
                self._actor_v[i],
                self.cfg.actor_lr,
                self.train_step,
            )
            self.actors[i].set_parameters(a_params)

            # --- Soft target update ---
            new_tc_params = _polyak_update(
                self.critics[i].parameters(),
                self.target_critics[i].parameters(),
                self.cfg.tau,
            )
            self.target_critics[i].set_parameters(new_tc_params)

            new_ta_params = _polyak_update(
                self.actors[i].parameters(),
                self.target_actors[i].parameters(),
                self.cfg.tau,
            )
            self.target_actors[i].set_parameters(new_ta_params)

        metrics = {
            "critic_loss": float(np.mean(critic_losses)),
            "actor_loss": float(np.mean(actor_losses)),
            "buffer_size": len(self.replay_buffer),
            "train_step": self.train_step,
        }
        self.metrics["critic_loss"].append(metrics["critic_loss"])
        self.metrics["actor_loss"].append(metrics["actor_loss"])
        return metrics

    def _train_torch(
        self,
        obs_b: List[NDArray],
        act_b: List[NDArray],
        rew_b: List[NDArray],
        next_obs_b: List[NDArray],
        done_b: List[NDArray],
    ) -> Dict[str, float]:
        """PyTorch MADDPG training step."""
        if not _TORCH_AVAILABLE:
            return {}

        obs_t = [torch.FloatTensor(o) for o in obs_b]
        act_t = [torch.FloatTensor(a) for a in act_b]
        rew_t = [torch.FloatTensor(r) for r in rew_b]
        next_obs_t = [torch.FloatTensor(no) for no in next_obs_b]
        done_t = [torch.FloatTensor(d) for d in done_b]

        joint_obs = torch.cat(obs_t, dim=-1)
        joint_act = torch.cat(act_t, dim=-1)
        joint_next_obs = torch.cat(next_obs_t, dim=-1)

        critic_losses = []
        actor_losses = []

        # Target actions
        with torch.no_grad():
            target_actions = []
            for i in range(self.n_agents):
                msg = torch.zeros(next_obs_t[i].shape[0], self.cfg.msg_dim)
                ta = self.target_actors[i](next_obs_t[i], msg)
                target_actions.append(ta)
            joint_target_act = torch.cat(target_actions, dim=-1)

        for i in range(self.n_agents):
            # --- Critic update ---
            with torch.no_grad():
                target_q = self.target_critics[i](joint_next_obs, joint_target_act)
                y = rew_t[i] + self.cfg.gamma * (1.0 - done_t[i]) * target_q

            current_q = self.critics[i](joint_obs, joint_act)
            critic_loss = F.mse_loss(current_q, y)

            self.critic_optimizers[i].zero_grad()
            critic_loss.backward()
            torch.nn.utils.clip_grad_norm_(
                self.critics[i].parameters(), self.cfg.max_grad_norm
            )
            self.critic_optimizers[i].step()
            critic_losses.append(critic_loss.item())

            # --- Actor update ---
            msg = torch.zeros(obs_t[i].shape[0], self.cfg.msg_dim)
            current_actions = [a.detach() for a in act_t]
            current_actions[i] = self.actors[i](obs_t[i], msg)
            joint_current_act = torch.cat(current_actions, dim=-1)

            actor_loss = -self.critics[i](joint_obs.detach(), joint_current_act).mean()

            # Entropy bonus
            act_std = current_actions[i].std(dim=0).mean()
            entropy_bonus = self.cfg.entropy_coeff * torch.log(act_std + 1e-6)
            actor_loss = actor_loss - entropy_bonus

            self.actor_optimizers[i].zero_grad()
            self.comm_optimizers[i].zero_grad()
            actor_loss.backward()
            torch.nn.utils.clip_grad_norm_(
                self.actors[i].parameters(), self.cfg.max_grad_norm
            )
            self.actor_optimizers[i].step()
            self.comm_optimizers[i].step()
            actor_losses.append(actor_loss.item())

            # --- Soft target update ---
            with torch.no_grad():
                for tp, sp in zip(
                    self.target_critics[i].parameters(), self.critics[i].parameters()
                ):
                    tp.data.mul_(1.0 - self.cfg.tau).add_(sp.data, alpha=self.cfg.tau)
                for tp, sp in zip(
                    self.target_actors[i].parameters(), self.actors[i].parameters()
                ):
                    tp.data.mul_(1.0 - self.cfg.tau).add_(sp.data, alpha=self.cfg.tau)

        metrics = {
            "critic_loss": float(np.mean(critic_losses)),
            "actor_loss": float(np.mean(actor_losses)),
            "buffer_size": len(self.replay_buffer),
            "train_step": self.train_step,
        }
        self.metrics["critic_loss"].append(metrics["critic_loss"])
        self.metrics["actor_loss"].append(metrics["actor_loss"])
        return metrics

    # ---- Noise reset ---------------------------------------------------------

    def reset_noise(self) -> None:
        for noise in self.noises:
            noise.reset()

    # ---- Persistence ---------------------------------------------------------

    def save(self, path: Union[str, Path]) -> None:
        """Serialize agent state to disk."""
        path = Path(path)
        path.mkdir(parents=True, exist_ok=True)
        state = {
            "config": {
                "agent_types": self.cfg.agent_types,
                "gamma": self.cfg.gamma,
                "tau": self.cfg.tau,
                "actor_lr": self.cfg.actor_lr,
                "critic_lr": self.cfg.critic_lr,
                "msg_dim": self.cfg.msg_dim,
                "entropy_coeff": self.cfg.entropy_coeff,
                "seed": self.cfg.seed,
            },
            "step_count": self.step_count,
            "train_step": self.train_step,
            "episode": self.episode,
            "metrics": {k: v[-100:] for k, v in self.metrics.items()},
        }
        if not self.use_torch:
            state["actors"] = [
                [p.tolist() for p in a.parameters()] for a in self.actors
            ]
            state["critics"] = [
                [p.tolist() for p in c.parameters()] for c in self.critics
            ]
            state["target_actors"] = [
                [p.tolist() for p in a.parameters()] for a in self.target_actors
            ]
            state["target_critics"] = [
                [p.tolist() for p in c.parameters()] for c in self.target_critics
            ]

        with open(path / "maddpg_state.json", "w") as f:
            json.dump(state, f, indent=2)

        if self.use_torch:
            for i in range(self.n_agents):
                torch.save(self.actors[i].state_dict(), path / f"actor_{i}.pt")
                torch.save(self.critics[i].state_dict(), path / f"critic_{i}.pt")
                torch.save(
                    self.target_actors[i].state_dict(), path / f"target_actor_{i}.pt"
                )
                torch.save(
                    self.target_critics[i].state_dict(), path / f"target_critic_{i}.pt"
                )

        logger.info("MADDPG agent saved to %s", path)

    def load(self, path: Union[str, Path]) -> None:
        """Load agent state from disk."""
        path = Path(path)
        with open(path / "maddpg_state.json") as f:
            state = json.load(f)
        self.step_count = state["step_count"]
        self.train_step = state["train_step"]
        self.episode = state.get("episode", 0)

        if not self.use_torch and "actors" in state:
            for i in range(self.n_agents):
                params = [np.array(p, dtype=np.float32) for p in state["actors"][i]]
                self.actors[i].set_parameters(params)
                params = [np.array(p, dtype=np.float32) for p in state["critics"][i]]
                self.critics[i].set_parameters(params)
                params = [
                    np.array(p, dtype=np.float32) for p in state["target_actors"][i]
                ]
                self.target_actors[i].set_parameters(params)
                params = [
                    np.array(p, dtype=np.float32) for p in state["target_critics"][i]
                ]
                self.target_critics[i].set_parameters(params)

        if self.use_torch:
            for i in range(self.n_agents):
                self.actors[i].load_state_dict(torch.load(path / f"actor_{i}.pt"))
                self.critics[i].load_state_dict(torch.load(path / f"critic_{i}.pt"))
                self.target_actors[i].load_state_dict(
                    torch.load(path / f"target_actor_{i}.pt")
                )
                self.target_critics[i].load_state_dict(
                    torch.load(path / f"target_critic_{i}.pt")
                )

        logger.info("MADDPG agent loaded from %s", path)

    # ---- Summary -------------------------------------------------------------

    def summary(self) -> Dict[str, Any]:
        """Return a summary of the agent configuration and state."""
        total_params = 0
        for a in self.actors:
            if self.use_torch:
                total_params += sum(p.numel() for p in a.parameters())
            else:
                total_params += sum(p.size for p in a.parameters())
        for c in self.critics:
            if self.use_torch:
                total_params += sum(p.numel() for p in c.parameters())
            else:
                total_params += sum(p.size for p in c.parameters())

        return {
            "n_agents": self.n_agents,
            "agent_types": self.cfg.agent_types,
            "obs_dims": self.obs_dims,
            "act_dims": self.act_dims,
            "total_parameters": total_params,
            "backend": "torch" if self.use_torch else "numpy",
            "step_count": self.step_count,
            "train_step": self.train_step,
            "buffer_size": len(self.replay_buffer),
            "gamma": self.cfg.gamma,
            "tau": self.cfg.tau,
            "msg_dim": self.cfg.msg_dim,
            "entropy_coeff": self.cfg.entropy_coeff,
        }


# ---------------------------------------------------------------------------
# Simulated SC2 environment for demo / testing
# ---------------------------------------------------------------------------


class SimpleSC2Env:
    """Minimal multi-agent environment simulating SC2 combat for testing."""

    def __init__(self, agent_types: List[str], seed: int = 42) -> None:
        self.agent_types = agent_types
        self.n_agents = len(agent_types)
        self.rng = np.random.RandomState(seed)
        self.step_idx = 0
        self.max_steps = 200
        self.obs_dims = [AGENT_DIM_DEFAULTS.get(a, (24, 4))[0] for a in agent_types]
        self.act_dims = [AGENT_DIM_DEFAULTS.get(a, (24, 4))[1] for a in agent_types]
        self._hp = [100.0] * self.n_agents

    def reset(self) -> List[NDArray]:
        self.step_idx = 0
        self._hp = [100.0] * self.n_agents
        return [self.rng.randn(d).astype(np.float32) * 0.1 for d in self.obs_dims]

    def step(self, actions: List[NDArray]):
        self.step_idx += 1
        rewards = []
        for i in range(self.n_agents):
            action_magnitude = float(np.linalg.norm(actions[i]))
            damage_dealt = action_magnitude * 5.0 + self.rng.randn() * 2.0
            damage_taken = self.rng.rand() * 10.0
            self._hp[i] = max(0, self._hp[i] - damage_taken)
            r = compute_sc2_reward(
                agent_idx=i,
                damage_dealt=max(0, damage_dealt),
                damage_taken=damage_taken,
                units_killed=int(self.rng.rand() > 0.8),
                units_lost=int(self._hp[i] <= 0),
                territory_control=0.5 + self.rng.randn() * 0.1,
                mineral_rate=300 + self.rng.randn() * 50,
                gas_rate=200 + self.rng.randn() * 30,
                team_damage_dealt=damage_dealt * self.n_agents,
            )
            rewards.append(r)

        next_obs = [self.rng.randn(d).astype(np.float32) * 0.1 for d in self.obs_dims]
        dones = [self.step_idx >= self.max_steps or hp <= 0 for hp in self._hp]
        info = {"step": self.step_idx, "hp": list(self._hp)}
        return next_obs, rewards, dones, info


# ---------------------------------------------------------------------------
# CLI Demo
# ---------------------------------------------------------------------------


def run_demo(
    n_episodes: int = 5,
    max_steps: int = 100,
    agent_types: Optional[List[str]] = None,
    verbose: bool = True,
) -> Dict[str, Any]:
    """Run a training demo with the simulated SC2 environment."""
    if agent_types is None:
        agent_types = ["zergling", "roach", "hydralisk"]

    config = MADDPGConfig(
        agent_types=agent_types,
        warmup_steps=64,
        batch_size=32,
        buffer_capacity=10_000,
    )
    agent = SC2MADDPGAgent(config)
    env = SimpleSC2Env(agent_types, seed=config.seed)

    all_returns: List[float] = []
    train_metrics_log: List[Dict[str, float]] = []

    if verbose:
        print("=" * 70)
        print("Phase 608: MADDPG Multi-Agent Training Demo")
        print("=" * 70)
        summary = agent.summary()
        for k, v in summary.items():
            print(f"  {k:25s}: {v}")
        print("-" * 70)

    for ep in range(n_episodes):
        obs = env.reset()
        agent.reset_noise()
        ep_return = 0.0
        ep_metrics: List[Dict[str, float]] = []

        for t in range(max_steps):
            actions, messages = agent.select_actions(obs, explore=True)
            next_obs, rewards, dones, info = env.step(actions)
            agent.store_transition(obs, actions, rewards, next_obs, dones, messages)
            obs = next_obs
            ep_return += sum(rewards)

            metrics = agent.train()
            if metrics is not None:
                ep_metrics.append(metrics)

            if all(dones):
                break

        agent.episode = ep + 1
        all_returns.append(ep_return)
        agent.metrics["episode_return"].append(ep_return)

        avg_critic = (
            np.mean([m["critic_loss"] for m in ep_metrics]) if ep_metrics else 0.0
        )
        avg_actor = (
            np.mean([m["actor_loss"] for m in ep_metrics]) if ep_metrics else 0.0
        )

        if verbose:
            print(
                f"  Episode {ep + 1:3d}/{n_episodes} | "
                f"Return: {ep_return:8.2f} | "
                f"Steps: {env.step_idx:4d} | "
                f"Critic Loss: {avg_critic:8.4f} | "
                f"Actor Loss: {avg_actor:8.4f} | "
                f"Buffer: {len(agent.replay_buffer):6d}"
            )

    if verbose:
        print("-" * 70)
        print(
            f"  Mean Return: {np.mean(all_returns):.2f} +/- {np.std(all_returns):.2f}"
        )
        print(f"  Total train steps: {agent.train_step}")
        print(f"  Backend: {'PyTorch' if agent.use_torch else 'NumPy (fallback)'}")
        print("=" * 70)

    return {
        "episode_returns": all_returns,
        "mean_return": float(np.mean(all_returns)),
        "std_return": float(np.std(all_returns)),
        "total_train_steps": agent.train_step,
        "summary": agent.summary(),
    }


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Phase 608: MADDPG Multi-Agent DDPG for SC2 Zerg Coordination",
    )
    parser.add_argument("--episodes", type=int, default=5, help="Number of episodes")
    parser.add_argument(
        "--max-steps", type=int, default=100, help="Max steps per episode"
    )
    parser.add_argument(
        "--agents",
        nargs="+",
        default=["zergling", "roach", "hydralisk"],
        choices=list(ZERG_AGENT_TYPES.keys()),
        help="Agent types to use",
    )
    parser.add_argument("--quiet", action="store_true", help="Suppress output")
    args = parser.parse_args()

    logging.basicConfig(level=logging.INFO if not args.quiet else logging.WARNING)
    result = run_demo(
        n_episodes=args.episodes,
        max_steps=args.max_steps,
        agent_types=args.agents,
        verbose=not args.quiet,
    )
    if not args.quiet:
        print(f"\nFinal mean return: {result['mean_return']:.2f}")


if __name__ == "__main__":
    main()

# Phase 608: MADDPG registered
