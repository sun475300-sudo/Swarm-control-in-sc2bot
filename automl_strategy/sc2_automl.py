# Phase 645: AutoML Pipeline for SC2 Strategy Discovery
# Automatic hyperparameter optimization, neural architecture search, and feature engineering

from __future__ import annotations

import copy
import json
import math
import os
import random
import time
import uuid
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Tuple

try:
    import numpy as np

    NP_AVAILABLE = True
except ImportError:
    NP_AVAILABLE = False

# ============================================================
# NumPy Fallback Utilities
# ============================================================


def _np_mean(values: list) -> float:
    if not values:
        return 0.0
    return sum(values) / len(values)


def _np_std(values: list) -> float:
    if not values:
        return 0.0
    m = _np_mean(values)
    var = sum((v - m) ** 2 for v in values) / max(len(values), 1)
    return math.sqrt(var)


def _np_random_normal(loc: float = 0.0, scale: float = 1.0) -> float:
    """Box-Muller transform fallback."""
    u1 = random.random() or 1e-10
    u2 = random.random()
    z = math.sqrt(-2.0 * math.log(u1)) * math.cos(2.0 * math.pi * u2)
    return loc + scale * z


def _softmax(logits: List[float]) -> List[float]:
    """Numerically stable softmax."""
    max_l = max(logits) if logits else 0.0
    exps = [math.exp(l - max_l) for l in logits]
    total = sum(exps)
    if total == 0:
        return [1.0 / len(logits)] * len(logits)
    return [e / total for e in exps]


def _categorical_sample(probs: List[float]) -> int:
    """Sample from a categorical distribution."""
    r = random.random()
    cumulative = 0.0
    for i, p in enumerate(probs):
        cumulative += p
        if r <= cumulative:
            return i
    return len(probs) - 1


# ============================================================
# SearchSpace
# ============================================================


@dataclass
class HyperParam:
    """A single hyperparameter definition."""

    name: str
    param_type: str  # "float", "int", "categorical", "log_float"
    low: Optional[float] = None
    high: Optional[float] = None
    choices: Optional[List[Any]] = None
    default: Optional[Any] = None

    def sample(self) -> Any:
        if self.param_type == "float":
            return random.uniform(self.low, self.high)
        elif self.param_type == "log_float":
            log_low = math.log(max(self.low, 1e-10))
            log_high = math.log(max(self.high, 1e-10))
            return math.exp(random.uniform(log_low, log_high))
        elif self.param_type == "int":
            return random.randint(int(self.low), int(self.high))
        elif self.param_type == "categorical":
            return random.choice(self.choices)
        return self.default


class SearchSpace:
    """Defines the hyperparameter search space for SC2 strategies."""

    def __init__(self) -> None:
        self.params: Dict[str, HyperParam] = {}

    def add_float(
        self, name: str, low: float, high: float, default: Optional[float] = None
    ) -> None:
        self.params[name] = HyperParam(
            name, "float", low=low, high=high, default=default
        )

    def add_log_float(
        self, name: str, low: float, high: float, default: Optional[float] = None
    ) -> None:
        self.params[name] = HyperParam(
            name, "log_float", low=low, high=high, default=default
        )

    def add_int(
        self, name: str, low: int, high: int, default: Optional[int] = None
    ) -> None:
        self.params[name] = HyperParam(
            name, "int", low=float(low), high=float(high), default=default
        )

    def add_categorical(
        self, name: str, choices: List[Any], default: Optional[Any] = None
    ) -> None:
        self.params[name] = HyperParam(
            name, "categorical", choices=choices, default=default
        )

    def sample_config(self) -> Dict[str, Any]:
        return {name: param.sample() for name, param in self.params.items()}

    def default_config(self) -> Dict[str, Any]:
        return {name: param.default for name, param in self.params.items()}

    def dimensionality(self) -> int:
        return len(self.params)

    @staticmethod
    def sc2_build_order_space() -> "SearchSpace":
        """Predefined search space for SC2 build order parameters."""
        space = SearchSpace()
        space.add_int("first_pool_supply", low=12, high=18, default=14)
        space.add_int("first_gas_supply", low=12, high=20, default=16)
        space.add_int("expand_supply", low=16, high=30, default=20)
        space.add_float("drone_ratio", low=0.3, high=0.8, default=0.6)
        space.add_float("aggression_timing", low=3.0, high=8.0, default=5.0)
        space.add_categorical(
            "opening_style",
            choices=["rush", "macro", "timing", "cheese"],
            default="macro",
        )
        space.add_categorical(
            "tech_path",
            choices=["ling_bane", "roach_ravager", "muta", "hydra"],
            default="roach_ravager",
        )
        space.add_log_float("learning_rate", low=1e-5, high=1e-2, default=1e-3)
        space.add_int("batch_size", low=16, high=256, default=64)
        space.add_float("gamma", low=0.9, high=0.999, default=0.99)
        return space

    @staticmethod
    def sc2_unit_composition_space() -> "SearchSpace":
        """Search space for unit composition ratios."""
        space = SearchSpace()
        space.add_float("zergling_ratio", low=0.0, high=1.0, default=0.3)
        space.add_float("baneling_ratio", low=0.0, high=0.5, default=0.15)
        space.add_float("roach_ratio", low=0.0, high=0.8, default=0.3)
        space.add_float("ravager_ratio", low=0.0, high=0.4, default=0.1)
        space.add_float("hydralisk_ratio", low=0.0, high=0.6, default=0.15)
        space.add_int("max_queens", low=2, high=10, default=5)
        space.add_float("overlord_buffer", low=1.0, high=4.0, default=2.0)
        return space


# ============================================================
# TrialRunner
# ============================================================


@dataclass
class Trial:
    """A single trial evaluation."""

    trial_id: str = field(default_factory=lambda: uuid.uuid4().hex[:8])
    config: Dict[str, Any] = field(default_factory=dict)
    score: float = 0.0
    metrics: Dict[str, float] = field(default_factory=dict)
    status: str = "pending"  # pending, running, completed, pruned
    start_time: float = 0.0
    end_time: float = 0.0
    intermediate_values: List[float] = field(default_factory=list)

    @property
    def duration(self) -> float:
        if self.end_time > 0:
            return self.end_time - self.start_time
        return 0.0

    def to_dict(self) -> Dict[str, Any]:
        return {
            "trial_id": self.trial_id,
            "config": self.config,
            "score": round(self.score, 6),
            "metrics": {k: round(v, 6) for k, v in self.metrics.items()},
            "status": self.status,
            "duration": round(self.duration, 3),
        }


class TrialRunner:
    """Manages trial execution with early stopping support."""

    def __init__(
        self, max_trials: int = 50, patience: int = 10, min_improvement: float = 0.001
    ):
        self.max_trials = max_trials
        self.patience = patience
        self.min_improvement = min_improvement
        self.trials: List[Trial] = []
        self.best_score: float = -math.inf
        self.best_trial: Optional[Trial] = None
        self.no_improve_count: int = 0

    def run_trial(
        self, config: Dict[str, Any], objective_fn: Callable[[Dict[str, Any]], float]
    ) -> Trial:
        """Execute a single trial with the given config."""
        trial = Trial(config=config)
        trial.status = "running"
        trial.start_time = time.time()
        try:
            score = objective_fn(config)
            trial.score = score
            trial.status = "completed"
        except Exception as e:
            trial.score = -math.inf
            trial.status = "pruned"
            trial.metrics["error"] = str(e)
        trial.end_time = time.time()
        self.trials.append(trial)
        if trial.score > self.best_score + self.min_improvement:
            self.best_score = trial.score
            self.best_trial = trial
            self.no_improve_count = 0
        else:
            self.no_improve_count += 1
        return trial

    def should_stop(self) -> bool:
        """Check early stopping criteria."""
        if len(self.trials) >= self.max_trials:
            return True
        if self.no_improve_count >= self.patience:
            return True
        return False

    def median_pruner(self, trial: Trial, step: int) -> bool:
        """Median pruner: prune if intermediate value below median at same step."""
        completed = [
            t
            for t in self.trials
            if t.status == "completed" and len(t.intermediate_values) > step
        ]
        if len(completed) < 5:
            return False
        medians = sorted([t.intermediate_values[step] for t in completed])
        median_val = medians[len(medians) // 2]
        if len(trial.intermediate_values) > step:
            return trial.intermediate_values[step] < median_val
        return False

    def get_top_k(self, k: int = 5) -> List[Trial]:
        """Return top-k trials by score."""
        completed = [t for t in self.trials if t.status == "completed"]
        completed.sort(key=lambda t: t.score, reverse=True)
        return completed[:k]

    def summary(self) -> Dict[str, Any]:
        completed = [t for t in self.trials if t.status == "completed"]
        pruned = [t for t in self.trials if t.status == "pruned"]
        scores = [t.score for t in completed]
        return {
            "total_trials": len(self.trials),
            "completed": len(completed),
            "pruned": len(pruned),
            "best_score": round(self.best_score, 6) if self.best_trial else None,
            "best_config": self.best_trial.config if self.best_trial else None,
            "mean_score": round(_np_mean(scores), 6) if scores else None,
            "std_score": round(_np_std(scores), 6) if scores else None,
        }


# ============================================================
# HPOOptimizer - Bayesian Optimization (TPE)
# ============================================================


class HPOOptimizer:
    """Hyperparameter Optimization with Random Search and TPE-inspired Bayesian Optimization."""

    def __init__(
        self,
        search_space: SearchSpace,
        method: str = "tpe",
        n_startup_trials: int = 10,
        gamma: float = 0.25,
    ):
        self.search_space = search_space
        self.method = method  # "random", "tpe"
        self.n_startup_trials = n_startup_trials
        self.gamma = gamma  # fraction of top trials for TPE l(x) distribution
        self.history: List[Tuple[Dict[str, Any], float]] = []

    def suggest(self) -> Dict[str, Any]:
        """Suggest next config to try."""
        if self.method == "random" or len(self.history) < self.n_startup_trials:
            return self.search_space.sample_config()
        return self._tpe_suggest()

    def _tpe_suggest(self) -> Dict[str, Any]:
        """Tree-structured Parzen Estimator suggestion."""
        sorted_hist = sorted(self.history, key=lambda x: x[1], reverse=True)
        n_good = max(1, int(len(sorted_hist) * self.gamma))
        good_configs = [h[0] for h in sorted_hist[:n_good]]
        bad_configs = [h[0] for h in sorted_hist[n_good:]]
        config: Dict[str, Any] = {}
        for name, param in self.search_space.params.items():
            if param.param_type in ("float", "log_float"):
                good_vals = [c[name] for c in good_configs if name in c]
                if good_vals:
                    mu = _np_mean(good_vals)
                    sigma = max(_np_std(good_vals), 1e-6)
                    # Sample from KDE around good values
                    candidate = _np_random_normal(mu, sigma)
                    lo = (
                        param.low
                        if param.param_type == "float"
                        else math.log(max(param.low, 1e-10))
                    )
                    hi = (
                        param.high
                        if param.param_type == "float"
                        else math.log(max(param.high, 1e-10))
                    )
                    if param.param_type == "log_float":
                        candidate = math.exp(max(lo, min(hi, candidate)))
                    else:
                        candidate = max(param.low, min(param.high, candidate))
                    config[name] = candidate
                else:
                    config[name] = param.sample()
            elif param.param_type == "int":
                good_vals = [c[name] for c in good_configs if name in c]
                if good_vals:
                    mu = _np_mean(good_vals)
                    sigma = max(_np_std(good_vals), 0.5)
                    candidate = int(round(_np_random_normal(mu, sigma)))
                    config[name] = max(int(param.low), min(int(param.high), candidate))
                else:
                    config[name] = param.sample()
            elif param.param_type == "categorical":
                good_vals = [c[name] for c in good_configs if name in c]
                if good_vals and param.choices:
                    counts = {ch: 0 for ch in param.choices}
                    for v in good_vals:
                        if v in counts:
                            counts[v] += 1
                    total = sum(counts.values()) + len(
                        param.choices
                    )  # Laplace smoothing
                    probs = [(counts[ch] + 1) / total for ch in param.choices]
                    idx = _categorical_sample(probs)
                    config[name] = param.choices[idx]
                else:
                    config[name] = param.sample()
        return config

    def report(self, config: Dict[str, Any], score: float) -> None:
        """Report a trial result to update the optimizer."""
        self.history.append((config, score))

    def best_config(self) -> Optional[Dict[str, Any]]:
        if not self.history:
            return None
        return max(self.history, key=lambda x: x[1])[0]

    def best_score(self) -> Optional[float]:
        if not self.history:
            return None
        return max(self.history, key=lambda x: x[1])[1]


# ============================================================
# NASController - Neural Architecture Search
# ============================================================


@dataclass
class Architecture:
    """Describes a neural network architecture."""

    arch_id: str = field(default_factory=lambda: uuid.uuid4().hex[:8])
    layers: List[Dict[str, Any]] = field(default_factory=list)
    score: float = 0.0

    def to_dict(self) -> Dict[str, Any]:
        return {
            "arch_id": self.arch_id,
            "layers": self.layers,
            "score": round(self.score, 6),
        }

    def param_count_estimate(self) -> int:
        """Rough parameter count estimate."""
        total = 0
        prev_size = 0
        for layer in self.layers:
            size = layer.get("units", layer.get("filters", 64))
            if prev_size > 0:
                total += prev_size * size + size  # weights + bias
            prev_size = size
        return total


class NASController:
    """Controller RNN (simplified) for Neural Architecture Search."""

    LAYER_TYPES = ["dense", "conv1d", "lstm", "attention", "skip_connection"]
    ACTIVATIONS = ["relu", "tanh", "elu", "swish", "gelu"]
    UNIT_OPTIONS = [32, 64, 128, 256, 512]

    def __init__(self, max_layers: int = 8, temperature: float = 1.0):
        self.max_layers = max_layers
        self.temperature = temperature
        # Controller parameters (simplified as logits)
        self.layer_type_logits = [0.0] * len(self.LAYER_TYPES)
        self.activation_logits = [0.0] * len(self.ACTIVATIONS)
        self.unit_logits = [0.0] * len(self.UNIT_OPTIONS)
        self.depth_logits = [0.0] * max_layers
        self.architecture_history: List[Architecture] = []
        self.learning_rate: float = 0.01
        self.baseline_reward: float = 0.0

    def sample_architecture(self) -> Architecture:
        """Sample a network architecture from the controller distribution."""
        # Sample depth
        depth_probs = _softmax([l / self.temperature for l in self.depth_logits])
        num_layers = _categorical_sample(depth_probs) + 1
        layers = []
        for i in range(num_layers):
            type_probs = _softmax(
                [l / self.temperature for l in self.layer_type_logits]
            )
            act_probs = _softmax([l / self.temperature for l in self.activation_logits])
            unit_probs = _softmax([l / self.temperature for l in self.unit_logits])
            layer_type = self.LAYER_TYPES[_categorical_sample(type_probs)]
            activation = self.ACTIVATIONS[_categorical_sample(act_probs)]
            units = self.UNIT_OPTIONS[_categorical_sample(unit_probs)]
            layers.append(
                {
                    "layer_idx": i,
                    "type": layer_type,
                    "activation": activation,
                    "units": units,
                    "dropout": round(random.uniform(0.0, 0.5), 2),
                }
            )
        arch = Architecture(layers=layers)
        return arch

    def update_controller(self, architecture: Architecture, reward: float) -> None:
        """REINFORCE update on controller parameters."""
        advantage = reward - self.baseline_reward
        self.baseline_reward = 0.95 * self.baseline_reward + 0.05 * reward
        lr = self.learning_rate
        # Update depth logits
        depth_idx = min(len(architecture.layers) - 1, self.max_layers - 1)
        self.depth_logits[depth_idx] += lr * advantage
        # Update layer-type, activation, and unit logits based on chosen architecture
        for layer in architecture.layers:
            lt = layer["type"]
            if lt in self.LAYER_TYPES:
                idx = self.LAYER_TYPES.index(lt)
                self.layer_type_logits[idx] += lr * advantage
            act = layer["activation"]
            if act in self.ACTIVATIONS:
                idx = self.ACTIVATIONS.index(act)
                self.activation_logits[idx] += lr * advantage
            units = layer["units"]
            if units in self.UNIT_OPTIONS:
                idx = self.UNIT_OPTIONS.index(units)
                self.unit_logits[idx] += lr * advantage
        self.architecture_history.append(architecture)

    def best_architecture(self) -> Optional[Architecture]:
        if not self.architecture_history:
            return None
        return max(self.architecture_history, key=lambda a: a.score)

    def controller_distribution(self) -> Dict[str, Any]:
        """Return current controller probability distributions."""
        return {
            "layer_types": dict(
                zip(self.LAYER_TYPES, _softmax(self.layer_type_logits))
            ),
            "activations": dict(
                zip(self.ACTIVATIONS, _softmax(self.activation_logits))
            ),
            "units": dict(zip(self.UNIT_OPTIONS, _softmax(self.unit_logits))),
            "depth": {i + 1: p for i, p in enumerate(_softmax(self.depth_logits))},
        }


# ============================================================
# Feature Engineering
# ============================================================


class SC2FeatureEngineer:
    """Auto-generate and select features from SC2 game state."""

    BASIC_FEATURES = [
        "minerals",
        "vespene",
        "supply_used",
        "supply_cap",
        "worker_count",
        "army_supply",
        "tech_level",
    ]

    DERIVED_FEATURES = [
        "mineral_rate",
        "vespene_rate",
        "supply_ratio",
        "army_worker_ratio",
        "mineral_per_worker",
        "time_since_last_expand",
        "bases_count",
    ]

    TEMPORAL_FEATURES = [
        "mineral_delta_30s",
        "army_delta_30s",
        "supply_delta_60s",
        "tech_progress_rate",
    ]

    def __init__(self) -> None:
        self.selected_features: List[str] = []
        self.feature_importances: Dict[str, float] = {}

    def generate_all_features(self, game_state: Dict[str, float]) -> Dict[str, float]:
        """Generate all possible features from a game state snapshot."""
        features: Dict[str, float] = {}
        # Basic features
        for f in self.BASIC_FEATURES:
            features[f] = game_state.get(f, 0.0)
        # Derived features
        workers = game_state.get("worker_count", 1)
        minerals = game_state.get("minerals", 0)
        supply_used = game_state.get("supply_used", 0)
        supply_cap = game_state.get("supply_cap", 1)
        army = game_state.get("army_supply", 0)
        features["supply_ratio"] = supply_used / max(supply_cap, 1)
        features["army_worker_ratio"] = army / max(workers, 1)
        features["mineral_per_worker"] = minerals / max(workers, 1)
        # Interaction features (pairwise products of normalized basic features)
        basic_vals = [features.get(f, 0.0) for f in self.BASIC_FEATURES]
        max_vals = [max(abs(v), 1.0) for v in basic_vals]
        normalized = [v / m for v, m in zip(basic_vals, max_vals)]
        for i in range(len(self.BASIC_FEATURES)):
            for j in range(i + 1, len(self.BASIC_FEATURES)):
                fname = f"{self.BASIC_FEATURES[i]}_x_{self.BASIC_FEATURES[j]}"
                features[fname] = round(normalized[i] * normalized[j], 6)
        return features

    def select_top_features(
        self, feature_scores: Dict[str, float], top_k: int = 10
    ) -> List[str]:
        """Select top-k features by importance score."""
        self.feature_importances = feature_scores
        sorted_feats = sorted(feature_scores.items(), key=lambda x: x[1], reverse=True)
        self.selected_features = [f[0] for f in sorted_feats[:top_k]]
        return self.selected_features

    def auto_importance(
        self, game_states: List[Dict[str, float]], outcomes: List[float]
    ) -> Dict[str, float]:
        """Estimate feature importance via correlation with outcomes."""
        if not game_states or not outcomes:
            return {}
        all_features = [self.generate_all_features(gs) for gs in game_states]
        feature_names = list(all_features[0].keys())
        importances: Dict[str, float] = {}
        outcome_mean = _np_mean(outcomes)
        outcome_std = _np_std(outcomes) or 1.0
        for fname in feature_names:
            vals = [f.get(fname, 0.0) for f in all_features]
            val_mean = _np_mean(vals)
            val_std = _np_std(vals) or 1.0
            # Pearson correlation
            cov = _np_mean(
                [(v - val_mean) * (o - outcome_mean) for v, o in zip(vals, outcomes)]
            )
            corr = cov / (val_std * outcome_std)
            importances[fname] = round(abs(corr), 6)
        return importances


# ============================================================
# AutoMLPipeline
# ============================================================


class AutoMLPipeline:
    """End-to-end AutoML pipeline for SC2 strategy discovery."""

    MODEL_TYPES = [
        "linear",
        "decision_tree",
        "random_forest",
        "neural_net",
        "gradient_boost",
    ]

    def __init__(
        self,
        search_space: Optional[SearchSpace] = None,
        max_trials: int = 30,
        method: str = "tpe",
    ):
        self.search_space = search_space or SearchSpace.sc2_build_order_space()
        self.optimizer = HPOOptimizer(self.search_space, method=method)
        self.runner = TrialRunner(max_trials=max_trials, patience=10)
        self.nas_controller = NASController(max_layers=6)
        self.feature_engineer = SC2FeatureEngineer()
        self.pipeline_results: List[Dict[str, Any]] = []

    def run_hpo(
        self,
        objective_fn: Callable[[Dict[str, Any]], float],
        n_trials: Optional[int] = None,
    ) -> Dict[str, Any]:
        """Run hyperparameter optimization loop."""
        n = n_trials or self.runner.max_trials
        for i in range(n):
            config = self.optimizer.suggest()
            trial = self.runner.run_trial(config, objective_fn)
            self.optimizer.report(config, trial.score)
            if self.runner.should_stop():
                break
        return self.runner.summary()

    def run_nas(
        self, eval_fn: Callable[[Architecture], float], n_architectures: int = 20
    ) -> Dict[str, Any]:
        """Run neural architecture search."""
        for _ in range(n_architectures):
            arch = self.nas_controller.sample_architecture()
            score = eval_fn(arch)
            arch.score = score
            self.nas_controller.update_controller(arch, score)
        best = self.nas_controller.best_architecture()
        return {
            "architectures_tried": n_architectures,
            "best_architecture": best.to_dict() if best else None,
            "best_score": round(best.score, 6) if best else None,
            "controller_dist": self.nas_controller.controller_distribution(),
        }

    def run_feature_selection(
        self,
        game_states: List[Dict[str, float]],
        outcomes: List[float],
        top_k: int = 10,
    ) -> Dict[str, Any]:
        """Auto feature engineering and selection."""
        importances = self.feature_engineer.auto_importance(game_states, outcomes)
        selected = self.feature_engineer.select_top_features(importances, top_k)
        return {
            "total_features": len(importances),
            "selected_features": selected,
            "top_importances": {f: importances[f] for f in selected},
        }

    def select_best_model(
        self, configs: Optional[List[Dict[str, Any]]] = None
    ) -> Dict[str, Any]:
        """Pipeline selection: evaluate different model types."""
        results = []
        for model_type in self.MODEL_TYPES:
            # Simulate model evaluation (in production: train + validate)
            base_score = {
                "linear": 0.55,
                "decision_tree": 0.58,
                "random_forest": 0.65,
                "neural_net": 0.68,
                "gradient_boost": 0.70,
            }
            score = base_score.get(model_type, 0.5) + random.gauss(0, 0.05)
            results.append({"model_type": model_type, "score": round(score, 6)})
        results.sort(key=lambda x: x["score"], reverse=True)
        return {
            "best_model": results[0]["model_type"],
            "best_score": results[0]["score"],
            "all_results": results,
        }

    def full_pipeline(
        self,
        objective_fn: Optional[Callable] = None,
        n_hpo_trials: int = 20,
        n_nas_trials: int = 10,
    ) -> Dict[str, Any]:
        """Run the complete AutoML pipeline."""
        if objective_fn is None:

            def objective_fn(config: Dict[str, Any]) -> float:
                # Simulated SC2 win rate based on config
                score = 0.5
                if "drone_ratio" in config:
                    score += (config["drone_ratio"] - 0.5) * 0.2
                if "aggression_timing" in config:
                    score += (6.0 - abs(config["aggression_timing"] - 5.5)) * 0.02
                if "learning_rate" in config:
                    lr = config["learning_rate"]
                    score += 0.1 * (1.0 - abs(math.log10(lr) + 3) / 2.0)
                score += random.gauss(0, 0.03)
                return max(0.0, min(1.0, score))

        # Step 1: HPO
        hpo_result = self.run_hpo(objective_fn, n_hpo_trials)

        # Step 2: NAS
        def nas_eval(arch: Architecture) -> float:
            depth = len(arch.layers)
            params = arch.param_count_estimate()
            score = 0.6 + 0.05 * min(depth, 4) - 0.00001 * max(params - 50000, 0)
            score += random.gauss(0, 0.03)
            return max(0.0, min(1.0, score))

        nas_result = self.run_nas(nas_eval, n_nas_trials)

        # Step 3: Feature Selection
        game_states = []
        outcomes = []
        for _ in range(50):
            gs = {
                "minerals": random.uniform(0, 5000),
                "vespene": random.uniform(0, 3000),
                "supply_used": random.uniform(10, 200),
                "supply_cap": random.uniform(20, 200),
                "worker_count": random.uniform(10, 80),
                "army_supply": random.uniform(0, 150),
                "tech_level": random.uniform(1, 3),
            }
            game_states.append(gs)
            outcome = (
                0.3
                + 0.005 * gs["army_supply"]
                - 0.001 * gs["minerals"]
                + random.gauss(0, 0.1)
            )
            outcomes.append(max(0.0, min(1.0, outcome)))
        feat_result = self.run_feature_selection(game_states, outcomes, top_k=8)

        # Step 4: Model Selection
        model_result = self.select_best_model()

        pipeline_output = {
            "hpo": hpo_result,
            "nas": nas_result,
            "features": feat_result,
            "model_selection": model_result,
        }
        self.pipeline_results.append(pipeline_output)
        return pipeline_output


# ============================================================
# Demo
# ============================================================


def demo() -> None:
    """Demonstrate the AutoML pipeline for SC2 strategy discovery."""
    print("=" * 70)
    print("Phase 645: AutoML Pipeline for SC2 Strategy Discovery")
    print("=" * 70)

    # --- Search Space ---
    print("\n[1] Search Space Definition")
    space = SearchSpace.sc2_build_order_space()
    print(f"    Dimensions: {space.dimensionality()}")
    sample = space.sample_config()
    for k, v in list(sample.items())[:5]:
        display_v = f"{v:.4f}" if isinstance(v, float) else str(v)
        print(f"    {k}: {display_v}")

    # --- HPO with TPE ---
    print("\n[2] Hyperparameter Optimization (TPE)")
    pipeline = AutoMLPipeline(search_space=space, max_trials=30, method="tpe")

    def sc2_objective(config: Dict[str, Any]) -> float:
        score = 0.5
        if "drone_ratio" in config:
            score += (config["drone_ratio"] - 0.4) * 0.15
        if "aggression_timing" in config:
            score -= abs(config["aggression_timing"] - 5.0) * 0.02
        score += random.gauss(0, 0.02)
        return max(0.0, min(1.0, score))

    hpo_result = pipeline.run_hpo(sc2_objective, n_trials=25)
    print(f"    Trials completed: {hpo_result['completed']}")
    print(f"    Best score: {hpo_result['best_score']}")
    if hpo_result["best_config"]:
        for k, v in list(hpo_result["best_config"].items())[:4]:
            display_v = f"{v:.4f}" if isinstance(v, float) else str(v)
            print(f"    Best {k}: {display_v}")

    # --- NAS ---
    print("\n[3] Neural Architecture Search")

    def nas_eval(arch: Architecture) -> float:
        depth = len(arch.layers)
        params = arch.param_count_estimate()
        return max(
            0.0,
            min(
                1.0,
                0.5
                + 0.06 * min(depth, 5)
                - 0.00002 * max(params - 30000, 0)
                + random.gauss(0, 0.03),
            ),
        )

    # Reset NAS controller for demo
    pipeline.nas_controller = NASController(max_layers=6)
    nas_result = pipeline.run_nas(nas_eval, n_architectures=15)
    print(f"    Architectures evaluated: {nas_result['architectures_tried']}")
    if nas_result["best_architecture"]:
        best_arch = nas_result["best_architecture"]
        print(f"    Best score: {nas_result['best_score']}")
        print(f"    Best arch layers: {len(best_arch['layers'])}")
        for layer in best_arch["layers"][:3]:
            print(f"      -> {layer['type']}({layer['units']}, {layer['activation']})")

    # --- Feature Engineering ---
    print("\n[4] Auto Feature Engineering")
    game_states = []
    outcomes = []
    for _ in range(60):
        gs = {
            "minerals": random.uniform(100, 4000),
            "vespene": random.uniform(0, 2500),
            "supply_used": random.uniform(20, 180),
            "supply_cap": random.uniform(30, 200),
            "worker_count": random.uniform(15, 75),
            "army_supply": random.uniform(5, 120),
            "tech_level": random.uniform(1, 3),
        }
        game_states.append(gs)
        outcome = (
            0.3
            + 0.004 * gs["army_supply"]
            - 0.0005 * gs["minerals"]
            + random.gauss(0, 0.08)
        )
        outcomes.append(max(0.0, min(1.0, outcome)))
    feat_result = pipeline.run_feature_selection(game_states, outcomes, top_k=6)
    print(f"    Total features generated: {feat_result['total_features']}")
    print(f"    Selected top features:")
    for fname in feat_result["selected_features"][:6]:
        imp = feat_result["top_importances"][fname]
        print(f"      {fname}: importance={imp:.4f}")

    # --- Model Selection ---
    print("\n[5] Model Selection")
    model_result = pipeline.select_best_model()
    print(f"    Best model type: {model_result['best_model']}")
    print(f"    Best model score: {model_result['best_score']:.4f}")
    for r in model_result["all_results"]:
        print(f"      {r['model_type']}: {r['score']:.4f}")

    # --- Unit Composition Space ---
    print("\n[6] Unit Composition Optimization")
    unit_space = SearchSpace.sc2_unit_composition_space()
    print(f"    Unit comp dimensions: {unit_space.dimensionality()}")
    unit_sample = unit_space.sample_config()
    for k, v in unit_sample.items():
        print(f"    {k}: {v:.3f}" if isinstance(v, float) else f"    {k}: {v}")

    # --- Full Pipeline Summary ---
    print("\n[7] Controller Distribution After NAS")
    dist = pipeline.nas_controller.controller_distribution()
    print("    Layer type preferences:")
    for lt, prob in sorted(
        dist["layer_types"].items(), key=lambda x: x[1], reverse=True
    ):
        print(f"      {lt}: {prob:.3f}")

    print("\n" + "=" * 70)
    print("Phase 645 demo complete.")
    print("=" * 70)


if __name__ == "__main__":
    demo()

# Phase 645: AutoML registered
