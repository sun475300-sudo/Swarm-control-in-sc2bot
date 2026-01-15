"""
Run multiple batch simulations for performance testing.
"""

from src.bot.agents.basic_zerg_agent import BasicZergAgent
from src.sc2_env.mock_env import MockSC2Env


def run_simulation(simulation_id: int, steps: int = 50) -> dict:
    """
    Run a single simulation.
    
    Args:
        simulation_id: ID for this simulation
        steps: Number of steps to run
        
    Returns:
        Final state dictionary
    """
    env = MockSC2Env(initial_minerals=100)
    agent = BasicZergAgent()
    
    obs = env.reset()
    
    for _ in range(steps):
        action = agent.on_step(obs)
        obs = env.step(action)
    
    return obs


def main() -> None:
    """Run batch simulations."""
    print("="*70)
    print("Batch Simulation Runner")
    print("="*70)
    print()
    
    num_simulations = 10
    results = []
    
    for i in range(num_simulations):
        print(f"[Simulation {i+1}/{num_simulations}] Running...", end=" ")
        result = run_simulation(i, steps=50)
        results.append(result)
        print(f"Done (Minerals: {result['minerals']}, Army: {result['army_size']})")
    
    # Statistics
    avg_minerals = sum(r["minerals"] for r in results) / len(results)
    avg_army = sum(r["army_size"] for r in results) / len(results)
    avg_supply = sum(r["food_used"] for r in results) / len(results)
    
    print()
    print("="*70)
    print("Statistics")
    print("="*70)
    print(f"Average Minerals: {avg_minerals:.1f}")
    print(f"Average Army Size: {avg_army:.1f}")
    print(f"Average Supply Used: {avg_supply:.1f}")
    print("="*70)


if __name__ == "__main__":
    main()
