"""
Phase 460: Snowflake - SC2 Cloud Data Warehouse
snowflake-connector-python with Snowpark DataFrame API, dynamic data masking, async queries.
"""

import asyncio
import logging
from contextlib import asynccontextmanager
from typing import Optional
import snowflake.connector
from snowflake.connector.cursor import DictCursor
from snowflake.snowpark import Session
from snowflake.snowpark.functions import col, avg, count, when, lit
from snowflake.snowpark.types import IntegerType, StringType, DoubleType

logger = logging.getLogger(__name__)

SNOWFLAKE_CONFIG = {
    "account":   "xy12345.us-east-1",
    "user":      "sc2bot_user",
    "password":  "your_password_here",
    "warehouse": "SC2_WH",
    "database":  "SC2_DB",
    "schema":    "ANALYTICS",
    "role":      "SC2_DATA_ROLE",
}


# ---- Snowpark Session ----

def get_snowpark_session() -> Session:
    """Create a Snowpark session for DataFrame-style operations."""
    session = Session.builder.configs(SNOWFLAKE_CONFIG).create()
    logger.info("Snowpark session created.")
    return session


# ---- Dynamic Data Masking ----

def setup_data_masking(conn):
    """Create masking policies for PII protection."""
    cursor = conn.cursor()
    # Mask player_id for non-admin roles (show hash only)
    cursor.execute("""
        CREATE MASKING POLICY IF NOT EXISTS mask_player_id AS (val STRING)
        RETURNS STRING ->
            CASE
                WHEN CURRENT_ROLE() IN ('SC2_ADMIN', 'SC2_BOT_SERVICE') THEN val
                ELSE SHA2(val, 256)
            END
    """)
    # Apply masking policy to players table
    cursor.execute("""
        ALTER TABLE SC2_DB.ANALYTICS.PLAYERS
        MODIFY COLUMN player_id
        SET MASKING POLICY mask_player_id
    """)
    logger.info("Dynamic data masking applied to player_id.")
    cursor.close()


# ---- Schema setup ----

def create_tables(conn):
    """Create SC2 analytics tables in Snowflake."""
    cursor = conn.cursor()
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS games (
            game_id       VARCHAR(64)  NOT NULL,
            player_id     VARCHAR(64),
            opponent_id   VARCHAR(64),
            player_race   VARCHAR(16),
            opponent_race VARCHAR(16),
            map_name      VARCHAR(128),
            result        VARCHAR(8),
            apm           INTEGER,
            mmr           INTEGER,
            duration_sec  INTEGER,
            win_rate      FLOAT,
            game_date     DATE,
            created_at    TIMESTAMP_NTZ DEFAULT CURRENT_TIMESTAMP()
        )
        CLUSTER BY (game_date, player_race)
    """)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS players (
            player_id    VARCHAR(64) PRIMARY KEY,
            name         VARCHAR(128),
            race         VARCHAR(16),
            current_mmr  INTEGER,
            total_games  INTEGER DEFAULT 0,
            win_rate     FLOAT,
            updated_at   TIMESTAMP_NTZ DEFAULT CURRENT_TIMESTAMP()
        )
    """)
    logger.info("Snowflake tables created.")
    cursor.close()


# ---- Snowpark Transformations ----

def compute_race_stats(session: Session):
    """Use Snowpark DataFrame API to compute win stats per race."""
    games = session.table("games")
    stats = (
        games
        .filter(col("result").isin("win", "loss"))
        .group_by("player_race")
        .agg(
            count("*").alias("total_games"),
            avg(when(col("result") == lit("win"), lit(1)).otherwise(lit(0))).alias("win_rate"),
            avg("apm").alias("avg_apm"),
            avg("mmr").alias("avg_mmr"),
        )
        .sort(col("win_rate").desc())
    )
    return stats


def player_ranking(session: Session, top_n: int = 20):
    """Rank players by MMR using Snowpark window functions."""
    from snowflake.snowpark.functions import rank
    from snowflake.snowpark.window import Window

    players = session.table("players")
    window = Window.order_by(col("current_mmr").desc())
    ranked = players.with_column("rank", rank().over(window)).limit(top_n)
    return ranked


# ---- Async Queries ----

async def async_bulk_insert(conn, records: list[dict]):
    """Async bulk insert using executemany."""
    loop = asyncio.get_event_loop()
    cursor = conn.cursor()

    insert_sql = """
        INSERT INTO games (game_id, player_id, player_race, map_name, result, apm, mmr, duration_sec, game_date)
        VALUES (%(game_id)s, %(player_id)s, %(player_race)s, %(map_name)s, %(result)s,
                %(apm)s, %(mmr)s, %(duration_sec)s, %(game_date)s)
    """
    await loop.run_in_executor(None, cursor.executemany, insert_sql, records)
    logger.info(f"Bulk inserted {len(records)} game records.")
    cursor.close()


def run_analytics_query(conn, query: str) -> list[dict]:
    """Run an analytics query and return results as dicts."""
    cursor = conn.cursor(DictCursor)
    cursor.execute(query)
    results = cursor.fetchall()
    cursor.close()
    return results


async def main():
    logging.basicConfig(level=logging.INFO)
    conn = snowflake.connector.connect(**SNOWFLAKE_CONFIG)
    create_tables(conn)
    setup_data_masking(conn)

    session = get_snowpark_session()
    race_stats = compute_race_stats(session)
    race_stats.show()

    ranking = player_ranking(session, top_n=10)
    ranking.show()

    sample = [
        {"game_id": "g001", "player_id": "ZergBot", "player_race": "Zerg",
         "map_name": "Solaris", "result": "win", "apm": 185,
         "mmr": 4200, "duration_sec": 420, "game_date": "2026-03-31"},
    ]
    await async_bulk_insert(conn, sample)
    session.close()
    conn.close()


if __name__ == "__main__":
    asyncio.run(main())
