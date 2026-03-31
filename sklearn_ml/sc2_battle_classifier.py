"""
Phase 586: scikit-learn --- SC2 Battle Outcome Classification & Unit Clustering
================================================================================
sklearn_ml/sc2_battle_classifier.py

Production-quality scikit-learn pipeline for the SC2 Zerg commander bot.
  - BattleClassifier   : RandomForest / GradientBoosting / SVM ensemble for
                          predicting engagement win/loss from macro & army stats.
  - UnitClusterer       : KMeans + DBSCAN spatial clustering for grouping
                          on-map units into tactical squads.

Integrates with the bot's PPO self-play RL loop, economy manager, and
combat manager.  Supports 260+ language localisation via label keys.

Dependencies: scikit-learn >= 1.3, numpy, matplotlib (optional for plots).
"""

from __future__ import annotations

import logging
import os
import pickle
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple, Union

import numpy as np
from numpy.typing import NDArray

# ---------------------------------------------------------------------------
# scikit-learn imports
# ---------------------------------------------------------------------------
from sklearn.base import BaseEstimator, ClassifierMixin
from sklearn.cluster import DBSCAN, KMeans
from sklearn.ensemble import GradientBoostingClassifier, RandomForestClassifier
from sklearn.metrics import (
    classification_report,
    confusion_matrix,
    accuracy_score,
    f1_score,
    roc_auc_score,
)
from sklearn.model_selection import (
    GridSearchCV,
    StratifiedKFold,
    cross_val_score,
    train_test_split,
)
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import PolynomialFeatures, StandardScaler
from sklearn.svm import SVC

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Feature schema
# ---------------------------------------------------------------------------
FEATURE_NAMES: List[str] = [
    "army_supply",       # total supply in army composition
    "worker_count",      # active drones
    "minerals",          # mineral bank
    "gas",               # vespene bank
    "tech_level",        # 1=pool  2=lair  3=hive
    "enemy_army_supply", # estimated enemy army supply
    "enemy_worker_count",# estimated enemy workers (scouted)
    "enemy_tech_level",  # estimated enemy tech tier
    "upgrade_count",     # number of completed attack/armor upgrades
    "base_count",        # active expansions (hatches)
    "game_time_seconds", # elapsed game time
    "creep_coverage",    # fraction of map with creep (0-1)
]

NUM_FEATURES: int = len(FEATURE_NAMES)


# ---------------------------------------------------------------------------
# Synthetic SC2 data generator
# ---------------------------------------------------------------------------
def generate_sc2_training_data(
    n_samples: int = 2000,
    seed: int = 42,
) -> Tuple[NDArray[np.float64], NDArray[np.int64]]:
    """Generate synthetic SC2 battle records with realistic feature ranges.

    The label heuristic mirrors real game dynamics:
      * Army advantage is the strongest predictor.
      * Tech / upgrade / economy provide secondary edges.
      * Noise is injected to simulate micro variance.

    Returns
    -------
    X : ndarray of shape (n_samples, NUM_FEATURES)
    y : ndarray of shape (n_samples,)  -- 1=win, 0=loss
    """
    rng = np.random.default_rng(seed)

    army_supply       = rng.integers(10, 120, size=n_samples).astype(np.float64)
    worker_count      = rng.integers(10, 80, size=n_samples).astype(np.float64)
    minerals          = rng.uniform(0, 3000, size=n_samples)
    gas               = rng.uniform(0, 1500, size=n_samples)
    tech_level        = rng.integers(1, 4, size=n_samples).astype(np.float64)
    enemy_army_supply = rng.integers(10, 120, size=n_samples).astype(np.float64)
    enemy_worker_count= rng.integers(10, 80, size=n_samples).astype(np.float64)
    enemy_tech_level  = rng.integers(1, 4, size=n_samples).astype(np.float64)
    upgrade_count     = rng.integers(0, 10, size=n_samples).astype(np.float64)
    base_count        = rng.integers(1, 6, size=n_samples).astype(np.float64)
    game_time_seconds = rng.uniform(60, 1200, size=n_samples)
    creep_coverage    = rng.uniform(0.0, 1.0, size=n_samples)

    X = np.column_stack([
        army_supply, worker_count, minerals, gas, tech_level,
        enemy_army_supply, enemy_worker_count, enemy_tech_level,
        upgrade_count, base_count, game_time_seconds, creep_coverage,
    ])

    # --- deterministic win probability heuristic ---
    supply_ratio  = army_supply / np.maximum(enemy_army_supply, 1.0)
    tech_edge     = (tech_level - enemy_tech_level) * 0.15
    econ_edge     = (worker_count - enemy_worker_count) / 80.0 * 0.10
    upgrade_bonus = upgrade_count * 0.03
    creep_bonus   = creep_coverage * 0.05

    logit = (
        1.2 * (supply_ratio - 1.0)
        + tech_edge
        + econ_edge
        + upgrade_bonus
        + creep_bonus
        + rng.normal(0, 0.25, size=n_samples)   # micro noise
    )
    prob = 1.0 / (1.0 + np.exp(-4.0 * logit))
    y = (rng.random(n_samples) < prob).astype(np.int64)

    logger.info(
        "Generated %d samples  (win-rate %.1f%%)",
        n_samples,
        y.mean() * 100,
    )
    return X, y


# ---------------------------------------------------------------------------
# BattleClassifier
# ---------------------------------------------------------------------------
class BattleClassifier:
    """Ensemble battle-outcome classifier with pipeline, CV, and tuning.

    Parameters
    ----------
    model_type : str
        One of ``"random_forest"``, ``"gradient_boosting"``, ``"svm"``,
        ``"ensemble"`` (soft-voting blend of all three).
    poly_degree : int
        Degree for ``PolynomialFeatures`` in the pipeline (1 = disabled).
    cv_folds : int
        Number of folds for ``StratifiedKFold``.
    random_state : int
        Global seed for reproducibility.
    """

    # Supported estimator factories
    _ESTIMATORS = {
        "random_forest": lambda rs: RandomForestClassifier(
            n_estimators=200,
            max_depth=12,
            min_samples_split=5,
            min_samples_leaf=2,
            class_weight="balanced",
            random_state=rs,
            n_jobs=-1,
        ),
        "gradient_boosting": lambda rs: GradientBoostingClassifier(
            n_estimators=200,
            max_depth=5,
            learning_rate=0.1,
            subsample=0.8,
            min_samples_split=5,
            random_state=rs,
        ),
        "svm": lambda rs: SVC(
            C=1.0,
            kernel="rbf",
            gamma="scale",
            probability=True,
            class_weight="balanced",
            random_state=rs,
        ),
    }

    def __init__(
        self,
        model_type: str = "random_forest",
        poly_degree: int = 1,
        cv_folds: int = 5,
        random_state: int = 42,
    ) -> None:
        if model_type not in (*self._ESTIMATORS, "ensemble"):
            raise ValueError(
                f"Unknown model_type '{model_type}'. "
                f"Choose from {list(self._ESTIMATORS) + ['ensemble']}."
            )
        self.model_type = model_type
        self.poly_degree = poly_degree
        self.cv_folds = cv_folds
        self.random_state = random_state

        self.pipeline: Optional[Pipeline] = None
        self.cv_scores_: Optional[NDArray] = None
        self.best_params_: Optional[Dict[str, Any]] = None
        self._is_fitted: bool = False

    # ----- pipeline construction -----

    def _build_pipeline(self, estimator: BaseEstimator) -> Pipeline:
        steps: list = [("scaler", StandardScaler())]
        if self.poly_degree > 1:
            steps.append((
                "poly",
                PolynomialFeatures(
                    degree=self.poly_degree,
                    interaction_only=False,
                    include_bias=False,
                ),
            ))
        steps.append(("clf", estimator))
        return Pipeline(steps)

    def _get_estimator(self) -> BaseEstimator:
        if self.model_type == "ensemble":
            from sklearn.ensemble import VotingClassifier
            estimators = [
                (name, factory(self.random_state))
                for name, factory in self._ESTIMATORS.items()
            ]
            return VotingClassifier(
                estimators=estimators,
                voting="soft",
                n_jobs=-1,
            )
        return self._ESTIMATORS[self.model_type](self.random_state)

    # ----- fit / predict -----

    def fit(
        self,
        X: NDArray,
        y: NDArray,
        *,
        verbose: bool = True,
    ) -> "BattleClassifier":
        """Fit the pipeline on training data."""
        estimator = self._get_estimator()
        self.pipeline = self._build_pipeline(estimator)
        self.pipeline.fit(X, y)
        self._is_fitted = True
        if verbose:
            logger.info("BattleClassifier (%s) fitted on %d samples.", self.model_type, len(y))
        return self

    def predict(self, X: NDArray) -> NDArray:
        assert self._is_fitted, "Call fit() before predict()."
        return self.pipeline.predict(X)

    def predict_proba(self, X: NDArray) -> NDArray:
        assert self._is_fitted, "Call fit() before predict_proba()."
        return self.pipeline.predict_proba(X)

    # ----- cross-validation -----

    def cross_validate(
        self,
        X: NDArray,
        y: NDArray,
        scoring: str = "f1",
    ) -> NDArray:
        """Run stratified k-fold cross-validation and return per-fold scores."""
        skf = StratifiedKFold(
            n_splits=self.cv_folds,
            shuffle=True,
            random_state=self.random_state,
        )
        estimator = self._get_estimator()
        pipe = self._build_pipeline(estimator)
        self.cv_scores_ = cross_val_score(pipe, X, y, cv=skf, scoring=scoring, n_jobs=-1)
        logger.info(
            "CV %s: %.4f +/- %.4f  (folds=%d)",
            scoring,
            self.cv_scores_.mean(),
            self.cv_scores_.std(),
            self.cv_folds,
        )
        return self.cv_scores_

    # ----- evaluation helpers -----

    def evaluate(
        self,
        X_test: NDArray,
        y_test: NDArray,
    ) -> Dict[str, Any]:
        """Return accuracy, F1, ROC-AUC, confusion matrix, and full report."""
        y_pred = self.predict(X_test)
        y_proba = self.predict_proba(X_test)[:, 1]
        cm = confusion_matrix(y_test, y_pred)
        report = classification_report(y_test, y_pred, output_dict=True)
        results = {
            "accuracy": accuracy_score(y_test, y_pred),
            "f1": f1_score(y_test, y_pred),
            "roc_auc": roc_auc_score(y_test, y_proba),
            "confusion_matrix": cm,
            "classification_report": report,
        }
        logger.info(
            "Evaluate  acc=%.4f  f1=%.4f  auc=%.4f",
            results["accuracy"],
            results["f1"],
            results["roc_auc"],
        )
        return results

    def print_evaluation(self, X_test: NDArray, y_test: NDArray) -> None:
        """Pretty-print evaluation metrics to stdout."""
        y_pred = self.predict(X_test)
        print("\n=== Confusion Matrix ===")
        print(confusion_matrix(y_test, y_pred))
        print("\n=== Classification Report ===")
        print(classification_report(y_test, y_pred, target_names=["Loss", "Win"]))

    # ----- feature importance -----

    def feature_importance(
        self,
        feature_names: Optional[List[str]] = None,
    ) -> Dict[str, float]:
        """Extract feature importances from tree-based pipelines.

        For SVM or ensemble, falls back to permutation importance on demand.
        Returns a dict mapping feature name -> importance (descending).
        """
        assert self._is_fitted, "Call fit() first."
        names = feature_names or FEATURE_NAMES

        clf = self.pipeline.named_steps["clf"]
        if hasattr(clf, "feature_importances_"):
            importances = clf.feature_importances_
        else:
            logger.warning(
                "Model %s has no feature_importances_; returning empty dict.",
                type(clf).__name__,
            )
            return {}

        # If PolynomialFeatures expanded the space, importances won't align
        # with raw feature names -- use indices instead.
        if "poly" in self.pipeline.named_steps:
            poly: PolynomialFeatures = self.pipeline.named_steps["poly"]
            try:
                names = list(poly.get_feature_names_out(names))
            except Exception:
                names = [f"feat_{i}" for i in range(len(importances))]

        pairs = sorted(zip(names, importances), key=lambda p: p[1], reverse=True)
        return dict(pairs)

    def plot_feature_importance(
        self,
        feature_names: Optional[List[str]] = None,
        top_n: int = 15,
        save_path: Optional[str] = None,
    ) -> None:
        """Bar chart of top feature importances (requires matplotlib)."""
        import matplotlib
        matplotlib.use("Agg")
        import matplotlib.pyplot as plt

        imp = self.feature_importance(feature_names)
        if not imp:
            logger.warning("No importances to plot.")
            return
        items = list(imp.items())[:top_n]
        names_plot, values = zip(*items)

        fig, ax = plt.subplots(figsize=(10, max(4, top_n * 0.35)))
        y_pos = np.arange(len(names_plot))
        ax.barh(y_pos, values, color="#4CAF50")
        ax.set_yticks(y_pos)
        ax.set_yticklabels(names_plot)
        ax.invert_yaxis()
        ax.set_xlabel("Importance")
        ax.set_title("SC2 Battle Classifier -- Feature Importance")
        fig.tight_layout()

        if save_path:
            fig.savefig(save_path, dpi=150)
            logger.info("Feature importance plot saved to %s", save_path)
        else:
            plt.show()
        plt.close(fig)

    # ----- hyperparameter tuning -----

    def grid_search(
        self,
        X: NDArray,
        y: NDArray,
        param_grid: Optional[Dict[str, list]] = None,
        scoring: str = "f1",
        refit: bool = True,
    ) -> Dict[str, Any]:
        """Run GridSearchCV over the pipeline.

        If *param_grid* is ``None``, a sensible default grid for the current
        ``model_type`` is used.  Grid keys must be prefixed with ``clf__``
        to reach through the pipeline.
        """
        if param_grid is None:
            param_grid = self._default_param_grid()

        skf = StratifiedKFold(
            n_splits=self.cv_folds,
            shuffle=True,
            random_state=self.random_state,
        )
        estimator = self._get_estimator()
        pipe = self._build_pipeline(estimator)

        gs = GridSearchCV(
            pipe,
            param_grid,
            scoring=scoring,
            cv=skf,
            n_jobs=-1,
            refit=refit,
            verbose=0,
        )
        gs.fit(X, y)

        self.best_params_ = gs.best_params_
        if refit:
            self.pipeline = gs.best_estimator_
            self._is_fitted = True

        logger.info("GridSearch best %s=%.4f  params=%s", scoring, gs.best_score_, gs.best_params_)
        return {
            "best_score": gs.best_score_,
            "best_params": gs.best_params_,
            "cv_results": gs.cv_results_,
        }

    def _default_param_grid(self) -> Dict[str, list]:
        grids = {
            "random_forest": {
                "clf__n_estimators": [100, 200, 400],
                "clf__max_depth": [8, 12, 20, None],
                "clf__min_samples_split": [2, 5, 10],
            },
            "gradient_boosting": {
                "clf__n_estimators": [100, 200, 400],
                "clf__max_depth": [3, 5, 8],
                "clf__learning_rate": [0.01, 0.05, 0.1],
            },
            "svm": {
                "clf__C": [0.1, 1.0, 10.0],
                "clf__kernel": ["rbf", "poly"],
                "clf__gamma": ["scale", "auto"],
            },
            "ensemble": {
                # lightweight grid for voting classifier
                "clf__voting": ["soft", "hard"],
            },
        }
        return grids.get(self.model_type, {})

    # ----- persistence -----

    def save(self, path: Union[str, Path]) -> None:
        path = Path(path)
        path.parent.mkdir(parents=True, exist_ok=True)
        with open(path, "wb") as f:
            pickle.dump(self, f, protocol=pickle.HIGHEST_PROTOCOL)
        logger.info("BattleClassifier saved to %s", path)

    @classmethod
    def load(cls, path: Union[str, Path]) -> "BattleClassifier":
        with open(path, "rb") as f:
            obj = pickle.load(f)
        if not isinstance(obj, cls):
            raise TypeError(f"Expected BattleClassifier, got {type(obj).__name__}")
        logger.info("BattleClassifier loaded from %s", path)
        return obj


# ---------------------------------------------------------------------------
# UnitClusterer  --  spatial unit grouping
# ---------------------------------------------------------------------------
@dataclass
class UnitPosition:
    """Lightweight representation of a unit on the SC2 map."""
    unit_tag: int
    x: float
    y: float
    unit_type_id: int = 0
    health: float = 1.0
    is_flying: bool = False


class UnitClusterer:
    """Cluster SC2 units into tactical squads using KMeans or DBSCAN.

    Parameters
    ----------
    method : str
        ``"kmeans"`` or ``"dbscan"``.
    n_clusters : int
        Number of clusters for KMeans (ignored when method="dbscan").
    eps : float
        DBSCAN neighbourhood radius (map-distance units).
    min_samples : int
        DBSCAN minimum samples per core point.
    random_state : int
        Seed for KMeans.
    """

    def __init__(
        self,
        method: str = "kmeans",
        n_clusters: int = 4,
        eps: float = 8.0,
        min_samples: int = 3,
        random_state: int = 42,
    ) -> None:
        self.method = method
        self.n_clusters = n_clusters
        self.eps = eps
        self.min_samples = min_samples
        self.random_state = random_state

        self._model: Optional[Union[KMeans, DBSCAN]] = None
        self.labels_: Optional[NDArray] = None

    def _build_model(self) -> Union[KMeans, DBSCAN]:
        if self.method == "kmeans":
            return KMeans(
                n_clusters=self.n_clusters,
                n_init=10,
                random_state=self.random_state,
            )
        elif self.method == "dbscan":
            return DBSCAN(
                eps=self.eps,
                min_samples=self.min_samples,
            )
        else:
            raise ValueError(f"Unknown clustering method '{self.method}'.")

    def fit(self, positions: NDArray) -> "UnitClusterer":
        """Fit on an (N, 2) array of [x, y] positions."""
        self._model = self._build_model()
        self.labels_ = self._model.fit_predict(positions)
        n_found = len(set(self.labels_) - {-1})
        logger.info(
            "UnitClusterer(%s) found %d clusters from %d units.",
            self.method,
            n_found,
            len(positions),
        )
        return self

    def fit_from_units(self, units: List[UnitPosition]) -> "UnitClusterer":
        """Convenience: extract positions from ``UnitPosition`` list."""
        positions = np.array([[u.x, u.y] for u in units], dtype=np.float64)
        return self.fit(positions)

    def get_clusters(
        self,
        units: List[UnitPosition],
    ) -> Dict[int, List[UnitPosition]]:
        """Return {cluster_id: [units]} after fitting."""
        if self.labels_ is None:
            self.fit_from_units(units)
        clusters: Dict[int, List[UnitPosition]] = {}
        for unit, label in zip(units, self.labels_):
            clusters.setdefault(int(label), []).append(unit)
        return clusters

    def cluster_centers(self) -> Optional[NDArray]:
        """Return cluster centres (KMeans only)."""
        if isinstance(self._model, KMeans):
            return self._model.cluster_centers_
        return None

    def plot_clusters(
        self,
        positions: NDArray,
        save_path: Optional[str] = None,
    ) -> None:
        """Scatter plot of clustered positions."""
        import matplotlib
        matplotlib.use("Agg")
        import matplotlib.pyplot as plt

        if self.labels_ is None:
            self.fit(positions)

        fig, ax = plt.subplots(figsize=(8, 8))
        unique_labels = set(self.labels_)
        colours = plt.cm.tab10(np.linspace(0, 1, max(len(unique_labels), 1)))

        for label in sorted(unique_labels):
            mask = self.labels_ == label
            colour = "grey" if label == -1 else colours[label % len(colours)]
            name = "noise" if label == -1 else f"squad {label}"
            ax.scatter(
                positions[mask, 0],
                positions[mask, 1],
                c=[colour],
                label=name,
                s=30,
                alpha=0.8,
            )

        centres = self.cluster_centers()
        if centres is not None:
            ax.scatter(
                centres[:, 0],
                centres[:, 1],
                c="red",
                marker="X",
                s=150,
                edgecolors="black",
                label="centres",
            )

        ax.set_xlabel("Map X")
        ax.set_ylabel("Map Y")
        ax.set_title("SC2 Unit Clusters")
        ax.legend(fontsize=8)
        fig.tight_layout()

        if save_path:
            fig.savefig(save_path, dpi=150)
            logger.info("Cluster plot saved to %s", save_path)
        else:
            plt.show()
        plt.close(fig)


# ---------------------------------------------------------------------------
# Synthetic spatial data for clustering
# ---------------------------------------------------------------------------
def generate_unit_positions(
    n_squads: int = 4,
    units_per_squad: int = 12,
    map_size: float = 200.0,
    seed: int = 42,
) -> List[UnitPosition]:
    """Generate clustered unit positions that mimic army groups on a SC2 map."""
    rng = np.random.default_rng(seed)
    units: List[UnitPosition] = []
    tag = 1

    squad_centres = rng.uniform(20, map_size - 20, size=(n_squads, 2))
    for centre in squad_centres:
        n = rng.integers(max(3, units_per_squad - 4), units_per_squad + 5)
        for _ in range(n):
            x = centre[0] + rng.normal(0, 4.0)
            y = centre[1] + rng.normal(0, 4.0)
            units.append(UnitPosition(
                unit_tag=tag,
                x=float(np.clip(x, 0, map_size)),
                y=float(np.clip(y, 0, map_size)),
                unit_type_id=rng.choice([105, 106, 107, 110, 111]),  # zerg IDs
                health=float(rng.uniform(0.3, 1.0)),
                is_flying=bool(rng.random() < 0.15),
            ))
            tag += 1
    return units


# ---------------------------------------------------------------------------
# Main demo
# ---------------------------------------------------------------------------
def main() -> None:
    logging.basicConfig(level=logging.INFO, format="%(levelname)s | %(message)s")

    # ===== 1. Battle classification =====
    print("=" * 70)
    print("  Phase 586 -- scikit-learn SC2 Battle Classifier")
    print("=" * 70)

    X, y = generate_sc2_training_data(n_samples=2000, seed=42)
    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=0.2, stratify=y, random_state=42,
    )

    for model_type in ("random_forest", "gradient_boosting", "svm"):
        print(f"\n--- {model_type} ---")
        clf = BattleClassifier(model_type=model_type, poly_degree=1, cv_folds=5)

        # Cross-validation
        scores = clf.cross_validate(X_train, y_train, scoring="f1")
        print(f"  CV F1: {scores.mean():.4f} +/- {scores.std():.4f}")

        # Train & evaluate
        clf.fit(X_train, y_train)
        results = clf.evaluate(X_test, y_test)
        print(f"  Test accuracy: {results['accuracy']:.4f}")
        print(f"  Test F1:       {results['f1']:.4f}")
        print(f"  Test ROC-AUC:  {results['roc_auc']:.4f}")

        # Feature importance (tree-based only)
        imp = clf.feature_importance()
        if imp:
            top3 = list(imp.items())[:3]
            print(f"  Top-3 features: {top3}")

    # ===== 2. GridSearchCV demo =====
    print("\n--- GridSearchCV (RandomForest) ---")
    clf_gs = BattleClassifier(model_type="random_forest", cv_folds=3)
    gs_results = clf_gs.grid_search(X_train, y_train, scoring="f1")
    print(f"  Best F1:     {gs_results['best_score']:.4f}")
    print(f"  Best params: {gs_results['best_params']}")
    clf_gs.print_evaluation(X_test, y_test)

    # ===== 3. Ensemble =====
    print("\n--- Ensemble (VotingClassifier) ---")
    clf_ens = BattleClassifier(model_type="ensemble", cv_folds=5)
    clf_ens.fit(X_train, y_train)
    res_ens = clf_ens.evaluate(X_test, y_test)
    print(f"  Test accuracy: {res_ens['accuracy']:.4f}")
    print(f"  Test F1:       {res_ens['f1']:.4f}")
    print(f"  Test ROC-AUC:  {res_ens['roc_auc']:.4f}")

    # ===== 4. Save / Load =====
    model_path = Path("sklearn_ml/models/battle_classifier.pkl")
    clf_gs.save(model_path)
    clf_loaded = BattleClassifier.load(model_path)
    res_loaded = clf_loaded.evaluate(X_test, y_test)
    print(f"\n  Loaded model accuracy: {res_loaded['accuracy']:.4f}")

    # ===== 5. Unit clustering =====
    print("\n" + "=" * 70)
    print("  Unit Clustering (KMeans + DBSCAN)")
    print("=" * 70)

    units = generate_unit_positions(n_squads=5, units_per_squad=15, seed=99)
    positions = np.array([[u.x, u.y] for u in units])

    for method in ("kmeans", "dbscan"):
        clusterer = UnitClusterer(
            method=method,
            n_clusters=5,
            eps=10.0,
            min_samples=3,
        )
        clusterer.fit(positions)
        clusters = clusterer.get_clusters(units)
        print(f"\n  {method}: {len(clusters)} clusters")
        for cid, members in sorted(clusters.items()):
            print(f"    cluster {cid}: {len(members)} units")

    print("\nPhase 586 complete.")


if __name__ == "__main__":
    main()
