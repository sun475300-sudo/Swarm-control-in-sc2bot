"""
Phase 457: Apache Iceberg - SC2 Data Lake Table Format
PyIceberg catalog, partitioning, schema evolution, snapshot management.
"""

import logging
from datetime import date, datetime

from pyiceberg.catalog import load_catalog
from pyiceberg.expressions import And, EqualTo, GreaterThanOrEqual
from pyiceberg.partitioning import PartitionField, PartitionSpec
from pyiceberg.schema import Schema
from pyiceberg.table.snapshots import Operation
from pyiceberg.transforms import DayTransform, IdentityTransform
from pyiceberg.types import (
    BooleanType,
    DateType,
    DoubleType,
    IntegerType,
    NestedField,
    StringType,
    TimestampType,
)

logger = logging.getLogger(__name__)

CATALOG_NAME = "sc2_catalog"
NAMESPACE = "sc2bot"
TABLE_NAME = "game_records"
FULL_TABLE = f"{NAMESPACE}.{TABLE_NAME}"

# Iceberg schema for SC2 game records
SC2_SCHEMA = Schema(
    NestedField(1, "game_id", StringType(), required=True),
    NestedField(2, "player_id", StringType(), required=True),
    NestedField(3, "player_race", StringType(), required=False),
    NestedField(4, "opponent_race", StringType(), required=False),
    NestedField(5, "map_name", StringType(), required=False),
    NestedField(6, "result", StringType(), required=False),
    NestedField(7, "apm", IntegerType(), required=False),
    NestedField(8, "mmr", IntegerType(), required=False),
    NestedField(9, "duration_sec", IntegerType(), required=False),
    NestedField(10, "win_rate", DoubleType(), required=False),
    NestedField(11, "game_date", DateType(), required=True),
    NestedField(12, "race_matchup", StringType(), required=False),
    NestedField(13, "processed", BooleanType(), required=False),
    NestedField(14, "created_at", TimestampType(), required=False),
)

# Partition by game_date (day) and race_matchup (identity)
SC2_PARTITION = PartitionSpec(
    PartitionField(
        source_id=11, field_id=100, transform=DayTransform(), name="game_date_day"
    ),
    PartitionField(
        source_id=12, field_id=101, transform=IdentityTransform(), name="race_matchup"
    ),
)


def load_sc2_catalog():
    """Load PyIceberg catalog (REST or local filesystem)."""
    catalog = load_catalog(
        CATALOG_NAME,
        **{
            "type": "rest",
            "uri": "http://localhost:8181",
            "s3.endpoint": "http://localhost:9000",
            "s3.access-key-id": "minioadmin",
            "s3.secret-access-key": "minioadmin",
        },
    )
    return catalog


def setup_catalog(catalog):
    """Create namespace and table if not exists."""
    if NAMESPACE not in [ns[0] for ns in catalog.list_namespaces()]:
        catalog.create_namespace(NAMESPACE)
        logger.info(f"Namespace {NAMESPACE} created.")

    try:
        table = catalog.load_table(FULL_TABLE)
        logger.info(f"Table {FULL_TABLE} already exists.")
    except Exception:
        table = catalog.create_table(
            identifier=FULL_TABLE,
            schema=SC2_SCHEMA,
            partition_spec=SC2_PARTITION,
            properties={
                "write.format.default": "parquet",
                "write.parquet.compression-codec": "snappy",
                "write.metadata.compression-codec": "gzip",
            },
        )
        logger.info(f"Table {FULL_TABLE} created.")
    return table


def append_games(table, records: list[dict]):
    """Append new game records to the Iceberg table."""
    import pyarrow as pa

    arrow_schema = table.schema().as_arrow()
    arrow_table = pa.Table.from_pylist(records, schema=arrow_schema)
    table.append(arrow_table)
    logger.info(f"Appended {len(records)} records to {FULL_TABLE}.")


def query_by_partition(table, game_date: date, race_matchup: str = None):
    """Scan table with partition pruning filters."""
    filters = [GreaterThanOrEqual("game_date", str(game_date))]
    if race_matchup:
        filters.append(EqualTo("race_matchup", race_matchup))
    scan = table.scan(row_filter=And(*filters) if len(filters) > 1 else filters[0])
    return scan.to_arrow()


def evolve_schema(catalog, new_column_name: str = "supply_peak"):
    """Schema evolution: add a new column without rewriting data."""
    table = catalog.load_table(FULL_TABLE)
    with table.update_schema() as update:
        update.add_column(new_column_name, IntegerType())
    logger.info(f"Schema evolved: added column {new_column_name}.")


def manage_snapshots(table):
    """List and expire old snapshots to manage storage."""
    snapshots = table.snapshots()
    logger.info(f"Total snapshots: {len(snapshots)}")
    for snap in snapshots[-3:]:
        logger.info(
            f"  Snapshot {snap.snapshot_id}: operation={snap.summary.get('operation')}"
        )

    # Expire snapshots older than 7 days
    table.expire_snapshots().expire_older_than(
        datetime.now().timestamp() * 1000 - 7 * 24 * 3600 * 1000
    ).commit()
    logger.info("Old snapshots expired.")


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    print("SC2 Iceberg catalog schema defined.")
    print(f"Fields: {[f.name for f in SC2_SCHEMA.fields]}")
    print(f"Partitions: game_date_day, race_matchup")
