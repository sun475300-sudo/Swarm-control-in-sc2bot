from build_order_system import BuildOrderSystem, BuildOrderType
import logging

logger = logging.getLogger("TestKnowledgeLoading")

class MockBot:
    def __init__(self):
        pass

def test():
    logger.info("Initializing BuildOrderSystem...")
    bot = MockBot()
    system = BuildOrderSystem(bot)
    
    # Test loading default build (Roach Rush)
    logger.info(f"\nCurrent Build: {system.current_build_order}")
    logger.info(f"Steps Loaded: {len(system.build_steps)}")
    if system.build_steps:
        logger.info(f"First Step: {system.build_steps[0]}")
        logger.info(f"Last Step: {system.build_steps[-1]}")
    else:
        logger.error("ERROR: No steps loaded!")

    # Test switching build
    logger.info("\nSwitching to STANDARD_12POOL...")
    system.current_build_order = BuildOrderType.STANDARD_12POOL
    system._setup_build_order()
    logger.info(f"Steps Loaded: {len(system.build_steps)}")
    if system.build_steps:
        logger.info(f"First Step: {system.build_steps[0]}")

if __name__ == "__main__":
    test()
