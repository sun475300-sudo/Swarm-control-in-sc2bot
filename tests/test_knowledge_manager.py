# -*- coding: utf-8 -*-
"""
KnowledgeManager 테스트 - 전략 지식 JSON 로더
"""

import sys
from pathlib import Path

import pytest

PROJECT_ROOT = Path(__file__).parent.parent
BOT_ROOT = PROJECT_ROOT / "wicked_zerg_challenger"
if str(BOT_ROOT) not in sys.path:
    sys.path.insert(0, str(BOT_ROOT))


class TestInit:
    def test_init_loads(self):
        from knowledge_manager import KnowledgeManager
        km = KnowledgeManager()
        assert isinstance(km.knowledge, dict)


@pytest.fixture
def km_data():
    from knowledge_manager import KnowledgeManager
    km = KnowledgeManager()
    km.knowledge = {
        "version": "1.0",
        "build_orders": {
            "standard_12pool": {"steps": ["pool", "drone"], "win_rate": 0.6},
            "fast_expand": {"steps": ["hatch"], "win_rate": 0.55},
        },
        "unit_ratios": {"Terran": {"early": {"zergling": 0.5}}},
        "timings": {"expansion": {"first": 30.0}},
        "map_strategies": {"Small": {"aggression": "high"}, "Default": {"aggression": "balanced"}},
        "counter_rules": {"VOIDRAY": {"counter_unit": "QUEEN"}},
        "micro_settings": {"target_priorities": {"MEDIVAC": 10}},
    }
    return km


class TestQueries:
    def test_get_build_order(self, km_data):
        assert km_data.get_build_order("standard_12pool")["win_rate"] == 0.6

    def test_get_build_order_missing(self, km_data):
        assert km_data.get_build_order("nonexistent") is None

    def test_get_unit_ratios(self, km_data):
        assert km_data.get_unit_ratios("Terran", "early")["zergling"] == 0.5

    def test_get_unit_ratios_missing_race(self, km_data):
        assert km_data.get_unit_ratios("X", "early") == {}

    def test_get_timing(self, km_data):
        assert km_data.get_timing("expansion", "first") == 30.0

    def test_get_timing_missing(self, km_data):
        assert km_data.get_timing("x", "y") == 0.0

    def test_get_all_build_names(self, km_data):
        names = km_data.get_all_build_names()
        assert "standard_12pool" in names and "fast_expand" in names

    def test_get_map_strategy_specific(self, km_data):
        assert km_data.get_map_strategy("Small")["aggression"] == "high"

    def test_get_map_strategy_default(self, km_data):
        assert km_data.get_map_strategy("Unknown")["aggression"] == "balanced"

    def test_get_counter_unit_case_insensitive(self, km_data):
        assert km_data.get_counter_unit("voidray")["counter_unit"] == "QUEEN"
        assert km_data.get_counter_unit("VOIDRAY")["counter_unit"] == "QUEEN"

    def test_get_counter_unit_missing(self, km_data):
        assert km_data.get_counter_unit("nope") is None

    def test_get_micro_priority(self, km_data):
        assert km_data.get_micro_priority("MEDIVAC") == 10
        assert km_data.get_micro_priority("medivac") == 10

    def test_get_micro_priority_default(self, km_data):
        assert km_data.get_micro_priority("UNKNOWN") == 1
