"""
Phase 534: Tianshou RL Framework
SC2 Bot RL with Tianshou's modular Policy/Collector/Trainer
"""

from __future__ import annotations
from typing import Any, Optional
import math
import random
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

try:
    import tianshou as ts
    from tianshou.data import Collector, VectorReplayBuffer, Batch
    from tianshou.env import DummyVectorEnv
    from tianshou.policy import PPOPolicy, A2CPolicy, SACPolicy
    from tianshou.trainer import onpolicy_trainer, offpolicy_trainer
    from tianshou.utils import TensorboardLogger
    import torch
    import torch.nn as nn

    TIANSHOU_AVAILABLE = True
except ImportError:
    TIANSHOU_AVAILABLE = False

from gymnasium_env.sc2_gym_env import SC2ZergEnv, OBS_DIM, ACT_DIM


# ─────────────────────────────────────────────
# Neural network (Tianshou-compatible)
# ─────────────────────────────────────────────

if TIANSHOU_AVAILABLE:

    class SC2ActorNet(nn.Module):
        def __init__(self, obs_dim: int, act_dim: int, hidden: int = 256):
            super().__init__()
            self.net = nn.Sequential(
                nn.Linear(obs_dim, hidden),
                nn.ReLU(),
                nn.Linear(hidden, hidden),
                nn.ReLU(),
                nn.Linear(hidden, act_dim),
            )
            self.output_dim = act_dim

        def forward(self, obs, state=None):
            if isinstance(obs, dict):
                obs = obs.get("obs", obs)
            import torch

            if not isinstance(obs, torch.Tensor):
                obs = torch.FloatTensor(obs)
            return self.net(obs), state

    class SC2CriticNet(nn.Module):
        def __init__(self, obs_dim: int, hidden: int = 256):
            super().__init__()
            self.net = nn.Sequential(
                nn.Linear(obs_dim, hidden),
                nn.ReLU(),
                nn.Linear(hidden, hidden),
                nn.ReLU(),
                nn.Linear(hidden, 1),
            )

        def forward(self, obs, state=None):
            import torch

            if not isinstance(obs, torch.Tensor):
                obs = torch.FloatTensor(obs)
            return self.net(obs)


# ─────────────────────────────────────────────
# Tianshou PPO training setup
# ─────────────────────────────────────────────


def build_ppo_agent():
    if not TIANSHOU_AVAILABLE:
        return None
    import torch
    import torch.optim as optim
    from torch.distributions import Categorical

    actor = SC2ActorNet(OBS_DIM, ACT_DIM)
    critic = SC2CriticNet(OBS_DIM)
    optim_ = optim.Adam(list(actor.parameters()) + list(critic.parameters()), lr=3e-4)

    def dist_fn(logits):
        return Categorical(logits=logits)

    policy = PPOPolicy(
        actor=actor,
        critic=critic,
        optim=optim_,
        dist_fn=dist_fn,
        discount_factor=0.99,
        gae_lambda=0.95,
        eps_clip=0.2,
        value_clip=True,
        dual_clip=None,
        advantage_normalization=True,
        recompute_advantage=False,
        vf_coef=0.5,
        ent_coef=0.01,
        max_grad_norm=0.5,
    )
    return policy


def train_with_tianshou(total_steps: int = 100_000):
    if not TIANSHOU_AVAILABLE:
        print("[Tianshou] Not available — using simulation")
        return _simulate_tianshou_training(total_steps)

    train_envs = DummyVectorEnv([lambda: SC2ZergEnv(max_frames=2000) for _ in range(4)])
    test_envs = DummyVectorEnv([lambda: SC2ZergEnv(max_frames=2000) for _ in range(2)])

    policy = build_ppo_agent()
    train_collector = Collector(
        policy, train_envs, VectorReplayBuffer(20000, len(train_envs))
    )
    test_collector = Collector(policy, test_envs)

    result = onpolicy_trainer(
        policy=policy,
        train_collector=train_collector,
        test_collector=test_collector,
        max_epoch=10,
        step_per_epoch=total_steps // 10,
        repeat_per_collect=10,
        episode_per_test=5,
        batch_size=256,
        step_per_collect=2000,
    )
    return result


# ─────────────────────────────────────────────
# Pure-Python simulation fallback
# ─────────────────────────────────────────────


class SimpleReplayBuffer:
    def __init__(self, capacity: int):
        self.capacity = capacity
        self.buffer: list[dict] = []
        self.pos = 0

    def push(self, transition: dict) -> None:
        if len(self.buffer) < self.capacity:
            self.buffer.append(transition)
        else:
            self.buffer[self.pos] = transition
        self.pos = (self.pos + 1) % self.capacity

    def sample(self, batch_size: int) -> list[dict]:
        return random.sample(self.buffer, min(batch_size, len(self.buffer)))

    def __len__(self) -> int:
        return len(self.buffer)


class SimpleValueNetwork:
    """Tabular-like value estimates for SC2 states."""

    def __init__(self, n_actions: int = ACT_DIM):
        self.n_actions = n_actions
        self.q_table: dict[tuple, list[float]] = {}
        self.lr = 0.01
        self.gamma = 0.99

    def _key(self, obs: list[float]) -> tuple:
        # Discretize observation into bins
        return tuple(int(v * 4) for v in obs[:6])

    def get_q(self, obs: list[float]) -> list[float]:
        k = self._key(obs)
        if k not in self.q_table:
            self.q_table[k] = [0.0] * self.n_actions
        return self.q_table[k]

    def update(
        self, obs: list[float], action: int, reward: float, next_obs: list[float]
    ) -> None:
        q = self.get_q(obs)
        next_q = self.get_q(next_obs)
        td_target = reward + self.gamma * max(next_q)
        q[action] += self.lr * (td_target - q[action])

    def select_action(self, obs: list[float], epsilon: float = 0.1) -> int:
        if random.random() < epsilon:
            return random.randint(0, self.n_actions - 1)
        return self.get_q(obs).index(max(self.get_q(obs)))


def _simulate_tianshou_training(total_steps: int) -> dict:
    """Q-learning simulation mimicking Tianshou's trainer loop."""
    env = SC2ZergEnv(max_frames=1000)
    agent = SimpleValueNetwork()
    buffer = SimpleReplayBuffer(capacity=10000)

    steps = 0
    episodes = 0
    total_reward = 0.0
    epsilon = 1.0

    while steps < total_steps:
        obs, _ = env.reset(seed=episodes)
        ep_r = 0.0
        done = False
        epsilon = max(0.05, epsilon * 0.999)

        while not done and steps < total_steps:
            action = agent.select_action(obs, epsilon)
            next_obs, reward, terminated, truncated, _ = env.step(action)
            done = terminated or truncated
            buffer.push(
                {"obs": obs, "action": action, "reward": reward, "next_obs": next_obs}
            )
            ep_r += reward
            steps += 1
            obs = next_obs

            # Learn from buffer
            if len(buffer) >= 32:
                batch = buffer.sample(32)
                for t in batch:
                    agent.update(t["obs"], t["action"], t["reward"], t["next_obs"])

        total_reward += ep_r
        episodes += 1
        if episodes % 20 == 0:
            avg = total_reward / episodes
            print(
                f"  Ep {episodes:4d} | Steps: {steps:5d} | "
                f"ε: {epsilon:.3f} | Avg reward: {avg:.2f}"
            )

    return {
        "total_steps": steps,
        "episodes": episodes,
        "mean_reward": total_reward / max(1, episodes),
    }


# ─────────────────────────────────────────────
# Main
# ─────────────────────────────────────────────

if __name__ == "__main__":
    print("Phase 534: Tianshou RL — SC2 Bot Training")
    print(f"Tianshou available: {TIANSHOU_AVAILABLE}")

    result = _simulate_tianshou_training(total_steps=3000)
    print(f"\nResult: {result}")
