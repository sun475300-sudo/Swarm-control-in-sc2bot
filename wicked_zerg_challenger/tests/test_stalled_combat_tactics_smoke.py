# -*- coding: utf-8 -*-
"""
Smoke tests for the Feature #91-#98 tactical managers.

These managers (Nydus Worm, Queen Walk, Baneling Bomb, Doom Drop,
Lurker Positioning, Viper Tactics, Multiprong Attack) are exported from
`combat/__init__.py` but are never instantiated anywhere in
`bot_step_integration.py` or `combat_manager.py` -- they are fully
written (~3500 lines total) but were never wired into the live on_step
loop and have no existing test coverage. See REMAINING_ISSUES.md N12.

This file does not wire them in (that needs a dedicated, isolated PR
per module plus real-game validation). It only guards against basic
regressions (import errors, constructor bugs, crashes on the
trivially-gated on_step path) so the modules don't silently rot further
while they wait to be integrated or removed.
"""

import asyncio
import os
import sys
import unittest
from unittest.mock import Mock

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

try:
    from combat.baneling_bomb import BanelingTacticsManager
    from combat.doom_drop import DoomDropManager
    from combat.lurker_positioning import LurkerPositionManager
    from combat.multiprong_attack import MultiprongAttackManager
    from combat.nydus_tactics import NydusTacticsManager
    from combat.queen_walk import QueenWalkManager
    from combat.viper_tactics import ViperTacticsManager

    SC2_AVAILABLE = True
except (ImportError, TypeError):
    SC2_AVAILABLE = False


def _make_mock_bot():
    """Minimal bot double: empty unit collections, no townhalls/enemies."""
    bot = Mock()
    bot.time = 0.0
    empty_units = Mock()
    empty_units.__iter__ = lambda self: iter([])
    empty_units.__len__ = lambda self: 0
    empty_units.amount = 0
    for attr in ("units", "structures", "enemy_units", "enemy_structures", "townhalls"):
        setattr(bot, attr, empty_units)
    bot.minerals = 0
    bot.vespene = 0
    return bot


MANAGER_CLASSES = {
    "NydusTacticsManager": NydusTacticsManager if SC2_AVAILABLE else None,
    "QueenWalkManager": QueenWalkManager if SC2_AVAILABLE else None,
    "BanelingTacticsManager": BanelingTacticsManager if SC2_AVAILABLE else None,
    "DoomDropManager": DoomDropManager if SC2_AVAILABLE else None,
    "LurkerPositionManager": LurkerPositionManager if SC2_AVAILABLE else None,
    "ViperTacticsManager": ViperTacticsManager if SC2_AVAILABLE else None,
    "MultiprongAttackManager": MultiprongAttackManager if SC2_AVAILABLE else None,
}


@unittest.skipIf(not SC2_AVAILABLE, "sc2 library not compatible with current protobuf")
class TestStalledTacticalManagersSmoke(unittest.TestCase):
    """Constructor + trivially-gated on_step should never raise."""

    def test_all_managers_construct(self):
        for name, cls in MANAGER_CLASSES.items():
            with self.subTest(manager=name):
                bot = _make_mock_bot()
                manager = cls(bot)
                self.assertIs(manager.bot, bot)

    def test_all_managers_on_step_does_not_crash(self):
        # iteration=1 does not satisfy any of these managers' internal
        # "iteration % N == 0" gates (N is always > 1), so on_step should
        # return after the top-level guard without touching deep bot state.
        for name, cls in MANAGER_CLASSES.items():
            with self.subTest(manager=name):
                bot = _make_mock_bot()
                manager = cls(bot)
                asyncio.run(manager.on_step(1))


if __name__ == "__main__":
    unittest.main()
