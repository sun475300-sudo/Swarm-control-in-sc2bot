"""
Meta Game Analyzer - Analyzes current meta and adapts strategy
HIGH PRIORITY FEATURE
"""

from collections import defaultdict
from dataclasses import dataclass
from datetime import datetime
from typing import Any, Dict, List


@dataclass
class MetaStrategy:
    name: str
    win_rate: float
    popularity: float
    counter_strategy: str
    difficulty: str


class MetaGameAnalyzer:
    def __init__(self):
        self.game_history: list[dict] = []
        self.strategy_performance: dict[str, dict] = defaultdict(
            lambda: {"wins": 0, "losses": 0}
        )
        self.race_performance: dict[str, dict] = defaultdict(
            lambda: {"wins": 0, "losses": 0}
        )
        self.map_performance: dict[str, dict] = defaultdict(
            lambda: {"wins": 0, "losses": 0}
        )

    def record_game(self, result: dict[str, Any]) -> None:
        """Record a game result for analysis"""
        self.game_history.append({**result, "timestamp": datetime.now().isoformat()})

        strategy = result.get("strategy", "unknown")
        self.strategy_performance[strategy]["wins"] += result.get("win", 0)
        self.strategy_performance[strategy]["losses"] += 1 - result.get("win", 0)

        race = result.get("enemy_race", "unknown")
        self.race_performance[race]["wins"] += result.get("win", 0)

        map_name = result.get("map", "unknown")
        self.map_performance[map_name]["wins"] += result.get("win", 0)

    def get_current_meta_strategies(self) -> list[MetaStrategy]:
        """Get current meta strategies based on win rates"""
        meta_strategies = [
            MetaStrategy(
                name="Rush",
                win_rate=self._calculate_win_rate("rush"),
                popularity=0.25,
                counter_strategy="Defensive",
                difficulty="EASY",
            ),
            MetaStrategy(
                name="Macro",
                win_rate=self._calculate_win_rate("macro"),
                popularity=0.30,
                counter_strategy="Aggressive",
                difficulty="MEDIUM",
            ),
            MetaStrategy(
                name="Timing Attack",
                win_rate=self._calculate_win_rate("timing"),
                popularity=0.20,
                counter_strategy="Hold",
                difficulty="HARD",
            ),
            MetaStrategy(
                name="All-In",
                win_rate=self._calculate_win_rate("all_in"),
                popularity=0.15,
                counter_strategy="Contain",
                difficulty="EXTREME",
            ),
            MetaStrategy(
                name="Tech",
                win_rate=self._calculate_win_rate("tech"),
                popularity=0.10,
                counter_strategy="Pressure",
                difficulty="HARD",
            ),
        ]
        return sorted(meta_strategies, key=lambda x: x.win_rate, reverse=True)

    def _calculate_win_rate(self, strategy: str) -> float:
        """Calculate win rate for a strategy"""
        perf = self.strategy_performance.get(strategy, {"wins": 0, "losses": 0})
        total = perf["wins"] + perf["losses"]
        if total == 0:
            return 50.0
        return (perf["wins"] / total) * 100

    def recommend_strategy(self, enemy_race: str, map_name: str) -> dict[str, Any]:
        """Recommend best strategy based on current meta"""
        race_perf = self.race_performance.get(enemy_race, {"wins": 0})
        map_perf = self.map_performance.get(map_name, {"wins": 0})

        best_strategies = {
            ("terran", "small"): "RUSH",
            ("terran", "large"): "MACRO",
            ("zerg", "small"): "TIMING",
            ("zerg", "large"): "TECH",
            ("protoss", "small"): "ALL_IN",
            ("protoss", "large"): "MACRO",
        }

        map_size = "small" if map_name in ["GroundZero", "Corridor"] else "large"
        recommended = best_strategies.get((enemy_race.lower(), map_size), "MACRO")

        return {
            "recommended_strategy": recommended,
            "confidence": 0.75,
            "reasoning": f"Based on vs {enemy_race} on {map_name}",
            "alternatives": ["RUSH", "MACRO", "TIMING"],
            "meta_analysis": self.get_current_meta_strategies()[:3],
        }

    def get_counter_picks(self, enemy_strategy: str) -> list[str]:
        """Get counter picks for enemy strategy"""
        counters = {
            "rush": ["DEFENSIVE", "EXPAND"],
            "macro": ["AGGRESSIVE", "TIMING"],
            "timing": ["DEFENSIVE", "COUNTER"],
            "all_in": ["DEFENSIVE", "ECONOMY"],
            "tech": ["PRESSURE", "RUSH"],
        }
        return counters.get(enemy_strategy.lower(), ["MACRO"])

    def analyze_trends(self) -> dict[str, Any]:
        """Analyze recent trends"""
        recent_games = (
            self.game_history[-20:]
            if len(self.game_history) >= 20
            else self.game_history
        )

        if not recent_games:
            return {"trend": "NO_DATA", "recommendation": "Play more games"}

        recent_win_rate = sum(g.get("win", 0) for g in recent_games) / len(recent_games)

        trend = "IMPROVING" if recent_win_rate > 0.5 else "DECLINING"

        return {
            "trend": trend,
            "recent_win_rate": recent_win_rate * 100,
            "games_analyzed": len(recent_games),
            "recommendation": (
                "Keep current strategy"
                if trend == "IMPROVING"
                else "Try different approach"
            ),
        }


def create_meta_analyzer() -> MetaGameAnalyzer:
    """Factory function to create meta analyzer"""
    return MetaGameAnalyzer()
