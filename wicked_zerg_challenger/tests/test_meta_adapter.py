# -*- coding: utf-8 -*-
import importlib.util
import json
import os
import sys
import tempfile
import unittest
from pathlib import Path

os.environ["PROTOCOL_BUFFERS_PYTHON_IMPLEMENTATION"] = "python"
_REPO_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
sys.path.insert(0, _REPO_ROOT)

# wicked_zerg_challenger/local_training/scripts is a *separate* regular
# package also named "scripts" (has __init__.py). When both it and the
# repo root are on sys.path, Python's import system resolves the regular
# package over this namespace package (PEP 420) regardless of sys.path
# order, so `from scripts.meta_adapter import ...` can silently bind to
# the wrong package during full-suite collection. Load by explicit path
# instead of relying on "scripts" name resolution.
_spec = importlib.util.spec_from_file_location(
    "wzc_meta_adapter_module", os.path.join(_REPO_ROOT, "scripts", "meta_adapter.py")
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
            Path(tmp, "analytics.json").write_text(json.dumps(analytics), encoding="utf-8")

            adjustments = MetaAdapter(tmp).generate_strategy_adjustments()

            self.assertIn("ZvT", adjustments)
            self.assertTrue(Path(tmp, "strategy_adjustments.json").exists())

    def test_missing_analytics_returns_empty(self):
        with tempfile.TemporaryDirectory() as tmp:
            self.assertEqual(MetaAdapter(tmp).generate_strategy_adjustments(), {})


if __name__ == "__main__":
    unittest.main()
