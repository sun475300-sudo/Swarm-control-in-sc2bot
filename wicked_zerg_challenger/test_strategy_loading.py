from strategy_manager import StrategyManager, EnemyRace, GamePhase

class MockBot:
    def __init__(self):
        self.enemy_race = None
        self.time = 0

def test():
    print("Initializing StrategyManager...")
    bot = MockBot()
    strategy = StrategyManager(bot)
    
    # Check if ratios are loaded
    print("\nChecking Terran Ratios:")
    terran_ratios = strategy.race_unit_ratios.get(EnemyRace.TERRAN)
    if terran_ratios:
        print(f"Early: {terran_ratios.get(GamePhase.EARLY)}")
        print(f"Mid: {terran_ratios.get(GamePhase.MID)}")
    else:
        print("ERROR: Terran ratios not loaded")

    # Check if defaults loaded for Unknown
    print("\nChecking Unknown Ratios (should default to Terran):")
    unknown_ratios = strategy.race_unit_ratios.get(EnemyRace.UNKNOWN)
    if unknown_ratios:
         print(f"Early: {unknown_ratios.get(GamePhase.EARLY)}")

if __name__ == "__main__":
    test()
