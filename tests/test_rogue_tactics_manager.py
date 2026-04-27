# -*- coding: utf-8 -*-
"""Tests for RogueTacticsManager state and configuration."""

import sys
import pytest

sys.path.insert(0, "wicked_zerg_challenger")

from rogue_tactics_manager import RogueTacticsManager


class _FakeBot:
    time = 0.0


class TestInitialization:
    def test_instantiate(self):
        mgr = RogueTacticsManager(_FakeBot())
        assert mgr.bot is not None

    def test_drop_cooldown_defaults(self):
        mgr = RogueTacticsManager(_FakeBot())
        assert mgr._drop_cooldown_duration == 60
        assert mgr._drop_cooldown == 0
        assert mgr._last_drop_time == 0
        assert not mgr._drop_in_progress

    def test_drop_overlords_set_empty(self):
        mgr = RogueTacticsManager(_FakeBot())
        assert isinstance(mgr._drop_overlords, set)
        assert len(mgr._drop_overlords) == 0


class TestLarvaSaving:
    def test_larva_saving_disabled_by_default(self):
        mgr = RogueTacticsManager(_FakeBot())
        assert not mgr._larva_saving_mode

    def test_larva_save_duration_configured(self):
        mgr = RogueTacticsManager(_FakeBot())
        assert mgr._larva_save_duration == 30

    def test_min_larva_threshold(self):
        mgr = RogueTacticsManager(_FakeBot())
        assert mgr._min_larva_for_burst == 10


class TestEnemyCreepDetection:
    def test_enemy_not_on_creep_initially(self):
        mgr = RogueTacticsManager(_FakeBot())
        assert not mgr._enemy_on_creep
        assert mgr._enemy_creep_position is None
        assert not mgr._enemy_advancing


class TestCacheInvalidation:
    def test_drop_target_cache_empty_initially(self):
        mgr = RogueTacticsManager(_FakeBot())
        assert mgr._cached_drop_target is None
        assert mgr._drop_target_update_time == 0

    def test_stealth_path_cache_empty_initially(self):
        mgr = RogueTacticsManager(_FakeBot())
        assert mgr._stealth_path_cache is None
        assert mgr._stealth_path_update_time == 0


class TestDropState:
    def test_drop_overlords_can_add_and_remove(self):
        mgr = RogueTacticsManager(_FakeBot())
        mgr._drop_overlords.add(101)
        mgr._drop_overlords.add(102)
        assert len(mgr._drop_overlords) == 2

        mgr._drop_overlords.discard(101)
        assert len(mgr._drop_overlords) == 1
        assert 102 in mgr._drop_overlords
