# -*- coding: utf-8 -*-
"""Tests for MapManager - map rotation, selection, and stats tracking."""

import sys
import json
import tempfile
import os
import pytest

sys.path.insert(0, "wicked_zerg_challenger")

from map_manager import MapManager, TRAINING_MAPS, MAP_CHARACTERISTICS


class TestMapCatalog:
    def test_training_maps_is_non_empty(self):
        assert len(TRAINING_MAPS) > 0

    def test_characteristics_exist_for_each_map(self):
        for map_name in TRAINING_MAPS:
            assert map_name in MAP_CHARACTERISTICS
            info = MAP_CHARACTERISTICS[map_name]
            assert "description" in info
            assert "focus" in info
            assert "difficulty" in info


class TestInitialization:
    def test_instantiate_with_tempfile(self):
        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
            fname = f.name
        try:
            os.unlink(fname)  # remove so _load_stats hits "file missing" path
            mgr = MapManager(stats_file=fname)
            assert mgr.stats == {}
            assert mgr.current_map_index == 0
        finally:
            if os.path.exists(fname):
                os.unlink(fname)

    def test_load_existing_stats(self):
        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
            json.dump({"LeyLinesAIE_v3": {"wins": 3, "losses": 1}}, f)
            fname = f.name
        try:
            mgr = MapManager(stats_file=fname)
            assert mgr.stats["LeyLinesAIE_v3"]["wins"] == 3
        finally:
            os.unlink(fname)


class TestGetAvailableMaps:
    def test_returns_training_maps_when_no_maps_dir(self):
        mgr = MapManager(stats_file="/tmp/nonexistent_stats.json")
        maps = mgr.get_available_maps()
        # When Maps/ directory doesn't exist, falls back to TRAINING_MAPS
        assert len(maps) > 0
        assert all(isinstance(m, str) for m in maps)


class TestSelectMap:
    def setup_method(self):
        self.tmpfile = tempfile.NamedTemporaryFile(
            mode="w", suffix=".json", delete=False
        )
        self.tmpfile.close()
        os.unlink(self.tmpfile.name)
        self.mgr = MapManager(stats_file=self.tmpfile.name)

    def teardown_method(self):
        if os.path.exists(self.tmpfile.name):
            os.unlink(self.tmpfile.name)

    def test_sequential_selection_cycles(self):
        available = self.mgr.get_available_maps()
        if len(available) < 2:
            pytest.skip("Need at least 2 maps for sequential test")
        first = self.mgr.select_map("sequential")
        second = self.mgr.select_map("sequential")
        assert first != second

    def test_single_mode_always_returns_first(self):
        first = self.mgr.select_map("single")
        second = self.mgr.select_map("single")
        assert first == second

    def test_random_mode_returns_valid_map(self):
        m = self.mgr.select_map("random")
        assert m in self.mgr.get_available_maps()

    def test_weighted_mode_returns_valid_map(self):
        m = self.mgr.select_map("weighted")
        assert m in self.mgr.get_available_maps()


class TestRecordResult:
    def setup_method(self):
        self.tmpfile = tempfile.NamedTemporaryFile(
            mode="w", suffix=".json", delete=False
        )
        self.tmpfile.close()
        os.unlink(self.tmpfile.name)
        self.mgr = MapManager(stats_file=self.tmpfile.name)

    def teardown_method(self):
        if os.path.exists(self.tmpfile.name):
            os.unlink(self.tmpfile.name)

    def test_record_win(self):
        self.mgr.record_result("TestMap", True)
        stats = self.mgr.get_map_stats("TestMap")
        assert stats["wins"] == 1
        assert stats["losses"] == 0

    def test_record_loss(self):
        self.mgr.record_result("TestMap", False)
        stats = self.mgr.get_map_stats("TestMap")
        assert stats["wins"] == 0
        assert stats["losses"] == 1

    def test_record_multiple_results(self):
        for _ in range(3):
            self.mgr.record_result("M1", True)
        for _ in range(2):
            self.mgr.record_result("M1", False)
        stats = self.mgr.get_map_stats("M1")
        assert stats["wins"] == 3
        assert stats["losses"] == 2

    def test_record_persists_to_file(self):
        self.mgr.record_result("TestMap", True)
        # Read file directly
        with open(self.tmpfile.name) as f:
            saved = json.load(f)
        assert saved["TestMap"]["wins"] == 1


class TestGetMapStats:
    def test_missing_map_returns_zero_record(self):
        with tempfile.NamedTemporaryFile(suffix=".json", delete=False) as f:
            fname = f.name
        try:
            os.unlink(fname)
            mgr = MapManager(stats_file=fname)
            stats = mgr.get_map_stats("Unknown_Map")
            assert stats == {"wins": 0, "losses": 0}
        finally:
            if os.path.exists(fname):
                os.unlink(fname)


class TestWeightedSelection:
    def test_weighted_penalizes_high_winrate_maps(self):
        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
            fname = f.name
        try:
            os.unlink(fname)
            mgr = MapManager(stats_file=fname)
            # Give one map 100% winrate, another 0% winrate
            easy = TRAINING_MAPS[0]
            hard = TRAINING_MAPS[1]
            mgr.stats[easy] = {"wins": 100, "losses": 0}
            mgr.stats[hard] = {"wins": 0, "losses": 100}

            selections = [mgr._select_weighted([easy, hard]) for _ in range(50)]
            # hard should appear more often due to lower win_rate (higher weight)
            hard_count = selections.count(hard)
            assert hard_count > 15  # should be > 50% on average
        finally:
            if os.path.exists(fname):
                os.unlink(fname)
