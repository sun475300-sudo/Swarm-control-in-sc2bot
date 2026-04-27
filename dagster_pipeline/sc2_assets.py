"""
Phase 425: Dagster - SC2 ML Data Assets
Declarative data assets for the full SC2 machine learning pipeline.
"""

from dagster import (
    asset,
    AssetIn,
    AssetCheckResult,
    asset_check,
    DailyPartitionsDefinition,
    MetadataValue,
    Output,
    define_asset_job,
    AssetSelection,
)
import pandas as pd
import numpy as np
from datetime import date, timedelta

# ── Partition definition ──────────────────────────────────────────────────────

daily_partitions = DailyPartitionsDefinition(start_date="2025-01-01")


# ── Assets ────────────────────────────────────────────────────────────────────


@asset(
    partitions_def=daily_partitions,
    description="Raw SC2 replay files downloaded for the partition date.",
    metadata={"source": "ladder-api", "format": "sc2replay"},
    group_name="ingestion",
)
def raw_replays(context) -> Output:
    """Download raw SC2 replay files for the given day."""
    partition_date = context.partition_key
    n_replays = np.random.randint(200, 600)
    context.log.info(f"Downloading {n_replays} replays for {partition_date}")

    df = pd.DataFrame(
        {
            "game_id": [f"{partition_date}_g{i:04d}" for i in range(n_replays)],
            "duration": np.random.uniform(90, 1500, n_replays),
            "race_p1": np.random.choice(["Zerg", "Terran", "Protoss"], n_replays),
            "race_p2": np.random.choice(["Zerg", "Terran", "Protoss"], n_replays),
            "winner": np.random.randint(1, 3, n_replays),
        }
    )

    return Output(
        value=df,
        metadata={
            "partition_date": partition_date,
            "n_replays": MetadataValue.int(n_replays),
            "size_mb": MetadataValue.float(round(n_replays * 0.8, 2)),
        },
    )


@asset(
    ins={"raw_replays": AssetIn()},
    partitions_def=daily_partitions,
    description="Extracted feature vectors from SC2 replays.",
    group_name="feature_engineering",
)
def processed_features(context, raw_replays: pd.DataFrame) -> Output:
    """Parse replays and extract ML feature vectors."""
    df = raw_replays.copy()
    n = len(df)
    context.log.info(f"Engineering features for {n} replays...")

    # Simulate feature extraction
    features = pd.DataFrame(
        {
            "game_id": df["game_id"],
            "duration": df["duration"],
            "race_p1_enc": pd.Categorical(df["race_p1"]).codes,
            "race_p2_enc": pd.Categorical(df["race_p2"]).codes,
            "winner": df["winner"],
            "apm_p1": np.random.uniform(40, 300, n),
            "apm_p2": np.random.uniform(40, 300, n),
            "supply_peak_p1": np.random.randint(60, 200, n),
            "supply_peak_p2": np.random.randint(60, 200, n),
            "minerals_p1": np.random.randint(3000, 25000, n),
            "army_value_p1": np.random.randint(1000, 15000, n),
        }
    )

    return Output(
        value=features,
        metadata={
            "n_samples": MetadataValue.int(n),
            "n_features": MetadataValue.int(len(features.columns) - 1),
        },
    )


@asset(
    ins={"processed_features": AssetIn()},
    partitions_def=daily_partitions,
    description="Trained SC2 strategy model checkpoint.",
    group_name="training",
)
def trained_model(context, processed_features: pd.DataFrame) -> Output:
    """Train SC2 model on processed features."""
    n = len(processed_features)
    context.log.info(f"Training on {n} samples...")

    model_artifact = {
        "model_type": "PPO",
        "n_training_samples": n,
        "train_loss": round(np.random.uniform(0.15, 0.30), 4),
        "val_loss": round(np.random.uniform(0.18, 0.35), 4),
        "checkpoint_path": f"checkpoints/{context.partition_key}_model.pt",
        "architecture": {"hidden_layers": [256, 256, 128], "activation": "ReLU"},
    }

    return Output(
        value=model_artifact,
        metadata={
            "train_loss": MetadataValue.float(model_artifact["train_loss"]),
            "val_loss": MetadataValue.float(model_artifact["val_loss"]),
            "checkpoint": MetadataValue.path(model_artifact["checkpoint_path"]),
        },
    )


@asset(
    ins={"trained_model": AssetIn(), "processed_features": AssetIn()},
    partitions_def=daily_partitions,
    description="Evaluation metrics for the trained SC2 model.",
    group_name="evaluation",
)
def model_metrics(
    context, trained_model: dict, processed_features: pd.DataFrame
) -> Output:
    """Compute evaluation metrics on held-out test set."""
    n_test = int(len(processed_features) * 0.1)
    context.log.info(f"Evaluating on {n_test} test samples...")

    metrics = {
        "win_rate": round(np.random.uniform(0.52, 0.70), 4),
        "action_accuracy": round(np.random.uniform(0.68, 0.92), 4),
        "avg_game_length": round(np.random.uniform(350, 650), 1),
        "build_order_adherence": round(np.random.uniform(0.72, 0.94), 4),
        "n_test_games": n_test,
        "model_checkpoint": trained_model["checkpoint_path"],
    }

    return Output(
        value=metrics,
        metadata={
            "win_rate": MetadataValue.float(metrics["win_rate"]),
            "action_accuracy": MetadataValue.float(metrics["action_accuracy"]),
        },
    )


# ── Asset checks ──────────────────────────────────────────────────────────────


@asset_check(asset=raw_replays, description="Ensure raw replay count is reasonable.")
def check_replay_count(raw_replays: pd.DataFrame) -> AssetCheckResult:
    n = len(raw_replays)
    passed = n >= 50
    return AssetCheckResult(passed=passed, metadata={"n_replays": n})


@asset_check(asset=model_metrics, description="Win rate must exceed baseline.")
def check_win_rate(model_metrics: dict) -> AssetCheckResult:
    win_rate = model_metrics["win_rate"]
    passed = win_rate >= 0.50
    return AssetCheckResult(
        passed=passed,
        metadata={"win_rate": win_rate, "threshold": 0.50},
    )


# ── Job definition ────────────────────────────────────────────────────────────

sc2_ml_job = define_asset_job(
    name="sc2_daily_ml_job",
    selection=AssetSelection.groups(
        "ingestion", "feature_engineering", "training", "evaluation"
    ),
    description="Daily SC2 ML training job.",
)


if __name__ == "__main__":
    print("[Dagster] SC2 asset definitions loaded.")
    print(f"  Assets: raw_replays, processed_features, trained_model, model_metrics")
    print(f"  Checks: check_replay_count, check_win_rate")
    print(f"  Job: {sc2_ml_job.name}")

# Phase 425: Dagster registered
