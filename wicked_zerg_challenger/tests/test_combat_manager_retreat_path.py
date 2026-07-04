# -*- coding: utf-8 -*-
"""
Unit tests for CombatManager._retreat_to_closest_base using rust_accel's
calculate_retreat_path (prefers creep/spine-crawler-backed bases over the
purely geometric closest one).
"""

import os
import sys
import unittest
from unittest.mock import Mock

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from combat_manager import CombatManager
from sc2.ids.unit_typeid import UnitTypeId
from sc2.position import Point2


def make_structure(position):
    structure = Mock()
    structure.position = position
    return structure


class FakeUnits(list):
    """Minimal stand-in for sc2's Units collection: a list plus `.exists`."""

    @property
    def exists(self):
        return len(self) > 0


class TestRetreatToClosestBaseRustAccel(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        self.bot = Mock()
        self.bot.units = Mock()
        self.bot.enemy_units = Mock()
        self.bot.iteration = 0
        self.bot.time = 0
        self.manager = CombatManager(self.bot)

    async def test_prefers_spine_backed_base_over_nearer_undefended_one(self):
        unit = Mock()
        unit.position = Point2((0, 0))

        near_undefended_base = Point2((5, 0))
        far_defended_base = Point2((20, 0))

        self.bot.townhalls = FakeUnits(
            [
                make_structure(near_undefended_base),
                make_structure(far_defended_base),
            ]
        )

        def structures(unit_type):
            if unit_type == UnitTypeId.SPINECRAWLER:
                return FakeUnits([make_structure(far_defended_base)])
            return FakeUnits([])

        self.bot.structures = Mock(side_effect=structures)
        self.bot.do = Mock()

        await self.manager._retreat_to_closest_base([unit])

        self.bot.do.assert_called_once()
        move_call = unit.move.call_args
        target = move_call.args[0]
        # Should retreat to the spine-crawler-backed base, not the merely closer one.
        self.assertAlmostEqual(target.x, far_defended_base.x, places=3)
        self.assertAlmostEqual(target.y, far_defended_base.y, places=3)

    async def test_falls_back_to_main_base_without_townhalls(self):
        unit = Mock()
        unit.position = Point2((0, 0))

        self.bot.townhalls = Mock()
        self.bot.townhalls.exists = False
        self.bot.start_location = Point2((20, 20))
        self.bot.do = Mock()

        await self.manager._retreat_to_closest_base([unit])

        self.bot.do.assert_called_once()
        move_call = unit.move.call_args
        target = move_call.args[0]
        self.assertEqual((target.x, target.y), (20, 20))


if __name__ == "__main__":
    unittest.main()
