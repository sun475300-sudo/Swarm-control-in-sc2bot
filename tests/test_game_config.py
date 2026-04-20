# -*- coding: utf-8 -*-
"""Tests for game_config.py — GameConfig + subclasses + JSON load/save."""

import sys
import json
import os
import tempfile
import pytest

sys.path.insert(0, "wicked_zerg_challenger")

from game_config import GameConfig, AggressiveConfig, EconomicConfig, SafeConfig


class TestGamePhaseTimings:
    def test_phase_timings_ordered(self):
        assert GameConfig.OPENING_PHASE_END < GameConfig.EARLY_GAME_END
        assert GameConfig.EARLY_GAME_END < GameConfig.MID_GAME_END

    def test_phase_timings_positive(self):
        assert GameConfig.OPENING_PHASE_END > 0
        assert GameConfig.EARLY_GAME_END > 0
        assert GameConfig.MID_GAME_END > 0


class TestEconomyLimits:
    def test_drone_limits_ordered(self):
        assert GameConfig.DRONE_LIMIT_PER_BASE <= GameConfig.DRONE_LIMIT_PER_BASE_GAS
        assert GameConfig.MIN_DRONES < GameConfig.MAX_DRONES

    def test_mineral_thresholds_ordered(self):
        assert GameConfig.MINERAL_BANKING_THRESHOLD < GameConfig.MINERAL_OVERFLOW
        assert GameConfig.MINERAL_OVERFLOW < GameConfig.MINERAL_CRITICAL

    def test_gas_thresholds_ordered(self):
        assert GameConfig.GAS_OVERFLOW_THRESHOLD < GameConfig.GAS_CRITICAL

    def test_mineral_gas_ratio_positive(self):
        assert GameConfig.MINERAL_TO_GAS_RATIO > 0


class TestSupplyConfig:
    def test_supply_cap_standard(self):
        assert GameConfig.SUPPLY_CAP == 200

    def test_supply_buffers_positive(self):
        assert GameConfig.SUPPLY_BUFFER_OPENING > 0
        assert GameConfig.SUPPLY_BUFFER_EARLY > 0
        assert GameConfig.SUPPLY_BUFFER_MID > 0


class TestExpansionTiming:
    def test_expansions_progress(self):
        assert GameConfig.NATURAL_EXPANSION_TIMING < GameConfig.THIRD_BASE_TIMING
        assert GameConfig.THIRD_BASE_TIMING < GameConfig.FOURTH_BASE_TIMING


class TestToDict:
    def test_returns_dict(self):
        data = GameConfig.to_dict()
        assert isinstance(data, dict)

    def test_contains_known_keys(self):
        data = GameConfig.to_dict()
        assert "OPENING_PHASE_END" in data
        assert "SUPPLY_CAP" in data

    def test_excludes_callables(self):
        data = GameConfig.to_dict()
        for key, value in data.items():
            assert not callable(value)

    def test_excludes_private(self):
        data = GameConfig.to_dict()
        for key in data.keys():
            assert not key.startswith("_")


class TestLoadFromDict:
    def test_loads_simple_override(self):
        original = GameConfig.SUPPLY_CAP
        try:
            GameConfig.load_from_dict({"SUPPLY_CAP": 150})
            assert GameConfig.SUPPLY_CAP == 150
        finally:
            GameConfig.SUPPLY_CAP = original  # restore

    def test_ignores_unknown_keys(self):
        GameConfig.load_from_dict({"NONEXISTENT_KEY_XYZ": 999})
        assert not hasattr(GameConfig, "NONEXISTENT_KEY_XYZ")


class TestSaveAndLoadFile:
    def test_save_and_load_roundtrip(self):
        with tempfile.NamedTemporaryFile(suffix=".json", delete=False) as f:
            fname = f.name
        try:
            GameConfig.save_to_file(fname)
            with open(fname) as f:
                saved = json.load(f)
            assert "SUPPLY_CAP" in saved
        finally:
            if os.path.exists(fname):
                os.unlink(fname)

    def test_load_nonexistent_file_does_not_raise(self):
        GameConfig.load_from_file("/tmp/definitely_not_a_real_config.json")

    def test_save_to_filename_only_path(self):
        # Bug fix test: os.makedirs("") on filename-only path
        with tempfile.TemporaryDirectory() as tmpdir:
            os.chdir(tmpdir)
            GameConfig.save_to_file("config.json")
            assert os.path.exists("config.json")


class TestSubclasses:
    def test_aggressive_inherits_game_config(self):
        assert issubclass(AggressiveConfig, GameConfig)

    def test_economic_inherits_game_config(self):
        assert issubclass(EconomicConfig, GameConfig)

    def test_safe_inherits_game_config(self):
        assert issubclass(SafeConfig, GameConfig)

    def test_subclasses_have_overrides(self):
        # Each variant should override at least something
        aggressive_dict = AggressiveConfig.to_dict()
        game_dict = GameConfig.to_dict()
        assert isinstance(aggressive_dict, dict)
        assert isinstance(game_dict, dict)
