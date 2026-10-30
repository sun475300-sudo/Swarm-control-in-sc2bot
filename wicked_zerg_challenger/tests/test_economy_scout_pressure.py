"""Opening scout history must not cap the economy for an entire game."""

import sys
from pathlib import Path
from types import SimpleNamespace

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from blackboard import GameStateBlackboard
from economy_manager import EconomyManager, ThreatLevel
from sc2.ids.unit_typeid import UnitTypeId


def make_manager(game_time, gas_time=None, cheese=False, report_time=None):
    blackboard = GameStateBlackboard()
    blackboard.set("early_scout_last_report_time", report_time or game_time)
    blackboard.set("early_scout_gas_time", gas_time)
    blackboard.set("early_scout_cheese_suspected", cheese)
    blackboard.set("early_scout_natural_confirmed", True)
    bases = SimpleNamespace(amount=3)
    bot = SimpleNamespace(
        time=game_time,
        iteration=220,
        blackboard=blackboard,
        workers=SimpleNamespace(amount=30),
        townhalls=SimpleNamespace(amount=3, ready=bases),
        enemy_units=[],
        supply_left=10,
        minerals=200,
        already_pending=lambda _: 0,
        intel=SimpleNamespace(_threat_level="none", enemy_army_supply=0),
        supply_army=20,
    )
    return EconomyManager(bot), blackboard


@pytest.mark.parametrize(
    ("gas_time", "cheese"), [(75.0, False), (None, True), (75.0, True)]
)
@pytest.mark.asyncio
async def test_midgame_fresh_report_of_opening_history_allows_drone_recovery(
    gas_time, cheese
):
    # EarlyScoutSystem republishes remembered opening timings every update.
    # Even a new report at 10:00 does not turn gas seen at 1:15 into a new rush.
    manager, blackboard = make_manager(600.0, gas_time=gas_time, cheese=cheese)

    await manager._train_drone_if_needed()

    requests = [
        request for queue in blackboard.production_queue.values() for request in queue
    ]
    assert len(requests) == 1
    assert requests[0][0] == UnitTypeId.DRONE
    assert manager._get_early_scout_pressure_state()["pressure_active"] is False


@pytest.mark.asyncio
async def test_opening_pressure_still_halts_drone_greed_and_delays_natural():
    manager, blackboard = make_manager(120.0, gas_time=75.0, cheese=True)
    manager.bot.townhalls.amount = manager.bot.townhalls.ready.amount = 1
    manager.bot.workers.amount = 20

    await manager._train_drone_if_needed()

    assert all(not queue for queue in blackboard.production_queue.values())
    assert manager._should_delay_opening_expansion(1) is True


@pytest.mark.asyncio
async def test_current_critical_threat_still_halts_midgame_drone_recovery():
    manager, blackboard = make_manager(600.0, gas_time=75.0, cheese=True)
    manager.bot.intel._threat_level = "critical"

    assert manager.update_economy_combat_balance() == ThreatLevel.CRITICAL
    await manager._train_drone_if_needed()

    assert manager.get_target_drone_count() == 0
    assert all(not queue for queue in blackboard.production_queue.values())


def test_future_scout_report_is_not_treated_as_current_opening_evidence():
    manager, _ = make_manager(120.0, gas_time=75.0, cheese=True, report_time=150.0)

    assert manager._get_early_scout_pressure_state()["pressure_active"] is False
