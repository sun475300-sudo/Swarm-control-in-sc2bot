# -*- coding: utf-8 -*-
import importlib.util
import json
import os
import sys
import tempfile
import unittest
from pathlib import Path

os.environ["PROTOCOL_BUFFERS_PYTHON_IMPLEMENTATION"] = "python"

# Load scripts/meta_adapter.py directly by file path instead of via
# `import scripts` — the bare "scripts" package name collides with
# wicked_zerg_challenger/local_training/scripts (also has an __init__.py),
# which other tests may have already put on sys.path, and a regular
# package there wins name resolution over the repo-root scripts/ package
# regardless of sys.path order.
_meta_adapter_path = os.path.join(
    os.path.dirname(__file__), "..", "..", "scripts", "meta_adapter.py"
)
_spec = importlib.util.spec_from_file_location(
    "_meta_adapter_standalone", _meta_adapter_path
)
_meta_adapter_module = importlib.util.module_from_spec(_spec)
sys.modules[_spec.name] = _meta_adapter_module
_spec.loader.exec_module(_meta_adapter_module)
MetaAdapter = _meta_adapter_module.MetaAdapter


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
