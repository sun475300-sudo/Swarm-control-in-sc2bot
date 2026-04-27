"""
Phase 444: ScyllaDB - SC2 Time-Series Game Events
High-throughput event logging using ScyllaDB (C++ Cassandra-compatible).
"""

import asyncio
import logging
from datetime import datetime, timezone
from cassandra.cluster import Cluster
from cassandra.query import BatchStatement, BatchType
from cassandra.policies import DCAwareRoundRobinPolicy
import uuid

logger = logging.getLogger(__name__)

SCYLLA_HOSTS = ["127.0.0.1"]
SCYLLA_PORT = 9042
KEYSPACE = "sc2bot"


def get_session():
    """Connect to ScyllaDB cluster."""
    cluster = Cluster(
        contact_points=SCYLLA_HOSTS,
        port=SCYLLA_PORT,
        load_balancing_policy=DCAwareRoundRobinPolicy(local_dc="datacenter1"),
    )
    session = cluster.connect()
    return cluster, session


def setup_keyspace_and_tables(session):
    """Create keyspace and time-series tables."""
    session.execute(f"""
        CREATE KEYSPACE IF NOT EXISTS {KEYSPACE}
        WITH replication = {{'class': 'SimpleStrategy', 'replication_factor': 1}}
    """)
    session.set_keyspace(KEYSPACE)

    session.execute("""
        CREATE TABLE IF NOT EXISTS game_events (
            game_id     TEXT,
            event_time  TIMESTAMP,
            event_type  TEXT,
            unit_name   TEXT,
            x           INT,
            y           INT,
            value       INT,
            metadata    MAP<TEXT, TEXT>,
            PRIMARY KEY ((game_id), event_time, event_type)
        ) WITH CLUSTERING ORDER BY (event_time ASC)
          AND default_time_to_live = 604800
    """)

    session.execute("""
        CREATE TABLE IF NOT EXISTS game_summary (
            game_id    TEXT PRIMARY KEY,
            player_id  TEXT,
            map_name   TEXT,
            result     TEXT,
            duration   INT,
            total_apm  INT,
            created_at TIMESTAMP
        )
    """)
    logger.info("ScyllaDB keyspace and tables ready.")


def batch_insert_events(session, game_id: str, events: list[dict]):
    """Batch insert game events for high throughput."""
    insert_stmt = session.prepare("""
        INSERT INTO game_events
            (game_id, event_time, event_type, unit_name, x, y, value, metadata)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
    """)

    batch = BatchStatement(batch_type=BatchType.UNLOGGED)
    for ev in events:
        batch.add(
            insert_stmt,
            (
                game_id,
                ev.get("event_time", datetime.now(timezone.utc)),
                ev.get("event_type", "unknown"),
                ev.get("unit_name", ""),
                ev.get("x", 0),
                ev.get("y", 0),
                ev.get("value", 0),
                ev.get("metadata", {}),
            ),
        )
    session.execute(batch)
    logger.info(f"Batch inserted {len(events)} events for game {game_id}")


def query_events_by_type(session, game_id: str, event_type: str) -> list:
    """Query events for a game filtered by type."""
    rows = session.execute(
        "SELECT * FROM game_events WHERE game_id = %s AND event_type = %s ALLOW FILTERING",
        (game_id, event_type),
    )
    return list(rows)


def get_game_timeline(session, game_id: str, limit: int = 100) -> list:
    """Get ordered timeline of events for a game."""
    rows = session.execute(
        "SELECT event_time, event_type, unit_name, x, y, value FROM game_events "
        "WHERE game_id = %s LIMIT %s",
        (game_id, limit),
    )
    return list(rows)


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    cluster, session = get_session()
    setup_keyspace_and_tables(session)

    game_id = "game_" + str(uuid.uuid4())[:8]
    sample_events = [
        {
            "event_type": "unit_created",
            "unit_name": "Zergling",
            "x": 10,
            "y": 20,
            "value": 1,
        },
        {
            "event_type": "unit_died",
            "unit_name": "Marine",
            "x": 50,
            "y": 60,
            "value": 0,
        },
        {
            "event_type": "building_started",
            "unit_name": "Hatchery",
            "x": 5,
            "y": 5,
            "value": 300,
        },
    ]
    batch_insert_events(session, game_id, sample_events)
    timeline = get_game_timeline(session, game_id)
    print(f"Timeline for {game_id}:", timeline)
    cluster.shutdown()
