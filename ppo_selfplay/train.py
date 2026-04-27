"""
Phase 354: Training Loop
Main training loop orchestrating PPO self-play for SC2 bot.
Supports distributed training (Ray / multiprocessing) and Wandb experiment tracking.
"""

import argparse
import json
import os
import time
from dataclasses import asdict, dataclass
from typing import Any, Dict, Optional

import torch

try:
    import wandb

    WANDB_AVAILABLE = True
except ImportError:
    WANDB_AVAILABLE = False

try:
    import ray

    RAY_AVAILABLE = True
except ImportError:
    RAY_AVAILABLE = False

from curriculum import CurriculumScheduler
from ppo_trainer import PPOConfig, PPOTrainer
from reward_shaper import RewardMode, RewardShaper
from selfplay_manager import AgentRole, OpponentPool, SelfPlayManager


@dataclass
class TrainConfig:
    total_steps: int = 10_000_000
    eval_interval: int = 50_000
    checkpoint_interval: int = 100_000
    checkpoint_dir: str = "checkpoints/ppo"
    log_interval: int = 5_000
    use_wandb: bool = False
    wandb_project: str = "sc2-selfplay-ppo"
    wandb_run_name: Optional[str] = None
    n_workers: int = 4
    use_ray: bool = False
    seed: int = 42


def setup_training(cfg: TrainConfig, ppo_cfg: PPOConfig) -> Dict[str, Any]:
    torch.manual_seed(cfg.seed)
    os.makedirs(cfg.checkpoint_dir, exist_ok=True)
    trainer = PPOTrainer(ppo_cfg)
    pool = OpponentPool(
        max_size=20, checkpoint_dir=os.path.join(cfg.checkpoint_dir, "opponents")
    )
    selfplay = SelfPlayManager(
        trainer.model, pool, checkpoint_interval=cfg.checkpoint_interval
    )
    curriculum = CurriculumScheduler()
    reward_shaper = RewardShaper(mode=RewardMode.SHAPED, curriculum_stage=0)

    if cfg.use_wandb and WANDB_AVAILABLE:
        wandb.init(
            project=cfg.wandb_project,
            name=cfg.wandb_run_name,
            config={**asdict(cfg), **asdict(ppo_cfg)},
        )

    return {
        "trainer": trainer,
        "selfplay": selfplay,
        "curriculum": curriculum,
        "reward_shaper": reward_shaper,
    }


def save_checkpoint(
    trainer: PPOTrainer, selfplay: SelfPlayManager, step: int, path: str
) -> None:
    os.makedirs(path, exist_ok=True)
    torch.save(trainer.model.state_dict(), os.path.join(path, f"model_{step}.pt"))
    torch.save(trainer.optimizer.state_dict(), os.path.join(path, f"optim_{step}.pt"))
    meta = {
        "step": step,
        "main_elo": selfplay.main_elo,
        "pool_size": len(selfplay.pool),
    }
    with open(os.path.join(path, f"meta_{step}.json"), "w") as f:
        json.dump(meta, f)
    print(f"[Checkpoint] saved at step {step} -> {path}")


def load_checkpoint(trainer: PPOTrainer, step: int, path: str) -> None:
    model_path = os.path.join(path, f"model_{step}.pt")
    optim_path = os.path.join(path, f"optim_{step}.pt")
    trainer.model.load_state_dict(torch.load(model_path, map_location="cpu"))
    trainer.optimizer.load_state_dict(torch.load(optim_path, map_location="cpu"))
    print(f"[Checkpoint] loaded step {step} from {path}")


def evaluate_vs_builtin(trainer: PPOTrainer, env_factory, n_games: int = 20) -> float:
    """Run evaluation games against built-in SC2 AI."""
    wins = 0
    trainer.model.eval()
    for _ in range(n_games):
        env = env_factory(difficulty="medium")
        obs = env.reset()
        done = False
        while not done:
            obs_t = torch.FloatTensor(obs).unsqueeze(0)
            with torch.no_grad():
                action, _, _ = trainer.model.get_action(obs_t)
            obs, _, done, info = env.step(action.item())
        if info.get("winner") == "self":
            wins += 1
    trainer.model.train()
    win_rate = wins / n_games
    print(f"[Eval] Win rate vs built-in: {win_rate:.2%} ({wins}/{n_games})")
    return win_rate


def run_training_loop(cfg: TrainConfig, ppo_cfg: PPOConfig, env_factory) -> None:
    ctx = setup_training(cfg, ppo_cfg)
    trainer: PPOTrainer = ctx["trainer"]
    selfplay: SelfPlayManager = ctx["selfplay"]
    curriculum: CurriculumScheduler = ctx["curriculum"]
    reward_shaper: RewardShaper = ctx["reward_shaper"]

    env = env_factory()
    step = 0
    t0 = time.time()

    while step < cfg.total_steps:
        trainer.collect_rollouts(env)
        metrics = trainer.train_epoch()
        step = trainer.total_steps

        if step % cfg.log_interval < ppo_cfg.n_steps:
            elapsed = time.time() - t0
            fps = step / max(elapsed, 1)
            stats = selfplay.get_stats()
            print(
                f"[Step {step:>8}] fps={fps:.0f} | "
                f"policy_loss={metrics['policy_loss']:.4f} | "
                f"value_loss={metrics['value_loss']:.4f} | "
                f"elo={stats['main_elo']:.1f} | "
                f"win_rate={stats['win_rate']:.2%}"
            )
            if cfg.use_wandb and WANDB_AVAILABLE:
                wandb.log({**metrics, **stats, "step": step, "fps": fps})

        if step % cfg.checkpoint_interval < ppo_cfg.n_steps:
            save_checkpoint(trainer, selfplay, step, cfg.checkpoint_dir)

        if step % cfg.eval_interval < ppo_cfg.n_steps:
            win_rate = evaluate_vs_builtin(trainer, env_factory)
            promoted = reward_shaper.advance_curriculum(win_rate)
            if promoted:
                curriculum.advance(win_rate)
                print(f"[Curriculum] Promoted to: {reward_shaper.stage_name}")

    if cfg.use_wandb and WANDB_AVAILABLE:
        wandb.finish()
    print("[Training] Complete.")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="PPO Self-Play Training for SC2 Zerg Bot"
    )
    parser.add_argument("--total_steps", type=int, default=10_000_000)
    parser.add_argument("--use_wandb", action="store_true")
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--eval_interval", type=int, default=50_000)
    parser.add_argument("--checkpoint_interval", type=int, default=100_000)
    parser.add_argument("--n_workers", type=int, default=4)
    args = parser.parse_args()

    train_cfg = TrainConfig(
        total_steps=args.total_steps,
        use_wandb=args.use_wandb,
        seed=args.seed,
        eval_interval=args.eval_interval,
        checkpoint_interval=args.checkpoint_interval,
        n_workers=args.n_workers,
    )
    ppo_cfg = PPOConfig()

    # Gymnasium 환경 팩토리 연결
    try:
        import sys

        sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
        from gymnasium_env.sc2_gym_env import SC2ZergEnv

        def env_factory(**kwargs):
            return SC2ZergEnv(max_frames=kwargs.get("max_frames", 20000))

    except ImportError:
        print("[WARN] SC2ZergEnv not found. Using fallback dummy environment.")

        class _DummyEnv:
            """Minimal fallback env for testing the training loop."""

            def __init__(self, **kw):
                import numpy as np

                self._np = np
                self.observation_space_n = 16
                self.action_space_n = 7

            def reset(self):
                return self._np.zeros(self.observation_space_n, dtype="float32")

            def step(self, action):
                obs = self._np.random.rand(self.observation_space_n).astype("float32")
                reward = self._np.random.uniform(-1, 1)
                done = self._np.random.random() < 0.005
                info = (
                    {"winner": "self"}
                    if done and self._np.random.random() > 0.5
                    else {}
                )
                return obs, reward, done, info

        def env_factory(**kwargs):
            return _DummyEnv(**kwargs)

    print("[Train] Config:", asdict(train_cfg))
    print("[Train] PPO Config:", asdict(ppo_cfg))
    print("[Train] Starting training loop...")
    run_training_loop(train_cfg, ppo_cfg, env_factory)
