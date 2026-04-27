# Phase 588: LightGBM
"""
sc2_build_classifier.py — StarCraft II Build Order Classification with LightGBM
Multi-class classifier that identifies 8 SC2 build patterns from game-state
features.  Includes Bayesian hyperparameter search (Optuna), DART boosting
comparison, learning-curve visualisation, and per-class evaluation metrics.

Graceful fallback to a pure-NumPy stub when LightGBM or Optuna are absent.
"""

from __future__ import annotations

import logging
import os
import time
import warnings
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple

import numpy as np

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
log = logging.getLogger("sc2_build_classifier")

# ---------------------------------------------------------------------------
# Optional imports — graceful fallback
# ---------------------------------------------------------------------------
try:
    import lightgbm as lgb

    LGB_AVAILABLE = True
    log.info("LightGBM %s available.", lgb.__version__)
except ImportError:
    LGB_AVAILABLE = False
    log.warning("LightGBM not installed — using NumPy stub classifier.")

try:
    import optuna

    OPTUNA_AVAILABLE = True
    optuna.logging.set_verbosity(optuna.logging.WARNING)
except ImportError:
    OPTUNA_AVAILABLE = False

try:
    import matplotlib

    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    PLT_AVAILABLE = True
except ImportError:
    PLT_AVAILABLE = False

try:
    from sklearn.metrics import (
        accuracy_score,
        classification_report,
        confusion_matrix,
        log_loss,
    )
    from sklearn.model_selection import StratifiedKFold, train_test_split
    from sklearn.preprocessing import LabelEncoder

    SK_AVAILABLE = True
except ImportError:
    SK_AVAILABLE = False

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------
BUILD_LABELS: List[str] = [
    "terran_bio",
    "terran_mech",
    "terran_rush",
    "protoss_stargate",
    "protoss_robo",
    "protoss_gateway",
    "zerg_pool_first",
    "zerg_hatch_first",
]

# Features used by the classifier.  The first block are numeric; the rest are
# categorical (handled natively by LightGBM).
NUMERIC_FEATURES: List[str] = [
    "game_time_seconds",
    "supply_used",
    "supply_cap",
    "mineral_rate",
    "vespene_rate",
    "minerals_banked",
    "vespene_banked",
    "worker_count",
    "army_supply",
    "army_value_minerals",
    "army_value_vespene",
    "tech_building_count",
    "production_building_count",
    "expansion_count",
    "units_killed",
    "units_lost",
    "enemy_units_seen",
    "enemy_buildings_seen",
]

CATEGORICAL_FEATURES: List[str] = [
    "opponent_race",  # terran / protoss / zerg / random
    "map_name",  # categorical map identifier
    "first_building_type",  # first non-hatchery building placed
    "gas_timing",  # early / normal / late
]

ALL_FEATURES: List[str] = NUMERIC_FEATURES + CATEGORICAL_FEATURES


# ---------------------------------------------------------------------------
# Data helpers
# ---------------------------------------------------------------------------
@dataclass
class SC2GameSample:
    """One training sample derived from a game snapshot."""

    features: Dict[str, Any]
    label: str  # one of BUILD_LABELS

    def to_array(self, feature_names: List[str]) -> np.ndarray:
        return np.array([self.features.get(f, 0) for f in feature_names])


def generate_synthetic_dataset(
    n_samples: int = 4000,
    seed: int = 42,
) -> Tuple[np.ndarray, np.ndarray, List[str]]:
    """Create a synthetic dataset for development / testing."""

    rng = np.random.RandomState(seed)
    n_numeric = len(NUMERIC_FEATURES)
    n_cat = len(CATEGORICAL_FEATURES)
    n_classes = len(BUILD_LABELS)
    n_features = n_numeric + n_cat

    X = np.zeros((n_samples, n_features), dtype=np.float32)
    y = rng.randint(0, n_classes, size=n_samples)

    # Numeric features — class-conditional means so the classifier can learn.
    for cls_idx in range(n_classes):
        mask = y == cls_idx
        centre = rng.uniform(20, 200, size=n_numeric)
        X[mask, :n_numeric] = rng.normal(
            loc=centre, scale=15.0, size=(mask.sum(), n_numeric)
        )

    # Categorical features — encoded as integers.
    cat_cards = [3, 8, 6, 3]  # cardinalities for each categorical feature
    for i, card in enumerate(cat_cards):
        col = n_numeric + i
        X[:, col] = rng.randint(0, card, size=n_samples)

    return X, y, ALL_FEATURES


def feature_engineering_from_game_state(state: Dict[str, Any]) -> Dict[str, Any]:
    """Extract classifier features from a raw game-state dictionary.

    Parameters
    ----------
    state : dict
        Keys expected: ``minerals``, ``vespene``, ``supply_used``,
        ``supply_cap``, ``game_loop``, ``structures``, ``units``,
        ``enemy_units``, ``enemy_structures``, etc.

    Returns
    -------
    dict  — feature-name -> value, ready for the model.
    """

    game_time = state.get("game_loop", 0) / 22.4  # game loops -> seconds
    minerals = state.get("minerals", 0)
    vespene = state.get("vespene", 0)
    supply_used = state.get("supply_used", 0)
    supply_cap = state.get("supply_cap", 0)

    structures = state.get("structures", [])
    units = state.get("units", [])
    enemy_units = state.get("enemy_units", [])
    enemy_structures = state.get("enemy_structures", [])

    tech_buildings = {
        "SPAWNINGPOOL",
        "ROACHWARREN",
        "HYDRALISKDEN",
        "SPIRE",
        "INFESTATIONPIT",
        "ULTRALISKCAVERN",
        "LURKERDENMP",
        "BANELINGNEST",
    }
    prod_buildings = {
        "HATCHERY",
        "LAIR",
        "HIVE",
        "GATEWAY",
        "BARRACKS",
        "FACTORY",
        "STARPORT",
        "ROBOTICSFACILITY",
    }

    tech_count = sum(
        1 for s in structures if s.get("name", "").upper() in tech_buildings
    )
    prod_count = sum(
        1 for s in structures if s.get("name", "").upper() in prod_buildings
    )
    expansion_count = sum(
        1
        for s in structures
        if s.get("name", "").upper()
        in {
            "HATCHERY",
            "LAIR",
            "HIVE",
            "NEXUS",
            "COMMANDCENTER",
            "ORBITALCOMMAND",
            "PLANETARYFORTRESS",
        }
    )

    workers = sum(
        1 for u in units if u.get("name", "").upper() in {"DRONE", "PROBE", "SCV"}
    )
    army_supply = supply_used - workers
    army_value_min = sum(
        u.get("mineral_cost", 0)
        for u in units
        if u.get("name", "").upper() not in {"DRONE", "PROBE", "SCV"}
    )
    army_value_ves = sum(
        u.get("vespene_cost", 0)
        for u in units
        if u.get("name", "").upper() not in {"DRONE", "PROBE", "SCV"}
    )

    # Simple mineral / gas income heuristic: 60 per worker-minute for minerals
    mineral_rate = workers * 60 if game_time > 0 else 0
    vespene_workers = min(state.get("vespene_workers", 0), 6)
    vespene_rate = vespene_workers * 38 if game_time > 0 else 0

    first_building = "unknown"
    if structures:
        sorted_structs = sorted(structures, key=lambda s: s.get("build_progress", 1.0))
        first_building = sorted_structs[0].get("name", "unknown")

    gas_timing = "normal"
    gas_time = state.get("first_gas_time", 60)
    if gas_time < 40:
        gas_timing = "early"
    elif gas_time > 90:
        gas_timing = "late"

    return {
        "game_time_seconds": game_time,
        "supply_used": supply_used,
        "supply_cap": supply_cap,
        "mineral_rate": mineral_rate,
        "vespene_rate": vespene_rate,
        "minerals_banked": minerals,
        "vespene_banked": vespene,
        "worker_count": workers,
        "army_supply": max(army_supply, 0),
        "army_value_minerals": army_value_min,
        "army_value_vespene": army_value_ves,
        "tech_building_count": tech_count,
        "production_building_count": prod_count,
        "expansion_count": expansion_count,
        "units_killed": state.get("units_killed", 0),
        "units_lost": state.get("units_lost", 0),
        "enemy_units_seen": len(enemy_units),
        "enemy_buildings_seen": len(enemy_structures),
        "opponent_race": state.get("opponent_race", "unknown"),
        "map_name": state.get("map_name", "unknown"),
        "first_building_type": first_building,
        "gas_timing": gas_timing,
    }


# ---------------------------------------------------------------------------
# SC2BuildClassifier
# ---------------------------------------------------------------------------
class SC2BuildClassifier:
    """LightGBM-based multi-class build order classifier.

    Parameters
    ----------
    boosting_type : str
        ``"gbdt"`` (default) or ``"dart"`` for DART boosting comparison.
    n_estimators : int
        Maximum number of boosting rounds.
    learning_rate : float
    max_depth : int
    num_leaves : int
    random_state : int
    """

    def __init__(
        self,
        boosting_type: str = "gbdt",
        n_estimators: int = 600,
        learning_rate: float = 0.05,
        max_depth: int = 8,
        num_leaves: int = 63,
        random_state: int = 42,
    ) -> None:
        self.boosting_type = boosting_type
        self.n_estimators = n_estimators
        self.learning_rate = learning_rate
        self.max_depth = max_depth
        self.num_leaves = num_leaves
        self.random_state = random_state

        self.model: Optional[Any] = None
        self.label_encoder: Optional[Any] = None
        self.feature_names: List[str] = list(ALL_FEATURES)
        self.categorical_indices: List[int] = [
            ALL_FEATURES.index(f) for f in CATEGORICAL_FEATURES
        ]
        self.train_log: Dict[str, List[float]] = {}
        self._fitted = False

    # ---- internal helpers -------------------------------------------------
    def _build_lgb_params(self) -> Dict[str, Any]:
        return {
            "boosting_type": self.boosting_type,
            "objective": "multiclass",
            "num_class": len(BUILD_LABELS),
            "metric": "multi_logloss",
            "learning_rate": self.learning_rate,
            "max_depth": self.max_depth,
            "num_leaves": self.num_leaves,
            "n_estimators": self.n_estimators,
            "subsample": 0.8,
            "colsample_bytree": 0.8,
            "reg_alpha": 0.1,
            "reg_lambda": 1.0,
            "min_child_samples": 20,
            "random_state": self.random_state,
            "verbose": -1,
        }

    def _make_classifier(self, params: Optional[Dict[str, Any]] = None) -> Any:
        if not LGB_AVAILABLE:
            return None
        p = params or self._build_lgb_params()
        return lgb.LGBMClassifier(**p)

    # ---- training ---------------------------------------------------------
    def fit(
        self,
        X: np.ndarray,
        y: np.ndarray,
        X_val: Optional[np.ndarray] = None,
        y_val: Optional[np.ndarray] = None,
        early_stopping_rounds: int = 50,
    ) -> "SC2BuildClassifier":
        """Train the classifier.

        If *X_val* / *y_val* are ``None`` a 15 % hold-out is split
        automatically for early stopping.
        """

        if not LGB_AVAILABLE:
            log.warning("LightGBM unavailable — fitting NumPy stub.")
            self._fit_stub(X, y)
            return self

        if X_val is None or y_val is None:
            X_train, X_val, y_train, y_val = train_test_split(
                X, y, test_size=0.15, stratify=y, random_state=self.random_state
            )
        else:
            X_train, y_train = X, y

        self.model = self._make_classifier()

        callbacks = [
            lgb.early_stopping(stopping_rounds=early_stopping_rounds, verbose=True),
            lgb.log_evaluation(period=50),
        ]

        self.model.fit(
            X_train,
            y_train,
            eval_set=[(X_val, y_val)],
            eval_metric="multi_logloss",
            callbacks=callbacks,
            categorical_feature=self.categorical_indices,
        )

        # Store evaluation log
        evals_result = self.model.evals_result_
        if evals_result:
            key = list(evals_result.keys())[0]
            self.train_log["val_logloss"] = evals_result[key]["multi_logloss"]

        self._fitted = True
        log.info(
            "Training complete — best iteration %d.",
            (
                self.model.best_iteration_
                if hasattr(self.model, "best_iteration_")
                else -1
            ),
        )
        return self

    def _fit_stub(self, X: np.ndarray, y: np.ndarray) -> None:
        """Minimal stub: memorise per-class centroids."""
        self._centroids: Dict[int, np.ndarray] = {}
        for cls in np.unique(y):
            self._centroids[int(cls)] = X[y == cls].mean(axis=0)
        self._fitted = True

    # ---- prediction -------------------------------------------------------
    def predict(self, X: np.ndarray) -> np.ndarray:
        if not self._fitted:
            raise RuntimeError("Classifier has not been fitted yet.")
        if self.model is not None:
            return self.model.predict(X)
        # stub prediction: nearest centroid
        preds = np.zeros(X.shape[0], dtype=int)
        for i in range(X.shape[0]):
            dists = {c: np.linalg.norm(X[i] - mu) for c, mu in self._centroids.items()}
            preds[i] = min(dists, key=dists.get)  # type: ignore[arg-type]
        return preds

    def predict_proba(self, X: np.ndarray) -> np.ndarray:
        if not self._fitted:
            raise RuntimeError("Classifier has not been fitted yet.")
        if self.model is not None:
            return self.model.predict_proba(X)
        # stub: softmax over negative distances
        n_classes = len(self._centroids)
        probs = np.zeros((X.shape[0], n_classes))
        for i in range(X.shape[0]):
            dists = np.array(
                [
                    np.linalg.norm(X[i] - self._centroids[c])
                    for c in sorted(self._centroids)
                ]
            )
            exp_neg = np.exp(-dists)
            probs[i] = exp_neg / exp_neg.sum()
        return probs

    def predict_build(self, game_state: Dict[str, Any]) -> Tuple[str, float]:
        """Predict the build label for a live game state dictionary."""
        feats = feature_engineering_from_game_state(game_state)
        row = np.array(
            [[feats.get(f, 0) for f in self.feature_names]], dtype=np.float32
        )
        proba = self.predict_proba(row)[0]
        idx = int(np.argmax(proba))
        return BUILD_LABELS[idx], float(proba[idx])

    # ---- feature importance -----------------------------------------------
    def feature_importance(self, importance_type: str = "gain") -> Dict[str, float]:
        """Return feature importances as {name: value}.

        Parameters
        ----------
        importance_type : str
            ``"gain"`` (default) or ``"split"``.
        """
        if self.model is None:
            log.warning("No LightGBM model — returning empty importances.")
            return {}
        raw = self.model.booster_.feature_importance(importance_type=importance_type)
        names = self.model.booster_.feature_name()
        total = raw.sum() or 1.0
        return {n: float(v / total) for n, v in zip(names, raw)}

    def print_feature_importance(self, top_k: int = 15) -> None:
        for imp_type in ("gain", "split"):
            imp = self.feature_importance(imp_type)
            if not imp:
                continue
            ranked = sorted(imp.items(), key=lambda kv: kv[1], reverse=True)[:top_k]
            log.info("Feature importance (%s):", imp_type)
            for name, val in ranked:
                log.info("  %-30s %.4f", name, val)

    # ---- evaluation -------------------------------------------------------
    def evaluate(self, X: np.ndarray, y: np.ndarray) -> Dict[str, Any]:
        """Compute accuracy, log-loss, confusion matrix, per-class report."""
        y_pred = self.predict(X)
        y_proba = self.predict_proba(X)

        acc = (
            float(accuracy_score(y, y_pred))
            if SK_AVAILABLE
            else float((y_pred == y).mean())
        )

        ll = None
        if SK_AVAILABLE:
            try:
                ll = float(log_loss(y, y_proba))
            except Exception:
                pass

        cm = None
        report = None
        if SK_AVAILABLE:
            cm = confusion_matrix(y, y_pred).tolist()
            report = classification_report(
                y, y_pred, target_names=BUILD_LABELS, output_dict=True
            )

        result = {
            "accuracy": acc,
            "log_loss": ll,
            "confusion_matrix": cm,
            "report": report,
        }
        log.info(
            "Evaluation — accuracy=%.4f  log_loss=%s", acc, f"{ll:.4f}" if ll else "N/A"
        )
        return result

    def plot_confusion_matrix(
        self,
        X: np.ndarray,
        y: np.ndarray,
        save_path: str = "confusion_matrix.png",
    ) -> Optional[str]:
        """Plot and save the confusion matrix with per-class metrics."""
        if not PLT_AVAILABLE or not SK_AVAILABLE:
            log.warning("matplotlib or sklearn not available — skipping plot.")
            return None

        y_pred = self.predict(X)
        cm = confusion_matrix(y, y_pred)
        n = len(BUILD_LABELS)

        fig, ax = plt.subplots(figsize=(10, 8))
        im = ax.imshow(cm, interpolation="nearest", cmap=plt.cm.Blues)
        ax.figure.colorbar(im, ax=ax)
        ax.set(
            xticks=np.arange(n),
            yticks=np.arange(n),
            xticklabels=BUILD_LABELS,
            yticklabels=BUILD_LABELS,
            ylabel="True label",
            xlabel="Predicted label",
            title="SC2 Build Order — Confusion Matrix",
        )
        plt.setp(ax.get_xticklabels(), rotation=45, ha="right")

        # Annotate cells
        thresh = cm.max() / 2.0
        for i in range(n):
            for j in range(n):
                ax.text(
                    j,
                    i,
                    f"{cm[i, j]}",
                    ha="center",
                    va="center",
                    color="white" if cm[i, j] > thresh else "black",
                )

        # Per-class precision / recall beneath the matrix
        report = classification_report(
            y, y_pred, target_names=BUILD_LABELS, output_dict=True
        )
        lines = []
        for lbl in BUILD_LABELS:
            p = report[lbl]["precision"]
            r = report[lbl]["recall"]
            f1 = report[lbl]["f1-score"]
            lines.append(f"{lbl}: P={p:.2f} R={r:.2f} F1={f1:.2f}")
        fig.text(0.02, 0.01, "  |  ".join(lines), fontsize=6, family="monospace")

        fig.tight_layout()
        fig.savefig(save_path, dpi=150)
        plt.close(fig)
        log.info("Confusion matrix saved to %s", save_path)
        return save_path

    # ---- learning curves --------------------------------------------------
    def plot_learning_curves(
        self,
        X: np.ndarray,
        y: np.ndarray,
        n_splits: int = 5,
        train_sizes: Optional[List[float]] = None,
        save_path: str = "learning_curves.png",
    ) -> Optional[str]:
        """Generate learning-curve plot (accuracy vs training-set size)."""
        if not PLT_AVAILABLE or not SK_AVAILABLE or not LGB_AVAILABLE:
            log.warning("Dependencies missing — skipping learning curves.")
            return None

        if train_sizes is None:
            train_sizes = [0.2, 0.4, 0.6, 0.8, 1.0]

        skf = StratifiedKFold(
            n_splits=n_splits, shuffle=True, random_state=self.random_state
        )
        train_scores_mean = []
        val_scores_mean = []

        for frac in train_sizes:
            fold_train_acc = []
            fold_val_acc = []
            for train_idx, val_idx in skf.split(X, y):
                n_use = max(int(len(train_idx) * frac), 10)
                sub_idx = train_idx[:n_use]
                X_tr, y_tr = X[sub_idx], y[sub_idx]
                X_va, y_va = X[val_idx], y[val_idx]

                clf = self._make_classifier()
                if clf is None:
                    return None
                clf.fit(
                    X_tr,
                    y_tr,
                    eval_set=[(X_va, y_va)],
                    callbacks=[
                        lgb.early_stopping(stopping_rounds=30, verbose=False),
                        lgb.log_evaluation(period=0),
                    ],
                    categorical_feature=self.categorical_indices,
                )
                fold_train_acc.append(accuracy_score(y_tr, clf.predict(X_tr)))
                fold_val_acc.append(accuracy_score(y_va, clf.predict(X_va)))

            train_scores_mean.append(np.mean(fold_train_acc))
            val_scores_mean.append(np.mean(fold_val_acc))

        fig, ax = plt.subplots(figsize=(8, 5))
        sample_counts = [int(len(y) * (1 - 1 / n_splits) * f) for f in train_sizes]
        ax.plot(sample_counts, train_scores_mean, "o-", label="Train")
        ax.plot(sample_counts, val_scores_mean, "o-", label="Validation")
        ax.set_xlabel("Training samples")
        ax.set_ylabel("Accuracy")
        ax.set_title("SC2 Build Classifier — Learning Curves")
        ax.legend()
        ax.grid(True, alpha=0.3)
        fig.tight_layout()
        fig.savefig(save_path, dpi=150)
        plt.close(fig)
        log.info("Learning curves saved to %s", save_path)
        return save_path

    # ---- DART comparison --------------------------------------------------
    def compare_dart(
        self,
        X: np.ndarray,
        y: np.ndarray,
        test_size: float = 0.2,
    ) -> Dict[str, Dict[str, float]]:
        """Train both GBDT and DART and compare metrics."""
        if not LGB_AVAILABLE or not SK_AVAILABLE:
            log.warning("LightGBM / sklearn not available — skipping DART comparison.")
            return {}

        X_train, X_test, y_train, y_test = train_test_split(
            X, y, test_size=test_size, stratify=y, random_state=self.random_state
        )

        results: Dict[str, Dict[str, float]] = {}
        for btype in ("gbdt", "dart"):
            params = self._build_lgb_params()
            params["boosting_type"] = btype
            if btype == "dart":
                params["drop_rate"] = 0.1
                params["max_drop"] = 50
                params["skip_drop"] = 0.5

            clf = lgb.LGBMClassifier(**params)
            t0 = time.perf_counter()
            clf.fit(
                X_train,
                y_train,
                eval_set=[(X_test, y_test)],
                callbacks=[
                    lgb.early_stopping(stopping_rounds=50, verbose=False),
                    lgb.log_evaluation(period=0),
                ],
                categorical_feature=self.categorical_indices,
            )
            elapsed = time.perf_counter() - t0
            y_pred = clf.predict(X_test)
            y_proba = clf.predict_proba(X_test)
            acc = float(accuracy_score(y_test, y_pred))
            ll = float(log_loss(y_test, y_proba))
            results[btype] = {"accuracy": acc, "log_loss": ll, "train_time_s": elapsed}
            log.info("%s — acc=%.4f  logloss=%.4f  time=%.2fs", btype, acc, ll, elapsed)

        return results

    # ---- Bayesian hyperparameter optimisation (Optuna) --------------------
    def bayesian_optimize(
        self,
        X: np.ndarray,
        y: np.ndarray,
        n_trials: int = 40,
        cv_folds: int = 3,
        timeout: Optional[int] = 300,
    ) -> Dict[str, Any]:
        """Run Optuna-based Bayesian hyperparameter search.

        Returns the best parameters found and re-fits the model.
        """
        if not OPTUNA_AVAILABLE or not LGB_AVAILABLE or not SK_AVAILABLE:
            log.warning(
                "Optuna / LightGBM / sklearn not available — skipping optimisation."
            )
            return {}

        X_train, X_val, y_train, y_val = train_test_split(
            X, y, test_size=0.15, stratify=y, random_state=self.random_state
        )

        def objective(trial: "optuna.Trial") -> float:
            params = {
                "boosting_type": trial.suggest_categorical(
                    "boosting_type", ["gbdt", "dart"]
                ),
                "objective": "multiclass",
                "num_class": len(BUILD_LABELS),
                "metric": "multi_logloss",
                "learning_rate": trial.suggest_float(
                    "learning_rate", 0.01, 0.3, log=True
                ),
                "max_depth": trial.suggest_int("max_depth", 3, 12),
                "num_leaves": trial.suggest_int("num_leaves", 15, 255),
                "n_estimators": 800,
                "subsample": trial.suggest_float("subsample", 0.5, 1.0),
                "colsample_bytree": trial.suggest_float("colsample_bytree", 0.4, 1.0),
                "reg_alpha": trial.suggest_float("reg_alpha", 1e-4, 10.0, log=True),
                "reg_lambda": trial.suggest_float("reg_lambda", 1e-4, 10.0, log=True),
                "min_child_samples": trial.suggest_int("min_child_samples", 5, 100),
                "random_state": self.random_state,
                "verbose": -1,
            }

            skf = StratifiedKFold(
                n_splits=cv_folds, shuffle=True, random_state=self.random_state
            )
            losses: List[float] = []

            for tr_idx, va_idx in skf.split(X_train, y_train):
                clf = lgb.LGBMClassifier(**params)
                clf.fit(
                    X_train[tr_idx],
                    y_train[tr_idx],
                    eval_set=[(X_train[va_idx], y_train[va_idx])],
                    callbacks=[
                        lgb.early_stopping(stopping_rounds=30, verbose=False),
                        lgb.log_evaluation(period=0),
                    ],
                    categorical_feature=self.categorical_indices,
                )
                proba = clf.predict_proba(X_train[va_idx])
                losses.append(log_loss(y_train[va_idx], proba))

            return float(np.mean(losses))

        study = optuna.create_study(direction="minimize", study_name="sc2_build_lgb")
        study.optimize(objective, n_trials=n_trials, timeout=timeout)

        best = study.best_params
        log.info("Optuna best trial — logloss=%.4f  params=%s", study.best_value, best)

        # Re-fit with best params on full training set
        best_full = {
            "objective": "multiclass",
            "num_class": len(BUILD_LABELS),
            "metric": "multi_logloss",
            "n_estimators": 800,
            "random_state": self.random_state,
            "verbose": -1,
        }
        best_full.update(best)
        self.model = lgb.LGBMClassifier(**best_full)
        self.model.fit(
            X_train,
            y_train,
            eval_set=[(X_val, y_val)],
            callbacks=[
                lgb.early_stopping(stopping_rounds=50, verbose=True),
                lgb.log_evaluation(period=50),
            ],
            categorical_feature=self.categorical_indices,
        )
        self._fitted = True

        return {
            "best_params": best,
            "best_logloss": study.best_value,
            "n_trials": len(study.trials),
        }

    # ---- serialisation ----------------------------------------------------
    def save(self, path: str = "sc2_build_classifier.txt") -> str:
        if self.model is not None:
            self.model.booster_.save_model(path)
            log.info("Model saved to %s", path)
        return path

    def load(self, path: str = "sc2_build_classifier.txt") -> None:
        if not LGB_AVAILABLE:
            log.warning("LightGBM not installed — cannot load model.")
            return
        booster = lgb.Booster(model_file=path)
        self.model = lgb.LGBMClassifier()
        self.model._Booster = booster
        self.model.fitted_ = True
        self.model._n_classes = len(BUILD_LABELS)
        self._fitted = True
        log.info("Model loaded from %s", path)


# ---------------------------------------------------------------------------
# Main — demonstrate full pipeline
# ---------------------------------------------------------------------------
def main() -> None:
    log.info("=== SC2 Build Classifier (LightGBM) ===")

    # 1. Generate data
    X, y, feat_names = generate_synthetic_dataset(n_samples=4000)
    log.info(
        "Dataset: %d samples, %d features, %d classes",
        X.shape[0],
        X.shape[1],
        len(BUILD_LABELS),
    )

    X_train, X_test, y_train, y_test = (
        train_test_split(X, y, test_size=0.2, stratify=y, random_state=42)
        if SK_AVAILABLE
        else (X[:3200], X[3200:], y[:3200], y[3200:])
    )

    # 2. Train classifier
    clf = SC2BuildClassifier(boosting_type="gbdt", n_estimators=400, learning_rate=0.05)
    clf.fit(X_train, y_train)

    # 3. Evaluate
    metrics = clf.evaluate(X_test, y_test)
    log.info("Test accuracy: %.4f", metrics["accuracy"])

    # 4. Feature importance
    clf.print_feature_importance(top_k=10)

    # 5. DART comparison
    dart_results = clf.compare_dart(X, y)
    if dart_results:
        for btype, vals in dart_results.items():
            log.info(
                "  %s → acc=%.4f  logloss=%.4f",
                btype,
                vals["accuracy"],
                vals["log_loss"],
            )

    # 6. Confusion matrix
    clf.plot_confusion_matrix(X_test, y_test, save_path="sc2_build_confusion.png")

    # 7. Learning curves
    clf.plot_learning_curves(X, y, save_path="sc2_build_learning_curves.png")

    # 8. Bayesian optimisation (short run)
    opt_result = clf.bayesian_optimize(X, y, n_trials=10, timeout=120)
    if opt_result:
        log.info("Optimised logloss: %.4f", opt_result["best_logloss"])
        post_metrics = clf.evaluate(X_test, y_test)
        log.info("Post-optimisation accuracy: %.4f", post_metrics["accuracy"])

    # 9. Live prediction demo
    demo_state = {
        "game_loop": 5000,
        "minerals": 400,
        "vespene": 200,
        "supply_used": 44,
        "supply_cap": 52,
        "structures": [
            {"name": "Hatchery"},
            {"name": "SpawningPool"},
            {"name": "RoachWarren"},
        ],
        "units": [{"name": "Drone"}] * 16
        + [{"name": "Roach", "mineral_cost": 75, "vespene_cost": 25}] * 8,
        "enemy_units": [{"name": "Marine"}] * 5,
        "enemy_structures": [{"name": "Barracks"}],
        "opponent_race": "terran",
        "map_name": "EverDream",
        "first_gas_time": 50,
        "vespene_workers": 3,
    }
    build_label, confidence = clf.predict_build(demo_state)
    log.info("Live prediction: %s (confidence %.2f%%)", build_label, confidence * 100)

    log.info("=== Phase 588 complete ===")


if __name__ == "__main__":
    main()
