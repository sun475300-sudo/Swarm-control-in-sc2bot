"""
Tests for mock SC2 environment.
These tests verify that the mock environment works correctly
without requiring actual StarCraft II installation.
"""

import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root / "wicked_zerg_challenger"))

from sc2_env.mock_env import MockSC2Env, MockBotAI, MockGameState, Race


def test_mock_env_init():
    """Test mock environment initialization."""
    env = MockSC2Env()
    assert env is not None
    assert env.state.minerals == 50
    assert env.state.supply_used == 6


def test_mock_env_reset():
    """Test environment reset."""
    env = MockSC2Env()
    env.state.minerals = 100
    state = env.reset()
    
    assert state["minerals"] == 50
    assert state["supply_used"] == 6


def test_mock_env_step_train_drone():
    """Test training a drone in mock environment."""
    env = MockSC2Env(initial_minerals=100)
    state = env.reset()
    
    initial_minerals = state["minerals"]
    initial_workers = state["worker_count"]
    initial_supply = state["supply_used"]
    
    # Train a drone
    new_state = env.step("train_drone")
    
    assert new_state["minerals"] == initial_minerals - 50
    assert new_state["worker_count"] == initial_workers + 1
    assert new_state["supply_used"] == initial_supply + 1


def test_mock_env_step_insufficient_resources():
    """Test that actions fail when resources are insufficient."""
    env = MockSC2Env(initial_minerals=25)
    state = env.reset()
    
    initial_minerals = state["minerals"]
    initial_workers = state["worker_count"]
    
    # Try to train drone (costs 50, but only have 25)
    new_state = env.step("train_drone")
    
    assert new_state["minerals"] == initial_minerals
    assert new_state["worker_count"] == initial_workers


def test_mock_env_step_supply_block():
    """Test that training is blocked when supply is full."""
    env = MockSC2Env()
    env.state.supply_used = 14
    env.state.supply_cap = 15
    
    state = env._state_to_dict()
    initial_army = state["army_count"]
    
    # Try to train zergling (needs 2 supply, but only 1 left)
    new_state = env.step("train_zergling")
    
    assert new_state["army_count"] == initial_army


def test_mock_env_can_afford():
    """Test can_afford method."""
    env = MockSC2Env(initial_minerals=100)
    
    assert env.can_afford(50, 0) is True
    assert env.can_afford(100, 0) is True
    assert env.can_afford(150, 0) is False
    assert env.can_afford(50, 50) is False  # No vespene


def test_mock_env_supply_calculation():
    """Test supply calculation."""
    env = MockSC2Env()
    
    assert env.get_supply_left() == 9  # 15 - 6
    
    env.state.supply_used = 15
    assert env.get_supply_left() == 0


def test_mock_bot_ai_init():
    """Test MockBotAI initialization."""
    bot = MockBotAI()
    assert bot is not None
    assert bot.minerals == 50.0
    assert bot.supply_used == 6


def test_mock_bot_ai_can_afford():
    """Test MockBotAI can_afford method."""
    bot = MockBotAI()
    bot.env.state.minerals = 100
    
    assert bot.can_afford("drone") is True
    assert bot.can_afford("zergling") is True
    assert bot.can_afford("extractor") is True
    
    bot.env.state.minerals = 25
    assert bot.can_afford("drone") is False
    assert bot.can_afford("extractor") is True


def test_mock_bot_ai_properties():
    """Test MockBotAI properties."""
    bot = MockBotAI()
    
    assert isinstance(bot.minerals, float)
    assert isinstance(bot.vespene, float)
    assert isinstance(bot.supply_used, int)
    assert isinstance(bot.supply_cap, int)
    assert isinstance(bot.supply_left, int)
    assert bot.supply_left >= 0


def test_mock_game_state_advancement():
    """Test that game state advances with steps."""
    env = MockSC2Env()
    state1 = env.reset()
    
    state2 = env.step("train_drone")
    state3 = env.step("train_drone")
    
    assert state3["game_time"] > state2["game_time"]
    assert state3["iteration"] > state2["iteration"]
    assert state2["game_time"] > state1["game_time"]
    assert state2["iteration"] > state1["iteration"]
