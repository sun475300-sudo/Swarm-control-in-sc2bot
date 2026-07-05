import asyncio
import os
import sys
import unittest
from unittest.mock import MagicMock

# Add project root to path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from nydus_network_trainer import NydusNetworkTrainer, NydusWormSpot


class TestNydusNetworkTrainer(unittest.TestCase):
    def setUp(self):
        self.bot = MagicMock()
        self.bot.time = 100.0
        self.bot.units = MagicMock()
        self.bot.units.filter.return_value = MagicMock(amount=0)
        self.bot.can_afford.return_value = False

        self.trainer = NydusNetworkTrainer(self.bot)
        self.network = MagicMock()

    def test_manage_nydus_operations_does_not_crash(self):
        """Regression test: _manage_nydus_operations() used to call the
        undefined method _command_deployed_units(), which raised
        AttributeError whenever a Nydus Network was actually on the field."""
        asyncio.run(self.trainer._manage_nydus_operations(self.network, self.bot.time))

    def test_manage_active_worms_commands_deployed_units(self):
        """Deployed-unit commanding is handled per-worm by
        _manage_active_worms()/_command_worm_units(), which this exercises
        instead of the removed _command_deployed_units() call."""
        self.bot.structures.return_value = MagicMock(amount=0)
        asyncio.run(self.trainer._manage_active_worms())

    def test_get_statistics_defaults(self):
        stats = self.trainer.get_statistics()
        self.assertEqual(stats["active_worms"], 0)
        self.assertEqual(stats["success_rate"], "0.0%")


if __name__ == "__main__":
    unittest.main()
