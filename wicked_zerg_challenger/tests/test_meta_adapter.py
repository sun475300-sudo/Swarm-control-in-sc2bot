# -*- coding: utf-8 -*-
import importlib.util
import json
import os
import sys
import tempfile
import unittest
from pathlib import Path

os.environ["PROTOCOL_BUFFERS_PYTHON_IMPLEMENTATION"] = "python"

# Loaded by explicit file path (not `from scripts.meta_adapter import ...`) because
# `wicked_zerg_challenger/local_training/scripts` is a *separate*, unrelated regular
# package also named `scripts`; whichever one lands on sys.path first during a full
# test run shadows the other and breaks this import depending on test order.
_REPO_ROOT = Path(__file__).resolve().parents[2]
_spec = importlib.util.spec_from_file_location(
    "meta_adapter_module", _REPO_ROOT / "scripts" / "meta_adapter.py"
)
_meta_adapter = importlib.util.module_from_spec(_spec)
sys.modules[_spec.name] = _meta_adapter
_spec.loader.exec_module(_meta_adapter)
MetaAdapter = _meta_adapter.MetaAdapter


class TestMetaAdapter(unittest.TestCase):
    def test_generate_strategy_adjustments_for_low_winrate(self):
        with tempfile.TemporaryDirectory() as tmp:
            analytics = {
                "overall": {"crash_rate": 0.0},
                "vs_terran": {"total": 5, "winrate": 40.0},
                "vs_protoss": {"total": 0, "winrate": 0.0},
                "vs_zerg": {"total": 3, "winrate": 66.0},
                "weaknesses": {},
            }
            Path(tmp, "analytics.json").write_text(
                json.dumps(analytics), encoding="utf-8"
            )

            adjustments = MetaAdapter(tmp).generate_strategy_adjustments()

            self.assertIn("ZvT", adjustments)
            self.assertTrue(Path(tmp, "strategy_adjustments.json").exists())

    def test_missing_analytics_returns_empty(self):
        with tempfile.TemporaryDirectory() as tmp:
            self.assertEqual(MetaAdapter(tmp).generate_strategy_adjustments(), {})


if __name__ == "__main__":
    unittest.main()
