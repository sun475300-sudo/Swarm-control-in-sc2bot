# -*- coding: utf-8 -*-
"""Lifecycle smoke tests for WickedZergBotProImpl.

The purpose of these tests is to catch the kind of bug that sweep #7
uncovered in opponent_modeling: attribute-name drift between code
paths that aren't exercised together by the existing unit tests.
We don't run a real SC2 game — we just construct the bot, poke a
couple of manager seams, and assert nothing raised.

If these tests start failing because the constructor signature
changes, that's the same signal as the dashboard / runner scripts
breaking — update both together.
"""

import os
import sys
import unittest
from unittest.mock import MagicMock

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))


class TestBotLifecycleSmoke(unittest.TestCase):
    """Construct-and-poke smoke tests; no real SC2 game state required."""

    def test_constructor_with_defaults_does_not_raise(self):
        """`WickedZergBotProImpl()` with defaults must instantiate cleanly."""
        from wicked_zerg_bot_pro_impl import WickedZergBotProImpl

        bot = WickedZergBotProImpl()
        self.assertFalse(bot.train_mode)
        self.assertEqual(bot.instance_id, 0)
        self.assertEqual(bot.personality_type, "serral")
        self.assertIsNone(bot.opponent_race)
        # Blackboard is the only manager created eagerly in __init__
        self.assertIsNotNone(bot.blackboard)
        # The rest are lazy placeholders
        for name in (
            "defense_coordinator",
            "early_defense",
            "production_controller",
            "intel",
            "economy",
            "production",
            "combat",
            "scout",
            "micro",
            "queen_manager",
            "strategy_manager",
            "performance_optimizer",
            "rogue_tactics",
            "aggressive_strategies",
        ):
            self.assertIsNone(
                getattr(bot, name), f"{name} should be None until on_start"
            )

    def test_constructor_with_train_mode(self):
        from wicked_zerg_bot_pro_impl import WickedZergBotProImpl

        bot = WickedZergBotProImpl(
            train_mode=True, instance_id=3, personality="dark", game_count=10
        )
        self.assertTrue(bot.train_mode)
        self.assertEqual(bot.instance_id, 3)
        self.assertEqual(bot.personality_type, "dark")
        self.assertEqual(bot.game_count, 10)

    def test_difficulty_progression_loaded(self):
        from wicked_zerg_bot_pro_impl import WickedZergBotProImpl

        bot = WickedZergBotProImpl()
        # DifficultyProgression should be created and queryable
        self.assertIsNotNone(bot.difficulty_progression)
        self.assertTrue(
            hasattr(bot.difficulty_progression, "get_recommended_difficulty")
        )

    def test_build_order_log_starts_empty(self):
        from wicked_zerg_bot_pro_impl import WickedZergBotProImpl

        bot = WickedZergBotProImpl()
        self.assertEqual(bot._build_order_log, [])
        self.assertEqual(bot._tracked_structure_tags, set())
        self.assertEqual(bot._units_lost, [])
        self.assertEqual(bot._workers_created, 0)
        self.assertEqual(bot._expansions_built, 0)


class TestOpponentModelingLifecycle(unittest.IsolatedAsyncioTestCase):
    """Guard against the sweep #7 regression: on_start → on_step path.

    Before sweep #7, `on_start` set `current_opponent_id` but
    `on_step`/`on_game_end` read `current_opponent`. Calling on_step
    immediately after on_start returned silently (the early
    `if not self.current_opponent: return` short-circuit was always
    true because that attribute didn't exist yet). This test pins down
    the contract so that drift can't recur.
    """

    async def test_on_start_then_on_step_runs_to_completion(self):
        import tempfile

        from opponent_modeling import OpponentModeling
        from sc2.position import Point2

        with tempfile.TemporaryDirectory() as tmp:
            bot = MagicMock()
            bot.time = 100.0
            bot.iteration = 0
            bot.enemy_race = MagicMock()
            bot.enemy_race.name = "Zerg"
            bot.start_location = Point2((50, 50))
            bot.enemy_structures = []

            modeling = OpponentModeling(
                bot=bot, intel_manager=None, data_file=f"{tmp}/m.json"
            )

            # on_start sets self.current_opponent_id
            await modeling.on_start()
            self.assertIsNotNone(modeling.current_opponent_id)

            # on_step must read the same attribute name (this asserts the
            # sweep #7 fix is still in place).
            await modeling.on_step(0)

            # The opponent must be tracked in opponent_models
            self.assertIn(modeling.current_opponent_id, modeling.opponent_models)


if __name__ == "__main__":
    unittest.main()
