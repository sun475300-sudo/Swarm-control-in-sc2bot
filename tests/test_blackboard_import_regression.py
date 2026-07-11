# -*- coding: utf-8 -*-
"""
Regression tests for a broken `from game_state_blackboard import ...` import
that silently disabled defense/threat escalation logic in three modules.

`game_state_blackboard` is not a module in this repo -- the classes
(`ThreatLevel`, `AuthorityMode`, `GameStateBlackboard`) actually live in
`blackboard.py`. All three call sites wrapped the bad import in a bare
`try/except ImportError` and fell back to `None`, so every guard of the
form `if ThreatLevel is not None and ...` silently short-circuited:

- `defense_coordinator.DefenseCoordinator._emergency_defense()` never ran
  at all (its own top-level guard returned immediately), so a real
  HIGH+/CRITICAL threat never triggered emergency unit requests, worker
  evacuation, or the EMERGENCY authority-mode escalation.
- `bot_step_integration.BotStepIntegrator._blackboard_has_serious_base_threat()`
  and `tech_coordinator.TechCoordinator._blackboard_has_serious_base_threat()`
  could only ever return True via the enemy-unit-count branch; the
  CRITICAL-threat-level + high-enemy-supply branch was dead code.
"""

import os
import sys
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import AsyncMock, Mock

import pytest

ROOT = Path(__file__).resolve().parents[1]
PACKAGE_ROOT = ROOT / "wicked_zerg_challenger"
os.environ.setdefault("PROTOCOL_BUFFERS_PYTHON_IMPLEMENTATION", "python")
for candidate in (str(ROOT), str(PACKAGE_ROOT)):
    if candidate not in sys.path:
        sys.path.insert(0, candidate)

# NOTE: imported bare (not `wicked_zerg_challenger.X`) deliberately -- these
# modules internally do bare intra-package imports too (e.g.
# `defense_coordinator.py` does `from blackboard import ThreatLevel`), so
# importing them under the `wicked_zerg_challenger.` prefix here would load
# a second, distinct copy of `blackboard` into sys.modules and break the
# `is`-identity checks below even though the fix is correct at runtime.
try:
    import bot_step_integration as bot_step_integration_module
    import defense_coordinator as defense_coordinator_module
    import tech_coordinator as tech_coordinator_module
    from blackboard import AuthorityMode, ThreatLevel
    from bot_step_integration import BotStepIntegrator
    from defense_coordinator import DefenseCoordinator
    from tech_coordinator import TechCoordinator
except ImportError:
    pytest.skip(
        "bot modules not importable (SC2 env required)", allow_module_level=True
    )


class TestModuleLevelImportsResolved:
    """The module-level `ThreatLevel`/`AuthorityMode` names must bind to the
    real classes in blackboard.py, not silently fall back to None."""

    def test_defense_coordinator_threat_level_is_real(self):
        assert defense_coordinator_module.ThreatLevel is ThreatLevel

    def test_defense_coordinator_authority_mode_is_real(self):
        assert defense_coordinator_module.AuthorityMode is AuthorityMode

    def test_defense_coordinator_game_state_blackboard_is_real(self):
        from blackboard import GameStateBlackboard

        assert defense_coordinator_module.GameStateBlackboard is GameStateBlackboard


class TestEmergencyDefenseFires:
    def _make_coordinator(self, threat_level):
        bot = Mock()
        blackboard = SimpleNamespace(
            threat=SimpleNamespace(level=threat_level, enemy_units_near_base=6),
            set_authority_mode=Mock(),
        )
        coordinator = DefenseCoordinator(bot, blackboard)
        coordinator._request_emergency_units = AsyncMock()
        coordinator._evacuate_workers = AsyncMock()
        return coordinator, blackboard

    @pytest.mark.asyncio
    async def test_critical_threat_escalates_authority_and_defends(self):
        coordinator, blackboard = self._make_coordinator(ThreatLevel.CRITICAL)

        await coordinator._emergency_defense()

        blackboard.set_authority_mode.assert_called_once()
        args, _ = blackboard.set_authority_mode.call_args
        assert args[0] is AuthorityMode.EMERGENCY
        coordinator._request_emergency_units.assert_awaited_once()
        coordinator._evacuate_workers.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_high_threat_still_defends_without_escalating_authority(self):
        coordinator, blackboard = self._make_coordinator(ThreatLevel.HIGH)

        await coordinator._emergency_defense()

        blackboard.set_authority_mode.assert_not_called()
        coordinator._request_emergency_units.assert_awaited_once()
        coordinator._evacuate_workers.assert_awaited_once()


class TestSeriousBaseThreatCriticalBranch:
    """Both duplicated implementations must honor the
    CRITICAL-threat-level + high-enemy-supply branch, not just the
    enemy-unit-count branch."""

    def _threat(self, level, enemy_near_base=0, enemy_army_supply=0.0):
        return SimpleNamespace(
            level=level,
            enemy_units_near_base=enemy_near_base,
            enemy_army_supply=enemy_army_supply,
        )

    def test_tech_coordinator_critical_level_alone_triggers(self):
        coordinator = TechCoordinator(bot=Mock())
        coordinator.bot.blackboard = SimpleNamespace(
            threat=self._threat(
                ThreatLevel.CRITICAL, enemy_near_base=0, enemy_army_supply=8.0
            )
        )

        assert coordinator._blackboard_has_serious_base_threat(min_enemies=4) is True

    def test_tech_coordinator_high_level_low_supply_does_not_trigger(self):
        coordinator = TechCoordinator(bot=Mock())
        coordinator.bot.blackboard = SimpleNamespace(
            threat=self._threat(
                ThreatLevel.HIGH, enemy_near_base=0, enemy_army_supply=8.0
            )
        )

        assert coordinator._blackboard_has_serious_base_threat(min_enemies=4) is False

    def test_bot_step_integrator_critical_level_alone_triggers(self):
        integrator = object.__new__(BotStepIntegrator)
        integrator.bot = Mock()
        integrator.bot.blackboard = SimpleNamespace(
            threat=self._threat(
                ThreatLevel.CRITICAL, enemy_near_base=0, enemy_army_supply=8.0
            )
        )

        assert integrator._blackboard_has_serious_base_threat(min_enemies=4) is True
