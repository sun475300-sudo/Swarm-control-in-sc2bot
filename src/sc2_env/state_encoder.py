"""
State Encoder - Encodes game state into feature vectors for ML models.
"""

from typing import Dict, Any, List
import numpy as np


class StateEncoder:
    """
    Encodes game state observations into feature vectors.
    
    This class converts the observation dictionary into a fixed-size
    feature vector that can be used by machine learning models.
    """

    def __init__(self, feature_dim: int = 10) -> None:
        """
        Initialize StateEncoder.
        
        Args:
            feature_dim: Dimension of output feature vector
        """
        self.feature_dim = feature_dim

    def encode(self, obs: Dict[str, Any]) -> np.ndarray:
        """
        Encode observation into feature vector.
        
        Args:
            obs: Observation dictionary
            
        Returns:
            Feature vector as numpy array
        """
        features = []

        # Resource features
        features.append(obs.get("minerals", 0) / 1000.0)  # Normalize
        features.append(obs.get("gas", 0) / 500.0)  # Normalize
        features.append(obs.get("food_used", 0) / 200.0)  # Normalize
        features.append(obs.get("food_cap", 15) / 200.0)  # Normalize

        # Army features
        features.append(obs.get("army_size", 0) / 100.0)  # Normalize
        features.append(obs.get("base_count", 1) / 5.0)  # Normalize

        # Enemy features
        features.append(1.0 if obs.get("enemy_air", False) else 0.0)
        features.append(1.0 if obs.get("enemy_rush", False) else 0.0)
        features.append(obs.get("enemy_tech_level", 0) / 5.0)  # Normalize

        # Time feature
        features.append(obs.get("game_time", 0.0) / 600.0)  # Normalize to 10 minutes

        # Pad or truncate to feature_dim
        while len(features) < self.feature_dim:
            features.append(0.0)
        features = features[:self.feature_dim]

        return np.array(features, dtype=np.float32)
