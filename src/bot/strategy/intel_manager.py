"""
Intel Manager - Collects and aggregates game facts from the environment.
"""

from dataclasses import dataclass, field


@dataclass
class IntelFacts:
    """Collected intelligence facts about the game state."""
    
    enemy_air: bool = False
    enemy_rush: bool = False
    enemy_ground: bool = False
    enemy_tech_level: int = 0
    our_minerals: int = 0
    our_gas: int = 0
    our_supply_used: int = 0
    our_supply_cap: int = 0
    our_army_size: int = 0
    our_base_count: int = 1
    enemy_base_count: int = 0
    game_time: float = 0.0
    last_enemy_sighting: float = 0.0


class IntelManager:
    """
    Collects and aggregates game facts from the environment.
    
    This class implements the Blackboard pattern - it serves as a central
    information store that all managers can access and update.
    """

    def __init__(self) -> None:
        """Initialize IntelManager with default facts."""
        self.facts = IntelFacts()

    def update_from_obs(self, obs: dict) -> None:
        """
        Update intelligence facts from observation.
        
        Args:
            obs: Observation dictionary containing game state
        """
        self.facts.our_minerals = obs.get("minerals", 0)
        self.facts.our_gas = obs.get("gas", 0)
        self.facts.our_supply_used = obs.get("food_used", 0)
        self.facts.our_supply_cap = obs.get("food_cap", 15)
        self.facts.our_army_size = obs.get("army_size", 0)
        self.facts.our_base_count = obs.get("base_count", 1)
        self.facts.game_time = obs.get("game_time", 0.0)
        
        # Enemy detection (simplified for mock environment)
        self.facts.enemy_air = obs.get("enemy_air", False)
        self.facts.enemy_rush = obs.get("enemy_rush", False)
        self.facts.enemy_ground = obs.get("enemy_ground", False)
        self.facts.enemy_tech_level = obs.get("enemy_tech_level", 0)
        self.facts.enemy_base_count = obs.get("enemy_base_count", 0)
        self.facts.last_enemy_sighting = obs.get("last_enemy_sighting", 0.0)

    def reset(self) -> None:
        """Reset all facts to default values."""
        self.facts = IntelFacts()
