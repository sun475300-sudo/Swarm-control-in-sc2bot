"""
Test Scenario 12 - Auto-generated test.
"""

from src.bot.agents.basic_zerg_agent import BasicZergAgent
from src.sc2_env.mock_env import MockSC2Env


def test_scenario_12():
    """Test scenario 12 execution."""
    env = MockSC2Env(initial_minerals=160)
    agent = BasicZergAgent()
    
    obs = env.reset()
    initial_minerals = obs["minerals"]
    
    # Run simulation
    for _ in range(5):
        action = agent.on_step(obs)
        assert isinstance(action, str)
        obs = env.step(action)
    
    # Verify final state
    assert obs["step"] == 5
    assert obs["minerals"] >= 0  # Should not go negative
    assert obs["food_used"] <= obs["food_cap"]  # Supply should be valid
