"""
Strategy Manager - High-level strategy decision making based on IntelFacts.
"""

from dataclasses import dataclass
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from .intel_manager import IntelManager, IntelFacts


@dataclass
class StrategyDecision:
    """Strategy decision output."""
    
    mode: str  # "eco", "army", "defend", "all_in", "expand"
    tech_focus: str  # "ground", "anti_air", "mixed"
    priority: str  # "economy", "production", "defense", "offense"


class StrategyManager:
    """
    High-level strategy based on IntelFacts.
    
    This class makes strategic decisions based on the collected intelligence,
    implementing a rule-based strategy system that can later be enhanced
    with machine learning.
    """

    def __init__(self, intel: "IntelManager") -> None:
        """
        Initialize StrategyManager.
        
        Args:
            intel: IntelManager instance to get facts from
        """
        self.intel = intel

    @property
    def facts(self) -> "IntelFacts":
        """Get current intelligence facts."""
        return self.intel.facts

    def decide(self) -> StrategyDecision:
        """
        Make strategic decision based on current intelligence.
        
        Returns:
            StrategyDecision with mode, tech_focus, and priority
        """
        f = self.facts

        # Priority 1: Defense against rush
        if f.enemy_rush:
            return StrategyDecision(
                mode="defend",
                tech_focus="ground",
                priority="defense"
            )

        # Priority 2: Anti-air if enemy has air units
        if f.enemy_air and f.our_army_size < 20:
            return StrategyDecision(
                mode="army",
                tech_focus="anti_air",
                priority="defense"
            )

        # Priority 3: Economy if resources are low
        if f.our_minerals < 100 and f.our_base_count < 2:
            return StrategyDecision(
                mode="eco",
                tech_focus="ground",
                priority="economy"
            )

        # Priority 4: Expand if economy is good
        if f.our_minerals >= 300 and f.our_base_count < 3 and f.our_supply_used < f.our_supply_cap * 0.7:
            return StrategyDecision(
                mode="expand",
                tech_focus="ground",
                priority="economy"
            )

        # Priority 5: Build army if resources are abundant
        if f.our_minerals >= 300 and f.our_supply_used < f.our_supply_cap * 0.9:
            return StrategyDecision(
                mode="army",
                tech_focus="mixed",
                priority="production"
            )

        # Priority 6: All-in if we have overwhelming advantage
        if f.our_army_size > 50 and f.our_supply_used >= f.our_supply_cap * 0.9:
            return StrategyDecision(
                mode="all_in",
                tech_focus="mixed",
                priority="offense"
            )

        # Default: Economy focus
        return StrategyDecision(
            mode="eco",
            tech_focus="ground",
            priority="economy"
        )
