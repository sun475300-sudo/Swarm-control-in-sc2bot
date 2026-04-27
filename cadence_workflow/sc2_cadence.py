"""
Phase 450: Uber Cadence - SC2 Long-Running Process Workflows
Multi-day training sessions with signals, child workflows, and saga support.
"""

import asyncio
import logging
from dataclasses import dataclass
from cadence.workflow import workflow_method, signal_method, query_method, Workflow
from cadence.activity import activity_method, Activity
from cadence.workerfactory import WorkerFactory
from cadence.cadence_types import WorkflowIdReusePolicy
import cadence

logger = logging.getLogger(__name__)

DOMAIN = "sc2bot"
TASK_LIST = "sc2-training-tasks"
CADENCE_HOST = "localhost:7933"


@dataclass
class TrainingProgress:
    epoch: int
    total_epochs: int
    current_win_rate: float
    paused: bool = False


# ---- Activity Interface ----


class SC2TrainingActivities:
    @activity_method(task_list=TASK_LIST, schedule_to_close_timeout_seconds=3600 * 48)
    async def run_training_epoch(self, epoch: int, config: dict) -> dict:
        """Run a single training epoch (may take hours)."""
        ...

    @activity_method(task_list=TASK_LIST, schedule_to_close_timeout_seconds=1800)
    async def collect_replay_batch(self, batch_id: int) -> list:
        """Collect a batch of replays for training."""
        ...

    @activity_method(task_list=TASK_LIST, schedule_to_close_timeout_seconds=600)
    async def evaluate_checkpoint(self, checkpoint_path: str) -> float:
        """Evaluate a model checkpoint and return win rate."""
        ...

    @activity_method(task_list=TASK_LIST, schedule_to_close_timeout_seconds=300)
    async def save_checkpoint(self, epoch: int, metrics: dict) -> str:
        """Save model checkpoint, return path."""
        ...


# ---- Child Workflows ----


class DataCollectionWorkflow:
    @workflow_method(
        task_list=TASK_LIST, execution_start_to_close_timeout_seconds=3600 * 24
    )
    async def run(self, num_batches: int) -> list:
        """Child workflow: collect replay data over extended period."""
        ...


class ModelOptimizationWorkflow:
    @workflow_method(
        task_list=TASK_LIST, execution_start_to_close_timeout_seconds=3600 * 72
    )
    async def run(self, config: dict) -> dict:
        """Child workflow: optimize model hyperparameters."""
        ...


# ---- Main Training Workflow ----


class SC2LongTrainingWorkflow:
    def __init__(self):
        self._paused = False
        self._progress = TrainingProgress(
            epoch=0, total_epochs=100, current_win_rate=0.0
        )

    @signal_method
    def pause_training(self):
        """Signal: pause training between epochs."""
        logger.info("Training pause signal received.")
        self._paused = True

    @signal_method
    def resume_training(self):
        """Signal: resume paused training."""
        logger.info("Training resume signal received.")
        self._paused = False

    @query_method
    def get_progress(self) -> TrainingProgress:
        """Query: return current training progress."""
        return self._progress

    @workflow_method(
        task_list=TASK_LIST,
        execution_start_to_close_timeout_seconds=3600 * 24 * 7,  # 7 days max
    )
    async def run_training_session(self, config: dict) -> dict:
        """Main long-running training session workflow."""
        total_epochs = config.get("epochs", 100)
        self._progress.total_epochs = total_epochs
        activities: SC2TrainingActivities = Workflow.new_activity_stub(
            SC2TrainingActivities
        )

        # Spawn child workflow for data collection
        data_wf: DataCollectionWorkflow = Workflow.new_child_workflow(
            DataCollectionWorkflow
        )
        replay_data = await data_wf.run(num_batches=10)
        logger.info(f"Data collection complete: {len(replay_data)} batches")

        best_win_rate = 0.0
        best_checkpoint = ""

        for epoch in range(total_epochs):
            # Wait while paused
            while self._paused:
                await Workflow.sleep(30)

            metrics = await activities.run_training_epoch(epoch, config)
            checkpoint = await activities.save_checkpoint(epoch, metrics)
            win_rate = await activities.evaluate_checkpoint(checkpoint)

            self._progress = TrainingProgress(
                epoch=epoch + 1,
                total_epochs=total_epochs,
                current_win_rate=win_rate,
                paused=self._paused,
            )

            if win_rate > best_win_rate:
                best_win_rate = win_rate
                best_checkpoint = checkpoint
                logger.info(f"Epoch {epoch}: new best win rate {win_rate:.3f}")

        return {
            "best_win_rate": best_win_rate,
            "best_checkpoint": best_checkpoint,
            "epochs_completed": total_epochs,
        }


def start_worker():
    """Start Cadence worker for SC2 training domain."""
    factory = WorkerFactory(CADENCE_HOST, DOMAIN)
    worker = factory.new_worker(TASK_LIST)
    worker.register_workflow_implementation_type(SC2LongTrainingWorkflow)
    factory.start()
    logger.info(f"Cadence worker started on domain={DOMAIN}, task_list={TASK_LIST}")
    return factory


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    print("SC2 Cadence long-running workflow defined.")
    print(f"Domain: {DOMAIN}, Task List: {TASK_LIST}")
    print("Signals: pause_training, resume_training")
    print("Query: get_progress")
    print("Child workflows: DataCollectionWorkflow, ModelOptimizationWorkflow")
