# Phase 583: Keras ML
"""
sc2_predictor.py — StarCraft II Outcome Prediction with Keras / TensorFlow
Predicts win/loss probability and classifies build orders from game state features.

Graceful fallback to a pure-NumPy implementation when TensorFlow/Keras is absent.
"""

from __future__ import annotations

import sys
import time
import logging
import random
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple

import numpy as np

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
log = logging.getLogger("sc2_predictor")

# ---------------------------------------------------------------------------
# Optional Keras / TensorFlow import — graceful fallback
# ---------------------------------------------------------------------------
try:
    import tensorflow as tf
    from tensorflow import keras
    from tensorflow.keras import layers, regularizers
    from tensorflow.keras.callbacks import (
        EarlyStopping, ReduceLROnPlateau, ModelCheckpoint,
    )
    TF_AVAILABLE = True
    log.info("TensorFlow %s / Keras available.", tf.__version__)
except ImportError:
    TF_AVAILABLE = False
    log.warning(
        "TensorFlow/Keras not installed. Running pure-NumPy fallback. "
        "Install with: pip install tensorflow"
    )

# ---------------------------------------------------------------------------
# Game state feature schema
# ---------------------------------------------------------------------------
#
# Feature vector (length 16):
#  0  minerals_normalised      (0–1, max 2000)
#  1  gas_normalised           (0–1, max 1500)
#  2  supply_used_normalised   (0–1, max 200)
#  3  supply_cap_normalised    (0–1, max 200)
#  4  worker_count_normalised  (0–1, max 80)
#  5  army_supply_normalised   (0–1, max 120)
#  6  base_count               (0–1, max 6)
#  7  tech_level               (0–1, max 3: none / tier1 / tier2 / tier3)
#  8  game_time_normalised     (0–1, max 1200s)
#  9  opponent_army_normalised (0–1, max 120)
# 10  map_control              (0–1, fraction of map under control)
# 11  opponent_base_count      (0–1, max 6)
# 12  energy_normalised        (Nexus/CC/Hatch special ability energy, 0–1, max 200)
# 13  upgrade_count_normalised (0–1, max 10)
# 14  kill_score_normalised    (0–1, max 5000)
# 15  loss_score_normalised    (0–1, max 5000)

FEATURE_DIM = 16
FEATURE_NAMES = [
    "minerals", "gas", "supply_used", "supply_cap", "workers",
    "army_supply", "base_count", "tech_level", "game_time",
    "opp_army", "map_control", "opp_bases", "energy",
    "upgrades", "kill_score", "loss_score",
]

BUILD_ORDER_CLASSES = [
    "macro_economy",      # 0
    "early_aggression",   # 1
    "tech_rush",          # 2
    "defensive_turtle",   # 3
    "timing_attack",      # 4
]
NUM_BUILD_CLASSES = len(BUILD_ORDER_CLASSES)


# ---------------------------------------------------------------------------
# SC2FeatureExtractor
# ---------------------------------------------------------------------------

@dataclass
class GameState:
    """Raw game state snapshot from the SC2 API."""
    minerals: float = 50.0
    gas: float = 0.0
    supply_used: float = 12.0
    supply_cap: float = 14.0
    worker_count: float = 12.0
    army_supply: float = 0.0
    base_count: float = 1.0
    tech_level: float = 0.0        # 0=none, 1=tier1, 2=tier2, 3=tier3
    game_time: float = 0.0         # seconds
    opponent_army: float = 0.0
    map_control: float = 0.5
    opponent_base_count: float = 1.0
    energy: float = 50.0
    upgrade_count: float = 0.0
    kill_score: float = 0.0
    loss_score: float = 0.0


class SC2FeatureExtractor:
    """Converts a GameState into a normalised feature vector."""

    NORMALISATION_MAX = np.array([
        2000.0,   # minerals
        1500.0,   # gas
        200.0,    # supply_used
        200.0,    # supply_cap
        80.0,     # workers
        120.0,    # army_supply
        6.0,      # base_count
        3.0,      # tech_level
        1200.0,   # game_time
        120.0,    # opp_army
        1.0,      # map_control  (already 0-1)
        6.0,      # opp_bases
        200.0,    # energy
        10.0,     # upgrades
        5000.0,   # kill_score
        5000.0,   # loss_score
    ], dtype=np.float32)

    def extract(self, state: GameState) -> np.ndarray:
        """Returns a normalised float32 vector of length FEATURE_DIM."""
        raw = np.array([
            state.minerals,
            state.gas,
            state.supply_used,
            state.supply_cap,
            state.worker_count,
            state.army_supply,
            state.base_count,
            state.tech_level,
            state.game_time,
            state.opponent_army,
            state.map_control,
            state.opponent_base_count,
            state.energy,
            state.upgrade_count,
            state.kill_score,
            state.loss_score,
        ], dtype=np.float32)
        return np.clip(raw / self.NORMALISATION_MAX, 0.0, 1.0)

    def extract_batch(self, states: List[GameState]) -> np.ndarray:
        """Extract features for a list of states → shape (N, FEATURE_DIM)."""
        return np.stack([self.extract(s) for s in states], axis=0)


# ---------------------------------------------------------------------------
# Pure-NumPy fallback model
# ---------------------------------------------------------------------------

def _sigmoid(x: np.ndarray) -> np.ndarray:
    return 1.0 / (1.0 + np.exp(-x))

def _relu(x: np.ndarray) -> np.ndarray:
    return np.maximum(0.0, x)

def _softmax(x: np.ndarray) -> np.ndarray:
    e = np.exp(x - x.max(axis=-1, keepdims=True))
    return e / e.sum(axis=-1, keepdims=True)


class NumpyDenseLayer:
    """A single fully-connected layer with optional activation."""

    def __init__(
        self,
        in_dim: int,
        out_dim: int,
        activation: str = "relu",
        seed: int = 42,
    ) -> None:
        rng = np.random.default_rng(seed)
        # He initialisation for relu, Xavier for others
        scale = np.sqrt(2.0 / in_dim) if activation == "relu" else np.sqrt(1.0 / in_dim)
        self.W = rng.normal(0.0, scale, (in_dim, out_dim)).astype(np.float32)
        self.b = np.zeros(out_dim, dtype=np.float32)
        self.activation = activation

    def forward(self, x: np.ndarray) -> np.ndarray:
        z = x @ self.W + self.b
        if self.activation == "relu":
            return _relu(z)
        if self.activation == "sigmoid":
            return _sigmoid(z)
        if self.activation == "softmax":
            return _softmax(z)
        return z   # linear


class NumpyWinPredictor:
    """
    Pure-NumPy binary classifier:
    input(16) → Dense(128, relu) → Dense(64, relu) → Dense(1, sigmoid)
    """

    def __init__(self) -> None:
        self.layers = [
            NumpyDenseLayer(FEATURE_DIM, 128, "relu",    seed=1),
            NumpyDenseLayer(128,         64,  "relu",    seed=2),
            NumpyDenseLayer(64,          1,   "sigmoid", seed=3),
        ]

    def predict(self, x: np.ndarray) -> np.ndarray:
        h = x
        for layer in self.layers:
            h = layer.forward(h)
        return h   # shape (..., 1)

    def fit(self, X: np.ndarray, y: np.ndarray, epochs: int = 10, lr: float = 0.01) -> List[float]:
        """
        Mini-batch SGD with binary cross-entropy.
        Returns list of epoch losses.
        """
        losses: List[float] = []
        n = len(X)
        batch_size = 64
        for epoch in range(epochs):
            idx = np.random.permutation(n)
            epoch_loss = 0.0
            batches = 0
            for start in range(0, n, batch_size):
                batch_idx = idx[start:start + batch_size]
                xb, yb = X[batch_idx], y[batch_idx]

                # Forward
                activations = [xb]
                h = xb
                for layer in self.layers:
                    h = layer.forward(h)
                    activations.append(h)

                pred = activations[-1]
                loss = -np.mean(
                    yb * np.log(pred + 1e-7) + (1 - yb) * np.log(1 - pred + 1e-7)
                )
                epoch_loss += loss
                batches += 1

                # Backward (simplified gradient update for output layer only)
                delta = pred - yb.reshape(-1, 1)
                prev_act = activations[-2]
                grad_W = prev_act.T @ delta / len(xb)
                grad_b = delta.mean(axis=0)
                self.layers[-1].W -= lr * grad_W
                self.layers[-1].b -= lr * grad_b

            losses.append(epoch_loss / batches)
            if (epoch + 1) % 5 == 0 or epoch == 0:
                log.info("  [NumPy WinPredictor] Epoch %d/%d — loss=%.4f",
                         epoch + 1, epochs, losses[-1])
        return losses

    def evaluate(self, X: np.ndarray, y: np.ndarray) -> Dict[str, float]:
        preds = self.predict(X).squeeze()
        pred_labels = (preds >= 0.5).astype(int)
        accuracy = (pred_labels == y.astype(int)).mean()
        loss = -np.mean(y * np.log(preds + 1e-7) + (1 - y) * np.log(1 - preds + 1e-7))
        return {"loss": float(loss), "accuracy": float(accuracy)}


class NumpyBuildOrderClassifier:
    """
    Pure-NumPy multi-class classifier:
    input(16) → Dense(128, relu) → Dense(64, relu) → Dense(5, softmax)
    """

    def __init__(self) -> None:
        self.layers = [
            NumpyDenseLayer(FEATURE_DIM, 128,              "relu",    seed=10),
            NumpyDenseLayer(128,         64,               "relu",    seed=11),
            NumpyDenseLayer(64,          NUM_BUILD_CLASSES, "softmax", seed=12),
        ]

    def predict(self, x: np.ndarray) -> np.ndarray:
        h = x
        for layer in self.layers:
            h = layer.forward(h)
        return h   # shape (..., NUM_BUILD_CLASSES)

    def predict_class(self, x: np.ndarray) -> np.ndarray:
        return np.argmax(self.predict(x), axis=-1)


# ---------------------------------------------------------------------------
# Keras-based models (used when TF_AVAILABLE)
# ---------------------------------------------------------------------------

def build_win_predictor_keras(
    input_dim: int = FEATURE_DIM,
    l2_reg: float = 1e-4,
    dropout_rate: float = 0.3,
) -> "keras.Model":
    """
    Sequential model:
      Input(16) → Dense(128, relu) → Dropout → Dense(64, relu) → Dense(1, sigmoid)
    """
    reg = regularizers.l2(l2_reg)

    model = keras.Sequential(
        [
            layers.Input(shape=(input_dim,), name="game_state_input"),
            layers.Dense(128, activation="relu", kernel_regularizer=reg, name="dense_1"),
            layers.BatchNormalization(name="bn_1"),
            layers.Dropout(dropout_rate, name="dropout_1"),
            layers.Dense(64, activation="relu", kernel_regularizer=reg, name="dense_2"),
            layers.BatchNormalization(name="bn_2"),
            layers.Dropout(dropout_rate / 2, name="dropout_2"),
            layers.Dense(32, activation="relu", kernel_regularizer=reg, name="dense_3"),
            layers.Dense(1, activation="sigmoid", name="win_probability"),
        ],
        name="SC2WinPredictor",
    )
    model.compile(
        optimizer=keras.optimizers.Adam(learning_rate=3e-4),
        loss="binary_crossentropy",
        metrics=["accuracy", keras.metrics.AUC(name="auc")],
    )
    return model


def build_build_order_classifier_keras(
    input_dim: int = FEATURE_DIM,
    num_classes: int = NUM_BUILD_CLASSES,
    l2_reg: float = 1e-4,
    dropout_rate: float = 0.3,
) -> "keras.Model":
    """
    Multi-class classifier for predicting build order style.
    Input(16) → Dense(128) → Dense(64) → Dense(5, softmax)
    """
    reg = regularizers.l2(l2_reg)

    model = keras.Sequential(
        [
            layers.Input(shape=(input_dim,), name="game_state_input"),
            layers.Dense(128, activation="relu", kernel_regularizer=reg, name="dense_1"),
            layers.BatchNormalization(name="bn_1"),
            layers.Dropout(dropout_rate, name="dropout_1"),
            layers.Dense(64, activation="relu", kernel_regularizer=reg, name="dense_2"),
            layers.BatchNormalization(name="bn_2"),
            layers.Dropout(dropout_rate / 2, name="dropout_2"),
            layers.Dense(num_classes, activation="softmax", name="build_order_class"),
        ],
        name="SC2BuildOrderClassifier",
    )
    model.compile(
        optimizer=keras.optimizers.Adam(learning_rate=3e-4),
        loss="sparse_categorical_crossentropy",
        metrics=["accuracy"],
    )
    return model


# ---------------------------------------------------------------------------
# Synthetic data generation
# ---------------------------------------------------------------------------

def generate_synthetic_data(
    n_samples: int = 5000,
    seed: int = 42,
) -> Tuple[np.ndarray, np.ndarray, np.ndarray]:
    """
    Generate synthetic training data (features, win_labels, build_order_labels).

    Win heuristic:
      High workers + high map_control + more bases than opponent → likely win.
    """
    rng = np.random.default_rng(seed)

    features = rng.uniform(0.0, 1.0, (n_samples, FEATURE_DIM)).astype(np.float32)

    # Heuristic win labels based on economic and military factors
    worker_norm   = features[:, 4]    # workers
    army_norm     = features[:, 5]    # army supply
    bases         = features[:, 6]    # base_count
    opp_army      = features[:, 9]    # opponent_army
    map_ctrl      = features[:, 10]   # map_control
    opp_bases     = features[:, 11]   # opp_bases

    win_score = (
        0.30 * worker_norm
        + 0.25 * army_norm
        + 0.20 * map_ctrl
        + 0.15 * bases
        - 0.20 * opp_army
        - 0.10 * opp_bases
        + rng.uniform(-0.15, 0.15, n_samples)   # noise
    )
    win_labels = (win_score > 0.5).astype(np.float32)

    # Build order labels — assign based on tech_level, timing, and army composition
    tech   = features[:, 7]   # tech_level
    time_  = features[:, 8]   # game_time
    army_s = features[:, 5]

    build_labels = np.zeros(n_samples, dtype=np.int32)
    for i in range(n_samples):
        if tech[i] > 0.6:
            build_labels[i] = 2   # tech_rush
        elif time_[i] < 0.25 and army_s[i] > 0.4:
            build_labels[i] = 1   # early_aggression
        elif worker_norm[i] > 0.6 and bases[i] > 0.5:
            build_labels[i] = 0   # macro_economy
        elif opp_army[i] > 0.6:
            build_labels[i] = 3   # defensive_turtle
        else:
            build_labels[i] = 4   # timing_attack

    return features, win_labels, build_labels


# ---------------------------------------------------------------------------
# WinPredictor (unified interface)
# ---------------------------------------------------------------------------

class WinPredictor:
    """
    Unified win-probability predictor.
    Uses Keras when TensorFlow is available, otherwise NumPy fallback.
    """

    def __init__(self) -> None:
        self.extractor = SC2FeatureExtractor()
        if TF_AVAILABLE:
            self._model = build_win_predictor_keras()
            self._backend = "keras"
            log.info("WinPredictor using Keras backend.")
        else:
            self._model = NumpyWinPredictor()
            self._backend = "numpy"
            log.info("WinPredictor using NumPy fallback backend.")
        self._trained = False

    def train(
        self,
        X: np.ndarray,
        y: np.ndarray,
        *,
        epochs: int = 30,
        validation_split: float = 0.15,
        verbose: int = 0,
    ) -> Any:
        """Train the model. Returns history or list of losses."""
        log.info("Training WinPredictor (%s) on %d samples...", self._backend, len(X))
        if TF_AVAILABLE:
            callbacks = [
                EarlyStopping(monitor="val_loss", patience=5, restore_best_weights=True),
                ReduceLROnPlateau(monitor="val_loss", factor=0.5, patience=3, min_lr=1e-6),
            ]
            history = self._model.fit(
                X, y,
                epochs=epochs,
                batch_size=128,
                validation_split=validation_split,
                callbacks=callbacks,
                verbose=verbose,
            )
            self._trained = True
            return history
        else:
            losses = self._model.fit(X, y, epochs=min(epochs, 20), lr=0.005)
            self._trained = True
            return losses

    def evaluate(self, X: np.ndarray, y: np.ndarray) -> Dict[str, float]:
        if TF_AVAILABLE:
            results = self._model.evaluate(X, y, verbose=0)
            metric_names = self._model.metrics_names
            return dict(zip(metric_names, results))
        return self._model.evaluate(X, y)

    def predict(self, state_or_features) -> float:
        """
        Predict win probability for a single GameState or feature vector.
        Returns a float in [0, 1].
        """
        if isinstance(state_or_features, GameState):
            features = self.extractor.extract(state_or_features).reshape(1, -1)
        else:
            features = np.array(state_or_features, dtype=np.float32).reshape(1, -1)

        if TF_AVAILABLE:
            prob = float(self._model.predict(features, verbose=0)[0, 0])
        else:
            prob = float(self._model.predict(features)[0, 0])
        return prob

    def save(self, path: str) -> None:
        if TF_AVAILABLE:
            self._model.save(path)
            log.info("Keras model saved to %s", path)
        else:
            log.info("NumPy model save not implemented (no-op).")

    @property
    def summary(self) -> str:
        if TF_AVAILABLE:
            lines: List[str] = []
            self._model.summary(print_fn=lines.append)
            return "\n".join(lines)
        return "NumPy WinPredictor: 16→128→64→1 (sigmoid)"


# ---------------------------------------------------------------------------
# BuildOrderClassifier (unified interface)
# ---------------------------------------------------------------------------

class BuildOrderClassifier:
    """
    Unified build order multi-class classifier.
    """

    def __init__(self) -> None:
        self.extractor = SC2FeatureExtractor()
        if TF_AVAILABLE:
            self._model = build_build_order_classifier_keras()
            self._backend = "keras"
            log.info("BuildOrderClassifier using Keras backend.")
        else:
            self._model = NumpyBuildOrderClassifier()
            self._backend = "numpy"
            log.info("BuildOrderClassifier using NumPy fallback backend.")
        self._trained = False

    def train(
        self,
        X: np.ndarray,
        y: np.ndarray,
        *,
        epochs: int = 30,
        validation_split: float = 0.15,
        verbose: int = 0,
    ) -> Any:
        log.info(
            "Training BuildOrderClassifier (%s) on %d samples...",
            self._backend, len(X),
        )
        if TF_AVAILABLE:
            callbacks = [
                EarlyStopping(monitor="val_loss", patience=5, restore_best_weights=True),
            ]
            history = self._model.fit(
                X, y,
                epochs=epochs,
                batch_size=128,
                validation_split=validation_split,
                callbacks=callbacks,
                verbose=verbose,
            )
            self._trained = True
            return history
        else:
            # NumPy model has no training implemented for multi-class (weights random)
            log.info("NumPy BuildOrderClassifier: using random-initialised weights.")
            self._trained = True
            return []

    def predict(self, state_or_features) -> Tuple[str, float]:
        """
        Predict the build order class and confidence.
        Returns (class_name, confidence).
        """
        if isinstance(state_or_features, GameState):
            features = self.extractor.extract(state_or_features).reshape(1, -1)
        else:
            features = np.array(state_or_features, dtype=np.float32).reshape(1, -1)

        if TF_AVAILABLE:
            probs = self._model.predict(features, verbose=0)[0]
        else:
            probs = self._model.predict(features)[0]

        class_idx = int(np.argmax(probs))
        confidence = float(probs[class_idx])
        return BUILD_ORDER_CLASSES[class_idx], confidence

    def evaluate(self, X: np.ndarray, y: np.ndarray) -> Dict[str, float]:
        if TF_AVAILABLE:
            results = self._model.evaluate(X, y, verbose=0)
            return dict(zip(self._model.metrics_names, results))
        preds = self._model.predict_class(X)
        acc = (preds == y).mean()
        return {"accuracy": float(acc)}

    @property
    def summary(self) -> str:
        if TF_AVAILABLE:
            lines: List[str] = []
            self._model.summary(print_fn=lines.append)
            return "\n".join(lines)
        return "NumPy BuildOrderClassifier: 16→128→64→5 (softmax)"


# ---------------------------------------------------------------------------
# Training pipeline helper
# ---------------------------------------------------------------------------

def run_training_pipeline(n_samples: int = 5000, epochs: int = 30) -> None:
    """Generate synthetic data, train both models, and report metrics."""
    log.info("Generating synthetic SC2 training data (%d samples)...", n_samples)
    X, y_win, y_build = generate_synthetic_data(n_samples=n_samples)

    # Train/test split (80/20)
    split = int(0.8 * n_samples)
    X_train, X_test = X[:split], X[split:]
    y_win_train, y_win_test = y_win[:split], y_win[split:]
    y_build_train, y_build_test = y_build[:split], y_build[split:]

    log.info("Train size: %d  |  Test size: %d", split, n_samples - split)

    # --- WinPredictor ---
    win_model = WinPredictor()
    log.info("\n%s", win_model.summary)
    win_model.train(X_train, y_win_train, epochs=epochs, verbose=0)
    win_metrics = win_model.evaluate(X_test, y_win_test)
    log.info("WinPredictor test metrics: %s", win_metrics)

    # --- BuildOrderClassifier ---
    bo_model = BuildOrderClassifier()
    bo_model.train(X_train, y_build_train, epochs=epochs, verbose=0)
    bo_metrics = bo_model.evaluate(X_test, y_build_test)
    log.info("BuildOrderClassifier test metrics: %s", bo_metrics)

    return win_model, bo_model


# ---------------------------------------------------------------------------
# Main demo
# ---------------------------------------------------------------------------

def main() -> None:
    print("\n[SC2 Keras/ML Predictor — Phase 583]\n")

    # ---- Feature extraction demo ----
    extractor = SC2FeatureExtractor()

    sample_state = GameState(
        minerals=350.0,
        gas=120.0,
        supply_used=34.0,
        supply_cap=38.0,
        worker_count=22.0,
        army_supply=12.0,
        base_count=2.0,
        tech_level=1.0,
        game_time=180.0,
        opponent_army=15.0,
        map_control=0.45,
        opponent_base_count=1.0,
        energy=75.0,
        upgrade_count=1.0,
        kill_score=800.0,
        loss_score=400.0,
    )

    features = extractor.extract(sample_state)
    print("Sample game state feature vector:")
    for name, val in zip(FEATURE_NAMES, features):
        print(f"  {name:<22s}: {val:.4f}")
    print()

    # ---- Training pipeline ----
    print("Running training pipeline...")
    t0 = time.time()
    win_model, bo_model = run_training_pipeline(n_samples=3000, epochs=15)
    elapsed = time.time() - t0
    print(f"Training completed in {elapsed:.2f}s.\n")

    # ---- Prediction demo ----
    print("--- Win Probability Predictions ---")
    test_states = [
        GameState(minerals=100, gas=50, supply_used=80, supply_cap=100,
                  worker_count=60, army_supply=20, base_count=3, tech_level=1,
                  game_time=300, opponent_army=30, map_control=0.6,
                  opponent_base_count=2, energy=100, upgrade_count=2,
                  kill_score=1500, loss_score=800),
        GameState(minerals=800, gas=400, supply_used=180, supply_cap=200,
                  worker_count=70, army_supply=110, base_count=5, tech_level=2,
                  game_time=900, opponent_army=60, map_control=0.7,
                  opponent_base_count=2, energy=150, upgrade_count=6,
                  kill_score=4000, loss_score=1000),
        GameState(minerals=30, gas=0, supply_used=10, supply_cap=14,
                  worker_count=10, army_supply=0, base_count=1, tech_level=0,
                  game_time=30, opponent_army=20, map_control=0.2,
                  opponent_base_count=2, energy=50, upgrade_count=0,
                  kill_score=0, loss_score=500),
    ]
    state_labels = ["Mid-game dominant", "Late-game supreme", "Early disaster"]

    for label, state in zip(state_labels, test_states):
        prob = win_model.predict(state)
        bo_class, bo_conf = bo_model.predict(state)
        print(f"  [{label}]")
        print(f"    Win probability : {prob:.1%}")
        print(f"    Build order     : {bo_class} (confidence {bo_conf:.1%})")
        print()

    # ---- Raw feature vector prediction ----
    print("--- Raw feature vector prediction ---")
    rand_features = np.random.rand(FEATURE_DIM).astype(np.float32)
    prob = win_model.predict(rand_features)
    bo_class, bo_conf = bo_model.predict(rand_features)
    print(f"  Random feature vector:")
    print(f"    Win probability : {prob:.1%}")
    print(f"    Build order     : {bo_class} (confidence {bo_conf:.1%})")

    print("\nDone.")


if __name__ == "__main__":
    main()
