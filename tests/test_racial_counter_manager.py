# -*- coding: utf-8 -*-
"""Tests for RacialCounterManager unit-ratio counter logic."""

import sys
import pytest

sys.path.insert(0, "wicked_zerg_challenger")

from racial_counter_manager import RacialCounterManager


class _FakeBot:
    def __init__(self):
        self.intel = None


class TestStaticHelpers:
    def test_set_boost_only(self):
        ratios = {"roach": 0.1}
        RacialCounterManager._set(ratios, "roach", 0.5)
        assert ratios["roach"] == 0.5

    def test_set_does_not_reduce(self):
        ratios = {"roach": 0.8}
        RacialCounterManager._set(ratios, "roach", 0.3)
        assert ratios["roach"] == 0.8

    def test_set_adds_missing_unit(self):
        ratios = {}
        RacialCounterManager._set(ratios, "baneling", 0.25)
        assert ratios["baneling"] == 0.25

    def test_normalize_sums_to_one(self):
        ratios = {"a": 1.0, "b": 2.0, "c": 1.0}
        normalized = RacialCounterManager._normalize(ratios)
        assert abs(sum(normalized.values()) - 1.0) < 1e-9

    def test_normalize_empty_returns_empty(self):
        result = RacialCounterManager._normalize({})
        assert result == {}

    def test_normalize_zero_total_returns_original(self):
        ratios = {"a": 0.0, "b": 0.0}
        result = RacialCounterManager._normalize(ratios)
        assert result == ratios


class TestLogOnce:
    def setup_method(self):
        self.mgr = RacialCounterManager(_FakeBot())

    def test_log_only_once(self):
        self.mgr._log_once("key1", 400.0, 300.0, "msg")
        self.mgr._log_once("key1", 500.0, 300.0, "msg")
        assert self.mgr._log_flags["key1"] is True

    def test_log_skipped_if_too_early(self):
        self.mgr._log_once("key2", 200.0, 300.0, "msg")
        assert "key2" not in self.mgr._log_flags


class TestCounterTerranBio:
    def setup_method(self):
        self.mgr = RacialCounterManager(_FakeBot())

    def test_bio_rush_boosts_baneling(self):
        comp = {"MARINE": 10, "MARAUDER": 2}
        ratios = self.mgr._counter_terran(200.0, comp, {})
        assert ratios.get("baneling", 0) >= 0.25
        assert ratios.get("zergling", 0) >= 0.30

    def test_medivac_drop_triggers_bio_counter(self):
        comp = {"MARINE": 4, "MEDIVAC": 2}
        ratios = self.mgr._counter_terran(200.0, comp, {})
        assert ratios.get("baneling", 0) >= 0.25

    def test_no_bio_threat_no_boost(self):
        comp = {"MARINE": 2}
        ratios = self.mgr._counter_terran(200.0, comp, {})
        assert ratios.get("baneling", 0) == 0


class TestCounterTerranMech:
    def test_tank_push_triggers_ravager(self):
        mgr = RacialCounterManager(_FakeBot())
        comp = {"SIEGETANK": 3}
        ratios = mgr._counter_terran(300.0, comp, {})
        assert ratios.get("ravager", 0) >= 0.30

    def test_thor_triggers_ravager(self):
        mgr = RacialCounterManager(_FakeBot())
        comp = {"THOR": 1}
        ratios = mgr._counter_terran(300.0, comp, {})
        assert ratios.get("ravager", 0) >= 0.30


class TestCounterTerranAir:
    def test_banshee_triggers_hydra(self):
        mgr = RacialCounterManager(_FakeBot())
        comp = {"BANSHEE": 2}
        ratios = mgr._counter_terran(300.0, comp, {})
        assert ratios.get("hydralisk", 0) >= 0.35
        assert ratios.get("corruptor", 0) >= 0.25

    def test_battlecruiser_triggers_anti_air(self):
        mgr = RacialCounterManager(_FakeBot())
        comp = {"BATTLECRUISER": 1}
        ratios = mgr._counter_terran(400.0, comp, {})
        assert ratios.get("hydralisk", 0) >= 0.35


class TestHellionRush:
    def test_hellion_rush_early(self):
        mgr = RacialCounterManager(_FakeBot())
        comp = {"HELLION": 4}
        ratios = mgr._counter_terran(150.0, comp, {})
        assert ratios.get("queen", 0) >= 0.20
        assert ratios.get("roach", 0) >= 0.40

    def test_hellion_late_game_no_rush_counter(self):
        mgr = RacialCounterManager(_FakeBot())
        comp = {"HELLION": 4}
        ratios = mgr._counter_terran(500.0, comp, {})
        # No hellion rush response after 300s (only applies early)
        # Verify queen wasn't boosted to rush-defense level
        assert ratios.get("roach", 0) != 0.40 or ratios.get("queen", 0) != 0.20


class TestUpdateMethod:
    def test_update_returns_normalized_dict(self):
        mgr = RacialCounterManager(_FakeBot())
        result = mgr.update("Terran", "MID", 400.0, {"MARINE": 10}, {})
        assert isinstance(result, dict)
        if sum(result.values()) > 0:
            assert abs(sum(result.values()) - 1.0) < 1e-9

    def test_update_unknown_race_does_not_crash(self):
        mgr = RacialCounterManager(_FakeBot())
        result = mgr.update("Unknown", "EARLY", 100.0, {}, {"roach": 0.5})
        assert isinstance(result, dict)
