# -*- coding: utf-8 -*-
import json
import os
import sys
import tempfile
import unittest
from pathlib import Path

os.environ["PROTOCOL_BUFFERS_PYTHON_IMPLEMENTATION"] = "python"
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from arena.preflight_validator import PreflightValidator


class TestArenaPreflight(unittest.TestCase):
    def make_project(self, root):
        (root / "run.py").write_text("print('ok')", encoding="utf-8")
        (root / "ladderbots.json").write_text(
            json.dumps(
                {
                    "Bots": {
                        "bot": {"Race": "Zerg", "Type": "Python", "FileName": "run.py"}
                    }
                }
            ),
            encoding="utf-8",
        )
        (root / "requirements.txt").write_text("burnysc2>=5", encoding="utf-8")
        for filename in PreflightValidator.REQUIRED_RUNTIME_FILES:
            path = root / "wicked_zerg_challenger" / filename
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text("# runtime", encoding="utf-8")

    def test_preflight_passes_with_required_files(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            self.make_project(root)

            result = PreflightValidator(str(root)).validate()

            self.assertTrue(result.passed)
            self.assertEqual(result.errors, [])

    def test_preflight_reports_missing_files(self):
        with tempfile.TemporaryDirectory() as tmp:
            result = PreflightValidator(tmp).validate()

            self.assertFalse(result.passed)
            self.assertTrue(any("run.py" in error for error in result.errors))

    def test_preflight_rejects_missing_economy_runtime(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            self.make_project(root)
            (
                root
                / "wicked_zerg_challenger/local_training/economy_combat_balancer.py"
            ).unlink()

            result = PreflightValidator(tmp).validate()

            self.assertFalse(result.passed)
            self.assertTrue(
                any("economy_combat_balancer.py" in error for error in result.errors)
            )

    def assert_invalid_manifest(self, contents):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            self.make_project(root)
            (root / "ladderbots.json").write_text(contents, encoding="utf-8")
            self.assertFalse(PreflightValidator(tmp).validate().passed)

    # Separate cases give each malformed input its own JUnit testcase. Pytest
    # 9's passing unittest subtests increase suite totals without XML testcases.
    def test_preflight_rejects_malformed_json(self):
        self.assert_invalid_manifest("{")

    def test_preflight_rejects_list_manifest(self):
        self.assert_invalid_manifest("[]")

    def test_preflight_rejects_empty_manifest(self):
        self.assert_invalid_manifest("{}")

    def test_preflight_rejects_missing_entrypoint(self):
        self.assert_invalid_manifest('{"Bots":{"bot":{"FileName":"missing.py"}}}')

    def test_valid_lurker_ids_do_not_raise_warning(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            self.make_project(root)
            path = root / "wicked_zerg_challenger/economy_manager.py"
            path.write_text(
                "UnitTypeId.LURKERMP\nUnitTypeId.LURKERMPBURROWED", encoding="utf-8"
            )
            self.assertEqual(PreflightValidator(tmp).validate().warnings, [])
            path.write_text("UnitTypeId.LURKER", encoding="utf-8")
            self.assertEqual(len(PreflightValidator(tmp).validate().warnings), 1)


if __name__ == "__main__":
    unittest.main()
