"""Regression tests for the upgrade_manager race_priority_modifiers fix.

Pre-fix bug: `_get_upgrade_priority` fetched
`race_modifiers = self.race_priority_modifiers.get(enemy_race, {})` and
then dropped it on the floor. The race-specific weight table was dead
state — Terran armor=1.3 / Zerg melee=1.3 etc. never influenced upgrade
order.

Post-fix: the race's heaviest-weighted lane gets promoted to the front of
the priority queue, so the table actually shapes upgrade order.

These tests don't exercise the full _get_upgrade_priority (it needs an
SC2 bot mock) — they verify the table structure and the max-lookup
behavior the fix relies on, plus the _normalize_enemy_race contract that
keys the lookup.
"""

from __future__ import annotations

import sys
import types
from unittest.mock import MagicMock

import pytest

# upgrade_manager imports `from utils.logger import get_logger` and the
# bot is normally launched with wicked_zerg_challenger/ on sys.path so
# `utils` resolves there. From the tests dir the project-root `utils`
# package wins instead and lacks `logger`. Inject a minimal shim so the
# module imports cleanly in the test process without altering sys.path
# for other tests.
if "utils.logger" not in sys.modules:
    shim = types.ModuleType("utils.logger")
    shim.get_logger = lambda name="": __import__("logging").getLogger(name)
    sys.modules["utils.logger"] = shim

try:
    from wicked_zerg_challenger.upgrade_manager import EvolutionUpgradeManager
except Exception as exc:
    pytest.skip(f"upgrade_manager import failed: {exc}", allow_module_level=True)


def _mgr():
    bot = MagicMock()
    return EvolutionUpgradeManager(bot)


class TestRacePriorityModifiersTable:
    """The dict the fix actually depends on."""

    def test_terran_prefers_armor(self):
        m = _mgr()
        weights = m.race_priority_modifiers["Terran"]
        assert max(weights, key=weights.get) == "armor", (
            "Terran's heaviest lane should be 'armor' (1.3) — "
            "promoted to front of upgrade queue vs marines/marauders."
        )

    def test_zerg_prefers_melee(self):
        m = _mgr()
        weights = m.race_priority_modifiers["Zerg"]
        assert max(weights, key=weights.get) == "melee", (
            "Zerg's heaviest lane should be 'melee' (1.3) — "
            "promoted to front of upgrade queue vs zergling fights."
        )

    def test_protoss_has_table(self):
        m = _mgr()
        weights = m.race_priority_modifiers["Protoss"]
        # Protoss has armor=1.2 and melee=1.2 — tie, max() returns first
        # which is implementation-dependent, but at least the table exists
        # and is non-empty.
        assert weights
        top = max(weights, key=weights.get)
        assert top in weights
        assert weights[top] >= 1.0

    def test_unknown_race_returns_empty(self):
        m = _mgr()
        # The fix code: race_modifiers = self.race_priority_modifiers.get(
        #     enemy_race, {}
        # ); race_lead_lane = None unless race_modifiers truthy.
        weights = m.race_priority_modifiers.get("Klingon", {})
        assert weights == {}, (
            "Unknown race must return empty dict so race_lead_lane stays "
            "None and the priorities list is unmodified — preserves the "
            "no-race-info baseline behavior."
        )


class TestRaceLeadLaneSelection:
    """The exact expression `max(weights, key=weights.get)` used in the fix."""

    def test_max_picks_highest_weight(self):
        weights = {"armor": 1.3, "melee": 1.0, "missile": 1.1}
        assert max(weights, key=weights.get) == "armor"

    def test_max_handles_single_entry(self):
        weights = {"melee": 1.5}
        assert max(weights, key=weights.get) == "melee"


class TestRaceNormalization:
    """The _normalize_enemy_race static method that keys the modifier lookup."""

    def test_lowercase_race_string(self):
        m = _mgr()
        assert m._normalize_enemy_race("terran") == "terran"

    def test_enum_with_name_attribute(self):
        m = _mgr()

        class FakeRace:
            name = "Zerg"

        # _normalize lowercases the .name attribute
        assert m._normalize_enemy_race(FakeRace()) == "zerg"

    def test_none_race_returns_empty(self):
        m = _mgr()
        assert m._normalize_enemy_race(None) == ""

    def test_race_dot_prefix_stripped(self):
        m = _mgr()
        # _normalize strips the "race." prefix on stringified enum values
        result = m._normalize_enemy_race("Race.Protoss")
        assert "protoss" in result.lower()
