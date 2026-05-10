# -*- coding: utf-8 -*-
import json
import os
import sys
import tempfile
import unittest
from pathlib import Path

os.environ["PROTOCOL_BUFFERS_PYTHON_IMPLEMENTATION"] = "python"
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))

# See test_ladder_tracker.py for why we go through importlib here.
import importlib.util as _ilu

_MA_PATH = os.path.abspath(
    os.path.join(os.path.dirname(__file__), "..", "..", "scripts", "meta_adapter.py")
)
_MA_SPEC = _ilu.spec_from_file_location("scripts_meta_adapter", _MA_PATH)
_MA_MOD = _ilu.module_from_spec(_MA_SPEC)
sys.modules[_MA_SPEC.name] = _MA_MOD
_MA_SPEC.loader.exec_module(_MA_MOD)
MetaAdapter = _MA_MOD.MetaAdapter


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
