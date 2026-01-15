"""
Abstract base class for all agents.
"""

from abc import ABC, abstractmethod
from typing import Dict, Any


class BaseAgent(ABC):
    """Abstract base class for all agents."""

    def reset(self) -> None:
        """Reset internal state between episodes."""
        pass

    @abstractmethod
    def on_step(self, obs: Dict[str, Any]) -> str:
        """
        Called every step with observation. Must return an action string.
        
        Args:
            obs: Observation dictionary containing game state
            
        Returns:
            Action string (e.g., "train_drone", "train_zergling", "wait")
        """
        raise NotImplementedError
