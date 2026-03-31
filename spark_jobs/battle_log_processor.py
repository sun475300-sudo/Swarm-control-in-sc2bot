# spark_jobs/battle_log_processor.py
# PySpark job for distributed SC2 Zerg battle log analysis

from pyspark.sql import SparkSession
from pyspark.sql import functions as F
from pyspark.sql.types import (
    StructType, StructField, StringType, IntegerType, FloatType, BooleanType
)

# ---------------------------------------------------------------------------
# SparkSession
# ---------------------------------------------------------------------------
spark = (
    SparkSession.builder
    .appName("SC2_BattleLogProcessor")
    .config("spark.sql.shuffle.partitions", "8")
    .getOrCreate()
)
spark.sparkContext.setLogLevel("WARN")

# ---------------------------------------------------------------------------
# Schema definition for battle_logs.csv
# ---------------------------------------------------------------------------
battle_schema = StructType([
    StructField("game_id",      StringType(),  nullable=False),
    StructField("matchup",      StringType(),  nullable=True),   # ZvT / ZvZ / ZvP
    StructField("result",       StringType(),  nullable=True),   # win / loss
    StructField("duration_sec", IntegerType(), nullable=True),
    StructField("build_order",  StringType(),  nullable=True),
    StructField("army_value",   IntegerType(), nullable=True),
    StructField("minerals_used",IntegerType(), nullable=True),
    StructField("gas_used",     IntegerType(), nullable=True),
    StructField("units_lost",   IntegerType(), nullable=True),
    StructField("units_killed", IntegerType(), nullable=True),
    StructField("supply_peak",  IntegerType(), nullable=True),
])

# ---------------------------------------------------------------------------
# Load data
# ---------------------------------------------------------------------------
INPUT_PATH  = "/data/battle_logs.csv"
OUTPUT_PATH = "/data/battle_log_output"

df = (
    spark.read
    .option("header", "true")
    .schema(battle_schema)
    .csv(INPUT_PATH)
)

# ---------------------------------------------------------------------------
# Parse & clean structured data
# ---------------------------------------------------------------------------
df_clean = (
    df
    .filter(F.col("matchup").isin("ZvT", "ZvZ", "ZvP"))
    .withColumn("is_win", (F.col("result") == "win").cast(BooleanType()))
    .withColumn(
        "kill_death_ratio",
        F.when(F.col("units_lost") > 0,
               F.col("units_killed") / F.col("units_lost"))
         .otherwise(F.col("units_killed").cast(FloatType()))
    )
    .withColumn(
        "resource_efficiency",
        F.when((F.col("minerals_used") + F.col("gas_used")) > 0,
               F.col("army_value") / (F.col("minerals_used") + F.col("gas_used")))
         .otherwise(F.lit(0.0))
    )
)

# ---------------------------------------------------------------------------
# Aggregate win rates by matchup (ZvT / ZvZ / ZvP)
# ---------------------------------------------------------------------------
win_rates = (
    df_clean
    .groupBy("matchup")
    .agg(
        F.count("*").alias("total_games"),
        F.sum(F.col("is_win").cast("int")).alias("wins"),
        F.round(
            F.mean(F.col("is_win").cast("int")) * 100, 2
        ).alias("win_rate_pct"),
        F.round(F.avg("duration_sec"), 1).alias("avg_duration_sec"),
    )
    .orderBy("matchup")
)

print("=== Win Rates by Matchup ===")
win_rates.show()

# ---------------------------------------------------------------------------
# Unit efficiency statistics
# ---------------------------------------------------------------------------
unit_efficiency = (
    df_clean
    .groupBy("matchup")
    .agg(
        F.round(F.avg("kill_death_ratio"),    2).alias("avg_kd_ratio"),
        F.round(F.avg("resource_efficiency"), 4).alias("avg_resource_eff"),
        F.round(F.avg("supply_peak"),         1).alias("avg_supply_peak"),
        F.round(F.avg("army_value"),          0).alias("avg_army_value"),
    )
    .orderBy("matchup")
)

print("=== Unit Efficiency Stats ===")
unit_efficiency.show()

# ---------------------------------------------------------------------------
# Top-N most effective build orders (by win rate, min 5 games)
# ---------------------------------------------------------------------------
TOP_N = 10

top_builds = (
    df_clean
    .groupBy("matchup", "build_order")
    .agg(
        F.count("*").alias("games"),
        F.round(F.mean(F.col("is_win").cast("int")) * 100, 2).alias("win_rate_pct"),
        F.round(F.avg("kill_death_ratio"), 2).alias("avg_kd"),
    )
    .filter(F.col("games") >= 5)
    .orderBy(F.desc("win_rate_pct"), F.desc("games"))
    .limit(TOP_N)
)

print(f"=== Top {TOP_N} Most Effective Build Orders ===")
top_builds.show(truncate=False)

# ---------------------------------------------------------------------------
# Write aggregated output as Parquet
# ---------------------------------------------------------------------------
win_rates.write.mode("overwrite").parquet(f"{OUTPUT_PATH}/win_rates")
unit_efficiency.write.mode("overwrite").parquet(f"{OUTPUT_PATH}/unit_efficiency")
top_builds.write.mode("overwrite").parquet(f"{OUTPUT_PATH}/top_builds")

print(f"Output written to {OUTPUT_PATH}")
spark.stop()
