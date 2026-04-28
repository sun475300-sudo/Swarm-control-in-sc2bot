# Phase 591: SHAP
"""
sc2_decision_explainer.py — StarCraft II Bot Decision Interpretability with SHAP
Explains ML-driven game decisions (attack / defend / expand) using SHAP values,
providing global and local explanations with visualisation support.

Graceful fallback to a pure-NumPy permutation-importance explainer when
SHAP / scikit-learn / XGBoost are absent.
"""

from __future__ import annotations

import hashlib
import json
import logging
import time
from collections import OrderedDict
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Callable, Dict, List, Optional, Sequence, Tuple, Union

import numpy as np

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
log = logging.getLogger("sc2_decision_explainer")

# ---------------------------------------------------------------------------
# Optional imports — graceful fallback
# ---------------------------------------------------------------------------
try:
    import shap

    SHAP_AVAILABLE = True
    log.info("SHAP %s available.", shap.__version__)
except ImportError:
    SHAP_AVAILABLE = False
    log.warning(
        "SHAP not installed. Running permutation-importance fallback. "
        "Install with: pip install shap"
    )

try:
    from sklearn.ensemble import GradientBoostingClassifier, RandomForestClassifier
    from sklearn.metrics import accuracy_score, classification_report
    from sklearn.model_selection import train_test_split

    SKLEARN_AVAILABLE = True
except ImportError:
    SKLEARN_AVAILABLE = False
    log.warning("scikit-learn not installed. Some model types unavailable.")

try:
    import xgboost as xgb

    XGB_AVAILABLE = True
    log.info("XGBoost %s available.", xgb.__version__)
except ImportError:
    XGB_AVAILABLE = False

try:
    import matplotlib

    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    MPL_AVAILABLE = True
except ImportError:
    MPL_AVAILABLE = False
    log.warning("matplotlib not installed. Plot export disabled.")

# ---------------------------------------------------------------------------
# SC2 feature schema
# ---------------------------------------------------------------------------

SC2_FEATURE_NAMES: List[str] = [
    "minerals",
    "gas",
    "supply_used",
    "supply_cap",
    "worker_count",
    "army_supply",
    "army_value_minerals",
    "army_value_gas",
    "enemy_army_value_estimate",
    "base_count",
    "enemy_base_count",
    "tech_level",  # 0=hatch, 1=lair, 2=hive
    "upgrade_count",
    "production_capacity",  # number of larvae / production buildings
    "map_control_pct",  # 0-1 creep / vision coverage
    "time_seconds",
    "idle_workers",
    "pending_units",
    "enemy_air_threat",  # 0-1 estimated
    "enemy_ground_threat",  # 0-1 estimated
]

NUM_FEATURES = len(SC2_FEATURE_NAMES)


class SC2Decision(Enum):
    """Possible bot macro decisions."""

    ATTACK = 0
    DEFEND = 1
    EXPAND = 2
    TECH_UP = 3
    PRODUCE = 4

    @classmethod
    def from_index(cls, idx: int) -> "SC2Decision":
        for member in cls:
            if member.value == idx:
                return member
        return cls.PRODUCE


DECISION_LABELS = [d.name.lower() for d in SC2Decision]

# ---------------------------------------------------------------------------
# Data classes
# ---------------------------------------------------------------------------


@dataclass
class FeatureExplanation:
    """Explanation for a single feature's contribution to a decision."""

    feature_name: str
    feature_value: float
    shap_value: float
    direction: str  # "positive" or "negative"

    def to_dict(self) -> Dict[str, Any]:
        return {
            "feature": self.feature_name,
            "value": round(self.feature_value, 4),
            "shap_value": round(self.shap_value, 6),
            "direction": self.direction,
        }


@dataclass
class DecisionExplanation:
    """Full explanation for a single game-state decision."""

    game_state: np.ndarray
    predicted_decision: SC2Decision
    predicted_proba: Dict[str, float]
    feature_explanations: List[FeatureExplanation]
    base_value: float
    model_output: float
    timestamp: float = field(default_factory=time.time)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "predicted_decision": self.predicted_decision.name,
            "predicted_proba": {
                k: round(v, 4) for k, v in self.predicted_proba.items()
            },
            "base_value": round(self.base_value, 6),
            "model_output": round(self.model_output, 6),
            "top_features": [fe.to_dict() for fe in self.feature_explanations[:10]],
            "timestamp": self.timestamp,
        }

    def to_json(self, indent: int = 2) -> str:
        return json.dumps(self.to_dict(), indent=indent)

    @property
    def top_positive(self) -> List[FeatureExplanation]:
        return [f for f in self.feature_explanations if f.direction == "positive"][:5]

    @property
    def top_negative(self) -> List[FeatureExplanation]:
        return [f for f in self.feature_explanations if f.direction == "negative"][:5]


@dataclass
class GlobalExplanation:
    """Global feature importance summary across all samples."""

    mean_abs_shap: Dict[str, float]
    feature_ranking: List[str]
    interaction_pairs: List[Tuple[str, str, float]]
    n_samples: int

    def to_dict(self) -> Dict[str, Any]:
        return {
            "feature_ranking": self.feature_ranking,
            "mean_abs_shap": {k: round(v, 6) for k, v in self.mean_abs_shap.items()},
            "top_interactions": [
                {"feature_a": a, "feature_b": b, "strength": round(s, 6)}
                for a, b, s in self.interaction_pairs[:10]
            ],
            "n_samples": self.n_samples,
        }


# ---------------------------------------------------------------------------
# SHAP value cache
# ---------------------------------------------------------------------------


class SHAPCache:
    """LRU cache for SHAP value computations keyed by game-state hash."""

    def __init__(self, max_size: int = 2048):
        self._max_size = max_size
        self._cache: OrderedDict[str, np.ndarray] = OrderedDict()
        self._hits = 0
        self._misses = 0

    def _key(self, game_state: np.ndarray) -> str:
        return hashlib.md5(game_state.tobytes()).hexdigest()

    def get(self, game_state: np.ndarray) -> Optional[np.ndarray]:
        key = self._key(game_state)
        if key in self._cache:
            self._hits += 1
            self._cache.move_to_end(key)
            return self._cache[key]
        self._misses += 1
        return None

    def put(self, game_state: np.ndarray, shap_values: np.ndarray) -> None:
        key = self._key(game_state)
        self._cache[key] = shap_values
        self._cache.move_to_end(key)
        if len(self._cache) > self._max_size:
            self._cache.popitem(last=False)

    def clear(self) -> int:
        count = len(self._cache)
        self._cache.clear()
        self._hits = 0
        self._misses = 0
        return count

    @property
    def stats(self) -> Dict[str, int]:
        total = self._hits + self._misses
        return {
            "size": len(self._cache),
            "max_size": self._max_size,
            "hits": self._hits,
            "misses": self._misses,
            "hit_rate": round(self._hits / total, 4) if total else 0.0,
        }


# ---------------------------------------------------------------------------
# Synthetic data generator
# ---------------------------------------------------------------------------


class SC2DataGenerator:
    """Generate synthetic SC2 game-state data with decision labels for demos."""

    @staticmethod
    def generate(
        n_samples: int = 5000, seed: int = 42
    ) -> Tuple[np.ndarray, np.ndarray]:
        """
        Generate (X, y) where X is game-state features and y is decision label.
        Decision logic:
          - ATTACK if army_value > enemy_estimate * 1.3 and army_supply > 40
          - DEFEND if enemy_army_value_estimate > army_value * 1.2
          - EXPAND if base_count < 4 and minerals > 400 and not under threat
          - TECH_UP if tech_level < 2 and gas > 200
          - PRODUCE otherwise
        """
        rng = np.random.RandomState(seed)
        X = np.zeros((n_samples, NUM_FEATURES), dtype=np.float32)
        y = np.zeros(n_samples, dtype=np.int32)

        for i in range(n_samples):
            minerals = rng.uniform(0, 2000)
            gas = rng.uniform(0, 1500)
            supply_used = rng.uniform(10, 200)
            supply_cap = max(supply_used, rng.uniform(supply_used, 200))
            workers = rng.uniform(10, 80)
            army_supply = max(0, supply_used - workers)
            army_val_min = army_supply * rng.uniform(20, 60)
            army_val_gas = army_supply * rng.uniform(5, 40)
            enemy_val = rng.uniform(500, 8000)
            bases = int(rng.uniform(1, 6))
            enemy_bases = int(rng.uniform(1, 6))
            tech = int(rng.uniform(0, 3))
            upgrades = int(rng.uniform(0, 10))
            prod_cap = rng.uniform(1, 20)
            map_ctrl = rng.uniform(0, 1)
            game_time = rng.uniform(60, 1200)
            idle = int(rng.uniform(0, 10))
            pending = int(rng.uniform(0, 15))
            air_threat = rng.uniform(0, 1)
            ground_threat = rng.uniform(0, 1)

            X[i] = [
                minerals,
                gas,
                supply_used,
                supply_cap,
                workers,
                army_supply,
                army_val_min,
                army_val_gas,
                enemy_val,
                bases,
                enemy_bases,
                tech,
                upgrades,
                prod_cap,
                map_ctrl,
                game_time,
                idle,
                pending,
                air_threat,
                ground_threat,
            ]

            total_army = army_val_min + army_val_gas
            threat = max(air_threat, ground_threat)

            # Decision logic with some noise
            noise = rng.uniform(-0.15, 0.15)
            if total_army > enemy_val * (1.3 + noise) and army_supply > 40:
                y[i] = SC2Decision.ATTACK.value
            elif enemy_val > total_army * (1.2 + noise) or threat > 0.7:
                y[i] = SC2Decision.DEFEND.value
            elif bases < 4 and minerals > 400 and threat < 0.4:
                y[i] = SC2Decision.EXPAND.value
            elif tech < 2 and gas > 200 and threat < 0.5:
                y[i] = SC2Decision.TECH_UP.value
            else:
                y[i] = SC2Decision.PRODUCE.value

        log.info(
            "Generated %d synthetic game states. Class distribution: %s",
            n_samples,
            dict(zip(*np.unique(y, return_counts=True))),
        )
        return X, y


# ---------------------------------------------------------------------------
# Main class — SC2DecisionExplainer
# ---------------------------------------------------------------------------


class SC2DecisionExplainer:
    """
    Explain SC2 bot macro decisions using SHAP values.

    Supports:
     - TreeExplainer for tree-based models (RandomForest, XGBoost)
     - KernelExplainer for model-agnostic explanations
     - Force / summary / dependence / waterfall plots
     - Feature interaction analysis
     - Global vs local explanations
     - SHAP value caching for performance
     - Decision boundary visualisation

    Falls back to permutation importance when SHAP is unavailable.
    """

    def __init__(
        self,
        model: Optional[Any] = None,
        model_type: str = "random_forest",
        feature_names: Optional[List[str]] = None,
        cache_size: int = 2048,
    ):
        self.feature_names = feature_names or SC2_FEATURE_NAMES
        self.model = model
        self.model_type = model_type
        self._explainer = None
        self._background_data: Optional[np.ndarray] = None
        self._cache = SHAPCache(max_size=cache_size)
        self._global_shap_values: Optional[np.ndarray] = None
        self._is_fitted = model is not None

        if model is not None:
            self._init_explainer(model)

    # --------------------------------------------------------------- init
    def _init_explainer(self, model: Any) -> None:
        """Initialise the appropriate SHAP explainer for the model type."""
        if not SHAP_AVAILABLE:
            log.info("SHAP unavailable — using permutation importance fallback.")
            return

        if self.model_type in ("random_forest", "gradient_boosting", "xgboost"):
            try:
                self._explainer = shap.TreeExplainer(model)
                log.info("Initialised TreeExplainer for %s.", self.model_type)
            except Exception as exc:
                log.warning(
                    "TreeExplainer failed (%s). Falling back to KernelExplainer.", exc
                )
                self._init_kernel_explainer(model)
        else:
            self._init_kernel_explainer(model)

    def _init_kernel_explainer(
        self, model: Any, background: Optional[np.ndarray] = None
    ) -> None:
        """Initialise KernelExplainer (model-agnostic)."""
        if not SHAP_AVAILABLE:
            return
        if background is None:
            background = self._background_data
        if background is None:
            log.warning(
                "No background data for KernelExplainer. Call set_background() first."
            )
            return

        predict_fn = (
            model.predict_proba if hasattr(model, "predict_proba") else model.predict
        )
        bg_summary = shap.kmeans(background, min(50, len(background)))
        self._explainer = shap.KernelExplainer(predict_fn, bg_summary)
        log.info(
            "Initialised KernelExplainer with %d background samples.", len(background)
        )

    def set_background(self, data: np.ndarray) -> None:
        """Set background dataset for KernelExplainer."""
        self._background_data = data
        log.info("Background data set: shape %s", data.shape)

    # --------------------------------------------------------- model training
    def train_model(
        self,
        X: Optional[np.ndarray] = None,
        y: Optional[np.ndarray] = None,
        model_type: str = "random_forest",
        test_size: float = 0.2,
        **model_kwargs,
    ) -> Dict[str, Any]:
        """
        Train a classifier on SC2 game-state data.
        If X, y not provided, generates synthetic data.
        Returns training metrics.
        """
        if X is None or y is None:
            X, y = SC2DataGenerator.generate()

        self.model_type = model_type

        if not SKLEARN_AVAILABLE and model_type != "xgboost":
            log.warning("scikit-learn not available. Using NumPy fallback model.")
            return self._train_fallback(X, y)

        X_train, X_test, y_train, y_test = train_test_split(
            X, y, test_size=test_size, random_state=42, stratify=y
        )
        self._background_data = X_train

        if model_type == "xgboost" and XGB_AVAILABLE:
            default_params = {
                "n_estimators": 200,
                "max_depth": 6,
                "learning_rate": 0.1,
                "use_label_encoder": False,
                "eval_metric": "mlogloss",
            }
            default_params.update(model_kwargs)
            self.model = xgb.XGBClassifier(**default_params)
        elif model_type == "gradient_boosting":
            default_params = {"n_estimators": 200, "max_depth": 5, "learning_rate": 0.1}
            default_params.update(model_kwargs)
            self.model = GradientBoostingClassifier(**default_params)
        else:
            default_params = {"n_estimators": 200, "max_depth": 10, "n_jobs": -1}
            default_params.update(model_kwargs)
            self.model = RandomForestClassifier(**default_params)

        t0 = time.time()
        self.model.fit(X_train, y_train)
        train_time = time.time() - t0

        y_pred = self.model.predict(X_test)
        acc = accuracy_score(y_test, y_pred)

        self._is_fitted = True
        self._init_explainer(self.model)

        metrics = {
            "model_type": model_type,
            "accuracy": round(acc, 4),
            "train_time_s": round(train_time, 3),
            "n_train": len(X_train),
            "n_test": len(X_test),
            "n_features": X.shape[1],
            "n_classes": len(np.unique(y)),
        }
        log.info("Model trained: %s", metrics)
        return metrics

    def _train_fallback(self, X: np.ndarray, y: np.ndarray) -> Dict[str, Any]:
        """NumPy-only nearest-centroid classifier fallback."""
        classes = np.unique(y)
        centroids = {}
        for c in classes:
            centroids[c] = X[y == c].mean(axis=0)
        self.model = _NearestCentroidModel(centroids, classes)
        self._is_fitted = True
        self._background_data = X

        y_pred = self.model.predict(X)
        acc = np.mean(y_pred == y)
        return {
            "model_type": "nearest_centroid_fallback",
            "accuracy": round(float(acc), 4),
            "n_samples": len(X),
        }

    # ------------------------------------------------- local explanations
    def explain_decision(
        self, game_state: np.ndarray, use_cache: bool = True
    ) -> DecisionExplanation:
        """
        Explain a single game-state decision.
        Returns a DecisionExplanation with per-feature SHAP values.
        """
        if not self._is_fitted:
            raise RuntimeError(
                "Model not fitted. Call train_model() or provide a model."
            )

        game_state = np.asarray(game_state, dtype=np.float32).reshape(1, -1)

        # Prediction
        if hasattr(self.model, "predict_proba"):
            proba = self.model.predict_proba(game_state)[0]
            pred_idx = int(np.argmax(proba))
            pred_proba = {DECISION_LABELS[i]: float(p) for i, p in enumerate(proba)}
        else:
            pred_idx = int(self.model.predict(game_state)[0])
            pred_proba = {DECISION_LABELS[pred_idx]: 1.0}

        predicted = SC2Decision.from_index(pred_idx)

        # SHAP values
        cached = self._cache.get(game_state[0]) if use_cache else None
        if cached is not None:
            shap_vals = cached
        else:
            shap_vals = self._compute_shap_values(game_state)
            if use_cache:
                self._cache.put(game_state[0], shap_vals)

        # For multi-class, select SHAP values for the predicted class
        if shap_vals.ndim == 3:
            sv = shap_vals[0, :, pred_idx]
        elif shap_vals.ndim == 2:
            sv = shap_vals[0]
        else:
            sv = shap_vals

        # Base value
        base_value = 0.0
        if SHAP_AVAILABLE and self._explainer is not None:
            ev = self._explainer.expected_value
            if isinstance(ev, (list, np.ndarray)):
                base_value = float(ev[pred_idx]) if pred_idx < len(ev) else float(ev[0])
            else:
                base_value = float(ev)

        # Build feature explanations
        feature_explanations = []
        for i, fname in enumerate(self.feature_names):
            val = float(game_state[0, i])
            shap_v = float(sv[i])
            feature_explanations.append(
                FeatureExplanation(
                    feature_name=fname,
                    feature_value=val,
                    shap_value=shap_v,
                    direction="positive" if shap_v > 0 else "negative",
                )
            )

        # Sort by absolute SHAP value
        feature_explanations.sort(key=lambda fe: abs(fe.shap_value), reverse=True)

        model_output = base_value + float(sv.sum())

        return DecisionExplanation(
            game_state=game_state[0],
            predicted_decision=predicted,
            predicted_proba=pred_proba,
            feature_explanations=feature_explanations,
            base_value=base_value,
            model_output=model_output,
        )

    def _compute_shap_values(self, game_state: np.ndarray) -> np.ndarray:
        """Compute SHAP values, with fallback to permutation importance."""
        if SHAP_AVAILABLE and self._explainer is not None:
            sv = self._explainer.shap_values(game_state)
            if isinstance(sv, list):
                return np.array(sv).transpose(
                    1, 2, 0
                )  # (n_samples, n_features, n_classes)
            return np.asarray(sv)
        else:
            return self._permutation_importance(game_state)

    def _permutation_importance(
        self, game_state: np.ndarray, n_repeats: int = 20
    ) -> np.ndarray:
        """Fallback: estimate feature importance via output perturbation."""
        n_features = game_state.shape[1]
        importances = np.zeros(n_features, dtype=np.float64)

        if hasattr(self.model, "predict_proba"):
            base_pred = self.model.predict_proba(game_state)[0]
        else:
            base_pred = np.array([float(self.model.predict(game_state)[0])])

        rng = np.random.RandomState(0)
        for f_idx in range(n_features):
            diffs = []
            for _ in range(n_repeats):
                perturbed = game_state.copy()
                if self._background_data is not None:
                    rand_val = self._background_data[
                        rng.randint(0, len(self._background_data)), f_idx
                    ]
                else:
                    rand_val = game_state[0, f_idx] * (1 + rng.randn() * 0.3)
                perturbed[0, f_idx] = rand_val

                if hasattr(self.model, "predict_proba"):
                    new_pred = self.model.predict_proba(perturbed)[0]
                else:
                    new_pred = np.array([float(self.model.predict(perturbed)[0])])
                diffs.append(np.sum(np.abs(base_pred - new_pred)))

            importances[f_idx] = np.mean(diffs)

        # Convert to signed SHAP-like values (positive = pushes toward predicted class)
        pred_idx = int(np.argmax(base_pred)) if len(base_pred) > 1 else 0
        signed = importances * np.sign(
            game_state[0]
            - (
                self._background_data.mean(axis=0)
                if self._background_data is not None
                else game_state[0]
            )
        )

        return signed.reshape(1, -1)

    # ------------------------------------------------- global explanations
    def global_explanation(
        self, X: np.ndarray, max_samples: int = 500
    ) -> GlobalExplanation:
        """
        Compute global feature importance across a dataset.
        Uses mean |SHAP values| across samples.
        """
        if not self._is_fitted:
            raise RuntimeError("Model not fitted.")

        if len(X) > max_samples:
            indices = np.random.RandomState(42).choice(
                len(X), max_samples, replace=False
            )
            X_sub = X[indices]
        else:
            X_sub = X

        log.info("Computing global SHAP values for %d samples...", len(X_sub))
        t0 = time.time()

        if SHAP_AVAILABLE and self._explainer is not None:
            sv = self._explainer.shap_values(X_sub)
            if isinstance(sv, list):
                # Multi-class: average absolute values across classes
                all_sv = np.array(sv)  # (n_classes, n_samples, n_features)
                mean_abs = np.mean(np.abs(all_sv), axis=(0, 1))
                self._global_shap_values = all_sv
            else:
                sv = np.asarray(sv)
                mean_abs = np.mean(np.abs(sv), axis=0)
                self._global_shap_values = sv
        else:
            # Fallback
            mean_abs = np.zeros(NUM_FEATURES)
            for i in range(len(X_sub)):
                sv = self._permutation_importance(X_sub[i : i + 1])
                mean_abs += np.abs(sv[0])
            mean_abs /= len(X_sub)

        elapsed = time.time() - t0
        log.info("Global explanation computed in %.2fs.", elapsed)

        mean_abs_dict = {
            self.feature_names[i]: float(mean_abs[i])
            for i in range(len(self.feature_names))
        }
        ranking = sorted(mean_abs_dict, key=mean_abs_dict.get, reverse=True)

        # Feature interactions (top pairs by correlation of SHAP values)
        interactions = self._compute_interactions(X_sub)

        return GlobalExplanation(
            mean_abs_shap=mean_abs_dict,
            feature_ranking=ranking,
            interaction_pairs=interactions,
            n_samples=len(X_sub),
        )

    def _compute_interactions(self, X: np.ndarray) -> List[Tuple[str, str, float]]:
        """Estimate feature interaction strength via SHAP value correlation."""
        if self._global_shap_values is None:
            return []

        sv = self._global_shap_values
        if sv.ndim == 3:
            # Average across classes
            sv = np.mean(sv, axis=0)  # (n_samples, n_features)

        n_feat = sv.shape[1] if sv.ndim == 2 else 0
        if n_feat < 2:
            return []

        interactions: List[Tuple[str, str, float]] = []
        for i in range(n_feat):
            for j in range(i + 1, n_feat):
                if np.std(sv[:, i]) < 1e-10 or np.std(sv[:, j]) < 1e-10:
                    continue
                corr = float(np.abs(np.corrcoef(sv[:, i], sv[:, j])[0, 1]))
                if not np.isnan(corr):
                    interactions.append(
                        (self.feature_names[i], self.feature_names[j], corr)
                    )

        interactions.sort(key=lambda t: t[2], reverse=True)
        return interactions[:20]

    # -------------------------------------------------------- SHAP interaction values
    def feature_interaction_values(
        self, game_state: np.ndarray
    ) -> Optional[np.ndarray]:
        """
        Compute SHAP interaction values for a single sample (TreeExplainer only).
        Returns (n_features, n_features) interaction matrix.
        """
        if not SHAP_AVAILABLE or self._explainer is None:
            log.warning("SHAP interaction values require TreeExplainer.")
            return None

        if not hasattr(self._explainer, "shap_interaction_values"):
            log.warning("Current explainer does not support interaction values.")
            return None

        game_state = np.asarray(game_state, dtype=np.float32).reshape(1, -1)
        try:
            iv = self._explainer.shap_interaction_values(game_state)
            if isinstance(iv, list):
                return np.array(iv[0])
            return np.asarray(iv[0])
        except Exception as exc:
            log.error("Interaction value computation failed: %s", exc)
            return None

    # -------------------------------------------------------- visualisations
    def plot_force(
        self, explanation: DecisionExplanation, save_path: Optional[str] = None
    ) -> Optional[str]:
        """Generate a SHAP force plot for a single decision."""
        if not SHAP_AVAILABLE or not MPL_AVAILABLE:
            log.warning("Force plot requires SHAP and matplotlib.")
            return None

        sv = np.array([fe.shap_value for fe in explanation.feature_explanations])
        fv = np.array([fe.feature_value for fe in explanation.feature_explanations])
        fn = [fe.feature_name for fe in explanation.feature_explanations]

        shap.force_plot(
            explanation.base_value,
            sv,
            fv,
            feature_names=fn,
            matplotlib=True,
            show=False,
        )

        path = (
            save_path or f"force_plot_{explanation.predicted_decision.name.lower()}.png"
        )
        plt.savefig(path, bbox_inches="tight", dpi=150)
        plt.close()
        log.info("Force plot saved to %s", path)
        return path

    def plot_summary(
        self, X: np.ndarray, save_path: Optional[str] = None, plot_type: str = "dot"
    ) -> Optional[str]:
        """Generate a SHAP summary plot (global feature importance)."""
        if not SHAP_AVAILABLE or not MPL_AVAILABLE:
            log.warning("Summary plot requires SHAP and matplotlib.")
            return None

        if self._global_shap_values is None:
            self.global_explanation(X)

        sv = self._global_shap_values
        if isinstance(sv, list):
            sv = sv[0]
        if sv.ndim == 3:
            sv = sv[0]

        n_plot = min(len(X), sv.shape[0])
        plt.figure(figsize=(10, 8))
        shap.summary_plot(
            sv[:n_plot],
            X[:n_plot],
            feature_names=self.feature_names,
            plot_type=plot_type,
            show=False,
        )

        path = save_path or "shap_summary_plot.png"
        plt.savefig(path, bbox_inches="tight", dpi=150)
        plt.close()
        log.info("Summary plot saved to %s", path)
        return path

    def plot_dependence(
        self,
        feature: str,
        X: np.ndarray,
        interaction_feature: Optional[str] = None,
        save_path: Optional[str] = None,
    ) -> Optional[str]:
        """Generate a SHAP dependence plot for a single feature."""
        if not SHAP_AVAILABLE or not MPL_AVAILABLE:
            log.warning("Dependence plot requires SHAP and matplotlib.")
            return None

        if self._global_shap_values is None:
            self.global_explanation(X)

        sv = self._global_shap_values
        if isinstance(sv, list):
            sv = sv[0]
        if sv.ndim == 3:
            sv = sv[0]

        n_plot = min(len(X), sv.shape[0])
        plt.figure(figsize=(8, 6))
        shap.dependence_plot(
            feature,
            sv[:n_plot],
            X[:n_plot],
            feature_names=self.feature_names,
            interaction_index=interaction_feature,
            show=False,
        )

        path = save_path or f"shap_dependence_{feature}.png"
        plt.savefig(path, bbox_inches="tight", dpi=150)
        plt.close()
        log.info("Dependence plot saved to %s", path)
        return path

    def plot_waterfall(
        self, explanation: DecisionExplanation, save_path: Optional[str] = None
    ) -> Optional[str]:
        """Generate a SHAP waterfall chart for a single decision."""
        if not SHAP_AVAILABLE or not MPL_AVAILABLE:
            log.warning("Waterfall chart requires SHAP and matplotlib.")
            return None

        sv = np.array([fe.shap_value for fe in explanation.feature_explanations])
        fn = [fe.feature_name for fe in explanation.feature_explanations]

        shap_explanation = shap.Explanation(
            values=sv,
            base_values=explanation.base_value,
            feature_names=fn,
        )

        plt.figure(figsize=(8, 10))
        shap.plots.waterfall(shap_explanation, show=False)

        path = (
            save_path or f"waterfall_{explanation.predicted_decision.name.lower()}.png"
        )
        plt.savefig(path, bbox_inches="tight", dpi=150)
        plt.close()
        log.info("Waterfall chart saved to %s", path)
        return path

    def plot_decision_boundary(
        self,
        X: np.ndarray,
        feature_x: str,
        feature_y: str,
        save_path: Optional[str] = None,
        resolution: int = 100,
    ) -> Optional[str]:
        """Visualise decision boundary for two selected features."""
        if not MPL_AVAILABLE or not self._is_fitted:
            log.warning(
                "Decision boundary plot requires matplotlib and a fitted model."
            )
            return None

        idx_x = self.feature_names.index(feature_x)
        idx_y = self.feature_names.index(feature_y)

        x_min, x_max = X[:, idx_x].min() - 1, X[:, idx_x].max() + 1
        y_min, y_max = X[:, idx_y].min() - 1, X[:, idx_y].max() + 1

        xx, yy = np.meshgrid(
            np.linspace(x_min, x_max, resolution),
            np.linspace(y_min, y_max, resolution),
        )

        # Fill grid with mean feature values except the two chosen
        grid = np.tile(X.mean(axis=0), (resolution * resolution, 1))
        grid[:, idx_x] = xx.ravel()
        grid[:, idx_y] = yy.ravel()

        Z = self.model.predict(grid).reshape(xx.shape)

        plt.figure(figsize=(10, 8))
        plt.contourf(xx, yy, Z, alpha=0.4, cmap="RdYlGn")
        plt.scatter(
            X[:300, idx_x],
            X[:300, idx_y],
            c=self.model.predict(X[:300]),
            cmap="RdYlGn",
            edgecolors="k",
            s=20,
            alpha=0.6,
        )
        plt.xlabel(feature_x)
        plt.ylabel(feature_y)
        plt.title(f"Decision Boundary: {feature_x} vs {feature_y}")
        plt.colorbar(label="Decision")

        path = save_path or f"decision_boundary_{feature_x}_vs_{feature_y}.png"
        plt.savefig(path, bbox_inches="tight", dpi=150)
        plt.close()
        log.info("Decision boundary plot saved to %s", path)
        return path

    # ----------------------------------------- explain specific game decisions
    def explain_game_moment(
        self,
        minerals: float,
        gas: float,
        supply_used: float,
        supply_cap: float,
        worker_count: float,
        army_supply: float,
        army_value_minerals: float,
        army_value_gas: float,
        enemy_army_value_estimate: float,
        base_count: float,
        enemy_base_count: float,
        tech_level: float = 1.0,
        upgrade_count: float = 0.0,
        production_capacity: float = 5.0,
        map_control_pct: float = 0.5,
        time_seconds: float = 300.0,
        idle_workers: float = 0.0,
        pending_units: float = 0.0,
        enemy_air_threat: float = 0.0,
        enemy_ground_threat: float = 0.0,
    ) -> DecisionExplanation:
        """
        Convenience method: explain a decision from explicit game-state values.
        All SC2 feature values are passed as keyword arguments.
        """
        state = np.array(
            [
                minerals,
                gas,
                supply_used,
                supply_cap,
                worker_count,
                army_supply,
                army_value_minerals,
                army_value_gas,
                enemy_army_value_estimate,
                base_count,
                enemy_base_count,
                tech_level,
                upgrade_count,
                production_capacity,
                map_control_pct,
                time_seconds,
                idle_workers,
                pending_units,
                enemy_air_threat,
                enemy_ground_threat,
            ],
            dtype=np.float32,
        )
        return self.explain_decision(state)

    # ------------------------------------------------------------ cache ops
    def clear_cache(self) -> int:
        count = self._cache.clear()
        log.info("SHAP cache cleared: %d entries removed.", count)
        return count

    @property
    def cache_stats(self) -> Dict[str, int]:
        return self._cache.stats

    # --------------------------------------------------------- serialisation
    def export_explanations(
        self,
        explanations: Sequence[DecisionExplanation],
        filepath: Optional[str] = None,
    ) -> str:
        """Export explanations as JSON."""
        data = [e.to_dict() for e in explanations]
        json_str = json.dumps(data, indent=2, ensure_ascii=False)
        if filepath:
            with open(filepath, "w", encoding="utf-8") as f:
                f.write(json_str)
            log.info("Exported %d explanations to %s", len(data), filepath)
        return json_str


# ---------------------------------------------------------------------------
# NumPy-only nearest centroid model (fallback)
# ---------------------------------------------------------------------------


class _NearestCentroidModel:
    """Minimal nearest-centroid classifier for fallback use."""

    def __init__(self, centroids: Dict[int, np.ndarray], classes: np.ndarray):
        self._centroids = centroids
        self._classes = classes

    def predict(self, X: np.ndarray) -> np.ndarray:
        X = np.atleast_2d(X)
        predictions = np.zeros(len(X), dtype=np.int32)
        for i, sample in enumerate(X):
            dists = {
                c: np.linalg.norm(sample - cent) for c, cent in self._centroids.items()
            }
            predictions[i] = min(dists, key=dists.get)
        return predictions

    def predict_proba(self, X: np.ndarray) -> np.ndarray:
        X = np.atleast_2d(X)
        n_classes = len(self._classes)
        proba = np.zeros((len(X), n_classes), dtype=np.float64)
        for i, sample in enumerate(X):
            dists = np.array(
                [np.linalg.norm(sample - self._centroids[c]) for c in self._classes]
            )
            inv_dists = 1.0 / (dists + 1e-10)
            proba[i] = inv_dists / inv_dists.sum()
        return proba


# ---------------------------------------------------------------------------
# CLI / demo
# ---------------------------------------------------------------------------


def _demo() -> None:
    """Run a demonstration of the SC2 decision explainer."""
    explainer = SC2DecisionExplainer()

    # Train model
    print("=" * 72)
    print("TRAINING MODEL")
    print("=" * 72)
    metrics = explainer.train_model()
    for k, v in metrics.items():
        print(f"  {k}: {v}")

    # Generate test data
    X, y = SC2DataGenerator.generate(n_samples=200, seed=99)

    # Local explanation — specific game moment
    print("\n" + "=" * 72)
    print("LOCAL EXPLANATION: Specific Game Moment")
    print("=" * 72)
    explanation = explainer.explain_game_moment(
        minerals=1200,
        gas=800,
        supply_used=140,
        supply_cap=200,
        worker_count=70,
        army_supply=70,
        army_value_minerals=5000,
        army_value_gas=3000,
        enemy_army_value_estimate=3500,
        base_count=4,
        enemy_base_count=3,
        tech_level=2,
        upgrade_count=6,
        production_capacity=12,
        map_control_pct=0.65,
        time_seconds=600,
        idle_workers=2,
        pending_units=5,
        enemy_air_threat=0.3,
        enemy_ground_threat=0.5,
    )
    print(f"  Decision: {explanation.predicted_decision.name}")
    print(f"  Probabilities: {explanation.predicted_proba}")
    print(f"  Base value: {explanation.base_value:.4f}")
    print(f"  Model output: {explanation.model_output:.4f}")
    print("  Top contributing features:")
    for fe in explanation.feature_explanations[:5]:
        arrow = "+" if fe.direction == "positive" else "-"
        print(
            f"    {arrow} {fe.feature_name}: value={fe.feature_value:.1f}, "
            f"shap={fe.shap_value:.4f}"
        )

    # Local explanation — defensive scenario
    print("\n" + "=" * 72)
    print("LOCAL EXPLANATION: Under Attack Scenario")
    print("=" * 72)
    explanation2 = explainer.explain_game_moment(
        minerals=300,
        gas=200,
        supply_used=80,
        supply_cap=100,
        worker_count=50,
        army_supply=30,
        army_value_minerals=1500,
        army_value_gas=800,
        enemy_army_value_estimate=6000,
        base_count=2,
        enemy_base_count=3,
        tech_level=1,
        upgrade_count=2,
        production_capacity=6,
        map_control_pct=0.3,
        time_seconds=360,
        idle_workers=0,
        pending_units=8,
        enemy_air_threat=0.2,
        enemy_ground_threat=0.85,
    )
    print(f"  Decision: {explanation2.predicted_decision.name}")
    print(f"  Probabilities: {explanation2.predicted_proba}")
    print("  Top contributing features:")
    for fe in explanation2.feature_explanations[:5]:
        arrow = "+" if fe.direction == "positive" else "-"
        print(
            f"    {arrow} {fe.feature_name}: value={fe.feature_value:.1f}, "
            f"shap={fe.shap_value:.4f}"
        )

    # Global explanation
    print("\n" + "=" * 72)
    print("GLOBAL EXPLANATION")
    print("=" * 72)
    global_exp = explainer.global_explanation(X)
    print("  Feature ranking (by mean |SHAP|):")
    for i, fname in enumerate(global_exp.feature_ranking[:10], 1):
        print(f"    {i:2d}. {fname}: {global_exp.mean_abs_shap[fname]:.6f}")
    if global_exp.interaction_pairs:
        print("  Top feature interactions:")
        for a, b, s in global_exp.interaction_pairs[:5]:
            print(f"    {a} <-> {b}: {s:.4f}")

    # Cache stats
    print("\n" + "=" * 72)
    print("CACHE STATS")
    print("=" * 72)
    for k, v in explainer.cache_stats.items():
        print(f"  {k}: {v}")

    # JSON export
    print("\n" + "=" * 72)
    print("JSON EXPORT (first explanation):")
    print("=" * 72)
    print(explanation.to_json())


if __name__ == "__main__":
    _demo()
