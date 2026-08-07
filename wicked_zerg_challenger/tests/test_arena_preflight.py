# -*- coding: utf-8 -*-
import os
import sys
import tempfile
import unittest
from pathlib import Path

os.environ["PROTOCOL_BUFFERS_PYTHON_IMPLEMENTATION"] = "python"
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from arena.preflight_validator import PreflightValidator


class TestArenaPreflight(unittest.TestCase):
    def test_preflight_passes_with_required_files(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "run.py").write_text("print('ok')", encoding="utf-8")
            (root / "ladderbots.json").write_text("{}", encoding="utf-8")
            (root / "requirements.txt").write_text("burnysc2>=5", encoding="utf-8")
            (root / "wicked_zerg_challenger").mkdir()

            result = PreflightValidator(str(root)).validate()

            self.assertTrue(result.passed)
            self.assertEqual(result.errors, [])

    def test_preflight_reports_missing_files(self):
        with tempfile.TemporaryDirectory() as tmp:
            result = PreflightValidator(tmp).validate()

            self.assertFalse(result.passed)
            self.assertTrue(any("run.py" in error for error in result.errors))

    def test_lurkermp_references_do_not_trigger_lurker_warning(self):
        """UnitTypeId.LURKERMP is the valid python-sc2 id; it must not be
        mistaken for the invalid bare UnitTypeId.LURKER."""
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "run.py").write_text("print('ok')", encoding="utf-8")
            (root / "ladderbots.json").write_text("{}", encoding="utf-8")
            (root / "requirements.txt").write_text("burnysc2>=5", encoding="utf-8")
            pkg = root / "wicked_zerg_challenger"
            pkg.mkdir()
            (pkg / "combat.py").write_text(
                "for lurker in self.bot.units(UnitTypeId.LURKERMP):\n    pass\n",
                encoding="utf-8",
            )

            result = PreflightValidator(str(root)).validate()

            self.assertEqual(result.warnings, [])

    def test_bare_lurker_reference_triggers_warning(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "run.py").write_text("print('ok')", encoding="utf-8")
            (root / "ladderbots.json").write_text("{}", encoding="utf-8")
            (root / "requirements.txt").write_text("burnysc2>=5", encoding="utf-8")
            pkg = root / "wicked_zerg_challenger"
            pkg.mkdir()
            (pkg / "combat.py").write_text(
                "for lurker in self.bot.units(UnitTypeId.LURKER):\n    pass\n",
                encoding="utf-8",
            )

            result = PreflightValidator(str(root)).validate()

            self.assertTrue(any("LURKER" in warning for warning in result.warnings))


if __name__ == "__main__":
    unittest.main()
