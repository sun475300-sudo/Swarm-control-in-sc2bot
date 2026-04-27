from strategy_manager import StrategyManager, EnemyRace, GamePhase
import logging

logger = logging.getLogger("TestStrategyLoading")


class MockBot:
    def __init__(self):
        self.enemy_race = None
        self.time = 0


def test():
    logger.info("Initializing StrategyManager...")
    bot = MockBot()
    strategy = StrategyManager(bot)

    # Check if ratios are loaded
    logger.info("\nChecking Terran Ratios:")
    terran_ratios = strategy.race_unit_ratios.get(EnemyRace.TERRAN)
    if terran_ratios:
        logger.info(f"Early: {terran_ratios.get(GamePhase.EARLY)}")
        logger.info(f"Mid: {terran_ratios.get(GamePhase.MID)}")
    else:
        logger.error("ERROR: Terran ratios not loaded")

    # Check if defaults loaded for Unknown
    logger.info("\nChecking Unknown Ratios (should default to Terran):")
    unknown_ratios = strategy.race_unit_ratios.get(EnemyRace.UNKNOWN)
    if unknown_ratios:
        logger.info(f"Early: {unknown_ratios.get(GamePhase.EARLY)}")


if __name__ == "__main__":
    test()
