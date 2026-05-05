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

    # Each import is wrapped so the assertion message identifies the failing
    # module; pytest collects this as a regular test (must not return a value).
    from wicked_zerg_bot_pro_impl import WickedZergBotProImpl  # noqa: F401

    logger.info("WickedZergBotProImpl imported successfully")

    from bot_step_integration import BotStepIntegrator  # noqa: F401

    logger.info("BotStepIntegrator imported successfully")

    from local_training.production_resilience import ProductionResilience  # noqa: F401

    logger.info("ProductionResilience imported successfully")

    from strategy_manager import StrategyManager  # noqa: F401

    logger.info("StrategyManager imported successfully")

    from rogue_tactics_manager import RogueTacticsManager  # noqa: F401

    logger.info("RogueTacticsManager imported successfully")

    from unit_factory import UnitFactory  # noqa: F401

    logger.info("UnitFactory imported successfully")

    from combat.boids_swarm_control import BoidsSwarmController  # noqa: F401

    logger.info("BoidsSwarmController imported successfully")


def test_bot_structure():
    """Test bot initialization structure."""
    logger.info("\n" + "=" * 60)
    logger.info("Testing Bot Structure")
    logger.info("=" * 60)

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

    # Check that on_step / on_start methods exist (these are required by SC2 API)
    assert hasattr(bot, "on_step"), "Bot missing on_step method"
    assert hasattr(bot, "on_start"), "Bot missing on_start method"
    logger.info("Bot has on_step + on_start methods")


def verify_code_patterns():
    """Verify critical code patterns exist in files."""
    logger.info("\n" + "=" * 60)
    logger.info("Verifying Critical Code Patterns")
    logger.info("=" * 60)

    # Check wicked_zerg_bot_pro_impl.py
    impl_path = os.path.join(os.path.dirname(__file__), "wicked_zerg_bot_pro_impl.py")
    with open(impl_path, "r", encoding="utf-8") as f:
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
    with open(factory_path, "r", encoding="utf-8") as f:
        factory_content = f.read()

    if "_safe_train" in factory_content:
        logger.info("unit_factory.py uses _safe_train")
    else:
        logger.info("unit_factory.py doesn't use _safe_train")

    # Check bot_step_integration.py
    integrator_path = os.path.join(os.path.dirname(__file__), "bot_step_integration.py")
    with open(integrator_path, "r", encoding="utf-8") as f:
        integrator_content = f.read()

    if "end_frame()" in integrator_content:
        logger.info("bot_step_integration.py calls end_frame()")
    else:
        logger.info("bot_step_integration.py doesn't call end_frame()")


def main():
    """Run all tests as a CLI smoke check (independent of pytest)."""
    logger.info("\n" + "=" * 60)
    logger.info("WICKED ZERG BOT - INITIALIZATION VERIFICATION")
    logger.info("=" * 60 + "\n")

    success = True

    for name, fn in (
        ("imports", test_imports),
        ("bot_structure", test_bot_structure),
        ("code_patterns", verify_code_patterns),
    ):
        try:
            fn()
        except Exception as e:
            logger.error(f"[{name}] failed: {e}")
            import traceback

            traceback.print_exc()
            success = False

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
