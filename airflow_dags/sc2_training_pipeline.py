# Phase 576: Airflow DAGs Advanced
# SC2 Bot ML Training Pipeline - Airflow DAG
# Standalone-runnable with graceful fallback if airflow not installed

from __future__ import annotations

import json
import logging
import random
import sys
from datetime import datetime, timedelta
from typing import Any

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Graceful fallback: define mock decorators if airflow is not installed
# ---------------------------------------------------------------------------
try:
    from airflow.decorators import dag, task
    from airflow.models import Variable
    from airflow.operators.email import EmailOperator
    from airflow.utils.dates import days_ago

    AIRFLOW_AVAILABLE = True
    print("[INFO] Airflow detected — using real DAG runtime.")
except ImportError:
    AIRFLOW_AVAILABLE = False
    print("[WARN] Airflow not installed — running in standalone simulation mode.")

    # ---- Mock decorator implementations ----
    class _MockDAGContext:
        def __init__(self, dag_id, **kwargs):
            self.dag_id = dag_id
            self.kwargs = kwargs

        def __call__(self, func):
            func._is_dag = True
            func._dag_id = self.dag_id
            return func

        def __enter__(self):
            return self

        def __exit__(self, *args):
            pass

    def dag(dag_id=None, **kwargs):
        def decorator(func):
            func._is_dag = True
            func._dag_id = dag_id or func.__name__
            return func

        return decorator

    def task(func=None, **kwargs):
        if func is not None:
            return func

        def decorator(f):
            return f

        return decorator

    class Variable:
        _store: dict[str, str] = {}

        @classmethod
        def get(cls, key: str, default_var: Any = None) -> Any:
            return cls._store.get(key, default_var)

        @classmethod
        def set(cls, key: str, value: Any) -> None:
            cls._store[key] = value

    def days_ago(n):
        return datetime.utcnow() - timedelta(days=n)


# ---------------------------------------------------------------------------
# Pipeline configuration (can be overridden via Airflow Variables)
# ---------------------------------------------------------------------------
DEFAULT_PARAMS = {
    "timesteps": 500_000,
    "learning_rate": 3e-4,
    "min_win_rate": 0.55,
    "replay_bucket": "s3://sc2-replays/raw/",
    "model_registry_uri": "mlflow://sc2-models/ppo-sc2",
    "notification_email": "sc2bot-team@example.com",
}


def get_param(key: str) -> Any:
    """Fetch param from Airflow Variable, fall back to DEFAULT_PARAMS."""
    raw = Variable.get(f"sc2_pipeline_{key}", default_var=None)
    if raw is not None:
        try:
            return json.loads(raw)
        except (json.JSONDecodeError, TypeError):
            return raw
    return DEFAULT_PARAMS[key]


# ---------------------------------------------------------------------------
# TaskFlow API — individual tasks
# ---------------------------------------------------------------------------


@task
def extract_replays(**context) -> dict:
    """
    Extract SC2 replay files from object storage.
    Returns metadata dict pushed via XCom.
    """
    bucket = get_param("replay_bucket")
    logger.info("Extracting replays from %s", bucket)

    # Simulate discovery of replay files
    replay_count = random.randint(120, 400)
    replay_ids = [f"replay_{i:05d}" for i in range(replay_count)]

    result = {
        "replay_count": replay_count,
        "replay_ids": replay_ids[:10],  # sample for XCom (full list stored externally)
        "source_bucket": bucket,
        "extraction_ts": datetime.utcnow().isoformat(),
        "races_found": ["Terran", "Zerg", "Protoss"],
    }
    logger.info("Extracted %d replays.", replay_count)
    return result


@task
def preprocess_features(extract_result: dict, **context) -> dict:
    """
    Convert raw replays into feature tensors for PPO training.
    Receives extract metadata via XCom argument.
    """
    replay_count = extract_result["replay_count"]
    logger.info("Preprocessing features for %d replays.", replay_count)

    # Simulate feature engineering
    feature_dim = 256
    valid_samples = int(replay_count * 0.92)  # ~8% discarded as corrupt/short

    result = {
        "valid_samples": valid_samples,
        "feature_dim": feature_dim,
        "feature_store_path": f"/tmp/sc2_features_{datetime.utcnow().strftime('%Y%m%d')}.npz",
        "label_distribution": {
            "win": round(random.uniform(0.45, 0.60), 3),
            "loss": None,  # computed below
        },
    }
    result["label_distribution"]["loss"] = round(
        1.0 - result["label_distribution"]["win"], 3
    )

    logger.info(
        "Features ready — %d valid samples, dim=%d, win_rate=%.3f",
        valid_samples,
        feature_dim,
        result["label_distribution"]["win"],
    )
    return result


@task
def train_ppo(preprocess_result: dict, **context) -> dict:
    """
    Train PPO agent on preprocessed SC2 replay features.
    Returns model checkpoint metadata via XCom.
    """
    timesteps = get_param("timesteps")
    lr = get_param("learning_rate")
    feature_path = preprocess_result["feature_store_path"]

    logger.info(
        "Starting PPO training — timesteps=%d, lr=%s, features=%s",
        timesteps,
        lr,
        feature_path,
    )

    # Simulate training loop telemetry
    epochs = 10
    losses = []
    for epoch in range(epochs):
        loss = 1.5 * (0.85**epoch) + random.uniform(-0.02, 0.02)
        losses.append(round(loss, 4))
        logger.info("  Epoch %d/%d — loss=%.4f", epoch + 1, epochs, loss)

    checkpoint_path = (
        f"/tmp/sc2_ppo_checkpoint_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}.pt"
    )

    result = {
        "checkpoint_path": checkpoint_path,
        "final_loss": losses[-1],
        "loss_history": losses,
        "timesteps_trained": timesteps,
        "learning_rate": lr,
        "training_duration_s": random.randint(600, 3600),
    }
    logger.info(
        "Training complete — checkpoint: %s, final_loss=%.4f",
        checkpoint_path,
        losses[-1],
    )
    return result


@task
def evaluate_model(train_result: dict, **context) -> dict:
    """
    Evaluate the trained PPO model against a fixed opponent pool.
    Returns evaluation metrics via XCom.
    """
    checkpoint = train_result["checkpoint_path"]
    logger.info("Evaluating model from checkpoint: %s", checkpoint)

    # Simulate evaluation games against scripted opponents
    evaluation_games = 200
    wins = random.randint(80, 160)
    win_rate = wins / evaluation_games

    matchup_results = {}
    races = ["Terran", "Zerg", "Protoss"]
    for race in races:
        race_games = evaluation_games // 3
        race_wins = random.randint(20, race_games)
        matchup_results[f"vs_{race}"] = {
            "games": race_games,
            "wins": race_wins,
            "win_rate": round(race_wins / race_games, 3),
        }

    result = {
        "checkpoint_path": checkpoint,
        "total_games": evaluation_games,
        "wins": wins,
        "win_rate": round(win_rate, 4),
        "matchup_results": matchup_results,
        "avg_game_duration_s": random.randint(180, 600),
        "avg_apm": random.randint(120, 300),
        "evaluation_ts": datetime.utcnow().isoformat(),
    }
    logger.info(
        "Evaluation complete — win_rate=%.4f (%d/%d games)",
        win_rate,
        wins,
        evaluation_games,
    )
    return result


@task
def promote_if_better(eval_result: dict, **context) -> dict:
    """
    Compare new model win rate against production threshold.
    Promotes model to registry if it meets/exceeds min_win_rate.
    """
    min_win_rate = get_param("min_win_rate")
    new_win_rate = eval_result["win_rate"]
    checkpoint = eval_result["checkpoint_path"]
    registry_uri = get_param("model_registry_uri")

    promoted = new_win_rate >= min_win_rate

    if promoted:
        logger.info(
            "Model PROMOTED — win_rate=%.4f >= threshold=%.4f. Pushing to %s",
            new_win_rate,
            min_win_rate,
            registry_uri,
        )
        model_version = f"v{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}"
        promotion_status = "promoted"
    else:
        logger.warning(
            "Model NOT promoted — win_rate=%.4f < threshold=%.4f",
            new_win_rate,
            min_win_rate,
        )
        model_version = None
        promotion_status = "rejected"

    result = {
        "promoted": promoted,
        "promotion_status": promotion_status,
        "new_win_rate": new_win_rate,
        "min_win_rate": min_win_rate,
        "model_version": model_version,
        "checkpoint_path": checkpoint,
        "registry_uri": registry_uri if promoted else None,
    }
    return result


@task
def notify(
    promote_result: dict, eval_result: dict, train_result: dict, **context
) -> str:
    """
    Send pipeline completion notification with summary metrics.
    """
    status = promote_result["promotion_status"].upper()
    win_rate = promote_result["new_win_rate"]
    final_loss = train_result["final_loss"]
    model_version = promote_result.get("model_version", "N/A")
    email = get_param("notification_email")

    matchup_lines = "\n".join(
        f"  vs {race}: {data['wins']}/{data['games']} ({data['win_rate']:.1%})"
        for race, data in eval_result["matchup_results"].items()
    )

    message = (
        f"[SC2 Bot Training Pipeline] Run Complete\n"
        f"{'=' * 50}\n"
        f"Status        : {status}\n"
        f"Win Rate      : {win_rate:.4f} (threshold: {promote_result['min_win_rate']})\n"
        f"Final Loss    : {final_loss:.4f}\n"
        f"Model Version : {model_version}\n"
        f"\nMatchup Breakdown:\n{matchup_lines}\n"
        f"{'=' * 50}\n"
        f"Notification target: {email}\n"
        f"Timestamp: {datetime.utcnow().isoformat()}"
    )
    logger.info("\n%s", message)
    return message


# ---------------------------------------------------------------------------
# DAG definition (TaskFlow API)
# ---------------------------------------------------------------------------


@dag(
    dag_id="sc2_training_pipeline",
    description="Daily SC2 bot PPO training pipeline: replay extraction → feature engineering → training → evaluation → promotion",
    schedule_interval="@daily",
    start_date=days_ago(1),
    catchup=False,
    max_active_runs=1,
    default_args={
        "owner": "sc2bot",
        "retries": 2,
        "retry_delay": timedelta(minutes=5),
        "execution_timeout": timedelta(hours=6),
        "email_on_failure": True,
        "email_on_retry": False,
        "email": [DEFAULT_PARAMS["notification_email"]],
    },
    tags=["sc2", "ml", "ppo", "training"],
    params={
        "timesteps": DEFAULT_PARAMS["timesteps"],
        "learning_rate": DEFAULT_PARAMS["learning_rate"],
        "min_win_rate": DEFAULT_PARAMS["min_win_rate"],
    },
    doc_md="""
    ## SC2 Bot Training Pipeline

    This DAG orchestrates the full ML training lifecycle for the StarCraft II bot:

    1. **extract_replays** — Pull raw `.SC2Replay` files from object storage
    2. **preprocess_features** — Convert replays to feature tensors via feature engineering
    3. **train_ppo** — Train PPO agent using Stable-Baselines3 / custom loop
    4. **evaluate_model** — Run evaluation games against scripted opponents
    5. **promote_if_better** — Register model if win rate >= `min_win_rate`
    6. **notify** — Send Slack/email notification with pipeline summary

    ### Configuration
    Override defaults via Airflow Variables prefixed with `sc2_pipeline_`:
    - `sc2_pipeline_timesteps` (int)
    - `sc2_pipeline_learning_rate` (float)
    - `sc2_pipeline_min_win_rate` (float)
    """,
)
def sc2_training_pipeline():
    # Build task dependency chain with XCom passing
    extract_result = extract_replays()
    preprocess_result = preprocess_features(extract_result)
    train_result = train_ppo(preprocess_result)
    eval_result = evaluate_model(train_result)
    promote_result = promote_if_better(eval_result)
    notify(promote_result, eval_result, train_result)


# Instantiate DAG (required for Airflow to discover it)
pipeline_dag = sc2_training_pipeline()


# ---------------------------------------------------------------------------
# Standalone simulation — runnable without Airflow
# ---------------------------------------------------------------------------


def run_standalone_simulation():
    """
    Execute the pipeline tasks sequentially to simulate the DAG run.
    Demonstrates XCom passing via plain Python dict returns.
    """
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(message)s",
        stream=sys.stdout,
    )
    print("\n" + "=" * 60)
    print("  SC2 Training Pipeline — Standalone Simulation")
    print("  Phase 576: Airflow DAGs Advanced")
    print("=" * 60 + "\n")

    # Task 1: Extract
    print("[STEP 1/6] extract_replays")
    extract_result = extract_replays()
    print(
        f"  -> replay_count={extract_result['replay_count']}, "
        f"ts={extract_result['extraction_ts']}\n"
    )

    # Task 2: Preprocess
    print("[STEP 2/6] preprocess_features")
    preprocess_result = preprocess_features(extract_result)
    print(
        f"  -> valid_samples={preprocess_result['valid_samples']}, "
        f"feature_dim={preprocess_result['feature_dim']}, "
        f"win_dist={preprocess_result['label_distribution']}\n"
    )

    # Task 3: Train
    print("[STEP 3/6] train_ppo")
    train_result = train_ppo(preprocess_result)
    print(
        f"  -> checkpoint={train_result['checkpoint_path']}, "
        f"final_loss={train_result['final_loss']}\n"
    )

    # Task 4: Evaluate
    print("[STEP 4/6] evaluate_model")
    eval_result = evaluate_model(train_result)
    print(
        f"  -> win_rate={eval_result['win_rate']:.4f} "
        f"({eval_result['wins']}/{eval_result['total_games']})\n"
    )

    # Task 5: Promote
    print("[STEP 5/6] promote_if_better")
    promote_result = promote_if_better(eval_result)
    print(
        f"  -> status={promote_result['promotion_status']}, "
        f"version={promote_result['model_version']}\n"
    )

    # Task 6: Notify
    print("[STEP 6/6] notify")
    message = notify(promote_result, eval_result, train_result)

    print("\n" + "=" * 60)
    print("  Simulation complete.")
    print("=" * 60)
    return {
        "extract": extract_result,
        "preprocess": preprocess_result,
        "train": train_result,
        "evaluate": eval_result,
        "promote": promote_result,
        "notification": message,
    }


if __name__ == "__main__":
    run_standalone_simulation()
