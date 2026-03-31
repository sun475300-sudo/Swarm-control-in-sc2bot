"""
Phase 372: Ladder Tracker
Tracks ladder progress, per-race win rates, map performance, streaks, and
rank history. Exports to JSON and generates trend analysis.
"""

from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple
import json
import time
import os


@dataclass
class MatchResult:
    match_id: str
    timestamp: float
    opponent_race: str
    map_name: str
    won: bool
    game_duration_s: float
    our_mmr_before: int
    our_mmr_after: int
    notes: str = ""

    @property
    def mmr_delta(self) -> int:
        return self.our_mmr_after - self.our_mmr_before

    def to_dict(self) -> Dict:
        return {
            "match_id": self.match_id,
            "timestamp": self.timestamp,
            "opponent_race": self.opponent_race,
            "map_name": self.map_name,
            "won": self.won,
            "duration_s": round(self.game_duration_s, 1),
            "mmr_before": self.our_mmr_before,
            "mmr_after": self.our_mmr_after,
            "mmr_delta": self.mmr_delta,
            "notes": self.notes,
        }


@dataclass
class PlayerStats:
    total_games: int = 0
    total_wins: int = 0
    current_mmr: int = 0
    peak_mmr: int = 0
    rank: str = "Unranked"
    current_streak: int = 0    # positive = win streak, negative = loss streak
    best_win_streak: int = 0

    @property
    def win_rate(self) -> float:
        return self.total_wins / max(self.total_games, 1)

    def to_dict(self) -> Dict:
        return {
            "total_games": self.total_games,
            "total_wins": self.total_wins,
            "win_rate": round(self.win_rate, 4),
            "current_mmr": self.current_mmr,
            "peak_mmr": self.peak_mmr,
            "rank": self.rank,
            "current_streak": self.current_streak,
            "best_win_streak": self.best_win_streak,
        }


# MMR → rank tier mapping
MMR_TIERS = [
    (6000, "Grandmaster"),
    (5400, "Master 1"),
    (4800, "Master 2"),
    (4200, "Master 3"),
    (3800, "Diamond 1"),
    (3400, "Diamond 2"),
    (3000, "Diamond 3"),
    (2600, "Platinum 1"),
    (2200, "Platinum 2"),
    (1800, "Gold 1"),
    (1400, "Gold 2"),
    (1000, "Silver 1"),
    (600,  "Bronze 1"),
    (0,    "Bronze 3"),
]


def mmr_to_rank(mmr: int) -> str:
    for threshold, rank in MMR_TIERS:
        if mmr >= threshold:
            return rank
    return "Bronze 3"


class LadderTracker:
    """Records and analyses ladder performance over time."""

    def __init__(self, save_path: Optional[str] = None):
        self.save_path = save_path
        self.stats = PlayerStats()
        self.match_history: List[MatchResult] = []
        self._mmr_history: List[Tuple[float, int]] = []  # (timestamp, mmr)

        if save_path and os.path.exists(save_path):
            self._load(save_path)

    # ------------------------------------------------------------------
    # Recording
    # ------------------------------------------------------------------

    def record_match(self, result: MatchResult):
        """Add a completed match and update all statistics."""
        self.match_history.append(result)
        s = self.stats

        s.total_games += 1
        if result.won:
            s.total_wins += 1
            s.current_streak = max(0, s.current_streak) + 1
            s.best_win_streak = max(s.best_win_streak, s.current_streak)
        else:
            s.current_streak = min(0, s.current_streak) - 1

        s.current_mmr = result.our_mmr_after
        s.peak_mmr = max(s.peak_mmr, result.our_mmr_after)
        s.rank = mmr_to_rank(s.current_mmr)

        self._mmr_history.append((result.timestamp, result.our_mmr_after))

        if self.save_path:
            self._save(self.save_path)

    # ------------------------------------------------------------------
    # Win-rate analysis
    # ------------------------------------------------------------------

    def win_rate_by_race(self) -> Dict[str, float]:
        """Return win rate broken down by opponent race."""
        counts: Dict[str, List[int]] = {}
        for m in self.match_history:
            r = m.opponent_race
            if r not in counts:
                counts[r] = [0, 0]
            counts[r][0] += 1
            if m.won:
                counts[r][1] += 1
        return {
            race: round(wins / total, 4)
            for race, (total, wins) in counts.items()
        }

    def win_rate_by_map(self) -> Dict[str, float]:
        """Return win rate broken down by map name."""
        counts: Dict[str, List[int]] = {}
        for m in self.match_history:
            mn = m.map_name
            if mn not in counts:
                counts[mn] = [0, 0]
            counts[mn][0] += 1
            if m.won:
                counts[mn][1] += 1
        return {
            map_name: round(wins / total, 4)
            for map_name, (total, wins) in counts.items()
        }

    def recent_form(self, n: int = 10) -> List[bool]:
        """Return win/loss for last n games."""
        return [m.won for m in self.match_history[-n:]]

    # ------------------------------------------------------------------
    # Trend analysis
    # ------------------------------------------------------------------

    def mmr_trend(self, window: int = 20) -> Dict:
        """Compute MMR trend over the last `window` games."""
        recent = self._mmr_history[-window:]
        if len(recent) < 2:
            return {"trend": "insufficient_data", "delta": 0, "games": len(recent)}
        start_mmr = recent[0][1]
        end_mmr = recent[-1][1]
        delta = end_mmr - start_mmr
        trend = "improving" if delta > 0 else ("declining" if delta < 0 else "stable")
        return {
            "trend": trend,
            "delta": delta,
            "start_mmr": start_mmr,
            "end_mmr": end_mmr,
            "games": len(recent),
        }

    def generate_full_report(self) -> Dict:
        """Return a comprehensive stats dictionary."""
        return {
            "player_stats": self.stats.to_dict(),
            "win_rate_by_race": self.win_rate_by_race(),
            "win_rate_by_map": self.win_rate_by_map(),
            "mmr_trend_20": self.mmr_trend(20),
            "recent_form_10": self.recent_form(10),
            "total_matches_recorded": len(self.match_history),
        }

    # ------------------------------------------------------------------
    # Persistence
    # ------------------------------------------------------------------

    def export_json(self, path: Optional[str] = None) -> str:
        target = path or self.save_path or "ladder_stats.json"
        data = {
            "stats": self.stats.to_dict(),
            "matches": [m.to_dict() for m in self.match_history],
            "mmr_history": self._mmr_history,
        }
        with open(target, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
        return target

    def _save(self, path: str):
        try:
            self.export_json(path)
        except Exception:
            pass

    def _load(self, path: str):
        try:
            with open(path, "r", encoding="utf-8") as f:
                data = json.load(f)
            s = data.get("stats", {})
            self.stats = PlayerStats(
                total_games=s.get("total_games", 0),
                total_wins=s.get("total_wins", 0),
                current_mmr=s.get("current_mmr", 0),
                peak_mmr=s.get("peak_mmr", 0),
                rank=s.get("rank", "Unranked"),
                current_streak=s.get("current_streak", 0),
                best_win_streak=s.get("best_win_streak", 0),
            )
            self._mmr_history = [tuple(x) for x in data.get("mmr_history", [])]
            for m in data.get("matches", []):
                self.match_history.append(MatchResult(
                    match_id=m["match_id"],
                    timestamp=m["timestamp"],
                    opponent_race=m["opponent_race"],
                    map_name=m["map_name"],
                    won=m["won"],
                    game_duration_s=m["duration_s"],
                    our_mmr_before=m["mmr_before"],
                    our_mmr_after=m["mmr_after"],
                    notes=m.get("notes", ""),
                ))
        except Exception:
            pass
