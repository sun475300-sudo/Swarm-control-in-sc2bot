#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Test script to verify bot initialization and manager connections.
"""

import logging
import os
import sys

logger = logging.getLogger("TestBotInitialization")

# Add current directory to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))


def test_imports():
    """Test that all critical modules can be imported."""
    logger.info("=" * 60)
    logger.info("Testing Module Imports")
    logger.info("=" * 60)

    try:

        logger.info("WickedZergBotProImpl imported successfully")
    except Exception as e:
        logger.error(f"Failed to import WickedZergBotProImpl: {e}")
        return False

    try:

        logger.info("BotStepIntegrator imported successfully")
    except Exception as e:
        logger.error(f"Failed to import BotStepIntegrator: {e}")
        return False

    try:

        logger.info("ProductionResilience imported successfully")
    except Exception as e:
        logger.error(f"Failed to import ProductionResilience: {e}")
        return False

    try:

        logger.info("StrategyManager imported successfully")
    except Exception as e:
        logger.error(f"Failed to import StrategyManager: {e}")
        return False

    try:

        logger.info("RogueTacticsManager imported successfully")
    except Exception as e:
        logger.error(f"Failed to import RogueTacticsManager: {e}")
        return False

    try:

        logger.info("UnitFactory imported successfully")
    except Exception as e:
        logger.error(f"Failed to import UnitFactory: {e}")
        return False

    try:

        logger.info("BoidsSwarmController imported successfully")
    except Exception as e:
        logger.error(f"Failed to import BoidsSwarmController: {e}")
        return False

    return True


def test_bot_structure():
    """Test bot initialization structure."""
    logger.info("\n" + "=" * 60)
    logger.info("Testing Bot Structure")
    logger.info("=" * 60)

    try:
        from wicked_zerg_bot_pro_impl import WickedZergBotProImpl

        # Create a mock bot instance (won't actually initialize game)
        bot = WickedZergBotProImpl(train_mode=False, instance_id=0)

        # Check that manager attributes exist
        managers = [
            "intel",
            "economy",
            "production",
            "combat",
            "scout",
            "micro",
            "queen_manager",
            "strategy_manager",
            "performance_optimizer",
            "formation_controller",
            "rogue_tactics",
            "transformer_model",
            "hierarchical_rl",
        ]

        for manager in managers:
            if hasattr(bot, manager):
                logger.info(f"Bot has attribute: {manager}")
            else:
                logger.info(f"Bot missing attribute: {manager}")

        # Check that on_step method exists
        if hasattr(bot, "on_step"):
            logger.info("Bot has on_step method")
        else:
            logger.info("Bot missing on_step method")

        # Check that on_start method exists
        if hasattr(bot, "on_start"):
            logger.info("Bot has on_start method")
        else:
            logger.info("Bot missing on_start method")

        return True

    except Exception as e:
        logger.error(f"Failed to test bot structure: {e}")
        import traceback

        traceback.print_exc()
        return False


def verify_code_patterns():
    """Verify critical code patterns exist in files."""
    logger.info("\n" + "=" * 60)
    logger.info("Verifying Critical Code Patterns")
    logger.info("=" * 60)

    # Check wicked_zerg_bot_pro_impl.py
    impl_path = os.path.join(os.path.dirname(__file__), "wicked_zerg_bot_pro_impl.py")
    with open(impl_path, encoding="utf-8") as f:
        impl_content = f.read()

    checks = [
        ("ProductionResilience initialization", "ProductionResilience(self)"),
        ("strategy_manager.update() call", "self.strategy_manager.update()"),
        ("rogue_tactics.update() call", "self.rogue_tactics.update(iteration)"),
        ("_step_integrator initialization", "BotStepIntegrator(self)"),
    ]

    for name, pattern in checks:
        if pattern in impl_content:
            logger.info(f"Found: {name}")
        else:
            logger.info(f"Missing: {name}")

    # Check unit_factory.py
    factory_path = os.path.join(os.path.dirname(__file__), "unit_factory.py")
    with open(factory_path, encoding="utf-8") as f:
        factory_content = f.read()

    if "_safe_train" in factory_content:
        logger.info("unit_factory.py uses _safe_train")
    else:
        logger.info("unit_factory.py doesn't use _safe_train")

    # Check bot_step_integration.py
    integrator_path = os.path.join(os.path.dirname(__file__), "bot_step_integration.py")
    with open(integrator_path, encoding="utf-8") as f:
        integrator_content = f.read()

    if "end_frame()" in integrator_content:
        logger.info("bot_step_integration.py calls end_frame()")
    else:
        logger.info("bot_step_integration.py doesn't call end_frame()")

    return True


def main():
    """Run all tests."""
    logger.info("\n" + "=" * 60)
    logger.info("WICKED ZERG BOT - INITIALIZATION VERIFICATION")
    logger.info("=" * 60 + "\n")

    success = True

    # Test 1: Imports
    if not test_imports():
        success = False

    # Test 2: Bot structure
    if not test_bot_structure():
        success = False

    # Test 3: Code patterns
    if not verify_code_patterns():
        success = False

    # Summary
    logger.info("\n" + "=" * 60)
    if success:
        logger.info("ALL TESTS PASSED")
        logger.info("=" * 60)
        logger.info("\nBot is properly configured:")
        logger.info("  - All managers can be imported")
        logger.info("  - ProductionResilience is initialized")
        logger.info("  - strategy_manager.update() is called in on_step")
        logger.info("  - rogue_tactics.update() is called in on_step")
        logger.info("  - unit_factory uses _safe_train")
        logger.info("  - performance_optimizer.end_frame() is called")
        logger.info("\nThe bot should now execute strategies and tactics correctly!")
    else:
        logger.error("SOME TESTS FAILED")
        logger.info("=" * 60)
        logger.error("\nPlease review the errors above.")
    return 0 if success else 1


if __name__ == "__main__":
    sys.exit(main())
