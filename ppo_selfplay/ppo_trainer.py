"""
Phase 348: PPO Trainer
PyTorch PPO (Proximal Policy Optimization) trainer for SC2 bot self-play.
"""

from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple

import numpy as np
import torch
import torch.nn as nn
import torch.optim as optim
from torch.distributions import Categorical


@dataclass
class PPOConfig:
    lr: float = 3e-4
    gamma: float = 0.99
    gae_lambda: float = 0.95
    clip_eps: float = 0.2
    value_coef: float = 0.5
    entropy_coef: float = 0.01
    max_grad_norm: float = 0.5
    n_steps: int = 2048
    n_epochs: int = 10
    batch_size: int = 64
    obs_dim: int = 512
    action_dim: int = 256


class PPOBuffer:
    """Rollout storage for PPO training."""

    def __init__(self, n_steps: int, obs_dim: int, action_dim: int):
        self.n_steps = n_steps
        self.obs_dim = obs_dim
        self.action_dim = action_dim
        self.reset()

    def reset(self):
        self.observations = []
        self.actions = []
        self.rewards = []
        self.values = []
        self.log_probs = []
        self.dones = []
        self.action_masks = []
        self.ptr = 0

    def add(self, obs, action, reward, value, log_prob, done, action_mask=None):
        self.observations.append(obs)
        self.actions.append(action)
        self.rewards.append(reward)
        self.values.append(value)
        self.log_probs.append(log_prob)
        self.dones.append(done)
        self.action_masks.append(action_mask)
        self.ptr += 1

    def is_full(self) -> bool:
        return self.ptr >= self.n_steps

    def get_tensors(self) -> Dict[str, torch.Tensor]:
        return {
            "obs": torch.stack(self.observations),
            "actions": torch.tensor(self.actions, dtype=torch.long),
            "rewards": torch.tensor(self.rewards, dtype=torch.float32),
            "values": torch.tensor(self.values, dtype=torch.float32),
            "log_probs": torch.tensor(self.log_probs, dtype=torch.float32),
            "dones": torch.tensor(self.dones, dtype=torch.float32),
        }


class ActorCritic(nn.Module):
    """Combined policy and value network for SC2."""

    def __init__(self, obs_dim: int, action_dim: int, hidden_dim: int = 256):
        super().__init__()
        self.shared = nn.Sequential(
            nn.Linear(obs_dim, hidden_dim),
            nn.ReLU(),
            nn.Linear(hidden_dim, hidden_dim),
            nn.ReLU(),
        )
        self.actor_head = nn.Linear(hidden_dim, action_dim)
        self.critic_head = nn.Linear(hidden_dim, 1)

    def forward(
        self, obs: torch.Tensor, action_mask: Optional[torch.Tensor] = None
    ) -> Tuple[torch.Tensor, torch.Tensor]:
        features = self.shared(obs)
        logits = self.actor_head(features)
        if action_mask is not None:
            logits = logits.masked_fill(~action_mask.bool(), float("-inf"))
        value = self.critic_head(features).squeeze(-1)
        return logits, value

    def get_action(
        self, obs: torch.Tensor, action_mask: Optional[torch.Tensor] = None
    ) -> Tuple[torch.Tensor, torch.Tensor, torch.Tensor]:
        logits, value = self.forward(obs, action_mask)
        dist = Categorical(logits=logits)
        action = dist.sample()
        log_prob = dist.log_prob(action)
        return action, log_prob, value


class PPOTrainer:
    """PPO trainer orchestrating SC2 self-play training."""

    def __init__(self, config: PPOConfig):
        self.cfg = config
        self.model = ActorCritic(config.obs_dim, config.action_dim)
        self.optimizer = optim.Adam(self.model.parameters(), lr=config.lr)
        self.buffer = PPOBuffer(config.n_steps, config.obs_dim, config.action_dim)
        self.total_steps = 0

    def collect_rollouts(self, env) -> None:
        """Collect n_steps of experience from the environment."""
        self.buffer.reset()
        obs = env.reset()
        while not self.buffer.is_full():
            obs_tensor = torch.FloatTensor(obs).unsqueeze(0)
            mask = env.get_action_mask() if hasattr(env, "get_action_mask") else None
            with torch.no_grad():
                action, log_prob, value = self.model.get_action(obs_tensor, mask)
            next_obs, reward, done, _ = env.step(action.item())
            self.buffer.add(
                obs_tensor.squeeze(0),
                action.item(),
                reward,
                value.item(),
                log_prob.item(),
                done,
                mask,
            )
            obs = env.reset() if done else next_obs
        self.total_steps += self.cfg.n_steps

    def compute_gae(
        self, rewards, values, dones, last_value: float = 0.0
    ) -> Tuple[torch.Tensor, torch.Tensor]:
        """Generalized Advantage Estimation."""
        n = len(rewards)
        advantages = torch.zeros(n)
        returns = torch.zeros(n)
        gae = 0.0
        next_val = last_value
        for t in reversed(range(n)):
            mask = 1.0 - dones[t].item()
            delta = rewards[t] + self.cfg.gamma * next_val * mask - values[t]
            gae = delta + self.cfg.gamma * self.cfg.gae_lambda * mask * gae
            advantages[t] = gae
            next_val = values[t].item()
        returns = advantages + values
        return advantages, returns

    def update_policy(
        self,
        batch: Dict[str, torch.Tensor],
        advantages: torch.Tensor,
        returns: torch.Tensor,
    ) -> Dict[str, float]:
        """Single PPO update step on a minibatch."""
        logits, values = self.model(batch["obs"])
        dist = Categorical(logits=logits)
        new_log_probs = dist.log_prob(batch["actions"])
        entropy = dist.entropy().mean()

        ratio = torch.exp(new_log_probs - batch["log_probs"])
        adv = (advantages - advantages.mean()) / (advantages.std() + 1e-8)
        surr1 = ratio * adv
        surr2 = torch.clamp(ratio, 1 - self.cfg.clip_eps, 1 + self.cfg.clip_eps) * adv
        policy_loss = -torch.min(surr1, surr2).mean()
        value_loss = nn.functional.mse_loss(values, returns)
        loss = (
            policy_loss
            + self.cfg.value_coef * value_loss
            - self.cfg.entropy_coef * entropy
        )

        self.optimizer.zero_grad()
        loss.backward()
        nn.utils.clip_grad_norm_(self.model.parameters(), self.cfg.max_grad_norm)
        self.optimizer.step()
        return {
            "policy_loss": policy_loss.item(),
            "value_loss": value_loss.item(),
            "entropy": entropy.item(),
        }

    def train_epoch(self) -> Dict[str, float]:
        """Run n_epochs of PPO updates over the buffer."""
        data = self.buffer.get_tensors()
        advantages, returns = self.compute_gae(
            data["rewards"], data["values"], data["dones"]
        )
        metrics: Dict[str, List[float]] = {
            "policy_loss": [],
            "value_loss": [],
            "entropy": [],
        }
        indices = torch.randperm(self.cfg.n_steps)
        for epoch in range(self.cfg.n_epochs):
            for start in range(0, self.cfg.n_steps, self.cfg.batch_size):
                idx = indices[start : start + self.cfg.batch_size]
                batch = {k: v[idx] for k, v in data.items()}
                step_metrics = self.update_policy(batch, advantages[idx], returns[idx])
                for k, v in step_metrics.items():
                    metrics[k].append(v)
        return {k: float(np.mean(v)) for k, v in metrics.items()}
