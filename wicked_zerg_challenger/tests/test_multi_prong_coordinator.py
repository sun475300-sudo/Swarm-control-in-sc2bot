"""
Tests for staggered multi-prong departure timing (ROADMAP Sprint 4.4).

Verifies that MultiProngCoordinator computes departure delays so that
prongs starting farther from (or slower toward) their target leave
immediately while closer/faster prongs wait, aiming for simultaneous
arrival — and that units held before their departure time hold position
instead of attacking early.
"""

import os
import sys

import pytest

pytest.importorskip("sc2")

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from combat.multi_prong_coordinator import MultiProngCoordinator  # noqa: E402
from sc2.position import Point2  # noqa: E402


class FakeUnit:
    def __init__(self, tag, position, movement_speed=4.13):
        self.tag = tag
        self.position = position
        self.movement_speed = movement_speed

    def attack(self, target):
        return ("attack", self.tag, target)

    def hold_position(self):
        return ("hold", self.tag)


class FakeUnitsCollection:
    def __init__(self, units):
        self._by_tag = {u.tag: u for u in units}

    def find_by_tag(self, tag):
        return self._by_tag.get(tag)


class FakeBot:
    def __init__(self, units, time=100.0):
        self.units = FakeUnitsCollection(units)
        self.time = time
        self.do_calls = []

    def do(self, action):
        self.do_calls.append(action)


@pytest.fixture
def coordinator_with_prongs():
    # Main army: slow (roach speed), far from its target -> long travel time.
    main_units = [FakeUnit(1, Point2((0, 0)), movement_speed=3.15)]
    # Runby: fast (zergling speed), close to its target -> short travel time.
    runby_units = [FakeUnit(2, Point2((0, 0)), movement_speed=4.13)]

    bot = FakeBot(main_units + runby_units, time=100.0)
    coordinator = MultiProngCoordinator(bot)

    coordinator.prong_assignments["main_army"] = {1}
    coordinator.prong_assignments["zergling_runby"] = {2}
    coordinator.prong_targets["main_army"] = Point2((100, 0))
    coordinator.prong_targets["zergling_runby"] = Point2((30, 0))

    return coordinator, bot


class TestComputeDepartureTimes:
    def test_farther_slower_prong_departs_immediately(self, coordinator_with_prongs):
        coordinator, bot = coordinator_with_prongs
        departures = coordinator._compute_departure_times()
        assert departures["main_army"] == pytest.approx(bot.time)

    def test_closer_faster_prong_is_delayed(self, coordinator_with_prongs):
        coordinator, bot = coordinator_with_prongs
        departures = coordinator._compute_departure_times()
        assert departures["zergling_runby"] > bot.time

    def test_delays_align_arrival_time(self, coordinator_with_prongs):
        coordinator, bot = coordinator_with_prongs
        departures = coordinator._compute_departure_times()

        main_travel = 100 / 3.15
        runby_travel = 30 / 4.13
        main_arrival = departures["main_army"] + main_travel
        runby_arrival = departures["zergling_runby"] + runby_travel

        assert main_arrival == pytest.approx(runby_arrival, abs=0.01)

    def test_empty_assignments_returns_empty(self):
        bot = FakeBot([], time=50.0)
        coordinator = MultiProngCoordinator(bot)
        assert coordinator._compute_departure_times() == {}

    def test_missing_units_are_skipped(self):
        bot = FakeBot([], time=50.0)
        coordinator = MultiProngCoordinator(bot)
        coordinator.prong_assignments["main_army"] = {999}
        coordinator.prong_targets["main_army"] = Point2((10, 10))
        assert coordinator._compute_departure_times() == {}


class TestExecuteMultiProngRespectsDeparture:
    @pytest.mark.asyncio
    async def test_undeparted_prong_holds_position(self, coordinator_with_prongs):
        coordinator, bot = coordinator_with_prongs
        coordinator.prong_departure_time = {
            "main_army": bot.time,
            "zergling_runby": bot.time + 20.0,
        }
        coordinator.attack_start_time = bot.time

        await coordinator._execute_multi_prong()

        assert ("attack", 1, Point2((100, 0))) in bot.do_calls
        assert ("hold", 2) in bot.do_calls
        assert ("attack", 2, Point2((30, 0))) not in bot.do_calls

    @pytest.mark.asyncio
    async def test_departed_prong_attacks(self, coordinator_with_prongs):
        coordinator, bot = coordinator_with_prongs
        coordinator.prong_departure_time = {
            "main_army": bot.time,
            "zergling_runby": bot.time + 20.0,
        }
        coordinator.attack_start_time = bot.time

        bot.time += 20.0
        await coordinator._execute_multi_prong()

        assert ("attack", 2, Point2((30, 0))) in bot.do_calls
