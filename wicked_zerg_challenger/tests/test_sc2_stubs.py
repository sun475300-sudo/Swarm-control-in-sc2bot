# -*- coding: utf-8 -*-
"""Tests for utils.sc2_stubs lenient fallback helper."""

import os
import sys
import unittest

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from utils.sc2_stubs import get_sc2_imports


class TestSc2StubsRealImports(unittest.TestCase):
    """When python-sc2 is installed, real classes are returned."""

    def test_returns_six_classes(self):
        result = get_sc2_imports()
        self.assertEqual(len(result), 6)

    def test_unit_type_id_has_overlord(self):
        _BotAI, UnitTypeId, _AbilityId, _UpgradeId, _Point2, _Unit = get_sc2_imports()
        # In a normal CI run python-sc2 is available; the test environment
        # for this suite installs burnysc2, so OVERLORD should exist.
        self.assertTrue(hasattr(UnitTypeId, "OVERLORD"))


class TestSc2StubsLenientFallback(unittest.TestCase):
    """Validate that the lenient stub gives importable classes when sc2 is
    missing without raising AttributeError on enum-style member access."""

    def test_lenient_meta_returns_sentinel_with_name(self):
        from utils.sc2_stubs import _StubUnitTypeId  # private but stable

        sentinel = _StubUnitTypeId.OVERLORD
        self.assertEqual(sentinel.name, "OVERLORD")
        self.assertIsInstance(sentinel, _StubUnitTypeId)

    def test_lenient_meta_arbitrary_lookup(self):
        from utils.sc2_stubs import _StubAbilityId, _StubUpgradeId

        self.assertEqual(_StubAbilityId.SOMENEWABILITY.name, "SOMENEWABILITY")
        self.assertEqual(_StubUpgradeId.METABOLICBOOST.name, "METABOLICBOOST")

    def test_stubs_can_be_used_as_default_argument(self):
        """Reproduce the original collection-time crash: a function whose
        default value is a stub enum member should now be definable."""
        from utils.sc2_stubs import _StubUnitTypeId

        def _f(x=_StubUnitTypeId.OVERLORD):
            return x

        self.assertEqual(_f().name, "OVERLORD")


if __name__ == "__main__":
    unittest.main()
