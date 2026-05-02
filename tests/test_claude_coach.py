"""
Tests for claude_api_coach.sc2_claude_coach.

Focus on pure-Python parts that don't require an Anthropic API key:
- GameState dataclass
- GameStateSerializer text output
- StrategyPromptBuilder
- ChatMessage / CoachingSession history management
"""

import os
import sys

import pytest

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

# numpy is a hard dependency of the module
np = pytest.importorskip("numpy")

from claude_api_coach.sc2_claude_coach import (  # noqa: E402
    ChatMessage,
    CoachingSession,
    CoachingTopic,
    GamePhase,
    GameState,
    GameStateSerializer,
    Matchup,
    StrategyPromptBuilder,
)


class TestGameState:
    def test_default_values(self):
        s = GameState()
        assert s.matchup == Matchup.ZvT
        assert s.supply_used == 0
        assert s.supply_cap == 200
        assert s.army_comp == {}

    def test_custom_values(self):
        s = GameState(
            game_time_seconds=300,
            minerals=500,
            army_comp={"Zergling": 12},
        )
        assert s.minerals == 500
        assert s.army_comp["Zergling"] == 12


class TestGameStateSerializer:
    def setup_method(self):
        self.serializer = GameStateSerializer()

    def test_serialize_includes_basics(self):
        s = GameState(
            game_time_seconds=185,
            supply_used=40,
            supply_cap=44,
            minerals=300,
            vespene=150,
            worker_count=22,
            army_supply=10,
            base_count=2,
        )
        text = self.serializer.serialize(s)
        assert "03:05" in text  # 185s = 3:05
        assert "ZvT" in text
        assert "40/44" in text
        assert "300 minerals" in text
        assert "150 gas" in text

    def test_serialize_phase_detection(self):
        # Should detect MID phase at 6+ minutes
        s = GameState(game_time_seconds=400)
        text = self.serializer.serialize(s)
        assert GamePhase.MID.name in text

    def test_serialize_includes_army(self):
        s = GameState(army_comp={"Zergling": 16, "Roach": 8})
        text = self.serializer.serialize(s)
        assert "Zergling: 16" in text
        assert "Roach: 8" in text

    def test_serialize_includes_creep_percentage(self):
        s = GameState(creep_coverage=0.42)
        text = self.serializer.serialize(s)
        assert "42%" in text


class TestStrategyPromptBuilder:
    def setup_method(self):
        self.builder = StrategyPromptBuilder()

    def test_builder_can_be_instantiated(self):
        assert self.builder is not None


class TestChatMessage:
    def test_default_timestamp_is_set(self):
        m = ChatMessage(role="user", content="hi")
        assert m.timestamp > 0
        assert m.role == "user"
        assert m.topic is None


class TestCoachingSession:
    def test_starts_empty(self):
        s = CoachingSession()
        assert len(s.messages) == 0
        assert s.matchup is None

    def test_add_user_message(self):
        s = CoachingSession()
        s.add_user_message("hello", topic=CoachingTopic.OPENING_ANALYSIS)
        assert len(s.messages) == 1
        assert s.messages[0].role == "user"
        assert s.messages[0].topic == CoachingTopic.OPENING_ANALYSIS

    def test_add_assistant_message(self):
        s = CoachingSession()
        s.add_assistant_message("response")
        assert s.messages[-1].role == "assistant"

    def test_history_trimmed_to_max(self):
        s = CoachingSession(max_history=3)
        for i in range(5):
            s.add_user_message(f"msg {i}")
        assert len(s.messages) == 3
        assert "msg 4" in s.messages[-1].content

    def test_to_api_messages_format(self):
        s = CoachingSession()
        s.add_user_message("q1")
        s.add_assistant_message("a1")
        api = s.to_api_messages()
        assert api == [
            {"role": "user", "content": "q1"},
            {"role": "assistant", "content": "a1"},
        ]

    def test_get_context_summary_empty(self):
        s = CoachingSession()
        assert "No conversation" in s.get_context_summary()

    def test_get_context_summary_with_topics(self):
        s = CoachingSession()
        s.add_user_message("q1", topic=CoachingTopic.ECONOMY_CHECK)
        s.add_user_message("q2", topic=CoachingTopic.SCOUTING_INFO)
        summary = s.get_context_summary()
        assert "2 messages" in summary
        assert "economy_check" in summary
        assert "scouting_info" in summary

    def test_clear_removes_all_messages(self):
        s = CoachingSession()
        s.add_user_message("a")
        s.add_assistant_message("b")
        s.clear()
        assert len(s.messages) == 0
