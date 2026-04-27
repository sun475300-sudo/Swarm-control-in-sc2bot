# Phase 417: Optuna - SC2 Hyperparameter Optimization
# Optuna TPE sampler with pruning for SC2 PPO model tuning

import optuna
from optuna.samplers import TPESampler
from optuna.pruners import MedianPruner
from optuna.visualization import (
    plot_optimization_history,
    plot_param_importances,
    plot_parallel_coordinate,
    plot_contour,
)
import torch
import torch.nn as nn
import numpy as np
from pathlib import Path

# ============================================================
# Policy Network
# ============================================================


class SC2Policy(nn.Module):
    def __init__(self, obs_dim: int, action_dim: int, hidden_dim: int, n_layers: int):
        super().__init__()
        layers = [nn.Linear(obs_dim, hidden_dim), nn.ReLU()]
        for _ in range(n_layers - 1):
            layers += [nn.Linear(hidden_dim, hidden_dim), nn.ReLU()]
        self.backbone = nn.Sequential(*layers)
        self.actor = nn.Linear(hidden_dim, action_dim)
        self.critic = nn.Linear(hidden_dim, 1)

    def forward(self, x):
        h = self.backbone(x)
        return self.actor(h), self.critic(h)


# ============================================================
# Objective Function
# ============================================================


def objective(trial: optuna.Trial) -> float:
    """PPO training objective — returns mean reward (higher is better)."""

    # Hyperparameter suggestions
    lr = trial.suggest_float("learning_rate", 1e-5, 1e-3, log=True)
    gamma = trial.suggest_float("gamma", 0.95, 0.999)
    clip_ratio = trial.suggest_float("clip_ratio", 0.1, 0.3)
    entropy_coef = trial.suggest_float("entropy_coef", 1e-4, 1e-2, log=True)
    batch_size = trial.suggest_int("batch_size", 64, 512, step=64)
    hidden_dim = trial.suggest_categorical("hidden_dim", [256, 512, 1024])
    n_layers = trial.suggest_int("n_layers", 1, 3)
    gae_lambda = trial.suggest_float("gae_lambda", 0.9, 0.99)
    optimizer_name = trial.suggest_categorical("optimizer", ["Adam", "RMSprop"])

    model = SC2Policy(
        obs_dim=256, action_dim=64, hidden_dim=hidden_dim, n_layers=n_layers
    )
    opt = getattr(torch.optim, optimizer_name)(model.parameters(), lr=lr)
    rng = np.random.default_rng(trial.number)

    total_reward = 0.0

    for step in range(20):
        obs = torch.randn(batch_size, 256)
        actions = torch.randint(0, 64, (batch_size,))
        rewards = torch.tensor(rng.normal(0.5, 1.0, batch_size), dtype=torch.float32)

        logits, values = model(obs)
        log_probs = torch.log_softmax(logits, dim=-1)
        selected = log_probs[range(batch_size), actions]

        ratio = torch.exp(selected - selected.detach())
        advantage = (rewards - values.squeeze()).detach()
        advantage = (advantage - advantage.mean()) / (advantage.std() + 1e-8)

        pg_loss = torch.max(
            -advantage * ratio,
            -advantage * torch.clamp(ratio, 1 - clip_ratio, 1 + clip_ratio),
        ).mean()
        vf_loss = nn.functional.mse_loss(values.squeeze(), rewards * gamma)
        entropy = -(log_probs.softmax(-1) * log_probs).sum(-1).mean()
        loss = pg_loss + 0.5 * vf_loss - entropy_coef * entropy

        opt.zero_grad()
        loss.backward()
        nn.utils.clip_grad_norm_(model.parameters(), 0.5)
        opt.step()

        step_reward = rewards.mean().item() + step * 0.03
        total_reward += step_reward

        # Report intermediate value for pruning
        trial.report(step_reward, step=step)
        if trial.should_prune():
            raise optuna.TrialPruned()

    return total_reward / 20


# ============================================================
# Study Setup and Execution
# ============================================================


def run_optimization(n_trials: int = 50, n_jobs: int = 1) -> optuna.Study:
    sampler = TPESampler(
        n_startup_trials=10,
        multivariate=True,
        seed=42,
    )
    pruner = MedianPruner(
        n_startup_trials=5,
        n_warmup_steps=5,
        interval_steps=2,
    )

    study = optuna.create_study(
        study_name="sc2-ppo-optuna",
        direction="maximize",
        sampler=sampler,
        pruner=pruner,
        storage="sqlite:///sc2_optuna.db",
        load_if_exists=True,
    )

    study.optimize(
        objective,
        n_trials=n_trials,
        n_jobs=n_jobs,
        show_progress_bar=True,
        callbacks=[
            lambda study, trial: (
                print(f"[Optuna] Trial {trial.number}: reward={trial.value:.4f}")
                if trial.value is not None
                else None
            )
        ],
    )

    return study


# ============================================================
# Results and Visualization
# ============================================================


def print_best_params(study: optuna.Study):
    print("\n=== Best Trial ===")
    trial = study.best_trial
    print(f"  Mean reward:  {trial.value:.4f}")
    print(f"  Best params:")
    for k, v in trial.params.items():
        print(f"    {k:20s}: {v}")


def visualize_study(study: optuna.Study, output_dir: str = "optuna_plots"):
    Path(output_dir).mkdir(exist_ok=True)

    # plot_optimization_history
    fig = plot_optimization_history(study)
    fig.write_html(f"{output_dir}/optimization_history.html")
    print(
        f"[Optuna] Saved optimization history to {output_dir}/optimization_history.html"
    )

    # plot_param_importances
    fig = plot_param_importances(study)
    fig.write_html(f"{output_dir}/param_importances.html")
    print(f"[Optuna] Saved param importances to {output_dir}/param_importances.html")

    # plot_parallel_coordinate
    fig = plot_parallel_coordinate(study)
    fig.write_html(f"{output_dir}/parallel_coordinate.html")
    print(
        f"[Optuna] Saved parallel coordinate to {output_dir}/parallel_coordinate.html"
    )

    # plot_contour for top 2 params
    fig = plot_contour(study, params=["learning_rate", "hidden_dim"])
    fig.write_html(f"{output_dir}/contour.html")
    print(f"[Optuna] Saved contour plot to {output_dir}/contour.html")


# ============================================================
# Main
# ============================================================


def main():
    print("[Optuna] SC2 PPO hyperparameter optimization starting...")
    optuna.logging.set_verbosity(optuna.logging.WARNING)

    study = run_optimization(n_trials=30)
    print_best_params(study)

    completed = len(
        [t for t in study.trials if t.state == optuna.trial.TrialState.COMPLETE]
    )
    pruned = len([t for t in study.trials if t.state == optuna.trial.TrialState.PRUNED])
    print(f"\n[Optuna] Trials: {completed} complete, {pruned} pruned")

    visualize_study(study)
    print("\n[Optuna] Optimization complete. HTML plots saved to optuna_plots/")


if __name__ == "__main__":
    main()
