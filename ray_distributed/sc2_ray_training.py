# Phase 403: Ray - SC2 Distributed Training
# Ray distributed training, tuning, and serving for SC2 bot

import ray
from ray import train, tune
from ray.train.torch import TorchTrainer
from ray.train import ScalingConfig, RunConfig, CheckpointConfig
from ray.tune import TuneConfig
from ray.tune.schedulers import ASHAScheduler
from ray.serve import deployment, serve
import ray.serve as rs

import torch
import torch.nn as nn
import numpy as np
from typing import Dict, Any

# ============================================================
# SC2 Policy Network
# ============================================================

class SC2PolicyNet(nn.Module):
    def __init__(self, obs_dim: int = 256, action_dim: int = 64, hidden_dim: int = 512):
        super().__init__()
        self.net = nn.Sequential(
            nn.Linear(obs_dim, hidden_dim),
            nn.ReLU(),
            nn.Linear(hidden_dim, hidden_dim),
            nn.ReLU(),
        )
        self.actor  = nn.Linear(hidden_dim, action_dim)
        self.critic = nn.Linear(hidden_dim, 1)

    def forward(self, obs):
        feat   = self.net(obs)
        logits = self.actor(feat)
        value  = self.critic(feat)
        return logits, value

# ============================================================
# Remote Actor: Parallel Game Simulator
# ============================================================

@ray.remote
class SC2GameSimulator:
    def __init__(self, worker_id: int):
        self.worker_id = worker_id
        self.episode   = 0

    def run_episode(self, policy_weights: Dict[str, Any]) -> Dict[str, float]:
        """Simulate one SC2 game episode and return trajectory stats."""
        self.episode += 1
        # Mock game simulation
        steps       = np.random.randint(200, 800)
        total_reward = np.random.uniform(-1.0, 1.0) * steps * 0.1
        win          = float(total_reward > 0)
        return {
            "worker_id":    self.worker_id,
            "episode":      self.episode,
            "steps":        steps,
            "total_reward": total_reward,
            "win":          win,
        }

    def get_worker_id(self) -> int:
        return self.worker_id

# ============================================================
# Ray Train: TorchTrainer
# ============================================================

def sc2_train_loop(config: Dict[str, Any]):
    """Training loop executed on each Ray Train worker."""
    model     = SC2PolicyNet(
        hidden_dim=config.get("hidden_dim", 512)
    )
    optimizer = torch.optim.Adam(
        model.parameters(), lr=config.get("lr", 3e-4)
    )

    for epoch in range(config.get("num_epochs", 10)):
        # Mock PPO update step
        obs    = torch.randn(config.get("batch_size", 256), 256)
        logits, value = model(obs)

        actor_loss  = -logits.mean()
        critic_loss = value.pow(2).mean()
        entropy     = -(logits.softmax(-1) * logits.log_softmax(-1)).sum(-1).mean()

        loss = (
            actor_loss
            + config.get("vf_coef", 0.5) * critic_loss
            - config.get("ent_coef", 0.01) * entropy
        )

        optimizer.zero_grad()
        loss.backward()
        optimizer.step()

        train.report({
            "epoch":        epoch,
            "loss":         loss.item(),
            "actor_loss":   actor_loss.item(),
            "critic_loss":  critic_loss.item(),
            "entropy":      entropy.item(),
        })

# ============================================================
# Ray Tune: Hyperparameter Optimization
# ============================================================

def run_hyperparameter_tuning():
    sweep_config = tune.TuneConfig(
        num_samples=20,
        scheduler=ASHAScheduler(metric="loss", mode="min"),
    )

    param_space = {
        "lr":         tune.loguniform(1e-5, 1e-3),
        "gamma":      tune.uniform(0.95, 0.999),
        "clip_ratio": tune.uniform(0.1, 0.3),
        "ent_coef":   tune.loguniform(1e-4, 1e-2),
        "batch_size": tune.choice([64, 128, 256, 512]),
        "hidden_dim": tune.choice([256, 512, 1024]),
        "vf_coef":    tune.uniform(0.25, 1.0),
        "num_epochs": 5,
    }

    trainer = TorchTrainer(
        train_loop_per_worker=sc2_train_loop,
        scaling_config=ScalingConfig(num_workers=2, use_gpu=False),
    )

    tuner = tune.Tuner(
        trainer,
        param_space={"train_loop_config": param_space},
        tune_config=sweep_config,
        run_config=RunConfig(
            name="sc2_ppo_tuning",
            checkpoint_config=CheckpointConfig(num_to_keep=2),
        ),
    )

    results = tuner.fit()
    best    = results.get_best_result(metric="loss", mode="min")
    print(f"[Ray Tune] Best config: {best.config}")
    return best

# ============================================================
# Ray Serve: Model Deployment
# ============================================================

@deployment(num_replicas=2, ray_actor_options={"num_cpus": 1})
class SC2PolicyServer:
    def __init__(self):
        self.model = SC2PolicyNet()
        self.model.eval()
        print("[Ray Serve] SC2 policy server ready")

    async def __call__(self, request):
        import json
        body = await request.json()
        obs  = torch.tensor(body["obs"], dtype=torch.float32).unsqueeze(0)
        with torch.no_grad():
            logits, value = self.model(obs)
        action = logits.argmax(dim=-1).item()
        return {"action": action, "value": value.item()}

def deploy_model():
    rs.start(detached=True)
    handle = rs.run(SC2PolicyServer.bind())
    print(f"[Ray Serve] Deployment handle: {handle}")
    return handle

# ============================================================
# Main: Parallel Simulation
# ============================================================

def run_parallel_simulation(num_workers: int = 4):
    simulators = [SC2GameSimulator.remote(i) for i in range(num_workers)]
    dummy_weights: Dict[str, Any] = {}

    futures = [sim.run_episode.remote(dummy_weights) for sim in simulators]
    results = ray.get(futures)

    wins  = sum(r["win"] for r in results)
    total = len(results)
    print(f"[Ray] Parallel sim: {wins}/{total} wins")
    return results

if __name__ == "__main__":
    ray.init(ignore_reinit_error=True)
    print("[Ray] Initialized distributed runtime")

    sim_results = run_parallel_simulation(num_workers=4)

    trainer = TorchTrainer(
        train_loop_per_worker=sc2_train_loop,
        train_loop_config={"lr": 3e-4, "batch_size": 256, "num_epochs": 3},
        scaling_config=ScalingConfig(num_workers=2, use_gpu=False),
    )
    result = trainer.fit()
    print(f"[Ray Train] Training complete: {result.metrics}")

    ray.shutdown()
    print("[Ray] Shutdown complete")
