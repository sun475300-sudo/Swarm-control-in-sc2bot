"""
Phase 421: Polars - Ultra-fast SC2 Replay Analytics
Rust-based DataFrame library for high-performance SC2 data processing.
"""

import polars as pl
from pathlib import Path
import json
from datetime import datetime

# ── Schema definitions ────────────────────────────────────────────────────────

REPLAY_SCHEMA = {
    "game_id": pl.Utf8,
    "player_id": pl.Int32,
    "race": pl.Utf8,
    "opponent_race": pl.Utf8,
    "map_name": pl.Utf8,
    "game_duration": pl.Float64,
    "winner": pl.Boolean,
    "apm": pl.Float64,
    "supply_used": pl.Int32,
    "minerals_spent": pl.Int64,
    "gas_spent": pl.Int64,
    "workers_produced": pl.Int32,
    "army_value": pl.Int64,
    "timestamp": pl.Utf8,
}


# ── Eager DataFrame operations ────────────────────────────────────────────────


def load_replay_data(path: str) -> pl.DataFrame:
    """Load SC2 replay CSV data into a Polars DataFrame."""
    return pl.read_csv(path, schema_overrides=REPLAY_SCHEMA)


def compute_win_rates(df: pl.DataFrame) -> pl.DataFrame:
    """Compute win rate by race matchup using group_by."""
    return (
        df.group_by(["race", "opponent_race"])
        .agg(
            [
                pl.col("winner").mean().alias("win_rate"),
                pl.col("game_id").count().alias("total_games"),
                pl.col("apm").mean().alias("avg_apm"),
            ]
        )
        .sort("win_rate", descending=True)
    )


# ── LazyFrame API (deferred computation) ─────────────────────────────────────


def build_lazy_pipeline(path: str) -> pl.LazyFrame:
    """Build a lazy computation pipeline for large replay datasets."""
    return (
        pl.scan_csv(path)
        .filter(pl.col("game_duration") > 60.0)  # Skip short games
        .with_columns(
            [
                (pl.col("minerals_spent") + pl.col("gas_spent")).alias(
                    "total_resources"
                ),
                pl.col("apm").cast(pl.Float64),
                pl.when(pl.col("winner"))
                .then(pl.lit(1))
                .otherwise(pl.lit(0))
                .alias("win_int"),
            ]
        )
        .with_columns(
            [
                (
                    pl.col("army_value") / pl.col("total_resources").clip(lower_bound=1)
                ).alias("army_efficiency"),
            ]
        )
    )


# ── Window functions with over() ──────────────────────────────────────────────


def add_rolling_win_rate(df: pl.DataFrame) -> pl.DataFrame:
    """Add per-player rolling win rate using window (over) expressions."""
    return df.with_columns(
        [
            pl.col("win_int").mean().over("player_id").alias("player_win_rate"),
            pl.col("apm").mean().over(["race", "map_name"]).alias("race_map_avg_apm"),
        ]
    )


# ── Parallel dataset processing ───────────────────────────────────────────────


def process_replay_batch(replay_files: list[str]) -> pl.DataFrame:
    """Process multiple replay CSV files in parallel using Polars lazy scans."""
    lazy_frames = [
        pl.scan_csv(f).with_columns(pl.lit(Path(f).stem).alias("source_file"))
        for f in replay_files
    ]
    combined = pl.concat(lazy_frames)
    return (
        combined.filter(pl.col("apm") > 30)
        .with_columns(
            [
                (pl.col("minerals_spent") / pl.col("game_duration")).alias(
                    "minerals_per_min"
                ),
                (pl.col("workers_produced") / pl.col("game_duration")).alias(
                    "workers_per_min"
                ),
            ]
        )
        .collect(streaming=True)  # Streaming for large data
    )


# ── Expressions: conditional logic ───────────────────────────────────────────


def classify_performance(df: pl.DataFrame) -> pl.DataFrame:
    """Classify player performance tier using when/then/otherwise."""
    return df.with_columns(
        [
            pl.when(pl.col("apm") >= 150)
            .then(pl.lit("Pro"))
            .when(pl.col("apm") >= 100)
            .then(pl.lit("Advanced"))
            .when(pl.col("apm") >= 60)
            .then(pl.lit("Intermediate"))
            .otherwise(pl.lit("Beginner"))
            .alias("skill_tier"),
        ]
    )


# ── Main analytics runner ─────────────────────────────────────────────────────


def run_sc2_analytics(data_dir: str = "data/replays") -> None:
    """Run the full SC2 analytics pipeline."""
    sample = pl.DataFrame(
        {
            "game_id": [f"game_{i:04d}" for i in range(1000)],
            "player_id": list(range(1000)),
            "race": (["Zerg", "Terran", "Protoss"] * 334)[:1000],
            "opponent_race": (["Terran", "Protoss", "Zerg"] * 334)[:1000],
            "map_name": (["Berlingrad", "Ancient Cistern"] * 500)[:1000],
            "game_duration": [120.0 + i * 0.5 for i in range(1000)],
            "winner": [i % 2 == 0 for i in range(1000)],
            "apm": [80.0 + (i % 120) for i in range(1000)],
            "supply_used": [100 + i % 100 for i in range(1000)],
            "minerals_spent": [5000 + i * 10 for i in range(1000)],
            "gas_spent": [2000 + i * 5 for i in range(1000)],
            "workers_produced": [20 + i % 40 for i in range(1000)],
            "army_value": [3000 + i * 7 for i in range(1000)],
            "timestamp": [datetime.now().isoformat()] * 1000,
            "win_int": [i % 2 for i in range(1000)],
        }
    )

    print("[Polars] Loaded sample replay dataset:", sample.shape)

    win_rates = compute_win_rates(sample)
    print("\n[Win Rates by Matchup]")
    print(win_rates)

    enriched = add_rolling_win_rate(sample)
    tiered = classify_performance(enriched)
    tier_counts = tiered.group_by("skill_tier").agg(
        pl.col("game_id").count().alias("count")
    )
    print("\n[Skill Tier Distribution]")
    print(tier_counts)

    print("\n[Polars SC2 Analytics complete.]")


if __name__ == "__main__":
    run_sc2_analytics()

# Phase 421: Polars registered
