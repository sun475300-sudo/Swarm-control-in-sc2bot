# -*- coding: utf-8 -*-
"""Tests for config/build_orders.yaml externalization (PLAN-NIGHTLY.md P2.3)."""

import os
import sys
import tempfile
import unittest

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

import build_order_system as bos
from build_order_system import (
    BUILD_ORDERS_YAML_PATH,
    ZVP_BUILDS,
    ZVT_BUILDS,
    ZVZ_BUILDS,
    _load_build_orders_from_yaml,
    _resolve_build_order_token,
)


class TestBuildOrdersYamlFile(unittest.TestCase):
    def test_yaml_file_exists(self):
        self.assertTrue(os.path.isfile(BUILD_ORDERS_YAML_PATH))

    def test_module_builds_match_yaml_source(self):
        zvt, zvp, zvz = _load_build_orders_from_yaml()
        self.assertEqual(zvt, ZVT_BUILDS)
        self.assertEqual(zvp, ZVP_BUILDS)
        self.assertEqual(zvz, ZVZ_BUILDS)

    def test_loaded_builds_match_built_in_defaults(self):
        # The YAML content must reproduce the built-in defaults exactly so
        # externalizing the config doesn't change bot behaviour.
        self.assertEqual(ZVT_BUILDS, bos._DEFAULT_ZVT_BUILDS)
        self.assertEqual(ZVP_BUILDS, bos._DEFAULT_ZVP_BUILDS)
        self.assertEqual(ZVZ_BUILDS, bos._DEFAULT_ZVZ_BUILDS)

    def test_build_keys_present(self):
        self.assertEqual(
            set(ZVT_BUILDS),
            {"hatch_first_16", "aggressive_pool_first", "fast_lair_macro"},
        )
        self.assertEqual(
            set(ZVP_BUILDS),
            {"roach_rush", "ling_flood_anti_cannon", "hydra_lair_macro"},
        )
        self.assertEqual(
            set(ZVZ_BUILDS),
            {"safe_14pool", "12pool_rush", "roach_warren_macro"},
        )

    def test_every_build_has_required_fields(self):
        for builds in (ZVT_BUILDS, ZVP_BUILDS, ZVZ_BUILDS):
            for key, build in builds.items():
                for field in ("name", "condition", "order", "transition", "note"):
                    self.assertIn(field, build, f"{key} missing '{field}'")
                self.assertGreater(len(build["order"]), 0, f"{key} has empty order")
                for supply, _unit_type in build["order"]:
                    self.assertIsInstance(supply, int)
                    self.assertGreater(supply, 0)


class TestResolveBuildOrderToken(unittest.TestCase):
    def test_resolves_known_unit_type(self):
        from build_order_system import UnitTypeId

        self.assertEqual(_resolve_build_order_token("OVERLORD"), UnitTypeId.OVERLORD)

    def test_passes_through_non_unit_marker(self):
        self.assertEqual(
            _resolve_build_order_token("METABOLIC_BOOST"), "METABOLIC_BOOST"
        )


class TestBuildOrdersYamlFallback(unittest.TestCase):
    def test_missing_file_falls_back_to_defaults(self):
        zvt, zvp, zvz = _load_build_orders_from_yaml("/nonexistent/build_orders.yaml")
        self.assertEqual(zvt, bos._DEFAULT_ZVT_BUILDS)
        self.assertEqual(zvp, bos._DEFAULT_ZVP_BUILDS)
        self.assertEqual(zvz, bos._DEFAULT_ZVZ_BUILDS)

    def test_malformed_file_falls_back_to_defaults(self):
        with tempfile.NamedTemporaryFile(
            "w", suffix=".yaml", delete=False, encoding="utf-8"
        ) as f:
            f.write("not: [valid, structure")
            bad_path = f.name
        try:
            zvt, zvp, zvz = _load_build_orders_from_yaml(bad_path)
            self.assertEqual(zvt, bos._DEFAULT_ZVT_BUILDS)
        finally:
            os.unlink(bad_path)

    def test_empty_file_falls_back_to_defaults(self):
        with tempfile.NamedTemporaryFile(
            "w", suffix=".yaml", delete=False, encoding="utf-8"
        ) as f:
            f.write("")
            empty_path = f.name
        try:
            zvt, zvp, zvz = _load_build_orders_from_yaml(empty_path)
            self.assertEqual(zvt, bos._DEFAULT_ZVT_BUILDS)
        finally:
            os.unlink(empty_path)

    def test_yaml_module_unavailable_falls_back_to_defaults(self):
        original_yaml = bos.yaml
        bos.yaml = None
        try:
            zvt, zvp, zvz = _load_build_orders_from_yaml()
            self.assertEqual(zvt, bos._DEFAULT_ZVT_BUILDS)
        finally:
            bos.yaml = original_yaml


if __name__ == "__main__":
    unittest.main()
