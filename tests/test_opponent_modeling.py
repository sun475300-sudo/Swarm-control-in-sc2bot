"""
Regression tests for OpponentModeling.on_step.

Context (REMAINING_ISSUES.md item N1, F811): OpponentModeling used to define
`on_step` twice in the same class. The second (later) definition silently
replaced the first, so the first definition's logic -- early-signal
detection, timing-attack tracking, tech-progression tracking, and blackboard
sync -- never ran. The live-but-weaker duplicate also referenced
`self.current_opponent`, an attribute the initializer never sets, and had no
guard for `self.bot` being unset.

These tests assert that the *comprehensive* behavior actually fires, and that
calling on_step before a bot is attached doesn't raise.
"""

import ast
import inspect
import os
import sys
from unittest.mock import Mock

import pytest

# opponent_modeling.py does `from utils.logger import get_logger`, which
# resolves to wicked_zerg_challenger/utils (not the top-level utils/ package)
# only if wicked_zerg_challenger/ is on sys.path ahead of the project root.
# Match the convention used by tests/test_combat_manager.py, and import the
# module at collection time (module-level), before pytest re-prepends the
# project root ahead of this path for the `tests` package.
sys.path.insert(
    0, os.path.join(os.path.dirname(__file__), "..", "wicked_zerg_challenger")
)
from opponent_modeling import OpponentModeling  # noqa: E402


class MockUnit:
    def __init__(self, type_id_name, supply_cost=1, is_worker=False, is_flying=False):
        self.type_id = Mock()
        self.type_id.name = type_id_name
        self.supply_cost = supply_cost
        self.is_worker = is_worker
        self.is_flying = is_flying


class MockStructure:
    def __init__(self, type_id_name):
        self.type_id = Mock()
        self.type_id.name = type_id_name


class MockBlackboard:
    def __init__(self):
        self.values = {}

    def set(self, key, value):
        self.values[key] = value


class MockBot:
    def __init__(self):
        self.time = 30.0
        self.enemy_race = Mock()
        self.enemy_race.name = "Zerg"
        self.enemy_structures = []
        self.enemy_units = []
        self.blackboard = MockBlackboard()


class MockIntel:
    """Minimal stand-in for IntelManager, just enough for on_step's
    _detect_early_signals / _track_tech_progression to run without error."""

    def __init__(self):
        self.enemy_tech_buildings = set()

    def is_under_attack(self):
        return False


def _make_opponent_modeling(bot, tmp_path, intel_manager=None):
    data_file = str(tmp_path / "opponent_models_test.json")
    # _detect_early_signals()/_track_tech_progression() no-op unless
    # self.intel is truthy, so tests that exercise on_step need a stand-in.
    return OpponentModeling(
        bot, intel_manager=intel_manager or MockIntel(), data_file=data_file
    )


class TestOnStepNotDuplicated:
    """Guard against the F811 duplicate-`on_step` regression (N1)."""

    def test_on_step_defined_only_once_in_source(self):
        """The class body must not define on_step twice (would be F811)."""
        import opponent_modeling

        source = inspect.getsource(opponent_modeling)
        tree = ast.parse(source)

        class_node = next(
            node
            for node in ast.walk(tree)
            if isinstance(node, ast.ClassDef) and node.name == "OpponentModeling"
        )
        on_step_defs = [
            n
            for n in class_node.body
            if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef))
            and n.name == "on_step"
        ]
        assert len(on_step_defs) == 1

    @pytest.mark.asyncio
    async def test_on_step_without_bot_does_not_raise(self, tmp_path):
        """The active on_step must safely no-op when self.bot is falsy."""
        om = _make_opponent_modeling(MockBot(), tmp_path)
        om.bot = None

        # Should return early instead of raising AttributeError on self.bot.time
        await om.on_step(1000)

    @pytest.mark.asyncio
    async def test_on_step_runs_early_signal_detection(self, tmp_path):
        """
        Previously-dead-code assertion: the comprehensive on_step must run
        early-game signal detection and sync results to the blackboard, not
        just the old stub's (now-removed) early-return behavior.
        """
        bot = MockBot()
        bot.time = 30.0  # inside 0-180s early-game window
        bot.enemy_structures = [
            MockStructure("HATCHERY"),
            MockStructure("HATCHERY"),
            MockStructure("SPAWNINGPOOL"),
        ]

        om = _make_opponent_modeling(bot, tmp_path)
        om.last_update = 0
        om.update_interval = 1

        await om.on_step(1000)

        # Early signals (fast expand + early pool) must have been detected.
        assert len(om.observed_signals) > 0

        # Blackboard sync (part of the comprehensive on_step) must have run.
        assert "predicted_strategy" in bot.blackboard.values
        assert "observed_signals" in bot.blackboard.values
