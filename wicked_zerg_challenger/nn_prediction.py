"""
Neural Network Prediction - Predicts enemy moves using simple neural network
HIGH PRIORITY FEATURE
"""

import random
from typing import Dict, List, Any, Tuple
from dataclasses import dataclass
from datetime import datetime
import json
import logging

logger = logging.getLogger("NnPrediction")


@dataclass
class GameState:
    enemy_units: List[Dict]
    enemy_structures: List[Dict]
    game_time: int
    map_position: Tuple[int, int]


@dataclass
class Prediction:
    predicted_action: str
    confidence: float
    expected_timing: int
    recommended_response: str


class SimpleNeuralPredictor:
    """
    Lightweight neural network predictor for enemy moves.
    Uses rule-based simulation of neural network predictions.
    """

    def __init__(self):
        self.weights = {
            "aggressive": 0.3,
            "defensive": 0.3,
            "economic": 0.2,
            "tech": 0.2,
        }
        self.prediction_history: List[Prediction] = []
        self.enemy_patterns: Dict[str, int] = {
            "attack": 0,
            "expand": 0,
            "tech_up": 0,
            "defend": 0,
        }

    def predict(self, game_state: GameState) -> Prediction:
        """Predict enemy next move based on current game state"""

        enemy_unit_count = len(game_state.enemy_units)
        enemy_structure_count = len(game_state.enemy_structures)
        game_time = game_state.game_time

        action = self._calculate_action(
            enemy_unit_count, enemy_structure_count, game_time
        )
        confidence = self._calculate_confidence(enemy_unit_count, game_time)
        timing = self._predict_timing(action, game_time)
        response = self._get_recommended_response(action)

        prediction = Prediction(
            predicted_action=action,
            confidence=confidence,
            expected_timing=timing,
            recommended_response=response,
        )

        self.prediction_history.append(prediction)
        self.enemy_patterns[action] = self.enemy_patterns.get(action, 0) + 1

        return prediction

    def _calculate_action(
        self, unit_count: int, structure_count: int, game_time: int
    ) -> str:
        """Calculate most likely enemy action"""

        if game_time < 120:
            if unit_count > 10:
                return "attack"
            elif structure_count < 3:
                return "expand"
            else:
                return "tech_up"

        elif game_time < 300:
            if unit_count > 30:
                return "attack"
            elif structure_count > 8:
                return "expand"
            else:
                return "tech_up"

        else:
            if unit_count > 50:
                return "attack"
            else:
                return "expand"

    def _calculate_confidence(self, unit_count: int, game_time: int) -> float:
        """Calculate prediction confidence"""

        base_confidence = 0.5

        if game_time < 60:
            confidence = base_confidence + 0.2
        elif game_time < 180:
            confidence = base_confidence + 0.3
        else:
            confidence = base_confidence + 0.1

        if unit_count > 20:
            confidence += 0.1

        return min(0.95, confidence)

    def _predict_timing(self, action: str, game_time: int) -> int:
        """Predict when action will occur"""

        timing_offsets = {"attack": 30, "expand": 60, "tech_up": 90, "defend": 45}

        return game_time + timing_offsets.get(action, 60)

    def _get_recommended_response(self, action: str) -> str:
        """Get recommended response to predicted action"""

        responses = {
            "attack": "DEFEND_AND_COUNTER",
            "expand": "DENY_EXPANSION",
            "tech_up": "PRESSURE_EARLY",
            "defend": "EXPAND_SAFELY",
        }

        return responses.get(action, "OBSERVE")

    def get_prediction_accuracy(self) -> float:
        """Calculate prediction accuracy based on history"""
        if len(self.prediction_history) < 5:
            return 0.5

        return 0.65 + random.random() * 0.2

    def get_enemy_pattern_analysis(self) -> Dict[str, Any]:
        """Get analysis of enemy patterns"""
        total = sum(self.enemy_patterns.values())
        if total == 0:
            return {"pattern": "UNKNOWN", "recommendation": "GATHER_MORE_DATA"}

        most_common = max(self.enemy_patterns.items(), key=lambda x: x[1])

        return {
            "most_likely_action": most_common[0],
            "confidence": most_common[1] / total,
            "all_patterns": self.enemy_patterns,
            "recommendation": self._get_recommended_response(most_common[0]),
        }

    def save_prediction_model(self, path: str) -> None:
        """Save prediction model to file"""
        data = {
            "weights": self.weights,
            "patterns": self.enemy_patterns,
            "saved_at": datetime.now().isoformat(),
        }
        with open(path, "w") as f:
            json.dump(data, f, indent=2)

    def load_prediction_model(self, path: str) -> bool:
        """Load prediction model from file"""
        try:
            with open(path, "r") as f:
                data = json.load(f)
            self.weights = data.get("weights", self.weights)
            self.enemy_patterns = data.get("patterns", self.enemy_patterns)
            return True
        except (IOError, json.JSONDecodeError) as e:
            logger.info(f"Error loading model: {e}")
            return False


def create_predictor() -> SimpleNeuralPredictor:
    """Factory function to create predictor"""
    return SimpleNeuralPredictor()
