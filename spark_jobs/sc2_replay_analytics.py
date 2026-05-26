# Phase 577: Spark Jobs
# SC2 Replay Data Analysis at Scale — PySpark Job
# Standalone-runnable with pure-Python fallback if pyspark not installed

from __future__ import annotations

import math
import random
import sys
from collections import defaultdict
from dataclasses import dataclass, field
from datetime import datetime
from statistics import mean, stdev
from typing import Any, Callable, Dict, Iterable, List, Optional, Tuple

# ---------------------------------------------------------------------------
# Graceful fallback: pure-Python DataFrame substitute if pyspark unavailable
# ---------------------------------------------------------------------------
try:
    from pyspark.sql import DataFrame, SparkSession
    from pyspark.sql import functions as F
    from pyspark.sql.types import (
        BooleanType,
        FloatType,
        IntegerType,
        StringType,
        StructField,
        StructType,
    )
    from pyspark.sql.window import Window

    PYSPARK_AVAILABLE = True
    print("[INFO] PySpark detected — using Spark runtime.")
except ImportError:
    PYSPARK_AVAILABLE = False
    print("[WARN] PySpark not installed — running pure-Python simulation.")

    # ---- Minimal pure-Python DataFrame shim ----
    class StructField:
        def __init__(self, name, dtype, nullable=True):
            self.name = name
            self.dtype = dtype
            self.nullable = nullable

    class StructType:
        def __init__(self, fields: list):
            self.fields = fields

        def __iter__(self):
            return iter(self.fields)

    class StringType:
        pass

    class IntegerType:
        pass

    class FloatType:
        pass

    class BooleanType:
        pass

    class Row(dict):
        """Dict-backed Row that supports attribute access."""

        def __getattr__(self, item):
            try:
                return self[item]
            except KeyError:
                raise AttributeError(item)

    class DataFrame:
        """Minimal pure-Python DataFrame backed by a list of Row dicts."""

        def __init__(self, data: List[dict], schema: StructType = None):
            self._data: List[dict] = [dict(r) for r in data]
            self.schema = schema

        @property
        def columns(self):
            return list(self._data[0].keys()) if self._data else []

        def count(self) -> int:
            return len(self._data)

        def filter(self, condition: Callable[[dict], bool]) -> "DataFrame":
            return DataFrame([r for r in self._data if condition(r)], self.schema)

        def select(self, *cols) -> "DataFrame":
            return DataFrame([{c: r.get(c) for c in cols} for r in self._data])

        def withColumn(self, name: str, expr: Callable[[dict], Any]) -> "DataFrame":
            rows = []
            for r in self._data:
                nr = dict(r)
                nr[name] = expr(r)
                rows.append(nr)
            return DataFrame(rows, self.schema)

        def groupBy(self, *keys) -> "_GroupedDF":
            return _GroupedDF(self._data, list(keys))

        def orderBy(self, *cols, **kwargs) -> "DataFrame":
            ascending = kwargs.get("ascending", True)
            col = cols[0] if cols else None
            if col:
                return DataFrame(
                    sorted(
                        self._data,
                        key=lambda r: (r.get(col) or 0),
                        reverse=not ascending,
                    ),
                    self.schema,
                )
            return self

        def limit(self, n: int) -> "DataFrame":
            return DataFrame(self._data[:n], self.schema)

        def show(self, n: int = 20, truncate: bool = True) -> None:
            rows = self._data[:n]
            if not rows:
                print("(empty DataFrame)")
                return
            cols = list(rows[0].keys())
            width = 18
            header = " | ".join(c.ljust(width)[:width] for c in cols)
            sep = "-" * len(header)
            print(sep)
            print(header)
            print(sep)
            for r in rows:
                line = " | ".join(str(r.get(c, "")).ljust(width)[:width] for c in cols)
                print(line)
            print(sep)
            if len(self._data) > n:
                print(f"... ({len(self._data) - n} more rows)")

        def toPandas(self):
            return self._data  # return list of dicts as substitute

        def collect(self) -> List[dict]:
            return list(self._data)

        def join(self, other: "DataFrame", on: str, how: str = "inner") -> "DataFrame":
            right_index = {r[on]: r for r in other._data}
            result = []
            for r in self._data:
                key = r.get(on)
                if key in right_index:
                    merged = {**r, **right_index[key]}
                    result.append(merged)
                elif how in ("left", "left_outer"):
                    result.append(dict(r))
            return DataFrame(result)

        def agg(self, **agg_exprs) -> "DataFrame":
            if not self._data:
                return DataFrame([])
            row: dict = {}
            for alias, (func_name, col) in agg_exprs.items():
                vals = [r.get(col) for r in self._data if r.get(col) is not None]
                if func_name == "count":
                    row[alias] = len(self._data)
                elif func_name == "sum":
                    row[alias] = sum(vals)
                elif func_name == "avg":
                    row[alias] = mean(vals) if vals else 0.0
                elif func_name == "max":
                    row[alias] = max(vals) if vals else None
                elif func_name == "min":
                    row[alias] = min(vals) if vals else None
                elif func_name == "stddev":
                    row[alias] = stdev(vals) if len(vals) > 1 else 0.0
            return DataFrame([row])

    class _GroupedDF:
        def __init__(self, data: List[dict], keys: List[str]):
            self._data = data
            self._keys = keys

        def _groups(self) -> Dict[tuple, List[dict]]:
            groups: Dict[tuple, List[dict]] = defaultdict(list)
            for r in self._data:
                key = tuple(r.get(k) for k in self._keys)
                groups[key].append(r)
            return groups

        def agg(self, **agg_exprs) -> DataFrame:
            rows = []
            for key, group in self._groups().items():
                row = {k: v for k, v in zip(self._keys, key)}
                for alias, (func_name, col) in agg_exprs.items():
                    vals = [r.get(col) for r in group if r.get(col) is not None]
                    if func_name == "count":
                        row[alias] = len(group)
                    elif func_name == "sum":
                        row[alias] = sum(vals)
                    elif func_name == "avg":
                        row[alias] = mean(vals) if vals else 0.0
                    elif func_name == "max":
                        row[alias] = max(vals) if vals else None
                    elif func_name == "min":
                        row[alias] = min(vals) if vals else None
                    elif func_name == "stddev":
                        row[alias] = round(stdev(vals), 4) if len(vals) > 1 else 0.0
                rows.append(row)
            return DataFrame(rows)

        def count(self) -> DataFrame:
            rows = []
            for key, group in self._groups().items():
                row = {k: v for k, v in zip(self._keys, key)}
                row["count"] = len(group)
                rows.append(row)
            return DataFrame(rows)

    class SparkSession:
        class builder:
            @staticmethod
            def appName(name: str):
                return SparkSession.builder

            @staticmethod
            def master(url: str):
                return SparkSession.builder

            @staticmethod
            def config(key: str, value: Any):
                return SparkSession.builder

            @staticmethod
            def getOrCreate() -> "SparkSession":
                return SparkSession()

        def createDataFrame(
            self, data: List[dict], schema: StructType = None
        ) -> DataFrame:
            return DataFrame(data, schema)

        def read(self):
            return self

        def parquet(self, path: str) -> DataFrame:
            print(f"[INFO] (Simulated) Reading parquet from: {path}")
            return DataFrame([])  # Caller will supply sample data

        def stop(self):
            print("[INFO] SparkSession stopped.")

    class Window:
        @staticmethod
        def partitionBy(*cols):
            return _WindowSpec(list(cols))

        @staticmethod
        def orderBy(*cols):
            return _WindowSpec([], list(cols))

        @staticmethod
        def rowsBetween(start, end):
            return _WindowSpec()

    class _WindowSpec:
        def __init__(self, partition=None, order=None):
            self._partition = partition or []
            self._order = order or []

        def orderBy(self, *cols):
            return _WindowSpec(self._partition, list(cols))

        def rowsBetween(self, start, end):
            return self

    class F:  # noqa: N801  (shadows import)
        @staticmethod
        def col(name):
            return lambda r: r.get(name)

        @staticmethod
        def count(col):
            return ("count", col)

        @staticmethod
        def sum(col):
            return ("sum", col)

        @staticmethod
        def avg(col):
            return ("avg", col)

        @staticmethod
        def max(col):
            return ("max", col)

        @staticmethod
        def min(col):
            return ("min", col)

        @staticmethod
        def stddev(col):
            return ("stddev", col)

        @staticmethod
        def round(col, decimals=0):
            return lambda r: round(r.get(col) or 0, decimals)

        @staticmethod
        def when(condition, value):
            class WhenExpr:
                def __init__(self, cond, val):
                    self._branches = [(cond, val)]

                def otherwise(self, other_val):
                    def _eval(r):
                        for c, v in self._branches:
                            if c(r):
                                return v(r) if callable(v) else v
                        return other_val(r) if callable(other_val) else other_val

                    return _eval

            return WhenExpr(condition, value)

        @staticmethod
        def lit(val):
            return lambda _: val

        @staticmethod
        def desc(col_name):
            return col_name  # marker only in shim


# ---------------------------------------------------------------------------
# Schema definition
# ---------------------------------------------------------------------------

REPLAY_SCHEMA = StructType(
    [
        StructField("game_id", StringType(), nullable=False),
        StructField("map", StringType(), nullable=False),
        StructField("race", StringType(), nullable=False),
        StructField("opponent_race", StringType(), nullable=False),
        StructField("result", StringType(), nullable=False),  # "win" / "loss"
        StructField("duration", IntegerType(), nullable=False),  # seconds
        StructField("minerals_collected", IntegerType(), nullable=False),
        StructField("gas_collected", IntegerType(), nullable=False),
        StructField("army_supply_peak", IntegerType(), nullable=False),
        StructField("workers_created", IntegerType(), nullable=False),
        StructField("apm", IntegerType(), nullable=False),
    ]
)


# ---------------------------------------------------------------------------
# Sample data generator
# ---------------------------------------------------------------------------

MAPS = [
    "Blackburn LE",
    "Submarine LE",
    "Crimson Court",
    "Ancient Cistern LE",
    "Goldenaura LE",
    "Radhuset Station LE",
    "Gresvan LE",
]
RACES = ["Terran", "Zerg", "Protoss"]


def _make_record(game_id: int, race: str = "Zerg") -> dict:
    opponent_race = random.choice(RACES)
    result = random.choice(["win", "loss"])
    duration = random.randint(180, 1800)
    eco_scale = duration / 1800
    return {
        "game_id": f"g{game_id:06d}",
        "map": random.choice(MAPS),
        "race": race,
        "opponent_race": opponent_race,
        "result": result,
        "duration": duration,
        "minerals_collected": int(random.gauss(3000, 800) * eco_scale),
        "gas_collected": int(random.gauss(1500, 400) * eco_scale),
        "army_supply_peak": random.randint(40, 200),
        "workers_created": int(random.gauss(60, 15) * eco_scale),
        "apm": random.randint(80, 350),
    }


def generate_sample_data(n: int = 2000, race: str = "Zerg") -> List[dict]:
    random.seed(42)
    return [_make_record(i, race) for i in range(n)]


# ---------------------------------------------------------------------------
# Analysis functions
# ---------------------------------------------------------------------------


def read_replay_data(
    spark: SparkSession, path: str, sample_data: List[dict]
) -> DataFrame:
    """Read parquet replay data (falls back to sample_data in non-Spark mode)."""
    if PYSPARK_AVAILABLE:
        try:
            df = spark.read.parquet(path)
            print(f"[INFO] Loaded replay data from {path}: {df.count()} records")
            return df
        except Exception as exc:
            print(f"[WARN] Could not read parquet ({exc}); using sample data.")
    return spark.createDataFrame(sample_data, REPLAY_SCHEMA)


def filter_by_race(df: DataFrame, race: str) -> DataFrame:
    """Keep only records where bot played the given race."""
    if PYSPARK_AVAILABLE:
        return df.filter(F.col("race") == race)
    return df.filter(lambda r: r["race"] == race)


def compute_win_rates(df: DataFrame) -> DataFrame:
    """Win rate per map/matchup combination."""
    if PYSPARK_AVAILABLE:
        return (
            df.groupBy("map", "opponent_race")
            .agg(
                F.count("game_id").alias("total_games"),
                F.sum(
                    F.when(F.col("result") == "win", F.lit(1)).otherwise(F.lit(0))
                ).alias("wins"),
                F.avg("duration").alias("avg_duration"),
                F.avg("apm").alias("avg_apm"),
            )
            .withColumn("win_rate", F.round(F.col("wins") / F.col("total_games"), 4))
            .orderBy("win_rate", ascending=False)
        )

    # Pure-Python path
    groups = defaultdict(list)
    for r in df.collect():
        groups[(r["map"], r["opponent_race"])].append(r)

    rows = []
    for (map_name, opp_race), grp in groups.items():
        total = len(grp)
        wins = sum(1 for r in grp if r["result"] == "win")
        rows.append(
            {
                "map": map_name,
                "opponent_race": opp_race,
                "total_games": total,
                "wins": wins,
                "avg_duration": round(mean(r["duration"] for r in grp), 2),
                "avg_apm": round(mean(r["apm"] for r in grp), 2),
                "win_rate": round(wins / total, 4),
            }
        )
    rows.sort(key=lambda r: r["win_rate"], reverse=True)
    return DataFrame(rows)


def army_composition_aggregation(df: DataFrame) -> DataFrame:
    """Aggregate army supply peak and economy metrics per result bucket."""
    if PYSPARK_AVAILABLE:
        return (
            df.groupBy("result", "opponent_race")
            .agg(
                F.count("game_id").alias("games"),
                F.avg("army_supply_peak").alias("avg_army_supply"),
                F.avg("minerals_collected").alias("avg_minerals"),
                F.avg("gas_collected").alias("avg_gas"),
                F.avg("workers_created").alias("avg_workers"),
                F.stddev("army_supply_peak").alias("stddev_army"),
            )
            .orderBy("result", "opponent_race")
        )

    groups = defaultdict(list)
    for r in df.collect():
        groups[(r["result"], r["opponent_race"])].append(r)

    rows = []
    for (result, opp_race), grp in groups.items():
        armies = [r["army_supply_peak"] for r in grp]
        rows.append(
            {
                "result": result,
                "opponent_race": opp_race,
                "games": len(grp),
                "avg_army_supply": round(mean(r["army_supply_peak"] for r in grp), 2),
                "avg_minerals": round(mean(r["minerals_collected"] for r in grp), 2),
                "avg_gas": round(mean(r["gas_collected"] for r in grp), 2),
                "avg_workers": round(mean(r["workers_created"] for r in grp), 2),
                "stddev_army": round(stdev(armies) if len(armies) > 1 else 0.0, 4),
            }
        )
    rows.sort(key=lambda r: (r["result"], r["opponent_race"]))
    return DataFrame(rows)


def optimal_build_timing_analysis(df: DataFrame) -> DataFrame:
    """
    Identify duration brackets with highest win rates —
    proxy for build order tempo analysis.
    """
    BUCKETS = [
        (0, 300, "0-5min  (early_all_in)"),
        (300, 600, "5-10min (aggression)"),
        (600, 900, "10-15min(mid_game)"),
        (900, 1200, "15-20min(late_mid)"),
        (1200, 99999, "20min+ (macro_late)"),
    ]

    if PYSPARK_AVAILABLE:
        bracket_col = None
        for lo, hi, label in BUCKETS:
            cond = (F.col("duration") >= lo) & (F.col("duration") < hi)
            if bracket_col is None:
                bracket_col = F.when(cond, label)
            else:
                bracket_col = bracket_col.when(cond, label)
        bracket_col = bracket_col.otherwise("unknown")

        return (
            df.withColumn("duration_bracket", bracket_col)
            .groupBy("duration_bracket")
            .agg(
                F.count("game_id").alias("total_games"),
                F.sum(
                    F.when(F.col("result") == "win", F.lit(1)).otherwise(F.lit(0))
                ).alias("wins"),
                F.avg("apm").alias("avg_apm"),
                F.avg("army_supply_peak").alias("avg_army"),
            )
            .withColumn("win_rate", F.round(F.col("wins") / F.col("total_games"), 4))
            .orderBy("win_rate", ascending=False)
        )

    def bucket_label(duration):
        for lo, hi, label in BUCKETS:
            if lo <= duration < hi:
                return label
        return "unknown"

    groups = defaultdict(list)
    for r in df.collect():
        groups[bucket_label(r["duration"])].append(r)

    rows = []
    for bracket, grp in groups.items():
        total = len(grp)
        wins = sum(1 for r in grp if r["result"] == "win")
        rows.append(
            {
                "duration_bracket": bracket,
                "total_games": total,
                "wins": wins,
                "avg_apm": round(mean(r["apm"] for r in grp), 2),
                "avg_army": round(mean(r["army_supply_peak"] for r in grp), 2),
                "win_rate": round(wins / total, 4),
            }
        )
    rows.sort(key=lambda r: r["win_rate"], reverse=True)
    return DataFrame(rows)


def rolling_win_rate(df: DataFrame, window_size: int = 50) -> DataFrame:
    """
    Compute rolling win rate over the last `window_size` games (ordered by game_id).
    Uses window functions in Spark; manual rolling average in pure Python.
    """
    if PYSPARK_AVAILABLE:
        win_flag = F.when(F.col("result") == "win", F.lit(1)).otherwise(F.lit(0))
        w = Window.orderBy("game_id").rowsBetween(-window_size + 1, 0)
        return (
            df.withColumn("win_flag", win_flag)
            .withColumn("rolling_win_rate", F.round(F.avg("win_flag").over(w), 4))
            .select("game_id", "result", "win_flag", "rolling_win_rate")
            .orderBy("game_id")
        )

    records = sorted(df.collect(), key=lambda r: r["game_id"])
    flags = [1 if r["result"] == "win" else 0 for r in records]
    rows = []
    for i, r in enumerate(records):
        window_flags = flags[max(0, i - window_size + 1) : i + 1]
        rolling = round(mean(window_flags), 4) if window_flags else 0.0
        rows.append(
            {
                "game_id": r["game_id"],
                "result": r["result"],
                "win_flag": flags[i],
                "rolling_win_rate": rolling,
            }
        )
    return DataFrame(rows)


def compute_summary_stats(
    win_rate_df: DataFrame,
    army_df: DataFrame,
    build_timing_df: DataFrame,
) -> dict:
    """Collect scalar summary statistics from analysis DataFrames."""
    wr_rows = win_rate_df.collect()
    army_rows = army_df.collect()
    bt_rows = build_timing_df.collect()

    overall_win_rate = mean(r["win_rate"] for r in wr_rows) if wr_rows else 0.0
    best_map = max(wr_rows, key=lambda r: r["win_rate"])["map"] if wr_rows else "N/A"
    best_bracket = bt_rows[0]["duration_bracket"] if bt_rows else "N/A"
    best_bracket_wr = bt_rows[0]["win_rate"] if bt_rows else 0.0

    win_army = [r["avg_army_supply"] for r in army_rows if r["result"] == "win"]
    loss_army = [r["avg_army_supply"] for r in army_rows if r["result"] == "loss"]

    return {
        "overall_win_rate": round(overall_win_rate, 4),
        "best_map": best_map,
        "best_duration_bracket": best_bracket,
        "best_bracket_win_rate": best_bracket_wr,
        "avg_army_on_win": round(mean(win_army), 2) if win_army else 0.0,
        "avg_army_on_loss": round(mean(loss_army), 2) if loss_army else 0.0,
        "total_matchup_combinations": len(wr_rows),
    }


# ---------------------------------------------------------------------------
# Main entrypoint
# ---------------------------------------------------------------------------


def run_analysis(
    parquet_path: str = "s3://sc2-replays/processed/replays.parquet",
    race_filter: str = "Zerg",
    num_sample_records: int = 2000,
) -> dict:
    print("\n" + "=" * 60)
    print("  SC2 Replay Analytics — PySpark Job")
    print("  Phase 577: Spark Jobs")
    print("=" * 60 + "\n")

    spark = (
        SparkSession.builder.appName("SC2ReplayAnalytics")
        .master("local[*]")
        .config("spark.sql.shuffle.partitions", "8")
        .getOrCreate()
    )

    # 1. Generate / load data
    sample = generate_sample_data(n=num_sample_records, race=race_filter)
    df = read_replay_data(spark, parquet_path, sample)
    print(f"[STEP 1] Total records loaded: {df.count()}")

    # 2. Filter by race
    df_race = filter_by_race(df, race_filter)
    print(f"[STEP 2] Records after race filter ({race_filter}): {df_race.count()}\n")

    # 3. Win rates per map/matchup
    print("[STEP 3] Win rates per map / matchup:")
    win_rate_df = compute_win_rates(df_race)
    win_rate_df.show(10)

    # 4. Army composition aggregation
    print("[STEP 4] Army composition aggregation (result × opponent_race):")
    army_df = army_composition_aggregation(df_race)
    army_df.show(12)

    # 5. Build timing analysis
    print("[STEP 5] Optimal build timing (duration brackets):")
    build_timing_df = optimal_build_timing_analysis(df_race)
    build_timing_df.show()

    # 6. Rolling win rate (sample of first 100 games)
    print("[STEP 6] Rolling win rate (last 50 games window, first 10 shown):")
    rolling_df = rolling_win_rate(df_race.limit(200))
    rolling_df.limit(10).show()

    # 7. Summary
    summary = compute_summary_stats(win_rate_df, army_df, build_timing_df)
    print("[STEP 7] Summary Statistics:")
    for k, v in summary.items():
        print(f"  {k:<35} = {v}")

    spark.stop()
    print("\n[DONE] SC2 Replay Analytics complete.")
    return summary


if __name__ == "__main__":
    results = run_analysis(
        parquet_path="s3://sc2-replays/processed/replays.parquet",
        race_filter="Zerg",
        num_sample_records=2000,
    )
