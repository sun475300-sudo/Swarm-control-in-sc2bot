"""
Test Scenario 18 - Auto-generated test.
"""

from src.bot.agents.basic_zerg_agent import BasicZergAgent
from src.sc2_env.mock_env import MockSC2Env


def test_scenario_18():
    """Test scenario 18 execution."""
    env = MockSC2Env(initial_minerals=190)
    agent = BasicZergAgent()
    
    obs = env.reset()
    initial_minerals = obs["minerals"]
    
    # Run simulation
    for _ in range(6):
        action = agent.on_step(obs)
        assert isinstance(action, str)
        obs = env.step(action)
    
    # Verify final state
    assert obs["step"] == 6
    assert obs["minerals"] >= 0  # Should not go negative
    assert obs["food_used"] <= obs["food_cap"]  # Supply should be valid
