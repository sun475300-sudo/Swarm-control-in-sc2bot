#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Bot initialization smoke tests.

Verifies that critical modules import, that the bot exposes the
manager attributes the integration layer relies on, and that the
delegation hooks expected by bot_step_integration still exist in the
codebase.

Previously this file claimed "ALL TESTS PASSED" while doing nothing
real: import blocks were `try: pass`, pattern checks ignored their
own results, and no logging handler was configured so the output was
silent. Rewritten to be honest with pytest.
"""

import importlib
import logging
import os
import sys

import pytest

logging.basicConfig(
    level=logging.INFO,
    format="%(levelname)s %(name)s: %(message)s",
)
logger = logging.getLogger("TestBotInitialization")

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# Modules every bot startup depends on. If any of these fail to import,
# the bot cannot run at all, so we want a hard failure (not a logged
# warning).
_REQUIRED_MODULES = [
    ("wicked_zerg_bot_pro_impl", "WickedZergBotProImpl"),
    ("bot_step_integration", "BotStepIntegrator"),
    ("local_training.production_resilience", "ProductionResilience"),
    ("strategy_manager", "StrategyManager"),
    ("rogue_tactics_manager", "RogueTacticsManager"),
    ("unit_factory", "UnitFactory"),
    ("combat.boids_swarm_control", "BoidsSwarmController"),
]


@pytest.mark.parametrize("module_name,symbol", _REQUIRED_MODULES)
def test_required_module_imports(module_name, symbol):
    module = importlib.import_module(module_name)
    assert hasattr(module, symbol), (
        f"Module {module_name} loaded but is missing expected symbol {symbol!r}"
    )


# Manager attributes the bot must expose; bot_step_integration.execute_game_logic
# reaches for these directly via getattr/hasattr and silently no-ops when
# missing, so a typo here regresses behavior without raising.
_EXPECTED_MANAGER_ATTRS = [
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


def test_bot_exposes_manager_attributes():
    from wicked_zerg_bot_pro_impl import WickedZergBotProImpl

    bot = WickedZergBotProImpl(train_mode=False, instance_id=0)

    missing = [name for name in _EXPECTED_MANAGER_ATTRS if not hasattr(bot, name)]
    assert not missing, f"WickedZergBotProImpl missing attrs: {missing}"

    assert hasattr(bot, "on_step"), "Bot missing on_step lifecycle method"
    assert hasattr(bot, "on_start"), "Bot missing on_start lifecycle method"


def _read(path):
    with open(path, "r", encoding="utf-8") as f:
        return f.read()


def test_step_integrator_initialized_in_bot_impl():
    """Bot impl must construct the step integrator so on_step delegates."""
    here = os.path.dirname(os.path.abspath(__file__))
    impl_content = _read(os.path.join(here, "wicked_zerg_bot_pro_impl.py"))
    assert "BotStepIntegrator(self)" in impl_content, (
        "wicked_zerg_bot_pro_impl.py no longer constructs BotStepIntegrator(self); "
        "on_step delegation will not happen."
    )


def test_strategy_and_rogue_called_from_integrator():
    """Per-frame strategy + rogue updates were moved into the integrator.

    The integration layer is what actually calls the per-frame update;
    the bot impl just instantiates the integrator. Verify the calls
    land in bot_step_integration.py (not in the bot impl, which was
    the older convention this test used to look for).
    """
    here = os.path.dirname(os.path.abspath(__file__))
    integrator = _read(os.path.join(here, "bot_step_integration.py"))

    assert "self.bot.strategy_manager.update()" in integrator, (
        "bot_step_integration.py no longer calls strategy_manager.update(); "
        "race-specific strategies and emergency mode will not run."
    )
    assert 'getattr(self.bot, "rogue_tactics", None)' in integrator, (
        "bot_step_integration.py no longer reads rogue_tactics; "
        "baneling-drop / larva-saving directives will not propagate."
    )


def test_unit_factory_uses_safe_train():
    here = os.path.dirname(os.path.abspath(__file__))
    factory_content = _read(os.path.join(here, "unit_factory.py"))
    assert "_safe_train" in factory_content, (
        "unit_factory.py no longer routes through _safe_train; "
        "production errors will surface as raw exceptions."
    )


def test_performance_optimizer_end_frame_called():
    here = os.path.dirname(os.path.abspath(__file__))
    integrator_content = _read(os.path.join(here, "bot_step_integration.py"))
    assert "end_frame()" in integrator_content, (
        "bot_step_integration.py no longer calls performance_optimizer.end_frame(); "
        "per-frame metrics will not be flushed."
    )
