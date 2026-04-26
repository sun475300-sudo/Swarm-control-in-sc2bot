"""
Phase 606: MAPPO (Multi-Agent PPO) for StarCraft II
====================================================

Centralized Training with Decentralized Execution (CTDE) using Multi-Agent
Proximal Policy Optimization. Each SC2 unit is treated as an independent agent
with its own actor network, while a shared centralized critic observes the
global state for stable value estimation.

Key features:
  - Shared observation encoder across all agents
  - Global-state centralized critic network
  - Per-agent decentralized actor networks with action masking
  - GAE advantage estimation via the centralized value function
  - Multi-agent rollout buffer with per-agent indexing
  - PPO clipped surrogate objective trained per agent
  - Self-play league with ELO rating
  - Population-Based Training (PBT) hyperparameter mutation
  - Full NumPy fallback when PyTorch is unavailable
"""

from __future__ import annotations

import argparse
import copy
import math
import random
import time
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Sequence, Tuple

import numpy as np

# ---------------------------------------------------------------------------
# Optional PyTorch import with NumPy fallback
# ---------------------------------------------------------------------------
try:
    import torch
    import torch.nn as nn
    import torch.optim as optim
    from torch.distributions import Categorical

    HAS_TORCH = True
except ImportError:
    HAS_TORCH = False

    class _NnStub:
        Module = type("Module", (object,), {"__init__": lambda self, *a, **k: None})

        def __getattr__(self, name):
            raise RuntimeError(
                f"PyTorch is required for nn.{name}; install torch to enable this code path"
            )

    nn = _NnStub()
    optim = _NnStub()
    torch = None
    Categorical = None

# ===================================================================
# NumPy fallback helpers
# ===================================================================


def _np_softmax(logits: np.ndarray) -> np.ndarray:
    """Numerically stable softmax."""
    shifted = logits - np.max(logits, axis=-1, keepdims=True)
    exp = np.exp(shifted)
    return exp / np.sum(exp, axis=-1, keepdims=True)


def _np_log_softmax(logits: np.ndarray) -> np.ndarray:
    shifted = logits - np.max(logits, axis=-1, keepdims=True)
    return shifted - np.log(np.sum(np.exp(shifted), axis=-1, keepdims=True))


def _np_categorical_sample(probs: np.ndarray) -> int:
    """Sample from a categorical distribution given probabilities."""
    return int(np.random.choice(len(probs), p=probs))


def _np_relu(x: np.ndarray) -> np.ndarray:
    return np.maximum(0.0, x)


def _np_layer_norm(x: np.ndarray, eps: float = 1e-5) -> np.ndarray:
    mean = np.mean(x, axis=-1, keepdims=True)
    var = np.var(x, axis=-1, keepdims=True)
    return (x - mean) / np.sqrt(var + eps)


def _np_linear(x: np.ndarray, W: np.ndarray, b: np.ndarray) -> np.ndarray:
    """Dense layer: y = xW^T + b."""
    return x @ W.T + b


# ===================================================================
# Configuration
# ===================================================================


@dataclass
class MAPPOConfig:
    """Hyperparameters for Multi-Agent PPO training."""

    # Environment
    n_agents: int = 12
    obs_dim: int = 64
    global_state_dim: int = 256
    action_dim: int = 16

    # PPO
    lr_actor: float = 3e-4
    lr_critic: float = 1e-3
    gamma: float = 0.99
    gae_lambda: float = 0.95
    clip_eps: float = 0.2
    value_coef: float = 0.5
    entropy_coef: float = 0.01
    max_grad_norm: float = 10.0

    # Training
    n_steps: int = 1024
    n_epochs: int = 5
    mini_batch_size: int = 256
    hidden_dim: int = 128
    encoder_dim: int = 64

    # Self-play / PBT
    league_size: int = 6
    elo_k: float = 32.0
    pbt_mutation_prob: float = 0.25
    pbt_perturb_factor: float = 0.2

    # Misc
    seed: int = 42
    device: str = "cpu"


# ===================================================================
# NumPy-only network surrogates
# ===================================================================


class NumpyLinear:
    """A single dense layer with Xavier-initialised weights."""

    def __init__(self, in_dim: int, out_dim: int):
        limit = math.sqrt(6.0 / (in_dim + out_dim))
        self.W = np.random.uniform(-limit, limit, (out_dim, in_dim)).astype(np.float32)
        self.b = np.zeros(out_dim, dtype=np.float32)

    def __call__(self, x: np.ndarray) -> np.ndarray:
        return _np_linear(x, self.W, self.b)


class NumpyMLP:
    """Simple feedforward MLP built from *NumpyLinear* layers."""

    def __init__(self, dims: Sequence[int], activate_last: bool = False):
        self.layers: List[NumpyLinear] = []
        self.activate_last = activate_last
        for i in range(len(dims) - 1):
            self.layers.append(NumpyLinear(dims[i], dims[i + 1]))

    def __call__(self, x: np.ndarray) -> np.ndarray:
        for i, layer in enumerate(self.layers):
            x = layer(x)
            if i < len(self.layers) - 1 or self.activate_last:
                x = _np_relu(x)
        return x

    def parameters(self) -> List[np.ndarray]:
        params: List[np.ndarray] = []
        for layer in self.layers:
            params.extend([layer.W, layer.b])
        return params


# ===================================================================
# Shared Observation Encoder
# ===================================================================


class SharedObsEncoderTorch(nn.Module):
    """Encodes per-agent local observations into a latent vector."""

    def __init__(self, obs_dim: int, encoder_dim: int, hidden_dim: int):
        super().__init__()
        self.net = nn.Sequential(
            nn.Linear(obs_dim, hidden_dim),
            nn.ReLU(),
            nn.LayerNorm(hidden_dim),
            nn.Linear(hidden_dim, encoder_dim),
            nn.ReLU(),
        )

    def forward(self, obs: torch.Tensor) -> torch.Tensor:
        return self.net(obs)


class SharedObsEncoderNumpy:
    """NumPy fallback for the shared observation encoder."""

    def __init__(self, obs_dim: int, encoder_dim: int, hidden_dim: int):
        self.fc1 = NumpyLinear(obs_dim, hidden_dim)
        self.fc2 = NumpyLinear(hidden_dim, encoder_dim)

    def __call__(self, obs: np.ndarray) -> np.ndarray:
        h = _np_relu(self.fc1(obs))
        h = _np_layer_norm(h)
        return _np_relu(self.fc2(h))


# ===================================================================
# Centralized Critic
# ===================================================================


class CentralizedCriticTorch(nn.Module):
    """Value network that takes the global state and outputs V(s)."""

    def __init__(self, state_dim: int, hidden_dim: int):
        super().__init__()
        self.net = nn.Sequential(
            nn.Linear(state_dim, hidden_dim),
            nn.ReLU(),
            nn.Linear(hidden_dim, hidden_dim),
            nn.ReLU(),
            nn.Linear(hidden_dim, 1),
        )

    def forward(self, state: torch.Tensor) -> torch.Tensor:
        return self.net(state).squeeze(-1)


class CentralizedCriticNumpy:
    """NumPy fallback for the centralized critic."""

    def __init__(self, state_dim: int, hidden_dim: int):
        self.mlp = NumpyMLP([state_dim, hidden_dim, hidden_dim, 1])

    def __call__(self, state: np.ndarray) -> np.ndarray:
        return self.mlp(state).squeeze(-1)

    def parameters(self) -> List[np.ndarray]:
        return self.mlp.parameters()


# ===================================================================
# Decentralized Actor
# ===================================================================


class DecentralizedActorTorch(nn.Module):
    """Per-agent policy network with action masking support."""

    def __init__(self, encoder_dim: int, action_dim: int, hidden_dim: int):
        super().__init__()
        self.net = nn.Sequential(
            nn.Linear(encoder_dim, hidden_dim),
            nn.ReLU(),
            nn.Linear(hidden_dim, action_dim),
        )

    def forward(
        self, encoded_obs: torch.Tensor, action_mask: Optional[torch.Tensor] = None
    ) -> torch.Tensor:
        """Return masked logits."""
        logits = self.net(encoded_obs)
        if action_mask is not None:
            logits = logits + (1.0 - action_mask) * (-1e8)
        return logits

    def get_action_and_log_prob(
        self, encoded_obs: torch.Tensor, action_mask: Optional[torch.Tensor] = None
    ) -> Tuple[torch.Tensor, torch.Tensor, torch.Tensor]:
        logits = self.forward(encoded_obs, action_mask)
        dist = Categorical(logits=logits)
        action = dist.sample()
        return action, dist.log_prob(action), dist.entropy()

    def evaluate_actions(
        self,
        encoded_obs: torch.Tensor,
        actions: torch.Tensor,
        action_mask: Optional[torch.Tensor] = None,
    ) -> Tuple[torch.Tensor, torch.Tensor]:
        logits = self.forward(encoded_obs, action_mask)
        dist = Categorical(logits=logits)
        return dist.log_prob(actions), dist.entropy()


class DecentralizedActorNumpy:
    """NumPy fallback for the decentralized actor."""

    def __init__(self, encoder_dim: int, action_dim: int, hidden_dim: int):
        self.mlp = NumpyMLP([encoder_dim, hidden_dim, action_dim])

    def forward(
        self, encoded_obs: np.ndarray, action_mask: Optional[np.ndarray] = None
    ) -> np.ndarray:
        logits = self.mlp(encoded_obs)
        if action_mask is not None:
            logits = logits + (1.0 - action_mask) * (-1e8)
        return logits

    def get_action_and_log_prob(
        self, encoded_obs: np.ndarray, action_mask: Optional[np.ndarray] = None
    ) -> Tuple[int, float, float]:
        logits = self.forward(encoded_obs, action_mask)
        log_probs = _np_log_softmax(logits)
        probs = _np_softmax(logits)
        action = _np_categorical_sample(probs)
        entropy = -float(np.sum(probs * log_probs))
        return action, float(log_probs[action]), entropy

    def evaluate_actions(
        self, encoded_obs: np.ndarray, actions: np.ndarray, action_mask: Optional[np.ndarray] = None
    ) -> Tuple[np.ndarray, np.ndarray]:
        logits = self.forward(encoded_obs, action_mask)
        log_probs = _np_log_softmax(logits)
        probs = _np_softmax(logits)
        chosen_log_probs = log_probs[np.arange(len(actions)), actions.astype(int)]
        entropy = -np.sum(probs * log_probs, axis=-1)
        return chosen_log_probs, entropy

    def parameters(self) -> List[np.ndarray]:
        return self.mlp.parameters()


# ===================================================================
# Multi-Agent Rollout Buffer
# ===================================================================


class MultiAgentRolloutBuffer:
    """Stores transitions for *n_agents* agents across *n_steps* time-steps.

    Data layout
    -----------
    Each field is a list (over time-steps) of lists (over agents), making it
    straightforward to slice by agent or by time.
    """

    def __init__(self, n_agents: int, n_steps: int):
        self.n_agents = n_agents
        self.n_steps = n_steps
        self.reset()

    def reset(self) -> None:
        self.obs: List[List[np.ndarray]] = []
        self.global_states: List[np.ndarray] = []
        self.actions: List[List[int]] = []
        self.rewards: List[List[float]] = []
        self.log_probs: List[List[float]] = []
        self.values: List[float] = []
        self.dones: List[bool] = []
        self.action_masks: List[List[Optional[np.ndarray]]] = []
        self.ptr = 0

    def add(
        self,
        obs_all: List[np.ndarray],
        global_state: np.ndarray,
        actions: List[int],
        rewards: List[float],
        log_probs: List[float],
        value: float,
        done: bool,
        action_masks: Optional[List[np.ndarray]] = None,
    ) -> None:
        self.obs.append(obs_all)
        self.global_states.append(global_state)
        self.actions.append(actions)
        self.rewards.append(rewards)
        self.log_probs.append(log_probs)
        self.values.append(value)
        self.dones.append(done)
        if action_masks is not None:
            self.action_masks.append(action_masks)
        else:
            self.action_masks.append([None] * self.n_agents)
        self.ptr += 1

    def is_full(self) -> bool:
        return self.ptr >= self.n_steps

    # ----- GAE computation -----

    def compute_gae(
        self, last_value: float, gamma: float = 0.99, lam: float = 0.95
    ) -> Tuple[np.ndarray, np.ndarray]:
        """Compute per-agent GAE advantages using the *centralized* value.

        Returns
        -------
        advantages : np.ndarray, shape (n_steps, n_agents)
        returns    : np.ndarray, shape (n_steps,)
        """
        T = self.ptr
        # Team reward = mean across agents
        team_rewards = np.array(
            [np.mean(r) for r in self.rewards[:T]], dtype=np.float32
        )
        values = np.array(self.values[:T], dtype=np.float32)
        dones = np.array(self.dones[:T], dtype=np.float32)

        advantages = np.zeros(T, dtype=np.float32)
        gae = 0.0
        for t in reversed(range(T)):
            next_val = last_value if t == T - 1 else values[t + 1]
            next_non_terminal = 1.0 - (dones[t] if t < T else 0.0)
            delta = team_rewards[t] + gamma * next_val * next_non_terminal - values[t]
            gae = delta + gamma * lam * next_non_terminal * gae
            advantages[t] = gae

        returns = advantages + values
        # Broadcast advantage to all agents (shared team advantage)
        advantages_2d = np.tile(advantages[:, None], (1, self.n_agents))
        return advantages_2d, returns

    def generate_batches(
        self, advantages: np.ndarray, returns: np.ndarray, batch_size: int
    ):
        """Yield mini-batches of flattened (step x agent) transitions."""
        T = self.ptr
        N = self.n_agents
        total = T * N
        indices = np.arange(total)
        np.random.shuffle(indices)

        # Flatten arrays
        flat_obs = np.array(
            [self.obs[t][a] for t in range(T) for a in range(N)], dtype=np.float32
        )
        flat_gs = np.array(
            [self.global_states[t] for t in range(T) for _ in range(N)],
            dtype=np.float32,
        )
        flat_actions = np.array(
            [self.actions[t][a] for t in range(T) for a in range(N)], dtype=np.int64
        )
        flat_lp = np.array(
            [self.log_probs[t][a] for t in range(T) for a in range(N)],
            dtype=np.float32,
        )
        flat_adv = advantages.reshape(-1)
        flat_ret = np.array(
            [returns[t] for t in range(T) for _ in range(N)], dtype=np.float32
        )
        flat_masks: List[Optional[np.ndarray]] = [
            self.action_masks[t][a] for t in range(T) for a in range(N)
        ]

        for start in range(0, total, batch_size):
            end = min(start + batch_size, total)
            idx = indices[start:end]
            batch_masks = [flat_masks[i] for i in idx]
            mask_array = (
                np.stack(batch_masks).astype(np.float32)
                if batch_masks[0] is not None
                else None
            )
            yield {
                "obs": flat_obs[idx],
                "global_state": flat_gs[idx],
                "actions": flat_actions[idx],
                "old_log_probs": flat_lp[idx],
                "advantages": flat_adv[idx],
                "returns": flat_ret[idx],
                "action_masks": mask_array,
            }


# ===================================================================
# Self-Play League
# ===================================================================


class ELOLeague:
    """Simple ELO-based league for self-play agent selection."""

    def __init__(self, league_size: int, k: float = 32.0):
        self.league_size = league_size
        self.k = k
        self.ratings: Dict[str, float] = {}
        self.snapshots: Dict[str, Any] = {}

    def register(self, agent_id: str, snapshot: Any, initial_elo: float = 1200.0):
        self.ratings[agent_id] = initial_elo
        self.snapshots[agent_id] = snapshot

    def expected_score(self, ra: float, rb: float) -> float:
        return 1.0 / (1.0 + 10.0 ** ((rb - ra) / 400.0))

    def update(self, winner_id: str, loser_id: str) -> None:
        ra, rb = self.ratings[winner_id], self.ratings[loser_id]
        ea = self.expected_score(ra, rb)
        self.ratings[winner_id] += self.k * (1.0 - ea)
        self.ratings[loser_id] -= self.k * (1.0 - (1.0 - ea))

    def select_opponent(self, agent_id: str) -> str:
        """Pick an opponent with probability weighted by closeness in ELO."""
        others = [k for k in self.ratings if k != agent_id]
        if not others:
            return agent_id
        ra = self.ratings[agent_id]
        diffs = np.array([abs(self.ratings[o] - ra) for o in others], dtype=np.float32)
        inv_diffs = 1.0 / (diffs + 50.0)
        probs = inv_diffs / inv_diffs.sum()
        return str(np.random.choice(others, p=probs))

    def top_agents(self, n: int = 3) -> List[Tuple[str, float]]:
        sorted_agents = sorted(self.ratings.items(), key=lambda x: -x[1])
        return sorted_agents[:n]


# ===================================================================
# Population-Based Training (PBT)
# ===================================================================


class PBTManager:
    """Mutates hyper-parameters for a population of training agents."""

    MUTABLE_KEYS = ["lr_actor", "lr_critic", "clip_eps", "entropy_coef", "gae_lambda"]

    def __init__(self, population_size: int, mutation_prob: float = 0.25, perturb: float = 0.2):
        self.population_size = population_size
        self.mutation_prob = mutation_prob
        self.perturb = perturb
        self.population: List[Dict[str, float]] = []
        self.fitness: List[float] = []

    def init_population(self, base_config: MAPPOConfig) -> List[Dict[str, float]]:
        self.population = []
        for _ in range(self.population_size):
            member: Dict[str, float] = {}
            for key in self.MUTABLE_KEYS:
                base_val = getattr(base_config, key)
                member[key] = base_val * (1.0 + np.random.uniform(-self.perturb, self.perturb))
            self.population.append(member)
        self.fitness = [0.0] * self.population_size
        return self.population

    def update_fitness(self, idx: int, fitness: float) -> None:
        self.fitness[idx] = fitness

    def exploit_and_explore(self) -> List[Dict[str, float]]:
        """Bottom 20 % copies hyper-params from top 20 %, then mutates."""
        ranked = sorted(range(len(self.fitness)), key=lambda i: -self.fitness[i])
        top_cutoff = max(1, len(ranked) // 5)
        bottom_cutoff = len(ranked) - top_cutoff

        for rank_pos in range(bottom_cutoff, len(ranked)):
            loser_idx = ranked[rank_pos]
            winner_idx = ranked[np.random.randint(0, top_cutoff)]
            self.population[loser_idx] = copy.deepcopy(self.population[winner_idx])
            # mutate
            for key in self.MUTABLE_KEYS:
                if np.random.random() < self.mutation_prob:
                    factor = 1.0 + np.random.uniform(-self.perturb, self.perturb)
                    self.population[loser_idx][key] *= factor
        return self.population


# ===================================================================
# SC2 MAPPO Agent (main class)
# ===================================================================


class SC2MAPPOAgent:
    """Multi-Agent PPO with centralized critic for StarCraft II.

    In CTDE fashion:
      * Each unit has a *decentralized actor* selecting actions from its own
        local observation.
      * A single *centralized critic* evaluates the global state value shared
        by all agents.

    Parameters
    ----------
    cfg : MAPPOConfig
        Full configuration dataclass.
    """

    def __init__(self, cfg: MAPPOConfig):
        self.cfg = cfg
        self.use_torch = HAS_TORCH and cfg.device != "numpy"
        self._build_networks()
        self.buffer = MultiAgentRolloutBuffer(cfg.n_agents, cfg.n_steps)
        self.league = ELOLeague(cfg.league_size, cfg.elo_k)
        self.pbt = PBTManager(cfg.league_size, cfg.pbt_mutation_prob, cfg.pbt_perturb_factor)
        self.train_step = 0

    # ----- network construction -----

    def _build_networks(self) -> None:
        cfg = self.cfg
        if self.use_torch:
            self.encoder = SharedObsEncoderTorch(cfg.obs_dim, cfg.encoder_dim, cfg.hidden_dim)
            self.critic = CentralizedCriticTorch(cfg.global_state_dim, cfg.hidden_dim)
            self.actors: List[Any] = [
                DecentralizedActorTorch(cfg.encoder_dim, cfg.action_dim, cfg.hidden_dim)
                for _ in range(cfg.n_agents)
            ]
            # Shared encoder params + all actor params in one optimizer
            actor_params = list(self.encoder.parameters())
            for actor in self.actors:
                actor_params += list(actor.parameters())
            self.actor_optim = optim.Adam(actor_params, lr=cfg.lr_actor)
            self.critic_optim = optim.Adam(self.critic.parameters(), lr=cfg.lr_critic)
        else:
            self.encoder = SharedObsEncoderNumpy(cfg.obs_dim, cfg.encoder_dim, cfg.hidden_dim)
            self.critic = CentralizedCriticNumpy(cfg.global_state_dim, cfg.hidden_dim)
            self.actors = [
                DecentralizedActorNumpy(cfg.encoder_dim, cfg.action_dim, cfg.hidden_dim)
                for _ in range(cfg.n_agents)
            ]

    # ----- inference -----

    def get_actions(
        self,
        observations: List[np.ndarray],
        global_state: np.ndarray,
        action_masks: Optional[List[np.ndarray]] = None,
    ) -> Tuple[List[int], List[float], float]:
        """Select actions for all agents and estimate state value.

        Returns
        -------
        actions    : list of ints (one per agent)
        log_probs  : list of floats
        value      : float  (centralized V(s))
        """
        actions: List[int] = []
        log_probs: List[float] = []

        if self.use_torch:
            with torch.no_grad():
                gs_t = torch.tensor(global_state, dtype=torch.float32)
                value = float(self.critic(gs_t).item())
                for i, actor in enumerate(self.actors):
                    obs_t = torch.tensor(observations[i], dtype=torch.float32)
                    enc = self.encoder(obs_t.unsqueeze(0)).squeeze(0)
                    mask_t = (
                        torch.tensor(action_masks[i], dtype=torch.float32)
                        if action_masks is not None
                        else None
                    )
                    a, lp, _ = actor.get_action_and_log_prob(enc.unsqueeze(0), mask_t.unsqueeze(0) if mask_t is not None else None)
                    actions.append(int(a.item()))
                    log_probs.append(float(lp.item()))
        else:
            value = float(self.critic(global_state))
            for i, actor in enumerate(self.actors):
                enc = self.encoder(observations[i].reshape(1, -1)).squeeze(0)
                mask = action_masks[i] if action_masks is not None else None
                a, lp, _ = actor.get_action_and_log_prob(enc, mask)
                actions.append(a)
                log_probs.append(lp)

        return actions, log_probs, value

    # ----- collect step -----

    def collect_step(
        self,
        observations: List[np.ndarray],
        global_state: np.ndarray,
        rewards: List[float],
        done: bool,
        action_masks: Optional[List[np.ndarray]] = None,
    ) -> List[int]:
        """One environment step: pick actions, store transition."""
        actions, log_probs, value = self.get_actions(observations, global_state, action_masks)
        self.buffer.add(
            observations, global_state, actions, rewards, log_probs, value, done, action_masks
        )
        return actions

    # ----- training (PPO update) -----

    def train(self) -> Dict[str, float]:
        """Run PPO update on the collected rollout buffer.

        Returns a dictionary with loss statistics.
        """
        cfg = self.cfg
        # Compute last value for GAE bootstrap
        last_gs = self.buffer.global_states[-1]
        if self.use_torch:
            with torch.no_grad():
                last_val = float(
                    self.critic(torch.tensor(last_gs, dtype=torch.float32)).item()
                )
        else:
            last_val = float(self.critic(last_gs))

        advantages, returns = self.buffer.compute_gae(last_val, cfg.gamma, cfg.gae_lambda)

        # Normalise advantages
        adv_mean = advantages.mean()
        adv_std = advantages.std() + 1e-8
        advantages = (advantages - adv_mean) / adv_std

        total_policy_loss = 0.0
        total_value_loss = 0.0
        total_entropy = 0.0
        n_updates = 0

        for _ in range(cfg.n_epochs):
            for batch in self.buffer.generate_batches(advantages, returns, cfg.mini_batch_size):
                if self.use_torch:
                    pl, vl, ent = self._torch_update(batch)
                else:
                    pl, vl, ent = self._numpy_update(batch)
                total_policy_loss += pl
                total_value_loss += vl
                total_entropy += ent
                n_updates += 1

        self.train_step += 1
        self.buffer.reset()

        return {
            "policy_loss": total_policy_loss / max(n_updates, 1),
            "value_loss": total_value_loss / max(n_updates, 1),
            "entropy": total_entropy / max(n_updates, 1),
            "train_step": self.train_step,
        }

    def _torch_update(self, batch: Dict[str, Any]) -> Tuple[float, float, float]:
        """Single PPO gradient step using PyTorch."""
        obs = torch.tensor(batch["obs"], dtype=torch.float32)
        gs = torch.tensor(batch["global_state"], dtype=torch.float32)
        actions = torch.tensor(batch["actions"], dtype=torch.long)
        old_lp = torch.tensor(batch["old_log_probs"], dtype=torch.float32)
        adv = torch.tensor(batch["advantages"], dtype=torch.float32)
        ret = torch.tensor(batch["returns"], dtype=torch.float32)
        mask_t = (
            torch.tensor(batch["action_masks"], dtype=torch.float32)
            if batch["action_masks"] is not None
            else None
        )

        # Encode
        encoded = self.encoder(obs)

        # Use actor 0 as shared policy for the mini-batch (parameter sharing)
        new_lp, entropy = self.actors[0].evaluate_actions(encoded, actions, mask_t)

        ratio = torch.exp(new_lp - old_lp)
        clipped = torch.clamp(ratio, 1.0 - self.cfg.clip_eps, 1.0 + self.cfg.clip_eps)
        policy_loss = -torch.min(ratio * adv, clipped * adv).mean()

        values = self.critic(gs)
        value_loss = 0.5 * ((values - ret) ** 2).mean()

        entropy_loss = -entropy.mean()

        loss = policy_loss + self.cfg.value_coef * value_loss + self.cfg.entropy_coef * entropy_loss

        self.actor_optim.zero_grad()
        self.critic_optim.zero_grad()
        loss.backward()
        # Gradient clipping
        all_params = list(self.encoder.parameters()) + list(self.actors[0].parameters())
        nn.utils.clip_grad_norm_(all_params, self.cfg.max_grad_norm)
        nn.utils.clip_grad_norm_(self.critic.parameters(), self.cfg.max_grad_norm)
        self.actor_optim.step()
        self.critic_optim.step()

        return float(policy_loss.item()), float(value_loss.item()), float(entropy.mean().item())

    def _numpy_update(self, batch: Dict[str, Any]) -> Tuple[float, float, float]:
        """Approximate PPO update with NumPy (no gradient, uses finite-diff noise)."""
        obs = batch["obs"]
        actions = batch["actions"]
        old_lp = batch["old_log_probs"]
        adv = batch["advantages"]

        encoded = self.encoder(obs)
        actor = self.actors[0]
        new_lp, entropy = actor.evaluate_actions(encoded, actions, batch["action_masks"])

        ratio = np.exp(new_lp - old_lp)
        clipped = np.clip(ratio, 1.0 - self.cfg.clip_eps, 1.0 + self.cfg.clip_eps)
        policy_loss = -np.minimum(ratio * adv, clipped * adv).mean()

        gs = batch["global_state"]
        values = self.critic(gs)
        ret = batch["returns"]
        value_loss = 0.5 * np.mean((values - ret) ** 2)

        entropy_mean = float(entropy.mean())

        # Evolutionary perturbation of weights (lightweight alternative to back-prop)
        lr = self.cfg.lr_actor
        for param in actor.parameters():
            noise = np.random.randn(*param.shape).astype(np.float32) * 0.01
            param -= lr * (policy_loss * noise)
        for param in self.critic.parameters():
            noise = np.random.randn(*param.shape).astype(np.float32) * 0.01
            param -= lr * (value_loss * noise)

        return float(policy_loss), float(value_loss), entropy_mean

    # ----- SC2 integration helpers -----

    @staticmethod
    def encode_sc2_unit_obs(unit_data: Dict[str, Any], obs_dim: int = 64) -> np.ndarray:
        """Convert a single SC2 unit's raw data to a fixed-size observation.

        Expected keys in *unit_data*: health, shield, energy, x, y,
        weapon_cooldown, is_selected, unit_type_id.
        """
        vec = np.zeros(obs_dim, dtype=np.float32)
        vec[0] = unit_data.get("health", 0.0) / 200.0
        vec[1] = unit_data.get("shield", 0.0) / 200.0
        vec[2] = unit_data.get("energy", 0.0) / 200.0
        vec[3] = unit_data.get("x", 0.0) / 200.0
        vec[4] = unit_data.get("y", 0.0) / 200.0
        vec[5] = unit_data.get("weapon_cooldown", 0.0) / 50.0
        vec[6] = float(unit_data.get("is_selected", False))
        vec[7] = (unit_data.get("unit_type_id", 0) % 256) / 255.0
        return vec

    @staticmethod
    def encode_sc2_global_state(game_data: Dict[str, Any], state_dim: int = 256) -> np.ndarray:
        """Encode global game state: minerals, gas, supply, time, etc."""
        vec = np.zeros(state_dim, dtype=np.float32)
        vec[0] = game_data.get("minerals", 0) / 10000.0
        vec[1] = game_data.get("vespene", 0) / 10000.0
        vec[2] = game_data.get("supply_used", 0) / 200.0
        vec[3] = game_data.get("supply_cap", 0) / 200.0
        vec[4] = game_data.get("game_loop", 0) / 30000.0
        vec[5] = game_data.get("army_count", 0) / 100.0
        vec[6] = game_data.get("worker_count", 0) / 80.0
        vec[7] = game_data.get("enemy_army_estimate", 0) / 100.0
        return vec

    # ----- serialization -----

    def save(self, path: str) -> None:
        """Persist model weights and config to disk."""
        state = {"config": self.cfg.__dict__, "train_step": self.train_step}
        if self.use_torch:
            state["encoder"] = self.encoder.state_dict()
            state["critic"] = self.critic.state_dict()
            state["actors"] = [a.state_dict() for a in self.actors]
            torch.save(state, path)
        else:
            state["encoder_fc1_W"] = self.encoder.fc1.W
            state["encoder_fc1_b"] = self.encoder.fc1.b
            np.savez(path, **state)
        print(f"[MAPPO] Model saved to {path}")

    def load(self, path: str) -> None:
        """Load model weights from disk."""
        if self.use_torch:
            state = torch.load(path, map_location="cpu")
            self.encoder.load_state_dict(state["encoder"])
            self.critic.load_state_dict(state["critic"])
            for i, sd in enumerate(state["actors"]):
                self.actors[i].load_state_dict(sd)
        else:
            data = np.load(path, allow_pickle=True)
            self.encoder.fc1.W = data["encoder_fc1_W"]
            self.encoder.fc1.b = data["encoder_fc1_b"]
        print(f"[MAPPO] Model loaded from {path}")


# ===================================================================
# Synthetic SC2 Environment for Testing
# ===================================================================


class SyntheticSC2MultiAgentEnv:
    """Lightweight environment that mimics multi-agent SC2 interactions."""

    def __init__(self, n_agents: int = 12, obs_dim: int = 64, global_dim: int = 256,
                 action_dim: int = 16):
        self.n_agents = n_agents
        self.obs_dim = obs_dim
        self.global_dim = global_dim
        self.action_dim = action_dim
        self.step_count = 0
        self.max_steps = 200

    def reset(self) -> Tuple[List[np.ndarray], np.ndarray]:
        self.step_count = 0
        obs = [np.random.randn(self.obs_dim).astype(np.float32) * 0.1 for _ in range(self.n_agents)]
        gs = np.random.randn(self.global_dim).astype(np.float32) * 0.1
        return obs, gs

    def step(self, actions: List[int]) -> Tuple[List[np.ndarray], np.ndarray, List[float], bool]:
        self.step_count += 1
        obs = [np.random.randn(self.obs_dim).astype(np.float32) * 0.1 for _ in range(self.n_agents)]
        gs = np.random.randn(self.global_dim).astype(np.float32) * 0.1

        # Shaped reward: cooperative bonus when agents pick similar actions
        action_arr = np.array(actions)
        mode = int(np.bincount(action_arr).argmax())
        agreement_ratio = np.mean(action_arr == mode)
        base_reward = agreement_ratio * 2.0 - 1.0
        rewards = [base_reward + np.random.randn() * 0.1 for _ in range(self.n_agents)]

        done = self.step_count >= self.max_steps
        return obs, gs, rewards, done

    def get_action_masks(self) -> List[np.ndarray]:
        masks = []
        for _ in range(self.n_agents):
            mask = np.ones(self.action_dim, dtype=np.float32)
            # Randomly disable ~25 % of actions
            disable = np.random.rand(self.action_dim) < 0.25
            mask[disable] = 0.0
            if mask.sum() == 0:
                mask[0] = 1.0
            masks.append(mask)
        return masks


# ===================================================================
# CLI Demo
# ===================================================================


def run_demo(args: argparse.Namespace) -> None:
    """Run a MAPPO training demo with synthetic SC2 data."""
    cfg = MAPPOConfig(
        n_agents=args.n_agents,
        obs_dim=args.obs_dim,
        global_state_dim=args.global_dim,
        action_dim=args.action_dim,
        n_steps=args.n_steps,
        n_epochs=args.n_epochs,
        seed=args.seed,
        device="numpy" if args.numpy else "cpu",
    )
    np.random.seed(cfg.seed)
    random.seed(cfg.seed)

    print("=" * 60)
    print(" Phase 606: MAPPO Multi-Agent PPO for SC2")
    print(f" Backend : {'NumPy (fallback)' if not HAS_TORCH or args.numpy else 'PyTorch'}")
    print(f" Agents  : {cfg.n_agents}  |  ObsDim: {cfg.obs_dim}  |  Actions: {cfg.action_dim}")
    print("=" * 60)

    agent = SC2MAPPOAgent(cfg)
    env = SyntheticSC2MultiAgentEnv(cfg.n_agents, cfg.obs_dim, cfg.global_state_dim, cfg.action_dim)

    # Initialize self-play league
    for i in range(cfg.league_size):
        agent.league.register(f"agent_{i}", snapshot=None)
    pbt_pop = agent.pbt.init_population(cfg)

    n_episodes = args.episodes
    for ep in range(1, n_episodes + 1):
        obs, gs = env.reset()
        ep_reward = 0.0
        done = False
        step = 0

        while not done:
            masks = env.get_action_masks()
            actions = agent.collect_step(obs, gs, [0.0] * cfg.n_agents if step == 0 else rewards, done, masks)
            obs, gs, rewards, done = env.step(actions)
            ep_reward += np.mean(rewards)
            step += 1

            if agent.buffer.is_full():
                stats = agent.train()
                if ep % max(1, n_episodes // 5) == 0:
                    print(
                        f"  [Train] step={stats['train_step']:<4d}  "
                        f"pol_loss={stats['policy_loss']:.4f}  "
                        f"val_loss={stats['value_loss']:.4f}  "
                        f"entropy={stats['entropy']:.4f}"
                    )

        # Update league ELO (simulated match)
        if len(agent.league.ratings) >= 2:
            ids = list(agent.league.ratings.keys())
            w, l = random.sample(ids, 2)
            agent.league.update(w, l)

        # PBT fitness update
        agent.pbt.update_fitness(ep % cfg.league_size, ep_reward)

        if ep % max(1, n_episodes // 5) == 0:
            top = agent.league.top_agents(3)
            elo_str = "  ".join(f"{a}={r:.0f}" for a, r in top)
            print(f"Episode {ep:>4d}/{n_episodes}  reward={ep_reward:.3f}  ELO: {elo_str}")

    # PBT exploit-and-explore at end
    agent.pbt.exploit_and_explore()
    print("\n[PBT] Hyperparameter mutation complete for league population.")

    print("\n" + "=" * 60)
    print(" MAPPO Demo Complete")
    print(f" Final league standings:")
    for name, elo in agent.league.top_agents(cfg.league_size):
        print(f"   {name:<12s}  ELO {elo:.0f}")
    print("=" * 60)


def main():
    parser = argparse.ArgumentParser(description="Phase 606: MAPPO SC2 Agent")
    parser.add_argument("--n-agents", type=int, default=8, help="Number of agents (units)")
    parser.add_argument("--obs-dim", type=int, default=64, help="Per-agent observation dim")
    parser.add_argument("--global-dim", type=int, default=256, help="Global state dim")
    parser.add_argument("--action-dim", type=int, default=16, help="Action space size")
    parser.add_argument("--n-steps", type=int, default=128, help="Rollout steps before update")
    parser.add_argument("--n-epochs", type=int, default=3, help="PPO epochs per update")
    parser.add_argument("--episodes", type=int, default=20, help="Training episodes")
    parser.add_argument("--seed", type=int, default=42, help="Random seed")
    parser.add_argument("--numpy", action="store_true", help="Force NumPy-only backend")
    args = parser.parse_args()
    run_demo(args)


if __name__ == "__main__":
    main()
