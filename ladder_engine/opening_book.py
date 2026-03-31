"""
Phase 361: Opening Book
SC2 Zerg opening book with build order trees and matchup-based selection.
"""

from dataclasses import dataclass, field
from typing import List, Dict, Optional, Tuple
from enum import Enum


class Race(Enum):
    ZERG = "Zerg"
    TERRAN = "Terran"
    PROTOSS = "Protoss"
    RANDOM = "Random"


@dataclass
class BuildStep:
    supply: int
    action: str
    unit_or_building: str
    note: str = ""


@dataclass
class BuildOrder:
    name: str
    race_matchup: str
    steps: List[BuildStep] = field(default_factory=list)
    win_rate: float = 0.5
    sample_size: int = 0
    description: str = ""

    def add_step(self, supply: int, action: str, target: str, note: str = ""):
        self.steps.append(BuildStep(supply, action, target, note))

    def __repr__(self):
        return f"BuildOrder({self.name}, wr={self.win_rate:.1%}, n={self.sample_size})"


def _build_hatch_first() -> BuildOrder:
    bo = BuildOrder(
        name="hatch_first",
        race_matchup="ZvX",
        win_rate=0.52,
        sample_size=340,
        description="Greedy economic opening; expand before pool."
    )
    bo.add_step(17, "build", "Hatchery", "natural expansion")
    bo.add_step(17, "build", "Spawning Pool")
    bo.add_step(20, "build", "Overlord")
    bo.add_step(20, "morph", "Queen", "both hatches")
    bo.add_step(22, "build", "Extractor")
    return bo


def _build_pool_first() -> BuildOrder:
    bo = BuildOrder(
        name="pool_first",
        race_matchup="ZvT",
        win_rate=0.55,
        sample_size=210,
        description="Early pool for lings/queen pressure into expand."
    )
    bo.add_step(13, "build", "Spawning Pool")
    bo.add_step(13, "build", "Overlord")
    bo.add_step(16, "morph", "Queen")
    bo.add_step(16, "build", "Zergling", "x4 for map control")
    bo.add_step(19, "build", "Hatchery", "natural")
    return bo


def _build_12pool() -> BuildOrder:
    bo = BuildOrder(
        name="12pool",
        race_matchup="ZvP",
        win_rate=0.49,
        sample_size=175,
        description="12-pool speedling rush to punish greedy protoss openers."
    )
    bo.add_step(12, "build", "Spawning Pool")
    bo.add_step(13, "build", "Overlord")
    bo.add_step(14, "research", "Metabolic Boost")
    bo.add_step(14, "morph", "Zergling", "x6 attack wave")
    bo.add_step(17, "build", "Hatchery", "natural after aggression")
    return bo


def _build_overpool() -> BuildOrder:
    bo = BuildOrder(
        name="overpool",
        race_matchup="ZvZ",
        win_rate=0.51,
        sample_size=290,
        description="Overlord first then pool; standard safe ZvZ opener."
    )
    bo.add_step(13, "build", "Overlord")
    bo.add_step(14, "build", "Spawning Pool")
    bo.add_step(16, "morph", "Queen")
    bo.add_step(16, "build", "Zergling", "x2 scouting/defense")
    bo.add_step(18, "build", "Hatchery", "natural")
    return bo


def _build_gasless_expand() -> BuildOrder:
    bo = BuildOrder(
        name="gasless_expand",
        race_matchup="ZvT",
        win_rate=0.48,
        sample_size=130,
        description="Gasless double expand into roach/ravager transition."
    )
    bo.add_step(17, "build", "Hatchery", "natural")
    bo.add_step(17, "build", "Spawning Pool")
    bo.add_step(20, "morph", "Queen", "both hatches")
    bo.add_step(23, "build", "Hatchery", "third base")
    bo.add_step(28, "build", "Extractor", "x2 gas")
    bo.add_step(30, "build", "Roach Warren")
    return bo


class OpeningBook:
    """Zerg opening book with decision logic per matchup and map context."""

    # Win rate stats: {(opening_name, opponent_race): win_rate}
    WIN_RATE_TABLE: Dict[Tuple[str, str], float] = {
        ("hatch_first", "Terran"):  0.51,
        ("hatch_first", "Protoss"): 0.53,
        ("hatch_first", "Zerg"):    0.50,
        ("pool_first",  "Terran"):  0.55,
        ("pool_first",  "Protoss"): 0.47,
        ("pool_first",  "Zerg"):    0.50,
        ("12pool",      "Terran"):  0.44,
        ("12pool",      "Protoss"): 0.49,
        ("12pool",      "Zerg"):    0.46,
        ("overpool",    "Terran"):  0.50,
        ("overpool",    "Protoss"): 0.51,
        ("overpool",    "Zerg"):    0.51,
        ("gasless_expand", "Terran"):  0.48,
        ("gasless_expand", "Protoss"): 0.45,
        ("gasless_expand", "Zerg"):    0.43,
    }

    # Maps flagged as favoring aggressive openers
    AGGRESSIVE_MAPS = {"BerlingradAIE", "MoondanceAIE", "SiteDeltaAIE"}

    def __init__(self):
        self._openings: Dict[str, BuildOrder] = {
            "hatch_first":    _build_hatch_first(),
            "pool_first":     _build_pool_first(),
            "12pool":         _build_12pool(),
            "overpool":       _build_overpool(),
            "gasless_expand": _build_gasless_expand(),
        }

    def _opponent_race_str(self, opponent_race: Race) -> str:
        return opponent_race.value if isinstance(opponent_race, Race) else str(opponent_race)

    def select_opening(
        self,
        opponent_race: Race,
        map_name: str = "",
        game_history: Optional[List[Dict]] = None
    ) -> BuildOrder:
        """
        Select the best opening based on matchup, map, and recent game history.
        Returns a BuildOrder instance.
        """
        race_str = self._opponent_race_str(opponent_race)
        game_history = game_history or []

        # Determine candidate openings for matchup
        if race_str == "Zerg":
            candidates = ["overpool", "hatch_first"]
        elif race_str == "Terran":
            candidates = ["pool_first", "hatch_first", "gasless_expand"]
        elif race_str == "Protoss":
            candidates = ["hatch_first", "12pool", "pool_first"]
        else:
            candidates = ["hatch_first", "overpool"]

        # Bias toward aggression on certain maps
        if map_name in self.AGGRESSIVE_MAPS:
            if "pool_first" in candidates:
                candidates = ["pool_first"] + [c for c in candidates if c != "pool_first"]
            elif "12pool" in candidates:
                candidates = ["12pool"] + [c for c in candidates if c != "12pool"]

        # Penalise recently-lost openings using game_history
        losses: Dict[str, int] = {}
        for result in game_history[-10:]:
            if not result.get("win", True):
                opening_used = result.get("opening", "")
                losses[opening_used] = losses.get(opening_used, 0) + 1

        def score(name: str) -> float:
            base = self.WIN_RATE_TABLE.get((name, race_str), 0.50)
            penalty = losses.get(name, 0) * 0.03
            return base - penalty

        best = max(candidates, key=score)
        selected = self._openings[best]

        # Update win_rate from table for display accuracy
        selected.win_rate = self.WIN_RATE_TABLE.get((best, race_str), selected.win_rate)
        return selected

    def get_all_openings(self) -> List[BuildOrder]:
        return list(self._openings.values())
