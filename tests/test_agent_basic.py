"""
Basic agent tests.
"""

from src.bot.agents.basic_zerg_agent import BasicZergAgent
from src.bot.agents.base_agent import BaseAgent


def test_agent_init():
    """Test agent initialization."""
    agent = BasicZergAgent()
    assert agent is not None
    assert isinstance(agent, BaseAgent)


def test_agent_returns_action():
    """Test that agent returns valid action."""
    agent = BasicZergAgent()
    obs = {"minerals": 100, "food_used": 10, "food_cap": 20, "gas": 0}
    action = agent.on_step(obs)
    assert isinstance(action, str)
    assert action in {
        "train_drone",
        "train_zergling",
        "train_roach",
        "train_queen",
        "build_spine",
        "expand",
        "attack_move",
        "wait"
    }


def test_agent_reset():
    """Test agent reset functionality."""
    agent = BasicZergAgent()
    agent.reset()
    assert agent.intel is not None
    assert agent.strategy is not None


def test_agent_with_different_observations():
    """Test agent with various observation states."""
    agent = BasicZergAgent()
    
    # Low resources
    obs_low = {"minerals": 30, "food_used": 10, "food_cap": 20, "gas": 0}
    action_low = agent.on_step(obs_low)
    assert action_low in {"wait", "train_drone"}  # Should wait or train drone
    
    # High resources
    obs_high = {"minerals": 500, "food_used": 10, "food_cap": 50, "gas": 200}
    action_high = agent.on_step(obs_high)
    assert action_high in {"train_zergling", "train_roach", "expand", "army"}
