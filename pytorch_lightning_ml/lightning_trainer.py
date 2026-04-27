"""
Phase 538: PyTorch Lightning
SC2 Bot ML training with Lightning modules, callbacks, and logging
"""

from __future__ import annotations
from typing import Any, Optional
import os
import sys
import math
import random

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from gymnasium_env.sc2_gym_env import SC2ZergEnv, OBS_DIM, ACT_DIM

try:
    import pytorch_lightning as pl
    import torch
    import torch.nn as nn
    import torch.optim as optim
    from torch.utils.data import DataLoader, TensorDataset

    PL_AVAILABLE = True
except ImportError:
    PL_AVAILABLE = False


# ─────────────────────────────────────────────
# Lightning Module: SC2 Actor-Critic
# ─────────────────────────────────────────────

if PL_AVAILABLE:

    class SC2ActorCritic(pl.LightningModule):
        def __init__(
            self,
            obs_dim: int = OBS_DIM,
            act_dim: int = ACT_DIM,
            hidden_dim: int = 256,
            lr: float = 3e-4,
            gamma: float = 0.99,
        ):
            super().__init__()
            self.save_hyperparameters()

            self.shared = nn.Sequential(
                nn.Linear(obs_dim, hidden_dim),
                nn.ReLU(),
                nn.Linear(hidden_dim, hidden_dim),
                nn.ReLU(),
            )
            self.actor = nn.Linear(hidden_dim, act_dim)
            self.critic = nn.Linear(hidden_dim, 1)

        def forward(self, obs):
            h = self.shared(obs)
            return self.actor(h), self.critic(h).squeeze(-1)

        def training_step(self, batch, batch_idx):
            obs, actions, returns, advantages = batch
            logits, values = self(obs)

            # Policy loss
            log_probs = torch.log_softmax(logits, dim=-1)
            log_pa = log_probs.gather(1, actions.unsqueeze(1)).squeeze(1)
            policy_loss = -(log_pa * advantages).mean()

            # Value loss
            value_loss = nn.functional.mse_loss(values, returns)

            # Entropy
            probs = torch.softmax(logits, dim=-1)
            entropy = -(probs * log_probs).sum(dim=-1).mean()

            loss = policy_loss + 0.5 * value_loss - 0.01 * entropy
            self.log_dict(
                {
                    "train/loss": loss,
                    "train/policy_loss": policy_loss,
                    "train/value_loss": value_loss,
                    "train/entropy": entropy,
                }
            )
            return loss

        def validation_step(self, batch, batch_idx):
            obs, actions, returns, advantages = batch
            logits, values = self(obs)
            val_loss = nn.functional.mse_loss(values, returns)
            self.log("val/loss", val_loss)
            return val_loss

        def configure_optimizers(self):
            optimizer = optim.Adam(self.parameters(), lr=self.hparams.lr)
            scheduler = optim.lr_scheduler.CosineAnnealingLR(optimizer, T_max=100)
            return {"optimizer": optimizer, "lr_scheduler": scheduler}

    class SC2DataModule(pl.LightningDataModule):
        def __init__(
            self,
            n_episodes: int = 100,
            batch_size: int = 128,
            gamma: float = 0.99,
        ):
            super().__init__()
            self.n_episodes = n_episodes
            self.batch_size = batch_size
            self.gamma = gamma
            self._train_dataset = None
            self._val_dataset = None

        def _collect_episodes(self, n: int) -> TensorDataset:
            obs_list, act_list, ret_list, adv_list = [], [], [], []
            env = SC2ZergEnv(max_frames=500)

            for ep in range(n):
                obs, _ = env.reset(seed=ep)
                done = False
                ep_obs, ep_act, ep_rew = [], [], []
                while not done:
                    action = random.randint(0, ACT_DIM - 1)
                    next_obs, r, term, trunc, _ = env.step(action)
                    ep_obs.append(obs)
                    ep_act.append(action)
                    ep_rew.append(r)
                    done = term or trunc
                    obs = next_obs

                # Compute returns
                returns = []
                R = 0.0
                for r in reversed(ep_rew):
                    R = r + self.gamma * R
                    returns.insert(0, R)

                obs_list.extend(ep_obs)
                act_list.extend(ep_act)
                ret_list.extend(returns)

            obs_t = torch.FloatTensor(obs_list)
            act_t = torch.LongTensor(act_list)
            ret_t = torch.FloatTensor(ret_list)
            adv_t = (ret_t - ret_t.mean()) / (ret_t.std() + 1e-8)

            return TensorDataset(obs_t, act_t, ret_t, adv_t)

        def setup(self, stage: Optional[str] = None):
            n_train = int(self.n_episodes * 0.8)
            n_val = self.n_episodes - n_train
            self._train_dataset = self._collect_episodes(n_train)
            self._val_dataset = self._collect_episodes(n_val)

        def train_dataloader(self):
            return DataLoader(
                self._train_dataset,
                batch_size=self.batch_size,
                shuffle=True,
                num_workers=0,
            )

        def val_dataloader(self):
            return DataLoader(
                self._val_dataset,
                batch_size=self.batch_size,
                num_workers=0,
            )

    class SC2MetricsCallback(pl.Callback):
        def __init__(self):
            self.val_losses: list[float] = []

        def on_validation_epoch_end(self, trainer, pl_module):
            metrics = trainer.callback_metrics
            val_loss = metrics.get("val/loss", None)
            if val_loss is not None:
                self.val_losses.append(float(val_loss))
                print(
                    f"  Epoch {trainer.current_epoch:3d} | "
                    f"Val loss: {float(val_loss):.4f}"
                )


# ─────────────────────────────────────────────
# Python fallback
# ─────────────────────────────────────────────


def _python_train(epochs: int = 20) -> dict:
    """Manual gradient-free training simulation."""
    env = SC2ZergEnv(max_frames=500)
    total_r = 0.0
    episodes = 0

    for ep in range(epochs * 10):
        obs, _ = env.reset(seed=ep)
        done = False
        ep_r = 0.0
        while not done:
            m, g, s, ms = obs[0], obs[1], obs[2], obs[3]
            t = obs[8]
            if t > 0.6:
                a = 6
            elif s > ms * 0.85:
                a = 3
            elif m > 0.3:
                a = 1
            else:
                a = 0
            obs, r, term, trunc, _ = env.step(a)
            ep_r += r
            done = term or trunc
        total_r += ep_r
        episodes += 1

    return {
        "epochs": epochs,
        "episodes": episodes,
        "mean_reward": total_r / max(1, episodes),
    }


# ─────────────────────────────────────────────
# Main
# ─────────────────────────────────────────────


def train():
    print("Phase 538: PyTorch Lightning — SC2 Actor-Critic")
    print(f"Lightning available: {PL_AVAILABLE}")

    if not PL_AVAILABLE:
        result = _python_train(epochs=10)
        print(f"Result: {result}")
        return

    model = SC2ActorCritic()
    datamodule = SC2DataModule(n_episodes=50, batch_size=64)
    callback = SC2MetricsCallback()

    trainer = pl.Trainer(
        max_epochs=20,
        callbacks=[callback],
        enable_progress_bar=True,
        log_every_n_steps=5,
    )
    trainer.fit(model, datamodule=datamodule)
    print(f"\nBest val loss: {min(callback.val_losses):.4f}")


if __name__ == "__main__":
    train()
