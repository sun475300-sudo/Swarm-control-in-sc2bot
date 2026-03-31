"""
Phase 455: Apache Hudi - SC2 Replay Archive Data Lake
Copy-on-Write table with upserts, incremental queries for new games.
"""

import logging
from datetime import datetime, timedelta
from pyspark.sql import SparkSession
from pyspark.sql.functions import col, lit, current_timestamp, to_date
from pyspark.sql.types import StructType, StructField, StringType, IntegerType, DoubleType, TimestampType

logger = logging.getLogger(__name__)

HUDI_TABLE_NAME = "sc2_replays"
HUDI_BASE_PATH  = "s3a://sc2-data-lake/hudi/replays/"

# Hudi options for Copy-on-Write table
COW_OPTIONS = {
    "hoodie.table.name": HUDI_TABLE_NAME,
    "hoodie.datasource.write.recordkey.field": "game_id",
    "hoodie.datasource.write.precombine.field": "updated_at",
    "hoodie.datasource.write.partitionpath.field": "game_date",
    "hoodie.datasource.write.table.type": "COPY_ON_WRITE",
    "hoodie.datasource.write.operation": "upsert",
    "hoodie.datasource.hive_sync.enable": "false",
    "hoodie.cleaner.policy": "KEEP_LATEST_COMMITS",
    "hoodie.cleaner.commits.retained": "10",
    "hoodie.keep.min.commits": "20",
    "hoodie.keep.max.commits": "30",
}


def get_spark() -> SparkSession:
    """Initialize Spark with Hudi packages."""
    return (
        SparkSession.builder
        .appName("SC2HudiPipeline")
        .config("spark.serializer", "org.apache.spark.serializer.KryoSerializer")
        .config("spark.sql.catalog.spark_catalog", "org.apache.spark.sql.hudi.catalog.HoodieCatalog")
        .config("spark.sql.extensions", "org.apache.spark.sql.hudi.HoodieSparkSessionExtension")
        .config("spark.hadoop.fs.s3a.impl", "org.apache.hadoop.fs.s3a.S3AFileSystem")
        .getOrCreate()
    )


def get_schema() -> StructType:
    return StructType([
        StructField("game_id",      StringType(),  False),
        StructField("player_id",    StringType(),  True),
        StructField("opponent_id",  StringType(),  True),
        StructField("player_race",  StringType(),  True),
        StructField("map_name",     StringType(),  True),
        StructField("result",       StringType(),  True),
        StructField("apm",          IntegerType(), True),
        StructField("mmr",          IntegerType(), True),
        StructField("duration_sec", IntegerType(), True),
        StructField("win_rate",     DoubleType(),  True),
        StructField("game_date",    StringType(),  True),  # partition key
        StructField("updated_at",   TimestampType(), True),
    ])


def upsert_games(spark: SparkSession, game_records: list[dict]):
    """Upsert game records into Hudi table (merge on game_id)."""
    df = spark.createDataFrame(game_records, schema=get_schema())
    df = df.withColumn("updated_at", current_timestamp())

    df.write.format("hudi") \
        .options(**COW_OPTIONS) \
        .mode("append") \
        .save(HUDI_BASE_PATH)

    logger.info(f"Upserted {df.count()} game records to Hudi.")


def incremental_query(spark: SparkSession, begin_instant: str, end_instant: str = None):
    """Read only new/changed games since a given commit instant."""
    read_options = {
        "hoodie.datasource.query.type": "incremental",
        "hoodie.datasource.read.begin.instanttime": begin_instant,
    }
    if end_instant:
        read_options["hoodie.datasource.read.end.instanttime"] = end_instant

    df = spark.read.format("hudi").options(**read_options).load(HUDI_BASE_PATH)
    logger.info(f"Incremental query returned {df.count()} new/changed records.")
    return df


def snapshot_query(spark: SparkSession, game_date: str = None):
    """Snapshot (full) read of Hudi table, optionally filtered by partition."""
    df = spark.read.format("hudi").load(HUDI_BASE_PATH)
    if game_date:
        df = df.filter(col("game_date") == game_date)
    return df


def time_travel_query(spark: SparkSession, as_of_instant: str):
    """Read data as it was at a specific Hudi commit instant."""
    df = spark.read.format("hudi") \
        .option("as.of.instant", as_of_instant) \
        .load(HUDI_BASE_PATH)
    logger.info(f"Time travel query as of {as_of_instant}: {df.count()} records.")
    return df


def compact_table(spark: SparkSession):
    """Run Hudi table compaction (MOR tables) and cleaning."""
    spark.sql(f"""
        CALL run_compaction(table => '{HUDI_TABLE_NAME}')
    """)
    logger.info("Hudi compaction triggered.")


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    spark = get_spark()

    sample_games = [
        {"game_id": "g001", "player_id": "ZergBot", "opponent_id": "TerranAI",
         "player_race": "Zerg", "map_name": "Solaris", "result": "win",
         "apm": 185, "mmr": 4200, "duration_sec": 420, "win_rate": 0.62,
         "game_date": "2026-03-31", "updated_at": datetime.now()},
    ]

    upsert_games(spark, sample_games)
    df = snapshot_query(spark, game_date="2026-03-31")
    df.show()
    spark.stop()
