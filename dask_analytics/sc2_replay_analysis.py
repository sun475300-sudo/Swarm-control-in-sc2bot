# Phase 404: Dask - SC2 Replay Distributed Analytics
# Dask distributed analytics pipeline for SC2 replay log processing

from pathlib import Path
from typing import Optional

import dask
import dask.array as da
import dask.dataframe as dd
import numpy as np
import pandas as pd
from dask.distributed import Client, LocalCluster, as_completed

# ============================================================
# Cluster Setup
# ============================================================


def create_cluster(n_workers: int = 4, threads_per_worker: int = 2) -> Client:
    cluster = LocalCluster(
        n_workers=n_workers,
        threads_per_worker=threads_per_worker,
        memory_limit="2GB",
    )
    client = Client(cluster)
    print(f"[Dask] Dashboard: {client.dashboard_link}")
    return client


# ============================================================
# dask.dataframe: Replay Log Processing
# ============================================================


def load_replay_logs(log_dir: str = "data/replays") -> dd.DataFrame:
    """Load all CSV replay logs lazily with Dask."""
    schema = {
        "game_id": "int64",
        "map": "object",
        "player_race": "object",
        "opponent_race": "object",
        "result": "object",
        "duration": "float64",
        "apm": "float64",
        "mmr": "int64",
        "mmr_change": "int64",
        "game_loop": "int64",
    }

    # Create mock data for demonstration
    mock_data = pd.DataFrame(
        {
            "game_id": range(1000),
            "map": np.random.choice(
                ["Equilibrium LE", "Site Delta LE", "Gresvan LE"], 1000
            ),
            "player_race": np.random.choice(["Zerg", "Terran", "Protoss"], 1000),
            "opponent_race": np.random.choice(["Zerg", "Terran", "Protoss"], 1000),
            "result": np.random.choice(["Win", "Loss"], 1000, p=[0.55, 0.45]),
            "duration": np.random.uniform(120, 900, 1000),
            "apm": np.random.normal(180, 40, 1000).clip(60, 400),
            "mmr": np.random.randint(4500, 5200, 1000),
            "mmr_change": np.random.randint(-25, 30, 1000),
            "game_loop": np.random.randint(3000, 22500, 1000),
        }
    )

    # Convert to Dask dataframe with 4 partitions
    ddf = dd.from_pandas(mock_data, npartitions=4)
    return ddf


# ============================================================
# Feature Computation with dask.array
# ============================================================


def compute_apm_features(ddf: dd.DataFrame) -> da.Array:
    """Compute APM feature matrix using dask.array."""
    apm_vals = ddf["apm"].values.compute()

    arr = da.from_array(
        np.column_stack(
            [
                apm_vals,
                np.log1p(apm_vals),
                (apm_vals - apm_vals.mean()) / (apm_vals.std() + 1e-8),
            ]
        ),
        chunks=(250, 3),
    )

    # Rolling statistics via dask.array slices
    mean_apm = da.mean(arr[:, 0])
    std_apm = da.std(arr[:, 0])
    return arr, mean_apm, std_apm


# ============================================================
# Lazy Computation Graph: Replay Statistics
# ============================================================


def build_stats_graph(ddf: dd.DataFrame) -> dict:
    """Build a lazy computation graph for replay statistics."""

    # Win rate by race matchup
    win_mask = ddf["result"] == "Win"

    win_rate_by_race = (
        ddf.assign(win=win_mask.astype(int))
        .groupby(["player_race", "opponent_race"])["win"]
        .mean()
    )

    # APM distribution
    apm_buckets = ddf["apm"].map_partitions(
        lambda s: pd.cut(
            s,
            bins=[0, 100, 150, 200, 250, 999],
            labels=["<100", "100-150", "150-200", "200-250", "250+"],
        )
    )
    apm_hist = apm_buckets.value_counts()

    # Average duration by map
    avg_duration_by_map = ddf.groupby("map")["duration"].mean()

    # MMR trend (cumulative mean)
    mmr_series = ddf["mmr"]

    # Build lazy graph dict
    graph = {
        "win_rate_by_race": win_rate_by_race,
        "apm_histogram": apm_hist,
        "avg_duration_by_map": avg_duration_by_map,
        "global_avg_apm": ddf["apm"].mean(),
        "global_win_rate": win_mask.mean(),
        "total_games": ddf["game_id"].count(),
        "avg_mmr_change": ddf["mmr_change"].mean(),
    }
    return graph


# ============================================================
# Execute Computation Graph
# ============================================================


def execute_graph(graph: dict, client: Optional[Client] = None) -> dict:
    """Execute all lazy computations, optionally on the cluster."""
    if client:
        # Submit all computations to the cluster
        futures = {k: client.compute(v) for k, v in graph.items()}
        results = {k: f.result() for k, f in futures.items()}
    else:
        # Local threaded execution
        results = dask.compute(graph)[0]
        results = {
            k: v.compute() if hasattr(v, "compute") else v for k, v in graph.items()
        }
    return results


# ============================================================
# Build Order Frequency Analysis
# ============================================================


def analyze_build_orders(ddf: dd.DataFrame) -> dd.DataFrame:
    """Frequency analysis of build orders per race matchup."""
    # In production, join with build_order table
    # Here we simulate with race columns
    build_freq = (
        ddf.groupby(["player_race", "opponent_race", "result"])
        .agg({"game_id": "count", "apm": "mean", "duration": "mean"})
        .rename(columns={"game_id": "count"})
    )
    return build_freq


# ============================================================
# Main
# ============================================================


def main():
    print("[Dask] Starting SC2 replay analytics pipeline...")

    client = create_cluster(n_workers=4)

    # Load replay logs lazily
    ddf = load_replay_logs()
    print(f"[Dask] Loaded replay dataframe: {ddf.npartitions} partitions")

    # Build lazy computation graph
    graph = build_stats_graph(ddf)
    print(f"[Dask] Computation graph built with {len(graph)} nodes")

    # Execute
    results = execute_graph(graph, client=client)

    print("\n=== SC2 Replay Statistics ===")
    print(f"Total games:      {results['total_games']}")
    print(f"Global win rate:  {results['global_win_rate']:.1%}")
    print(f"Average APM:      {results['global_avg_apm']:.1f}")
    print(f"Avg MMR change:   {results['avg_mmr_change']:+.1f}")

    # APM features
    arr, mean_apm, std_apm = compute_apm_features(ddf)
    m, s = dask.compute(mean_apm, std_apm)
    print(f"APM stats:        mean={m:.1f}, std={s:.1f}")

    # Build order analysis
    build_freq = analyze_build_orders(ddf)
    print("\n[Dask] Build order analysis complete (lazy)")

    client.close()
    print("[Dask] Pipeline complete, cluster shut down")


if __name__ == "__main__":
    main()
