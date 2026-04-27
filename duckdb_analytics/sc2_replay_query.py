# Phase 408: DuckDB - SC2 In-Process OLAP Analytics
# DuckDB for fast in-process analytical queries on SC2 replay Parquet files

from pathlib import Path
from typing import Optional

import duckdb
import numpy as np
import pandas as pd

# ============================================================
# Setup: Create DuckDB connection and sample Parquet files
# ============================================================


def create_connection(db_path: str = ":memory:") -> duckdb.DuckDBPyConnection:
    con = duckdb.connect(db_path)
    con.execute("INSTALL parquet; LOAD parquet;")
    return con


def generate_sample_parquet(output_dir: str = "data/replays"):
    """Generate sample Parquet replay files for demonstration."""
    Path(output_dir).mkdir(parents=True, exist_ok=True)

    rng = np.random.default_rng(42)
    n = 2000

    games_df = pd.DataFrame(
        {
            "game_id": range(n),
            "played_at": pd.date_range("2025-01-01", periods=n, freq="2h"),
            "map": rng.choice(
                ["Equilibrium LE", "Site Delta LE", "Gresvan LE", "Goldenaura LE"], n
            ),
            "player_race": rng.choice(["Zerg", "Terran", "Protoss"], n),
            "opponent_race": rng.choice(["Zerg", "Terran", "Protoss"], n),
            "result": rng.choice(["Win", "Loss"], n, p=[0.55, 0.45]),
            "duration_sec": rng.integers(120, 900, n),
            "apm": rng.integers(80, 350, n),
            "mmr_before": rng.integers(4500, 5200, n),
            "mmr_change": rng.integers(-25, 31, n),
            "supply_peak": rng.integers(60, 200, n),
        }
    )

    games_df.to_parquet(f"{output_dir}/games.parquet", index=False)
    print(f"[DuckDB] Sample data written to {output_dir}/games.parquet")
    return output_dir


# ============================================================
# Query 1: Win rate by matchup (direct Parquet query)
# ============================================================


def query_win_rate_by_matchup(
    con: duckdb.DuckDBPyConnection, parquet_dir: str
) -> pd.DataFrame:
    sql = f"""
    SELECT
        player_race,
        opponent_race,
        COUNT(*)                                              AS total_games,
        SUM(CASE WHEN result = 'Win' THEN 1 ELSE 0 END)      AS wins,
        ROUND(AVG(CASE WHEN result = 'Win' THEN 1.0 ELSE 0.0 END) * 100, 1) AS win_rate_pct,
        ROUND(AVG(apm), 1)                                    AS avg_apm,
        ROUND(AVG(duration_sec / 60.0), 1)                   AS avg_duration_min
    FROM read_parquet('{parquet_dir}/games.parquet')
    GROUP BY player_race, opponent_race
    ORDER BY player_race, opponent_race
    """
    return con.execute(sql).df()


# ============================================================
# Query 2: Window functions for per-game analysis
# ============================================================


def query_mmr_progression(
    con: duckdb.DuckDBPyConnection, parquet_dir: str
) -> pd.DataFrame:
    sql = f"""
    WITH ordered_games AS (
        SELECT
            game_id,
            played_at,
            mmr_before,
            mmr_change,
            mmr_before + mmr_change                                    AS mmr_after,
            apm,
            result,
            ROW_NUMBER() OVER (ORDER BY played_at)                     AS game_num,
            SUM(mmr_change) OVER (ORDER BY played_at ROWS UNBOUNDED PRECEDING) AS cumulative_mmr_delta,
            AVG(apm) OVER (ORDER BY played_at ROWS BETWEEN 9 PRECEDING AND CURRENT ROW) AS rolling_10_apm,
            SUM(CASE WHEN result = 'Win' THEN 1 ELSE 0 END)
                OVER (ORDER BY played_at ROWS BETWEEN 9 PRECEDING AND CURRENT ROW)  AS wins_last_10
        FROM read_parquet('{parquet_dir}/games.parquet')
    )
    SELECT *,
        ROUND(wins_last_10 / 10.0 * 100, 1) AS win_rate_last_10_pct
    FROM ordered_games
    ORDER BY game_num
    LIMIT 50
    """
    return con.execute(sql).df()


# ============================================================
# Query 3: APM histogram with ntile buckets
# ============================================================


def query_apm_histogram(
    con: duckdb.DuckDBPyConnection, parquet_dir: str
) -> pd.DataFrame:
    sql = f"""
    SELECT
        NTILE(10) OVER (ORDER BY apm)          AS apm_decile,
        MIN(apm)                               AS apm_min,
        MAX(apm)                               AS apm_max,
        COUNT(*)                               AS game_count,
        ROUND(AVG(apm), 1)                     AS avg_apm,
        ROUND(AVG(CASE WHEN result = 'Win' THEN 1.0 ELSE 0.0 END) * 100, 1) AS win_rate_pct
    FROM read_parquet('{parquet_dir}/games.parquet')
    GROUP BY apm_decile
    ORDER BY apm_decile
    """
    return con.execute(sql).df()


# ============================================================
# Query 4: Map statistics
# ============================================================


def query_map_stats(con: duckdb.DuckDBPyConnection, parquet_dir: str) -> pd.DataFrame:
    sql = f"""
    SELECT
        map,
        COUNT(*)                                              AS games,
        ROUND(AVG(duration_sec / 60.0), 1)                   AS avg_duration_min,
        ROUND(AVG(apm), 1)                                    AS avg_apm,
        ROUND(AVG(CASE WHEN result = 'Win' THEN 1.0 ELSE 0.0 END) * 100, 1) AS win_rate_pct,
        PERCENTILE_CONT(0.5) WITHIN GROUP (ORDER BY duration_sec / 60.0) AS median_duration_min
    FROM read_parquet('{parquet_dir}/games.parquet')
    GROUP BY map
    ORDER BY games DESC
    """
    return con.execute(sql).df()


# ============================================================
# Export to pandas for visualization
# ============================================================


def export_for_visualization(con: duckdb.DuckDBPyConnection, parquet_dir: str) -> dict:
    return {
        "win_rate_by_matchup": query_win_rate_by_matchup(con, parquet_dir),
        "mmr_progression": query_mmr_progression(con, parquet_dir),
        "apm_histogram": query_apm_histogram(con, parquet_dir),
        "map_stats": query_map_stats(con, parquet_dir),
    }


# ============================================================
# Main
# ============================================================


def main():
    print("[DuckDB] SC2 replay analytics starting...")
    con = create_connection()
    data_dir = generate_sample_parquet("data/replays")
    results = export_for_visualization(con, data_dir)

    print("\n=== Win Rate by Matchup ===")
    print(results["win_rate_by_matchup"].to_string(index=False))

    print("\n=== Map Statistics ===")
    print(results["map_stats"].to_string(index=False))

    print("\n=== APM Histogram (deciles) ===")
    print(results["apm_histogram"].to_string(index=False))

    print("\n[DuckDB] Analysis complete. DataFrames ready for matplotlib/plotly.")
    con.close()


if __name__ == "__main__":
    main()
