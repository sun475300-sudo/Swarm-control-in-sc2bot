"""
Mock SC2 Environment for testing without actual StarCraft II installation.
This module provides a lightweight simulation environment for testing bot logic.
"""



class Race(Enum):
    """Mock race enum."""
    ZERG = "Zerg"
    TERRAN = "Terran"
    PROTOSS = "Protoss"


@dataclass
class MockUnit:
    """Mock unit representation."""
 unit_type: str
 position: tuple = (0, 0)
 health: float = 100.0
 max_health: float = 100.0
 energy: float = 0.0
 is_ready: bool = True


@dataclass
class MockGameState:
    """Mock game state for testing."""
 minerals: int = 50
 vespene: int = 0
 supply_used: int = 6
 supply_cap: int = 15
 workers: list = field(default_factory=list)
 structures: list = field(default_factory=list)
 army: list = field(default_factory=list)
 game_time: float = 0.0
 iteration: int = 0


class MockSC2Env:
    """
 Mock SC2 Environment for testing bot logic without SC2 runtime.
 
 This class simulates basic SC2 game state and allows testing
 of bot decision-making logic in isolation.
 
 Example:
 >>> env = MockSC2Env()
 >>> state = env.reset()
        >>> action = "train_drone"
 >>> new_state = env.step(action)
    """

 def __init__(self, initial_minerals: int = 50):
        """
 Initialize mock SC2 environment.
 
 Args:
 initial_minerals: Starting mineral count
        """
 self.state = MockGameState(minerals=initial_minerals)
 self.race = Race.ZERG
 
 def reset(self) -> Dict[str, Any]:
        """
 Reset environment to initial state.
 
 Returns:
 Dictionary containing game state
        """
 self.state = MockGameState(minerals=50)
 return self._state_to_dict()
 
 def step(self, action: str) -> Dict[str, Any]:
        """
 Execute an action and update game state.
 
 Args:
            action: Action to execute (e.g., "train_drone", "build_extractor")
 
 Returns:
 Updated game state dictionary
        """
        if action == "train_drone":
 if self.state.minerals >= 50 and self.state.supply_used < self.state.supply_cap:
 self.state.minerals -= 50
 self.state.supply_used += 1
                self.state.workers.append(MockUnit("drone"))
 
        elif action == "build_extractor":
 if self.state.minerals >= 25:
 self.state.minerals -= 25
                self.state.structures.append(MockUnit("extractor", is_ready=False))
 
        elif action == "train_zergling":
 if self.state.minerals >= 50 and self.state.supply_used + 1 <= self.state.supply_cap:
 self.state.minerals -= 50
 self.state.supply_used += 2
                self.state.army.append(MockUnit("zergling"))
 
 # Advance game time
 self.state.game_time += 0.045 # ~22 FPS
 self.state.iteration += 1
 
 return self._state_to_dict()
 
 def _state_to_dict(self) -> Dict[str, Any]:
        """Convert game state to dictionary."""
 return {
            "minerals": self.state.minerals,
            "vespene": self.state.vespene,
            "supply_used": self.state.supply_used,
            "supply_cap": self.state.supply_cap,
            "worker_count": len(self.state.workers),
            "structure_count": len(self.state.structures),
            "army_count": len(self.state.army),
            "game_time": self.state.game_time,
            "iteration": self.state.iteration,
 }
 
 def can_afford(self, cost_minerals: int, cost_vespene: int = 0) -> bool:
        """
 Check if we can afford a cost.
 
 Args:
 cost_minerals: Mineral cost
 cost_vespene: Vespene gas cost
 
 Returns:
 True if we can afford, False otherwise
        """
 return (
 self.state.minerals >= cost_minerals
 and self.state.vespene >= cost_vespene
 )
 
 def get_supply_left(self) -> int:
        """Get remaining supply capacity."""
 return max(0, self.state.supply_cap - self.state.supply_used)


class MockBotAI:
    """
 Mock BotAI interface for testing manager logic.
 
 This class provides a minimal interface that mimics sc2.bot_ai.BotAI
 for testing purposes without requiring actual SC2 installation.
    """
 
 def __init__(self):
        """Initialize mock bot."""
 self.env = MockSC2Env()
 self.iteration = 0
 self.time = 0.0
 
 @property
 def minerals(self) -> float:
        """Get current minerals."""
 return float(self.env.state.minerals)
 
 @property
 def vespene(self) -> float:
        """Get current vespene gas."""
 return float(self.env.state.vespene)
 
 @property
 def supply_used(self) -> int:
        """Get used supply."""
 return self.env.state.supply_used
 
 @property
 def supply_cap(self) -> int:
        """Get supply capacity."""
 return self.env.state.supply_cap
 
 @property
 def supply_left(self) -> int:
        """Get remaining supply."""
 return self.env.get_supply_left()
 
 def can_afford(self, unit_type: str) -> bool:
        """
 Check if we can afford a unit type.
 
 Args:
            unit_type: Unit type to check (e.g., "drone", "zergling")
 
 Returns:
 True if affordable, False otherwise
        """
 costs = {
            "drone": (50, 0),
            "zergling": (50, 0),
            "extractor": (25, 0),
 }
 
 if unit_type in costs:
 minerals, vespene = costs[unit_type]
 return self.env.can_afford(minerals, vespene)
 return False