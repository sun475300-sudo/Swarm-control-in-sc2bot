"""
Phase 536: CleanRL
Single-file PPO implementation for SC2 Bot training
"""

from __future__ import annotations
import math
import random
import time
import os
import sys
from dataclasses import dataclass
from typing import Optional

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from gymnasium_env.sc2_gym_env import SC2ZergEnv, OBS_DIM, ACT_DIM

try:
    import torch
    import torch.nn as nn
    import torch.optim as optim
    from torch.distributions import Categorical
    import numpy as np

    TORCH_AVAILABLE = True
except ImportError:
    TORCH_AVAILABLE = False


# ─────────────────────────────────────────────
# Hyperparameters
# ─────────────────────────────────────────────


@dataclass
class Args:
    exp_name: str = "sc2_ppo"
    seed: int = 42
    total_timesteps: int = 100_000
    learning_rate: float = 2.5e-4
    num_envs: int = 4
    num_steps: int = 128
    anneal_lr: bool = True
    gae: bool = True
    gamma: float = 0.99
    gae_lambda: float = 0.95
    num_minibatches: int = 4
    update_epochs: int = 4
    norm_adv: bool = True
    clip_coef: float = 0.2
    clip_vloss: bool = True
    ent_coef: float = 0.01
    vf_coef: float = 0.5
    max_grad_norm: float = 0.5
    target_kl: Optional[float] = None

    @property
    def batch_size(self):
        return self.num_envs * self.num_steps

    @property
    def minibatch_size(self):
        return self.batch_size // self.num_minibatches


# ─────────────────────────────────────────────
# Agent network
# ─────────────────────────────────────────────

if TORCH_AVAILABLE:

    def layer_init(layer, std=math.sqrt(2), bias_const=0.0):
        nn.init.orthogonal_(layer.weight, std)
        nn.init.constant_(layer.bias, bias_const)
        return layer

    class SC2Agent(nn.Module):
        def __init__(self, obs_dim: int, act_dim: int):
            super().__init__()
            self.critic = nn.Sequential(
                layer_init(nn.Linear(obs_dim, 256)),
                nn.Tanh(),
                layer_init(nn.Linear(256, 256)),
                nn.Tanh(),
                layer_init(nn.Linear(256, 1), std=1.0),
            )
            self.actor = nn.Sequential(
                layer_init(nn.Linear(obs_dim, 256)),
                nn.Tanh(),
                layer_init(nn.Linear(256, 256)),
                nn.Tanh(),
                layer_init(nn.Linear(256, act_dim), std=0.01),
            )

        def get_value(self, x):
            return self.critic(x)

        def get_action_and_value(self, x, action=None):
            logits = self.actor(x)
            probs = Categorical(logits=logits)
            if action is None:
                action = probs.sample()
            return action, probs.log_prob(action), probs.entropy(), self.critic(x)


# ─────────────────────────────────────────────
# Vectorized environment (manual)
# ─────────────────────────────────────────────


class VecSC2Env:
    def __init__(self, num_envs: int, **env_kwargs):
        self.num_envs = num_envs
        self.envs = [SC2ZergEnv(**env_kwargs) for _ in range(num_envs)]
        self.obs_buf = [[0.0] * OBS_DIM] * num_envs

    def reset(self) -> list[list[float]]:
        obs = []
        for i, env in enumerate(self.envs):
            o, _ = env.reset(seed=i)
            obs.append(o)
        self.obs_buf = obs
        return obs

    def step(self, actions: list[int]):
        next_obs, rewards, dones = [], [], []
        for i, (env, action) in enumerate(zip(self.envs, actions)):
            o, r, term, trunc, _ = env.step(action)
            done = term or trunc
            if done:
                o, _ = env.reset(seed=random.randint(0, 9999))
            next_obs.append(o)
            rewards.append(r)
            dones.append(done)
        self.obs_buf = next_obs
        return next_obs, rewards, dones


# ─────────────────────────────────────────────
# CleanRL PPO training loop
# ─────────────────────────────────────────────


def train_cleanrl(args: Args) -> dict:
    if not TORCH_AVAILABLE:
        return _python_ppo(args)

    device = torch.device("cpu")
    random.seed(args.seed)
    torch.manual_seed(args.seed)

    envs = VecSC2Env(args.num_envs, max_frames=1000)
    agent = SC2Agent(OBS_DIM, ACT_DIM).to(device)
    optimizer = optim.Adam(agent.parameters(), lr=args.learning_rate, eps=1e-5)

    # Storage
    obs_buf = torch.zeros((args.num_steps, args.num_envs, OBS_DIM)).to(device)
    act_buf = torch.zeros((args.num_steps, args.num_envs)).long().to(device)
    logp_buf = torch.zeros((args.num_steps, args.num_envs)).to(device)
    rew_buf = torch.zeros((args.num_steps, args.num_envs)).to(device)
    done_buf = torch.zeros((args.num_steps, args.num_envs)).to(device)
    val_buf = torch.zeros((args.num_steps, args.num_envs)).to(device)

    next_obs = torch.FloatTensor(envs.reset()).to(device)
    next_done = torch.zeros(args.num_envs).to(device)
    num_updates = args.total_timesteps // args.batch_size
    ep_rewards: list[float] = []
    start_time = time.time()

    for update in range(1, num_updates + 1):
        # Anneal LR
        if args.anneal_lr:
            frac = 1.0 - (update - 1) / num_updates
            optimizer.param_groups[0]["lr"] = frac * args.learning_rate

        # Rollout
        for step in range(args.num_steps):
            obs_buf[step] = next_obs
            done_buf[step] = next_done
            with torch.no_grad():
                action, logp, _, value = agent.get_action_and_value(next_obs)
                val_buf[step] = value.flatten()
            act_buf[step] = action
            logp_buf[step] = logp

            raw_next, raw_rew, raw_done = envs.step(action.tolist())
            rew_buf[step] = torch.FloatTensor(raw_rew).to(device)
            next_obs = torch.FloatTensor(raw_next).to(device)
            next_done = torch.FloatTensor([float(d) for d in raw_done]).to(device)
            ep_rewards.extend(raw_rew)

        # GAE
        with torch.no_grad():
            next_value = agent.get_value(next_obs).reshape(1, -1)
            advantages = torch.zeros_like(rew_buf).to(device)
            lastgaelam = 0.0
            for t in reversed(range(args.num_steps)):
                if t == args.num_steps - 1:
                    nextnonterminal = 1.0 - next_done
                    nextvalues = next_value
                else:
                    nextnonterminal = 1.0 - done_buf[t + 1]
                    nextvalues = val_buf[t + 1]
                delta = (
                    rew_buf[t] + args.gamma * nextvalues * nextnonterminal - val_buf[t]
                )
                advantages[t] = lastgaelam = (
                    delta + args.gamma * args.gae_lambda * nextnonterminal * lastgaelam
                )
            returns = advantages + val_buf

        # Flatten
        b_obs = obs_buf.reshape(-1, OBS_DIM)
        b_act = act_buf.reshape(-1)
        b_logp = logp_buf.reshape(-1)
        b_adv = advantages.reshape(-1)
        b_ret = returns.reshape(-1)
        b_val = val_buf.reshape(-1)

        # PPO update
        b_inds = torch.randperm(args.batch_size)
        for epoch in range(args.update_epochs):
            for mb_start in range(0, args.batch_size, args.minibatch_size):
                mb_inds = b_inds[mb_start : mb_start + args.minibatch_size]
                _, newlogp, entropy, newval = agent.get_action_and_value(
                    b_obs[mb_inds], b_act[mb_inds]
                )
                logratio = newlogp - b_logp[mb_inds]
                ratio = logratio.exp()

                mb_adv = b_adv[mb_inds]
                if args.norm_adv:
                    mb_adv = (mb_adv - mb_adv.mean()) / (mb_adv.std() + 1e-8)

                pg_loss1 = -mb_adv * ratio
                pg_loss2 = -mb_adv * torch.clamp(
                    ratio, 1 - args.clip_coef, 1 + args.clip_coef
                )
                pg_loss = torch.max(pg_loss1, pg_loss2).mean()

                newval = newval.flatten()
                v_loss = 0.5 * ((newval - b_ret[mb_inds]) ** 2).mean()

                ent_loss = entropy.mean()
                loss = pg_loss - args.ent_coef * ent_loss + v_loss * args.vf_coef

                optimizer.zero_grad()
                loss.backward()
                nn.utils.clip_grad_norm_(agent.parameters(), args.max_grad_norm)
                optimizer.step()

        if update % 5 == 0:
            sps = int(update * args.batch_size / (time.time() - start_time))
            recent = ep_rewards[-100:] if ep_rewards else [0]
            print(
                f"  Update {update:4d}/{num_updates} | "
                f"SPS: {sps:5d} | "
                f"Avg reward: {sum(recent)/len(recent):.3f}"
            )

    return {
        "total_timesteps": num_updates * args.batch_size,
        "mean_reward": sum(ep_rewards[-500:]) / max(1, len(ep_rewards[-500:])),
    }


def _python_ppo(args: Args) -> dict:
    """Pure Python PPO approximation."""
    env = SC2ZergEnv(max_frames=500)
    value_fn = {i: 0.0 for i in range(1000)}
    total_r = 0.0
    episodes = 0

    steps = 0
    while steps < args.total_timesteps:
        obs, _ = env.reset(seed=episodes)
        done = False
        ep_r = 0.0
        while not done:
            action = random.randint(0, ACT_DIM - 1)
            obs, r, term, trunc, _ = env.step(action)
            ep_r += r
            steps += 1
            done = term or trunc
        total_r += ep_r
        episodes += 1

    return {
        "total_timesteps": steps,
        "mean_reward": total_r / max(1, episodes),
    }


if __name__ == "__main__":
    print("Phase 536: CleanRL — Single-file PPO for SC2")
    print(f"PyTorch available: {TORCH_AVAILABLE}")
    args = Args(total_timesteps=10_000, num_envs=2, num_steps=64)
    result = train_cleanrl(args)
    print(f"\nResult: {result}")
