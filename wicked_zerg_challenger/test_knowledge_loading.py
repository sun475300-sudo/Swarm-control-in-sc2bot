from build_order_system import BuildOrderSystem, BuildOrderType

class MockBot:
    def __init__(self):
        pass

def test():
    print("Initializing BuildOrderSystem...")
    bot = MockBot()
    system = BuildOrderSystem(bot)
    
    # Test loading default build (Roach Rush)
    print(f"\nCurrent Build: {system.current_build_order}")
    print(f"Steps Loaded: {len(system.build_steps)}")
    if system.build_steps:
        print(f"First Step: {system.build_steps[0]}")
        print(f"Last Step: {system.build_steps[-1]}")
    else:
        print("ERROR: No steps loaded!")

    # Test switching build
    print("\nSwitching to STANDARD_12POOL...")
    system.current_build_order = BuildOrderType.STANDARD_12POOL
    system._setup_build_order()
    print(f"Steps Loaded: {len(system.build_steps)}")
    if system.build_steps:
        print(f"First Step: {system.build_steps[0]}")

if __name__ == "__main__":
    test()
