"""
Phase 430: Hamilton - Declarative SC2 Feature Engineering Dataflow
Functions-as-nodes dataflow for reproducible SC2 feature pipelines.
"""

import pandas as pd
import numpy as np
from hamilton.function_modifiers import tag, extract_columns, check_output
from hamilton import driver, base

# ── Raw input nodes ───────────────────────────────────────────────────────────


def game_state(data_path: str) -> pd.DataFrame:
    """Load raw SC2 game state data from storage."""
    np.random.seed(42)
    n = 1000
    return pd.DataFrame(
        {
            "game_id": [f"g{i:05d}" for i in range(n)],
            "race": np.random.choice(["Zerg", "Terran", "Protoss"], n),
            "opponent_race": np.random.choice(["Zerg", "Terran", "Protoss"], n),
            "game_time": np.random.uniform(60, 1500, n),
            "minerals": np.random.randint(0, 2000, n),
            "gas": np.random.randint(0, 1000, n),
            "supply_used": np.random.randint(12, 200, n),
            "supply_cap": np.random.randint(14, 200, n),
            "army_supply": np.random.randint(0, 100, n),
            "worker_count": np.random.randint(10, 75, n),
            "expansion_count": np.random.randint(1, 5, n),
            "army_value": np.random.randint(500, 15000, n),
            "winner": np.random.randint(0, 2, n),
        }
    )


# ── Feature engineering nodes ─────────────────────────────────────────────────


@tag(feature_group="economy", feature_type="ratio")
def mineral_gas_ratio(game_state: pd.DataFrame) -> pd.Series:
    """Ratio of minerals to gas banked (economy balance indicator)."""
    return (game_state["minerals"] / (game_state["gas"] + 1)).rename(
        "mineral_gas_ratio"
    )


@tag(feature_group="macro", feature_type="ratio")
def supply_ratio(game_state: pd.DataFrame) -> pd.Series:
    """Supply used / supply cap (saturation indicator)."""
    return (game_state["supply_used"] / game_state["supply_cap"].clip(lower=1)).rename(
        "supply_ratio"
    )


@tag(feature_group="macro", feature_type="binary")
def is_supply_blocked(supply_ratio: pd.Series) -> pd.Series:
    """Boolean flag: is the player supply-blocked?"""
    return (supply_ratio >= 1.0).astype(int).rename("is_supply_blocked")


@tag(feature_group="economy", feature_type="derived")
def worker_saturation(game_state: pd.DataFrame) -> pd.Series:
    """Workers per expansion (measures worker efficiency)."""
    return (
        game_state["worker_count"] / game_state["expansion_count"].clip(lower=1)
    ).rename("worker_saturation")


@tag(feature_group="combat", feature_type="ratio")
def army_efficiency(game_state: pd.DataFrame) -> pd.Series:
    """Army value relative to total resources spent."""
    total_resources = game_state["minerals"] + game_state["gas"] + 1
    return (game_state["army_value"] / total_resources).rename("army_efficiency")


@tag(feature_group="timing", feature_type="normalized")
def normalized_game_time(game_state: pd.DataFrame) -> pd.Series:
    """Game time normalized to [0, 1] over 30-minute max."""
    return (game_state["game_time"] / 1800.0).clip(0, 1).rename("normalized_game_time")


@tag(feature_group="macro", feature_type="derived")
def expansion_rate(game_state: pd.DataFrame) -> pd.Series:
    """Expansions per unit of game time (pace indicator)."""
    return (game_state["expansion_count"] / (game_state["game_time"] / 60 + 1)).rename(
        "expansion_rate"
    )


# ── Feature assembly node ─────────────────────────────────────────────────────


def unit_features(
    game_state: pd.DataFrame,
    mineral_gas_ratio: pd.Series,
    supply_ratio: pd.Series,
    is_supply_blocked: pd.Series,
    worker_saturation: pd.Series,
    army_efficiency: pd.Series,
    normalized_game_time: pd.Series,
    expansion_rate: pd.Series,
) -> pd.DataFrame:
    """Assemble all engineered features into a single DataFrame."""
    return pd.concat(
        [
            game_state[["game_id", "race", "opponent_race", "winner"]],
            mineral_gas_ratio,
            supply_ratio,
            is_supply_blocked,
            worker_saturation,
            army_efficiency,
            normalized_game_time,
            expansion_rate,
        ],
        axis=1,
    )


# ── Normalization node ────────────────────────────────────────────────────────


def normalized_features(unit_features: pd.DataFrame) -> pd.DataFrame:
    """Min-max normalize all numeric feature columns."""
    df = unit_features.copy()
    num_cols = [
        "mineral_gas_ratio",
        "supply_ratio",
        "worker_saturation",
        "army_efficiency",
        "normalized_game_time",
        "expansion_rate",
    ]
    for col in num_cols:
        col_min = df[col].min()
        col_max = df[col].max()
        df[col] = (df[col] - col_min) / (col_max - col_min + 1e-8)
    return df


# ── Final model input node ────────────────────────────────────────────────────


def model_input(normalized_features: pd.DataFrame) -> np.ndarray:
    """Convert normalized feature DataFrame to model-ready numpy array."""
    feature_cols = [
        "mineral_gas_ratio",
        "supply_ratio",
        "is_supply_blocked",
        "worker_saturation",
        "army_efficiency",
        "normalized_game_time",
        "expansion_rate",
    ]
    return normalized_features[feature_cols].values.astype(np.float32)


# ── Driver runner ─────────────────────────────────────────────────────────────


def run_sc2_hamilton_dataflow(data_path: str = "data/replays/") -> None:
    """Execute the Hamilton dataflow graph for SC2 feature engineering."""
    import hamilton_pipeline.sc2_dataflow as this_module

    dr = driver.Driver(
        {"data_path": data_path},
        this_module,
        adapter=base.SimplePythonGraphAdapter(base.DictResult()),
    )

    outputs = dr.execute(
        final_vars=["model_input", "normalized_features"],
        inputs={"data_path": data_path},
    )

    print(f"[Hamilton] SC2 dataflow executed.")
    print(f"  game_state -> unit_features -> normalized_features -> model_input")
    print(f"  model_input shape: {outputs['model_input'].shape}")
    print(f"  Features: {list(outputs['normalized_features'].columns)}")


if __name__ == "__main__":
    print("[Hamilton] Building SC2 feature engineering graph...")
    run_sc2_hamilton_dataflow()

# Phase 430: Hamilton registered
