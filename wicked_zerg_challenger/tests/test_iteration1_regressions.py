# -*- coding: utf-8 -*-
"""Regression tests for bugs fixed in iteration 1 (P1.1-P1.7).

These bugs would have been silently lurking if not caught by a focused
test, so we lock them in here.
"""

import os
import sys
import unittest

os.environ["PROTOCOL_BUFFERS_PYTHON_IMPLEMENTATION"] = "python"

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))


class TestP11_BlackboardAliasExists(unittest.TestCase):
    """P1.1 — external code imports `Blackboard`, must alias GameStateBlackboard."""

    def test_blackboard_alias(self):
        from blackboard import Blackboard, GameStateBlackboard

        self.assertIs(Blackboard, GameStateBlackboard)

    def test_wicked_zerg_bot_imports(self):
        # Was previously broken by the missing Blackboard alias.
        import wicked_zerg_bot_pro_impl  # noqa: F401


class TestP12_OpponentModelingNotShadowed(unittest.TestCase):
    """P1.2 — second on_step was silently overriding the rich one.
    Also locks the standardized `current_opponent_id` attribute (P1.3).
    """

    def test_opponent_modeling_state_consistent(self):
        from opponent_modeling import OpponentModeling

        # Single source of truth for the current opponent.
        # The old code had both current_opponent (set by on_game_start) and
        # current_opponent_id (set by __init__ / on_start), causing the
        # second on_step's guard to use the wrong attribute.
        cls_attrs = dir(OpponentModeling)
        self.assertIn("on_step", cls_attrs)
        self.assertIn("on_game_start", cls_attrs)

    def test_on_step_uses_current_opponent_id(self):
        """The rich on_step now checks current_opponent_id (was current_opponent)."""
        import inspect

        from opponent_modeling import OpponentModeling

        src = inspect.getsource(OpponentModeling.on_step)
        self.assertIn("current_opponent_id", src)
        # The old buggy attribute must not be referenced.
        # (Use a word-boundary check to avoid matching current_opponent_id.)
        import re

        self.assertFalse(
            re.search(r"current_opponent(?!_id)", src),
            "on_step must not reference current_opponent (use current_opponent_id)",
        )

    def test_on_step_richness_preserved(self):
        """The shadowing duplicate dropped tech/timing/blackboard tracking.
        Make sure the merged on_step still calls all of those methods.
        """
        import inspect

        from opponent_modeling import OpponentModeling

        src = inspect.getsource(OpponentModeling.on_step)
        for expected_call in (
            "_detect_early_signals",
            "_make_strategy_prediction",
            "_track_build_order",
            "_detect_timing_attacks",
            "_track_tech_progression",
            "blackboard",
        ):
            self.assertIn(
                expected_call,
                src,
                f"on_step is missing {expected_call!r} — was rich version restored?",
            )


class TestP17_ShouldExpandTypoFixed(unittest.TestCase):
    """P1.7 — should_expand had `is_supply_block` (no -ed) typo."""

    def test_should_expand_no_attribute_error(self):
        from blackboard import GameStateBlackboard, ThreatLevel

        bb = GameStateBlackboard()
        bb.update_threat(ThreatLevel.NONE)
        bb.update_resources(minerals=500, vespene=0, supply_used=10, supply_cap=100)
        # Pre-fix this raised AttributeError.
        self.assertTrue(bb.should_expand())

    def test_should_expand_mineral_gate(self):
        """P1.8 — should_expand must enforce mineral threshold."""
        from blackboard import GameStateBlackboard, ThreatLevel

        bb = GameStateBlackboard()
        bb.update_threat(ThreatLevel.NONE)
        bb.update_resources(minerals=50, vespene=0, supply_used=10, supply_cap=100)
        self.assertFalse(bb.should_expand())


if __name__ == "__main__":
    unittest.main()
