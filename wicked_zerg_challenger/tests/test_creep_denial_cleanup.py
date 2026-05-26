# -*- coding: utf-8 -*-
"""Regression: _cleanup_old_tumor_data must not double-delete entries."""

import os
import sys
import unittest
from unittest.mock import Mock

os.environ["PROTOCOL_BUFFERS_PYTHON_IMPLEMENTATION"] = "python"
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from creep_denial_system import CreepDenialSystem, DetectedTumor
from sc2.position import Point2


class TestCleanupOldTumorData(unittest.TestCase):
    def setUp(self):
        self.bot = Mock()
        self.bot.time = 1000.0

        self.system = CreepDenialSystem.__new__(CreepDenialSystem)
        self.system.bot = self.bot
        self.system.logger = Mock()
        self.system.detected_tumors = {}
        self.system.tumor_memory_duration = 60.0
        self.system.tumors_destroyed = 0
        self.system.unit_authority = None
        self.system.managed_units = set()
        self.system._tumor_exists = Mock(return_value=False)

    def test_double_match_does_not_crash(self):
        # Tumor is both stale (last_seen long ago) AND destroyed (unit gone).
        # Old impl would append twice to to_remove and KeyError on the
        # second del.
        tumor = DetectedTumor(
            position=Point2((10, 10)),
            detection_time=0.0,
            last_seen=0.0,
            unit_tag=42,
        )
        self.system.detected_tumors[42] = tumor

        # Should not raise
        self.system._cleanup_old_tumor_data(self.bot.time)
        self.assertNotIn(42, self.system.detected_tumors)

    def test_stale_only_removed(self):
        tumor = DetectedTumor(
            position=Point2((10, 10)),
            detection_time=0.0,
            last_seen=0.0,
            unit_tag=None,
        )
        self.system.detected_tumors[7] = tumor

        self.system._cleanup_old_tumor_data(self.bot.time)
        self.assertNotIn(7, self.system.detected_tumors)


if __name__ == "__main__":
    unittest.main()
