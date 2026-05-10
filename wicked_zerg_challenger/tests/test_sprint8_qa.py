# -*- coding: utf-8 -*-
"""Tests for ROADMAP Sprint 8 QA helpers."""

import os
import sys
import unittest

import pytest

pytest.importorskip("sc2", reason="python-sc2 library not installed")

os.environ["PROTOCOL_BUFFERS_PYTHON_IMPLEMENTATION"] = "python"
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from run_mass_test import build_test_cases, parse_args


class TestRunMassTestCli(unittest.TestCase):
    def test_roadmap_medium_terran_command_builds_ten_games(self):
        args = parse_args(
            ["--opponent", "Terran", "--difficulty", "Medium", "--games", "10"]
        )

        cases = build_test_cases(args)

        self.assertEqual(len(cases), 10)
        self.assertEqual({case[1].name for case in cases}, {"Terran"})
        self.assertEqual({case[3] for case in cases}, {"Medium"})

    def test_dry_run_flag_parses_without_changing_matrix(self):
        args = parse_args(
            [
                "--opponent",
                "Zerg",
                "--difficulty",
                "Medium",
                "--games",
                "3",
                "--maps",
                "AbyssalReefLE,OdysseyLE",
                "--dry-run",
            ]
        )

        cases = build_test_cases(args)

        self.assertTrue(args.dry_run)
        self.assertEqual(
            [case[0] for case in cases], ["AbyssalReefLE", "OdysseyLE", "AbyssalReefLE"]
        )


if __name__ == "__main__":
    unittest.main()
