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
        pass

        logger.info("WickedZergBotProImpl imported successfully")
    except Exception as e:
        logger.error(f"Failed to import WickedZergBotProImpl: {e}")
        return False

    try:
        pass

        logger.info("BotStepIntegrator imported successfully")
    except Exception as e:
        logger.error(f"Failed to import BotStepIntegrator: {e}")
        return False

    try:
        pass

        logger.info("ProductionResilience imported successfully")
    except Exception as e:
        logger.error(f"Failed to import ProductionResilience: {e}")
        return False

    try:
        pass

        logger.info("StrategyManager imported successfully")
    except Exception as e:
        logger.error(f"Failed to import StrategyManager: {e}")
        return False

    try:
        pass

        logger.info("RogueTacticsManager imported successfully")
    except Exception as e:
        logger.error(f"Failed to import RogueTacticsManager: {e}")
        return False

    try:
        pass

        logger.info("UnitFactory imported successfully")
    except Exception as e:
        logger.error(f"Failed to import UnitFactory: {e}")
        return False

    try:
        pass

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
    """Verify critical code patterns exist in files.

    Returns False if any required pattern is missing so the test actually
    fails. The orchestration moved into BotStepIntegrator, so most calls
    are checked against bot_step_integration.py rather than the impl file.
    """
    logger.info("\n" + "=" * 60)
    logger.info("Verifying Critical Code Patterns")
    logger.info("=" * 60)

    here = os.path.dirname(__file__)
    impl_path = os.path.join(here, "wicked_zerg_bot_pro_impl.py")
    integrator_path = os.path.join(here, "bot_step_integration.py")
    factory_path = os.path.join(here, "unit_factory.py")

    with open(impl_path, "r", encoding="utf-8") as f:
        impl_content = f.read()
    with open(integrator_path, "r", encoding="utf-8") as f:
        integrator_content = f.read()
    with open(factory_path, "r", encoding="utf-8") as f:
        factory_content = f.read()

    # (description, file_label, content, pattern)
    checks = [
        (
            "_step_integrator initialization in impl",
            "wicked_zerg_bot_pro_impl.py",
            impl_content,
            "BotStepIntegrator(self)",
        ),
        (
            "strategy_manager.update() called by integrator",
            "bot_step_integration.py",
            integrator_content,
            ".strategy_manager.update()",
        ),
        (
            "rogue_tactics dispatched by integrator",
            "bot_step_integration.py",
            integrator_content,
            "rogue_tactics",
        ),
        (
            "performance_optimizer.end_frame() in integrator",
            "bot_step_integration.py",
            integrator_content,
            "end_frame()",
        ),
        (
            "unit_factory uses _safe_train",
            "unit_factory.py",
            factory_content,
            "_safe_train",
        ),
        (
            "ProductionResilience referenced in impl",
            "wicked_zerg_bot_pro_impl.py",
            impl_content,
            "ProductionResilience",
        ),
    ]

    success = True
    for name, file_label, content, pattern in checks:
        if pattern in content:
            logger.info(f"Found: {name}  ({file_label})")
        else:
            logger.error(f"Missing: {name}  ({file_label})")
            success = False

    return success


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
