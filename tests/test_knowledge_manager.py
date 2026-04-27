# -*- coding: utf-8 -*-
"""Tests for KnowledgeManager - JSON-based strategic knowledge loading."""

import sys
import pytest

sys.path.insert(0, "wicked_zerg_challenger")

from knowledge_manager import KnowledgeManager


class TestKnowledgeLoading:
    def test_loads_successfully(self):
        km = KnowledgeManager()
        assert isinstance(km.knowledge, dict)

    def test_has_version(self):
        km = KnowledgeManager()
        assert "version" in km.knowledge

    def test_has_build_orders(self):
        km = KnowledgeManager()
        assert "build_orders" in km.knowledge


class TestBuildOrders:
    def setup_method(self):
        self.km = KnowledgeManager()

    def test_get_known_build_order(self):
        result = self.km.get_build_order("STANDARD_12POOL")
        assert result is not None
        assert "name" in result
        assert "steps" in result

    def test_get_unknown_build_order_returns_none(self):
        assert self.km.get_build_order("NONEXISTENT_BUILD") is None

    def test_get_all_build_names_returns_list(self):
        names = self.km.get_all_build_names()
        assert isinstance(names, list)
        assert "STANDARD_12POOL" in names

    def test_build_order_has_steps(self):
        order = self.km.get_build_order("STANDARD_12POOL")
        if order:
            assert isinstance(order["steps"], list)
            assert len(order["steps"]) > 0


class TestUnitRatios:
    def setup_method(self):
        self.km = KnowledgeManager()

    def test_get_ratios_returns_dict(self):
        ratios = self.km.get_unit_ratios("Terran", "EARLY")
        assert isinstance(ratios, dict)

    def test_unknown_race_returns_empty(self):
        ratios = self.km.get_unit_ratios("InvalidRace", "EARLY")
        assert ratios == {}


class TestTimings:
    def setup_method(self):
        self.km = KnowledgeManager()

    def test_get_timing_returns_float(self):
        t = self.km.get_timing("expansion", "second_base")
        assert isinstance(t, (int, float))

    def test_unknown_timing_returns_zero(self):
        t = self.km.get_timing("bogus_category", "bogus_key")
        assert t == 0.0


class TestMapStrategy:
    def test_get_map_strategy_returns_dict_or_default(self):
        km = KnowledgeManager()
        result = km.get_map_strategy("Small")
        # Should not crash, returns dict (or None only if Default also missing)
        assert result is None or isinstance(result, dict)

    def test_unknown_size_falls_back_to_default(self):
        km = KnowledgeManager()
        bogus = km.get_map_strategy("NonexistentSize")
        default = km.get_map_strategy("Default")
        # bogus should equal default
        assert bogus == default


class TestCounterUnit:
    def setup_method(self):
        self.km = KnowledgeManager()

    def test_unknown_unit_returns_none(self):
        assert self.km.get_counter_unit("NONEXISTENT_UNIT") is None

    def test_upper_case_normalization(self):
        # Should not crash with lowercase input
        result = self.km.get_counter_unit("voidray")
        # Either valid or None, but no crash
        assert result is None or isinstance(result, dict)


class TestMicroPriority:
    def setup_method(self):
        self.km = KnowledgeManager()

    def test_unknown_unit_returns_default(self):
        p = self.km.get_micro_priority("RANDOM_UNIT_NAME")
        assert p == 1  # Documented default
