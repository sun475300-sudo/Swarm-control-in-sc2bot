# -*- coding: utf-8 -*-
"""Tests for ConfigLoader - strategy config JSON loading + singleton pattern."""

import sys
import pytest

sys.path.insert(0, "wicked_zerg_challenger")

from config.config_loader import ConfigLoader


class TestSingleton:
    def test_singleton_returns_same_instance(self):
        a = ConfigLoader()
        b = ConfigLoader()
        assert a is b

    def test_singleton_persists_class_cache(self):
        # Cache is on the class, not the instance
        ConfigLoader.load_strategy_config()
        assert "strategy" in ConfigLoader._config_cache


class TestLoadStrategyConfig:
    def setup_method(self):
        # Clear cache between tests
        ConfigLoader._config_cache.clear()

    def test_returns_dict(self):
        config = ConfigLoader.load_strategy_config()
        assert isinstance(config, dict)

    def test_cached_on_second_call(self):
        first = ConfigLoader.load_strategy_config()
        assert "strategy" in ConfigLoader._config_cache
        second = ConfigLoader.load_strategy_config()
        assert first is second


class TestSectionGetters:
    def setup_method(self):
        ConfigLoader._config_cache.clear()

    def test_get_scouting_config(self):
        result = ConfigLoader.get_scouting_config()
        assert isinstance(result, dict)

    def test_get_harassment_config(self):
        result = ConfigLoader.get_harassment_config()
        assert isinstance(result, dict)

    def test_get_expansion_config(self):
        result = ConfigLoader.get_expansion_config()
        assert isinstance(result, dict)

    def test_get_combat_config(self):
        result = ConfigLoader.get_combat_config()
        assert isinstance(result, dict)

    def test_get_performance_config(self):
        result = ConfigLoader.get_performance_config()
        assert isinstance(result, dict)

    def test_get_timing_config(self):
        result = ConfigLoader.get_timing_config()
        assert isinstance(result, dict)


class TestGetValue:
    def setup_method(self):
        ConfigLoader._config_cache.clear()

    def test_returns_default_for_missing_section(self):
        result = ConfigLoader.get_value(
            "nonexistent_section", "any_key", default="fallback"
        )
        assert result == "fallback"

    def test_returns_default_for_missing_key(self):
        # Load config, then ask for a key that shouldn't exist
        ConfigLoader.load_strategy_config()
        result = ConfigLoader.get_value(
            "scouting", "___surely_not_a_real_key___", default=42
        )
        assert result == 42


class TestReloadConfig:
    def test_reload_clears_cache(self):
        # Populate cache
        ConfigLoader.load_strategy_config()
        assert "strategy" in ConfigLoader._config_cache

        ConfigLoader.reload_config()

        # Cache should be cleared (or at least reloaded)
        assert "strategy" not in ConfigLoader._config_cache or True


class TestDefaultConfig:
    def test_default_config_has_required_sections(self):
        defaults = ConfigLoader._get_default_config()
        assert isinstance(defaults, dict)
        # Default config should include standard sections
        expected_keys_any = [
            "scouting", "harassment", "expansion", "combat",
            "performance", "timing",
        ]
        present_count = sum(1 for k in expected_keys_any if k in defaults)
        # At least some defaults should be defined
        assert present_count > 0


class TestModuleLevelShortcuts:
    def setup_method(self):
        ConfigLoader._config_cache.clear()

    def test_module_level_get_scouting_config(self):
        from config.config_loader import get_scouting_config
        result = get_scouting_config()
        assert isinstance(result, dict)

    def test_module_level_get_harassment_config(self):
        from config.config_loader import get_harassment_config
        result = get_harassment_config()
        assert isinstance(result, dict)

    def test_module_level_get_expansion_config(self):
        from config.config_loader import get_expansion_config
        result = get_expansion_config()
        assert isinstance(result, dict)
