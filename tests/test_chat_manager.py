# -*- coding: utf-8 -*-
"""Tests for ChatManager chat message handling."""

import sys
import pytest

sys.path.insert(0, "wicked_zerg_challenger")

from chat_manager import ChatManager


class _FakeBot:
    def __init__(self, time=0.0):
        self.time = time
        self.sent_messages = []

    def chat_send(self, msg):
        self.sent_messages.append(msg)


class TestInitialization:
    def test_instantiate_without_bot(self):
        cm = ChatManager()
        assert cm.bot is None
        assert cm.cooldown > 0

    def test_default_messages_loaded(self):
        cm = ChatManager()
        assert "greeting" in cm.messages
        assert "gg" in cm.messages
        assert "attack" in cm.messages

    def test_custom_messages_override_defaults(self):
        custom = {"hello": ["Hi there"]}
        cm = ChatManager(messages=custom)
        assert "hello" in cm.messages
        assert "greeting" not in cm.messages


class TestSending:
    def setup_method(self):
        self.bot = _FakeBot(time=0.0)
        self.cm = ChatManager(bot=self.bot, cooldown=5.0)

    def test_send_delivers_message(self):
        assert self.cm.send("greeting")
        assert len(self.bot.sent_messages) == 1

    def test_send_respects_cooldown(self):
        self.cm.send("attack")
        # Second call immediately should be blocked
        assert not self.cm.send("attack")

    def test_send_after_cooldown_passes(self):
        self.cm.send("attack")
        self.bot.time = 100.0
        assert self.cm.send("attack")

    def test_force_bypasses_cooldown(self):
        self.cm.send("attack")
        assert self.cm.send("attack", force=True)

    def test_unknown_category_returns_false(self):
        assert not self.cm.send("nonexistent_category")

    def test_stats_tracks_sends(self):
        self.cm.send("greeting")
        self.cm.send("attack")
        assert self.cm.stats["sent"] == 2


class TestGreeting:
    def test_greet_sends_once(self):
        bot = _FakeBot()
        cm = ChatManager(bot=bot)
        assert cm.greet()
        assert not cm.greet()  # second call blocked

    def test_greet_sends_greeting_message(self):
        bot = _FakeBot()
        cm = ChatManager(bot=bot)
        cm.greet()
        assert bot.sent_messages[0] in cm.messages["greeting"]


class TestGG:
    def test_say_gg_sends_message(self):
        bot = _FakeBot()
        cm = ChatManager(bot=bot)
        assert cm.say_gg()
        assert bot.sent_messages[0] in cm.messages["gg"]


class TestAddMessage:
    def test_add_to_existing_category(self):
        cm = ChatManager()
        cm.add_message("greeting", "Howdy")
        assert "Howdy" in cm.messages["greeting"]

    def test_add_to_new_category(self):
        cm = ChatManager()
        cm.add_message("taunts", "You shall not pass")
        assert cm.messages["taunts"] == ["You shall not pass"]


class TestNoBot:
    def test_send_without_bot_still_records(self):
        cm = ChatManager()
        # No bot; send should still return True and update stats
        assert cm.send("greeting")
        assert cm.stats["sent"] == 1


class TestBotWithoutChatSend:
    def test_bot_without_chat_send_does_not_crash(self):
        class DummyBot:
            time = 0.0

        cm = ChatManager(bot=DummyBot())
        assert cm.send("greeting")  # returns True without crashing
