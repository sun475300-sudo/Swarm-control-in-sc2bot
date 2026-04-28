"""
Proxy Detection System - Detects and counters proxy strategies
HIGH PRIORITY FEATURE
"""

from dataclasses import dataclass
from enum import Enum
from typing import Any, Dict, List, Optional, Tuple


class ProxyType(Enum):
    GATEWAY = "gateway"
    FORGE = "forge"
    PYLON = "pylon"
    BARRACKS = "barracks"
    FACTORY = "factory"
    STARPORT = "starport"
    UNKNOWN = "unknown"


class ProxyDetectionResult:
    def __init__(self):
        self.is_proxy: bool = False
        self.proxy_type: ProxyType = ProxyType.UNKNOWN
        self.confidence: float = 0.0
        self.location: Optional[Tuple[int, int]] = None
        self.threat_level: str = "LOW"
        self.recommendation: str = ""


class ProxyDetector:
    def __init__(self, bot=None):
        self.bot = bot
        self.proxy_history: List[ProxyDetectionResult] = []
        self.enemy_buildings_spotted: List[Dict] = []
        self.normal_expansion_locations: List[Tuple[int, int]] = []

    def initialize_normal_expansions(self, locations: List[Tuple[int, int]]) -> None:
        """Initialize known expansion locations"""
        self.normal_expansion_locations = locations

    def analyze_enemy_building(
        self, position: Tuple[int, int], building_type: str
    ) -> ProxyDetectionResult:
        """Analyze if enemy building is a proxy"""
        result = ProxyDetectionResult()

        is_near_expansion = self._is_near_expansion(position)
        is_near_start = self._is_near_start(position)
        distance_to_base = self._distance_to_enemy_base(position)

        if building_type.lower() in ["pylon", "gateway", "forge", "barracks"]:
            if not is_near_expansion and not is_near_start:
                result.is_proxy = True
                result.confidence = 0.8
                result.proxy_type = self._classify_proxy(building_type)
                result.location = position
                result.threat_level = "HIGH"
                result.recommendation = f"ATTACK {building_type} IMMEDIATELY"
            elif is_near_expansion:
                result.is_proxy = False
                result.confidence = 0.9
                result.proxy_type = ProxyType.UNKNOWN
                result.threat_level = "LOW"
                result.recommendation = "Normal expansion"

        self.proxy_history.append(result)
        return result

    def _is_near_expansion(self, position: Tuple[int, int]) -> bool:
        """Check if position is near an expansion"""
        for exp in self.normal_expansion_locations:
            if self._distance(position, exp) < 15:
                return True
        return False

    def _is_near_start(self, position: Tuple[int, int]) -> bool:
        """Check if position is near start locations"""
        start_locations = [(0, 0), (150, 150), (150, 0), (0, 150)]
        for start in start_locations:
            if self._distance(position, start) < 20:
                return True
        return False

    def _distance_to_enemy_base(self, position: Tuple[int, int]) -> float:
        """Calculate distance to estimated enemy base"""
        enemy_base_estimate = (150, 150)
        return self._distance(position, enemy_base_estimate)

    def _distance(self, pos1: Tuple[int, int], pos2: Tuple[int, int]) -> float:
        """Calculate distance between two points"""
        return ((pos1[0] - pos2[0]) ** 2 + (pos1[1] - pos2[1]) ** 2) ** 0.5

    def _classify_proxy(self, building_type: str) -> ProxyType:
        """Classify the type of proxy"""
        mapping = {
            "gateway": ProxyType.GATEWAY,
            "forge": ProxyType.FORGE,
            "pylon": ProxyType.PYLON,
            "barracks": ProxyType.BARRACKS,
            "factory": ProxyType.FACTORY,
            "starport": ProxyType.STARPORT,
        }
        return mapping.get(building_type.lower(), ProxyType.UNKNOWN)

    def get_proxy_alerts(self) -> List[ProxyDetectionResult]:
        """Get all detected proxy alerts"""
        return [r for r in self.proxy_history if r.is_proxy]

    def calculate_counter_strategy(self, proxy_type: ProxyType) -> Dict[str, Any]:
        """Calculate counter strategy for detected proxy"""
        strategies = {
            ProxyType.GATEWAY: {
                "response": "RUSH_WITH_ZERGLINGS",
                "timing": "IMMEDIATE",
                "recommended_units": ["Zergling"],
                "attack_point": "PROXY_LOCATION",
            },
            ProxyType.FORGE: {
                "response": "DEFENSIVE_HOLD",
                "timing": "2_MINUTES",
                "recommended_units": ["Zergling", "Roach"],
                "attack_point": "PROXY_LOCATION",
            },
            ProxyType.BARRACKS: {
                "response": "EARLY_ATTACK",
                "timing": "ASAP",
                "recommended_units": ["Zergling", "Baneling"],
                "attack_point": "PROXY_LOCATION",
            },
            ProxyType.PYLON: {
                "response": "DESTROY_PYLON",
                "timing": "IMMEDIATE",
                "recommended_units": ["Zergling"],
                "attack_point": "PYLON",
            },
            ProxyType.UNKNOWN: {
                "response": "SCOUT_MORE",
                "timing": "NOW",
                "recommended_units": ["Zergling", "Overlord"],
                "attack_point": "ENEMY_BASE",
            },
        }
        return strategies.get(proxy_type, strategies[ProxyType.UNKNOWN])


def create_proxy_detector(bot=None) -> ProxyDetector:
    """Factory function to create proxy detector"""
    return ProxyDetector(bot)
