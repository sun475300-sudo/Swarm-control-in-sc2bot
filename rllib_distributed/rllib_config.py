"""
Phase 535: Ray RLlib Distributed
SC2 Bot large-scale RL with RLlib APPO/IMPALA
"""

from __future__ import annotations
from typing import Optional, Any
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

try:
    import ray
    from ray.rllib.algorithms.ppo import PPOConfig
    from ray.rllib.algorithms.appo import APPOConfig
    from ray.rllib.algorithms.impala import IMPALAConfig
    from ray.rllib.env.env_context import EnvContext

    RLLIB_AVAILABLE = True
except ImportError:
    RLLIB_AVAILABLE = False

from gymnasium_env.sc2_gym_env import SC2ZergEnv

# ─────────────────────────────────────────────
# RLlib environment wrapper
# ─────────────────────────────────────────────


class SC2RLlibEnv(SC2ZergEnv):
    """RLlib-compatible SC2 Gym environment."""

    def __init__(self, env_config: Optional[dict] = None):
        config = env_config or {}
        super().__init__(
            max_frames=config.get("max_frames", 2000),
            enemy_aggression=config.get("enemy_aggression", 0.5),
        )


# ─────────────────────────────────────────────
# Algorithm configurations
# ─────────────────────────────────────────────


def build_ppo_config() -> dict:
    """PPO config for SC2 bot training."""
    if not RLLIB_AVAILABLE:
        return {}
    return (
        PPOConfig()
        .environment(SC2RLlibEnv)
        .rollouts(
            num_rollout_workers=4,
            rollout_fragment_length=256,
        )
        .training(
            train_batch_size=2048,
            sgd_minibatch_size=128,
            num_sgd_iter=10,
            lr=3e-4,
            gamma=0.99,
            lambda_=0.95,
            clip_param=0.2,
            vf_clip_param=10.0,
            entropy_coeff=0.01,
        )
        .resources(num_gpus=0)
        .framework("torch")
    )


def build_impala_config() -> dict:
    """IMPALA config for distributed SC2 training."""
    if not RLLIB_AVAILABLE:
        return {}
    return (
        IMPALAConfig()
        .environment(SC2RLlibEnv)
        .rollouts(
            num_rollout_workers=8,
            rollout_fragment_length=50,
        )
        .training(
            train_batch_size=1000,
            lr=6e-4,
            gamma=0.99,
            vtrace=True,
            vtrace_clip_rho_threshold=1.0,
            vtrace_clip_pg_rho_threshold=1.0,
        )
        .resources(num_gpus=0)
    )


def build_appo_config() -> dict:
    """APPO (Async PPO) for SC2 self-play."""
    if not RLLIB_AVAILABLE:
        return {}
    return (
        APPOConfig()
        .environment(SC2RLlibEnv)
        .rollouts(num_rollout_workers=4)
        .training(
            train_batch_size=2048,
            lr=2.5e-4,
            gamma=0.99,
            vtrace=True,
            use_kl_loss=True,
            kl_coeff=0.2,
        )
    )


# ─────────────────────────────────────────────
# Training runner
# ─────────────────────────────────────────────


def train_with_rllib(
    algorithm: str = "ppo",
    iterations: int = 10,
    checkpoint_dir: str = "./checkpoints",
) -> dict:
    if not RLLIB_AVAILABLE:
        print("[RLlib] Not available — using local simulation")
        return _simulate_distributed_training(iterations)

    ray.init(ignore_reinit_error=True)
    os.makedirs(checkpoint_dir, exist_ok=True)

    configs = {
        "ppo": build_ppo_config,
        "impala": build_impala_config,
        "appo": build_appo_config,
    }

    config = configs[algorithm]()
    algo = config.build()

    results = []
    for i in range(iterations):
        result = algo.train()
        results.append(result)
        print(
            f"  Iter {i+1:3d} | "
            f"Reward: {result.get('episode_reward_mean', 0):.2f} | "
            f"Steps: {result.get('timesteps_total', 0)}"
        )

        if (i + 1) % 5 == 0:
            checkpoint = algo.save(checkpoint_dir)
            print(f"  Checkpoint saved: {checkpoint}")

    algo.stop()
    ray.shutdown()
    return {"iterations": iterations, "final_result": results[-1]}


# ─────────────────────────────────────────────
# Self-play league (multi-agent)
# ─────────────────────────────────────────────


def build_selfplay_config():
    """Multi-agent self-play configuration."""
    if not RLLIB_AVAILABLE:
        return {}

    # Two agents: main + opponent (frozen periodically)
    policies = {
        "main": (None, None, None, {}),
        "opponent": (None, None, None, {"explore": False}),
    }

    def policy_mapping(agent_id, episode, worker, **kw):
        return "main" if agent_id == "player_0" else "opponent"

    return (
        PPOConfig()
        .environment(SC2RLlibEnv)
        .multi_agent(
            policies=policies,
            policy_mapping_fn=policy_mapping,
            policies_to_train=["main"],
        )
    )


# ─────────────────────────────────────────────
# Simulation fallback
# ─────────────────────────────────────────────


def _simulate_distributed_training(iterations: int) -> dict:
    """Simulate multi-worker training without Ray."""
    from gymnasium_env.sc2_gym_env import SC2ZergEnv
    import random

    # 4 parallel "workers"
    n_workers = 4
    envs = [SC2ZergEnv(max_frames=500) for _ in range(n_workers)]
    all_rewards = []

    for it in range(iterations):
        iter_rewards = []
        for env in envs:
            obs, _ = env.reset(seed=it)
            ep_r = 0.0
            done = False
            while not done:
                # Heuristic policy
                m, gas, sup, max_sup = obs[0], obs[1], obs[2], obs[3]
                threat = obs[8]
                if threat > 0.6:
                    action = 6
                elif sup > max_sup * 0.85:
                    action = 3
                elif m > 0.3:
                    action = 1
                else:
                    action = 0
                obs, r, term, trunc, _ = env.step(action)
                ep_r += r
                done = term or trunc
            iter_rewards.append(ep_r)
        mean_r = sum(iter_rewards) / len(iter_rewards)
        all_rewards.append(mean_r)
        print(
            f"  Iter {it+1:3d} | Mean reward: {mean_r:.2f} " f"(4 workers × 500 steps)"
        )

    return {
        "iterations": iterations,
        "mean_reward": sum(all_rewards) / len(all_rewards),
        "best_reward": max(all_rewards),
    }


if __name__ == "__main__":
    print("Phase 535: Ray RLlib — Distributed SC2 Training")
    print(f"RLlib available: {RLLIB_AVAILABLE}")

    result = train_with_rllib(algorithm="ppo", iterations=5)
    print(f"\nResult: mean_reward = {result.get('mean_reward', 'N/A'):.2f}")
