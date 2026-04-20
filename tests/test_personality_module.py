# -*- coding: utf-8 -*-
"""Tests for personality_module.py — chat personality & phase logic."""

import sys
import pytest

sys.path.insert(0, "wicked_zerg_challenger")

from personality_module import PersonalityModule, PersonalityMode, GamePhase


class _FakeBot:
    def __init__(self, supply_used=0):
        self.supply_used = supply_used
        self.workers = type("W", (), {"amount": 10})()


class TestPersonalityModeEnum:
    def test_all_modes_exist(self):
        assert PersonalityMode.POLITE
        assert PersonalityMode.NEUTRAL
        assert PersonalityMode.COCKY
        assert PersonalityMode.SILENT

    def test_mode_values(self):
        assert PersonalityMode.POLITE.value == "polite"
        assert PersonalityMode.COCKY.value == "cocky"


class TestGamePhaseEnum:
    def test_all_phases_exist(self):
        assert GamePhase.OPENING
        assert GamePhase.EARLY
        assert GamePhase.MID
        assert GamePhase.LATE
        assert GamePhase.ENDING


class TestInitialization:
    def test_default_mode_neutral(self):
        pm = PersonalityModule(bot=_FakeBot())
        assert pm.mode == PersonalityMode.NEUTRAL

    def test_custom_mode(self):
        pm = PersonalityModule(bot=_FakeBot(), mode=PersonalityMode.COCKY)
        assert pm.mode == PersonalityMode.COCKY

    def test_state_flags_initial(self):
        pm = PersonalityModule(bot=_FakeBot())
        assert not pm.game_start_greeted
        assert not pm.good_game_sent
        assert not pm.victory_declared
        assert pm.taunt_count == 0

    def test_messages_database_populated(self):
        pm = PersonalityModule(bot=_FakeBot())
        # _init_messages should populate self.messages
        assert hasattr(pm, "messages")
        assert isinstance(pm.messages, dict)


class TestReset:
    def test_reset_clears_state(self):
        pm = PersonalityModule(bot=_FakeBot())
        pm.game_start_greeted = True
        pm.good_game_sent = True
        pm.victory_declared = True
        pm.messages_sent.append("test")

        pm.reset()

        assert not pm.game_start_greeted
        assert not pm.good_game_sent
        assert not pm.victory_declared


class TestGamePhaseDetection:
    def setup_method(self):
        self.pm = PersonalityModule(bot=_FakeBot())

    def test_opening_phase(self):
        assert self.pm._get_game_phase(100.0) == GamePhase.OPENING

    def test_early_phase(self):
        assert self.pm._get_game_phase(400.0) == GamePhase.EARLY

    def test_mid_phase(self):
        assert self.pm._get_game_phase(700.0) == GamePhase.MID

    def test_late_phase(self):
        assert self.pm._get_game_phase(1000.0) == GamePhase.LATE

    def test_boundary_openning_early(self):
        # 300s is the boundary
        assert self.pm._get_game_phase(299.0) == GamePhase.OPENING
        assert self.pm._get_game_phase(300.0) == GamePhase.EARLY


class TestSetMode:
    def test_set_mode_updates(self):
        pm = PersonalityModule(bot=_FakeBot())
        pm.set_mode(PersonalityMode.COCKY)
        assert pm.mode == PersonalityMode.COCKY


class TestRandomMessage:
    def test_unknown_category_returns_none(self):
        pm = PersonalityModule(bot=_FakeBot())
        assert pm._get_random_message("nonexistent_category") is None

    def test_known_category_returns_string(self):
        pm = PersonalityModule(bot=_FakeBot(), mode=PersonalityMode.NEUTRAL)
        # Try common categories that should exist
        for category in pm.messages.keys():
            result = pm._get_random_message(category)
            # Either None (no messages for this mode) or a string
            assert result is None or isinstance(result, str)


class TestIsAhead:
    def test_equal_supply_not_ahead(self):
        bot = _FakeBot(supply_used=30)
        pm = PersonalityModule(bot=bot)
        # Without intel, no opponent reference → not ahead
        assert not pm._is_ahead()

    def test_ahead_with_intel(self):
        bot = _FakeBot(supply_used=60)
        bot.intel = type("I", (), {"enemy_army_supply": 10})()
        pm = PersonalityModule(bot=bot)
        # our_army = 60 - 10 (workers) = 50; enemy = 10; 50 > 10 * 1.3
        assert pm._is_ahead()


class TestStatistics:
    def test_get_statistics_returns_dict(self):
        pm = PersonalityModule(bot=_FakeBot())
        stats = pm.get_statistics()
        assert isinstance(stats, dict)

    def test_stats_includes_message_count(self):
        pm = PersonalityModule(bot=_FakeBot())
        pm.messages_sent.append("hi")
        pm.messages_sent.append("hello")
        stats = pm.get_statistics()
        # Either 'messages_sent' or similar key
        any_value = list(stats.values())
        # At least one entry should reflect the count
        assert 2 in any_value or any(v == 2 for v in any_value if isinstance(v, int))
