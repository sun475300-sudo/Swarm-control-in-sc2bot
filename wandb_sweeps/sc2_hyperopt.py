# Phase 416: Weights & Biases Sweeps - SC2 PPO Hyperparameter Optimization
# W&B Sweeps with Bayesian optimization for SC2 PPO training

import wandb
import torch
import torch.nn as nn
import numpy as np
from typing import Optional

# ============================================================
# Sweep Configuration
# ============================================================

sweep_config = {
    "name":   "sc2-ppo-hyperopt",
    "method": "bayes",
    "metric": {
        "name": "mean_reward",
        "goal": "maximize",
    },
    "parameters": {
        "learning_rate": {
            "distribution": "log_uniform_values",
            "min": 1e-5,
            "max": 1e-3,
        },
        "gamma": {
            "distribution": "uniform",
            "min": 0.95,
            "max": 0.999,
        },
        "clip_ratio": {
            "distribution": "uniform",
            "min": 0.1,
            "max": 0.3,
        },
        "entropy_coef": {
            "distribution": "log_uniform_values",
            "min": 1e-4,
            "max": 1e-2,
        },
        "batch_size": {
            "values": [64, 128, 256, 512],
        },
        "hidden_dim": {
            "values": [256, 512, 1024],
        },
        "n_epochs": {
            "values": [4, 8, 16],
        },
        "gae_lambda": {
            "distribution": "uniform",
            "min": 0.9,
            "max": 0.99,
        },
    },
    "early_terminate": {
        "type": "hyperband",
        "min_iter": 3,
    },
}

# ============================================================
# PPO Policy Network
# ============================================================

class SC2PPONet(nn.Module):
    def __init__(self, obs_dim: int = 256, action_dim: int = 64, hidden_dim: int = 512):
        super().__init__()
        self.shared = nn.Sequential(
            nn.Linear(obs_dim, hidden_dim), nn.Tanh(),
            nn.Linear(hidden_dim, hidden_dim), nn.Tanh(),
        )
        self.actor  = nn.Linear(hidden_dim, action_dim)
        self.critic = nn.Linear(hidden_dim, 1)

    def forward(self, obs):
        h      = self.shared(obs)
        logits = self.actor(h)
        value  = self.critic(h)
        return logits, value

# ============================================================
# Training Function (called by wandb.agent)
# ============================================================

def train_ppo(config: Optional[wandb.config] = None):
    with wandb.init(config=config):
        cfg = wandb.config

        model     = SC2PPONet(hidden_dim=cfg.hidden_dim)
        optimizer = torch.optim.Adam(model.parameters(), lr=cfg.learning_rate)

        best_reward = -float("inf")
        rng         = np.random.default_rng(42)

        for epoch in range(20):
            # Simulate PPO training step
            obs     = torch.randn(cfg.batch_size, 256)
            actions = torch.randint(0, 64, (cfg.batch_size,))
            rewards = torch.tensor(rng.normal(0, 1, cfg.batch_size), dtype=torch.float32)
            returns = rewards * cfg.gamma

            logits, values = model(obs)
            log_probs      = torch.log_softmax(logits, dim=-1)
            selected_lp    = log_probs[range(cfg.batch_size), actions]

            # PPO surrogate loss
            ratio       = torch.exp(selected_lp - selected_lp.detach())
            advantage   = (returns - values.squeeze()).detach()
            advantage   = (advantage - advantage.mean()) / (advantage.std() + 1e-8)

            pg_loss1    = -advantage * ratio
            pg_loss2    = -advantage * torch.clamp(ratio, 1 - cfg.clip_ratio, 1 + cfg.clip_ratio)
            actor_loss  = torch.max(pg_loss1, pg_loss2).mean()

            critic_loss = nn.functional.mse_loss(values.squeeze(), returns)
            entropy     = -(log_probs.softmax(-1) * log_probs).sum(-1).mean()
            loss        = actor_loss + 0.5 * critic_loss - cfg.entropy_coef * entropy

            optimizer.zero_grad()
            loss.backward()
            nn.utils.clip_grad_norm_(model.parameters(), 0.5)
            optimizer.step()

            mean_reward = rewards.mean().item() + epoch * 0.05
            win_rate    = float(rng.binomial(1, min(0.5 + epoch * 0.02, 0.75)))
            best_reward = max(best_reward, mean_reward)

            wandb.log({
                "epoch":       epoch,
                "loss":        loss.item(),
                "actor_loss":  actor_loss.item(),
                "critic_loss": critic_loss.item(),
                "entropy":     entropy.item(),
                "mean_reward": mean_reward,
                "best_reward": best_reward,
                "win_rate":    win_rate,
            })

        wandb.summary["best_reward"] = best_reward
        print(f"[W&B Sweep] Run complete. Best reward: {best_reward:.3f}")

# ============================================================
# Main: Create and run sweep
# ============================================================

def main():
    print("[W&B] SC2 PPO hyperparameter sweep starting...")

    # Initialize W&B
    wandb.login()

    # Create sweep
    sweep_id = wandb.sweep(
        sweep=sweep_config,
        project="sc2-bot-ppo",
        entity=None,  # set to your W&B username/org
    )
    print(f"[W&B] Sweep ID: {sweep_id}")

    # Run agent (count=20 runs total)
    wandb.agent(sweep_id, function=train_ppo, count=20)

    print(f"[W&B] Sweep complete. View at: https://wandb.ai/sc2-bot-ppo/sweeps/{sweep_id}")

if __name__ == "__main__":
    main()
