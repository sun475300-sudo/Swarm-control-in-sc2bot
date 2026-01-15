"""
Configuration utilities.
"""

from dataclasses import dataclass
from typing import Optional


@dataclass
class Config:
    """Application configuration."""
    
    # Resource thresholds
    MINERAL_THRESHOLD_ECONOMY: int = 100
    MINERAL_THRESHOLD_EXPAND: int = 300
    MINERAL_THRESHOLD_ARMY: int = 300
    
    # Supply thresholds
    SUPPLY_URGENT_THRESHOLD: float = 0.9  # 90% of cap
    SUPPLY_EXPAND_THRESHOLD: float = 0.7  # 70% of cap
    
    # Army thresholds
    ARMY_SIZE_DEFENSE: int = 20
    ARMY_SIZE_ALL_IN: int = 50
    
    # Training settings
    DEFAULT_EPOCHS: int = 1
    DEFAULT_BATCH_SIZE: int = 64
    
    # Logging
    LOG_DIR: str = "logs"
    PATCH_SUGGESTIONS_FILE: str = "patch_suggestions.txt"


# Global config instance
config = Config()
