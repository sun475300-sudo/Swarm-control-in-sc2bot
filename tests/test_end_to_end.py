"""
End-to-end integration tests.
"""

from src.bot.agents.basic_zerg_agent import BasicZergAgent
from src.sc2_env.mock_env import MockSC2Env


def test_end_to_end_loop():
    """Test complete agent-environment interaction loop."""
    env = MockSC2Env()
    agent = BasicZergAgent()
    
    obs = env.reset()
    assert obs["step"] == 0
    
    for i in range(5):
        action = agent.on_step(obs)
        assert isinstance(action, str)
        obs = env.step(action)
        assert obs["step"] == i + 1
    
    assert obs["step"] == 5


def test_end_to_end_with_resources():
    """Test end-to-end with resource management."""
    env = MockSC2Env(initial_minerals=200)
    agent = BasicZergAgent()
    
    obs = env.reset()
    initial_minerals = obs["minerals"]
    
    # Run several steps
    for _ in range(10):
        action = agent.on_step(obs)
        obs = env.step(action)
    
    # Should have spent some resources
    assert obs["minerals"] != initial_minerals or obs["food_used"] > obs.get("food_used", 0)


def test_end_to_end_strategy_changes():
    """Test that strategy changes based on game state."""
    env = MockSC2Env()
    agent = BasicZergAgent()
    
    obs = env.reset()
    
    # Initially should focus on economy
    action1 = agent.on_step(obs)
    obs = env.step(action1)
    
    # After accumulating resources, should build army or expand
    obs["minerals"] = 400  # Force high minerals
    action2 = agent.on_step(obs)
    
    # Should not be waiting when resources are high
    assert action2 != "wait" or obs["food_used"] >= obs["food_cap"] * 0.9
