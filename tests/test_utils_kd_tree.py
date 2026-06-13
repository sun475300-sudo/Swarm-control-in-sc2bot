# -*- coding: utf-8 -*-
"""utils.kd_tree 테스트 - K-D 트리 공간 인덱싱"""

import sys
import importlib.util
from pathlib import Path

import pytest

PROJECT_ROOT = Path(__file__).parent.parent
BOT_ROOT = PROJECT_ROOT / "wicked_zerg_challenger"
if str(BOT_ROOT) not in sys.path:
    sys.path.insert(0, str(BOT_ROOT))


def _load():
    if "bot_kd_tree" in sys.modules:
        return sys.modules["bot_kd_tree"]
    spec = importlib.util.spec_from_file_location(
        "bot_kd_tree", BOT_ROOT / "utils" / "kd_tree.py"
    )
    mod = importlib.util.module_from_spec(spec)
    sys.modules["bot_kd_tree"] = mod
    spec.loader.exec_module(mod)
    return mod


class TestInit:
    def test_empty(self):
        t = _load().KDTree()
        assert t.root is None and t.size == 0
        assert len(t) == 0 and bool(t) is False

    def test_with_points(self):
        t = _load().KDTree([((1.0, 2.0), "a"), ((3.0, 4.0), "b")])
        assert t.size == 2 and bool(t) is True


class TestNearestNeighbor:
    def test_empty(self):
        assert _load().KDTree().nearest_neighbor((0, 0)) is None

    def test_single(self):
        t = _load().KDTree([((5.0, 5.0), "s")])
        p, d, dist = t.nearest_neighbor((0, 0))
        assert d == "s"

    def test_finds_closest(self):
        t = _load().KDTree([((0.0, 0.0), "a"), ((10.0, 10.0), "b"), ((100.0, 100.0), "c")])
        _, d, _ = t.nearest_neighbor((1.0, 1.0))
        assert d == "a"

    def test_exclude(self):
        t = _load().KDTree([((1.0, 1.0), "self"), ((10.0, 10.0), "other")])
        _, d, _ = t.nearest_neighbor((1.0, 1.0), exclude_data="self")
        assert d == "other"


class TestRangeQuery:
    def test_empty(self):
        assert _load().KDTree().range_query((0, 0), 100.0) == []

    def test_finds(self):
        t = _load().KDTree([((0.0, 0.0), "a"), ((1.0, 1.0), "b"), ((100.0, 100.0), "far")])
        data = [r[1] for r in t.range_query((0, 0), 5.0)]
        assert "a" in data and "b" in data and "far" not in data


class TestKNN:
    def test_empty(self):
        assert _load().KDTree().k_nearest_neighbors((0, 0), k=3) == []

    def test_k_results(self):
        t = _load().KDTree([((float(i), float(i)), f"p{i}") for i in range(10)])
        results = t.k_nearest_neighbors((0, 0), k=3)
        assert len(results) == 3
        assert results[0][1] == "p0"


class TestDistance:
    def test_distance(self):
        assert _load().KDTree._distance((0, 0), (3, 4)) == 5.0

    def test_same(self):
        assert _load().KDTree._distance((5, 5), (5, 5)) == 0.0
