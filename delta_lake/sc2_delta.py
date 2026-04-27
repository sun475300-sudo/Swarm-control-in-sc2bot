"""
Phase 456: Delta Lake - SC2 Training Data with ACID Transactions
Upsert (merge), time travel, and schema evolution for ML feature data.
"""

import logging
from datetime import datetime
from pyspark.sql import SparkSession
from pyspark.sql.functions import col, current_timestamp, lit
from pyspark.sql.types import (
    StructType,
    StructField,
    StringType,
    IntegerType,
    DoubleType,
    TimestampType,
    BooleanType,
)
from delta.tables import DeltaTable

logger = logging.getLogger(__name__)

DELTA_PATH = "s3a://sc2-data-lake/delta/game_records/"
DELTA_CHECKPOINTS = "s3a://sc2-data-lake/delta/_checkpoints/"


def get_spark() -> SparkSession:
    """Initialize Spark with Delta Lake extensions."""
    return (
        SparkSession.builder.appName("SC2DeltaLake")
        .config("spark.sql.extensions", "io.delta.sql.DeltaSparkSessionExtension")
        .config(
            "spark.sql.catalog.spark_catalog",
            "org.apache.spark.sql.delta.catalog.DeltaCatalog",
        )
        .config("spark.databricks.delta.retentionDurationCheck.enabled", "false")
        .getOrCreate()
    )


def get_schema() -> StructType:
    return StructType(
        [
            StructField("game_id", StringType(), False),
            StructField("player_id", StringType(), True),
            StructField("player_race", StringType(), True),
            StructField("map_name", StringType(), True),
            StructField("result", StringType(), True),
            StructField("apm", IntegerType(), True),
            StructField("mmr", IntegerType(), True),
            StructField("duration_sec", IntegerType(), True),
            StructField("win_rate", DoubleType(), True),
            StructField("processed", BooleanType(), True),
            StructField("updated_at", TimestampType(), True),
        ]
    )


def create_delta_table(spark: SparkSession):
    """Create Delta table if it doesn't exist."""
    if not DeltaTable.isDeltaTable(spark, DELTA_PATH):
        empty_df = spark.createDataFrame([], schema=get_schema())
        empty_df.write.format("delta").partitionBy("player_race").save(DELTA_PATH)
        logger.info("Delta table created.")
    else:
        logger.info("Delta table already exists.")


def merge_game_records(spark: SparkSession, new_records: list[dict]):
    """Upsert game records using Delta merge (SCD Type 1)."""
    new_df = spark.createDataFrame(new_records, schema=get_schema())
    new_df = new_df.withColumn("updated_at", current_timestamp())

    delta_table = DeltaTable.forPath(spark, DELTA_PATH)
    delta_table.alias("target").merge(
        new_df.alias("source"), "target.game_id = source.game_id"
    ).whenMatchedUpdate(
        set={
            "player_race": "source.player_race",
            "map_name": "source.map_name",
            "result": "source.result",
            "apm": "source.apm",
            "mmr": "source.mmr",
            "win_rate": "source.win_rate",
            "processed": "source.processed",
            "updated_at": "source.updated_at",
        }
    ).whenNotMatchedInsertAll().execute()

    logger.info(f"Merged {len(new_records)} game records into Delta table.")


def time_travel_read(spark: SparkSession, version: int = None, timestamp: str = None):
    """Read Delta table at a specific version or timestamp."""
    reader = spark.read.format("delta")
    if version is not None:
        reader = reader.option("versionAsOf", version)
        label = f"version {version}"
    elif timestamp:
        reader = reader.option("timestampAsOf", timestamp)
        label = f"timestamp {timestamp}"
    else:
        label = "latest"
    df = reader.load(DELTA_PATH)
    logger.info(f"Time travel read ({label}): {df.count()} records.")
    return df


def add_new_feature_column(spark: SparkSession):
    """Schema evolution: add 'supply_peak' column to existing table."""
    delta_table = DeltaTable.forPath(spark, DELTA_PATH)
    spark.sql(f"""
        ALTER TABLE delta.`{DELTA_PATH}`
        ADD COLUMNS (supply_peak INT AFTER mmr)
    """)
    logger.info("Schema evolved: added supply_peak column.")


def get_table_history(spark: SparkSession) -> list[dict]:
    """Return Delta table transaction history."""
    delta_table = DeltaTable.forPath(spark, DELTA_PATH)
    history_df = delta_table.history(20)
    history = [row.asDict() for row in history_df.collect()]
    logger.info(f"Table has {len(history)} history entries.")
    return history


def vacuum_old_files(spark: SparkSession, retain_hours: int = 168):
    """Remove files older than retain_hours from Delta table."""
    delta_table = DeltaTable.forPath(spark, DELTA_PATH)
    delta_table.vacuum(retain_hours)
    logger.info(f"Vacuum complete (retained {retain_hours}h).")


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    spark = get_spark()
    create_delta_table(spark)

    sample_records = [
        {
            "game_id": "g001",
            "player_id": "ZergBot",
            "player_race": "Zerg",
            "map_name": "Solaris",
            "result": "win",
            "apm": 185,
            "mmr": 4200,
            "duration_sec": 420,
            "win_rate": 0.62,
            "processed": False,
            "updated_at": datetime.now(),
        },
    ]
    merge_game_records(spark, sample_records)

    df = time_travel_read(spark, version=0)
    df.show()

    history = get_table_history(spark)
    print(f"History entries: {len(history)}")
    spark.stop()
