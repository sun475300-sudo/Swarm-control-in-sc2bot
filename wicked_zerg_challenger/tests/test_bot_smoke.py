# -*- coding: utf-8 -*-
"""Smoke tests — catch the "bot can't even load" class of regressions.

Cycle 1 of the test-driven improvement pass found that
`wicked_zerg_bot_pro_impl.py` couldn't be imported at all because
`blackboard.py` was missing the `Blackboard` alias used by multiple
managers. Tests that mocked individual managers wouldn't have caught
this — only an end-to-end import does.

The cost of these tests is one cheap import / construction per run,
in exchange for fast feedback on any future "missing alias / broken
import / signature mismatch" change.
"""
from __future__ import annotations

import os
import sys
import unittest
from pathlib import Path

os.environ.setdefault("PROTOCOL_BUFFERS_PYTHON_IMPLEMENTATION", "python")

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))


class TestBotImports(unittest.TestCase):
    def test_blackboard_module_exports_alias(self):
        import blackboard

        self.assertTrue(hasattr(blackboard, "Blackboard"))
        self.assertTrue(hasattr(blackboard, "GameStateBlackboard"))
        self.assertIs(blackboard.Blackboard, blackboard.GameStateBlackboard)

    def test_main_bot_module_imports(self):
        # Just importing this module exercises all `from blackboard import X`
        # and other top-level wiring across the manager constellation.
        import wicked_zerg_bot_pro_impl

        self.assertTrue(hasattr(wicked_zerg_bot_pro_impl, "WickedZergBotProImpl"))

    def test_main_bot_class_instantiates(self):
        import wicked_zerg_bot_pro_impl

        bot = wicked_zerg_bot_pro_impl.WickedZergBotProImpl()
        # Blackboard must be the runtime singleton.
        self.assertEqual(type(bot.blackboard).__name__, "GameStateBlackboard")
        # Lifecycle hooks the SC2 client calls each frame must exist.
        for hook in ("on_start", "on_step", "on_end"):
            self.assertTrue(callable(getattr(bot, hook, None)), f"missing {hook}")


class TestBlackboardCoreLogic(unittest.TestCase):
    """The bugs caught in cycle 1 — keep them caught."""

    def test_should_expand_requires_minerals(self):
        from blackboard import GameStateBlackboard, ThreatLevel

        bb = GameStateBlackboard()
        bb.update_threat(ThreatLevel.NONE)
        bb.update_resources(100, 50, 50, 100)  # under hatchery cost
        self.assertFalse(bb.should_expand())

    def test_should_expand_under_attack_blocks(self):
        from blackboard import GameStateBlackboard, ThreatLevel

        bb = GameStateBlackboard()
        bb.update_threat(ThreatLevel.NONE)
        bb.update_resources(500, 100, 50, 100)
        bb.is_under_attack = True
        self.assertFalse(bb.should_expand())

    def test_should_expand_supply_blocked_blocks(self):
        from blackboard import GameStateBlackboard, ThreatLevel

        bb = GameStateBlackboard()
        bb.update_threat(ThreatLevel.NONE)
        # supply_used == supply_cap → is_supply_blocked True
        bb.update_resources(500, 100, 100, 100)
        self.assertFalse(bb.should_expand())


if __name__ == "__main__":
    unittest.main()
