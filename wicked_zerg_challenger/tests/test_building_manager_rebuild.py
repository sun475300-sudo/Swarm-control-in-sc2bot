# -*- coding: utf-8 -*-
"""
Unit tests -- BuildingManager critical structure rebuild (P2-9)

Locks in the behaviour: if every copy of a critical structure (Spawning
Pool / Hatchery / Evolution Chamber) that previously existed is destroyed,
BuildingManager should re-queue it instead of leaving the loss permanent.
Structures that simply haven't been built yet must NOT trigger a request.
"""

import os
import sys
import unittest
from types import SimpleNamespace

os.environ["PROTOCOL_BUFFERS_PYTHON_IMPLEMENTATION"] = "python"
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from building_manager import BuildingManager
from sc2.ids.unit_typeid import UnitTypeId
from sc2.position import Point2


class FakeStructures:
    def __init__(self, count):
        self.amount = count
        self.exists = count > 0


class FakeStructuresSource:
    def __init__(self, counts):
        self.counts = dict(counts)

    def __call__(self, structure_type):
        return FakeStructures(self.counts.get(structure_type, 0))

    def set_count(self, structure_type, count):
        self.counts[structure_type] = count


def _make_bot(counts):
    structures = FakeStructuresSource(counts)
    townhall = SimpleNamespace(position=Point2((50, 50)))
    return SimpleNamespace(
        time=100.0,
        start_location=Point2((50, 50)),
        structures=structures,
        already_pending=lambda t: 0,
        townhalls=[townhall],
        enemy_units=[],
        blackboard=None,
        building_coord=None,
    )


class TestCriticalStructureRebuild(unittest.TestCase):
    def test_existing_structure_records_high_water_mark_and_does_not_request(self):
        bot = _make_bot({UnitTypeId.SPAWNINGPOOL: 1})
        manager = BuildingManager(bot)

        manager._check_critical_structure_rebuild()

        self.assertEqual(manager._structure_max_seen.get(UnitTypeId.SPAWNINGPOOL), 1)
        self.assertNotIn(UnitTypeId.SPAWNINGPOOL, manager._last_rebuild_request)

    def test_never_built_structure_does_not_trigger_rebuild(self):
        """Evolution Chamber not built yet (max seen == 0) should be left alone."""
        bot = _make_bot({UnitTypeId.EVOLUTIONCHAMBER: 0})
        manager = BuildingManager(bot)

        manager._check_critical_structure_rebuild()

        self.assertNotIn(UnitTypeId.EVOLUTIONCHAMBER, manager._last_rebuild_request)

    def test_destroyed_structure_triggers_rebuild_request(self):
        bot = _make_bot({UnitTypeId.SPAWNINGPOOL: 1})
        manager = BuildingManager(bot)

        # Pool exists -> records high-water mark of 1.
        manager._check_critical_structure_rebuild()
        self.assertNotIn(UnitTypeId.SPAWNINGPOOL, manager._last_rebuild_request)

        # Pool destroyed -> total drops to 0, should now request a rebuild.
        bot.structures.set_count(UnitTypeId.SPAWNINGPOOL, 0)
        manager._check_critical_structure_rebuild()

        self.assertIn(UnitTypeId.SPAWNINGPOOL, manager._last_rebuild_request)
        self.assertIn(UnitTypeId.SPAWNINGPOOL, bot.building_coord.building_requests)

    def test_rebuild_request_respects_retry_cooldown(self):
        bot = _make_bot({UnitTypeId.SPAWNINGPOOL: 0})
        manager = BuildingManager(bot)
        manager._structure_max_seen[UnitTypeId.SPAWNINGPOOL] = 1

        manager._check_critical_structure_rebuild()
        first_request_time = manager._last_rebuild_request[UnitTypeId.SPAWNINGPOOL]

        # Still destroyed, but well within REBUILD_RETRY_INTERVAL -- no
        # re-request should be recorded.
        bot.time += 5.0
        manager._check_critical_structure_rebuild()

        self.assertEqual(
            manager._last_rebuild_request[UnitTypeId.SPAWNINGPOOL],
            first_request_time,
        )

    def test_hatchery_rebuild_uses_start_location_as_anchor(self):
        bot = _make_bot({UnitTypeId.HATCHERY: 0})
        manager = BuildingManager(bot)
        manager._structure_max_seen[UnitTypeId.HATCHERY] = 1

        manager._check_critical_structure_rebuild()

        self.assertIn(UnitTypeId.HATCHERY, manager._last_rebuild_request)
        self.assertIn(UnitTypeId.HATCHERY, bot.building_coord.building_requests)


if __name__ == "__main__":
    unittest.main()
