"""
Phase 422: Ibis - Portable SC2 Analytics
Works across DuckDB, BigQuery, Snowflake, and more with a single API.
"""

import ibis
import ibis.expr.datatypes as dt
from ibis import _
import pandas as pd


# ── Backend configuration ─────────────────────────────────────────────────────

def get_connection(backend: str = "duckdb"):
    """Get Ibis connection for specified backend."""
    if backend == "duckdb":
        return ibis.duckdb.connect(":memory:")
    elif backend == "sqlite":
        return ibis.sqlite.connect(":memory:")
    else:
        raise ValueError(f"Unsupported backend: {backend}")


# ── Table schema definitions ──────────────────────────────────────────────────

def create_sc2_tables(con) -> dict:
    """Create SC2 analytics tables."""
    games_df = pd.DataFrame({
        "game_id": [f"g{i:04d}" for i in range(500)],
        "map_name": (["Berlingrad", "Ancient Cistern", "Equilibrium"] * 167)[:500],
        "duration_sec": [180 + i * 2 for i in range(500)],
        "patch_version": ["5.0.11"] * 500,
    })

    unit_events_df = pd.DataFrame({
        "event_id": range(2000),
        "game_id": [f"g{i % 500:04d}" for i in range(2000)],
        "player_id": [i % 10 for i in range(2000)],
        "unit_type": (["Zergling", "Marine", "Stalker", "Roach", "Medivac"] * 400)[:2000],
        "event_type": (["created", "destroyed", "attacked"] * 667)[:2000],
        "game_time": [i * 3.0 for i in range(2000)],
    })

    player_stats_df = pd.DataFrame({
        "player_id": range(100),
        "player_name": [f"Player_{i}" for i in range(100)],
        "race": (["Zerg", "Terran", "Protoss"] * 34)[:100],
        "mmr": [1500 + i * 15 for i in range(100)],
        "total_games": [50 + i for i in range(100)],
        "wins": [25 + i // 2 for i in range(100)],
    })

    con.create_table("games", games_df, overwrite=True)
    con.create_table("unit_events", unit_events_df, overwrite=True)
    con.create_table("player_stats", player_stats_df, overwrite=True)

    return {
        "games": con.table("games"),
        "unit_events": con.table("unit_events"),
        "player_stats": con.table("player_stats"),
    }


# ── Portable queries ──────────────────────────────────────────────────────────

def query_win_rates(tables: dict) -> ibis.Expr:
    """Win rate by race - works on any backend."""
    ps = tables["player_stats"]
    return (
        ps.group_by("race")
        .aggregate([
            ps.wins.sum().name("total_wins"),
            ps.total_games.sum().name("total_games"),
            (ps.wins.sum() / ps.total_games.sum()).name("win_rate"),
            ps.mmr.mean().name("avg_mmr"),
        ])
        .order_by(ibis.desc("win_rate"))
    )


def query_unit_activity(tables: dict) -> ibis.Expr:
    """Unit production and loss counts per game."""
    ue = tables["unit_events"]
    return (
        ue.filter(ue.event_type.isin(["created", "destroyed"]))
        .group_by(["game_id", "unit_type", "event_type"])
        .aggregate(ue.event_id.count().name("event_count"))
        .order_by(["game_id", "unit_type"])
    )


def query_top_players(tables: dict, min_games: int = 60) -> ibis.Expr:
    """Top players filtered by minimum games played."""
    ps = tables["player_stats"]
    return (
        ps.filter(ps.total_games >= min_games)
        .mutate(win_pct=(ps.wins / ps.total_games * 100).round(2))
        .select(["player_name", "race", "mmr", "total_games", "win_pct"])
        .order_by(ibis.desc("mmr"))
        .limit(20)
    )


def query_game_unit_join(tables: dict) -> ibis.Expr:
    """Join games with unit events to get per-game unit stats."""
    games = tables["games"]
    ue = tables["unit_events"]
    return (
        games.join(ue, games.game_id == ue.game_id)
        .group_by(["games.game_id", "map_name"])
        .aggregate([
            ue.event_id.count().name("total_events"),
            ue.game_time.max().name("last_event_time"),
        ])
        .order_by(ibis.desc("total_events"))
    )


# ── Backend-agnostic runner ───────────────────────────────────────────────────

def run_sc2_ibis_analytics(backend: str = "duckdb") -> None:
    """Run SC2 analytics on the specified Ibis backend."""
    print(f"[Ibis] Connecting to backend: {backend}")
    con = get_connection(backend)
    tables = create_sc2_tables(con)

    print("\n[Win Rates by Race]")
    print(query_win_rates(tables).execute())

    print("\n[Top Players (>=60 games)]")
    print(query_top_players(tables, min_games=60).execute())

    print("\n[Unit Activity Summary]")
    activity = query_unit_activity(tables).execute()
    print(activity.head(10))

    print(f"\n[Ibis SC2 analytics complete on {backend} backend.]")


if __name__ == "__main__":
    run_sc2_ibis_analytics("duckdb")

# Phase 422: Ibis registered
