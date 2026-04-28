"""
keras_ml/battle_predictor.py
Keras Sequential model that predicts battle outcome (win/loss) from SC2 game features.
Features: army_supply, enemy_supply, minerals, gas, tech_level, time_seconds
"""

import os

import numpy as np

os.environ["TF_CPP_MIN_LOG_LEVEL"] = "2"

import tensorflow as tf
from tensorflow import keras
from tensorflow.keras import layers

# ---------------------------------------------------------------------------
# Feature definitions
# ---------------------------------------------------------------------------
FEATURE_NAMES = [
    "army_supply",  # Our army supply used
    "enemy_supply",  # Enemy army supply used
    "minerals",  # Current mineral bank
    "gas",  # Current gas bank
    "tech_level",  # 1=pool, 2=lair, 3=hive
    "time_seconds",  # Game time in seconds
]
NUM_FEATURES = len(FEATURE_NAMES)


# ---------------------------------------------------------------------------
# Sample SC2 training data  (features, label)
# label: 1 = we win the engagement, 0 = we lose
# ---------------------------------------------------------------------------
TRAINING_DATA = np.array(
    [
        # army  enemy  min   gas  tech  time   win
        [40, 20, 800, 300, 2, 300],  # big army advantage
        [15, 40, 200, 50, 1, 180],  # outnumbered early
        [60, 60, 1200, 600, 3, 600],  # mirror, rich — slight edge
        [30, 50, 400, 200, 2, 350],  # slightly behind
        [50, 10, 900, 400, 2, 400],  # massive advantage
        [10, 10, 300, 100, 1, 120],  # early game equal
        [70, 55, 1500, 800, 3, 700],  # hive tech, winning
        [20, 60, 100, 20, 1, 200],  # heavy deficit
        [45, 45, 600, 300, 2, 500],  # even, slight tech edge
        [55, 30, 700, 350, 2, 450],  # strong position
        [25, 25, 500, 250, 2, 400],  # equal mid-game
        [80, 40, 2000, 900, 3, 900],  # late game stomp
        [10, 80, 50, 10, 1, 150],  # all-in defense loss
        [35, 20, 800, 400, 3, 650],  # tech advantage small army
        [60, 80, 1000, 500, 3, 800],  # outnumbered but equal tech
        [90, 90, 2500, 1200, 3, 1100],  # maxed mirror
        [40, 40, 600, 300, 2, 480],  # even fight
        [15, 55, 150, 80, 1, 250],  # pressure from enemy
        [50, 50, 900, 450, 3, 750],  # hive mirror
        [65, 35, 1100, 600, 3, 700],  # winning late
    ],
    dtype=np.float32,
)

LABELS = np.array(
    [1, 0, 1, 0, 1, 0, 1, 0, 1, 1, 0, 1, 0, 1, 0, 1, 0, 0, 1, 1],
    dtype=np.float32,
)

# Normalise features (simple min-max for demo)
FEATURE_MIN = TRAINING_DATA.min(axis=0)
FEATURE_MAX = TRAINING_DATA.max(axis=0) + 1e-8


def normalise(x: np.ndarray) -> np.ndarray:
    return (x - FEATURE_MIN) / (FEATURE_MAX - FEATURE_MIN)


X_TRAIN = normalise(TRAINING_DATA)


# ---------------------------------------------------------------------------
# Model definition
# ---------------------------------------------------------------------------
def build_battle_predictor() -> keras.Model:
    """Build a 3-layer Dense network for binary battle outcome prediction."""
    model = keras.Sequential(
        [
            layers.Input(shape=(NUM_FEATURES,), name="game_state"),
            layers.Dense(32, activation="relu", name="hidden_1"),
            layers.Dropout(0.2, name="dropout_1"),
            layers.Dense(16, activation="relu", name="hidden_2"),
            layers.Dropout(0.2, name="dropout_2"),
            layers.Dense(8, activation="relu", name="hidden_3"),
            layers.Dense(1, activation="sigmoid", name="battle_outcome"),
        ],
        name="battle_predictor",
    )
    model.compile(
        optimizer=keras.optimizers.Adam(learning_rate=1e-3),
        loss="binary_crossentropy",
        metrics=["accuracy"],
    )
    return model


# ---------------------------------------------------------------------------
# Train
# ---------------------------------------------------------------------------
def train_model(model: keras.Model, epochs: int = 80) -> keras.callbacks.History:
    history = model.fit(
        X_TRAIN,
        LABELS,
        epochs=epochs,
        batch_size=8,
        validation_split=0.15,
        verbose=0,
    )
    final_acc = history.history["accuracy"][-1]
    print(f"[BattlePredictor] Training complete — final accuracy: {final_acc:.2%}")
    return history


# ---------------------------------------------------------------------------
# Predict
# ---------------------------------------------------------------------------
def predict_battle(
    model: keras.Model,
    army_supply: float,
    enemy_supply: float,
    minerals: float,
    gas: float,
    tech_level: int,
    time_seconds: float,
) -> tuple[float, str]:
    """
    Returns (win_probability, label) for a given game state snapshot.
    """
    raw = np.array(
        [[army_supply, enemy_supply, minerals, gas, tech_level, time_seconds]],
        dtype=np.float32,
    )
    x = normalise(raw)
    prob = float(model.predict(x, verbose=0)[0][0])
    label = "WIN" if prob >= 0.5 else "LOSS"
    return prob, label


# ---------------------------------------------------------------------------
# Save / Load
# ---------------------------------------------------------------------------
MODEL_PATH = os.path.join(os.path.dirname(__file__), "battle_predictor.keras")


def save_model(model: keras.Model, path: str = MODEL_PATH) -> None:
    model.save(path)
    print(f"[BattlePredictor] Model saved → {path}")


def load_model(path: str = MODEL_PATH) -> keras.Model:
    model = keras.models.load_model(path)
    print(f"[BattlePredictor] Model loaded ← {path}")
    return model


# ---------------------------------------------------------------------------
# Entry point demo
# ---------------------------------------------------------------------------
if __name__ == "__main__":
    model = build_battle_predictor()
    model.summary()
    train_model(model)

    # Demo predictions
    test_cases = [
        (60, 30, 1000, 500, 3, 600),  # Should be WIN
        (10, 70, 100, 20, 1, 180),  # Should be LOSS
        (45, 45, 700, 350, 2, 480),  # Borderline
    ]
    print("\n--- Battle Outcome Predictions ---")
    for case in test_cases:
        prob, label = predict_battle(model, *case)
        names = dict(zip(FEATURE_NAMES, case))
        print(f"  {names}  →  {label} ({prob:.1%})")

    save_model(model)
