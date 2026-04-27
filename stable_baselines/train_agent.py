"""
Phase 533: Stable Baselines 3
SC2 Bot RL training with PPO/SAC/A2C via SB3
"""

from __future__ import annotations
from typing import Optional
import math
import random
import os
import sys

# Add parent dir so sc2_gym_env is importable
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


try:
    from stable_baselines3 import PPO, SAC, A2C
    from stable_baselines3.common.env_util import make_vec_env
    from stable_baselines3.common.evaluation import evaluate_policy
    from stable_baselines3.common.callbacks import (
        EvalCallback,
        CheckpointCallback,
        BaseCallback,
    )
    from stable_baselines3.common.monitor import Monitor
    from stable_baselines3.common.vec_env import SubprocVecEnv

    SB3_AVAILABLE = True
except ImportError:
    SB3_AVAILABLE = False

from gymnasium_env.sc2_gym_env import SC2ZergEnv

# ─────────────────────────────────────────────
# Custom callbacks
# ─────────────────────────────────────────────

if SB3_AVAILABLE:

    class SC2MetricsCallback(BaseCallback):
        """Log SC2-specific metrics during training."""

        def __init__(self, verbose: int = 0):
            super().__init__(verbose)
            self.episode_rewards: list[float] = []
            self.episode_lengths: list[int] = []

        def _on_step(self) -> bool:
            if "episode" in self.locals.get("infos", [{}])[0]:
                ep_info = self.locals["infos"][0]["episode"]
                self.episode_rewards.append(ep_info["r"])
                self.episode_lengths.append(ep_info["l"])
                if self.verbose > 0:
                    print(f"  Episode reward: {ep_info['r']:.2f}")
            return True

        def _on_training_end(self) -> None:
            if self.episode_rewards:
                avg = sum(self.episode_rewards) / len(self.episode_rewards)
                print(
                    f"Training end | Avg reward: {avg:.2f} "
                    f"over {len(self.episode_rewards)} episodes"
                )


# ─────────────────────────────────────────────
# Training configuration
# ─────────────────────────────────────────────

PPO_CONFIG = {
    "policy": "MlpPolicy",
    "learning_rate": 3e-4,
    "n_steps": 2048,
    "batch_size": 64,
    "n_epochs": 10,
    "gamma": 0.99,
    "gae_lambda": 0.95,
    "clip_range": 0.2,
    "ent_coef": 0.01,
    "vf_coef": 0.5,
    "max_grad_norm": 0.5,
    "verbose": 1,
}

A2C_CONFIG = {
    "policy": "MlpPolicy",
    "learning_rate": 7e-4,
    "n_steps": 5,
    "gamma": 0.99,
    "gae_lambda": 1.0,
    "ent_coef": 0.01,
    "vf_coef": 0.25,
    "verbose": 1,
}


# ─────────────────────────────────────────────
# Training runner
# ─────────────────────────────────────────────


def make_env(seed: int = 0):
    def _init():
        env = SC2ZergEnv(max_frames=2000, enemy_aggression=0.5)
        if SB3_AVAILABLE:
            env = Monitor(env)
        env.reset(seed=seed)
        return env

    return _init


def train_ppo(total_timesteps: int = 100_000, save_path: str = "./models"):
    if not SB3_AVAILABLE:
        print("[SB3] Not available — running simulation instead")
        return simulate_training(total_timesteps)

    os.makedirs(save_path, exist_ok=True)
    vec_env = make_vec_env(make_env(), n_envs=4)

    model = PPO(env=vec_env, **PPO_CONFIG)

    callbacks = [
        CheckpointCallback(
            save_freq=10_000,
            save_path=save_path,
            name_prefix="sc2_ppo",
        ),
        SC2MetricsCallback(verbose=1),
    ]

    model.learn(
        total_timesteps=total_timesteps,
        callback=callbacks,
        progress_bar=True,
    )
    model.save(f"{save_path}/sc2_ppo_final")
    print(f"Model saved to {save_path}/sc2_ppo_final")
    return model


def train_a2c(total_timesteps: int = 50_000, save_path: str = "./models"):
    if not SB3_AVAILABLE:
        return simulate_training(total_timesteps)

    env = make_env(seed=0)()
    model = A2C(env=env, **A2C_CONFIG)
    model.learn(total_timesteps=total_timesteps, progress_bar=True)
    model.save(f"{save_path}/sc2_a2c_final")
    return model


# ─────────────────────────────────────────────
# Python-native simulation fallback
# ─────────────────────────────────────────────


def simulate_training(total_timesteps: int) -> dict:
    """Simulate SB3-style training without the dependency."""
    env = SC2ZergEnv(max_frames=2000)
    steps_done = 0
    episodes = 0
    total_reward = 0.0

    # Simple heuristic policy (mimics trained agent)
    def heuristic_policy(obs: list[float]) -> int:
        minerals_n = obs[0]
        army_n = obs[5]
        supply_n = obs[2]
        max_supply_n = obs[3]
        threat = obs[8]

        if threat > 0.6:
            return 6  # defend
        if supply_n > max_supply_n * 0.8:
            return 3  # overlord
        if minerals_n > 0.3 and army_n < 0.5:
            return 1  # zergling
        if minerals_n > 0.1 and obs[4] < 0.3:
            return 0  # drone
        return 4 if minerals_n > 0.35 else 0

    while steps_done < total_timesteps:
        obs, _ = env.reset(seed=episodes)
        ep_reward = 0.0
        done = False
        while not done:
            action = heuristic_policy(obs)
            obs, reward, terminated, truncated, _ = env.step(action)
            ep_reward += reward
            steps_done += 1
            done = terminated or truncated
        total_reward += ep_reward
        episodes += 1

        if episodes % 10 == 0:
            avg = total_reward / episodes
            print(
                f"  Episode {episodes:4d} | "
                f"Steps: {steps_done:6d} | "
                f"Avg reward: {avg:.2f}"
            )

    return {
        "total_timesteps": steps_done,
        "episodes": episodes,
        "mean_reward": total_reward / max(1, episodes),
    }


# ─────────────────────────────────────────────
# Main
# ─────────────────────────────────────────────

if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Phase 533: SB3 SC2 Bot RL Training")
    parser.add_argument(
        "--algo",
        choices=["ppo", "a2c", "sim"],
        default="ppo",
        help="Training algorithm: ppo, a2c, or sim(ulation)",
    )
    parser.add_argument("--timesteps", type=int, default=100_000)
    parser.add_argument("--save_path", type=str, default="./models")
    args = parser.parse_args()

    print("Phase 533: Stable Baselines 3 — SC2 Bot RL Training")
    print(f"SB3 available: {SB3_AVAILABLE}")
    print(f"Algorithm: {args.algo} | Timesteps: {args.timesteps}")

    if args.algo == "ppo":
        result = train_ppo(total_timesteps=args.timesteps, save_path=args.save_path)
    elif args.algo == "a2c":
        result = train_a2c(total_timesteps=args.timesteps, save_path=args.save_path)
    else:
        result = simulate_training(total_timesteps=args.timesteps)

    print(f"\nTraining result: {result}")
