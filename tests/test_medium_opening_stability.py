import os
from pathlib import Path
import sys
from types import SimpleNamespace

ROOT = Path(__file__).resolve().parents[1]
PACKAGE_ROOT = ROOT / "wicked_zerg_challenger"
os.environ.setdefault("PROTOCOL_BUFFERS_PYTHON_IMPLEMENTATION", "python")
for candidate in (str(ROOT), str(PACKAGE_ROOT)):
    if candidate not in sys.path:
        sys.path.insert(0, candidate)

import pytest

from wicked_zerg_challenger.blackboard import GameStateBlackboard
from wicked_zerg_challenger.early_scout_system import EarlyScoutSystem
from wicked_zerg_challenger.economy_manager import EconomyManager
from wicked_zerg_challenger.strategy_manager import StrategyManager, StrategyMode
from wicked_zerg_challenger.training_automation import (
    GameResult,
    build_enemy_race_sequence,
    build_training_summary,
)


class MockPoint2:
    def __init__(self, x: float, y: float):
        self.x = x
        self.y = y

    def distance_to(self, other) -> float:
        ox = getattr(other, "x", None)
        oy = getattr(other, "y", None)
        if ox is not None and oy is not None:
            return ((self.x - ox) ** 2 + (self.y - oy) ** 2) ** 0.5

        position = getattr(other, "position", None)
        if position is not None:
            return self.distance_to(position)

        return 0.0

    def towards(self, other, distance):
        del distance
        ox = getattr(other, "x", self.x)
        oy = getattr(other, "y", self.y)
        return MockPoint2((self.x + ox) / 2, (self.y + oy) / 2)


class MockTypeId:
    def __init__(self, name: str):
        self.name = name

    def __str__(self) -> str:
        return self.name


class MockUnit:
    def __init__(self, type_name: str, position=(50, 50), can_attack=False, tag=None):
        self.type_id = MockTypeId(type_name)
        self._position = MockPoint2(*position)
        self.can_attack = can_attack
        self.tag = tag if tag is not None else id(self)

    @property
    def position(self):
        return self._position

    def distance_to(self, other):
        return self.position.distance_to(other)

    def move(self, target):
        return ("move", self.tag, target)

    def attack(self, target):
        return ("attack", self.tag, target)


class MockStructure:
    def __init__(self, type_name: str, position=(50, 50)):
        self.type_id = MockTypeId(type_name)
        self._position = MockPoint2(*position)

    @property
    def position(self):
        return self._position

    def distance_to(self, other):
        return self.position.distance_to(other)


class UnitGroup(list):
    @property
    def amount(self):
        return len(self)

    @property
    def exists(self):
        return bool(self)

    @property
    def first(self):
        return self[0]

    @property
    def ready(self):
        return self

    @property
    def idle(self):
        return self

    def take(self, count):
        return UnitGroup(self[:count])

    def tags_in(self, tags):
        tag_set = set(tags)
        return UnitGroup([unit for unit in self if unit.tag in tag_set])

    def closest_to(self, target):
        return min(self, key=lambda unit: unit.distance_to(target))

    def filter(self, predicate):
        return UnitGroup([unit for unit in self if predicate(unit)])


def test_mixed_enemy_race_rotation_cycles_in_fixed_order():
    sequence = build_enemy_race_sequence(games=8, enemy_races="mixed")
    assert sequence == [
        "Protoss",
        "Terran",
        "Zerg",
        "Protoss",
        "Terran",
        "Zerg",
        "Protoss",
        "Terran",
    ]


def test_training_summary_tracks_by_race_and_next_focus():
    results = [
        GameResult(1, "AbyssalReefLE", "Protoss", "Medium", "victory", 500.0, 0, 0, 0),
        GameResult(2, "AbyssalReefLE", "Protoss", "Medium", "victory", 480.0, 1, 0, 0),
        GameResult(3, "AbyssalReefLE", "Terran", "Medium", "defeat", 430.0, 0, 1, 1, crashed=True),
        GameResult(4, "AbyssalReefLE", "Zerg", "Medium", "timeout", 1500.0, 0, 1, -1, timed_out=True),
    ]

    summary = build_training_summary(results, started_at="20260329_120000", finished_at="20260329_121000")

    assert summary.by_race["Protoss"]["win_rate"] == 100.0
    assert summary.timeouts == 1
    assert summary.crashes == 1
    assert summary.weakest_matchup == "Terran"
    assert summary.next_focus_race == "Terran"
    assert summary.benchmark_passed is False


@pytest.mark.asyncio
async def test_early_scout_syncs_blackboard_state():
    blackboard = GameStateBlackboard()
    enemy_start = MockPoint2(100, 100)
    enemy_natural = MockPoint2(92, 92)
    bot = SimpleNamespace(
        blackboard=blackboard,
        time=75.0,
        enemy_start_locations=[enemy_start],
        expansion_locations_list=[enemy_start, enemy_natural, MockPoint2(80, 80)],
        game_info=SimpleNamespace(map_center=MockPoint2(64, 64)),
        enemy_structures=[
            MockStructure("SPAWNINGPOOL", position=(100, 100)),
            MockStructure("EXTRACTOR", position=(98, 98)),
            MockStructure("HATCHERY", position=(92, 92)),
        ],
        enemy_units=[],
    )

    scout = EarlyScoutSystem(bot)
    await scout._analyze_enemy_info()
    scout._sync_blackboard_state(refresh_report=True)

    assert blackboard.get("early_scout_pool_time") == 75.0
    assert blackboard.get("early_scout_gas_time") == 75.0
    assert blackboard.get("early_scout_natural_confirmed") is True
    assert blackboard.get("early_scout_cheese_suspected") is True
    assert blackboard.get("early_scout_last_report_time") == 75.0


def test_strategy_manager_switches_to_defense_on_early_scout_pressure():
    blackboard = GameStateBlackboard()
    blackboard.set("early_scout_last_report_time", 100.0)
    blackboard.set("early_scout_cheese_suspected", True)
    blackboard.set("early_scout_gas_time", 80.0)
    blackboard.set("early_scout_natural_confirmed", False)

    bot = SimpleNamespace(
        time=130.0,
        iteration=22,
        enemy_race=SimpleNamespace(name="Protoss"),
        enemy_units=UnitGroup(),
        enemy_structures=[],
        units=UnitGroup([MockUnit("DRONE", can_attack=False)]),
        blackboard=blackboard,
        intel=SimpleNamespace(has_tech_alert=lambda _: False),
    )

    manager = StrategyManager(bot, blackboard=blackboard)
    manager.update()

    assert manager.current_mode == StrategyMode.DEFENSIVE
    assert manager.emergency_spine_requested is True
    assert manager.emergency_spore_requested is True
    assert blackboard.get("urgent_spore_all_bases") is True


@pytest.mark.asyncio
async def test_economy_manager_suppresses_drone_greed_under_pressure():
    blackboard = GameStateBlackboard()
    blackboard.set("early_scout_last_report_time", 100.0)
    blackboard.set("early_scout_cheese_suspected", True)
    blackboard.set("early_scout_gas_time", 80.0)
    blackboard.set("early_scout_natural_confirmed", False)

    bot = SimpleNamespace(
        blackboard=blackboard,
        time=120.0,
        iteration=44,
        workers=UnitGroup([MockUnit("DRONE") for _ in range(20)]),
        townhalls=SimpleNamespace(ready=UnitGroup([MockStructure("HATCHERY")]), amount=1),
        supply_left=8,
        production=None,
    )

    manager = EconomyManager(bot)
    await manager._train_drone_if_needed()

    assert manager._should_delay_opening_expansion(1) is True
    assert all(len(queue) == 0 for queue in blackboard.production_queue.values())
