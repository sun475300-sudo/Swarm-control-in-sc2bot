# -*- coding: utf-8 -*-
"""utils.spatial_partition 테스트"""

import sys
import importlib.util
from pathlib import Path

import pytest

PROJECT_ROOT = Path(__file__).parent.parent
BOT_ROOT = PROJECT_ROOT / "wicked_zerg_challenger"
if str(BOT_ROOT) not in sys.path:
    sys.path.insert(0, str(BOT_ROOT))


def _load():
    if "bot_spatial_partition" in sys.modules:
        return sys.modules["bot_spatial_partition"]
    spec = importlib.util.spec_from_file_location(
        "bot_spatial_partition", BOT_ROOT / "utils" / "spatial_partition.py"
    )
    mod = importlib.util.module_from_spec(spec)
    sys.modules["bot_spatial_partition"] = mod
    spec.loader.exec_module(mod)
    return mod


class TestInit:
    def test_default(self):
        g = _load().SpatialGrid()
        assert g.cell_size == 5.0 and g.size == 0
        assert len(g) == 0 and bool(g) is False

    def test_zero_cell_size(self):
        assert _load().SpatialGrid(cell_size=0).cell_size > 0


class TestInsertRemove:
    def test_insert(self):
        g = _load().SpatialGrid()
        g.insert((10, 20), "u1")
        assert g.size == 1 and bool(g) is True

    def test_remove(self):
        g = _load().SpatialGrid()
        u = ["u1"]
        g.insert((10, 20), u)
        assert g.remove(u) is True and g.size == 0

    def test_remove_nonexistent(self):
        assert _load().SpatialGrid().remove("x") is False

    def test_clear(self):
        g = _load().SpatialGrid()
        g.insert((0, 0), "a")
        g.clear()
        assert g.size == 0


class TestQuery:
    def test_empty_radius(self):
        assert _load().SpatialGrid().query_radius((0, 0), 50) == []

    def test_finds_in_radius(self):
        g = _load().SpatialGrid()
        g.insert((0, 0), "a")
        g.insert((3, 4), "b")
        g.insert((100, 100), "far")
        data = [r[1] for r in g.query_radius((0, 0), 10)]
        assert "a" in data and "b" in data and "far" not in data

    def test_nn_empty(self):
        assert _load().SpatialGrid().nearest_neighbor((0, 0)) is None

    def test_nn_single(self):
        g = _load().SpatialGrid()
        g.insert((10, 20), "u")
        result = g.nearest_neighbor((0, 0))
        assert result is not None and result[1] == "u"

    def test_knn(self):
        g = _load().SpatialGrid()
        for i in range(5):
            g.insert((float(i*10), float(i*10)), f"u{i}")
        assert len(g.k_nearest_neighbors((0, 0), k=3)) == 3


class TestDynamicPartition:
    def test_init(self):
        p = _load().DynamicSpatialPartition(cell_size=5.0, density_threshold=10)
        assert p.cell_size == 5.0 and p.density_threshold == 10
