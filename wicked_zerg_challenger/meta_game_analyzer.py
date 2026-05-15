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
        self.game_history: List[Dict] = []
        self.strategy_performance: Dict[str, Dict] = defaultdict(
            lambda: {"wins": 0, "losses": 0}
        )
        self.race_performance: Dict[str, Dict] = defaultdict(
            lambda: {"wins": 0, "losses": 0}
        )
        self.map_performance: Dict[str, Dict] = defaultdict(
            lambda: {"wins": 0, "losses": 0}
        )

    def record_game(self, result: Dict[str, Any]) -> None:
        """Record a game result for analysis"""
        self.game_history.append({**result, "timestamp": datetime.now().isoformat()})

        # 정규화된 승/패 카운트. result.get("win")이 None/False/0이면 패배.
        won = 1 if result.get("win") else 0
        lost = 1 - won

        strategy = result.get("strategy", "unknown")
        self.strategy_performance[strategy]["wins"] += won
        self.strategy_performance[strategy]["losses"] += lost

        # 이전 버전은 race_performance / map_performance의 losses를
        # 절대 증가시키지 않아 통계가 영구적으로 한쪽으로 치우치는 결함이
        # 있었음. 동일하게 won/lost로 기록한다.
        race = result.get("enemy_race", "unknown")
        self.race_performance[race]["wins"] += won
        self.race_performance[race]["losses"] += lost

        map_name = result.get("map", "unknown")
        self.map_performance[map_name]["wins"] += won
        self.map_performance[map_name]["losses"] += lost

    def get_current_meta_strategies(self) -> List[MetaStrategy]:
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

    def recommend_strategy(self, enemy_race: str, map_name: str) -> Dict[str, Any]:
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

    def get_counter_picks(self, enemy_strategy: str) -> List[str]:
        """Get counter picks for enemy strategy"""
        counters = {
            "rush": ["DEFENSIVE", "EXPAND"],
            "macro": ["AGGRESSIVE", "TIMING"],
            "timing": ["DEFENSIVE", "COUNTER"],
            "all_in": ["DEFENSIVE", "ECONOMY"],
            "tech": ["PRESSURE", "RUSH"],
        }
        return counters.get(enemy_strategy.lower(), ["MACRO"])

    def analyze_trends(self) -> Dict[str, Any]:
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
