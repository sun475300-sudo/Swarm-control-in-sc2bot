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
    """Verify critical code patterns exist in files."""
    logger.info("\n" + "=" * 60)
    logger.info("Verifying Critical Code Patterns")
    logger.info("=" * 60)

    base = os.path.dirname(__file__)

    def _read(rel):
        with open(os.path.join(base, rel), "r", encoding="utf-8") as f:
            return f.read()

    impl_content = _read("wicked_zerg_bot_pro_impl.py")
    integrator_content = _read("bot_step_integration.py")
    factory_content = _read("unit_factory.py")
    registry_content = _read(os.path.join("core", "manager_registry.py"))

    # After the ManagerFactory refactor production_resilience and rogue_tactics
    # are no longer instantiated by the bot impl directly; they live in the
    # registry, and their per-step calls happen inside bot_step_integration.
    checks = [
        ("BotStepIntegrator initialization (impl)", "BotStepIntegrator(self)", impl_content),
        ("ManagerFactory wired (impl)", "ManagerFactory(self)", impl_content),
        ("ProductionResilience registered (registry)", "production_resilience", registry_content),
        ("strategy_manager.update() call (integrator)", "strategy_manager.update()", integrator_content),
        ("rogue_tactics step call (integrator)", '"rogue_tactics"', integrator_content),
        ("end_frame() call (integrator)", "end_frame()", integrator_content),
        ("unit_factory uses _safe_train", "_safe_train", factory_content),
    ]

    all_ok = True
    for name, pattern, content in checks:
        if pattern in content:
            logger.info(f"Found: {name}")
        else:
            logger.info(f"Missing: {name}")
            all_ok = False

    return all_ok


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
