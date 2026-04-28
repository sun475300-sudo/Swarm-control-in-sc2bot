# Phase 418: Hydra - SC2 Configuration Management
# Hydra structured configs for SC2 bot with CLI overrides and multi-run sweeps

import logging
import os
from dataclasses import dataclass, field
from typing import List, Optional

import hydra
from hydra.core.config_store import ConfigStore
from hydra.core.hydra_config import HydraConfig
from omegaconf import DictConfig, OmegaConf

log = logging.getLogger(__name__)

# ============================================================
# Structured Config Dataclasses
# ============================================================


@dataclass
class ModelConfig:
    _target_: str = "sc2_bot.model.SC2PolicyNet"
    arch: str = "mlp"  # mlp | transformer | lstm
    hidden_dim: int = 512
    n_layers: int = 3
    obs_dim: int = 256
    action_dim: int = 64
    dropout: float = 0.1
    use_lstm: bool = False


@dataclass
class TrainingConfig:
    algorithm: str = "ppo"  # ppo | a2c | sac
    lr: float = 3e-4
    gamma: float = 0.99
    clip_ratio: float = 0.2
    entropy_coef: float = 0.01
    batch_size: int = 256
    n_epochs: int = 8
    total_steps: int = 1_000_000
    eval_interval: int = 10_000
    save_interval: int = 50_000
    grad_clip: float = 0.5
    gae_lambda: float = 0.95


@dataclass
class EnvConfig:
    map_name: str = "Equilibrium LE"
    enemy_race: str = "random"  # zerg | terran | protoss | random
    difficulty: str = "VeryHard"  # Easy | Medium | Hard | VeryHard | CheatMoney
    realtime: bool = False
    max_game_steps: int = 22400  # ~16 min at 24 FPS
    n_envs: int = 4  # parallel environments
    obs_type: str = "raw"  # raw | feature_layer | both


@dataclass
class InfraConfig:
    device: str = "cpu"  # cpu | cuda | mps
    num_workers: int = 4
    use_wandb: bool = True
    wandb_project: str = "sc2-bot"
    checkpoint_dir: str = "checkpoints"
    log_dir: str = "logs"
    seed: int = 42
    debug: bool = False


@dataclass
class SC2BotConfig:
    model: ModelConfig = field(default_factory=ModelConfig)
    training: TrainingConfig = field(default_factory=TrainingConfig)
    env: EnvConfig = field(default_factory=EnvConfig)
    infra: InfraConfig = field(default_factory=InfraConfig)


# ============================================================
# Config Store Registration
# ============================================================

cs = ConfigStore.instance()
cs.store(name="sc2_base", node=SC2BotConfig)
cs.store(group="model", name="mlp", node=ModelConfig(arch="mlp", hidden_dim=512))
cs.store(
    group="model",
    name="transformer",
    node=ModelConfig(arch="transformer", hidden_dim=256, n_layers=4),
)
cs.store(
    group="model",
    name="lstm",
    node=ModelConfig(arch="lstm", hidden_dim=512, use_lstm=True),
)
cs.store(group="training", name="ppo_default", node=TrainingConfig(algorithm="ppo"))
cs.store(
    group="training",
    name="a2c_fast",
    node=TrainingConfig(algorithm="a2c", lr=7e-4, batch_size=128),
)

# ============================================================
# Main Application
# ============================================================


@hydra.main(version_base=None, config_name="sc2_base")
def main(cfg: SC2BotConfig) -> None:
    # Print full resolved config
    log.info(f"[Hydra] SC2 Bot Configuration:\n{OmegaConf.to_yaml(cfg)}")

    # Access config values
    log.info(f"[Hydra] Model:    {cfg.model.arch} ({cfg.model.hidden_dim} hidden)")
    log.info(f"[Hydra] Training: {cfg.training.algorithm} lr={cfg.training.lr}")
    log.info(f"[Hydra] Env:      {cfg.env.map_name} vs {cfg.env.enemy_race}")
    log.info(f"[Hydra] Device:   {cfg.infra.device}")

    # Multi-run detection
    if HydraConfig.get().mode.name == "MULTIRUN":
        run_id = HydraConfig.get().job.num
        log.info(f"[Hydra] Multi-run sweep, job #{run_id}")

    # Simulate training setup
    os.makedirs(cfg.infra.checkpoint_dir, exist_ok=True)
    os.makedirs(cfg.infra.log_dir, exist_ok=True)

    log.info(f"[Hydra] Batch size: {cfg.training.batch_size}")
    log.info(f"[Hydra] Total steps: {cfg.training.total_steps:,}")
    log.info(f"[Hydra] Checkpoints -> {cfg.infra.checkpoint_dir}")

    # Example: serialize config to JSON for downstream use
    config_dict = OmegaConf.to_container(cfg, resolve=True)
    log.info(f"[Hydra] Config keys: {list(config_dict.keys())}")

    # Return metric for Hydra's --multirun optimization sweeps
    simulated_reward = (
        cfg.training.lr * 1e4
        + cfg.model.hidden_dim * 0.001
        - cfg.training.entropy_coef * 10
    )
    log.info(f"[Hydra] Simulated reward: {simulated_reward:.4f}")
    return simulated_reward


# ============================================================
# Usage Examples (comments)
# ============================================================

# Standard run:
#   python sc2_hydra_main.py
#
# Override single parameter:
#   python sc2_hydra_main.py training.lr=0.001 model=transformer
#
# Override env:
#   python sc2_hydra_main.py env.map_name="Site Delta LE" env.enemy_race=terran
#
# Multi-run sweep:
#   python sc2_hydra_main.py --multirun training.lr=0.001,0.0001,0.00001
#
# Multi-run with model sweep:
#   python sc2_hydra_main.py --multirun model=mlp,transformer training.lr=0.001,0.0001
#
# Debug mode:
#   python sc2_hydra_main.py infra.debug=true infra.device=cpu

if __name__ == "__main__":
    main()
