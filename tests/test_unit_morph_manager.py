# -*- coding: utf-8 -*-
"""Tests for UnitMorphManager morph ratio logic."""

import sys
import pytest

sys.path.insert(0, "wicked_zerg_challenger")

from unit_morph_manager import UnitMorphManager


class _FakeBot:
    def __init__(self):
        self.blackboard = None


class TestInitialization:
    def test_instantiate(self):
        mgr = UnitMorphManager(_FakeBot())
        assert mgr.last_morph_check == 0

    def test_morph_ratios_include_all_races(self):
        mgr = UnitMorphManager(_FakeBot())
        assert "Terran" in mgr.morph_ratios
        assert "Protoss" in mgr.morph_ratios
        assert "Zerg" in mgr.morph_ratios
        assert "Unknown" in mgr.morph_ratios


class TestMorphRatios:
    def setup_method(self):
        self.mgr = UnitMorphManager(_FakeBot())

    def test_terran_has_expected_ratios(self):
        ratios = self.mgr.morph_ratios["Terran"]
        assert "baneling_ratio" in ratios
        assert "ravager_ratio" in ratios
        assert "lurker_ratio" in ratios
        assert "broodlord_ratio" in ratios

    def test_all_ratios_are_floats(self):
        for race, ratios in self.mgr.morph_ratios.items():
            for name, value in ratios.items():
                assert isinstance(value, float), f"{race}.{name} is not float"

    def test_all_ratios_in_valid_range(self):
        for race, ratios in self.mgr.morph_ratios.items():
            for name, value in ratios.items():
                assert 0.0 <= value <= 1.0, f"{race}.{name}={value} out of range"


class TestDynamicRatios:
    def setup_method(self):
        self.mgr = UnitMorphManager(_FakeBot())

    def test_dynamic_ratios_falls_back_to_base(self):
        # No blackboard -> should return base ratios
        result = self.mgr._get_dynamic_ratios("Terran")
        base = self.mgr.morph_ratios["Terran"]
        assert result == base

    def test_unknown_race_returns_unknown_defaults(self):
        result = self.mgr._get_dynamic_ratios("Alien")
        assert result == self.mgr.morph_ratios["Unknown"]

    def test_dynamic_ratios_returns_copy(self):
        result = self.mgr._get_dynamic_ratios("Terran")
        result["baneling_ratio"] = 0.99
        # Original should not be modified
        assert self.mgr.morph_ratios["Terran"]["baneling_ratio"] != 0.99


class TestCooldownState:
    def test_cooldowns_initialized_to_zero(self):
        mgr = UnitMorphManager(_FakeBot())
        assert mgr.last_baneling_morph == 0
        assert mgr.last_ravager_morph == 0
        assert mgr.last_lurker_morph == 0
        assert mgr.last_broodlord_morph == 0

    def test_morph_check_interval_is_set(self):
        mgr = UnitMorphManager(_FakeBot())
        assert mgr.morph_check_interval > 0
