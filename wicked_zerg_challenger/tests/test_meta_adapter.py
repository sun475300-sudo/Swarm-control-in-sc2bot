# -*- coding: utf-8 -*-
import importlib.util
import json
import os
import sys
import tempfile
import unittest
from pathlib import Path

os.environ["PROTOCOL_BUFFERS_PYTHON_IMPLEMENTATION"] = "python"
_PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
if _PROJECT_ROOT not in sys.path:
    sys.path.insert(0, _PROJECT_ROOT)


def _load_meta_adapter():
    # 다른 테스트의 ``sys.path`` 변경으로 ``scripts`` namespace package가
    # 잘못된 위치에 캐시될 수 있어 파일 경로로 직접 로드한다. ``dataclasses``는
    # 모듈을 ``sys.modules``에서 조회하므로 exec 전에 등록해두어야 한다.
    mod_name = "scripts_meta_adapter"
    src = os.path.join(_PROJECT_ROOT, "scripts", "meta_adapter.py")
    spec = importlib.util.spec_from_file_location(mod_name, src)
    if spec is None or spec.loader is None:
        raise ImportError(f"cannot load {src}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[mod_name] = module
    spec.loader.exec_module(module)
    return module.MetaAdapter


MetaAdapter = _load_meta_adapter()


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
