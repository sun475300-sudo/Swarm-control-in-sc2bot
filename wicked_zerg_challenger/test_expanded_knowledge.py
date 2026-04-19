from knowledge_manager import KnowledgeManager
import logging

logger = logging.getLogger("TestExpandedKnowledge")

def test():
    logger.info("Initializing KnowledgeManager...")
    km = KnowledgeManager()
    
    logger.info("\n--- 1. Map Strategies ---")
    small_map = km.get_map_strategy("Small")
    large_map = km.get_map_strategy("Large")
    logger.info(f"Small Map: {small_map}")
    logger.info(f"Large Map: {large_map}")
    
    if small_map and small_map.get("default_build") == "ROACH_RUSH":
        logger.info(">> PASS: Small map strategy correct")
    else:
        logger.info(">> FAIL: Small map strategy incorrect")

    logger.info("\n--- 2. Counter Rules ---")
    voidray_counter = km.get_counter_unit("VOIDRAY")
    colossus_counter = km.get_counter_unit("COLOSSUS")
    logger.info(f"VoidRay Counter: {voidray_counter}")
    logger.info(f"Colossus Counter: {colossus_counter}")
    
    if voidray_counter and voidray_counter["unit"] == "HYDRALISK":
        logger.info(">> PASS: VoidRay counter correct")
    else:
        logger.info(">> FAIL: VoidRay counter incorrect")

    logger.info("\n--- 3. Micro Settings ---")
    tank_prio = km.get_micro_priority("SIEGETANK")
    logger.info(f"SiegeTank Priority: {tank_prio}")
    
    if tank_prio == 10:
        logger.info(">> PASS: Micro priority correct")
    else:
        logger.info(">> FAIL: Micro priority incorrect")

if __name__ == "__main__":
    test()
