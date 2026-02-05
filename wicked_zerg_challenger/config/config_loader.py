"""
Configuration Loader - Centralized configuration management

Loads strategy configurations from JSON files and provides
type-safe access to configuration values.
"""

import json
from pathlib import Path
from typing import Dict, Any, Optional


class ConfigLoader:
    """Centralized configuration management"""

    _instance = None
    _config_cache: Dict[str, Any] = {}

    def __new__(cls):
        """Singleton pattern"""
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    @staticmethod
    def load_strategy_config() -> Dict[str, Any]:
        """
        Load strategy configuration from JSON

        Returns:
            Dictionary containing all strategy configuration
        """
        if "strategy" in ConfigLoader._config_cache:
            return ConfigLoader._config_cache["strategy"]

        config_path = Path(__file__).parent / "strategy_config.json"

        try:
            with open(config_path, 'r', encoding='utf-8') as f:
                config = json.load(f)
                ConfigLoader._config_cache["strategy"] = config
                return config
        except FileNotFoundError:
            print(f"[WARNING] Strategy config not found: {config_path}")
            return ConfigLoader._get_default_config()
        except json.JSONDecodeError as e:
            print(f"[ERROR] Invalid JSON in strategy config: {e}")
            return ConfigLoader._get_default_config()

    @staticmethod
    def get_scouting_config() -> Dict[str, Any]:
        """Get scouting configuration"""
        config = ConfigLoader.load_strategy_config()
        return config.get("scouting", {})

    @staticmethod
    def get_harassment_config() -> Dict[str, Any]:
        """Get harassment configuration"""
        config = ConfigLoader.load_strategy_config()
        return config.get("harassment", {})

    @staticmethod
    def get_expansion_config() -> Dict[str, Any]:
        """Get expansion configuration"""
        config = ConfigLoader.load_strategy_config()
        return config.get("expansion", {})

    @staticmethod
    def get_combat_config() -> Dict[str, Any]:
        """Get combat configuration"""
        config = ConfigLoader.load_strategy_config()
        return config.get("combat", {})

    @staticmethod
    def get_performance_config() -> Dict[str, Any]:
        """Get performance configuration"""
        config = ConfigLoader.load_strategy_config()
        return config.get("performance", {})

    @staticmethod
    def get_timing_config() -> Dict[str, Any]:
        """Get timing configuration"""
        config = ConfigLoader.load_strategy_config()
        return config.get("timing", {})

    @staticmethod
    def get_value(section: str, key: str, default: Any = None) -> Any:
        """
        Get a specific configuration value

        Args:
            section: Configuration section name
            key: Key within section (supports dot notation for nested keys)
            default: Default value if not found

        Returns:
            Configuration value or default

        Example:
            >>> ConfigLoader.get_value("scouting", "early_game_interval", 30)
            25
            >>> ConfigLoader.get_value("harassment", "allocation_percent.aggressive", 0.15)
            0.15
        """
        config = ConfigLoader.load_strategy_config()
        section_config = config.get(section, {})

        # Support dot notation for nested keys
        if "." in key:
            keys = key.split(".")
            value = section_config
            for k in keys:
                if isinstance(value, dict):
                    value = value.get(k)
                else:
                    return default
            return value if value is not None else default
        else:
            return section_config.get(key, default)

    @staticmethod
    def reload_config() -> None:
        """Reload configuration from disk (clear cache)"""
        ConfigLoader._config_cache.clear()

    @staticmethod
    def _get_default_config() -> Dict[str, Any]:
        """
        Get default configuration (fallback)

        Returns:
            Default configuration dictionary
        """
        return {
            "scouting": {
                "early_game_interval": 25,
                "mid_game_interval": 40,
                "late_game_interval": 35,
                "emergency_interval": 15
            },
            "harassment": {
                "default_mode": "opportunistic",
                "allocation_percent": {
                    "opportunistic": 0.10
                }
            },
            "expansion": {
                "target_timings": [60, 90, 150, 210, 270, 330],
                "aggressive_minerals": 300
            },
            "combat": {
                "hp_thresholds": {
                    "retreat": 0.3,
                    "burrow": 0.4
                }
            },
            "performance": {
                "frame_time_targets": {
                    "target_ms": 10.0,
                    "warning_ms": 15.0
                }
            },
            "timing": {
                "game_fps": 22,
                "intervals_frames": {
                    "1_second": 22
                }
            }
        }


# Convenience functions for direct access

def get_scouting_config() -> Dict[str, Any]:
    """Get scouting configuration"""
    return ConfigLoader.get_scouting_config()


def get_harassment_config() -> Dict[str, Any]:
    """Get harassment configuration"""
    return ConfigLoader.get_harassment_config()


def get_expansion_config() -> Dict[str, Any]:
    """Get expansion configuration"""
    return ConfigLoader.get_expansion_config()


def get_combat_config() -> Dict[str, Any]:
    """Get combat configuration"""
    return ConfigLoader.get_combat_config()


def get_performance_config() -> Dict[str, Any]:
    """Get performance configuration"""
    return ConfigLoader.get_performance_config()


def get_timing_config() -> Dict[str, Any]:
    """Get timing configuration"""
    return ConfigLoader.get_timing_config()
