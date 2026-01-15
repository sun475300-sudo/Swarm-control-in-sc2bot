"""
Mock SC2 Environment for testing without actual StarCraft II installation.
This module provides a lightweight simulation environment for testing bot logic.
"""

from dataclasses import dataclass, field
from typing import Dict, Any, List, Tuple


@dataclass
class MockState:
    """Mock game state representation."""
    
    minerals: int = 50
    gas: int = 0
    food_used: int = 12
    food_cap: int = 22
    step: int = 0
    game_time: float = 0.0
    base_count: int = 1
    army_size: int = 0
    enemy_air: bool = False
    enemy_rush: bool = False
    enemy_ground: bool = False
    enemy_tech_level: int = 0
    enemy_base_count: int = 0
    last_enemy_sighting: float = 0.0
    structures: List[str] = field(default_factory=list)
    units: List[str] = field(default_factory=list)


class MockSC2Env:
    """
    StarCraft II 없이, Swarm 제어 느낌만 테스트할 수 있는 간단 환경.
    
    This mock environment simulates basic SC2 game mechanics without
    requiring an actual StarCraft II installation. It allows testing
    of bot logic in isolation.
    """

    def __init__(self, initial_minerals: int = 50, initial_gas: int = 0) -> None:
        """
        Initialize mock SC2 environment.
        
        Args:
            initial_minerals: Starting mineral count
            initial_gas: Starting gas count
        """
        self.state = MockState(minerals=initial_minerals, gas=initial_gas)
        self.mineral_rate = 10  # Minerals per step
        self.gas_rate = 2  # Gas per step

    def reset(self) -> Dict[str, Any]:
        """
        Reset environment to initial state.
        
        Returns:
            Dictionary containing initial game state
        """
        self.state = MockState(minerals=50, gas=0)
        return self._to_obs()

    def step(self, action: str) -> Dict[str, Any]:
        """
        Execute an action and update game state.
        
        Args:
            action: Action to execute (e.g., "train_drone", "train_zergling")
            
        Returns:
            Updated game state dictionary
        """
        self.state.step += 1
        self.state.game_time += 0.045  # ~22 FPS

        # Process action
        self._process_action(action)

        # Natural resource generation
        self.state.minerals += self.mineral_rate * self.state.base_count
        self.state.gas += self.gas_rate * min(self.state.base_count, 2)

        # Simulate enemy detection (random for testing)
        if self.state.step % 50 == 0:
            self.state.enemy_air = self.state.step % 100 < 50
            self.state.enemy_rush = self.state.step < 200

        return self._to_obs()

    def _process_action(self, action: str) -> None:
        """Process action and update state."""
        if action == "train_drone":
            if self.state.minerals >= 50 and self.state.food_used < self.state.food_cap:
                self.state.minerals -= 50
                self.state.food_used += 1
                self.state.units.append("drone")

        elif action == "train_zergling":
            if self.state.minerals >= 50 and self.state.food_used < self.state.food_cap - 1:
                self.state.minerals -= 50
                self.state.food_used += 2
                self.state.army_size += 2
                self.state.units.extend(["zergling", "zergling"])

        elif action == "train_roach":
            if self.state.minerals >= 75 and self.state.gas >= 25 and self.state.food_used < self.state.food_cap - 2:
                self.state.minerals -= 75
                self.state.gas -= 25
                self.state.food_used += 2
                self.state.army_size += 1
                self.state.units.append("roach")

        elif action == "train_queen":
            if self.state.minerals >= 150 and self.state.gas >= 100 and self.state.food_used < self.state.food_cap - 2:
                self.state.minerals -= 150
                self.state.gas -= 100
                self.state.food_used += 2
                self.state.army_size += 1
                self.state.units.append("queen")

        elif action == "build_spine":
            if self.state.minerals >= 100:
                self.state.minerals -= 100
                self.state.structures.append("spine_crawler")

        elif action == "expand":
            if self.state.minerals >= 300:
                self.state.minerals -= 300
                self.state.base_count += 1
                self.state.food_cap += 8

        elif action == "attack_move":
            # Simulate attack - no state change, just recorded
            pass

        # Action "wait" does nothing

    def _to_obs(self) -> Dict[str, Any]:
        """Convert game state to observation dictionary."""
        return {
            "minerals": self.state.minerals,
            "gas": self.state.gas,
            "food_used": self.state.food_used,
            "food_cap": self.state.food_cap,
            "step": self.state.step,
            "game_time": self.state.game_time,
            "base_count": self.state.base_count,
            "army_size": self.state.army_size,
            "enemy_air": self.state.enemy_air,
            "enemy_rush": self.state.enemy_rush,
            "enemy_ground": self.state.enemy_ground,
            "enemy_tech_level": self.state.enemy_tech_level,
            "enemy_base_count": self.state.enemy_base_count,
            "last_enemy_sighting": self.state.last_enemy_sighting,
        }
