# -*- coding: utf-8 -*-
"""Tests for knowledge_updater.py — game data analysis and JSON aggregation."""

import sys
import os
import json
import tempfile
import shutil
import pytest

sys.path.insert(0, "wicked_zerg_challenger")

from knowledge_updater import KnowledgeUpdater


@pytest.fixture
def temp_games_dir():
    """Create a temp directory with sample game JSONs."""
    tmpdir = tempfile.mkdtemp()

    # Sample game 1: Victory on MapA
    game1 = {
        "meta": {"map_name": "MapA"},
        "game_result": {"result": "Victory"},
        "expansions": [
            {"expansion_number": 1, "time": 60.0},
            {"expansion_number": 2, "time": 180.0},
        ],
        "tech_upgrades": [
            {"building": "SPAWNING_POOL", "time": 30.0},
            {"building": "LAIR", "time": 240.0},
        ],
    }
    # Sample game 2: Defeat on MapA
    game2 = {
        "meta": {"map_name": "MapA"},
        "game_result": {"result": "Defeat"},
        "expansions": [{"expansion_number": 1, "time": 80.0}],
        "tech_upgrades": [{"building": "SPAWNING_POOL", "time": 40.0}],
    }
    # Sample game 3: Victory on MapB
    game3 = {
        "meta": {"map_name": "MapB"},
        "game_result": {"result": "Victory"},
        "expansions": [{"expansion_number": 1, "time": 70.0}],
        "tech_upgrades": [],
    }

    for i, game in enumerate([game1, game2, game3], 1):
        with open(os.path.join(tmpdir, f"game_{i}.json"), "w") as f:
            json.dump(game, f)

    yield tmpdir
    shutil.rmtree(tmpdir)


class TestInitialization:
    def test_default_paths(self):
        ku = KnowledgeUpdater()
        assert ku.games_dir == "data/games"
        assert ku.knowledge_file == "commander_knowledge.json"

    def test_initial_games_empty(self):
        ku = KnowledgeUpdater()
        assert ku.games_data == []


class TestLoadAllGames:
    def test_loads_all_json_files(self, temp_games_dir):
        ku = KnowledgeUpdater(games_dir=temp_games_dir)
        ku.load_all_games()
        assert len(ku.games_data) == 3

    def test_missing_dir_handled_gracefully(self):
        ku = KnowledgeUpdater(games_dir="/nonexistent_dir_xyz")
        ku.load_all_games()
        assert ku.games_data == []

    def test_skips_non_json_files(self):
        tmpdir = tempfile.mkdtemp()
        try:
            # Create non-JSON and JSON files
            with open(os.path.join(tmpdir, "not_json.txt"), "w") as f:
                f.write("hello")
            with open(os.path.join(tmpdir, "game.json"), "w") as f:
                json.dump({"meta": {"map_name": "Test"}, "game_result": {"result": "Victory"}}, f)

            ku = KnowledgeUpdater(games_dir=tmpdir)
            ku.load_all_games()
            assert len(ku.games_data) == 1
        finally:
            shutil.rmtree(tmpdir)


class TestMapWinrates:
    def test_winrate_calculation(self, temp_games_dir):
        ku = KnowledgeUpdater(games_dir=temp_games_dir)
        ku.load_all_games()
        result = ku._analyze_map_winrates()

        assert "MapA" in result
        assert "MapB" in result

        # MapA: 1 win, 1 loss = 50% winrate
        assert result["MapA"]["games"] == 2
        assert result["MapA"]["wins"] == 1
        assert result["MapA"]["losses"] == 1
        assert result["MapA"]["winrate"] == 50.0

        # MapB: 1 win, 0 loss = 100% winrate
        assert result["MapB"]["winrate"] == 100.0

    def test_empty_data_returns_empty(self):
        ku = KnowledgeUpdater()
        result = ku._analyze_map_winrates()
        assert result == {}


class TestTimingAnalysis:
    def test_expansion_timing_averages(self, temp_games_dir):
        ku = KnowledgeUpdater(games_dir=temp_games_dir)
        ku.load_all_games()
        result = ku._analyze_timings()

        assert "expansion_avg" in result
        assert "base_1" in result["expansion_avg"]

        # base_1 times: 60.0, 80.0, 70.0 → avg = 70.0
        base1 = result["expansion_avg"]["base_1"]
        assert abs(base1["avg"] - 70.0) < 0.1
        assert base1["min"] == 60.0
        assert base1["max"] == 80.0
        assert base1["samples"] == 3

    def test_tech_timing_analysis(self, temp_games_dir):
        ku = KnowledgeUpdater(games_dir=temp_games_dir)
        ku.load_all_games()
        result = ku._analyze_timings()

        assert "tech_avg" in result
        assert "SPAWNING_POOL" in result["tech_avg"]

        # Two SPAWNING_POOL times: 30.0, 40.0 → avg = 35.0
        sp = result["tech_avg"]["SPAWNING_POOL"]
        assert abs(sp["avg"] - 35.0) < 0.1


class TestLoadSaveKnowledge:
    def test_save_and_reload(self, temp_games_dir):
        with tempfile.NamedTemporaryFile(suffix=".json", delete=False) as f:
            kfile = f.name
        try:
            os.unlink(kfile)
            ku = KnowledgeUpdater(games_dir=temp_games_dir, knowledge_file=kfile)
            data = {"test": "value"}
            ku._save_knowledge(data)

            loaded = ku._load_knowledge()
            assert loaded == {"test": "value"}
        finally:
            if os.path.exists(kfile):
                os.unlink(kfile)

    def test_load_missing_returns_empty_dict(self):
        ku = KnowledgeUpdater(knowledge_file="/tmp/does_not_exist_xyz.json")
        result = ku._load_knowledge()
        assert result == {}


class TestAnalyzeAndUpdate:
    def test_runs_without_error_on_empty_data(self):
        with tempfile.NamedTemporaryFile(suffix=".json", delete=False) as f:
            kfile = f.name
        try:
            os.unlink(kfile)
            ku = KnowledgeUpdater(games_dir="/nonexistent", knowledge_file=kfile)
            ku.analyze_and_update()  # should not raise
        finally:
            if os.path.exists(kfile):
                os.unlink(kfile)
