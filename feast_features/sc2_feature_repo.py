"""
Phase 429: Feast - SC2 Feature Store Repository
Centralized feature management for SC2 ML training and real-time serving.
"""

from feast import (
    Entity, FeatureView, Feature, FeatureStore,
    FileSource, RequestSource, OnDemandFeatureView,
    ValueType, Field,
)
from feast.types import Float32, Float64, Int32, Int64, String
from datetime import timedelta
from pathlib import Path
import pandas as pd
import numpy as np


# ── Entities ──────────────────────────────────────────────────────────────────

player_entity = Entity(
    name="player_id",
    join_keys=["player_id"],
    value_type=ValueType.INT64,
    description="Unique SC2 player identifier",
)

game_entity = Entity(
    name="game_id",
    join_keys=["game_id"],
    value_type=ValueType.STRING,
    description="Unique SC2 game identifier",
)


# ── Data sources ──────────────────────────────────────────────────────────────

unit_features_source = FileSource(
    name="unit_features_source",
    path="feast_features/data/unit_features.parquet",
    timestamp_field="event_timestamp",
)

game_context_source = FileSource(
    name="game_context_source",
    path="feast_features/data/game_context.parquet",
    timestamp_field="event_timestamp",
)

player_history_source = FileSource(
    name="player_history_source",
    path="feast_features/data/player_history.parquet",
    timestamp_field="event_timestamp",
)


# ── Feature Views ─────────────────────────────────────────────────────────────

unit_features_view = FeatureView(
    name="unit_features",
    entities=[game_entity],
    ttl=timedelta(days=7),
    schema=[
        Field(name="zergling_count", dtype=Int32),
        Field(name="roach_count", dtype=Int32),
        Field(name="hydralisk_count", dtype=Int32),
        Field(name="army_supply", dtype=Int32),
        Field(name="army_value", dtype=Int64),
        Field(name="worker_count", dtype=Int32),
        Field(name="queen_count", dtype=Int32),
    ],
    source=unit_features_source,
    description="Real-time unit composition features per game",
)

game_context_view = FeatureView(
    name="game_context_features",
    entities=[game_entity],
    ttl=timedelta(days=30),
    schema=[
        Field(name="game_time", dtype=Float32),
        Field(name="minerals_banked", dtype=Int32),
        Field(name="gas_banked", dtype=Int32),
        Field(name="supply_used", dtype=Int32),
        Field(name="supply_cap", dtype=Int32),
        Field(name="expansion_count", dtype=Int32),
        Field(name="map_name", dtype=String),
    ],
    source=game_context_source,
    description="Macro-level game context features",
)

player_history_view = FeatureView(
    name="player_history_features",
    entities=[player_entity],
    ttl=timedelta(days=90),
    schema=[
        Field(name="avg_apm_30d", dtype=Float32),
        Field(name="win_rate_30d", dtype=Float32),
        Field(name="games_played_30d", dtype=Int32),
        Field(name="mmr", dtype=Int32),
        Field(name="race", dtype=String),
        Field(name="preferred_opening", dtype=String),
    ],
    source=player_history_source,
    description="Historical player performance statistics",
)


# ── On-demand feature view (real-time computation) ────────────────────────────

real_time_input = RequestSource(
    name="real_time_game_state",
    schema=[
        Field(name="minerals_banked", dtype=Int32),
        Field(name="gas_banked", dtype=Int32),
        Field(name="supply_used", dtype=Int32),
        Field(name="supply_cap", dtype=Int32),
        Field(name="army_value", dtype=Int64),
    ],
)


@OnDemandFeatureView(
    sources=[real_time_input],
    schema=[
        Field(name="supply_ratio", dtype=Float32),
        Field(name="resource_efficiency", dtype=Float32),
        Field(name="is_supply_blocked", dtype=Int32),
    ],
)
def compute_derived_features(inputs: pd.DataFrame) -> pd.DataFrame:
    """Compute real-time derived features for SC2 game state."""
    df = pd.DataFrame()
    df["supply_ratio"] = (inputs["supply_used"] / inputs["supply_cap"].clip(lower=1)).astype("float32")
    df["resource_efficiency"] = (
        inputs["army_value"] / (inputs["minerals_banked"] + inputs["gas_banked"] + 1)
    ).astype("float32")
    df["is_supply_blocked"] = ((inputs["supply_used"] >= inputs["supply_cap"]).astype(int))
    return df


# ── Data generation helpers ───────────────────────────────────────────────────

def generate_sample_feature_data(output_dir: str = "feast_features/data") -> None:
    """Generate sample Parquet files for local feature store testing."""
    Path(output_dir).mkdir(parents=True, exist_ok=True)
    np.random.seed(42)
    n = 2000
    timestamps = pd.date_range("2025-01-01", periods=n, freq="5min")

    pd.DataFrame({
        "game_id": [f"g{i:05d}" for i in range(n)],
        "event_timestamp": timestamps,
        "zergling_count": np.random.randint(0, 40, n),
        "roach_count": np.random.randint(0, 20, n),
        "hydralisk_count": np.random.randint(0, 15, n),
        "army_supply": np.random.randint(0, 80, n),
        "army_value": np.random.randint(0, 15000, n),
        "worker_count": np.random.randint(10, 75, n),
        "queen_count": np.random.randint(0, 8, n),
    }).to_parquet(f"{output_dir}/unit_features.parquet")

    pd.DataFrame({
        "game_id": [f"g{i:05d}" for i in range(n)],
        "event_timestamp": timestamps,
        "game_time": np.random.uniform(60, 1500, n).astype("float32"),
        "minerals_banked": np.random.randint(0, 2000, n),
        "gas_banked": np.random.randint(0, 1000, n),
        "supply_used": np.random.randint(12, 200, n),
        "supply_cap": np.random.randint(14, 200, n),
        "expansion_count": np.random.randint(1, 5, n),
        "map_name": np.random.choice(["Berlingrad", "Ancient Cistern"], n),
    }).to_parquet(f"{output_dir}/game_context.parquet")

    pd.DataFrame({
        "player_id": list(range(n)),
        "event_timestamp": timestamps,
        "avg_apm_30d": np.random.uniform(40, 250, n).astype("float32"),
        "win_rate_30d": np.random.uniform(0.3, 0.7, n).astype("float32"),
        "games_played_30d": np.random.randint(5, 200, n),
        "mmr": np.random.randint(1000, 7000, n),
        "race": np.random.choice(["Zerg", "Terran", "Protoss"], n),
        "preferred_opening": np.random.choice(["Pool First", "Hatch First", "Gas First"], n),
    }).to_parquet(f"{output_dir}/player_history.parquet")

    print(f"[Feast] Sample data written to {output_dir}/")


if __name__ == "__main__":
    print("[Feast] SC2 Feature Repository initialized.")
    print(f"  Entities: player_id, game_id")
    print(f"  Feature Views: unit_features, game_context_features, player_history_features")
    print(f"  On-demand: compute_derived_features (supply_ratio, resource_efficiency)")
    generate_sample_feature_data()

# Phase 429: Feast registered
