# -*- coding: utf-8 -*-
"""Game result analytics and training summary helpers."""

import json
import logging
import uuid
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Dict, List, Optional

logger = logging.getLogger("GameAnalyticsSystem")


class DefeatReason(Enum):
    """Canonical defeat reason labels used by training analytics."""

    EARLY_RUSH = "early_rush"
    ECONOMY_COLLAPSE = "economy_collapse"
    ARMY_WIPEOUT = "army_wipeout"
    TECH_DISADVANTAGE = "tech_disadvantage"
    EXPANSION_FAILURE = "expansion_failure"
    HARASSMENT = "harassment"
    RESOURCE_DENIAL = "resource_denial"
    TIMEOUT = "timeout"
    UNKNOWN = "unknown"


class GameAnalytics:
    """Collects per-game results and lightweight matchup statistics."""

    def __init__(self):
        self.games: List[Dict] = []
        self.total_games = 0
        self.total_wins = 0
        self.race_stats: Dict[str, Dict] = {
            "Terran": {"games": 0, "wins": 0, "avg_time": 0.0},
            "Protoss": {"games": 0, "wins": 0, "avg_time": 0.0},
            "Zerg": {"games": 0, "wins": 0, "avg_time": 0.0},
        }
        self.map_stats: Dict[str, Dict] = {}
        self.defeat_reasons: Dict[str, int] = {
            reason.value: 0 for reason in DefeatReason
        }
        self.timing_stats = {
            "avg_game_time": 0.0,
            "shortest_game": float("inf"),
            "longest_game": 0.0,
            "avg_first_expand": 0.0,
            "avg_pool_timing": 0.0,
        }
        self.save_path = Path("local_training/game_analytics.json")
        self.detailed_log_path = Path("local_training/detailed_game_log.jsonl")
        self._load_stats()

    def record_game(
        self,
        game_id: int,
        map_name: str,
        opponent_race: str,
        difficulty: str,
        result: str,
        game_time: float,
        defeat_reason: Optional[DefeatReason] = None,
        additional_stats: Optional[Dict] = None,
    ) -> None:
        """Record one game result and update aggregate statistics."""
        stats = additional_stats or {}
        won = "VICTORY" in result.upper() or "WIN" in result.upper()
        if not won and defeat_reason is None:
            defeat_reason = self._analyze_defeat_reason(game_time, stats)

        unique_game_id = f"{uuid.uuid4().hex[:8]}_{self.total_games + 1}"
        game_record = {
            "game_id": unique_game_id,
            "source_game_id": game_id,
            "timestamp": datetime.now().isoformat(),
            "map": map_name,
            "opponent_race": opponent_race,
            "difficulty": difficulty,
            "result": result,
            "won": won,
            "game_time": game_time,
            "defeat_reason": defeat_reason.value if defeat_reason else None,
            "additional_stats": stats,
        }

        self.games.append(game_record)
        self.total_games += 1
        if won:
            self.total_wins += 1

        self._update_race_stats(opponent_race, won, game_time)
        self._update_map_stats(map_name, won, game_time)
        if not won and defeat_reason:
            self.defeat_reasons.setdefault(defeat_reason.value, 0)
            self.defeat_reasons[defeat_reason.value] += 1

        self._update_timing_stats(game_time, stats)
        self._save_detailed_log(game_record)
        if self.total_games % 10 == 0:
            self._save_stats()
        if not won:
            logger.info(self._get_defeat_analysis(game_record))

    def _update_race_stats(
        self, opponent_race: str, won: bool, game_time: float
    ) -> None:
        if opponent_race not in self.race_stats:
            self.race_stats[opponent_race] = {"games": 0, "wins": 0, "avg_time": 0.0}
        race = self.race_stats[opponent_race]
        race["games"] += 1
        if won:
            race["wins"] += 1
        race["avg_time"] = (race["avg_time"] * (race["games"] - 1) + game_time) / race[
            "games"
        ]

    def _update_map_stats(self, map_name: str, won: bool, game_time: float) -> None:
        if map_name not in self.map_stats:
            self.map_stats[map_name] = {"games": 0, "wins": 0, "avg_time": 0.0}
        map_stat = self.map_stats[map_name]
        map_stat["games"] += 1
        if won:
            map_stat["wins"] += 1
        map_stat["avg_time"] = (
            map_stat["avg_time"] * (map_stat["games"] - 1) + game_time
        ) / map_stat["games"]

    def _analyze_defeat_reason(self, game_time: float, stats: Dict) -> DefeatReason:
        worker_count = stats.get("worker_count", 0)
        army_count = stats.get("army_count", 0)
        base_count = stats.get("base_count", 1)

        if game_time < 180:
            return DefeatReason.EARLY_RUSH
        if worker_count < 16 and game_time < 300:
            return DefeatReason.ECONOMY_COLLAPSE
        if army_count < 5:
            return DefeatReason.ARMY_WIPEOUT
        if base_count == 1 and game_time > 300:
            return DefeatReason.EXPANSION_FAILURE
        if game_time > 1200:
            return DefeatReason.TIMEOUT
        return DefeatReason.UNKNOWN

    def _update_timing_stats(self, game_time: float, stats: Dict) -> None:
        self.timing_stats["avg_game_time"] = (
            self.timing_stats["avg_game_time"] * (self.total_games - 1) + game_time
        ) / self.total_games
        self.timing_stats["shortest_game"] = min(
            self.timing_stats["shortest_game"], game_time
        )
        self.timing_stats["longest_game"] = max(
            self.timing_stats["longest_game"], game_time
        )

        pool_timing = stats.get("pool_timing", 0)
        if pool_timing > 0:
            current = self.timing_stats["avg_pool_timing"]
            self.timing_stats["avg_pool_timing"] = (
                pool_timing if current == 0.0 else current * 0.9 + pool_timing * 0.1
            )

        expand_timing = stats.get("first_expand_timing", 0)
        if expand_timing > 0:
            current = self.timing_stats["avg_first_expand"]
            self.timing_stats["avg_first_expand"] = (
                expand_timing if current == 0.0 else current * 0.9 + expand_timing * 0.1
            )

    def _get_defeat_analysis(self, game_record: Dict) -> str:
        lines = [
            "",
            "=" * 60,
            f"[GAME ANALYTICS] Defeat analysis - Game #{game_record['game_id']}",
            "=" * 60,
            f"Map: {game_record['map']}",
            f"Opponent: {game_record['opponent_race']} ({game_record['difficulty']})",
            f"Game time: {int(game_record['game_time'])}s",
            f"Defeat reason: {game_record['defeat_reason']}",
        ]
        suggestions = self._get_improvement_suggestions(game_record)
        if suggestions:
            lines.append("")
            lines.append("Suggestions:")
            lines.extend(f"  - {suggestion}" for suggestion in suggestions)
        lines.extend([("=" * 60), ""])
        return "\n".join(lines)

    def _get_improvement_suggestions(self, game_record: Dict) -> List[str]:
        defeat_reason = game_record.get("defeat_reason")
        game_time = game_record.get("game_time", 0)
        suggestions: List[str] = []

        if defeat_reason == DefeatReason.EARLY_RUSH.value:
            suggestions.extend(
                [
                    "Tighten early defense and queen/zergling response.",
                    "Scout earlier to identify rush builds.",
                ]
            )
        elif defeat_reason == DefeatReason.ECONOMY_COLLAPSE.value:
            suggestions.extend(
                [
                    "Increase drone priority before the first army cutoff.",
                    "Check expansion timing and mineral spending.",
                ]
            )
        elif defeat_reason == DefeatReason.ARMY_WIPEOUT.value:
            suggestions.extend(
                [
                    "Convert economy into army earlier.",
                    "Avoid taking fights before the attack threshold is met.",
                ]
            )
        elif defeat_reason == DefeatReason.EXPANSION_FAILURE.value:
            suggestions.extend(
                [
                    "Improve second and third base timing.",
                    "Add defense around exposed expansions.",
                ]
            )
        elif game_time < 120:
            suggestions.append("Check survival build order and opening defense.")

        return suggestions

    def get_summary(self) -> str:
        win_rate = (
            (self.total_wins / self.total_games * 100) if self.total_games > 0 else 0.0
        )
        avg_game_time = int(self.timing_stats.get("avg_game_time", 0))
        lines = [
            "",
            "=" * 60,
            "[GAME ANALYTICS] Summary",
            "=" * 60,
            f"Overall win rate: {self.total_wins}/{self.total_games} ({win_rate:.1f}%)",
            f"Average game time: {avg_game_time}s",
            "",
            "Win rate by race:",
        ]

        for race, stats in self.race_stats.items():
            if stats["games"] > 0:
                race_wr = stats["wins"] / stats["games"] * 100
                lines.append(
                    f"  vs {race}: {stats['wins']}/{stats['games']} "
                    f"({race_wr:.1f}%) | avg {int(stats['avg_time'])}s"
                )

        lines.append("")
        lines.append("Win rate by map:")
        sorted_maps = sorted(
            self.map_stats.items(), key=lambda item: item[1]["games"], reverse=True
        )[:5]
        for map_name, stats in sorted_maps:
            if stats["games"] > 0:
                map_wr = stats["wins"] / stats["games"] * 100
                lines.append(
                    f"  {map_name}: {stats['wins']}/{stats['games']} ({map_wr:.1f}%)"
                )

        lines.append("")
        lines.append("Top defeat reasons:")
        sorted_reasons = sorted(
            self.defeat_reasons.items(), key=lambda item: item[1], reverse=True
        )[:3]
        for reason, count in sorted_reasons:
            if count > 0:
                lines.append(f"  {reason}: {count}")

        lines.extend([("=" * 60), ""])
        return "\n".join(lines)

    def get_race_specific_advice(self, opponent_race: str) -> str:
        if opponent_race not in self.race_stats:
            return ""
        stats = self.race_stats[opponent_race]
        if stats["games"] < 3:
            return f"\n[ADVICE] vs {opponent_race}: need at least 3 games of data."

        win_rate = stats["wins"] / stats["games"] * 100 if stats["games"] else 0.0
        lines = [f"\n[ADVICE] vs {opponent_race}:"]
        if win_rate < 20:
            lines.extend(
                [
                    f"  [CRITICAL] Win rate is very low ({win_rate:.1f}%).",
                    f"  - Review the opening and unit composition for {opponent_race}.",
                    f"  - Add matchup-specific counter checks for {opponent_race}.",
                ]
            )
        elif win_rate < 40:
            lines.extend(
                [
                    f"  [WARNING] Win rate is low ({win_rate:.1f}%).",
                    f"  - Improve counter composition and timing attacks.",
                ]
            )
        elif win_rate < 60:
            lines.append(
                f"  [OK] Win rate is mixed ({win_rate:.1f}%). Continue training."
            )
        else:
            lines.append(f"  [GOOD] Win rate is healthy ({win_rate:.1f}%).")
        return "\n".join(lines)

    def _save_stats(self) -> None:
        try:
            self.save_path.parent.mkdir(parents=True, exist_ok=True)
            data = {
                "total_games": self.total_games,
                "total_wins": self.total_wins,
                "race_stats": self.race_stats,
                "map_stats": self.map_stats,
                "defeat_reasons": self.defeat_reasons,
                "timing_stats": self.timing_stats,
                "recent_games": self.games[-50:],
            }
            with open(self.save_path, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
        except Exception as exc:
            logger.info(f"Failed to save analytics: {exc}")

    def _save_detailed_log(self, game_record: Dict) -> None:
        try:
            self.detailed_log_path.parent.mkdir(parents=True, exist_ok=True)
            with open(self.detailed_log_path, "a", encoding="utf-8") as f:
                f.write(json.dumps(game_record, ensure_ascii=False) + "\n")
        except Exception as exc:
            logger.info(f"Failed to save detailed game log: {exc}")

    def _load_stats(self) -> None:
        try:
            if not self.save_path.exists():
                return
            with open(self.save_path, "r", encoding="utf-8") as f:
                data = json.load(f)

            self.total_games = data.get("total_games", 0)
            self.total_wins = data.get("total_wins", 0)
            self.race_stats.update(data.get("race_stats", {}))
            self.map_stats = data.get("map_stats", {})

            loaded_reasons = data.get("defeat_reasons", {})
            self.defeat_reasons.update(loaded_reasons)

            loaded_timing = data.get("timing_stats", {})
            self.timing_stats.update(loaded_timing)
            self.games = data.get("recent_games", [])
            logger.info(f"Loaded analytics for {self.total_games} games")
        except Exception as exc:
            logger.info(f"Failed to load analytics; starting fresh: {exc}")
