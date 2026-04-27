# Phase 575: MLflow Tracking — SC2 Bot Experiment Tracker
# StarCraft II Commander Bot — tracks RL training experiments, hyperparameters,
# metrics, model artifacts, and game results using MLflow.
# Falls back gracefully to a console/file sink when MLflow is not installed.

from __future__ import annotations

import json
import logging
import math
import os
import random
import tempfile
import threading
import time
from contextlib import contextmanager
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from enum import Enum
from pathlib import Path
from typing import Any, Dict, Generator, List, Optional, Tuple, Union

logger = logging.getLogger(__name__)

# ──────────────────────────────────────────────
# Optional MLflow dependency
# ──────────────────────────────────────────────
try:
    import mlflow
    import mlflow.pyfunc
    from mlflow.exceptions import MlflowException
    from mlflow.models import infer_signature
    from mlflow.tracking import MlflowClient

    _MLFLOW_AVAILABLE = True
except ImportError:
    _MLFLOW_AVAILABLE = False
    logger.warning(
        "mlflow not installed — using console/file fallback. "
        "Install with: pip install mlflow"
    )


# ──────────────────────────────────────────────
# Enums & constants
# ──────────────────────────────────────────────
class GameResult(str, Enum):
    WIN = "win"
    LOSS = "loss"
    TIE = "tie"
    CRASH = "crash"


class Race(str, Enum):
    TERRAN = "terran"
    ZERG = "zerg"
    PROTOSS = "protoss"


class ModelStage(str, Enum):
    NONE = "None"
    STAGING = "Staging"
    PRODUCTION = "Production"
    ARCHIVED = "Archived"


DEFAULT_EXPERIMENT = "sc2bot-rl-training"
DEFAULT_MODEL_NAME = "sc2bot-policy"
TRACKING_URI_ENV = "MLFLOW_TRACKING_URI"


# ──────────────────────────────────────────────
# Dataclasses
# ──────────────────────────────────────────────
@dataclass
class TrainingHyperparams:
    """Hyperparameters for a PPO/IMPALA-style RL training run."""

    algorithm: str = "PPO"
    learning_rate: float = 3e-4
    gamma: float = 0.99
    gae_lambda: float = 0.95
    clip_range: float = 0.2
    clip_range_vf: Optional[float] = None
    value_coef: float = 0.5
    entropy_coef: float = 0.01
    max_grad_norm: float = 0.5
    batch_size: int = 256
    mini_batch_size: int = 64
    n_epochs: int = 4
    n_steps: int = 2048
    total_timesteps: int = 10_000_000
    # Network
    network_arch: str = "resnet"
    hidden_size: int = 512
    n_layers: int = 4
    # SC2-specific
    use_entity_encoder: bool = True
    use_spatial_encoder: bool = True
    spatial_resolution: int = 64
    reward_shaping: str = "sparse+economy"
    map_pool: str = "all-ladder"
    opponent_pool: str = "random-bots"


@dataclass
class TrainingMetrics:
    """Per-step training metrics."""

    step: int
    timestep: int
    policy_loss: float
    value_loss: float
    entropy_loss: float
    approx_kl: float
    clip_fraction: float
    explained_variance: float
    gradient_norm: float
    learning_rate: float
    avg_reward: float
    avg_episode_length: float
    win_rate: float = 0.0


@dataclass
class GameResultRecord:
    """Record of a single SC2 game outcome during evaluation."""

    game_id: str
    bot_race: Race
    opponent_race: Race
    map_name: str
    result: GameResult
    duration_seconds: float
    actions_per_minute: float
    avg_decision_latency_ms: float
    economy_score: float  # normalised mineral/gas efficiency 0-1
    combat_score: float  # kill-loss ratio normalised 0-1


# ──────────────────────────────────────────────
# Fallback: file-based sink
# ──────────────────────────────────────────────
class _FileSink:
    """Write experiment data to local JSONL files when MLflow is absent."""

    def __init__(self, base_dir: Path) -> None:
        self._dir = base_dir
        self._dir.mkdir(parents=True, exist_ok=True)
        self._run_id: Optional[str] = None
        self._params: Dict[str, Any] = {}
        self._metrics: List[Dict] = []

    def start_run(self, run_name: str, tags: Dict) -> str:
        ts = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S")
        self._run_id = f"local-{ts}-{run_name[:16]}"
        run_file = self._dir / f"{self._run_id}.jsonl"
        run_file.write_text(
            json.dumps(
                {
                    "type": "run_start",
                    "run_id": self._run_id,
                    "run_name": run_name,
                    "tags": tags,
                }
            )
            + "\n"
        )
        print(f"[MLflow-STUB] Run started: {self._run_id}")
        return self._run_id

    def log_params(self, params: Dict) -> None:
        self._params.update(params)
        self._append({"type": "params", "params": params})

    def log_metric(self, key: str, value: float, step: int) -> None:
        self._metrics.append({"key": key, "value": value, "step": step})
        self._append({"type": "metric", "key": key, "value": value, "step": step})

    def log_metrics(self, metrics: Dict[str, float], step: int) -> None:
        for k, v in metrics.items():
            self.log_metric(k, v, step)

    def end_run(self, status: str = "FINISHED") -> None:
        self._append({"type": "run_end", "status": status})
        print(f"[MLflow-STUB] Run ended: {self._run_id} ({status})")

    def _append(self, record: Dict) -> None:
        if self._run_id:
            run_file = self._dir / f"{self._run_id}.jsonl"
            with open(run_file, "a") as fh:
                fh.write(json.dumps(record) + "\n")

    def set_tag(self, key: str, value: str) -> None:
        self._append({"type": "tag", "key": key, "value": value})


# ──────────────────────────────────────────────
# Core experiment tracker
# ──────────────────────────────────────────────
class SC2ExperimentTracker:
    """
    MLflow-backed (or fallback) experiment tracker for SC2 RL training.

    Usage
    -----
    >>> tracker = SC2ExperimentTracker.from_env()
    >>> with tracker.start_run("ppo-run-001") as run_id:
    ...     tracker.log_params(hyperparams)
    ...     for step in train():
    ...         tracker.log_training_metrics(metrics)
    ...     tracker.log_game_result(game)
    """

    def __init__(
        self,
        tracking_uri: str = "",
        experiment_name: str = DEFAULT_EXPERIMENT,
        model_name: str = DEFAULT_MODEL_NAME,
        fallback_dir: Optional[Path] = None,
        tags: Optional[Dict[str, str]] = None,
    ) -> None:
        self._experiment_name = experiment_name
        self._model_name = model_name
        self._global_tags = tags or {}
        self._active_run_id: Optional[str] = None
        self._lock = threading.Lock()
        self._game_results: List[GameResultRecord] = []

        if _MLFLOW_AVAILABLE:
            uri = tracking_uri or os.environ.get(TRACKING_URI_ENV, "")
            if uri:
                mlflow.set_tracking_uri(uri)
            try:
                mlflow.set_experiment(experiment_name)
                self._client = MlflowClient()
                self._sink = None
                logger.info(
                    "SC2ExperimentTracker connected to MLflow: %s | experiment: %s",
                    uri or "(local)",
                    experiment_name,
                )
            except Exception as exc:
                logger.warning("MLflow init failed (%s) — using file fallback.", exc)
                self._client = None
                fb_dir = fallback_dir or Path(tempfile.gettempdir()) / "sc2bot_mlflow"
                self._sink = _FileSink(fb_dir)
        else:
            self._client = None
            fb_dir = fallback_dir or Path(tempfile.gettempdir()) / "sc2bot_mlflow"
            self._sink = _FileSink(fb_dir)

    @classmethod
    def from_env(cls) -> "SC2ExperimentTracker":
        return cls(
            tracking_uri=os.environ.get(TRACKING_URI_ENV, ""),
            experiment_name=os.environ.get("MLFLOW_EXPERIMENT", DEFAULT_EXPERIMENT),
            model_name=os.environ.get("MLFLOW_MODEL_NAME", DEFAULT_MODEL_NAME),
        )

    # ── Run lifecycle ──────────────────────────

    @contextmanager
    def start_run(
        self,
        run_name: str,
        tags: Optional[Dict[str, str]] = None,
        nested: bool = False,
    ) -> Generator[str, None, None]:
        """Context manager that starts and ends an MLflow run."""
        merged_tags = {**self._global_tags, **(tags or {})}
        merged_tags.setdefault("bot", "sc2bot")
        merged_tags.setdefault("phase", "575")

        if _MLFLOW_AVAILABLE and self._sink is None:
            with mlflow.start_run(
                run_name=run_name, tags=merged_tags, nested=nested
            ) as run:
                self._active_run_id = run.info.run_id
                logger.info(
                    "MLflow run started: %s (id=%s)", run_name, self._active_run_id
                )
                try:
                    yield self._active_run_id
                except Exception:
                    mlflow.end_run(status="FAILED")
                    raise
                else:
                    mlflow.end_run(status="FINISHED")
                finally:
                    self._active_run_id = None
        else:
            run_id = self._sink.start_run(run_name, merged_tags)
            self._active_run_id = run_id
            try:
                yield run_id
            except Exception:
                self._sink.end_run(status="FAILED")
                raise
            else:
                self._sink.end_run(status="FINISHED")
            finally:
                self._active_run_id = None

    # ── Logging methods ────────────────────────

    def log_params(self, params: Union[TrainingHyperparams, Dict[str, Any]]) -> None:
        """Log hyperparameters (flat dict or TrainingHyperparams dataclass)."""
        if isinstance(params, TrainingHyperparams):
            param_dict = {k: str(v) for k, v in asdict(params).items() if v is not None}
        else:
            param_dict = {k: str(v) for k, v in params.items()}

        if _MLFLOW_AVAILABLE and self._sink is None:
            mlflow.log_params(param_dict)
        else:
            self._sink.log_params(param_dict)

        logger.debug("Logged %d parameters.", len(param_dict))

    def log_training_metrics(self, metrics: TrainingMetrics) -> None:
        """Log a single training step's metrics."""
        metric_dict = {
            "policy_loss": metrics.policy_loss,
            "value_loss": metrics.value_loss,
            "entropy_loss": metrics.entropy_loss,
            "approx_kl": metrics.approx_kl,
            "clip_fraction": metrics.clip_fraction,
            "explained_variance": metrics.explained_variance,
            "gradient_norm": metrics.gradient_norm,
            "learning_rate": metrics.learning_rate,
            "avg_reward": metrics.avg_reward,
            "avg_episode_length": metrics.avg_episode_length,
            "win_rate": metrics.win_rate,
        }
        self._log_metrics(metric_dict, step=metrics.step)

    def log_metrics(self, metrics: Dict[str, float], step: int = 0) -> None:
        """Log an arbitrary dict of float metrics."""
        self._log_metrics(metrics, step=step)

    def _log_metrics(self, metrics: Dict[str, float], step: int) -> None:
        if _MLFLOW_AVAILABLE and self._sink is None:
            mlflow.log_metrics(metrics, step=step)
        else:
            self._sink.log_metrics(metrics, step=step)

    def log_game_result(self, record: GameResultRecord) -> None:
        """Log a single game outcome and accumulate for aggregate reporting."""
        with self._lock:
            self._game_results.append(record)

        game_dict = {
            f"game/{record.game_id}/won": (
                1.0 if record.result == GameResult.WIN else 0.0
            ),
            f"game/{record.game_id}/duration_s": record.duration_seconds,
            f"game/{record.game_id}/apm": record.actions_per_minute,
            f"game/{record.game_id}/latency_ms": record.avg_decision_latency_ms,
            f"game/{record.game_id}/economy_score": record.economy_score,
            f"game/{record.game_id}/combat_score": record.combat_score,
        }

        total = len(self._game_results)
        wins = sum(1 for g in self._game_results if g.result == GameResult.WIN)
        aggregate = {
            "eval/win_rate": wins / max(total, 1),
            "eval/games_played": float(total),
            "eval/avg_apm": sum(g.actions_per_minute for g in self._game_results)
            / max(total, 1),
            "eval/avg_latency_ms": sum(
                g.avg_decision_latency_ms for g in self._game_results
            )
            / max(total, 1),
            "eval/avg_economy_score": sum(g.economy_score for g in self._game_results)
            / max(total, 1),
        }

        self._log_metrics({**game_dict, **aggregate}, step=total)

        if _MLFLOW_AVAILABLE and self._sink is None:
            mlflow.set_tags(
                {
                    f"game.{record.game_id}.result": record.result.value,
                    f"game.{record.game_id}.map": record.map_name,
                }
            )
        else:
            self._sink.set_tag(f"game.{record.game_id}.result", record.result.value)

    def log_model(
        self,
        model: Any,
        artifact_path: str = "policy",
        registered_name: Optional[str] = None,
        pip_requirements: Optional[List[str]] = None,
    ) -> Optional[str]:
        """
        Log a model artifact. Returns the model URI if successful.
        With fallback, saves model metadata to a JSON file.
        """
        reqs = pip_requirements or ["torch>=2.0", "numpy", "python-sc2"]
        reg_name = registered_name or self._model_name

        if _MLFLOW_AVAILABLE and self._sink is None:
            try:
                model_info = mlflow.pyfunc.log_model(
                    artifact_path=artifact_path,
                    python_model=model,
                    pip_requirements=reqs,
                    registered_model_name=reg_name,
                )
                uri = model_info.model_uri
                logger.info("Model logged: %s", uri)
                return uri
            except Exception as exc:
                logger.error("Model logging failed: %s", exc)
                return None
        else:
            stub = {
                "artifact_path": artifact_path,
                "registered_name": reg_name,
                "pip_requirements": reqs,
                "model_type": type(model).__name__,
                "timestamp": datetime.now(timezone.utc).isoformat(),
            }
            stub_file = (
                self._sink._dir / f"model_{artifact_path}_{int(time.time())}.json"
            )
            stub_file.write_text(json.dumps(stub, indent=2))
            logger.info("[MLflow-STUB] Model stub saved: %s", stub_file)
            return str(stub_file)

    def set_tag(self, key: str, value: str) -> None:
        if _MLFLOW_AVAILABLE and self._sink is None:
            mlflow.set_tag(key, value)
        else:
            self._sink.set_tag(key, value)

    def log_artifact(
        self, local_path: str, artifact_path: Optional[str] = None
    ) -> None:
        if _MLFLOW_AVAILABLE and self._sink is None:
            mlflow.log_artifact(local_path, artifact_path)
        else:
            logger.info("[MLflow-STUB] log_artifact(%s)", local_path)

    # ── Model registry ─────────────────────────

    def register_model(
        self,
        model_uri: str,
        name: Optional[str] = None,
        description: Optional[str] = None,
        tags: Optional[Dict[str, str]] = None,
    ) -> Optional[str]:
        """Register a logged model in the MLflow Model Registry."""
        reg_name = name or self._model_name

        if not (_MLFLOW_AVAILABLE and self._client):
            logger.info("[MLflow-STUB] register_model(%s) as '%s'", model_uri, reg_name)
            return None

        try:
            # Ensure registered model exists
            try:
                self._client.create_registered_model(
                    name=reg_name,
                    description=description
                    or f"SC2 Commander Bot policy -- {reg_name}",
                    tags=tags,
                )
            except MlflowException:
                pass  # Already exists

            mv = self._client.create_model_version(
                name=reg_name,
                source=model_uri,
                description=description,
                tags=tags,
            )
            logger.info("Registered model version %s/%s", reg_name, mv.version)
            return mv.version
        except Exception as exc:
            logger.error("Model registration failed: %s", exc)
            return None

    def promote_to_production(
        self,
        version: str,
        name: Optional[str] = None,
        archive_existing: bool = True,
    ) -> bool:
        """
        Promote a model version to Production in the registry.
        Optionally archives the previous production version.
        """
        reg_name = name or self._model_name

        if not (_MLFLOW_AVAILABLE and self._client):
            logger.info(
                "[MLflow-STUB] promote_to_production(%s v%s)", reg_name, version
            )
            return False

        try:
            if archive_existing:
                for mv in self._client.get_latest_versions(
                    name=reg_name, stages=["Production"]
                ):
                    self._client.transition_model_version_stage(
                        name=reg_name,
                        version=mv.version,
                        stage=ModelStage.ARCHIVED.value,
                        archive_existing_versions=False,
                    )
                    logger.info("Archived previous production v%s.", mv.version)

            self._client.transition_model_version_stage(
                name=reg_name,
                version=version,
                stage=ModelStage.PRODUCTION.value,
            )
            logger.info("Promoted %s v%s to Production.", reg_name, version)
            return True
        except Exception as exc:
            logger.error("Promotion failed: %s", exc)
            return False

    def get_production_model_uri(self, name: Optional[str] = None) -> Optional[str]:
        """Return the URI of the current production model."""
        reg_name = name or self._model_name
        if not (_MLFLOW_AVAILABLE and self._client):
            return None
        try:
            versions = self._client.get_latest_versions(
                name=reg_name, stages=["Production"]
            )
            if versions:
                return f"models:/{reg_name}/Production"
            return None
        except Exception:
            return None

    # ── Experiment comparison ──────────────────

    def compare_runs(
        self,
        metric_key: str = "eval/win_rate",
        n_runs: int = 10,
        experiment_name: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        """
        Return the top N runs sorted by a given metric.
        Falls back to returning an empty list if MLflow unavailable.
        """
        exp_name = experiment_name or self._experiment_name

        if not (_MLFLOW_AVAILABLE and self._client):
            logger.info(
                "[MLflow-STUB] compare_runs('%s') -- returning empty list.", metric_key
            )
            return []

        try:
            experiment = self._client.get_experiment_by_name(exp_name)
            if experiment is None:
                return []

            runs = mlflow.search_runs(
                experiment_ids=[experiment.experiment_id],
                order_by=[f"metrics.{metric_key} DESC"],
                max_results=n_runs,
            )
            results = []
            for _, row in runs.iterrows():
                results.append(
                    {
                        "run_id": row.get("run_id"),
                        "run_name": row.get("tags.mlflow.runName", ""),
                        metric_key: row.get(f"metrics.{metric_key}"),
                        "status": row.get("status"),
                        "start_time": row.get("start_time"),
                    }
                )
            return results
        except Exception as exc:
            logger.error("compare_runs failed: %s", exc)
            return []

    def get_best_run(
        self,
        metric_key: str = "eval/win_rate",
        experiment_name: Optional[str] = None,
    ) -> Optional[Dict[str, Any]]:
        """Return the single best run by a given metric."""
        runs = self.compare_runs(
            metric_key=metric_key, n_runs=1, experiment_name=experiment_name
        )
        return runs[0] if runs else None

    # ── Summary helpers ───────────────────────

    def win_rate_summary(self) -> Dict[str, float]:
        """Aggregate win rate stats from logged game results this run."""
        total = len(self._game_results)
        if total == 0:
            return {"games": 0, "wins": 0, "win_rate": 0.0}
        wins = sum(1 for g in self._game_results if g.result == GameResult.WIN)
        by_race: Dict[str, Tuple[int, int]] = {}
        for g in self._game_results:
            key = g.opponent_race.value
            w, n = by_race.get(key, (0, 0))
            by_race[key] = (w + (1 if g.result == GameResult.WIN else 0), n + 1)
        summary: Dict[str, float] = {
            "games": float(total),
            "wins": float(wins),
            "win_rate": wins / total,
        }
        for race, (w, n) in by_race.items():
            summary[f"win_rate_vs_{race}"] = w / n
        return summary


# ──────────────────────────────────────────────
# Simulated training loop
# ──────────────────────────────────────────────
def _simulate_training_run(
    tracker: SC2ExperimentTracker,
    run_name: str,
    num_steps: int = 50,
    num_eval_games: int = 10,
    seed: int = 42,
) -> None:
    """Simulate a complete RL training run with evaluation games."""
    rng = random.Random(seed)

    hp = TrainingHyperparams(
        algorithm="PPO",
        learning_rate=rng.choice([1e-4, 3e-4, 5e-4]),
        gamma=rng.choice([0.99, 0.995]),
        clip_range=rng.choice([0.1, 0.2, 0.3]),
        batch_size=rng.choice([128, 256, 512]),
        entropy_coef=rng.choice([0.005, 0.01, 0.02]),
        hidden_size=512,
        n_layers=4,
        total_timesteps=10_000_000,
        reward_shaping="sparse+economy",
        map_pool="all-ladder",
    )

    print(f"\n  [RUN] {run_name}")
    print(
        f"  lr={hp.learning_rate}, gamma={hp.gamma}, clip={hp.clip_range}, "
        f"batch={hp.batch_size}, entropy={hp.entropy_coef}"
    )

    with tracker.start_run(run_name=run_name, tags={"algorithm": hp.algorithm}):
        tracker.log_params(hp)
        tracker.set_tag("sc2bot.version", "2.4.1")
        tracker.set_tag("sc2bot.race", "zerg")

        # Simulate training steps with realistic convergence curve
        policy_loss = 3.0
        value_loss = 4.5
        entropy = 1.5
        reward = -0.5
        grad_norm = 2.0

        for step in range(num_steps):
            timestep = step * hp.batch_size

            decay = math.exp(-step / (num_steps * 0.7))
            policy_loss = max(0.05, 0.8 * decay + rng.gauss(0, 0.04))
            value_loss = max(0.02, 1.2 * decay + rng.gauss(0, 0.06))
            entropy = max(0.01, 1.5 * decay + rng.gauss(0, 0.03))
            reward = min(0.8, -0.5 + step * 0.025 + rng.gauss(0, 0.1))
            grad_norm = max(0.1, abs(rng.gauss(1.0, 0.4)))
            win_rate = max(0.0, min(1.0, 0.3 + step * 0.01 + rng.gauss(0, 0.05)))
            kl = abs(rng.gauss(0.01, 0.005))
            clip_frac = abs(rng.gauss(0.08, 0.03))
            ev = min(0.99, max(-1.0, 0.3 + step * 0.01 + rng.gauss(0, 0.05)))

            metrics = TrainingMetrics(
                step=step,
                timestep=timestep,
                policy_loss=policy_loss,
                value_loss=value_loss,
                entropy_loss=entropy,
                approx_kl=kl,
                clip_fraction=clip_frac,
                explained_variance=ev,
                gradient_norm=grad_norm,
                learning_rate=hp.learning_rate,
                avg_reward=reward,
                avg_episode_length=rng.gauss(450, 60),
                win_rate=win_rate,
            )
            tracker.log_training_metrics(metrics)

        # Simulate evaluation games
        maps = ["Equilibrium", "Gresvan", "Tropical Sacrifice", "Inside and Out"]
        opp_races = list(Race)
        wins_count = 0

        for i in range(num_eval_games):
            is_win = rng.random() < (0.35 + num_steps * 0.005)
            wins_count += int(is_win)
            game = GameResultRecord(
                game_id=f"eval-{run_name}-{i:04d}",
                bot_race=Race.ZERG,
                opponent_race=rng.choice(opp_races),
                map_name=rng.choice(maps),
                result=GameResult.WIN if is_win else GameResult.LOSS,
                duration_seconds=rng.uniform(200, 1000),
                actions_per_minute=rng.uniform(60, 160),
                avg_decision_latency_ms=rng.uniform(25, 100),
                economy_score=rng.uniform(0.4, 0.9),
                combat_score=rng.uniform(0.3, 0.85),
            )
            tracker.log_game_result(game)

        summary = tracker.win_rate_summary()
        tracker.log_metrics(
            {
                "final/win_rate": summary["win_rate"],
                "final/policy_loss": policy_loss,
                "final/value_loss": value_loss,
            },
            step=num_steps,
        )

        print(
            f"  Win rate: {summary['win_rate']:.1%} ({wins_count}/{num_eval_games} games)"
        )
        print(
            f"  Final losses -- policy={policy_loss:.4f}, value={value_loss:.4f}, "
            f"entropy={entropy:.4f}"
        )


# ──────────────────────────────────────────────
# Demo / standalone entry point
# ──────────────────────────────────────────────
if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="SC2 MLflow Experiment Tracker Demo")
    parser.add_argument("--tracking-uri", default=os.environ.get(TRACKING_URI_ENV, ""))
    parser.add_argument("--experiment", default=DEFAULT_EXPERIMENT)
    parser.add_argument("--model-name", default=DEFAULT_MODEL_NAME)
    parser.add_argument(
        "--runs", type=int, default=3, help="Number of simulated training runs"
    )
    parser.add_argument("--steps", type=int, default=30, help="Training steps per run")
    parser.add_argument(
        "--eval-games", type=int, default=10, help="Evaluation games per run"
    )
    parser.add_argument("--verbose", action="store_true")
    args = parser.parse_args()

    logging.basicConfig(
        level=logging.DEBUG if args.verbose else logging.INFO,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    )

    print("=== SC2 Bot MLflow Experiment Tracker Demo ===")
    print(f"Tracking URI : {args.tracking_uri or '(local ./mlruns)'}")
    print(f"Experiment   : {args.experiment}")
    print(f"Model name   : {args.model_name}")
    if not _MLFLOW_AVAILABLE:
        print("NOTE: mlflow not installed -- using file-based fallback.\n")

    tracker = SC2ExperimentTracker(
        tracking_uri=args.tracking_uri,
        experiment_name=args.experiment,
        model_name=args.model_name,
        tags={"project": "sc2bot", "phase": "575"},
    )

    for run_idx in range(args.runs):
        run_name = f"ppo-zerg-run-{run_idx + 1:03d}"
        _simulate_training_run(
            tracker,
            run_name=run_name,
            num_steps=args.steps,
            num_eval_games=args.eval_games,
            seed=run_idx * 17 + 3,
        )

    # Experiment comparison (real data if MLflow available)
    print("\n=== Experiment Comparison (top runs by eval/win_rate) ===")
    top_runs = tracker.compare_runs(metric_key="eval/win_rate", n_runs=args.runs)
    if top_runs:
        for rank, run in enumerate(top_runs, 1):
            wr = run.get("eval/win_rate") or 0.0
            print(f"  #{rank}  {run['run_name']:<30}  win_rate={wr:.1%}")
    else:
        print("  (No MLflow server -- comparison skipped for fallback mode)")

    best = tracker.get_best_run()
    if best:
        print(
            f"\nBest run: {best.get('run_name')} -- win_rate={best.get('eval/win_rate', 0):.1%}"
        )

    print("\nDone. All runs tracked.")
