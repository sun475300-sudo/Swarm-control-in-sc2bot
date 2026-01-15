"""
Scenario 13 - Auto-generated execution script.
This script demonstrates running the bot in scenario 13.
"""

from src.bot.agents.basic_zerg_agent import BasicZergAgent
from src.sc2_env.mock_env import MockSC2Env


def main() -> None:
    """Run scenario 13 simulation."""
    print("="*70)
    print(f"Scenario 13 Simulation")
    print("="*70)
    print()
    
    env = MockSC2Env(initial_minerals=230)
    agent = BasicZergAgent()
    
    obs = env.reset()
    print(f"Initial State: Minerals={obs['minerals']}, Supply={obs['food_used']}/{obs['food_cap']}")
    print()
    
    for step in range(36):
        action = agent.on_step(obs)
        obs = env.step(action)
        
        if step % 5 == 0:
            print(f"Step {obs['step']:3d}: {action:15s} | "
                  f"Minerals={obs['minerals']:3d} | Supply={obs['food_used']:2d}/{obs['food_cap']:2d}")
    
    print()
    print(f"Final State: Minerals={obs['minerals']}, Supply={obs['food_used']}/{obs['food_cap']}, Army={obs['army_size']}")
    print("="*70)


if __name__ == "__main__":
    main()
