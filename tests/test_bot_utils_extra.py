# -*- coding: utf-8 -*-
"""
추가 유틸 단위 테스트

- utils.error_handler — safe_execute, retry_on_failure, validate_unit,
  validate_position, log_error_context
- utils.kd_tree — KDTree nearest_neighbor / range_query / k_nearest_neighbors

주의: 레포 루트 `utils/` 와 이름이 충돌하므로 importlib로 파일 경로에서 로드.
"""

import asyncio
import importlib.util
import sys
from pathlib import Path

import pytest

BOT_ROOT = Path(__file__).resolve().parent.parent / "wicked_zerg_challenger"


def _load_module(name: str, relpath: str):
    path = BOT_ROOT / relpath
    spec = importlib.util.spec_from_file_location(name, str(path))
    module = importlib.util.module_from_spec(spec)
    bot_root_str = str(BOT_ROOT)
    if bot_root_str not in sys.path:
        sys.path.insert(0, bot_root_str)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


@pytest.fixture(scope="module")
def eh_mod():
    return _load_module("wzc_error_handler", "utils/error_handler.py")


@pytest.fixture(scope="module")
def kdt_mod():
    return _load_module("wzc_kd_tree", "utils/kd_tree.py")


# ═══════════════════════════════════════════════════════
# Error Handler
# ═══════════════════════════════════════════════════════


class TestSafeExecuteSync:
    def test_happy_path_returns_value(self, eh_mod):
        @eh_mod.safe_execute(default_return="default")
        def fn():
            return 42

        assert fn() == 42

    def test_attribute_error_returns_default(self, eh_mod):
        @eh_mod.safe_execute(default_return="fallback", log_errors=False)
        def fn():
            raise AttributeError("boom")

        assert fn() == "fallback"

    def test_key_error_returns_default(self, eh_mod):
        @eh_mod.safe_execute(default_return=0, log_errors=False)
        def fn():
            raise KeyError("boom")

        assert fn() == 0

    def test_unexpected_exception_returns_default(self, eh_mod):
        @eh_mod.safe_execute(default_return=None, log_errors=False)
        def fn():
            raise RuntimeError("boom")

        assert fn() is None

    def test_sc2boterror_returns_default(self, eh_mod):
        @eh_mod.safe_execute(default_return="fallback", log_errors=False)
        def fn():
            raise eh_mod.SC2BotError("bot error")

        assert fn() == "fallback"


class TestSafeExecuteAsync:
    @pytest.mark.asyncio
    async def test_async_happy_path(self, eh_mod):
        @eh_mod.safe_execute(default_return="default")
        async def fn():
            return "ok"

        assert await fn() == "ok"

    @pytest.mark.asyncio
    async def test_async_swallows_attribute_error(self, eh_mod):
        @eh_mod.safe_execute(default_return="fallback", log_errors=False)
        async def fn():
            raise AttributeError()

        assert await fn() == "fallback"


class TestRetrySync:
    def test_eventual_success(self, eh_mod):
        attempts = {"n": 0}

        @eh_mod.retry_on_failure(max_retries=3, delay=0)
        def fn():
            attempts["n"] += 1
            if attempts["n"] < 3:
                raise KeyError("retry me")
            return "ok"

        assert fn() == "ok"
        assert attempts["n"] == 3

    def test_exhausts_retries_returns_none(self, eh_mod):
        attempts = {"n": 0}

        @eh_mod.retry_on_failure(max_retries=2, delay=0)
        def fn():
            attempts["n"] += 1
            raise IndexError("always")

        assert fn() is None
        assert attempts["n"] == 2


class TestValidation:
    def test_validate_unit_none(self, eh_mod):
        assert eh_mod.validate_unit(None) is False

    def test_validate_unit_missing_attrs(self, eh_mod):
        class Fake:
            pass

        assert eh_mod.validate_unit(Fake()) is False

    def test_validate_unit_ok(self, eh_mod):
        class Fake:
            tag = 1
            position = (0, 0)
            type_id = "ZERGLING"

        assert eh_mod.validate_unit(Fake()) is True

    def test_validate_position_none(self, eh_mod):
        assert eh_mod.validate_position(None) is False

    def test_validate_position_tuple(self, eh_mod):
        assert eh_mod.validate_position((1.0, 2.0)) is True

    def test_validate_position_object(self, eh_mod):
        class P:
            x = 1.0
            y = 2.0

        assert eh_mod.validate_position(P()) is True

    def test_validate_position_invalid(self, eh_mod):
        assert eh_mod.validate_position(object()) is False


class TestLogErrorContext:
    def test_log_error_does_not_raise(self, eh_mod):
        try:
            raise ValueError("oops")
        except ValueError as e:
            # Should not raise, just logs
            eh_mod.log_error_context("test_fn", e, context={"k": "v"})


# ═══════════════════════════════════════════════════════
# KD Tree
# ═══════════════════════════════════════════════════════


class TestKDTreeBasic:
    def test_empty_tree(self, kdt_mod):
        tree = kdt_mod.KDTree()
        assert len(tree) == 0
        assert bool(tree) is False
        assert tree.nearest_neighbor((0, 0)) is None

    def test_build_from_points(self, kdt_mod):
        points = [((0, 0), "a"), ((1, 1), "b"), ((5, 5), "c")]
        tree = kdt_mod.KDTree(points)
        assert len(tree) == 3
        assert bool(tree) is True

    def test_nearest_neighbor_simple(self, kdt_mod):
        points = [((0, 0), "a"), ((1, 1), "b"), ((10, 10), "c")]
        tree = kdt_mod.KDTree(points)
        point, data, dist = tree.nearest_neighbor((0.1, 0.1))
        assert data == "a"
        assert dist < 0.5

    def test_nearest_neighbor_exclude(self, kdt_mod):
        points = [((0, 0), "a"), ((1, 1), "b"), ((10, 10), "c")]
        tree = kdt_mod.KDTree(points)
        point, data, dist = tree.nearest_neighbor((0.1, 0.1), exclude_data="a")
        assert data == "b"

    def test_range_query(self, kdt_mod):
        points = [((x, 0), f"p{x}") for x in range(10)]
        tree = kdt_mod.KDTree(points)
        results = tree.range_query((0, 0), radius=3.0)
        # Points at x=0,1,2,3 are within radius 3 from (0,0)
        found_data = {r[1] for r in results}
        assert found_data == {"p0", "p1", "p2", "p3"}

    def test_range_query_no_hits(self, kdt_mod):
        points = [((100, 100), "far")]
        tree = kdt_mod.KDTree(points)
        assert tree.range_query((0, 0), radius=1.0) == []

    def test_k_nearest_neighbors(self, kdt_mod):
        points = [((x, 0), f"p{x}") for x in range(10)]
        tree = kdt_mod.KDTree(points)
        results = tree.k_nearest_neighbors((0, 0), k=3)
        assert len(results) == 3
        # Sorted by distance ascending
        distances = [r[2] for r in results]
        assert distances == sorted(distances)
        # Three closest: p0, p1, p2
        assert {r[1] for r in results} == {"p0", "p1", "p2"}

    def test_k_nearest_zero_returns_empty(self, kdt_mod):
        points = [((0, 0), "a")]
        tree = kdt_mod.KDTree(points)
        assert tree.k_nearest_neighbors((0, 0), k=0) == []

    def test_k_nearest_more_than_size(self, kdt_mod):
        points = [((0, 0), "a"), ((1, 1), "b")]
        tree = kdt_mod.KDTree(points)
        results = tree.k_nearest_neighbors((0, 0), k=10)
        assert len(results) == 2

    def test_build_unit_kdtree(self, kdt_mod):
        class Pos:
            def __init__(self, x, y):
                self.x = x
                self.y = y

        class Unit:
            def __init__(self, x, y, tag):
                self.position = Pos(x, y)
                self.tag = tag

        units = [Unit(0, 0, 1), Unit(3, 4, 2), Unit(10, 10, 3)]
        tree = kdt_mod.build_unit_kdtree(units)
        assert len(tree) == 3
        _, unit, _ = tree.nearest_neighbor((0.5, 0.5))
        assert unit.tag == 1


class TestKDTreeDistance:
    def test_euclidean_distance(self, kdt_mod):
        d = kdt_mod.KDTree._distance((0, 0), (3, 4))
        assert d == pytest.approx(5.0)

    def test_distance_same_point(self, kdt_mod):
        d = kdt_mod.KDTree._distance((1, 1), (1, 1))
        assert d == 0.0
