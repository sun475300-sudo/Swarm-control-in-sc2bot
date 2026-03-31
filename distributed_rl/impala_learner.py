"""
Phase 356: IMPALA Learner
IMPALA (Importance Weighted Actor-Learner Architecture) for distributed SC2 training.
Central learner with V-trace off-policy correction and async actor workers.
"""

import torch
import torch.nn as nn
import torch.nn.functional as F
from torch.distributions import Categorical
import numpy as np
from dataclasses import dataclass, field
from typing import List, Dict, Optional, Tuple
import queue
import threading


@dataclass
class ImpalaConfig:
    obs_dim: int = 512
    action_dim: int = 256
    hidden_dim: int = 256
    lr: float = 5e-4
    gamma: float = 0.99
    rho_bar: float = 1.0      # V-trace importance ratio clip
    c_bar: float = 1.0        # V-trace trace coefficient clip
    entropy_coef: float = 0.01
    value_coef: float = 0.5
    max_grad_norm: float = 40.0
    n_actors: int = 32
    rollout_len: int = 20
    batch_size: int = 32


@dataclass
class ActorBatch:
    """A single rollout from an actor worker."""
    obs: torch.Tensor              # (T, obs_dim)
    actions: torch.Tensor          # (T,)
    behavior_log_probs: torch.Tensor  # (T,)
    rewards: torch.Tensor          # (T,)
    dones: torch.Tensor            # (T,)


def vtrace_returns(
    behavior_log_probs: torch.Tensor,
    target_log_probs: torch.Tensor,
    rewards: torch.Tensor,
    values: torch.Tensor,
    bootstrap_value: torch.Tensor,
    dones: torch.Tensor,
    gamma: float,
    rho_bar: float,
    c_bar: float,
) -> Tuple[torch.Tensor, torch.Tensor]:
    """Compute V-trace targets and advantages (off-policy correction)."""
    T = rewards.shape[0]
    log_rho = target_log_probs - behavior_log_probs
    rho = torch.exp(log_rho).clamp(max=rho_bar)
    c = torch.exp(log_rho).clamp(max=c_bar)

    deltas = rho * (rewards + gamma * (1 - dones) * torch.cat([values[1:], bootstrap_value.unsqueeze(0)]) - values[:T])
    vs = torch.zeros(T)
    vs_t = bootstrap_value.item()
    for t in reversed(range(T)):
        vs_t = values[t].item() + deltas[t].item() + gamma * (1 - dones[t].item()) * c[t].item() * (vs_t - values[t].item())
        vs[t] = vs_t

    advantages = rho * (rewards + gamma * (1 - dones) * torch.cat([vs[1:], bootstrap_value.unsqueeze(0)]) - values[:T])
    return vs, advantages


class ImpalaNet(nn.Module):
    """Shared network for IMPALA actors and learner."""

    def __init__(self, obs_dim: int, action_dim: int, hidden_dim: int = 256):
        super().__init__()
        self.backbone = nn.Sequential(
            nn.Linear(obs_dim, hidden_dim), nn.ReLU(),
            nn.Linear(hidden_dim, hidden_dim), nn.ReLU(),
        )
        self.policy_head = nn.Linear(hidden_dim, action_dim)
        self.value_head = nn.Linear(hidden_dim, 1)

    def forward(self, obs: torch.Tensor) -> Tuple[torch.Tensor, torch.Tensor]:
        h = self.backbone(obs)
        return self.policy_head(h), self.value_head(h).squeeze(-1)

    def get_log_prob_and_value(self, obs: torch.Tensor, actions: torch.Tensor):
        logits, values = self.forward(obs)
        dist = Categorical(logits=logits)
        return dist.log_prob(actions), values, dist.entropy()


class ImpalaLearner:
    """Central IMPALA learner processing batches from actor queue."""

    def __init__(self, cfg: ImpalaConfig):
        self.cfg = cfg
        self.net = ImpalaNet(cfg.obs_dim, cfg.action_dim, cfg.hidden_dim)
        self.optimizer = torch.optim.Adam(self.net.parameters(), lr=cfg.lr)
        self.queue: queue.Queue = queue.Queue(maxsize=cfg.n_actors * 2)
        self.update_count = 0
        self._lock = threading.Lock()

    def get_weights(self) -> Dict[str, torch.Tensor]:
        with self._lock:
            return {k: v.clone() for k, v in self.net.state_dict().items()}

    def learn_from_batch(self, batch: ActorBatch) -> Dict[str, float]:
        T = batch.obs.shape[0]
        target_log_probs, values, entropy = self.net.get_log_prob_and_value(
            batch.obs, batch.actions)
        bootstrap_val = torch.zeros(1)
        with torch.no_grad():
            _, bv = self.net(batch.obs[-1:])
            bootstrap_val = bv.squeeze()

        vs, advantages = vtrace_returns(
            batch.behavior_log_probs, target_log_probs, batch.rewards,
            values.detach(), bootstrap_val, batch.dones,
            self.cfg.gamma, self.cfg.rho_bar, self.cfg.c_bar)

        policy_loss = -(advantages.detach() * target_log_probs).mean()
        value_loss = F.mse_loss(values, vs.detach())
        loss = policy_loss + self.cfg.value_coef * value_loss - self.cfg.entropy_coef * entropy.mean()

        self.optimizer.zero_grad()
        loss.backward()
        nn.utils.clip_grad_norm_(self.net.parameters(), self.cfg.max_grad_norm)
        with self._lock:
            self.optimizer.step()
        self.update_count += 1
        return {"policy_loss": policy_loss.item(), "value_loss": value_loss.item(),
                "entropy": entropy.mean().item()}

    def run(self) -> None:
        """Main learner loop consuming actor batches from queue."""
        print(f"[ImpalaLearner] Starting with {self.cfg.n_actors} actors")
        while True:
            batch = self.queue.get()
            if batch is None:
                break
            self.learn_from_batch(batch)


class ImpalaActor:
    """Distributed actor collecting rollouts and pushing to learner queue."""

    def __init__(self, actor_id: int, cfg: ImpalaConfig,
                 learner_queue: queue.Queue):
        self.actor_id = actor_id
        self.cfg = cfg
        self.queue = learner_queue
        self.net = ImpalaNet(cfg.obs_dim, cfg.action_dim, cfg.hidden_dim)
        self.net.eval()

    def sync_weights(self, weights: Dict[str, torch.Tensor]) -> None:
        self.net.load_state_dict(weights)

    def collect_rollout(self, env) -> ActorBatch:
        obs_list, action_list, log_prob_list, reward_list, done_list = [], [], [], [], []
        obs = env.reset()
        for _ in range(self.cfg.rollout_len):
            obs_t = torch.FloatTensor(obs).unsqueeze(0)
            with torch.no_grad():
                logits, _ = self.net(obs_t)
            dist = Categorical(logits=logits)
            action = dist.sample()
            log_prob = dist.log_prob(action)
            next_obs, reward, done, _ = env.step(action.item())
            obs_list.append(obs_t.squeeze(0))
            action_list.append(action.item())
            log_prob_list.append(log_prob.item())
            reward_list.append(reward)
            done_list.append(float(done))
            obs = env.reset() if done else next_obs
        return ActorBatch(
            obs=torch.stack(obs_list),
            actions=torch.tensor(action_list, dtype=torch.long),
            behavior_log_probs=torch.tensor(log_prob_list),
            rewards=torch.tensor(reward_list),
            dones=torch.tensor(done_list),
        )

    def run(self, env, learner: ImpalaLearner, max_steps: int = 1_000_000) -> None:
        steps = 0
        while steps < max_steps:
            self.sync_weights(learner.get_weights())
            batch = self.collect_rollout(env)
            learner.queue.put(batch)
            steps += self.cfg.rollout_len
