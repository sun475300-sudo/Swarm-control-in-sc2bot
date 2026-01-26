import json
from pathlib import Path
from typing import Dict, Any, Optional
from utils.logger import get_logger

class KnowledgeManager:
    """
    Commander Knowledge Manager
    Loads and serves strategic knowledge (build orders, ratios, timings) from JSON.
    """
    def __init__(self):
        self.logger = get_logger("KnowledgeManager")
        self.knowledge: Dict[str, Any] = {}
        self.load_knowledge()

    def load_knowledge(self) -> None:
        """Load knowledge from commander_knowledge.json"""
        try:
            # Assume file is in the same directory as this script
            file_path = Path(__file__).parent / "commander_knowledge.json"
            
            if not file_path.exists():
                self.logger.error(f"Knowledge file not found: {file_path}")
                return

            with open(file_path, "r", encoding="utf-8") as f:
                self.knowledge = json.load(f)
            
            self.logger.info(f"Loaded knowledge version: {self.knowledge.get('version', 'unknown')}")
            self.logger.info(f"Loaded {len(self.knowledge.get('build_orders', {}))} build orders")

        except Exception as e:
            self.logger.error(f"Failed to load knowledge: {e}")

    def get_build_order(self, build_name: str) -> Optional[Dict]:
        """Get specific build order by name"""
        return self.knowledge.get("build_orders", {}).get(build_name)

    def get_unit_ratios(self, race: str, game_phase: str) -> Dict[str, float]:
        """Get unit ratios for specific race and phase"""
        # Normalize keys (e.g., "Terran" -> "Terran")
        race_data = self.knowledge.get("unit_ratios", {}).get(race, {})
        return race_data.get(game_phase, {})

    def get_timing(self, category: str, key: str) -> float:
        """Get specific timingBenchmark"""
        return self.knowledge.get("timings", {}).get(category, {}).get(key, 0.0)

    def get_all_build_names(self) -> list:
        """Get list of available build orders"""
        return list(self.knowledge.get("build_orders", {}).keys())

    def get_map_strategy(self, map_size: str) -> Dict:
        """Get strategy for map size (Small/Large/Default)"""
        strategies = self.knowledge.get("map_strategies", {})
        return strategies.get(map_size, strategies.get("Default"))

    def get_counter_unit(self, enemy_unit_type: str) -> Optional[Dict]:
        """Get counter rule for specific enemy unit"""
        # Upper case key (e.g., VOIDRAY)
        key = enemy_unit_type.upper()
        return self.knowledge.get("counter_rules", {}).get(key)

    def get_micro_priority(self, enemy_unit_type: str) -> int:
        """Get target priority for enemy unit"""
        key = enemy_unit_type.upper()
        return self.knowledge.get("micro_settings", {}).get("target_priorities", {}).get(key, 1) # Default 1
