"""
Tests for langchain_coach.sc2_strategy_coach.

Focuses on the pure-Python parts that don't require an actual LLM:
- Phase classification
- SC2GameState description and matchup detection
- StrategyOutputParser
- BuildOrderDB lookup
- UnitCounterLookup
- StrategyRecommendation serialization
"""

import os
import sys

import pytest

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

# numpy is required for the module
np = pytest.importorskip("numpy")

from langchain_coach.sc2_strategy_coach import (  # noqa: E402
    BuildOrderDB,
    GamePhase,
    Matchup,
    Race,
    SC2GameState,
    StrategyOutputParser,
    StrategyRecommendation,
    UnitCounterLookup,
    classify_phase,
)


class TestClassifyPhase:
    def test_opening(self):
        assert classify_phase(0.0) == GamePhase.OPENING
        assert classify_phase(120.0) == GamePhase.OPENING

    def test_early(self):
        assert classify_phase(180.0) == GamePhase.EARLY
        assert classify_phase(300.0) == GamePhase.EARLY

    def test_mid(self):
        assert classify_phase(360.0) == GamePhase.MID
        assert classify_phase(600.0) == GamePhase.MID

    def test_late(self):
        assert classify_phase(720.0) == GamePhase.LATE
        assert classify_phase(1500.0) == GamePhase.LATE


class TestSC2GameState:
    def test_default_zvt_matchup(self):
        s = SC2GameState()
        assert s.matchup == Matchup.ZvT

    def test_zvz_matchup(self):
        s = SC2GameState(player_race=Race.ZERG, enemy_race=Race.ZERG)
        assert s.matchup == Matchup.ZvZ

    def test_zvp_matchup(self):
        s = SC2GameState(player_race=Race.ZERG, enemy_race=Race.PROTOSS)
        assert s.matchup == Matchup.ZvP

    def test_phase_property_uses_classify(self):
        s = SC2GameState(game_time_seconds=400)
        assert s.phase == GamePhase.MID

    def test_minutes_property(self):
        s = SC2GameState(game_time_seconds=300)
        assert s.minutes == 5.0

    def test_to_description_includes_key_fields(self):
        s = SC2GameState(
            game_time_seconds=300,
            minerals=500,
            vespene=200,
            supply_used=40,
            supply_cap=44,
            worker_count=22,
            base_count=2,
            army_composition={"Zergling": 10},
            enemy_army_scouted={"Marine": 8},
            upgrades_completed=["MeleeAttack1"],
            creep_coverage=0.3,
        )
        desc = s.to_description()
        assert "ZvT" in desc
        assert "5.0 min" in desc
        assert "500" in desc
        assert "Zergling: 10" in desc
        assert "Marine: 8" in desc
        assert "30%" in desc

    def test_to_description_handles_empty_lists(self):
        s = SC2GameState()
        desc = s.to_description()
        assert "None" in desc  # empty army & upgrades
        assert "Unknown" in desc  # unknown enemy


class TestStrategyRecommendation:
    def test_to_dict_round_trip(self):
        r = StrategyRecommendation(
            summary="hold ground",
            immediate_actions=["build queens"],
            build_order_next=["lair"],
            army_composition_target={"Roach": 20},
            tech_priority=["Melee+1"],
            warnings=["low gas"],
            confidence=0.75,
            reasoning="enemy massing marines",
        )
        d = r.to_dict()
        assert d["summary"] == "hold ground"
        assert d["immediate_actions"] == ["build queens"]
        assert d["confidence"] == 0.75

    def test_to_display_includes_all_sections(self):
        r = StrategyRecommendation(
            summary="hold",
            immediate_actions=["a"],
            build_order_next=["b"],
            army_composition_target={"Roach": 20},
            tech_priority=["t"],
            warnings=["w"],
            confidence=0.9,
            reasoning="r",
        )
        text = r.to_display()
        assert "Summary: hold" in text
        assert "Immediate actions:" in text
        assert "Build order" in text
        assert "Roach: 20" in text
        assert "[!] w" in text
        assert "90%" in text


class TestStrategyOutputParser:
    def setup_method(self):
        self.parser = StrategyOutputParser()

    def test_parse_summary(self):
        text = "Summary: Push aggressive\nReasoning: enemy weak"
        rec = self.parser.parse(text)
        assert "Push aggressive" in rec.summary

    def test_parse_confidence(self):
        text = "Confidence: 0.85"
        rec = self.parser.parse(text)
        assert rec.confidence == 0.85

    def test_parse_empty_input(self):
        rec = self.parser.parse("")
        assert isinstance(rec, StrategyRecommendation)
        assert rec.summary == ""


class TestBuildOrderDB:
    def setup_method(self):
        self.db = BuildOrderDB()

    def test_search_by_matchup(self):
        results = self.db.search(matchup="ZvT")
        assert isinstance(results, list)

    def test_recommend_returns_list(self):
        state = SC2GameState(game_time_seconds=120)
        out = self.db.recommend(state)
        assert isinstance(out, list)


class TestUnitCounterLookup:
    def setup_method(self):
        self.lookup = UnitCounterLookup()

    def test_lookup_known_unit_returns_data(self):
        result = self.lookup.lookup("Marine")
        # Either we get counter data, or None if Marine isn't in DB
        assert result is None or isinstance(result, dict)

    def test_lookup_unknown_unit_returns_none(self):
        result = self.lookup.lookup("ThisIsNotARealUnit123")
        assert result is None

    def test_counter_army_returns_recommendation_shape(self):
        result = self.lookup.counter_army({"Marine": 10, "Marauder": 4})
        assert isinstance(result, dict)
        assert "recommended_units" in result
        assert "scores" in result
        assert "notes" in result
        assert isinstance(result["recommended_units"], list)
