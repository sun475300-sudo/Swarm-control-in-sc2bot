"""
Phase 446: PocketBase - SC2 Bot Backend as a Service
Lightweight BaaS using PocketBase REST API with real-time subscriptions.
"""

import asyncio
import logging
import httpx
import json
from dataclasses import dataclass, asdict
from typing import Optional, Callable
import websockets

logger = logging.getLogger(__name__)

PB_URL = "http://127.0.0.1:8090"


@dataclass
class GameRecord:
    game_id: str
    map_name: str
    result: str
    duration: int
    apm: int
    player_id: str


@dataclass
class PlayerRecord:
    player_id: str
    name: str
    race: str
    mmr: int


class SC2PocketBaseClient:
    def __init__(self, base_url: str = PB_URL):
        self.base_url = base_url
        self.token: Optional[str] = None
        self.client = httpx.AsyncClient(base_url=base_url)

    async def authenticate(self, email: str, password: str):
        """Authenticate admin and store token."""
        resp = await self.client.post(
            "/api/admins/auth-with-password",
            json={"identity": email, "password": password},
        )
        resp.raise_for_status()
        self.token = resp.json()["token"]
        self.client.headers["Authorization"] = f"Bearer {self.token}"
        logger.info("PocketBase admin authenticated.")

    def _headers(self) -> dict:
        return {"Authorization": f"Bearer {self.token}"} if self.token else {}

    async def create_game(self, game: GameRecord) -> dict:
        """Create a game record in the 'games' collection."""
        resp = await self.client.post(
            "/api/collections/games/records", json=asdict(game)
        )
        resp.raise_for_status()
        result = resp.json()
        logger.info(f"Game created: {result['id']}")
        return result

    async def list_games(
        self, page: int = 1, per_page: int = 20, filter_str: str = ""
    ) -> dict:
        """List games with optional filter."""
        params = {"page": page, "perPage": per_page}
        if filter_str:
            params["filter"] = filter_str
        resp = await self.client.get("/api/collections/games/records", params=params)
        resp.raise_for_status()
        return resp.json()

    async def create_player(self, player: PlayerRecord) -> dict:
        """Create a player record."""
        resp = await self.client.post(
            "/api/collections/players/records", json=asdict(player)
        )
        resp.raise_for_status()
        return resp.json()

    async def update_leaderboard(self, player_id: str, mmr: int, win_rate: float):
        """Upsert leaderboard entry for a player."""
        # Check if entry exists
        resp = await self.client.get(
            "/api/collections/leaderboard/records",
            params={"filter": f'player_id="{player_id}"'},
        )
        data = resp.json()
        entry = {"player_id": player_id, "mmr": mmr, "win_rate": win_rate}

        if data.get("totalItems", 0) > 0:
            record_id = data["items"][0]["id"]
            resp = await self.client.patch(
                f"/api/collections/leaderboard/records/{record_id}", json=entry
            )
        else:
            resp = await self.client.post(
                "/api/collections/leaderboard/records", json=entry
            )
        resp.raise_for_status()
        logger.info(f"Leaderboard updated for player {player_id}")
        return resp.json()

    async def subscribe_realtime(self, collection: str, callback: Callable):
        """Subscribe to real-time updates via SSE/WebSocket."""
        ws_url = self.base_url.replace("http", "ws") + f"/api/realtime"
        async with websockets.connect(ws_url) as ws:
            # Subscribe to collection
            await ws.send(
                json.dumps(
                    {
                        "clientId": "sc2bot",
                        "subscriptions": [f"{collection}/*"],
                    }
                )
            )
            logger.info(f"Subscribed to {collection} real-time events.")
            async for message in ws:
                event = json.loads(message)
                await callback(event)

    async def get_replay_upload_url(self, filename: str) -> str:
        """Get upload URL for a replay file."""
        resp = await self.client.post(
            "/api/collections/replays/records",
            data={"filename": filename, "status": "pending"},
        )
        resp.raise_for_status()
        record = resp.json()
        return f"{self.base_url}/api/files/replays/{record['id']}/{filename}"

    async def close(self):
        await self.client.aclose()


async def main():
    logging.basicConfig(level=logging.INFO)
    client = SC2PocketBaseClient()

    game = GameRecord("g001", "Solaris", "win", 420, 185, "p001")
    player = PlayerRecord("p001", "ZergBot", "Zerg", 4200)

    print("PocketBase SC2 client initialized.")
    print("Game data:", asdict(game))
    print("Player data:", asdict(player))
    # In production: await client.authenticate("admin@sc2.bot", "password")
    # await client.create_game(game)
    # await client.create_player(player)
    await client.close()


if __name__ == "__main__":
    asyncio.run(main())
