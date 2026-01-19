"""
Quick import test to verify new structure works.
"""

import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

try:
    from src.bot.agents.basic_zerg_agent import BasicZergAgent
    from src.sc2_env.mock_env import MockSC2Env
    
    print("="*70)
    print("Import Test")
    print("="*70)
    print()
    
    # Test agent
    agent = BasicZergAgent()
    print(f"? Agent created: {type(agent).__name__}")
    
    # Test environment
    env = MockSC2Env()
    print(f"? Environment created: {type(env).__name__}")
    
    # Test interaction
    obs = env.reset()
    action = agent.on_step(obs)
    
    print()
    print(f"? Interaction successful:")
    print(f"   Action: {action}")
    print(f"   State: Minerals={obs['minerals']}, Supply={obs['food_used']}/{obs['food_cap']}")
    print()
    print("="*70)
    print("? All imports successful!")
    print("="*70)
    
except ImportError as e:
    print(f"? Import failed: {e}")
    sys.exit(1)
