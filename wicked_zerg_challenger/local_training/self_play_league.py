# -*- coding: utf-8 -*-
"""ELO-based self-play league for checkpoint opponents."""

from __future__ import annotations

import random
from dataclasses import asdict, dataclass
from typing import Dict, List, Optional


def update_elo(winner_elo: float, loser_elo: float, k: int = 32):
    expected = 1 / (1 + 10 ** ((loser_elo - winner_elo) / 400))
    return winner_elo + k * (1 - expected), loser_elo - k * (1 - expected)


@dataclass
class LeaguePlayer:
    player_id: str
    elo: float = 1000.0
    games: int = 0
    wins: int = 0
    model_path: str = ""


class SelfPlayLeague:
    """Maintain recent opponents and match by nearby ELO."""

    def __init__(self, max_players: int = 20, elo_window: float = 200.0):
        self.max_players = int(max_players)
        self.elo_window = float(elo_window)
        self.players: Dict[str, LeaguePlayer] = {}

    def add_player(
        self, player_id: str, elo: float = 1000.0, model_path: str = ""
    ) -> LeaguePlayer:
        player = LeaguePlayer(
            player_id=player_id, elo=float(elo), model_path=model_path
        )
        self.players[player_id] = player
        self._trim()
        return player

    def get_opponent(self, player_id: str, rng=None) -> Optional[str]:
        if player_id not in self.players:
            return None
        rng = rng or random
        player = self.players[player_id]
        candidates = [
            other
            for other in self.players.values()
            if other.player_id != player_id
            and abs(other.elo - player.elo) <= self.elo_window
        ]
        if not candidates:
            candidates = [
                other for other in self.players.values() if other.player_id != player_id
            ]
        if not candidates:
            return None
        return rng.choice(candidates).player_id

    def record_result(self, winner_id: str, loser_id: str, k: int = 32):
        winner = self.players[winner_id]
        loser = self.players[loser_id]
        winner.elo, loser.elo = update_elo(winner.elo, loser.elo, k=k)
        winner.games += 1
        winner.wins += 1
        loser.games += 1
        return winner.elo, loser.elo

    def as_dict(self) -> List[dict]:
        return [asdict(player) for player in self.players.values()]

    def _trim(self) -> None:
        while len(self.players) > self.max_players:
            oldest_key = next(iter(self.players))
            del self.players[oldest_key]
