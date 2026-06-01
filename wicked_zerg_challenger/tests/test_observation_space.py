# -*- coding: utf-8 -*-
import os
import sys
import unittest
from unittest.mock import MagicMock

import pytest

os.environ["PROTOCOL_BUFFERS_PYTHON_IMPLEMENTATION"] = "python"
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

try:
    from local_training.sc2_env import SC2ActionSpace, SC2Observation, UnitTypeId
except ImportError:
    pytest.skip(
        "local_training.sc2_env dependencies not available (numpy/sc2)",
        allow_module_level=True,
    )


class TestObservationSpace(unittest.TestCase):
    def test_observation_is_16d_and_normalized(self):
        bot = MagicMock()
        bot.minerals = 500
        bot.vespene = 200
        bot.supply_used = 50
        bot.supply_army = 20
        bot.supply_left = 5
        bot.time = 120
        bot.start_location = MagicMock()
        bot.workers.amount = 30
        bot.townhalls.amount = 2
        bot.enemy_units.amount = 3
        bot.enemy_units.closer_than.return_value = []
        bot.enemy_structures.amount = 4

        ready = MagicMock()
        ready.exists = True
        structures = MagicMock()
        structures.ready = ready
        bot.structures.return_value = structures

        unit_amounts = {
            UnitTypeId.QUEEN: 3,
            UnitTypeId.ZERGLING: 12,
            UnitTypeId.ROACH: 5,
            UnitTypeId.HYDRALISK: 2,
        }

        def units(unit_type):
            collection = MagicMock()
            collection.amount = unit_amounts.get(unit_type, 0)
            return collection

        bot.units.side_effect = units

        observation = SC2Observation.from_bot(bot)

        self.assertEqual(observation.shape, (16,))
        self.assertGreaterEqual(float(observation.min()), 0.0)
        self.assertLessEqual(float(observation.max()), 1.0)

    def test_action_space_labels(self):
        self.assertTrue(SC2ActionSpace.contains(3))
        self.assertEqual(SC2ActionSpace.label(3), "ATTACK")


if __name__ == "__main__":
    unittest.main()
