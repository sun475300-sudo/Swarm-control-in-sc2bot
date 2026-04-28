"""
Phase 448: Temporal - SC2 Training Pipeline Workflow Orchestration
Durable workflows with activities, retries, timeouts, and saga pattern.
"""

import asyncio
import logging
from dataclasses import dataclass
from datetime import timedelta

from temporalio import activity, workflow
from temporalio.client import Client
from temporalio.common import RetryPolicy
from temporalio.exceptions import ApplicationError
from temporalio.worker import Worker

logger = logging.getLogger(__name__)

TEMPORAL_HOST = "localhost:7233"
TASK_QUEUE = "sc2-training-queue"


@dataclass
class TrainingConfig:
    model_name: str
    replay_source: str
    epochs: int
    batch_size: int
    target_mmr: int


@dataclass
class TrainingResult:
    model_version: str
    win_rate: float
    mmr_achieved: int
    deployed: bool


# ---- Activities ----


@activity.defn
async def collect_replays(source: str) -> list[str]:
    """Collect replay files from storage."""
    logger.info(f"Collecting replays from {source}")
    await asyncio.sleep(0.1)  # Simulate I/O
    return [f"replay_{i}.SC2Replay" for i in range(50)]


@activity.defn
async def process_features(replays: list[str]) -> str:
    """Extract features from replays, return dataset path."""
    logger.info(f"Processing {len(replays)} replays into features")
    await asyncio.sleep(0.1)
    return "/data/features/sc2_features_latest.parquet"


@activity.defn
async def train_model(config: TrainingConfig, dataset_path: str) -> str:
    """Train SC2 bot model, return model artifact path."""
    logger.info(f"Training {config.model_name} for {config.epochs} epochs")
    await asyncio.sleep(0.2)
    return f"/models/{config.model_name}_v{1}.pt"


@activity.defn
async def evaluate_model(model_path: str, target_mmr: int) -> TrainingResult:
    """Evaluate model against ladder, return metrics."""
    logger.info(f"Evaluating model at {model_path}")
    await asyncio.sleep(0.1)
    return TrainingResult(
        model_version="v1",
        win_rate=0.62,
        mmr_achieved=4350,
        deployed=False,
    )


@activity.defn
async def deploy_model(model_path: str, result: TrainingResult) -> bool:
    """Deploy model to production bot."""
    if result.win_rate < 0.55:
        raise ApplicationError("Win rate too low for deployment", non_retryable=True)
    logger.info(
        f"Deploying model {result.model_version} (win_rate={result.win_rate:.2f})"
    )
    return True


@activity.defn
async def rollback_deployment(model_version: str):
    """Saga compensation: rollback failed deployment."""
    logger.warning(f"Rolling back deployment of {model_version}")
    await asyncio.sleep(0.05)


# ---- Workflow ----


@workflow.defn
class SC2TrainingWorkflow:
    """Durable training pipeline with saga pattern for rollback."""

    @workflow.run
    async def run(self, config: TrainingConfig) -> TrainingResult:
        retry_policy = RetryPolicy(
            initial_interval=timedelta(seconds=5),
            maximum_interval=timedelta(minutes=5),
            maximum_attempts=3,
        )

        replays = await workflow.execute_activity(
            collect_replays,
            config.replay_source,
            start_to_close_timeout=timedelta(minutes=10),
            retry_policy=retry_policy,
        )

        dataset_path = await workflow.execute_activity(
            process_features,
            replays,
            start_to_close_timeout=timedelta(hours=2),
            retry_policy=retry_policy,
        )

        model_path = await workflow.execute_activity(
            train_model,
            args=[config, dataset_path],
            start_to_close_timeout=timedelta(hours=6),
            retry_policy=retry_policy,
        )

        result = await workflow.execute_activity(
            evaluate_model,
            args=[model_path, config.target_mmr],
            start_to_close_timeout=timedelta(minutes=30),
            retry_policy=retry_policy,
        )

        # Saga pattern: compensate on failure
        try:
            deployed = await workflow.execute_activity(
                deploy_model,
                args=[model_path, result],
                start_to_close_timeout=timedelta(minutes=5),
            )
            result.deployed = deployed
        except Exception as e:
            await workflow.execute_activity(
                rollback_deployment,
                result.model_version,
                start_to_close_timeout=timedelta(minutes=2),
            )
            raise

        return result


async def run_worker():
    """Start Temporal worker for SC2 training queue."""
    client = await Client.connect(TEMPORAL_HOST)
    worker = Worker(
        client,
        task_queue=TASK_QUEUE,
        workflows=[SC2TrainingWorkflow],
        activities=[
            collect_replays,
            process_features,
            train_model,
            evaluate_model,
            deploy_model,
            rollback_deployment,
        ],
    )
    logger.info(f"Worker started on {TASK_QUEUE}")
    await worker.run()


async def start_training(config: TrainingConfig) -> TrainingResult:
    """Start a training workflow execution."""
    client = await Client.connect(TEMPORAL_HOST)
    result = await client.execute_workflow(
        SC2TrainingWorkflow.run,
        config,
        id=f"sc2-training-{config.model_name}",
        task_queue=TASK_QUEUE,
    )
    return result


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    config = TrainingConfig(
        model_name="zerg_bot_v2",
        replay_source="s3://sc2-replays/",
        epochs=50,
        batch_size=256,
        target_mmr=4500,
    )
    print("SC2 Temporal workflow defined.")
    print("Config:", config)
