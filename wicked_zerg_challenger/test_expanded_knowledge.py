from knowledge_manager import KnowledgeManager

def test():
    print("Initializing KnowledgeManager...")
    km = KnowledgeManager()
    
    print("\n--- 1. Map Strategies ---")
    small_map = km.get_map_strategy("Small")
    large_map = km.get_map_strategy("Large")
    print(f"Small Map: {small_map}")
    print(f"Large Map: {large_map}")
    
    if small_map and small_map.get("default_build") == "ROACH_RUSH":
        print(">> PASS: Small map strategy correct")
    else:
        print(">> FAIL: Small map strategy incorrect")

    print("\n--- 2. Counter Rules ---")
    voidray_counter = km.get_counter_unit("VOIDRAY")
    colossus_counter = km.get_counter_unit("COLOSSUS")
    print(f"VoidRay Counter: {voidray_counter}")
    print(f"Colossus Counter: {colossus_counter}")
    
    if voidray_counter and voidray_counter["unit"] == "HYDRALISK":
        print(">> PASS: VoidRay counter correct")
    else:
        print(">> FAIL: VoidRay counter incorrect")

    print("\n--- 3. Micro Settings ---")
    tank_prio = km.get_micro_priority("SIEGETANK")
    print(f"SiegeTank Priority: {tank_prio}")
    
    if tank_prio == 10:
        print(">> PASS: Micro priority correct")
    else:
        print(">> FAIL: Micro priority incorrect")

if __name__ == "__main__":
    test()
