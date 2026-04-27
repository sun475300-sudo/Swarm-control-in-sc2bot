"""
Phase 442: SurrealDB - SC2 Multi-Model Database
Document + graph relations using surrealdb Python async client.
"""

import asyncio
import logging
from datetime import datetime
from surrealdb import Surreal

logger = logging.getLogger(__name__)

SURREAL_URL = "ws://localhost:8000/rpc"
NAMESPACE = "sc2bot"
DATABASE = "games"


async def connect() -> Surreal:
    db = Surreal(SURREAL_URL)
    await db.connect()
    await db.signin({"user": "root", "pass": "root"})
    await db.use(NAMESPACE, DATABASE)
    return db


async def setup_schema(db: Surreal):
    """Define SurrealDB schema for SC2 data."""
    await db.query("""
        DEFINE TABLE game SCHEMAFULL;
        DEFINE FIELD game_id ON game TYPE string;
        DEFINE FIELD map ON game TYPE string;
        DEFINE FIELD duration ON game TYPE int;
        DEFINE FIELD result ON game TYPE string;
        DEFINE FIELD played_at ON game TYPE datetime;

        DEFINE TABLE player SCHEMAFULL;
        DEFINE FIELD player_id ON player TYPE string;
        DEFINE FIELD name ON player TYPE string;
        DEFINE FIELD race ON player TYPE string;
        DEFINE FIELD mmr ON player TYPE int;

        DEFINE TABLE unit_graph SCHEMAFULL TYPE RELATION IN player OUT game;
        DEFINE FIELD apm ON unit_graph TYPE int;
        DEFINE FIELD units_made ON unit_graph TYPE array;
    """)
    logger.info("SurrealDB schema defined.")


async def insert_game(db: Surreal, game_data: dict) -> str:
    """Insert a game document record."""
    result = await db.create(
        "game",
        {
            "game_id": game_data["game_id"],
            "map": game_data.get("map", "Unknown"),
            "duration": game_data.get("duration", 0),
            "result": game_data.get("result", "unknown"),
            "played_at": datetime.utcnow().isoformat(),
        },
    )
    game_id = result[0]["id"] if isinstance(result, list) else result["id"]
    logger.info(f"Inserted game: {game_id}")
    return game_id


async def insert_player(db: Surreal, player_data: dict) -> str:
    """Insert a player document record."""
    result = await db.create(
        "player",
        {
            "player_id": player_data["player_id"],
            "name": player_data["name"],
            "race": player_data.get("race", "Zerg"),
            "mmr": player_data.get("mmr", 1000),
        },
    )
    player_id = result[0]["id"] if isinstance(result, list) else result["id"]
    logger.info(f"Inserted player: {player_id}")
    return player_id


async def relate_player_game(
    db: Surreal, player_id: str, game_id: str, apm: int, units: list
):
    """Create a graph relation between player and game."""
    await db.query(
        f"RELATE {player_id}->unit_graph->{game_id} SET apm = {apm}, units_made = {units};"
    )
    logger.info(f"Related {player_id} -> {game_id}")


async def query_player_games(db: Surreal, player_name: str) -> list:
    """Graph query: SELECT games played by a player via relation."""
    result = await db.query(
        "SELECT ->unit_graph->game.* AS games FROM player WHERE name = $name;",
        {"name": player_name},
    )
    games = result[0]["result"] if result else []
    return games


async def query_top_players(db: Surreal, limit: int = 10) -> list:
    """Query top players by MMR."""
    result = await db.query(
        f"SELECT name, race, mmr FROM player ORDER BY mmr DESC LIMIT {limit};"
    )
    return result[0]["result"] if result else []


async def main():
    logging.basicConfig(level=logging.INFO)
    db = await connect()
    await setup_schema(db)

    game_id = await insert_game(
        db, {"game_id": "g001", "map": "Solaris", "duration": 420, "result": "win"}
    )
    player_id = await insert_player(
        db, {"player_id": "p001", "name": "ZergBot", "race": "Zerg", "mmr": 4200}
    )
    await relate_player_game(
        db, player_id, game_id, apm=180, units=["Zergling", "Roach", "Mutalisk"]
    )

    games = await query_player_games(db, "ZergBot")
    print("Player games:", games)
    top = await query_top_players(db)
    print("Top players:", top)
    await db.close()


if __name__ == "__main__":
    asyncio.run(main())
