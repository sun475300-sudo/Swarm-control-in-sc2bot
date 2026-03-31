"""
mlflow_tracking/experiment_tracker.py
MLflow experiment tracking for SC2 Zerg bot training runs.

Tracks: hyperparameters, per-epoch win_rate / avg_game_length / army_efficiency,
model checkpoints, and queries the best run by win_rate.
"""

from __future__ import annotations

import os
import json
import time
import random
import tempfile
import pathlib

import mlflow
import mlflow.sklearn
from mlflow.tracking import MlflowClient

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------
EXPERIMENT_NAME = "sc2_bot_training"
TRACKING_URI    = os.path.join(os.path.dirname(__file__), "mlruns")
mlflow.set_tracking_uri(f"file://{pathlib.Path(TRACKING_URI).resolve()}")


# ---------------------------------------------------------------------------
# Simulate a training run  (placeholder for real SC2 bot training)
# ---------------------------------------------------------------------------
def simulate_training(
    learning_rate: float,
    batch_size: int,
    model_type: str,
    num_epochs: int = 20,
    seed: int = 42,
) -> dict:
    """
    Mock SC2 bot training loop — returns per-epoch metric history.
    In production this would call the actual Keras / JAX training code.
    """
    random.seed(seed)
    history: dict[str, list[float]] = {
        "win_rate":         [],
        "avg_game_length":  [],
        "army_efficiency":  [],
    }
    # Simulate convergence with noise
    for epoch in range(1, num_epochs + 1):
        noise    = random.gauss(0, 0.02)
        progress = epoch / num_epochs
        history["win_rate"].append(
            min(0.95, 0.35 + 0.50 * progress + noise)
        )
        history["avg_game_length"].append(
            max(120, 480 - 120 * progress + random.gauss(0, 10))
        )
        history["army_efficiency"].append(
            min(1.0, 0.45 + 0.40 * progress + random.gauss(0, 0.03))
        )
    return history


# ---------------------------------------------------------------------------
# Save a mock model checkpoint artifact
# ---------------------------------------------------------------------------
def save_checkpoint(run_id: str, model_type: str, epoch: int) -> str:
    tmp_dir  = tempfile.mkdtemp()
    ckpt_path = os.path.join(tmp_dir, f"sc2_bot_{model_type}_ep{epoch}.json")
    checkpoint = {
        "run_id":     run_id,
        "model_type": model_type,
        "epoch":      epoch,
        "saved_at":   time.strftime("%Y-%m-%dT%H:%M:%S"),
    }
    with open(ckpt_path, "w") as f:
        json.dump(checkpoint, f, indent=2)
    return ckpt_path


# ---------------------------------------------------------------------------
# Main tracking function
# ---------------------------------------------------------------------------
def track_run(
    learning_rate: float = 1e-3,
    batch_size: int = 32,
    model_type: str = "policy_gradient",
    num_epochs: int = 20,
    seed: int = 42,
    tags: dict | None = None,
) -> str:
    """
    Log a complete SC2 bot training run to MLflow.
    Returns the run_id of the logged run.
    """
    mlflow.set_experiment(EXPERIMENT_NAME)

    with mlflow.start_run(tags=tags or {"race": "zerg", "framework": "keras"}) as run:
        run_id = run.info.run_id
        print(f"[MLflow] Run started  id={run_id[:8]}…")

        # --- Log hyperparameters ---
        mlflow.log_params({
            "learning_rate": learning_rate,
            "batch_size":    batch_size,
            "model_type":    model_type,
            "num_epochs":    num_epochs,
            "optimizer":     "adam",
            "discount_gamma": 0.99,
        })

        # --- Simulate training ---
        history = simulate_training(learning_rate, batch_size, model_type, num_epochs, seed)

        # --- Log per-epoch metrics ---
        for epoch in range(1, num_epochs + 1):
            mlflow.log_metrics(
                {
                    "win_rate":        history["win_rate"][epoch - 1],
                    "avg_game_length": history["avg_game_length"][epoch - 1],
                    "army_efficiency": history["army_efficiency"][epoch - 1],
                },
                step=epoch,
            )

        # --- Log summary metrics ---
        final_win_rate = history["win_rate"][-1]
        mlflow.log_metrics({
            "final_win_rate":        final_win_rate,
            "final_army_efficiency": history["army_efficiency"][-1],
            "best_win_rate":         max(history["win_rate"]),
        })

        # --- Log model checkpoint artifact ---
        ckpt_path = save_checkpoint(run_id, model_type, num_epochs)
        mlflow.log_artifact(ckpt_path, artifact_path="checkpoints")

        print(f"[MLflow] Run logged  |  final_win_rate={final_win_rate:.2%}")

    return run_id


# ---------------------------------------------------------------------------
# Query best run
# ---------------------------------------------------------------------------
def get_best_run(metric: str = "final_win_rate") -> dict | None:
    """Return the run with the highest value for `metric`."""
    client = MlflowClient()
    exp    = client.get_experiment_by_name(EXPERIMENT_NAME)
    if exp is None:
        print("[MLflow] No experiment found — run some training first.")
        return None

    runs = client.search_runs(
        experiment_ids=[exp.experiment_id],
        order_by=[f"metrics.{metric} DESC"],
        max_results=1,
    )
    if not runs:
        return None

    best = runs[0]
    print(f"\n[MLflow] Best run by {metric}:")
    print(f"  run_id      = {best.info.run_id[:8]}…")
    print(f"  {metric:20s} = {best.data.metrics.get(metric, 'N/A'):.4f}")
    print(f"  model_type  = {best.data.params.get('model_type', 'N/A')}")
    print(f"  lr          = {best.data.params.get('learning_rate', 'N/A')}")
    return {
        "run_id":      best.info.run_id,
        "metric_name": metric,
        "metric_val":  best.data.metrics.get(metric),
        "params":      best.data.params,
    }


# ---------------------------------------------------------------------------
# Entry point — run a grid of hyperparameter configs
# ---------------------------------------------------------------------------
if __name__ == "__main__":
    print(f"[MLflow] Tracking URI : {TRACKING_URI}")
    print(f"[MLflow] Experiment   : {EXPERIMENT_NAME}\n")

    configs = [
        {"learning_rate": 1e-3, "batch_size": 32, "model_type": "policy_gradient", "seed": 1},
        {"learning_rate": 5e-4, "batch_size": 64, "model_type": "dqn",             "seed": 2},
        {"learning_rate": 2e-3, "batch_size": 16, "model_type": "actor_critic",    "seed": 3},
    ]

    run_ids = []
    for cfg in configs:
        rid = track_run(**cfg, num_epochs=20)
        run_ids.append(rid)

    print(f"\n[MLflow] Completed {len(run_ids)} runs.")
    get_best_run("final_win_rate")
