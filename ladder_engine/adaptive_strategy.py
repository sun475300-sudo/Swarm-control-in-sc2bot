"""
Phase 370: Adaptive Strategy
Opponent-history-aware strategy selection with Bayesian model updates
and counter-strategy logic for common SC2 archetypes.
"""

from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple
import math


# ------------------------------------------------------------------
# Known strategy archetypes the bot must counter
# ------------------------------------------------------------------

STRATEGY_ARCHETYPES = [
    "bio_terran",  # marine/marauder/medivac
    "mech_terran",  # tank/hellion/viking
    "sky_terran",  # battlecruiser/banshee
    "gateway_protoss",  # zealot/stalker/immortal
    "skytoss",  # carrier/void ray
    "colossus_protoss",  # colossus/gateway
    "zergling_bane",  # zerg mirror ling/bane
    "roach_ravager",  # zerg roach pressure
    "hydra_ling_bane",  # zerg hydra army
    "nydus_all_in",  # nydus drop all-in
    "unknown",
]

# Counter recommendations: {archetype: [zerg_counter_composition]}
COUNTER_TABLE: Dict[str, List[str]] = {
    "bio_terran": ["roach_ravager", "bane_ling", "hydralisk"],
    "mech_terran": ["ultralisk", "bane_infestor", "swarm_host"],
    "sky_terran": ["corruptor_hydra", "queen_spore"],
    "gateway_protoss": ["roach_ravager", "bane_ling"],
    "skytoss": ["corruptor_hydra", "queen_net"],
    "colossus_protoss": ["corruptor_ravager", "hydra_ling"],
    "zergling_bane": ["roach", "spine_crawler"],
    "roach_ravager": ["hydra_ling_bane", "roach_ravager"],
    "hydra_ling_bane": ["roach_ravager", "infestor"],
    "nydus_all_in": ["spine_crawler_wall", "queen_pull"],
    "unknown": ["hatch_first_macro"],
}


@dataclass
class OpponentProfile:
    """Tracks an opponent's strategy tendencies across multiple games."""

    opponent_id: str
    race: str = "Unknown"
    games_played: int = 0
    wins_vs: int = 0
    # Prior probability of each strategy archetype
    strategy_priors: Dict[str, float] = field(default_factory=dict)
    # Observed features per game (list of feature dicts)
    game_history: List[Dict] = field(default_factory=list)

    def __post_init__(self):
        if not self.strategy_priors:
            n = len(STRATEGY_ARCHETYPES)
            self.strategy_priors = {s: 1.0 / n for s in STRATEGY_ARCHETYPES}

    @property
    def win_rate(self) -> float:
        return self.wins_vs / max(self.games_played, 1)

    def top_strategy(self) -> str:
        return max(self.strategy_priors, key=self.strategy_priors.get)

    def bayesian_update(self, observed_strategy: str, game_won: bool):
        """
        Update strategy prior using Bayes' rule.
        Likelihood function: P(evidence | strategy) = 0.8 if match, 0.2 otherwise.
        """
        LIKELIHOOD_MATCH = 0.8
        LIKELIHOOD_NO_MATCH = 0.2

        posteriors: Dict[str, float] = {}
        for strategy, prior in self.strategy_priors.items():
            if strategy == observed_strategy:
                likelihood = LIKELIHOOD_MATCH
            else:
                likelihood = LIKELIHOOD_NO_MATCH
            posteriors[strategy] = prior * likelihood

        # Normalize
        total = sum(posteriors.values())
        if total > 0:
            self.strategy_priors = {k: v / total for k, v in posteriors.items()}

        # Update game record
        self.games_played += 1
        if game_won:
            self.wins_vs += 1
        self.game_history.append({"strategy": observed_strategy, "won": game_won})

    def record_in_game_observation(self, observation: Dict):
        """Add an in-game scouting observation for mid-game Bayesian update."""
        units = observation.get("enemy_units", {})
        # Lightweight in-game update
        detected = _classify_from_units(units, self.race)
        if detected != "unknown":
            self.bayesian_update(detected, game_won=False)  # partial update


def _classify_from_units(units: Dict[str, int], race: str) -> str:
    """Heuristically classify strategy from observed unit counts."""
    if race == "Terran":
        bio = units.get("Marine", 0) + units.get("Marauder", 0)
        mech = units.get("SiegeTank", 0) + units.get("Hellion", 0)
        air = units.get("BattleCruiser", 0) + units.get("Banshee", 0)
        if bio > mech and bio > air:
            return "bio_terran"
        if mech >= bio:
            return "mech_terran"
        if air > 0:
            return "sky_terran"
    elif race == "Protoss":
        colossus = units.get("Colossus", 0)
        carriers = units.get("Carrier", 0) + units.get("VoidRay", 0)
        if carriers > 0:
            return "skytoss"
        if colossus > 0:
            return "colossus_protoss"
        return "gateway_protoss"
    elif race == "Zerg":
        banes = units.get("Baneling", 0)
        roaches = units.get("Roach", 0)
        hydras = units.get("Hydralisk", 0)
        if banes > 0 and hydras > 0:
            return "hydra_ling_bane"
        if roaches > 0:
            return "roach_ravager"
        return "zergling_bane"
    return "unknown"


class AdaptiveStrategySelector:
    """Selects optimal counter-strategy for the current opponent."""

    def __init__(self):
        self._profiles: Dict[str, OpponentProfile] = {}

    def get_or_create_profile(
        self, opponent_id: str, race: str = "Unknown"
    ) -> OpponentProfile:
        if opponent_id not in self._profiles:
            self._profiles[opponent_id] = OpponentProfile(
                opponent_id=opponent_id, race=race
            )
        return self._profiles[opponent_id]

    def select_counter_strategy(
        self,
        opponent_id: str,
        race: str,
        in_game_units: Optional[Dict[str, int]] = None,
    ) -> Tuple[str, List[str]]:
        """
        Return (predicted_archetype, [counter_compositions]) for the opponent.
        Uses Bayesian profile if available; falls back to defaults.
        """
        profile = self.get_or_create_profile(opponent_id, race)

        # If we have in-game observations, update the model
        if in_game_units:
            detected = _classify_from_units(in_game_units, race)
            if detected != "unknown":
                profile.bayesian_update(detected, game_won=False)

        predicted = profile.top_strategy()
        counters = COUNTER_TABLE.get(predicted, COUNTER_TABLE["unknown"])
        return (predicted, counters)

    def record_game_result(
        self,
        opponent_id: str,
        race: str,
        observed_strategy: str,
        won: bool,
    ):
        """Update opponent profile after a completed game."""
        profile = self.get_or_create_profile(opponent_id, race)
        profile.bayesian_update(observed_strategy, won)

    def opponent_win_rate(self, opponent_id: str) -> float:
        profile = self._profiles.get(opponent_id)
        return profile.win_rate if profile else 0.0

    def get_meta_strategy(self, race: str) -> Tuple[str, List[str]]:
        """
        Return the overall most-common strategy for a race (population-level).
        Used when opponent has no history.
        """
        meta = {
            "Terran": ("bio_terran", COUNTER_TABLE["bio_terran"]),
            "Protoss": ("gateway_protoss", COUNTER_TABLE["gateway_protoss"]),
            "Zerg": ("zergling_bane", COUNTER_TABLE["zergling_bane"]),
        }
        return meta.get(race, ("unknown", COUNTER_TABLE["unknown"]))

    def probability_report(self, opponent_id: str) -> Dict[str, float]:
        """Return strategy probability distribution for an opponent."""
        profile = self._profiles.get(opponent_id)
        if not profile:
            return {}
        return {
            k: round(v, 4)
            for k, v in sorted(
                profile.strategy_priors.items(), key=lambda x: x[1], reverse=True
            )
        }
