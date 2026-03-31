"""
GraphQL resolvers for SC2 Bot Statistics API.
Uses Strawberry (Python GraphQL library) with async resolvers.
"""

import asyncio
import uuid
from datetime import datetime, timezone
from typing import AsyncGenerator, Optional

import strawberry
from strawberry import ID
from strawberry.scalars import JSON


# ── Enums ─────────────────────────────────────────────────────────────────────

@strawberry.enum
class MatchResult:
    WIN = "WIN"
    LOSS = "LOSS"
    TIE = "TIE"


@strawberry.enum
class GamePhase:
    EARLY = "EARLY"
    MID = "MID"
    LATE = "LATE"


# ── Types ─────────────────────────────────────────────────────────────────────

@strawberry.type
class PlayerStats:
    player_id: ID
    username: str
    race: str
    wins: int
    losses: int
    win_rate: float
    avg_apm: int
    current_rating: int
    total_games: int
    created_at: datetime


@strawberry.type
class MatchRecord:
    match_id: ID
    player_id: ID
    opponent_id: ID
    result: str
    race: str
    map_name: str
    game_duration: int
    apm: int
    score: float
    played_at: datetime


@strawberry.type
class LeaderboardEntry:
    rank: int
    player_id: ID
    username: str
    race: str
    rating: int
    wins: int
    losses: int
    win_rate: float
    streak: int


@strawberry.type
class LiveStats:
    player_id: ID
    game_loop: int
    minerals: int
    vespene: int
    supply_used: int
    supply_cap: int
    army_value: float
    phase: str
    timestamp: datetime


@strawberry.type
class MutationResult:
    success: bool
    match_id: Optional[ID] = None
    message: str = ""


# ── In-memory data store (replace with DB in production) ─────────────────────

_players: dict[str, dict] = {
    "player_1": {
        "username": "ZergMaster",
        "race": "Zerg",
        "wins": 42,
        "losses": 18,
        "avg_apm": 180,
        "current_rating": 2100,
        "created_at": datetime(2024, 1, 1, tzinfo=timezone.utc),
    }
}
_matches: list[dict] = []


# ── Query resolvers ───────────────────────────────────────────────────────────

@strawberry.type
class Query:
    @strawberry.field
    async def player_stats(self, player_id: ID) -> Optional[PlayerStats]:
        p = _players.get(str(player_id))
        if not p:
            return None
        total = p["wins"] + p["losses"]
        return PlayerStats(
            player_id=player_id,
            username=p["username"],
            race=p["race"],
            wins=p["wins"],
            losses=p["losses"],
            win_rate=round(p["wins"] / total, 3) if total else 0.0,
            avg_apm=p["avg_apm"],
            current_rating=p["current_rating"],
            total_games=total,
            created_at=p["created_at"],
        )

    @strawberry.field
    async def match_history(
        self, player_id: ID, limit: int = 20, offset: int = 0
    ) -> list[MatchRecord]:
        filtered = [m for m in _matches if m["player_id"] == str(player_id)]
        return [
            MatchRecord(**m) for m in filtered[offset : offset + limit]
        ]

    @strawberry.field
    async def leaderboard(self, limit: int = 10) -> list[LeaderboardEntry]:
        sorted_players = sorted(
            _players.items(),
            key=lambda x: x[1]["current_rating"],
            reverse=True,
        )
        return [
            LeaderboardEntry(
                rank=i + 1,
                player_id=pid,
                username=p["username"],
                race=p["race"],
                rating=p["current_rating"],
                wins=p["wins"],
                losses=p["losses"],
                win_rate=round(p["wins"] / max(1, p["wins"] + p["losses"]), 3),
                streak=3,
            )
            for i, (pid, p) in enumerate(sorted_players[:limit])
        ]


# ── Mutation resolvers ────────────────────────────────────────────────────────

@strawberry.type
class Mutation:
    @strawberry.mutation
    async def record_match(
        self,
        player_id: ID,
        opponent_id: ID,
        result: str,
        race: str,
        map_name: str,
        game_duration: int,
        apm: int,
        score: float,
    ) -> MutationResult:
        match_id = str(uuid.uuid4())
        _matches.append({
            "match_id": match_id,
            "player_id": str(player_id),
            "opponent_id": str(opponent_id),
            "result": result,
            "race": race,
            "map_name": map_name,
            "game_duration": game_duration,
            "apm": apm,
            "score": score,
            "played_at": datetime.now(timezone.utc),
        })
        return MutationResult(success=True, match_id=match_id, message="Match recorded")

    @strawberry.mutation
    async def update_profile(
        self, player_id: ID, username: Optional[str] = None
    ) -> MutationResult:
        pid = str(player_id)
        if pid not in _players:
            return MutationResult(success=False, message="Player not found")
        if username:
            _players[pid]["username"] = username
        return MutationResult(success=True, message="Profile updated")


# ── Subscription resolvers ────────────────────────────────────────────────────

@strawberry.type
class Subscription:
    @strawberry.subscription
    async def live_stats(self, player_id: ID) -> AsyncGenerator[LiveStats, None]:
        for tick in range(50):
            yield LiveStats(
                player_id=player_id,
                game_loop=tick * 22,
                minerals=50 + tick * 8,
                vespene=max(0, tick * 3 - 60),
                supply_used=min(200, 12 + tick // 4),
                supply_cap=min(200, 14 + (tick // 8) * 8),
                army_value=float(tick * 40),
                phase="early" if tick < 20 else ("mid" if tick < 40 else "late"),
                timestamp=datetime.now(timezone.utc),
            )
            await asyncio.sleep(1.0)


schema = strawberry.Schema(query=Query, mutation=Mutation, subscription=Subscription)
